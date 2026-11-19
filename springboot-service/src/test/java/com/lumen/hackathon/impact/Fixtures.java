package com.lumen.hackathon.impact;

import com.lumen.hackathon.impact.model.ImpactContracts;
import com.lumen.hackathon.impact.model.ImpactContracts.*;

import java.util.List;

public final class Fixtures {
    private Fixtures() {}

    public static PredictionResponse abstention() {
        return new PredictionResponse(
                ImpactContracts.AI_LABEL, "synthetic_only", "provided_synthetic_observations",
                "run-001", 150, 30,
                List.of(new ServiceRisk(
                        "EVC-12", "Org-I", Status.INSUFFICIENT_EVIDENCE,
                        "Required current telemetry is unavailable",
                        RiskBand.INSUFFICIENT_EVIDENCE, null, null, null, null)),
                List.of(new CustomerRisk(
                        "Org-I", Status.INSUFFICIENT_EVIDENCE, null, 0, 1, 0)),
                List.of("Synthetic-only prediction; not a production outage probability."));
    }
}
