package com.lumen.hackathon.impact.web;

import com.lumen.hackathon.impact.Fixtures;
import com.lumen.hackathon.impact.adapter.InferenceException;
import com.lumen.hackathon.impact.port.ImpactPredictionPort;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import static org.hamcrest.Matchers.nullValue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(ImpactController.class)
class ImpactControllerTest {
    @Autowired MockMvc mvc;
    @MockitoBean ImpactPredictionPort predictor;

    @Test
    void preservesExplicitAbstentionAndNullScore() throws Exception {
        when(predictor.predict(any())).thenReturn(Fixtures.abstention());
        mvc.perform(post("/api/v1/impact/predictions").contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"predictionMinute":150,"serviceIds":["EVC-12"]}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.dataDomain").value("synthetic_only"))
                .andExpect(jsonPath("$.services[0].status").value("insufficient_evidence"))
                .andExpect(jsonPath("$.services[0].riskBand").value("Insufficient evidence"))
                .andExpect(jsonPath("$.services[0].uncalibratedModelScore").value(nullValue()));
    }

    @ParameterizedTest
    @ValueSource(strings = {
            "{}", "{\"predictionMinute\":151}", "{\"predictionMinute\":-5}",
            "{\"predictionMinute\":150,\"serviceIds\":[]}",
            "{\"predictionMinute\":150,\"target\":1}",
            "{\"predictionMinute\":150,\"serviceIds\":[\"raw-circuit\"]}"
    })
    void rejectsInvalidInputBeforeInvokingModel(String json) throws Exception {
        mvc.perform(post("/api/v1/impact/predictions")
                        .contentType(MediaType.APPLICATION_JSON).content(json))
                .andExpect(status().isBadRequest());
        verifyNoInteractions(predictor);
    }

    @Test
    void backendFailureIsNotReportedAsLowRisk() throws Exception {
        when(predictor.demo(150)).thenThrow(
                new InferenceException(HttpStatus.SERVICE_UNAVAILABLE, "Inference backend is unavailable"));
        mvc.perform(get("/api/v1/demo/predictions?minute=150"))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.detail").value("Inference backend is unavailable"))
                .andExpect(jsonPath("$.services").doesNotExist());
    }
}
