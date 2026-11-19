"""Run: python -m impact_predictor --run-name run-002"""

import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack
import csv
from dataclasses import fields
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import tempfile

import joblib
import numpy as np

from . import AI_LABEL
from .features import FEATURE_NAMES, extract_features
from .inference import predict_assessment, risk_band
from .paths import INVENTORY, verify_inventory
from .simulation import (
    Alarm, FeedStatus, Maintenance, Performance, Settings, Topology,
    future_label, new_onsets, simulate_episode,
)
from .training import compare_models, episode_split, load_assessed_windows


PROJECT = Path(__file__).resolve().parents[1]
NEIGHBORHOOD = INVENTORY


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save_json(path, data):
    path.write_text(
        json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def csv_writer(stack, path, columns):
    stream = stack.enter_context(path.open("x", encoding="utf-8", newline=""))
    writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="raise")
    writer.writeheader()
    return writer


def service_observations(episode, resources):
    return (
        [row for row in episode.performance if row.resource_id in resources],
        [row for row in episode.alarms if row.resource_id in resources],
        [row for row in episode.maintenance if row.resource_id in resources],
        episode.feed_status,
    )


def prediction_indices(settings):
    return range(
        settings.history_intervals - 1,
        settings.episode_intervals - settings.horizon_intervals,
    )


def generate_dataset(directory, topology, settings, seed):
    directory.mkdir()
    outcomes = []
    status_counts = defaultdict(Counter)
    window_columns = [
        "episode_number", "episode_id", "service_id", "prediction_minute",
        "split", "status", "reason", "target",
    ] + list(FEATURE_NAMES)
    with ExitStack() as stack:
        window_writer = csv_writer(stack, directory / "feature_windows.csv", window_columns)
        episode_writer = csv_writer(
            stack, directory / "episode_index.csv",
            ["episode_number", "episode_id", "start_utc", "scenario", "split", "synthetic"],
        )
        source_writers = {}
        for name, cls in (
            ("hiper_performance", Performance), ("rfm_alarms", Alarm),
            ("clarify_gcr_maintenance", Maintenance), ("feed_status", FeedStatus),
        ):
            source_writers[name] = csv_writer(
                stack, directory / f"{name}.csv",
                ["episode_id", "synthetic"] + [field.name for field in fields(cls)],
            )
        outcome_writer = csv_writer(
            stack, directory / "clarify_incident_outcomes.csv",
            ["episode_number", "episode_id", "service_id", "confirmation_minute",
             "first_bad_interval_start_minute", "eligible_for_evaluation", "synthetic"],
        )
        for number in range(settings.episodes):
            episode = simulate_episode(topology, settings, number, seed)
            split = episode_split(number, settings.episodes)
            episode_writer.writerow({
                "episode_number": number, "episode_id": episode.episode_id,
                "start_utc": episode.start_utc, "scenario": episode.scenario,
                "split": split, "synthetic": True,
            })
            for name, records in (
                ("hiper_performance", episode.performance), ("rfm_alarms", episode.alarms),
                ("clarify_gcr_maintenance", episode.maintenance),
                ("feed_status", episode.feed_status),
            ):
                for record in records:
                    source_writers[name].writerow({
                        "episode_id": episode.episode_id, "synthetic": True,
                        **{field.name: getattr(record, field.name) for field in fields(record)},
                    })
            for service, resources in sorted(topology.service_resources.items()):
                observations = service_observations(episode, resources)
                for index in prediction_indices(settings):
                    minute = (index + 1) * settings.step_minutes
                    assessment = extract_features(
                        resources, minute, *observations, settings
                    )
                    status_counts[split][assessment.status] += 1
                    values = {
                        "episode_number": number, "episode_id": episode.episode_id,
                        "service_id": service, "prediction_minute": minute,
                        "split": split, "status": assessment.status,
                        "reason": assessment.reason,
                        "target": future_label(
                            episode.confirmed_degradation[service], index,
                            settings.horizon_intervals,
                        ),
                    }
                    if assessment.features is not None:
                        values.update(zip(FEATURE_NAMES, assessment.features, strict=True))
                    window_writer.writerow(values)
                for confirmation in new_onsets(
                    episode.confirmed_degradation[service], settings.step_minutes
                ):
                    eligible = (
                        settings.history_intervals * settings.step_minutes
                        < confirmation <= settings.episode_intervals * settings.step_minutes
                    )
                    outcome = {
                        "episode_number": number, "episode_id": episode.episode_id,
                        "service_id": service, "confirmation_minute": confirmation,
                        "first_bad_interval_start_minute": confirmation - 2 * settings.step_minutes,
                        "eligible_for_evaluation": eligible, "synthetic": True,
                    }
                    outcome_writer.writerow(outcome)
                    if eligible:
                        outcomes.append(outcome)
            if (number + 1) % 50 == 0:
                print(json.dumps({"phase": "simulation", "completed_episodes": number + 1}),
                      flush=True)
    return outcomes, status_counts


