// SPDX-License-Identifier: Apache-2.0
// File: packages/domain-finance/tools/OracleErpAdapter.java
// Project: AstraDesk Domain Finance Pack
// Description:
//     Asynchronous Java client for Oracle ERP integration via Admin API v1.2.0.
//     Used by OracleErpGrpcServer, calls /connectors for data.
//     Production-ready with Java 25 virtual threads, retry, and logging.

// Author: Siergej Sobolewski
// Since: 2025-10-16

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;
import io.github.resilience4j.retry.Retry;
import io.github.resilience4j.retry.RetryConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executor;
import java.util.concurrent.Executors;

public class OracleErpAdapter {
    private static final Logger LOGGER = LoggerFactory.getLogger(OracleErpAdapter.class);
    private final HttpClient client;
    private final String apiUrl;
    private final String token;
    private final ObjectMapper mapper = new ObjectMapper();
    private final Retry retry;

    public OracleErpAdapter(String apiUrl, String token) {
        this.apiUrl = apiUrl;
        this.token = token;
        Executor executor = Executors.newVirtualThreadPerTaskExecutor();
        this.client = HttpClient.newBuilder()
                .executor(executor)
                .connectTimeout(Duration.ofSeconds(10))
                .build();
        RetryConfig config = RetryConfig.custom()
                .maxAttempts(3)
                .waitDuration(Duration.ofMillis(500))
                .build();
        this.retry = Retry.of("apiRetry", config);
    }

    public CompletableFuture<String> createConnector(Map<String, Object> connectorData) {
        return Retry.decorateCompletionStage(retry, () -> {
            String body;
            try {
                body = mapper.writeValueAsString(connectorData);
            } catch (Exception e) {
                throw new RuntimeException("Failed to serialize connector data", e);
            }
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(apiUrl + "/connectors"))
                    .header("Authorization", "Bearer " + token)
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(body))
                    .build();
            return client.sendAsync(request, HttpResponse.BodyHandlers.ofString())
                    .thenApply(resp -> {
                        if (resp.statusCode() != 201) {
                            throw new RuntimeException(parseProblemDetail(resp.body()));
                        }
                        return extractId(resp.body());
                    });
        }).toCompletableFuture();
    }

    public CompletableFuture<List<Map<String, Object>>> probeConnector(String connectorId, Map<String, Object> probeData) {
        return Retry.decorateCompletionStage(retry, () -> {
            String body;
            try {
                body = mapper.writeValueAsString(probeData);
            } catch (Exception e) {
                throw new RuntimeException("Failed to serialize probe data", e);
            }
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(apiUrl + "/connectors/" + connectorId + ":probe"))
                    .header("Authorization", "Bearer " + token)
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(body))
                    .build();
            return client.sendAsync(request, HttpResponse.BodyHandlers.ofString())
                    .thenApply(resp -> {
                        if (resp.statusCode() != 200) {
                            throw new RuntimeException(parseProblemDetail(resp.body()));
                        }
                        return parseResultList(resp.body());
                    });
        }).toCompletableFuture();
    }

    private String parseProblemDetail(String body) {
        try {
            JsonNode node = mapper.readTree(body);
            return "API Error: " + node.get("title").asText() + " - " + node.get("detail").asText();
        } catch (Exception e) {
            return "Unknown API error: " + body;
        }
    }

    private String extractId(String body) {
        try {
            JsonNode node = mapper.readTree(body);
            return node.get("id").asText();
        } catch (Exception e) {
            throw new RuntimeException("Failed to parse ID from response", e);
        }
    }

    private List<Map<String, Object>> parseResultList(String body) {
        try {
            JsonNode node = mapper.readTree(body);
            List<Map<String, Object>> result = new ArrayList<>();
            for (JsonNode item : node.get("result")) {
                result.add(mapper.convertValue(item, Map.class));
            }
            return result;
        } catch (Exception e) {
            throw new RuntimeException("Failed to parse result list", e);
        }
    }
}
