package com.lumen.hackathon.impact.model;

import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;

import java.util.List;
import java.util.Map;

public final class ImpactContracts {
    public static final String AI_LABEL =
            "[AI-GENERATED CONTENT BY AIFEL TEAM ASSISTANT :: AIFEL-AI-LABEL-V1]";

    private ImpactContracts() {}

    public enum Status {
        @JsonProperty("assessed") ASSESSED,
        @JsonProperty("insufficient_evidence") INSUFFICIENT_EVIDENCE,
        @JsonProperty("already_degraded") ALREADY_DEGRADED
    }

    public enum RiskBand {
        @JsonProperty("Low") LOW,
        @JsonProperty("Watch") WATCH,
        @JsonProperty("Elevated") ELEVATED,
        @JsonProperty("High") HIGH,
        @JsonProperty("Insufficient evidence") INSUFFICIENT_EVIDENCE
    }

    public enum AlarmAction { RAISE, CLEAR }

    public record Performance(
            @NotBlank @Pattern(regexp = "R-\\d{2}") String resourceId,
            @NotNull @Min(0) @Max(1440) Integer eventMinute,
            @NotNull @Min(0) @Max(1440) Integer observedMinute,
            @DecimalMin("0") Double latencyMs,
            @DecimalMin("0") @DecimalMax("100") Double packetDeliveryPct,
            @DecimalMin("0") Double jitterMs) {}

    public record Alarm(
            @NotBlank @Pattern(regexp = "R-\\d{2}") String resourceId,
            @NotNull @Min(0) @Max(1440) Integer eventMinute,
            @NotNull @Min(0) @Max(1440) Integer observedMinute,
            @NotNull @Min(0) @Max(3) Integer severity,
            @NotNull AlarmAction action) {}

    public record Maintenance(
            @NotBlank @Pattern(regexp = "R-\\d{2}") String resourceId,
            @NotNull @Min(0) @Max(1440) Integer startMinute,
            @NotNull @Min(0) @Max(1440) Integer endMinute,
            @NotNull @Min(0) @Max(1440) Integer knownMinute,
            @NotNull @Min(0) @Max(1440) Integer observedMinute) {}

    public record FeedStatus(
            @NotNull @Min(0) @Max(1440) Integer eventMinute,
            @NotNull @Min(0) @Max(1440) Integer observedMinute,
            @NotNull Boolean alarmFeedAvailable,
            @NotNull Boolean maintenanceFeedAvailable) {}

    public record PredictionRequest(
            @NotNull @Min(0) @Max(360) Integer predictionMinute,
            @Size(min = 1, max = 12)
            List<@NotBlank @Pattern(regexp = "EVC-\\d{2}") String> serviceIds,
            @Size(max = 5000) List<@NotNull @Valid Performance> performance,
            @Size(max = 2000) List<@NotNull @Valid Alarm> alarms,
            @Size(max = 500) List<@NotNull @Valid Maintenance> maintenance,
            @Size(max = 500) List<@NotNull @Valid FeedStatus> feedStatus) {
        public PredictionRequest {
            performance = performance == null ? List.of() : List.copyOf(performance);
            alarms = alarms == null ? List.of() : List.copyOf(alarms);
            maintenance = maintenance == null ? List.of() : List.copyOf(maintenance);
            feedStatus = feedStatus == null ? List.of() : List.copyOf(feedStatus);
        }

        @AssertTrue(message = "Prediction minute must be aligned to five minutes")
        @JsonIgnore
        public boolean isMinuteAligned() {
            return predictionMinute == null || predictionMinute % 5 == 0;
        }
    }

    public record HeuristicComponents(
            @NotNull Integer telemetryAnomaly, @NotNull Integer sustainedDeterioration,
            @NotNull Integer relevantActiveAlarm, @NotNull Integer recentThresholdBreach) {}

