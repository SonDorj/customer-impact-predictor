"""Inference API regressions against the real, checksum-verified local model."""

import unittest
from dataclasses import asdict

from fastapi.testclient import TestClient

from impact_predictor.api import create_app


class InferenceApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_context = TestClient(create_app())
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)

    def test_real_model_replay_and_customer_aggregation(self):
        response = self.client.get("/v1/demo/predictions?minute=150")
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["dataDomain"], "synthetic_only")
        self.assertEqual(body["forecastHorizonMinutes"], 30)
        self.assertEqual(len(body["services"]), 12)
        self.assertEqual(len(body["customers"]), 9)
        services = {row["serviceId"]: row for row in body["services"]}
        self.assertEqual(services["EVC-01"]["riskBand"], "High")
        self.assertEqual(services["EVC-12"]["status"], "insufficient_evidence")
        self.assertIsNone(services["EVC-12"]["uncalibratedModelScore"])
        self.assertIsNone(services["EVC-12"]["heuristicScore"])
        customer = next(row for row in body["customers"] if row["customerId"] == "Org-I")
        self.assertEqual(customer["status"], "insufficient_evidence")
        self.assertIsNone(customer["riskBandAmongAssessedServices"])

    def test_missing_custom_observations_abstain_without_fallback(self):
        response = self.client.post("/v1/predictions", json={
            "predictionMinute": 150, "serviceIds": ["EVC-01"],
        })
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["source"], "provided_synthetic_observations")
        self.assertEqual(body["services"][0]["status"], "insufficient_evidence")
        self.assertIsNone(body["services"][0]["uncalibratedModelScore"])

    def test_custom_source_observations_match_replay_and_ignore_future_values(self):
        predictor = self.client.app.state.predictor
        request = {
            "predictionMinute": 150, "serviceIds": ["EVC-01"],
            "performance": [asdict(row) for row in predictor.replay["hiper_performance"]],
            "alarms": [asdict(row) for row in predictor.replay["rfm_alarms"]],
            "feedStatus": [asdict(row) for row in predictor.replay["feed_status"]],
        }
        reference = self.client.get("/v1/demo/predictions?minute=150").json()
        expected = next(row for row in reference["services"] if row["serviceId"] == "EVC-01")
        for row in request["performance"]:
            if row["observed_minute"] > 150:
                row["latency_ms"] = 900
                row["packet_delivery_pct"] = 1
        response = self.client.post("/v1/predictions", json=request)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()["services"][0]
        self.assertEqual(result["riskBand"], expected["riskBand"])
        self.assertAlmostEqual(
            result["uncalibratedModelScore"], expected["uncalibratedModelScore"], places=12
        )

    def test_existing_degradation_is_not_returned_as_future_probability(self):
        resources = self.client.app.state.predictor.topology.service_resources["EVC-01"]
        response = self.client.post("/v1/predictions", json={
            "predictionMinute": 30, "serviceIds": ["EVC-01"],
            "performance": [
                {"resourceId": resource, "eventMinute": minute, "observedMinute": minute,
                 "latencyMs": 110 if minute >= 25 else 20,
                 "packetDeliveryPct": 99.99, "jitterMs": 1}
                for resource in sorted(resources) for minute in range(5, 35, 5)
            ],
        })
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()["services"][0]
        self.assertEqual(result["status"], "already_degraded")
        self.assertIsNone(result["uncalibratedModelScore"])
        self.assertIsNone(result["riskBand"])

    def test_unknown_service_is_explicit_not_found(self):
        response = self.client.post("/v1/predictions", json={
            "predictionMinute": 150, "serviceIds": ["EVC-99"],
        })
        self.assertEqual(response.status_code, 404)

    def test_invalid_and_duplicate_observations_rejected(self):
        for request in [
            {"predictionMinute": 151},
            {"predictionMinute": 150, "target": 1},
            {"predictionMinute": 150, "serviceIds": []},
            {"predictionMinute": 150, "serviceIds": ["EVC-01", "EVC-01"]},
            {"predictionMinute": 150, "performance": [{
                "resourceId": "R-01", "eventMinute": 30, "observedMinute": 25,
                "latencyMs": 20, "packetDeliveryPct": 99.9, "jitterMs": 1,
            }]},
        ]:
            with self.subTest(request=request):
                self.assertEqual(self.client.post("/v1/predictions", json=request).status_code, 422)

    def test_metadata_and_inventory_are_alias_only(self):
        metadata = self.client.get("/v1/model").json()
        inventory = self.client.get("/v1/inventory").json()
        self.assertEqual(metadata["modelId"], "run-001")
        self.assertEqual(len(metadata["modelSha256"]), 64)
        self.assertTrue(all(node["id"].startswith(("EVC-", "R-", "UNI-", "Org-"))
                            for node in inventory["nodes"]))


if __name__ == "__main__":
    unittest.main()
