package com.astradesk.ticket.clients;

import admin_api.ApiClient;
import admin_api.models.Agent;
import java.io.IOException;
import java.util.List;

/**
 * Convenience wrapper around the generated Admin API client.
 *
 * <p>Example usage:
 *
 * <pre>
 * var adminApi = AdminApiClient.fromEnv();
 * var agents = adminApi.listAgents(20, 0);
 * </pre>
 */
public final class AdminApiClient {
  private final ApiClient delegate;

  private AdminApiClient(ApiClient delegate) {
    this.delegate = delegate;
  }

  public static AdminApiClient fromEnv() {
    String baseUrl = System.getenv().getOrDefault("ADMIN_API_URL", "http://localhost:8080/api/admin/v1");
    String token = System.getenv("ADMIN_API_TOKEN");
    return new AdminApiClient(new ApiClient(baseUrl, token));
  }

  public List<Agent> listAgents(Integer limit, Integer offset) throws IOException {
    return delegate.listAgents(limit, offset);
  }

  public Agent getAgent(String agentId) throws IOException {
    return delegate.getAgent(agentId);
  }

  public Agent promoteAgent(String agentId) throws IOException {
    return delegate.promoteAgent(agentId);
  }

  public byte[] exportLogs(String format, String agentId, String status, String from, String to) throws IOException {
    return delegate.exportLogs(format, agentId, status, from, to);
  }

  public ApiClient raw() {
    return delegate;
  }
}
