"""Verify all bundled bytes and load the trusted, local synthetic-only model."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from impact_predictor.api import PredictorService
from impact_predictor.paths import load_run

directory, _ = load_run("run-001")
service = PredictorService()
assert service.health()["status"] == "ready"
assert service.health()["dataDomain"] == "synthetic_only"
print(f"Verified bundled inventory, provenance, dependencies and model: {directory.name}")
print(f"Model SHA-256: {service.model_sha256}")
