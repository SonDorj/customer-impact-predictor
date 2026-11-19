"""Episode-grouped fitting, baseline comparison and explicitly synthetic metrics."""

import csv
from dataclasses import dataclass
import statistics

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score, precision_recall_curve
from sklearn.pipeline import make_pipeline

from .features import FEATURE_NAMES, heuristic_score


@dataclass(frozen=True)
class Window:
    episode_number: int
    episode_id: str
    service_id: str
    minute: int


def episode_split(number, total):
    if total < 20:
        raise ValueError("At least 20 episodes are required for grouped evaluation")
    if not 0 <= number < total:
        raise ValueError("Episode index is outside the configured run")
    if number < int(total * 0.7):
        return "train"
    if number < int(total * 0.7) + int(total * 0.15):
        return "validation"
    return "test"


def load_assessed_windows(path):
    x, y, windows = [], [], []
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["status"] != "assessed":
                continue
            x.append([float(row[name]) for name in FEATURE_NAMES])
            y.append(int(row["target"]))
            windows.append(Window(
                int(row["episode_number"]), row["episode_id"], row["service_id"],
                int(row["prediction_minute"]),
            ))
    if not x:
        raise ValueError("No windows passed the evidence gate")
    return np.asarray(x, dtype=np.float32), np.asarray(y, dtype=np.int8), windows


def masks_for(windows, total):
    splits = np.array([episode_split(window.episode_number, total) for window in windows])
    return {name: splits == name for name in ("train", "validation", "test")}


def fit_model(x, y, train_mask, seed):
    if len(np.unique(y[train_mask])) != 2:
        raise ValueError("Training needs both future-impact and non-impact examples")
    model = make_pipeline(
        SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
        RandomForestClassifier(
            n_estimators=120, max_depth=10, min_samples_leaf=20,
            class_weight="balanced_subsample", max_samples=0.8,
            random_state=seed, n_jobs=2,
        ),
    )
    model.fit(x[train_mask], y[train_mask])
    return model


def select_alert_threshold(y, scores):
    if len(np.unique(y)) != 2:
        raise ValueError("Validation needs both classes; increase independent episodes")
    precision, recall, thresholds = precision_recall_curve(y, scores)
    f1 = np.divide(
        2 * precision[:-1] * recall[:-1], precision[:-1] + recall[:-1],
        out=np.zeros_like(thresholds, dtype=float),
        where=(precision[:-1] + recall[:-1]) > 0,
    )
    # Prefer the higher threshold when validation F1 ties.
    best = np.flatnonzero(np.isclose(f1, f1.max(), rtol=0, atol=1e-12))[-1]
    return float(thresholds[best])


def select_bands(validation_scores, high):
    below_high = np.unique(validation_scores[validation_scores < high])
    if len(below_high) < 3:
        raise ValueError("Validation scores do not support four distinct risk bands")
    watch, elevated = np.quantile(below_high, (0.5, 0.9))
    return {"Watch": float(watch), "Elevated": float(elevated), "High": float(high)}


def evaluate(y, scores, threshold, windows, outcomes, step_minutes=5, horizon_minutes=30):
    if len(np.unique(y)) != 2:
        raise ValueError("Evaluation needs both classes")
    predicted = scores >= threshold
    true_positive = int(np.sum(predicted & (y == 1)))
    false_positive = int(np.sum(predicted & (y == 0)))
    false_negative = int(np.sum(~predicted & (y == 1)))
    alerts = {}
    false_service_episodes = set()
    for window, alert, target in zip(windows, predicted, y, strict=True):
        if alert:
            alerts.setdefault((window.episode_id, window.service_id), []).append(window.minute)
            if not target:
                false_service_episodes.add((window.episode_id, window.service_id))
    confirmation_leads, proactive_leads = [], []
    for outcome in outcomes:
        key = outcome["episode_id"], outcome["service_id"]
        confirmation = outcome["confirmation_minute"]
        candidates = [
            minute for minute in alerts.get(key, [])
            if confirmation - horizon_minutes <= minute < confirmation
        ]
        if candidates:
            first = min(candidates)
            confirmation_leads.append(confirmation - first)
            lead_before_degradation = confirmation - 2 * step_minutes - first
            if lead_before_degradation > 0:
                proactive_leads.append(lead_before_degradation)
    return {
        "assessed_service_windows": len(y),
        "positive_windows": int(np.sum(y)),
        "positive_window_prevalence": float(np.mean(y)),
        "precision": true_positive / max(1, true_positive + false_positive),
        "recall": true_positive / max(1, true_positive + false_negative),
        "PR_AUC_average_precision": float(average_precision_score(y, scores)),
        "false_alert_windows": false_positive,
        "false_alert_windows_per_100_assessed": 100 * false_positive / len(y),
        "service_episodes_with_false_alerts": len(false_service_episodes),
        "eligible_service_degradation_events": len(outcomes),
        "events_warned_before_confirmation": len(confirmation_leads),
        "median_lead_to_confirmation_minutes": (
            statistics.median(confirmation_leads) if confirmation_leads else None
        ),
        "events_warned_before_first_bad_interval": len(proactive_leads),
        "median_proactive_lead_minutes": (
            statistics.median(proactive_leads) if proactive_leads else None
        ),
        "alert_threshold": threshold,
    }


def compare_models(x, y, windows, outcomes, total, seed, settings):
    masks = masks_for(windows, total)
    model = fit_model(x, y, masks["train"], seed)
    model_scores = model.predict_proba(x)[:, 1]
    baseline_scores = np.asarray([heuristic_score(row)[0] for row in x], dtype=float)
    validation = masks["validation"]
    model_threshold = select_alert_threshold(y[validation], model_scores[validation])
    baseline_threshold = select_alert_threshold(y[validation], baseline_scores[validation])
    bands = select_bands(model_scores[validation], model_threshold)
    evaluation = {}
    for split in ("validation", "test"):
        mask = masks[split]
        split_windows = [window for window, keep in zip(windows, mask, strict=True) if keep]
        split_outcomes = [
            outcome for outcome in outcomes
            if episode_split(outcome["episode_number"], total) == split
        ]
        evaluation[split] = {
            "random_forest": evaluate(
                y[mask], model_scores[mask], model_threshold, split_windows, split_outcomes,
                settings.step_minutes, settings.step_minutes * settings.horizon_intervals,
            ),
            "heuristic": evaluate(
                y[mask], baseline_scores[mask], baseline_threshold,
                split_windows, split_outcomes, settings.step_minutes,
                settings.step_minutes * settings.horizon_intervals,
            ),
        }
    return (
        {"model": model, "feature_names": FEATURE_NAMES, "band_thresholds": bands,
         "baseline_alert_threshold": baseline_threshold},
        evaluation, masks, model_scores, baseline_scores,
    )
