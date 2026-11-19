"""Typed, camel-case HTTP contracts for synthetic-only inference."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid",
        allow_inf_nan=False, strict=True,
    )


ResourceId = Annotated[str, Field(pattern=r"^R-\d{2}$")]
ServiceId = Annotated[str, Field(pattern=r"^EVC-\d{2}$")]
Minute = Annotated[int, Field(ge=0, le=1440, strict=True)]
PredictionMinute = Annotated[int, Field(ge=0, le=360, multiple_of=5, strict=True)]
RiskBand = Literal["Low", "Watch", "Elevated", "High", "Insufficient evidence"]
Status = Literal["assessed", "insufficient_evidence", "already_degraded"]


class PerformanceInput(ApiModel):
    resource_id: ResourceId
    event_minute: Minute
    observed_minute: Minute
    latency_ms: float | None = Field(default=None, ge=0)
    packet_delivery_pct: float | None = Field(default=None, ge=0, le=100)
    jitter_ms: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def valid_times(self):
        if self.observed_minute < self.event_minute:
            raise ValueError("Observation cannot precede its performance interval")
        return self


class AlarmInput(ApiModel):
    resource_id: ResourceId
    event_minute: Minute
    observed_minute: Minute
    severity: int = Field(ge=0, le=3, strict=True)
    action: Literal["RAISE", "CLEAR"]

    @model_validator(mode="after")
    def valid_event(self):
        if self.observed_minute < self.event_minute:
            raise ValueError("Observation cannot precede the alarm")
        if (self.action == "CLEAR") != (self.severity == 0):
            raise ValueError("CLEAR needs severity zero; RAISE needs positive severity")
        return self


class MaintenanceInput(ApiModel):
    resource_id: ResourceId
    start_minute: Minute
    end_minute: Minute
    known_minute: Minute
    observed_minute: Minute

    @model_validator(mode="after")
    def valid_schedule(self):
        if self.end_minute <= self.start_minute or self.observed_minute < self.known_minute:
            raise ValueError("Invalid maintenance schedule or publication time")
        return self


class FeedStatusInput(ApiModel):
    event_minute: Minute
    observed_minute: Minute
    alarm_feed_available: bool = Field(strict=True)
    maintenance_feed_available: bool = Field(strict=True)

    @model_validator(mode="after")
    def valid_times(self):
        if self.observed_minute < self.event_minute:
            raise ValueError("Feed status observation precedes its event")
        return self


class PredictionRequest(ApiModel):
    prediction_minute: PredictionMinute
    service_ids: list[ServiceId] | None = Field(default=None, min_length=1, max_length=12)
    performance: list[PerformanceInput] = Field(default_factory=list, max_length=5000)
    alarms: list[AlarmInput] = Field(default_factory=list, max_length=2000)
    maintenance: list[MaintenanceInput] = Field(default_factory=list, max_length=500)
    feed_status: list[FeedStatusInput] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def unique_records(self):
        if self.service_ids is not None and len(set(self.service_ids)) != len(self.service_ids):
            raise ValueError("Duplicate service aliases")
        for records in (self.performance, self.alarms):
            keys = [(row.resource_id, row.event_minute, row.observed_minute) for row in records]
            if len(set(keys)) != len(keys):
                raise ValueError("Duplicate resource observation keys")
        keys = [row.event_minute for row in self.feed_status]
        if len(set(keys)) != len(keys):
            raise ValueError("Duplicate feed-status intervals")
        return self


class HeuristicComponents(ApiModel):
    telemetry_anomaly: int
    sustained_deterioration: int
    relevant_active_alarm: int
    recent_threshold_breach: int


class Evidence(ApiModel):
    latest_latency_ms: float
    latest_packet_loss_pct: float
    valid_history_fraction: float
    alarm_feed_available: bool
    maintenance_feed_available: bool
    active_alarm_max_severity: float | None
    maintenance_active: bool | None


class ServiceRisk(ApiModel):
    service_id: str
    customer_id: str
    status: Status
    reason: str
    risk_band: RiskBand | None
    uncalibrated_model_score: float | None
    heuristic_score: int | None
    heuristic_components: HeuristicComponents | None
    evidence: Evidence | None


class CustomerRisk(ApiModel):
    customer_id: str
    status: Status
    risk_band_among_assessed_services: RiskBand | None
    assessed_services: int
    insufficient_evidence_services: int
    already_degraded_services: int


class PredictionResponse(ApiModel):
    ai_label: str
    data_domain: Literal["synthetic_only"]
    source: Literal["provided_synthetic_observations", "synthetic_replay"]
    model_id: str
    prediction_minute: int
    forecast_horizon_minutes: int
    services: list[ServiceRisk]
    customers: list[CustomerRisk]
    warnings: list[str]
