import { apiFetch } from '@/lib/api';
import type {
  Agent,
  AgentConfigRequest,
  AgentIoMessage,
  AgentMetrics,
  AgentTestResult,
  AuditEntry,
  Dataset,
  DatasetCreateRequest,
  DatasetEmbedding,
  DatasetReindexResponse,
  DatasetSchema,
  DlqItem,
  DomainPack,
  Flow,
  FlowCreateRequest,
  FlowDryRunResult,
  FlowGenerationRequest,
  FlowList,
  FlowTestResult,
  FlowUpdateRequest,
  FlowValidation,
  HealthStatus,
  IntentGraph,
  Job,
  JobCreateRequest,
  JobTriggerResult,
  Policy,
  PolicyCreateRequest,
  PolicySimulationRequest,
  PolicySimulationResult,
  RecentError,
  Run,
  Secret,
  SecretCreateRequest,
  SecretRotationResult,
  Setting,
  SettingsResponse,
  UsageMetrics,
  User,
  UserCreateRequest,
  Connector,
  ConnectorConfigRequest,
  ConnectorProbeResult,
  ConnectorTestResult,
} from '@/api/types';

const ADMIN_PREFIX = '/api/admin/v1';

type PaginationParams = {
  limit?: number;
  offset?: number;
};

export const openApiClient = {
  dashboard: {
    getHealth: () => apiFetch<HealthStatus>({ path: `${ADMIN_PREFIX}/health`, method: 'GET' }),
    getUsage: () => apiFetch<UsageMetrics>({ path: `${ADMIN_PREFIX}/usage/llm`, method: 'GET' }),
    getRecentErrors: ({ limit = 10, offset = 0 }: PaginationParams = {}) =>
      apiFetch<RecentError[]>({
        path: `${ADMIN_PREFIX}/errors/recent`,
        method: 'GET',
        searchParams: { limit, offset },
      }),
  },
  agents: {
    list: (params: PaginationParams = {}) =>
      apiFetch<Agent[]>({
        path: `${ADMIN_PREFIX}/agents`,
        method: 'GET',
        searchParams: params,
      }),
    get: (id: string) => apiFetch<Agent>({ path: `${ADMIN_PREFIX}/agents/${id}`, method: 'GET' }),
    create: (payload: AgentConfigRequest) =>
      apiFetch<Agent, AgentConfigRequest>({
        path: `${ADMIN_PREFIX}/agents`,
        method: 'POST',
        body: payload,
      }),
    update: (id: string, payload: AgentConfigRequest) =>
      apiFetch<Agent, AgentConfigRequest>({
        path: `${ADMIN_PREFIX}/agents/${id}`,
        method: 'PUT',
        body: payload,
      }),
    delete: (id: string) => apiFetch<void>({ path: `${ADMIN_PREFIX}/agents/${id}`, method: 'DELETE' }),
    test: (id: string, input: string) =>
      apiFetch<AgentTestResult, { input: string }>({
        path: `${ADMIN_PREFIX}/agents/${id}:test`,
        method: 'POST',
        body: { input },
      }),
    clone: (id: string) => apiFetch<Agent>({ path: `${ADMIN_PREFIX}/agents/${id}:clone`, method: 'POST' }),
    promote: (id: string) => apiFetch<Agent>({ path: `${ADMIN_PREFIX}/agents/${id}:promote`, method: 'POST' }),
    metrics: (id: string, timeWindow?: string) =>
      apiFetch<AgentMetrics>({
        path: `${ADMIN_PREFIX}/agents/${id}/metrics`,
        method: 'GET',
        searchParams: { timeWindow },
      }),
    io: (id: string, params: PaginationParams = {}) =>
      apiFetch<AgentIoMessage[]>({
        path: `${ADMIN_PREFIX}/agents/${id}/io`,
        method: 'GET',
        searchParams: params,
      }),
  },
  intentGraph: {
    get: () => apiFetch<IntentGraph>({ path: `${ADMIN_PREFIX}/intents/graph`, method: 'GET' }),
  },
  flows: {
    list: (
      params: PaginationParams & { status?: Flow['status']; env?: Agent['env'] } = {},
    ) =>
      apiFetch<FlowList>({
        path: `${ADMIN_PREFIX}/flows`,
        method: 'GET',
        searchParams: {
          limit: params.limit,
          offset: params.offset,
          status: params.status,
          env: params.env,
        },
      }),
    get: (id: string) => apiFetch<Flow>({ path: `${ADMIN_PREFIX}/flows/${id}`, method: 'GET' }),
    create: (payload: FlowCreateRequest) =>
      apiFetch<Flow, FlowCreateRequest>({
        path: `${ADMIN_PREFIX}/flows`,
        method: 'POST',
        body: payload,
      }),
    update: (id: string, payload: FlowUpdateRequest) =>
      apiFetch<Flow, FlowUpdateRequest>({
        path: `${ADMIN_PREFIX}/flows/${id}`,
        method: 'PUT',
        body: payload,
      }),
    delete: (id: string) => apiFetch<void>({ path: `${ADMIN_PREFIX}/flows/${id}`, method: 'DELETE' }),
    validate: (id: string) =>
      apiFetch<FlowValidation>({ path: `${ADMIN_PREFIX}/flows/${id}:validate`, method: 'POST' }),
    dryRun: (id: string) =>
      apiFetch<FlowDryRunResult>({ path: `${ADMIN_PREFIX}/flows/${id}:dryrun`, method: 'POST' }),
    test: (id: string) =>
      apiFetch<FlowTestResult>({ path: `${ADMIN_PREFIX}/flows/${id}:test`, method: 'POST' }),
    log: (id: string, params: PaginationParams = {}) =>
      apiFetch<string[]>({
        path: `${ADMIN_PREFIX}/flows/${id}/log`,
        method: 'GET',
        searchParams: params,
      }),
    generate: (payload: FlowGenerationRequest) =>
      apiFetch<string, FlowGenerationRequest>({
        path: `${ADMIN_PREFIX}/flows/generate`,
        method: 'POST',
        body: payload,
      }),
  },
  datasets: {
    list: (params: PaginationParams = {}) =>
      apiFetch<Dataset[]>({
        path: `${ADMIN_PREFIX}/datasets`,
        method: 'GET',
        searchParams: params,
      }),
    get: (id: string) => apiFetch<Dataset>({ path: `${ADMIN_PREFIX}/datasets/${id}`, method: 'GET' }),
    create: (payload: DatasetCreateRequest) =>
      apiFetch<Dataset, DatasetCreateRequest>({
        path: `${ADMIN_PREFIX}/datasets`,
        method: 'POST',
        body: payload,
      }),
    delete: (id: string) => apiFetch<void>({ path: `${ADMIN_PREFIX}/datasets/${id}`, method: 'DELETE' }),
    reindex: (id: string) =>
      apiFetch<DatasetReindexResponse>({
        path: `${ADMIN_PREFIX}/datasets/${id}:reindex`,
        method: 'POST',
      }),
    schema: (id: string) =>
      apiFetch<DatasetSchema>({ path: `${ADMIN_PREFIX}/datasets/${id}/schema`, method: 'GET' }),
    embeddings: (id: string, params: PaginationParams = {}) =>
      apiFetch<DatasetEmbedding[]>({
        path: `${ADMIN_PREFIX}/datasets/${id}/embeddings`,
        method: 'GET',
        searchParams: params,
      }),
  },
  connectors: {
    list: (params: PaginationParams = {}) =>
      apiFetch<Connector[]>({
        path: `${ADMIN_PREFIX}/connectors`,
        method: 'GET',
        searchParams: params,
      }),
    get: (id: string) => apiFetch<Connector>({ path: `${ADMIN_PREFIX}/connectors/${id}`, method: 'GET' }),
    create: (payload: ConnectorConfigRequest) =>
      apiFetch<Connector, ConnectorConfigRequest>({
        path: `${ADMIN_PREFIX}/connectors`,
        method: 'POST',
        body: payload,
      }),
    update: (id: string, payload: ConnectorConfigRequest) =>
      apiFetch<Connector, ConnectorConfigRequest>({
        path: `${ADMIN_PREFIX}/connectors/${id}`,
        method: 'PUT',
        body: payload,
      }),
    delete: (id: string) =>
      apiFetch<void>({ path: `${ADMIN_PREFIX}/connectors/${id}`, method: 'DELETE' }),
    test: (id: string) =>
      apiFetch<ConnectorTestResult>({ path: `${ADMIN_PREFIX}/connectors/${id}:test`, method: 'POST' }),
    probe: (id: string) =>
      apiFetch<ConnectorProbeResult>({ path: `${ADMIN_PREFIX}/connectors/${id}:probe`, method: 'POST' }),
  },
  secrets: {
    list: (params: PaginationParams = {}) =>
      apiFetch<Secret[]>({
        path: `${ADMIN_PREFIX}/secrets`,
        method: 'GET',
        searchParams: params,
      }),
    create: (payload: SecretCreateRequest) =>
      apiFetch<Secret, SecretCreateRequest>({
        path: `${ADMIN_PREFIX}/secrets`,
        method: 'POST',
        body: payload,
      }),
    rotate: (id: string) =>
      apiFetch<SecretRotationResult>({ path: `${ADMIN_PREFIX}/secrets/${id}:rotate`, method: 'POST' }),
    disable: (id: string) =>
      apiFetch<void>({ path: `${ADMIN_PREFIX}/secrets/${id}:disable`, method: 'DELETE' }),
  },
  runs: {
    list: (
      params: PaginationParams & { agentId?: string; status?: Run['status'] } = {},
    ) =>
      apiFetch<Run[]>({
        path: `${ADMIN_PREFIX}/runs`,
        method: 'GET',
        searchParams: {
          limit: params.limit,
          offset: params.offset,
          agentId: params.agentId,
          status: params.status,
        },
      }),
    get: (id: string) => apiFetch<Run>({ path: `${ADMIN_PREFIX}/runs/${id}`, method: 'GET' }),
    exportLogs: (format: 'json' | 'ndjson' | 'csv', params: Record<string, string | number | undefined> = {}) =>
      apiFetch<string>({
        path: `${ADMIN_PREFIX}/logs/export`,
        method: 'GET',
        searchParams: { format, ...params },
      }),
  },
  jobs: {
    list: (params: PaginationParams = {}) =>
      apiFetch<Job[]>({
        path: `${ADMIN_PREFIX}/jobs`,
        method: 'GET',
        searchParams: params,
      }),
    get: (id: string) => apiFetch<Job>({ path: `${ADMIN_PREFIX}/jobs/${id}`, method: 'GET' }),
    create: (payload: JobCreateRequest) =>
      apiFetch<Job, JobCreateRequest>({
        path: `${ADMIN_PREFIX}/jobs`,
        method: 'POST',
        body: payload,
      }),
    update: (id: string, payload: JobCreateRequest) =>
      apiFetch<Job, JobCreateRequest>({
        path: `${ADMIN_PREFIX}/jobs/${id}`,
        method: 'PUT',
        body: payload,
      }),
    delete: (id: string) => apiFetch<void>({ path: `${ADMIN_PREFIX}/jobs/${id}`, method: 'DELETE' }),
    trigger: (id: string) =>
      apiFetch<JobTriggerResult>({ path: `${ADMIN_PREFIX}/jobs/${id}:trigger`, method: 'POST' }),
    pause: (id: string) => apiFetch<Job>({ path: `${ADMIN_PREFIX}/jobs/${id}:pause`, method: 'POST' }),
    resume: (id: string) => apiFetch<Job>({ path: `${ADMIN_PREFIX}/jobs/${id}:resume`, method: 'POST' }),
    dlq: (params: PaginationParams = {}) =>
      apiFetch<DlqItem[]>({
        path: `${ADMIN_PREFIX}/dlq`,
        method: 'GET',
        searchParams: params,
      }),
  },
  rbac: {
    users: (params: PaginationParams = {}) =>
      apiFetch<User[]>({
        path: `${ADMIN_PREFIX}/users`,
        method: 'GET',
        searchParams: params,
      }),
    create: (payload: UserCreateRequest) =>
      apiFetch<User, UserCreateRequest>({
        path: `${ADMIN_PREFIX}/users`,
        method: 'POST',
        body: payload,
      }),
    get: (id: string) => apiFetch<User>({ path: `${ADMIN_PREFIX}/users/${id}`, method: 'GET' }),
    delete: (id: string) => apiFetch<void>({ path: `${ADMIN_PREFIX}/users/${id}`, method: 'DELETE' }),
    resetMfa: (id: string) =>
      apiFetch<{ status: string }>({ path: `${ADMIN_PREFIX}/users/${id}:reset-mfa`, method: 'POST' }),
    updateRole: (id: string, role: User['role']) =>
      apiFetch<User, { role: User['role'] }>({
        path: `${ADMIN_PREFIX}/users/${id}/role`,
        method: 'POST',
        body: { role },
      }),
    roles: () => apiFetch<string[]>({ path: `${ADMIN_PREFIX}/roles`, method: 'GET' }),
  },
  policies: {
    list: (params: PaginationParams = {}) =>
      apiFetch<Policy[]>({
        path: `${ADMIN_PREFIX}/policies`,
        method: 'GET',
        searchParams: params,
      }),
    get: (id: string) => apiFetch<Policy>({ path: `${ADMIN_PREFIX}/policies/${id}`, method: 'GET' }),
    create: (payload: PolicyCreateRequest) =>
      apiFetch<Policy, PolicyCreateRequest>({
        path: `${ADMIN_PREFIX}/policies`,
        method: 'POST',
        body: payload,
      }),
    update: (id: string, payload: PolicyCreateRequest) =>
      apiFetch<Policy, PolicyCreateRequest>({
        path: `${ADMIN_PREFIX}/policies/${id}`,
        method: 'PUT',
        body: payload,
      }),
    delete: (id: string) => apiFetch<void>({ path: `${ADMIN_PREFIX}/policies/${id}`, method: 'DELETE' }),
    simulate: (id: string, input: PolicySimulationRequest['input']) =>
      apiFetch<PolicySimulationResult, PolicySimulationRequest>({
        path: `${ADMIN_PREFIX}/policies/${id}:simulate`,
        method: 'POST',
        body: { input },
      }),
  },
  audit: {
    list: (params: PaginationParams & { user?: string; action?: string } = {}) =>
      apiFetch<AuditEntry[]>({
        path: `${ADMIN_PREFIX}/audit`,
        method: 'GET',
        searchParams: {
          limit: params.limit,
          offset: params.offset,
          user: params.user,
          action: params.action,
        },
      }),
    get: (id: string) => apiFetch<AuditEntry>({ path: `${ADMIN_PREFIX}/audit/${id}`, method: 'GET' }),
    exportData: (format: 'json' | 'ndjson', params: Record<string, string | number | undefined> = {}) =>
      apiFetch<string>({
        path: `${ADMIN_PREFIX}/audit/export`,
        method: 'GET',
        searchParams: { format, ...params },
      }),
  },
  settings: {
    list: (group: 'integrations' | 'localization' | 'platform') =>
      apiFetch<SettingsResponse>({
        path: `${ADMIN_PREFIX}/settings/${group}`,
        method: 'GET',
      }),
    update: (group: 'integrations' | 'localization' | 'platform', payload: { key: string; value: Record<string, unknown> }) =>
      apiFetch<Setting, typeof payload>({
        path: `${ADMIN_PREFIX}/settings/${group}`,
        method: 'PUT',
        body: payload,
      }),
  },
  domainPacks: {
    list: () => apiFetch<DomainPack[]>({ path: `${ADMIN_PREFIX}/domain-packs`, method: 'GET' }),
    install: (name: string) =>
      apiFetch<{ job_id: string }>({ path: `${ADMIN_PREFIX}/domain-packs/${name}:install`, method: 'POST' }),
    uninstall: (name: string) =>
      apiFetch<{ job_id: string }>({ path: `${ADMIN_PREFIX}/domain-packs/${name}:uninstall`, method: 'POST' }),
  },
};

export const apiClient = openApiClient;