    public record Evidence(
            @NotNull Double latestLatencyMs, @NotNull Double latestPacketLossPct,
            @NotNull @DecimalMin("0") @DecimalMax("1") Double validHistoryFraction,
            @NotNull Boolean alarmFeedAvailable, @NotNull Boolean maintenanceFeedAvailable,
            Double activeAlarmMaxSeverity, Boolean maintenanceActive) {}

    public record ServiceRisk(
            @NotBlank String serviceId, @NotBlank String customerId,
            @NotNull Status status, @NotBlank String reason, RiskBand riskBand,
            @DecimalMin("0") @DecimalMax("1") Double uncalibratedModelScore,
            @Min(0) @Max(100) Integer heuristicScore,
            @Valid HeuristicComponents heuristicComponents, @Valid Evidence evidence) {
        @AssertTrue(message = "Prediction contradicts its evidence status")
        @JsonIgnore
        public boolean isEvidenceConsistent() {
            if (status == Status.ASSESSED) {
                return riskBand != null && riskBand != RiskBand.INSUFFICIENT_EVIDENCE
                        && uncalibratedModelScore != null && heuristicScore != null
                        && heuristicComponents != null && evidence != null;
            }
            return uncalibratedModelScore == null && heuristicScore == null
                    && heuristicComponents == null && evidence == null
                    && (status == Status.INSUFFICIENT_EVIDENCE
                        ? riskBand == RiskBand.INSUFFICIENT_EVIDENCE : riskBand == null);
        }
    }

    public record CustomerRisk(
            @NotBlank String customerId, @NotNull Status status,
            RiskBand riskBandAmongAssessedServices,
            @NotNull @Min(0) Integer assessedServices,
            @NotNull @Min(0) Integer insufficientEvidenceServices,
            @NotNull @Min(0) Integer alreadyDegradedServices) {}

    public record PredictionResponse(
            @NotBlank String aiLabel, @NotBlank @Pattern(regexp = "synthetic_only") String dataDomain,
            @NotBlank @Pattern(regexp = "synthetic_replay|provided_synthetic_observations") String source,
            @NotBlank String modelId, @NotNull @Min(0) Integer predictionMinute,
            @NotNull @Min(1) Integer forecastHorizonMinutes,
            @NotEmpty List<@NotNull @Valid ServiceRisk> services,
            @NotEmpty List<@NotNull @Valid CustomerRisk> customers,
            @NotEmpty List<@NotBlank String> warnings) {}

    public record Metrics(
            @NotNull @DecimalMin("0") @DecimalMax("1") Double precision,
            @NotNull @DecimalMin("0") @DecimalMax("1") Double recall,
            @NotNull @DecimalMin("0") @DecimalMax("1") Double prAuc,
            @NotNull @DecimalMin("0") @DecimalMax("1") Double forecastCoverage,
            Double medianProactiveLeadMinutes) {}

    public record ModelInfo(
            @NotBlank String aiLabel, @NotBlank String modelId,
            @NotBlank @Pattern(regexp = "[a-f0-9]{64}") String modelSha256,
            @NotBlank @Pattern(regexp = "synthetic_only") String dataDomain,
            @NotNull @Min(1) Integer forecastHorizonMinutes, @NotEmpty List<String> featureNames,
            @NotEmpty Map<String, Double> bandThresholds,
            @NotNull @Valid Metrics testMetrics, @NotEmpty List<String> warnings) {}

    public record TopologyNode(@NotBlank String id, @NotBlank String type, String role) {}
    public record TopologyEdge(@NotBlank String from, @NotBlank String to, @NotBlank String relation) {}
    public record Inventory(
            @NotBlank String aiLabel, @Pattern(regexp = "synthetic_only") @NotBlank String dataDomain,
            @NotEmpty List<@Valid TopologyNode> nodes, @NotEmpty List<@Valid TopologyEdge> edges,
            @NotBlank String relationshipSemantics) {}

    public record BackendHealth(
            @NotBlank @Pattern(regexp = "ready") String status,
            @NotBlank String modelId, @NotBlank String modelSha256,
            @NotBlank @Pattern(regexp = "synthetic_only") String dataDomain) {}
}
