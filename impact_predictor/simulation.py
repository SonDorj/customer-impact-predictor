"""Original resource-condition simulation; no live-source calls."""

import csv
from dataclasses import dataclass, fields
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import random


@dataclass(frozen=True)
class ObservationSettings:
    latency_noise_sd_ms: float
    packet_loss_noise_sd_pct: float
    independent_performance_dropout: float
    performance_delay_minutes_and_probabilities: list[list[float]]


@dataclass(frozen=True)
class Settings:
    step_minutes: int
    history_intervals: int
    minimum_valid_intervals: int
    freshness_minutes: int
    horizon_intervals: int
    latency_threshold_ms: float
    packet_loss_threshold_pct: float
    confirmation_intervals: int
    episodes: int
    episode_intervals: int
    observation_defaults: ObservationSettings

    @classmethod
    def load(cls, path: Path):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data["status"] != "approved_for_simulator_and_training_only":
            raise ValueError("An approved simulation contract is required")
        parameters = {field.name: data[field.name] for field in fields(cls)}
        parameters["observation_defaults"] = ObservationSettings(
            **parameters["observation_defaults"]
        )
        result = cls(**parameters)
        if result.confirmation_intervals != 2 or result.step_minutes != 5:
            raise ValueError("This POC implements two consecutive five-minute intervals")
        if not 1 <= result.minimum_valid_intervals <= result.history_intervals:
            raise ValueError("Invalid history coverage requirement")
        probabilities = result.observation_defaults.performance_delay_minutes_and_probabilities
        if (not probabilities or any(delay < 0 or weight < 0 for delay, weight in probabilities)
                or abs(sum(weight for _, weight in probabilities) - 1) > 1e-9):
            raise ValueError("Performance-delay probabilities must sum to one")
        if not 0 <= result.observation_defaults.independent_performance_dropout < 1:
            raise ValueError("Invalid performance dropout rate")
        return result


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


@dataclass(frozen=True)
class Topology:
    service_resources: dict[str, frozenset[str]]
    customers: dict[str, str]
    primary_resource: str
    secondary_resource: str
    missing_service: str

    @classmethod
    def load(cls, directory: Path):
        services = read_csv(directory / "demo_services.csv")
        relationships = read_csv(directory / "resource_service_map.csv")
        summary = json.loads((directory / "neighborhood_summary.json").read_text())
        resources = {
            service["service_id"]: frozenset(
                row["resource_id"] for row in relationships
                if row["service_id"] == service["service_id"]
            )
            for service in services
        }
        if not resources or any(not value for value in resources.values()):
            raise ValueError("Every service needs inventory resource relationships")
        return cls(
            resources, {row["service_id"]: row["customer_id"] for row in services},
            summary["primary_event_resource"], summary["secondary_event_resource"],
            summary["insufficient_evidence_service"],
        )


@dataclass(frozen=True)
class Performance:
    resource_id: str
    event_minute: int
    observed_minute: int
    latency_ms: float | None
    packet_delivery_pct: float | None
    jitter_ms: float | None


@dataclass(frozen=True)
class Alarm:
    resource_id: str
    event_minute: int
    observed_minute: int
    severity: int
    action: str


@dataclass(frozen=True)
class Maintenance:
    resource_id: str
    start_minute: int
    end_minute: int
    known_minute: int
    observed_minute: int


@dataclass(frozen=True)
class FeedStatus:
    event_minute: int
    observed_minute: int
    alarm_feed_available: bool
    maintenance_feed_available: bool


@dataclass
class Episode:
    episode_id: str
    scenario: str
    start_utc: str
    performance: list[Performance]
    alarms: list[Alarm]
    maintenance: list[Maintenance]
    feed_status: list[FeedStatus]
    confirmed_degradation: dict[str, list[bool]]


SCENARIOS = (
    "healthy_variation", "gradual_deterioration", "intermittent_fault",
    "planned_maintenance_expected_events",
    "unexpected_deterioration_during_maintenance", "missing_or_stale_evidence",
)


def confirmed_states(raw_bad):
    return [index > 0 and bool(value and raw_bad[index - 1])
            for index, value in enumerate(raw_bad)]


def new_onsets(confirmed, step_minutes=5):
    return [(index + 1) * step_minutes for index, state in enumerate(confirmed)
            if state and (index == 0 or not confirmed[index - 1])]


def future_label(confirmed, index, horizon_intervals):
    if index + horizon_intervals >= len(confirmed):
        raise ValueError("Right-censored label window")
    return int(any(
        confirmed[future] and not confirmed[future - 1]
        for future in range(index + 1, index + horizon_intervals + 1)
    ))


