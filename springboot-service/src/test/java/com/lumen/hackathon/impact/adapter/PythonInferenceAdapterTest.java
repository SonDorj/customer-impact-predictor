package com.lumen.hackathon.impact.adapter;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.lumen.hackathon.impact.Fixtures;
import com.lumen.hackathon.impact.model.ImpactContracts.*;
import jakarta.validation.Validation;
import jakarta.validation.ValidatorFactory;
import org.junit.jupiter.api.*;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;

import java.net.ConnectException;
import java.net.SocketTimeoutException;

import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.*;

class PythonInferenceAdapterTest {
    private MockRestServiceServer server;
    private PythonInferenceAdapter adapter;
    private ValidatorFactory validation;

    @BeforeEach
    void setUp() {
        var builder = RestClient.builder().baseUrl("http://inference.invalid");
        server = MockRestServiceServer.bindTo(builder).build();
        validation = Validation.buildDefaultValidatorFactory();
        adapter = new PythonInferenceAdapter(builder.build(), validation.getValidator());
    }

    @AfterEach
    void close() {
        server.verify();
        validation.close();
    }

    @Test
    void decodesTypedAbstentionWithoutInventingConfidence() throws Exception {
        server.expect(requestTo("http://inference.invalid/v1/demo/predictions?minute=150"))
                .andRespond(withSuccess(
                        new ObjectMapper().writeValueAsString(Fixtures.abstention()),
                        MediaType.APPLICATION_JSON));
        var result = adapter.demo(150);
        assertEquals(Status.INSUFFICIENT_EVIDENCE, result.services().getFirst().status());
        assertNull(result.services().getFirst().uncalibratedModelScore());
    }

    @Test
    void rejectsSuccessShapedButIncompleteBackendPayload() {
        server.expect(requestTo("http://inference.invalid/v1/demo/predictions?minute=150"))
                .andRespond(withSuccess("{\"dataDomain\":\"synthetic_only\"}", MediaType.APPLICATION_JSON));
        assertEquals(HttpStatus.BAD_GATEWAY,
                assertThrows(InferenceException.class, () -> adapter.demo(150)).status());
    }

    @Test
    void mapsConnectionFailureToUnavailable() {
        server.expect(requestTo("http://inference.invalid/v1/demo/predictions?minute=150"))
                .andRespond(request -> {
                    throw new ResourceAccessException("offline", new ConnectException());
                });
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE,
                assertThrows(InferenceException.class, () -> adapter.demo(150)).status());
    }

    @Test
    void mapsTimeoutToGatewayTimeout() {
        server.expect(requestTo("http://inference.invalid/v1/demo/predictions?minute=150"))
                .andRespond(request -> {
                    throw new ResourceAccessException("timeout", new SocketTimeoutException());
                });
        assertEquals(HttpStatus.GATEWAY_TIMEOUT,
                assertThrows(InferenceException.class, () -> adapter.demo(150)).status());
    }

    @Test
    void mapsBackendValidationFailureToBadRequest() {
        server.expect(requestTo("http://inference.invalid/v1/demo/predictions?minute=150"))
                .andRespond(withStatus(HttpStatus.UNPROCESSABLE_ENTITY));
        assertEquals(HttpStatus.BAD_REQUEST,
                assertThrows(InferenceException.class, () -> adapter.demo(150)).status());
    }

    @Test
    void inconsistentAbstentionWithNumericScoreFailsValidation() {
        var invalid = new ServiceRisk(
                "EVC-12", "Org-I", Status.INSUFFICIENT_EVIDENCE, "missing",
                RiskBand.INSUFFICIENT_EVIDENCE, 0.1, null, null, null);
        assertFalse(validation.getValidator().validate(invalid).isEmpty());
    }
}
