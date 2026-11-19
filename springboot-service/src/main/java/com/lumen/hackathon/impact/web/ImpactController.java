package com.lumen.hackathon.impact.web;

import com.lumen.hackathon.impact.model.ImpactContracts.*;
import com.lumen.hackathon.impact.port.ImpactPredictionPort;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/v1")
public class ImpactController {
    private final ImpactPredictionPort predictor;

    public ImpactController(ImpactPredictionPort predictor) {
        this.predictor = predictor;
    }

    @PostMapping("/impact/predictions")
    public PredictionResponse predict(@Valid @RequestBody PredictionRequest request) {
        return predictor.predict(request);
    }

    @GetMapping("/demo/predictions")
    public PredictionResponse demo(
            @RequestParam(defaultValue = "150") @Min(0) @Max(360) int minute) {
        if (minute % 5 != 0) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Minute must align to five minutes");
        }
        return predictor.demo(minute);
    }

    @GetMapping("/model")
    public ModelInfo model() {
        return predictor.model();
    }

    @GetMapping("/inventory")
    public Inventory inventory() {
        return predictor.inventory();
    }
}
