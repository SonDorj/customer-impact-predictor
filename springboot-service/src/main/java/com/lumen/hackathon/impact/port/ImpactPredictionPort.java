package com.lumen.hackathon.impact.port;

import com.lumen.hackathon.impact.model.ImpactContracts.*;

public interface ImpactPredictionPort {
    PredictionResponse predict(PredictionRequest request);
    PredictionResponse demo(int minute);
    ModelInfo model();
    Inventory inventory();
    BackendHealth health();
}
