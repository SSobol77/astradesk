// SPDX-License-Identifier: Apache-2.0
// File: packages/domain-supply/tests/java/SapS4HanaGrpcServerTest.java
// Project: AstraDesk Domain Supply Pack
// Description:
//     JUnit tests for SapS4HanaGrpcServer, using gRPC in-process server and MockWebServer for API.
//     Tests FetchInventory, ensuring API integration and response.

// Author: Siergej Sobolewski
// Since: 2025-10-16

import io.grpc.inprocess.InProcessChannelBuilder;
import io.grpc.inprocess.InProcessServerBuilder;
import io.grpc.testing.GrpcCleanupRule;
import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import com.astradesk.supply.grpc.SupplyServiceGrpc;
import com.astradesk.supply.grpc.FetchInventoryRequest;
import com.astradesk.supply.grpc.FetchInventoryResponse;
import static org.junit.jupiter.api.Assertions.*;

public class SapS4HanaGrpcServerTest {
    @Rule
    public final GrpcCleanupRule grpcCleanup = new GrpcCleanupRule();
    private static MockWebServer apiServer;
    private SupplyServiceGrpc.SupplyServiceBlockingStub blockingStub;

    @BeforeAll
    static void setUp() throws Exception {
        apiServer = new MockWebServer();
        apiServer.start();
    }

    @AfterAll
    static void tearDown() throws Exception {
        apiServer.shutdown();
    }

    @Test
    void testFetchInventorySuccess() throws Exception {
        String serverName = InProcessServerBuilder.generateName();
        SapS4HanaGrpcServer server = new SapS4HanaGrpcServer("http://" + apiServer.getHostName() + ":" + apiServer.getPort(), "test-token");
        grpcCleanup.register(InProcessServerBuilder.forName(serverName).directExecutor().addService(server.new SupplyServiceImpl()).build().start());
        blockingStub = SupplyServiceGrpc.newBlockingStub(
                grpcCleanup.register(InProcessChannelBuilder.forName(serverName).directExecutor().build()));

        // Mock API responses
        apiServer.enqueue(new MockResponse().setBody("{\"id\": \"sap1\"}").setResponseCode(201));
        apiServer.enqueue(new MockResponse().setBody("{\"result\": [{\"material\": \"M1\", \"stock\": 100}]}").setResponseCode(200));

        FetchInventoryRequest request = FetchInventoryRequest.newBuilder().setQuery("SELECT material, stock FROM MM").build();
        FetchInventoryResponse response = blockingStub.fetchInventory(request);

        assertEquals(1, response.getItemsCount());
        assertEquals("M1", response.getItems(0).getMaterial());
        assertEquals(100, response.getItems(0).getStock());
    }

    @Test
    void testFetchInventoryApiFailure() throws Exception {
        String serverName = InProcessServerBuilder.generateName();
        SapS4HanaGrpcServer server = new SapS4HanaGrpcServer("http://" + apiServer.getHostName() + ":" + apiServer.getPort(), "test-token");
        grpcCleanup.register(InProcessServerBuilder.forName(serverName).directExecutor().addService(server.new SupplyServiceImpl()).build().start());
        blockingStub = SupplyServiceGrpc.newBlockingStub(
                grpcCleanup.register(InProcessChannelBuilder.forName(serverName).directExecutor().build()));

        // Mock API failure
        apiServer.enqueue(new MockResponse().setBody("{\"type\": \"https://error\", \"title\": \"Bad Request\", \"status\": 400, \"detail\": \"Invalid config\"}").setResponseCode(400));

        FetchInventoryRequest request = FetchInventoryRequest.newBuilder().setQuery("SELECT material, stock FROM MM").build();
        assertThrows(Exception.class, () -> blockingStub.fetchInventory(request));
    }
}
