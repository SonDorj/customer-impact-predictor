package com.lumen.hackathon.impact.adapter;

import com.lumen.hackathon.impact.model.ImpactContracts.*;
import com.lumen.hackathon.impact.port.ImpactPredictionPort;
import jakarta.validation.Validator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.*;

import java.net.SocketTimeoutException;
import java.net.http.HttpTimeoutException;
import java.util.function.Supplier;

@Component
public class PythonInferenceAdapter implements ImpactPredictionPort {
    private static final Logger LOG = LoggerFactory.getLogger(PythonInferenceAdapter.class);
    private final RestClient client;
    private final Validator validator;

    public PythonInferenceAdapter(RestClient inferenceRestClient, Validator validator) {
        this.client = inferenceRestClient;
        this.validator = validator;
    }

    @Override
    public PredictionResponse predict(PredictionRequest request) {
        return invoke(() -> client.post().uri("/v1/predictions")
                .contentType(MediaType.APPLICATION_JSON).body(request)
                .retrieve().body(PredictionResponse.class));
    }

    @Override
    public PredictionResponse demo(int minute) {
        return invoke(() -> client.get().uri("/v1/demo/predictions?minute={minute}", minute)
                .retrieve().body(PredictionResponse.class));
    }

    @Override
    public ModelInfo model() {
        return invoke(() -> client.get().uri("/v1/model").retrieve().body(ModelInfo.class));
    }

    @Override
    public Inventory inventory() {
        return invoke(() -> client.get().uri("/v1/inventory").retrieve().body(Inventory.class));
    }

    @Override
    public BackendHealth health() {
        return invoke(() -> client.get().uri("/health").retrieve().body(BackendHealth.class));
    }

    private <T> T invoke(Supplier<T> operation) {
        try {
            T response = operation.get();
            if (response == null || !validator.validate(response).isEmpty()) {
                throw failure(HttpStatus.BAD_GATEWAY, "Inference backend returned an invalid response");
            }
            return response;
        } catch (RestClientResponseException error) {
            if (error.getStatusCode().value() == 404) {
                throw failure(HttpStatus.NOT_FOUND, "Requested service alias was not found");
            }
            if (error.getStatusCode().value() == 422 || error.getStatusCode().value() == 400) {
                throw failure(HttpStatus.BAD_REQUEST, "Observation data violates the inference contract");
            }
            throw failure(HttpStatus.BAD_GATEWAY, "Inference backend rejected the operation");
        } catch (ResourceAccessException error) {
            if (error.contains(HttpTimeoutException.class) || error.contains(SocketTimeoutException.class)) {
                throw failure(HttpStatus.GATEWAY_TIMEOUT, "Inference backend timed out");
            }
            throw failure(HttpStatus.SERVICE_UNAVAILABLE, "Inference backend is unavailable");
        } catch (RestClientException error) {
            throw failure(HttpStatus.BAD_GATEWAY, "Inference response could not be decoded");
        }
    }

    private InferenceException failure(HttpStatus status, String message) {
        LOG.warn("Inference operation failed: HTTP {} - {}", status.value(), message);
        return new InferenceException(status, message);
    }
}
