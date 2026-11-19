"""Focused tests for causal labels, evidence gating and grouped evaluation."""

from dataclasses import replace
import math
from pathlib import Path
import unittest

from impact_predictor.features import extract_features, valid_performance
from impact_predictor.inference import predict_assessment
from impact_predictor.simulation import (
    Alarm, FeedStatus, Maintenance, Performance, Settings, Topology,
    confirmed_states, future_label, new_onsets, simulate_episode,
)
from impact_predictor.training import episode_split, select_alert_threshold

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


class PredictorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = Settings.load(ROOT / "approved_contract.json")
        cls.topology = Topology.load(ROOT / "data/inventory")

    def healthy(self, resource="R-01"):
        return [
            Performance(resource, minute, minute, 20.0, 99.99, 1.0)
            for minute in range(5, 35, 5)
        ]

    def assess(self, performance, resources=frozenset({"R-01"}), **kwargs):
        return extract_features(
            resources, 30, performance, kwargs.get("alarms", []),
            kwargs.get("maintenance", []),
            kwargs.get("feeds", [FeedStatus(30, 30, True, True)]),
            kwargs.get("settings", self.settings),
        )

    def test_confirmation_and_open_closed_forecast_boundary(self):
        states = confirmed_states([False] * 5 + [True, True] + [False] * 4)
        self.assertEqual(new_onsets(states), [35])
        self.assertEqual(future_label(states, 0, 6), 1)
        self.assertEqual(future_label(states, 4, 1), 0)
        self.assertEqual(future_label(states, 6, 3), 0)
        with self.assertRaisesRegex(ValueError, "censored"):
            future_label(states, 6, 6)

    def test_missing_resource_is_not_imputed_into_healthy_service(self):
        assessment = self.assess(
            self.healthy(), resources=frozenset({"R-01", "R-02"})
        )
        self.assertEqual(assessment.status, "insufficient_evidence")
        self.assertIsNone(assessment.features)

    def test_history_coverage_and_freshness(self):
        self.assertEqual(self.assess(self.healthy()[:-1]).status, "assessed")
        self.assertEqual(self.assess(self.healthy()[:-2]).status, "insufficient_evidence")
        stale = self.assess(
            self.healthy()[:-1], settings=replace(self.settings, freshness_minutes=0)
        )
        self.assertEqual(stale.status, "insufficient_evidence")
        self.assertIn("stale", stale.reason)

    def test_invalid_metrics_are_not_valid_health_evidence(self):
        original = self.healthy()[0]
        for invalid in (
            replace(original, latency_ms=math.nan),
            replace(original, latency_ms=-1),
            replace(original, packet_delivery_pct=101),
            replace(original, jitter_ms=None),
        ):
            self.assertFalse(valid_performance(invalid))

    def test_future_or_delayed_observations_cannot_change_features(self):
        reference = self.assess(self.healthy())
        changed = self.assess(
            self.healthy() + [
                Performance("R-01", 35, 35, 300, 90, 50),
                Performance("R-01", 25, 40, 300, 90, 50),
            ],
            alarms=[Alarm("R-01", 25, 40, 3, "RAISE")],
            maintenance=[
                Maintenance("R-01", 25, 90, 40, 40),
                Maintenance("R-01", 25, 90, 5, 40),
            ],
        )
        self.assertEqual(reference.features, changed.features)

    def test_missing_optional_feeds_are_not_zero_events(self):
        result = self.assess(
            self.healthy(), feeds=[FeedStatus(30, 30, False, False)]
        )
        self.assertEqual(result.status, "assessed")
        self.assertTrue(math.isnan(result.features[11]))
        self.assertTrue(math.isnan(result.features[14]))
        self.assertEqual(result.features[13], 0)
        self.assertEqual(result.features[16], 0)

    def test_observed_existing_degradation_is_separate_from_forecast(self):
        observations = self.healthy()
        observations[-2:] = [replace(row, latency_ms=110) for row in observations[-2:]]
        result = self.assess(observations)
        self.assertEqual(result.status, "already_degraded")
        self.assertIsNone(result.features)

    def test_abstention_never_calls_classifier_or_emits_score(self):
        class MustNotPredict:
            def predict_proba(self, _):
                raise AssertionError("Abstention reached classifier")

        result = predict_assessment({"model": MustNotPredict()}, self.assess([]))
        self.assertEqual(result["risk_band"], "Insufficient evidence")
        self.assertIsNone(result["uncalibrated_model_score"])
        self.assertIsNone(result["heuristic_score"])

    def test_episode_split_keeps_all_windows_together(self):
        assignments = {
            split: {episode for episode in range(300)
                    if episode_split(episode, 300) == split}
            for split in ("train", "validation", "test")
        }
        self.assertEqual([len(values) for values in assignments.values()], [210, 45, 45])
        self.assertFalse(assignments["train"] & assignments["validation"])
        self.assertFalse(assignments["validation"] & assignments["test"])
        self.assertEqual(set.union(*assignments.values()), set(range(300)))

    def test_demo_topology_propagates_only_declared_event_exposure(self):
        episode = simulate_episode(self.topology, self.settings, 0, 902026, demo=True)
        primary = [
            service for service, resources in self.topology.service_resources.items()
            if self.topology.primary_resource in resources
        ]
        self.assertEqual(len(primary), 5)
        self.assertTrue(any(episode.confirmed_degradation[primary[0]]))
        self.assertTrue(all(
            episode.confirmed_degradation[service] == episode.confirmed_degradation[primary[0]]
            for service in primary
        ))
        missing_resources = self.topology.service_resources[self.topology.missing_service]
        self.assertFalse(any(row.resource_id in missing_resources for row in episode.performance))
        non_event_services = [
            service for service, resources in self.topology.service_resources.items()
            if self.topology.primary_resource not in resources
            and self.topology.secondary_resource not in resources
        ]
        self.assertTrue(all(not any(episode.confirmed_degradation[service])
                            for service in non_event_services))

    def test_resource_simulation_is_seed_reproducible(self):
        first = simulate_episode(self.topology, self.settings, 1, 2026)
        second = simulate_episode(self.topology, self.settings, 1, 2026)
        self.assertEqual(first, second)

    def test_alert_threshold_rejects_uninformative_validation_labels(self):
        with self.assertRaisesRegex(ValueError, "both classes"):
            select_alert_threshold(np.array([0, 0]), np.array([0.1, 0.9]))


if __name__ == "__main__":
    unittest.main()
