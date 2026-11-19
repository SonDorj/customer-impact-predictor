"""As-of-time features and explicit evidence gates; outcome data is not accepted."""

from dataclasses import dataclass
import math
import statistics


FEATURE_NAMES = (
    "latency_latest_ms", "latency_mean_ms", "latency_max_ms", "latency_std_ms",
    "latency_slope_per_interval_ms", "loss_latest_pct", "loss_mean_pct",
    "loss_max_pct", "loss_slope_per_interval_pct", "jitter_latest_ms",
    "recent_breach_count", "active_alarm_max_severity", "alarm_raises_last_30m",
    "alarm_feed_available", "maintenance_active", "maintenance_starting_next_30m",
    "maintenance_feed_available", "valid_history_fraction", "newest_service_age_minutes",
)


@dataclass(frozen=True)
class Assessment:
    status: str
    reason: str
    features: tuple[float, ...] | None


def valid_performance(row):
    values = (row.latency_ms, row.packet_delivery_pct, row.jitter_ms)
    return (
        all(value is not None and math.isfinite(value) for value in values)
        and row.latency_ms >= 0 and row.jitter_ms >= 0
        and 0 <= row.packet_delivery_pct <= 100
    )


def slope(points):
    if len(points) < 2:
        return 0.0
    mean_x = statistics.mean(point[0] for point in points)
    mean_y = statistics.mean(point[1] for point in points)
    denominator = sum((point[0] - mean_x) ** 2 for point in points)
    return sum((x - mean_x) * (y - mean_y) for x, y in points) / denominator


def extract_features(resources, minute, performance, alarms, maintenance, feed_status, settings):
    if not resources:
        return Assessment("insufficient_evidence", "No inventory resource relationships", None)
    history_start = minute - settings.history_intervals * settings.step_minutes
    received = {}
    for row in performance:
        if (row.resource_id in resources and history_start < row.event_minute <= minute
                and row.observed_minute <= minute):
            key = row.resource_id, row.event_minute
            previous = received.get(key)
            if previous is None or row.observed_minute > previous.observed_minute:
                received[key] = row
    samples = {}
    for event_minute in range(history_start + settings.step_minutes,
                              minute + 1, settings.step_minutes):
        observations = [received.get((resource, event_minute)) for resource in resources]
        if all(row is not None and valid_performance(row) for row in observations):
            samples[event_minute] = (
                max(row.latency_ms for row in observations),
                max(100 - row.packet_delivery_pct for row in observations),
                max(row.jitter_ms for row in observations),
            )
    if len(samples) < settings.minimum_valid_intervals:
        return Assessment(
            "insufficient_evidence",
            f"Only {len(samples)}/{settings.history_intervals} complete valid performance intervals",
            None,
        )
    newest = max(samples)
    if minute - newest > settings.freshness_minutes:
        return Assessment("insufficient_evidence", "Current performance is stale", None)

    def bad(sample):
        return (sample[0] >= settings.latency_threshold_ms
                or sample[1] >= settings.packet_loss_threshold_pct)

    if all(timestamp in samples and bad(samples[timestamp])
           for timestamp in (minute - settings.step_minutes, minute)):
        return Assessment("already_degraded", "Two observed consecutive bad intervals", None)
    available_feeds = [
        row for row in feed_status
        if row.event_minute <= minute and row.observed_minute <= minute
    ]
    latest_feed = max(available_feeds, key=lambda row: row.event_minute, default=None)
    feed_fresh = latest_feed is not None and (
        minute - latest_feed.event_minute <= settings.freshness_minutes
    )
    alarm_available = feed_fresh and latest_feed.alarm_feed_available
    maintenance_available = feed_fresh and latest_feed.maintenance_feed_available
    received_alarms = [
        row for row in alarms if row.resource_id in resources
        and row.event_minute <= minute and row.observed_minute <= minute
    ]
    active = {}
    for row in sorted(received_alarms, key=lambda row: (row.event_minute, row.observed_minute)):
        active[row.resource_id] = row.severity if row.action != "CLEAR" else 0
    known_schedules = [
        row for row in maintenance if row.resource_id in resources
        and row.known_minute <= minute and row.observed_minute <= minute
    ]
    latency = [sample[0] for sample in samples.values()]
    loss = [sample[1] for sample in samples.values()]
    values = (
        samples[newest][0], statistics.mean(latency), max(latency),
        statistics.pstdev(latency),
        slope([(timestamp / settings.step_minutes, sample[0])
               for timestamp, sample in samples.items()]),
        samples[newest][1], statistics.mean(loss), max(loss),
        slope([(timestamp / settings.step_minutes, sample[1])
               for timestamp, sample in samples.items()]),
        samples[newest][2], float(sum(bad(sample) for sample in samples.values())),
        float(max(active.values(), default=0)) if alarm_available else math.nan,
        float(sum(row.action == "RAISE" and row.event_minute > history_start
                  for row in received_alarms)) if alarm_available else math.nan,
        float(bool(alarm_available)),
        float(any(row.start_minute <= minute < row.end_minute
                  for row in known_schedules)) if maintenance_available else math.nan,
        float(any(minute < row.start_minute <= minute + settings.step_minutes
                  * settings.horizon_intervals for row in known_schedules))
        if maintenance_available else math.nan,
        float(bool(maintenance_available)),
        len(samples) / settings.history_intervals, float(minute - newest),
    )
    return Assessment("assessed", "Fresh inventory-linked performance available", values)


def heuristic_score(features):
    value = dict(zip(FEATURE_NAMES, features, strict=True))
    components = {
        "telemetry_anomaly": 30 if (
            value["latency_latest_ms"] >= 80 or value["loss_latest_pct"] >= 0.7
        ) else 0,
        "sustained_deterioration": 20 if (
            value["latency_slope_per_interval_ms"] >= 3
            or value["loss_slope_per_interval_pct"] >= 0.06
        ) else 0,
        "relevant_active_alarm": 25 if value["active_alarm_max_severity"] >= 2 else 0,
        "recent_threshold_breach": 25 if value["recent_breach_count"] >= 1 else 0,
    }
    return sum(components.values()), components
