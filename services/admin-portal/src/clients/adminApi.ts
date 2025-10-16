/**
 * Thin convenience wrapper around the auto-generated Admin API client.
 *
 * Usage:
 * ```ts
 * import { getAdminApi } from "@/clients/adminApi";
 *
 * const adminApi = getAdminApi();
 * const agents = await adminApi.listAgents({ limit: 20 });
 * ```
 */

import type { LogsExportQuery, RequestConfig } from "@/_gen/admin_api";
import { exportLogs, getAgent, listAgents, promoteAgent } from "@/_gen/admin_api";

type ListAgentsQuery = Parameters<typeof listAgents>[1];

export interface AdminApiOptions {
  baseUrl?: string;
  token?: string;
  fetchFn?: typeof fetch;
  timeoutMs?: number;
}

class AdminApi {
  private readonly config: RequestConfig;

  constructor(options: AdminApiOptions = {}) {
    const baseUrl = (options.baseUrl ?? process.env.ADMIN_API_URL ?? "http://localhost:8080/api/admin/v1").replace(/\/$/, "");

    this.config = {
      baseUrl,
      token: options.token ?? process.env.ADMIN_API_TOKEN ?? undefined,
      fetchFn: options.fetchFn,
      timeoutMs: options.timeoutMs,
    };
  }

  async listAgents(query: ListAgentsQuery = {}) {
    return listAgents(this.config, query);
  }

  async getAgent(agentId: string) {
    return getAgent(this.config, agentId);
  }

  async promoteAgent(agentId: string) {
    return promoteAgent(this.config, agentId);
  }

  async exportLogs(query: LogsExportQuery = {}) {
    return exportLogs(this.config, query);
  }
}

export const getAdminApi = (options?: AdminApiOptions) => new AdminApi(options);

export type { AdminApi };
