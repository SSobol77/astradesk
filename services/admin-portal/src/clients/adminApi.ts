// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/src/clients/adminApi.ts
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/src/clients/adminApi.ts.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

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
