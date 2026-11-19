"""Write a complete camelCase POST request from the bundled synthetic replay."""

import argparse
from dataclasses import asdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from impact_predictor.api import PredictorService
from impact_predictor.api_models import PredictionRequest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minute", type=int, default=150)
    parser.add_argument("--service-id", action="append")
    parser.add_argument("--output", type=Path, default=Path("build/demo-request.json"))
    args = parser.parse_args()
    predictor = PredictorService()
    body = PredictionRequest(
        prediction_minute=args.minute, service_ids=args.service_id,
        performance=[asdict(row) for row in predictor.replay["hiper_performance"]],
        alarms=[asdict(row) for row in predictor.replay["rfm_alarms"]],
        feed_status=[asdict(row) for row in predictor.replay["feed_status"]],
    )
    if args.service_id and set(args.service_id) - predictor.topology.service_resources.keys():
        parser.error("Service alias is not in this cohort")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(body.model_dump_json(by_alias=True, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote synthetic replay request to {args.output}")


if __name__ == "__main__":
    main()
