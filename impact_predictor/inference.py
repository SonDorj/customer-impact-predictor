"""Local batch inference only; not a web service."""

import math

from .features import FEATURE_NAMES, heuristic_score


def risk_band(score, thresholds):
    if score >= thresholds["High"]:
        return "High"
    if score >= thresholds["Elevated"]:
        return "Elevated"
    if score >= thresholds["Watch"]:
        return "Watch"
    return "Low"


def predict_assessment(bundle, assessment):
    result = {
        "status": assessment.status, "reason": assessment.reason,
        "risk_band": None, "uncalibrated_model_score": None,
        "heuristic_score": None, "heuristic_components": None, "evidence": None,
    }
    if assessment.status != "assessed":
        if assessment.status == "insufficient_evidence":
            result["risk_band"] = "Insufficient evidence"
        return result
    score = float(bundle["model"].predict_proba([assessment.features])[0, 1])
    heuristic, components = heuristic_score(assessment.features)
    values = dict(zip(FEATURE_NAMES, assessment.features, strict=True))
    result.update({
        "risk_band": risk_band(score, bundle["band_thresholds"]),
        "uncalibrated_model_score": score, "heuristic_score": heuristic,
        "heuristic_components": components,
        "evidence": {
            "latest_latency_ms": values["latency_latest_ms"],
            "latest_packet_loss_pct": values["loss_latest_pct"],
            "valid_history_fraction": values["valid_history_fraction"],
            "alarm_feed_available": bool(values["alarm_feed_available"]),
            "maintenance_feed_available": bool(values["maintenance_feed_available"]),
            "active_alarm_max_severity": (
                None if math.isnan(values["active_alarm_max_severity"])
                else values["active_alarm_max_severity"]
            ),
            "maintenance_active": (
                None if math.isnan(values["maintenance_active"])
                else bool(values["maintenance_active"])
            ),
        },
    })
    return result