def export_test_predictions(path, windows, y, mask, model_scores, baseline_scores, bundle):
    with ExitStack() as stack:
        writer = csv_writer(
            stack, path, [
                "episode_id", "service_id", "prediction_minute", "target",
                "uncalibrated_model_score", "risk_band", "model_alert",
                "heuristic_score", "heuristic_alert",
            ],
        )
        for index in np.flatnonzero(mask):
            window = windows[index]
            score = float(model_scores[index])
            writer.writerow({
                "episode_id": window.episode_id, "service_id": window.service_id,
                "prediction_minute": window.minute, "target": int(y[index]),
                "uncalibrated_model_score": score,
                "risk_band": risk_band(score, bundle["band_thresholds"]),
                "model_alert": score >= bundle["band_thresholds"]["High"],
                "heuristic_score": float(baseline_scores[index]),
                "heuristic_alert": (
                    baseline_scores[index] >= bundle["baseline_alert_threshold"]
                ),
            })


def replay_demo(directory, topology, settings, seed, bundle):
    directory.mkdir()
    episode = simulate_episode(topology, settings, 0, seed + 900_000, demo=True)
    snapshot_rows = []
    predictions = []
    with ExitStack() as stack:
        writer = csv_writer(
            stack, directory / "predictions.csv",
            ["prediction_minute", "service_id", "customer_id", "status", "reason",
             "risk_band", "uncalibrated_model_score", "heuristic_score",
             "heuristic_components", "evidence"],
        )
        for index in prediction_indices(settings):
            minute = (index + 1) * settings.step_minutes
            for service, resources in sorted(topology.service_resources.items()):
                assessment = extract_features(
                    resources, minute, *service_observations(episode, resources), settings
                )
                result = predict_assessment(bundle, assessment)
                record = {
                    "prediction_minute": minute, "service_id": service,
                    "customer_id": topology.customers[service], **result,
                }
                predictions.append(record)
                writer.writerow({
                    **record,
                    "heuristic_components": json.dumps(result["heuristic_components"]),
                    "evidence": json.dumps(result["evidence"], allow_nan=False),
                })
        for name, records, cls in (
            ("hiper_performance", episode.performance, Performance),
            ("rfm_alarms", episode.alarms, Alarm),
            ("feed_status", episode.feed_status, FeedStatus),
        ):
            source = csv_writer(
                stack, directory / f"{name}.csv",
                [field.name for field in fields(cls)],
            )
            for record in records:
                source.writerow({field.name: getattr(record, field.name) for field in fields(cls)})
    missing_rows = [row for row in predictions if row["service_id"] == topology.missing_service]
    if not all(row["status"] == "insufficient_evidence"
               and row["uncalibrated_model_score"] is None for row in missing_rows):
        raise ValueError("Missing-evidence demo unexpectedly produced a forecast")
    by_minute = defaultdict(list)
    primary = {service for service, resources in topology.service_resources.items()
               if topology.primary_resource in resources}
    for row in predictions:
        by_minute[row["prediction_minute"]].append(row)
    chosen_minute = max(
        sorted(by_minute),
        key=lambda minute: sum(
            row["risk_band"] == "High" and row["service_id"] in primary
            for row in by_minute[minute]
        ),
    )
    snapshot_rows = by_minute[chosen_minute]
    customer_states = {}
    ordering = {label: rank for rank, label in enumerate(("Low", "Watch", "Elevated", "High"))}
    for customer in sorted(set(topology.customers.values())):
        customer_rows = [row for row in snapshot_rows if row["customer_id"] == customer]
        assessed = [row for row in customer_rows if row["status"] == "assessed"]
        customer_states[customer] = {
            "risk_band_among_assessed_services": max(
                (row["risk_band"] for row in assessed),
                key=lambda label: ordering[label], default=None,
            ),
            "assessed_services": len(assessed),
            "insufficient_evidence_services": sum(
                row["status"] == "insufficient_evidence" for row in customer_rows
            ),
            "already_degraded_services": sum(
                row["status"] == "already_degraded" for row in customer_rows
            ),
        }
    save_json(directory / "snapshot.json", {
        "ai_label": AI_LABEL, "synthetic": True, "episode_start_utc": episode.start_utc,
        "prediction_minute": chosen_minute,
        "selection": "Earliest replay frame with the most primary-group High forecasts; no scores altered.",
        "services": snapshot_rows, "customers": customer_states,
        "limitations": "Customer risk is max assessed-service band, not probability. Missing services stay visible.",
    })
    return {
        "missing_service_always_abstained": True, "replay_windows": len(predictions),
        "representative_frame_minute": chosen_minute,
        "frame_status_counts": dict(Counter(row["status"] for row in snapshot_rows)),
        "frame_risk_band_counts": dict(Counter(
            row["risk_band"] for row in snapshot_rows if row["risk_band"] is not None
        )),
    }


