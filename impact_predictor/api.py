"""FastAPI adapter over the locally trained model. No live integrations.

[AI-GENERATED CONTENT BY AIFEL TEAM ASSISTANT :: AIFEL-AI-LABEL-V1]
"""

from contextlib import asynccontextmanager
import csv
import importlib.metadata
import json
import os
import threading

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import joblib

from . import AI_LABEL
from .api_models import CustomerRisk, PredictionRequest, PredictionResponse, ServiceRisk
from .features import FEATURE_NAMES, extract_features
from .inference import predict_assessment
from .paths import INVENTORY, PROJECT, digest, load_run
from .simulation import Alarm, FeedStatus, Maintenance, Performance, Settings, Topology


WARNINGS = [
    "Synthetic-only model; scores are not calibrated production outage probabilities.",
    "Inventory associations do not verify forwarding paths or real service protection.",
    "Heuristic components explain only the heuristic, not Random Forest attribution.",
]


class PredictorService:
    def __init__(self, run_name="run-001"):
        run, manifest = load_run(run_name)
        neighborhood = INVENTORY
        contract = PROJECT / "approved_contract.json"
        if digest(contract) != manifest["contract_sha256"]:
            raise ValueError("Approved contract differs from the trained model contract")
        for name in ("features.py", "simulation.py", "inference.py"):
            if digest(PROJECT / "impact_predictor" / name) != manifest["code_sha256"][
                "impact_predictor/" + name
            ]:
                raise ValueError("Feature/inference code differs from the trained run")
        for name, version in manifest["dependency_versions"].items():
            if importlib.metadata.version(name) != version:
                raise ValueError("Training dependency versions differ; use the locked environment")
        for name in (
            "model.joblib", "evaluation.json", "demo-replay/hiper_performance.csv",
            "demo-replay/rfm_alarms.csv", "demo-replay/feed_status.csv",
        ):
            if digest(run / name) != manifest["artifacts"][name]:
                raise ValueError("Local model/replay artifact checksum mismatch")
        # This is the explicitly selected local training artifact, never a remote upload.
        self.bundle = joblib.load(run / "model.joblib")
        if (self.bundle["data_domain"] != "synthetic_only"
                or tuple(self.bundle["feature_names"]) != FEATURE_NAMES
                or self.bundle["contract_sha256"] != manifest["contract_sha256"]
                or self.bundle["neighborhood_manifest_sha256"]
                != manifest["neighborhood_manifest_sha256"]):
            raise ValueError("Unsupported model domain or feature schema")
        self.settings = Settings.load(contract)
        self.topology = Topology.load(neighborhood)
        self.inventory = json.loads((neighborhood / "topology.json").read_text())
        self.evaluation = json.loads((run / "evaluation.json").read_text())
        self.run_name = run_name
        self.model_sha256 = manifest["artifacts"]["model.joblib"]
        self._capacity = threading.BoundedSemaphore(2)
        self.replay = {}
        for name, cls in (
            ("hiper_performance", Performance), ("rfm_alarms", Alarm),
            ("feed_status", FeedStatus),
        ):
            with (run / "demo-replay" / f"{name}.csv").open(newline="", encoding="utf-8") as stream:
                self.replay[name] = [
                    cls(**{
                        key: (value if key in {"resource_id", "action"}
                              else value == "True" if key.endswith("_available")
                              else float(value) if key in {
                                  "latency_ms", "packet_delivery_pct", "jitter_ms"
                              } else int(value))
                        for key, value in row.items()
                    }) for row in csv.DictReader(stream)
                ]

    def health(self):
        return {
            "status": "ready", "modelId": self.run_name,
            "modelSha256": self.model_sha256, "dataDomain": "synthetic_only",
        }

    def metadata(self):
        test = self.evaluation["evaluation"]["test"]
        metrics = test["random_forest"]
        return {
            "aiLabel": AI_LABEL, **{key: value for key, value in self.health().items()
                                    if key != "status"},
            "forecastHorizonMinutes": self.settings.step_minutes * self.settings.horizon_intervals,
            "featureNames": list(FEATURE_NAMES),
            "bandThresholds": self.bundle["band_thresholds"],
            "testMetrics": {
                "precision": metrics["precision"], "recall": metrics["recall"],
                "prAuc": metrics["PR_AUC_average_precision"],
                "forecastCoverage": test["forecast_coverage_excluding_observed_already_degraded"],
                "medianProactiveLeadMinutes": metrics["median_proactive_lead_minutes"],
            },
            "warnings": WARNINGS,
        }

    def predict(self, request, demo=False):
        service_ids = (sorted(self.topology.service_resources) if request.service_ids is None
                       else request.service_ids)
        if set(service_ids) - self.topology.service_resources.keys():
            raise HTTPException(404, "Service alias is not in this inventory cohort")
        if demo:
            performance = self.replay["hiper_performance"]
            alarms = self.replay["rfm_alarms"]
            maintenance = []
            feeds = self.replay["feed_status"]
        else:
            all_resources = set().union(*self.topology.service_resources.values())
            supplied = {row.resource_id for records in (
                request.performance, request.alarms, request.maintenance
            ) for row in records}
            if supplied - all_resources:
                raise HTTPException(422, "Resource alias is not in this inventory cohort")
            performance = [Performance(**row.model_dump()) for row in request.performance]
            alarms = [Alarm(**row.model_dump()) for row in request.alarms]
            maintenance = [Maintenance(**row.model_dump()) for row in request.maintenance]
            feeds = [FeedStatus(**row.model_dump()) for row in request.feed_status]
        results = []
        with self._capacity:
            for service in service_ids:
                assessment = extract_features(
                    self.topology.service_resources[service], request.prediction_minute,
                    performance, alarms, maintenance, feeds, self.settings,
                )
                results.append(ServiceRisk(
                    service_id=service, customer_id=self.topology.customers[service],
                    **predict_assessment(self.bundle, assessment),
                ))
        order = {"High": 1, "Elevated": 2, "Watch": 3, "Low": 4, "Insufficient evidence": 5}
        results.sort(key=lambda result: (
            0 if result.status == "already_degraded" else order[result.risk_band],
            result.service_id,
        ))
        customers = []
        for customer in sorted({result.customer_id for result in results}):
            customer_results = [row for row in results if row.customer_id == customer]
            assessed = [row for row in customer_results if row.status == "assessed"]
            already = sum(row.status == "already_degraded" for row in customer_results)
            customers.append(CustomerRisk(
                customer_id=customer,
                status="already_degraded" if already else "assessed" if assessed
                else "insufficient_evidence",
                risk_band_among_assessed_services=(
                    min((row.risk_band for row in assessed), key=lambda band: order[band])
                    if assessed else None
                ),
                assessed_services=len(assessed),
                insufficient_evidence_services=sum(
                    row.status == "insufficient_evidence" for row in customer_results
                ),
                already_degraded_services=already,
            ))
        return PredictionResponse(
            ai_label=AI_LABEL, data_domain="synthetic_only",
            source="synthetic_replay" if demo else "provided_synthetic_observations",
            model_id=self.run_name, prediction_minute=request.prediction_minute,
            forecast_horizon_minutes=self.settings.step_minutes * self.settings.horizon_intervals,
            services=results, customers=customers, warnings=WARNINGS,
        )