def condition_profile(index, start, amplitude, ramp, hold=6):
    elapsed = index - start
    if elapsed < 0:
        return 0.0
    if elapsed < ramp:
        return amplitude * (elapsed + 1) / ramp
    if elapsed < ramp + hold:
        return amplitude
    return amplitude * max(0.0, 1 - (elapsed - ramp - hold + 1) / 8)


def simulate_episode(topology, settings, number, seed, demo=False):
    rng = random.Random(seed + number * 1009)
    observation = settings.observation_defaults
    delays, weights = zip(*observation.performance_delay_minutes_and_probabilities, strict=True)
    resource_ids = sorted(set().union(*topology.service_resources.values()))
    scenario = "scripted_demo" if demo else SCENARIOS[number % len(SCENARIOS)]
    start = 25 if demo else rng.randint(16, 36)
    target = topology.primary_resource if demo else rng.choice(resource_ids)
    amplitude = 1.65 if demo else rng.uniform(0.65, 1.95)
    ramp = 10 if demo else rng.randint(5, 14)
    missing_resources = frozenset()
    if demo:
        missing_resources = topology.service_resources[topology.missing_service]
    elif scenario == "missing_or_stale_evidence":
        missing_resources = topology.service_resources[
            rng.choice(sorted(topology.service_resources))
        ]
    base_latency = {resource: rng.uniform(8, 24) for resource in resource_ids}
    latent = dict.fromkeys(resource_ids, 0.0)
    alarm_state = dict.fromkeys(resource_ids, 0)
    performance, alarms, maintenance, feed_status = [], [], [], []
    raw_bad = {service: [] for service in topology.service_resources}
    if scenario in {
        "planned_maintenance_expected_events",
        "unexpected_deterioration_during_maintenance",
    }:
        planned_start = (start - 2) * settings.step_minutes
        known = max(0, planned_start - 60)
        maintenance.append(Maintenance(
            target, planned_start, (start + ramp + 12) * settings.step_minutes,
            known, known + rng.choice((0, 0, 5)),
        ))

    for index in range(settings.episode_intervals):
        minute = (index + 1) * settings.step_minutes
        actual = {}
        feed_status.append(FeedStatus(
            minute, minute, rng.random() >= 0.025, rng.random() >= 0.015
        ))
        for resource in resource_ids:
            desired = 0.0
            if resource == target:
                if demo or scenario in {
                    "gradual_deterioration", "unexpected_deterioration_during_maintenance",
                    "missing_or_stale_evidence",
                }:
                    desired = condition_profile(index, start, amplitude, ramp)
                elif scenario == "planned_maintenance_expected_events":
                    desired = condition_profile(index, start, rng.uniform(0.3, 0.65), ramp)
                elif scenario == "intermittent_fault" and start <= index < start + 18:
                    desired = rng.uniform(1.0, 2.4) if (index - start) % 4 < 2 else 0
            if demo and resource == topology.secondary_resource:
                desired = condition_profile(index, 23, 0.72, 12, hold=14)
            persistence = 0.35 if scenario == "intermittent_fault" else 0.65
            latent[resource] = max(
                0, persistence * latent[resource] + (1 - persistence) * desired
                + rng.gauss(0, 0.035)
            )
            stress = latent[resource]
            latency = base_latency[resource] + stress * 75
            loss = min(100, 0.02 + max(0, stress - 0.35) * 1.1)
            actual[resource] = (latency, loss)
            severity = 3 if stress > 1.05 else 2 if stress > 0.65 else 0
            if severity == 0 and rng.random() < 0.003:
                severity = rng.choice((1, 2))
            if severity != alarm_state[resource]:
                alarms.append(Alarm(
                    resource, minute, minute + rng.choice((0, 0, 5, 10)),
                    severity, "CLEAR" if severity == 0 else "RAISE",
                ))
                alarm_state[resource] = severity
            if (resource in missing_resources
                    or rng.random() < observation.independent_performance_dropout):
                continue
            delay = int(rng.choices(delays, weights, k=1)[0])
            performance.append(Performance(
                resource, minute, minute + delay,
                max(0, latency + rng.gauss(0, observation.latency_noise_sd_ms)),
                100 - min(100, max(0, loss + rng.gauss(
                    0, observation.packet_loss_noise_sd_pct
                ))),
                max(0, 1 + stress * 4 + rng.gauss(0, 0.25)),
            ))
        for service, resources in topology.service_resources.items():
            raw_bad[service].append(any(
                actual[resource][0] >= settings.latency_threshold_ms
                or actual[resource][1] >= settings.packet_loss_threshold_pct
                for resource in resources
            ))
    epoch = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(hours=8 * number)
    return Episode(
        "DEMO-001" if demo else f"EP-{number:04d}", scenario,
        epoch.isoformat(), performance, alarms, maintenance, feed_status,
        {service: confirmed_states(values) for service, values in raw_bad.items()},
    )
