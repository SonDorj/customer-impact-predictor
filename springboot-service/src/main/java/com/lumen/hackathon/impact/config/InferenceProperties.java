package com.lumen.hackathon.impact.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.net.URI;
import java.time.Duration;
import java.util.Set;

@ConfigurationProperties("impact.inference")
public record InferenceProperties(URI baseUrl, Duration connectTimeout, Duration readTimeout) {
    public InferenceProperties {
        if (baseUrl == null || baseUrl.getHost() == null || baseUrl.getUserInfo() != null
                || !Set.of("http", "https").contains(baseUrl.getScheme())) {
            throw new IllegalArgumentException("Inference URL must be an HTTP(S) origin without credentials");
        }
        if (connectTimeout == null || connectTimeout.isNegative() || connectTimeout.isZero()
                || readTimeout == null || readTimeout.isNegative() || readTimeout.isZero()) {
            throw new IllegalArgumentException("Positive inference timeouts are required");
        }
    }
}
