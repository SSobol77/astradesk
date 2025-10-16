// SPDX-License-Identifier: Apache-2.0
// File: packages/domain-finance/tests/java/OracleErpGrpcServerTest.java
// Project: AstraDesk Domain Finance Pack
// Description:
//     JUnit tests for OracleErpGrpcServer, using gRPC in-process server and MockWebServer for API.
//     Tests FetchSales, ensuring API integration and response.

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
import com.astradesk.finance.grpc.FinanceServiceGrpc;
import com.astradesk.finance.grpc.FetchSalesRequest;
import com.astradesk.finance.grpc.FetchSalesResponse;
import static org.junit.jupiter.api.Assertions.*;

public class OracleErpGrpcServerTest {
    @Rule
    public final GrpcCleanupRule grpcCleanup = new GrpcCleanupRule();
    private static MockWebServer apiServer;
    private FinanceServiceGrpc.FinanceServiceBlockingStub blockingStub;

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
    void testFetchSalesSuccess() throws Exception {
        String serverName = InProcessServerBuilder.generateName();
        OracleErpGrpcServer server = new OracleErpGrpcServer("http://" + apiServer.getHostName() + ":" + apiServer.getPort(), "test-token");
        grpcCleanup.register(InProcessServerBuilder.forName(serverName).directExecutor().addService(server.new FinanceServiceImpl()).build().start());
        blockingStub = FinanceServiceGrpc.newBlockingStub(
                grpcCleanup.register(InProcessChannelBuilder.forName(serverName).directExecutor().build()));

        // Mock API responses
        apiServer.enqueue(new MockResponse().setBody("{\"id\": \"erp1\"}").setResponseCode(201));
        apiServer.enqueue(new MockResponse().setBody("{\"result\": [{\"revenue\": 1000.0, \"date\": \"2025-10-01\"}]}").setResponseCode(200));

        FetchSalesRequest request = FetchSalesRequest.newBuilder().setQuery("SELECT revenue, date FROM sales").build();
        FetchSalesResponse response = blockingStub.fetchSales(request);

        assertEquals(1, response.getItemsCount());
        assertEquals(1000.0, response.getItems(0).getRevenue(), 0.01);
        assertEquals("2025-10-01", response.getItems(0).getDate());
    }

    @Test
    void testFetchSalesApiFailure() throws Exception {
        String serverName = InProcessServerBuilder.generateName();
        OracleErpGrpcServer server = new OracleErpGrpcServer("http://" + apiServer.getHostName() + ":" + apiServer.getPort(), "test-token");
        grpcCleanup.register(InProcessServerBuilder.forName(serverName).directExecutor().addService(server.new FinanceServiceImpl()).build().start());
        blockingStub = FinanceServiceGrpc.newBlockingStub(
                grpcCleanup.register(InProcessChannelBuilder.forName(serverName).directExecutor().build()));

        // Mock API failure
        apiServer.enqueue(new MockResponse().setBody("{\"type\": \"https://error\", \"title\": \"Bad Request\", \"status\": 400, \"detail\": \"Invalid config\"}").setResponseCode(400));

        FetchSalesRequest request = FetchSalesRequest.newBuilder().setQuery("SELECT revenue, date FROM sales").build();
        assertThrows(Exception.class, () -> blockingStub.fetchSales(request));
    }
}
