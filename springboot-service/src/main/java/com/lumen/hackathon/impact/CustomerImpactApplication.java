package com.lumen.hackathon.impact;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@SpringBootApplication
@ConfigurationPropertiesScan
public class CustomerImpactApplication {
    public static void main(String[] args) {
        SpringApplication.run(CustomerImpactApplication.class, args);
    }
}
