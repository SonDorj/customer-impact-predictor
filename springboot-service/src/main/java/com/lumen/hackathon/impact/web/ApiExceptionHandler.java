package com.lumen.hackathon.impact.web;

import com.lumen.hackathon.impact.adapter.InferenceException;
import com.lumen.hackathon.impact.model.ImpactContracts;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class ApiExceptionHandler {
    @ExceptionHandler(InferenceException.class)
    public ProblemDetail inferenceFailure(InferenceException error) {
        return problem(error.status(), error.getMessage());
    }

    @ExceptionHandler({MethodArgumentNotValidException.class, HttpMessageNotReadableException.class})
    public ProblemDetail invalidRequest(Exception error) {
        return problem(HttpStatus.BAD_REQUEST, "Request violates the prediction schema");
    }

    private ProblemDetail problem(HttpStatus status, String detail) {
        var response = ProblemDetail.forStatusAndDetail(status, detail);
        response.setProperty("aiLabel", ImpactContracts.AI_LABEL);
        return response;
    }
}