def create_app(service_factory=PredictorService):
    @asynccontextmanager
    async def lifespan(app):
        app.state.predictor = service_factory(os.environ.get("IMPACT_RUN_NAME", "run-001"))
        yield

    app = FastAPI(title="Customer Impact Predictor - synthetic POC", version="1.0.0",
                  lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request, _error):
        return JSONResponse(
            status_code=422,
            content={"detail": "Request violates the observation schema", "aiLabel": AI_LABEL},
        )

    @app.get("/health")
    def health(request: Request):
        return request.app.state.predictor.health()

    @app.get("/v1/model")
    def model(request: Request):
        return request.app.state.predictor.metadata()

    @app.get("/v1/inventory")
    def inventory(request: Request):
        graph = request.app.state.predictor.inventory
        return {
            "aiLabel": AI_LABEL, "dataDomain": "synthetic_only",
            "nodes": graph["nodes"], "edges": graph["edges"],
            "relationshipSemantics": graph["relationship_semantics"],
        }

    @app.post("/v1/predictions", response_model=PredictionResponse)
    def predict(body: PredictionRequest, request: Request):
        return request.app.state.predictor.predict(body)

    @app.get("/v1/demo/predictions", response_model=PredictionResponse)
    def demo(request: Request, minute: int = Query(default=150, ge=0, le=360, multiple_of=5)):
        return request.app.state.predictor.predict(
            PredictionRequest(prediction_minute=minute), demo=True
        )

    return app


app = create_app()
