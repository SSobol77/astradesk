// SPDX-License-Identifier: Apache-2.0
// File: packages/domain-finance/tools/OracleErpGrpcServer.java
// Project: AstraDesk Domain Finance Pack
// Description:
//     gRPC server for Oracle ERP adapter, integrating with Admin API v1.2.0.
//     Uses Java 25 virtual threads, gRPC-Netty, and API /connectors for data.
//     Production-ready with logging, error handling, and shutdown hook.

// Author: Siergej Sobolewski
// Since: 2025-10-16

import io.grpc.Server;
import io.grpc.ServerBuilder;
import io.grpc.stub.StreamObserver;
import com.astradesk.finance.grpc.FinanceServiceGrpc;
import com.astradesk.finance.grpc.FetchSalesRequest;
import com.astradesk.finance.grpc.FetchSalesResponse;
import com.astradesk.finance.grpc.SalesItem;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Executors;

public class OracleErpGrpcServer {
    private static final Logger LOGGER = LoggerFactory.getLogger(OracleErpGrpcServer.class);
    private Server server;
    private final OracleErpAdapter apiAdapter;

    public OracleErpGrpcServer(String apiUrl, String token) {
        this.apiAdapter = new OracleErpAdapter(apiUrl, token);
    }

    /**
     * Start gRPC server on port 50051.
     */
    private void start() throws IOException {
        server = ServerBuilder.forPort(50051)
                .addService(new FinanceServiceImpl())
                .executor(Executors.newVirtualThreadPerTaskExecutor()) // Java 25 virtual threads
                .build()
                .start();
        LOGGER.info("gRPC server started on port 50051");

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            LOGGER.warn("Shutting down gRPC server");
            OracleErpGrpcServer.this.stop();
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

    class FinanceServiceImpl extends FinanceServiceGrpc.FinanceServiceImplBase {
        @Override
        public void fetchSales(FetchSalesRequest request, StreamObserver<FetchSalesResponse> responseObserver) {
            String query = request.getQuery();
            LOGGER.info("Fetching sales with query: {}", query);

            // Call Admin API via adapter
            Map<String, Object> connectorData = Map.of(
                "name", "erp_oracle",
                "type", "db",
                "config", Map.of("dsn", "oracle://user:pass@host")
            );
            apiAdapter.createConnector(connectorData)
                    .thenCompose(id -> {
                        Map<String, Object> probeData = Map.of("query", query);
                        return apiAdapter.probeConnector(id, probeData);
                    })
                    .thenAccept(result -> {
                        FetchSalesResponse.Builder builder = FetchSalesResponse.newBuilder();
                        for (Map<String, Object> item : result) {
                            SalesItem salesItem = SalesItem.newBuilder()
                                    .setRevenue(((Number) item.getOrDefault("revenue", 0.0)).doubleValue())
                                    .setDate((String) item.getOrDefault("date", ""))
                                    .build();
                            builder.addItems(salesItem);
                        }
                        responseObserver.onNext(builder.build());
                        responseObserver.onCompleted();
                    })
                    .exceptionally(ex -> {
                        LOGGER.error("Error fetching sales: {}", ex.getMessage());
                        responseObserver.onError(new RuntimeException("Failed to fetch sales: " + ex.getMessage()));
                        return null;
                    });
        }
    }

    public static void main(String[] args) throws IOException, InterruptedException {
        String apiUrl = System.getenv("API_URL") != null ? System.getenv("API_URL") : "http://localhost:8080/api/admin/v1";
        String token = System.getenv("API_TOKEN") != null ? System.getenv("API_TOKEN") : "";
        OracleErpGrpcServer server = new OracleErpGrpcServer(apiUrl, token);
        server.start();
        server.blockUntilShutdown();
    }
}
