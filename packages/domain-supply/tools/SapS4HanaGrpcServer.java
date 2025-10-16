// SPDX-License-Identifier: Apache-2.0
// File: packages/domain-supply/tools/SapS4HanaGrpcServer.java
// Project: AstraDesk Domain Supply Pack
// Description:
//     gRPC server for SAP S/4HANA adapter, integrating with Admin API v1.2.0.
//     Uses Java 25 virtual threads, gRPC-Netty, and API /connectors for data.
//     Production-ready with logging, error handling, and shutdown hook.

// Author: Siergej Sobolewski
// Since: 2025-10-16

import io.grpc.Server;
import io.grpc.ServerBuilder;
import io.grpc.stub.StreamObserver;
import com.astradesk.supply.grpc.SupplyServiceGrpc;
import com.astradesk.supply.grpc.FetchInventoryRequest;
import com.astradesk.supply.grpc.FetchInventoryResponse;
import com.astradesk.supply.grpc.InventoryItem;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Executors;

public class SapS4HanaGrpcServer {
    private static final Logger LOGGER = LoggerFactory.getLogger(SapS4HanaGrpcServer.class);
    private Server server;
    private final SapS4HanaAdapter apiAdapter;

    public SapS4HanaGrpcServer(String apiUrl, String token) {
        this.apiAdapter = new SapS4HanaAdapter(apiUrl, token);
    }

    /**
     * Start gRPC server on port 50051.
     */
    private void start() throws IOException {
        server = ServerBuilder.forPort(50051)
                .addService(new SupplyServiceImpl())
                .executor(Executors.newVirtualThreadPerTaskExecutor()) // Java 25 virtual threads
                .build()
                .start();
        LOGGER.info("gRPC server started on port 50051");

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            LOGGER.warn("Shutting down gRPC server");
            SapS4HanaGrpcServer.this.stop();
            LOGGER.info("Server shut down");
        }));
    }

    /**
     * Stop gRPC server gracefully.
     */
    private void stop() {
        if (server != null) {
            server.shutdown();
        }
    }

    /**
     * Block until server terminates.
     */
    private void blockUntilShutdown() throws InterruptedException {
        if (server != null) {
            server.awaitTermination();
        }
    }

    class SupplyServiceImpl extends SupplyServiceGrpc.SupplyServiceImplBase {
        @Override
        public void fetchInventory(FetchInventoryRequest request, StreamObserver<FetchInventoryResponse> responseObserver) {
            String query = request.getQuery();
            LOGGER.info("Fetching inventory with query: {}", query);

            // Call Admin API via adapter
            Map<String, Object> connectorData = Map.of(
                "name", "sap_s4hana",
                "type", "sap",
                "config", Map.of("system", "S4HANA")
            );
            apiAdapter.createConnector(connectorData)
                    .thenCompose(id -> {
                        Map<String, Object> probeData = Map.of("query", query);
                        return apiAdapter.probeConnector(id, probeData);
                    })
                    .thenAccept(result -> {
                        FetchInventoryResponse.Builder builder = FetchInventoryResponse.newBuilder();
                        for (Map<String, Object> item : result) {
                            InventoryItem inventoryItem = InventoryItem.newBuilder()
                                    .setMaterial((String) item.getOrDefault("material", ""))
                                    .setStock(((Number) item.getOrDefault("stock", 0)).intValue())
                                    .build();
                            builder.addItems(inventoryItem);
                        }
                        responseObserver.onNext(builder.build());
                        responseObserver.onCompleted();
                    })
                    .exceptionally(ex -> {
                        LOGGER.error("Error fetching inventory: {}", ex.getMessage());
                        responseObserver.onError(new RuntimeException("Failed to fetch inventory: " + ex.getMessage()));
                        return null;
                    });
        }
    }

    public static void main(String[] args) throws IOException, InterruptedException {
        String apiUrl = System.getenv("API_URL") != null ? System.getenv("API_URL") : "http://localhost:8080/api/admin/v1";
        String token = System.getenv("API_TOKEN") != null ? System.getenv("API_TOKEN") : "";
        SapS4HanaGrpcServer server = new SapS4HanaGrpcServer(apiUrl, token);
        server.start();
        server.blockUntilShutdown();
    }
}