def run(run_name, seed):
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", run_name) is None:
        raise ValueError("Use a simple run name without directory separators")
    runs = PROJECT / "runs"
    runs.mkdir(exist_ok=True)
    output = runs / run_name
    if output.exists() or (PROJECT / "models" / run_name).exists():
        raise FileExistsError("Refusing to overwrite or shadow an existing run")
    verify_inventory()
    contract_path = PROJECT / "approved_contract.json"
    settings = Settings.load(contract_path)
    topology = Topology.load(NEIGHBORHOOD)
    with tempfile.TemporaryDirectory(prefix=f".{run_name}-", dir=runs) as temporary:
        stage = Path(temporary)
        outcomes, counts = generate_dataset(stage / "synthetic-data", topology, settings, seed)
        x, y, windows = load_assessed_windows(stage / "synthetic-data/feature_windows.csv")
        print(json.dumps({"phase": "training", "assessed_windows": len(y)}), flush=True)
        bundle, evaluation, masks, scores, baseline = compare_models(
            x, y, windows, outcomes, settings.episodes, seed, settings
        )
        bundle.update({
            "ai_label": AI_LABEL, "data_domain": "synthetic_only",
            "contract_sha256": sha256(contract_path),
            "neighborhood_manifest_sha256": sha256(NEIGHBORHOOD / "manifest.json"),
        })
        model_path = stage / "model.joblib"
        joblib.dump(bundle, model_path, compress=3)
        # Only reload the artifact generated here, never a downloaded pickle/joblib.
        restored = joblib.load(model_path)
        sample = x[np.flatnonzero(masks["test"])[:128]]
        if not np.allclose(
            restored["model"].predict_proba(sample),
            bundle["model"].predict_proba(sample), rtol=0, atol=1e-12,
        ):
            raise ValueError("Reloaded model predictions differ")
        export_test_predictions(
            stage / "heldout_predictions.csv", windows, y, masks["test"], scores, baseline, bundle
        )
        replay = replay_demo(stage / "demo-replay", topology, settings, seed, restored)
        for split, counter in counts.items():
            eligible = counter["assessed"] + counter["insufficient_evidence"]
            evaluation[split] = {
                **evaluation.get(split, {}), "status_counts": dict(counter),
                "forecast_coverage_excluding_observed_already_degraded": (
                    counter["assessed"] / max(1, eligible)
                ),
            }
        save_json(stage / "evaluation.json", {
            "ai_label": AI_LABEL, "data_domain": "synthetic_only",
            "evaluation": evaluation, "model_band_thresholds": bundle["band_thresholds"],
            "band_method": "High maximizes validation F1; Watch/Elevated use 50th/90th percentiles of distinct validation scores below High.",
            "baseline_alert_threshold": bundle["baseline_alert_threshold"],
            "important_limitations": [
                "Synthetic generator-dependent performance, not production accuracy.",
                "Whole episodes are disjoint; topology and generator family are shared across splits.",
                "Service windows sharing a resource are correlated, not independent samples.",
                "Lead to confirmation is not the same as lead before degradation begins.",
                "Neither model nor heuristic was tuned using the test split.",
                "No measured financial savings or production probability calibration.",
            ],
        })
        save_json(stage / "verification.json", {
            "ai_label": AI_LABEL, "local_model_reload_matches": True,
            "whole_episode_splits": {
                name: sorted({windows[index].episode_number
                              for index in np.flatnonzero(mask)})
                for name, mask in masks.items()
            }, "demo": replay,
        })
        save_json(stage / "data_dictionary.json", {
            "ai_label": AI_LABEL, "all_observations_and_outcomes_are_synthetic": True,
            "minute_fields": "Relative to episode_index.csv start_utc. Performance rows describe completed 5-minute intervals.",
            "source_shapes": "Normalized source-inspired tables, not verified native RFM/HiPer/Clarify wire schemas.",
            "resource_mapping": "Alias-only demo-neighborhood associations; no private crosswalk required.",
            "features": list(FEATURE_NAMES),
            "feature_windows": "target is label-only; episode/service/split/status fields are not model features.",
            "outcomes": "Future simulator confirmation times; kept separate from as-of-time observation features.",
            "unavailable_feeds": "NaN optional features plus explicit availability flags; not zero alarms/maintenance.",
            "model_score": "Uncalibrated simulation-trained classifier output; never a production outage probability.",
            "explanations": "heuristic_components explain only the heuristic, not Random Forest attribution.",
            "replay": "Separate held-out scripted episode, not used for fitting or threshold selection.",
        })
        verify_inventory()
        save_json(stage / "manifest.json", {
            "ai_label": AI_LABEL, "seed": seed, "episodes": settings.episodes,
            "contract_sha256": sha256(contract_path),
            "neighborhood_manifest_sha256": sha256(NEIGHBORHOOD / "manifest.json"),
            "bundled_alias_inventory_unchanged": True,
            "code_sha256": {
                path.relative_to(PROJECT).as_posix(): sha256(path)
                for path in sorted((PROJECT / "impact_predictor").glob("*.py"))
            },
            "dependency_versions": {
                name: importlib.metadata.version(name)
                for name in ("numpy", "scikit-learn", "scipy", "joblib", "threadpoolctl")
            },
            "artifacts": {
                path.relative_to(stage).as_posix(): sha256(path)
                for path in sorted(stage.rglob("*")) if path.is_file()
            },
            "model_loading_policy": "Only load this locally generated model after checking its manifest hash. Joblib is unsafe for untrusted artifacts.",
        })
        if output.exists():
            raise FileExistsError("Run output appeared during execution")
        stage.rename(output)
    print(json.dumps({
        "output_directory": str(output), "data_domain": "synthetic_only",
        "test": evaluation["test"], "demo": replay,
    }, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Synthetic-only Customer Impact Predictor")
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    run(args.run_name, args.seed)


if __name__ == "__main__":
    main()
