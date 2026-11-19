package com.lumen.hackathon.impact.adapter;

import com.lumen.hackathon.impact.port.ImpactPredictionPort;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.stereotype.Component;

@Component("inference")
public class InferenceHealthIndicator implements HealthIndicator {
    private final ImpactPredictionPort predictor;

    public InferenceHealthIndicator(ImpactPredictionPort predictor) {
        this.predictor = predictor;
    }

    @Override
    public Health health() {
        try {
            predictor.health();
            return Health.up().build();
        } catch (InferenceException error) {
            return Health.down().withDetail("reason", error.getMessage()).build();
        }
    }
}
