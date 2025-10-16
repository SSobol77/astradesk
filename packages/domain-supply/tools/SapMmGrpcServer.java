// SPDX-License-Identifier: Apache-2.0
// File: packages/domain-supply/tools/SapMmGrpcServer.java
// Project: AstraDesk Domain Supply Pack
// Description:
//     gRPC server for SAP MM adapter, integrating with Admin API.
//     Uses Java 25, gRPC-Netty, and calls API for probe/create.
//     Production-ready with virtual threads, logging, and shutdown hook.

// Author: Siergej Sobolewski
// Since: 2025-10-16

import io.grpc.Server;
import io.grpc.ServerBuilder;
import io.grpc.stub.StreamObserver;
import astradesk.supply.grpc.SupplyServiceGrpc;
import astradesk.supply.grpc.FetchInventoryRequest;
import astradesk.supply.grpc.FetchInventoryResponse;
import astradesk.supply.grpc.InventoryItem;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.List;
import java.util.Map;

public class SapMmGrpcServer {
    private static final Logger LOGGER = LoggerFactory.getLogger(SapMmGrpcServer.class);
    private Server server;
    private final SapMmAdapter apiAdapter;  # Adapted from previous SAP MM adapter

    public SapMmGrpcServer(String apiUrl, String token) {
        this.apiAdapter = new SapMmAdapter(apiUrl, token);
    }

    private void start() throws IOException {
        server = ServerBuilder.forPort(50051)
                .addService(new SupplyServiceImpl())
                .executor(Executors.newVirtualThreadPerTaskExecutor())  // Java 25 virtual threads
                .build()
                .start();
        LOGGER.info("gRPC server started on port 50051");

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            LOGGER.warn("Shutting down gRPC server");
            SapMmGrpcServer.this.stop();
            LOGGER.info("Server shut down");
        }));
    }

    private void stop() {
        if (server != null) {
            server.shutdown();
        }
    }

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

            // Call Admin API via adapter (production integration)
            Map<String, Object> connectorData = Map.of("name", "sap_mm", "type", "sap", "config", Map.of("system", "SAP_MM"));
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
                                    .setStock((Integer) item.getOrDefault("stock", 0))
                                    .build();
                            builder.addItems(inventoryItem);
                        }
                        responseObserver.onNext(builder.build());
                        responseObserver.onCompleted();
                    })
                    .exceptionally(ex -> {
                        LOGGER.error("Error fetching inventory: {}", ex.getMessage());
                        responseObserver.onError(ex);
                        return null;
                    });
        }
    }

    public static void main(String[] args) throws IOException, InterruptedException {
        String apiUrl = System.getenv("API_URL") != null ? System.getenv("API_URL") : "http://localhost:8080/api/admin/v1";
        String token = System.getenv("API_TOKEN") != null ? System.getenv("API_TOKEN") : "";
        SapMmGrpcServer server = new SapMmGrpcServer(apiUrl, token);
        server.start();
        server.blockUntilShutdown();
    }
}
