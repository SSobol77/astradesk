import { apiFetch } from '@/lib/api';
import type {
  Agent,
  AgentIoMessage,
  AgentMetrics,
  AuditEntry,
  Dataset,
  DatasetEmbedding,
  DatasetSchema,
  DlqItem,
  Flow,
  FlowDryRunResult,
  FlowValidation,
  HealthStatus,
  IntentGraph,
  Job,
  Policy,
  PolicySimulationResult,
  Run,
  SettingsGroup,
  UsageMetrics,
  User,
} from '@/openapi/openapi-types';

export const openApiClient = {
  dashboard: {
    getHealth: () => apiFetch<HealthStatus>({ path: '/health', method: 'GET' }),
    getUsage: () => apiFetch<UsageMetrics>({ path: '/usage/llm', method: 'GET' }),
    getRecentErrors: (limit = 10) =>
      apiFetch<{ errors: string[] }>({
        path: '/errors/recent',
        method: 'GET',
        searchParams: { limit },
      }),
  },
  agents: {
    list: () => apiFetch<Agent[]>({ path: '/agents', method: 'GET' }),
    get: (id: string) => apiFetch<Agent>({ path: `/agents/${id}`, method: 'GET' }),
    create: (payload: Agent) => apiFetch<Agent, Agent>({ path: '/agents', method: 'POST', body: payload }),
    update: (id: string, payload: Agent) =>
      apiFetch<Agent, Agent>({ path: `/agents/${id}`, method: 'PUT', body: payload }),
    test: (id: string) => apiFetch<{ status: string }>({ path: `/agents/${id}:test`, method: 'POST' }),
    clone: (id: string) => apiFetch<Agent>({ path: `/agents/${id}:clone`, method: 'POST' }),
    promote: (id: string) => apiFetch<Agent>({ path: `/agents/${id}:promote`, method: 'POST' }),
    metrics: (id: string, query?: { p95?: boolean; p99?: boolean }) =>
      apiFetch<AgentMetrics>({
        path: `/agents/${id}/metrics`,
        method: 'GET',
        searchParams: {
          p95: query?.p95,
          p99: query?.p99,
        },
      }),
    io: (id: string, tail = 10) =>
      apiFetch<AgentIoMessage[]>({
        path: `/agents/${id}/io`,
        method: 'GET',
        searchParams: { tail },
      }),
  },
  intentGraph: {
    get: () => apiFetch<IntentGraph>({ path: '/intents/graph', method: 'GET' }),
  },
  flows: {
    list: () => apiFetch<Flow[]>({ path: '/flows', method: 'GET' }),
    get: (id: string) => apiFetch<Flow>({ path: `/flows/${id}`, method: 'GET' }),
    create: (payload: Flow) => apiFetch<Flow, Flow>({ path: '/flows', method: 'POST', body: payload }),
    validate: (id: string) => apiFetch<FlowValidation>({ path: `/flows/${id}:validate`, method: 'POST' }),
    dryRun: (id: string) => apiFetch<FlowDryRunResult>({ path: `/flows/${id}:dryrun`, method: 'POST' }),
    log: (id: string) => apiFetch<string[]>({ path: `/flows/${id}/log`, method: 'GET' }),
  },
  datasets: {
    list: () => apiFetch<Dataset[]>({ path: '/datasets', method: 'GET' }),
    get: (id: string) => apiFetch<Dataset>({ path: `/datasets/${id}`, method: 'GET' }),
    create: (payload: Dataset) => apiFetch<Dataset, Dataset>({ path: '/datasets', method: 'POST', body: payload }),
    reindex: (id: string) => apiFetch<{ status: string }>({ path: `/datasets/${id}:reindex`, method: 'POST' }),
    schema: (id: string) => apiFetch<DatasetSchema>({ path: `/datasets/${id}/schema`, method: 'GET' }),
    embeddings: (id: string) => apiFetch<DatasetEmbedding[]>({ path: `/datasets/${id}/embeddings`, method: 'GET' }),
  },
  tools: {
    list: () => apiFetch<{ id: string; name: string; type: string }[]>({ path: '/connectors', method: 'GET' }),
    get: (id: string) => apiFetch<{ id: string; name: string; type: string; status?: string }>({ path: `/connectors/${id}`, method: 'GET' }),
    create: (payload: { name: string; type: string }) =>
      apiFetch<{ id: string; name: string; type: string }, { name: string; type: string }>({
        path: '/connectors',
        method: 'POST',
        body: payload,
      }),
    test: (id: string) => apiFetch<{ status: string }>({ path: `/connectors/${id}:test`, method: 'POST' }),
    probe: (id: string) => apiFetch<{ latency_ms: number }>({ path: `/connectors/${id}:probe`, method: 'POST' }),
  },
  secrets: {
    list: () => apiFetch<{ id: string; name: string; type: string; last_used_at?: string }[]>({ path: '/secrets', method: 'GET' }),
    create: (payload: { name: string; type: string }) =>
      apiFetch<{ id: string; name: string; type: string }, { name: string; type: string }>({
        path: '/secrets',
        method: 'POST',
        body: payload,
      }),
    rotate: (id: string) => apiFetch<{ status: string }>({ path: `/secrets/${id}:rotate`, method: 'POST' }),
    disable: (id: string) => apiFetch<{ status: string }>({ path: `/secrets/${id}:disable`, method: 'POST' }),
  },
  runs: {
    list: (query?: Record<string, string | number | undefined>) =>
      apiFetch<Run[]>({ path: '/runs', method: 'GET', searchParams: query }),
    get: (id: string) => apiFetch<Run>({ path: `/runs/${id}`, method: 'GET' }),
    exportLogs: (format: 'json' | 'ndjson') =>
      apiFetch<string>({
        path: '/logs/export',
        method: 'GET',
        searchParams: { format },
      }),
  },
  jobs: {
    list: () => apiFetch<Job[]>({ path: '/jobs', method: 'GET' }),
    get: (id: string) => apiFetch<Job>({ path: `/jobs/${id}`, method: 'GET' }),
    create: (payload: Job) => apiFetch<Job, Job>({ path: '/jobs', method: 'POST', body: payload }),
    trigger: (id: string) => apiFetch<{ run_id: string }>({ path: `/jobs/${id}:trigger`, method: 'POST' }),
    pause: (id: string) => apiFetch<{ status: string }>({ path: `/jobs/${id}:pause`, method: 'POST' }),
    dlq: () => apiFetch<DlqItem[]>({ path: '/dlq', method: 'GET' }),
  },
  rbac: {
    users: () => apiFetch<User[]>({ path: '/users', method: 'GET' }),
    invite: (payload: { email: string; role: User['role'] }) =>
      apiFetch<User, { email: string; role: User['role'] }>({
        path: '/users:invite',
        method: 'POST',
        body: payload,
      }),
    resetMfa: (id: string) => apiFetch<{ status: string }>({ path: `/users/${id}:reset-mfa`, method: 'POST' }),
    updateRole: (id: string, role: User['role']) =>
      apiFetch<User>({ path: `/users/${id}:role`, method: 'POST', body: { role } }),
    roles: () => apiFetch<string[]>({ path: '/roles', method: 'GET' }),
  },
  policies: {
    list: () => apiFetch<Policy[]>({ path: '/policies', method: 'GET' }),
    get: (id: string) => apiFetch<Policy>({ path: `/policies/${id}`, method: 'GET' }),
    create: (payload: Policy) => apiFetch<Policy, Policy>({ path: '/policies', method: 'POST', body: payload }),
    update: (id: string, payload: Policy) =>
      apiFetch<Policy, Policy>({ path: `/policies/${id}`, method: 'PUT', body: payload }),
    simulate: (id: string, input: Record<string, unknown>) =>
      apiFetch<PolicySimulationResult>({ path: `/policies/${id}:simulate`, method: 'POST', body: { input } }),
  },
  audit: {
    list: (query?: Record<string, string | undefined>) =>
      apiFetch<AuditEntry[]>({ path: '/audit', method: 'GET', searchParams: query }),
    get: (id: string) => apiFetch<AuditEntry>({ path: `/audit/${id}`, method: 'GET' }),
    exportData: (format: 'json' | 'ndjson') =>
      apiFetch<string>({ path: '/audit/export', method: 'GET', searchParams: { format } }),
  },
  settings: {
    integrations: () => apiFetch<SettingsGroup>({ path: '/settings/integrations', method: 'GET' }),
    updateIntegrations: (payload: SettingsGroup) =>
      apiFetch<SettingsGroup, SettingsGroup>({ path: '/settings/integrations', method: 'PUT', body: payload }),
    localization: () => apiFetch<SettingsGroup>({ path: '/settings/localization', method: 'GET' }),
    updateLocalization: (payload: SettingsGroup) =>
      apiFetch<SettingsGroup, SettingsGroup>({ path: '/settings/localization', method: 'PUT', body: payload }),
    platform: () => apiFetch<SettingsGroup>({ path: '/settings/platform', method: 'GET' }),
    updatePlatform: (payload: SettingsGroup) =>
      apiFetch<SettingsGroup, SettingsGroup>({ path: '/settings/platform', method: 'PUT', body: payload }),
  },
};
