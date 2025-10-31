import type {
  Agent,
  AgentIoMessage,
  AgentMetrics,
  AuditEntry,
  Connector,
  Dataset,
  DatasetEmbedding,
  DatasetSchema,
  DlqItem,
  DomainPack,
  Flow,
  FlowDryRunResult,
  FlowLogEntry,
  FlowValidation,
  HealthStatus,
  IntentGraph,
  Job,
  Policy,
  RecentError,
  Run,
  Secret,
  Setting,
  UsageMetrics,
  User,
} from '@/api/types';

const now = () => new Date().toISOString();

export const simulationAgents: Agent[] = [
  {
    id: 'agent-sim-1',
    name: 'Knowledge Assistant',
    version: '1.4.0',
    env: 'prod',
    status: 'active',
    config: { model: 'gpt-4o-mini', temperature: 0.2 },
  },
  {
    id: 'agent-sim-2',
    name: 'Ops Triage Bot',
    version: '0.9.5',
    env: 'staging',
    status: 'degraded',
    config: { model: 'gpt-4o-mini', temperature: 0.4 },
  },
];

export const simulationAgentMetrics: AgentMetrics = {
  p95_latency_ms: 1200,
  p99_latency_ms: 1500,
  request_count: 4200,
};

export const simulationAgentIo: AgentIoMessage[] = [
  {
    timestamp: now(),
    input: 'How do I rotate the customer API key?',
    output: 'Navigate to Settings → Keys & Secrets, select the API key, and choose “Rotate”.',
  },
  {
    timestamp: now(),
    input: 'What is our current CSAT score?',
    output: 'The latest CSAT score is 4.7/5 based on 231 recent tickets.',
  },
];

export const simulationFlows: Flow[] = [
  {
    id: 'flow-sim-1',
    name: 'Daily Reporting',
    version: '1.0.0',
    status: 'active',
    env: 'prod',
    config_yaml: 'steps:\n  - id: export\n    action: export_daily_metrics\n  - id: email\n    action: email_summary\n',
    created_at: now(),
    updated_at: now(),
  },
];

export const simulationFlowValidation: FlowValidation = {
  valid: true,
  errors: [],
};

export const simulationFlowDryRun: FlowDryRunResult = {
  steps: [
    {
      name: 'export',
      status: 'success',
      output: { records: 128 },
    },
    {
      name: 'email',
      status: 'success',
      output: { recipients: 12 },
    },
  ],
};

export const simulationFlowLog: FlowLogEntry[] = [
  { timestamp: now(), level: 'INFO', message: 'Flow execution started' },
  { timestamp: now(), level: 'INFO', message: 'Exported 128 records' },
  { timestamp: now(), level: 'INFO', message: 'Summary email dispatched' },
];

export const simulationDatasets: Dataset[] = [
  {
    id: 'dataset-sim-1',
    name: 'Knowledge Base',
    type: 'git',
    indexing_status: 'indexed',
  },
];

export const simulationDatasetSchema: DatasetSchema = {
  fields: [
    { name: 'id', type: 'string' },
    { name: 'title', type: 'string' },
    { name: 'body', type: 'text', nullable: true },
  ],
};

export const simulationDatasetEmbeddings: DatasetEmbedding[] = [
  {
    id: 'embedding-1',
    source: 'knowledge-base/article-1.md',
    created_at: now(),
  },
];

export const simulationIntentGraph: IntentGraph = {
  nodes: [
    { id: 'intent-reset', label: 'Reset password', type: 'intent' },
    { id: 'tool-zendesk', label: 'Zendesk', type: 'tool' },
  ],
  edges: [{ source: 'intent-reset', target: 'tool-zendesk', label: 'uses' }],
};

export const simulationUsageMetrics: UsageMetrics = {
  total_requests: 1482,
  cost_usd: 12.45,
  latency_p95_ms: 945,
};

export const simulationHealthStatus: HealthStatus = {
  status: 'healthy',
  components: {
    workers: 'healthy',
    'vector-db': 'healthy',
    cache: 'degraded',
  },
};

export const simulationRecentErrors: RecentError[] = [
  {
    timestamp: now(),
    message: 'Connector timeout: zendesk',
    trace_id: 'trace-connector-1',
  },
  {
    timestamp: now(),
    message: 'Flow dry run failed at step validate_schema',
    trace_id: 'trace-flow-1',
  },
];

export const simulationJobs: Job[] = [
  {
    id: 'job-sim-1',
    name: 'Daily summary email',
    schedule_expr: '0 9 * * *',
    status: 'active',
    task_definition: { type: 'email-summary', recipients: ['ops@astradesk.com'] },
  },
];

export const simulationDlqItems: DlqItem[] = [
  {
    id: 'dlq-1',
    original_message: { job_id: 'job-sim-1' },
    error_message: 'Temporary SMTP failure',
    failed_at: now(),
  },
];

export const simulationPolicies: Policy[] = [
  {
    id: 'policy-sim-1',
    name: 'Support analysts',
    rego_text: 'package astradesk.authz\n\nallow { input.user.role == \"support\" }',
  },
];

export const simulationRuns: Run[] = [
  {
    id: 'run-sim-1',
    agent_id: 'agent-sim-1',
    status: 'completed',
    latency_ms: 834,
    cost_usd: 0.014,
    created_at: now(),
    completed_at: now(),
  },
];

export const simulationAuditEntries: AuditEntry[] = [
  {
    id: 'audit-sim-1',
    user_id: 'user-sim-1',
    action: 'secret.rotate',
    resource: 'secret:customer-api',
    when_ts: now(),
    signature: 'simulation-signature',
  },
];

export const simulationSecrets: Secret[] = [
  {
    id: 'secret-sim-1',
    name: 'Customer API',
    type: 'api-key',
    last_used_at: now(),
    created_at: now(),
  },
];

export const simulationConnectors: Connector[] = [
  { id: 'connector-sim-1', name: 'Zendesk', type: 'zendesk', status: 'healthy' },
];

export const simulationUsers: User[] = [
  {
    id: 'user-sim-1',
    email: 'admin@example.com',
    role: 'admin',
  },
];

export const simulationDomainPacks: DomainPack[] = [
  { name: 'customer-support', version: '2.1.0', status: 'installed' },
  { name: 'it-operations', version: '1.4.3', status: 'disabled' },
];

export const simulationSettings: Record<'integrations' | 'localization' | 'platform', Setting[]> = {
  integrations: [
    {
      group: 'integrations',
      key: 'zendesk',
      value: { subdomain: 'astradesk', enabled: true },
    },
  ],
  localization: [
    {
      group: 'localization',
      key: 'default_locale',
      value: { locale: 'en-US', currency: 'USD' },
    },
  ],
  platform: [
    {
      group: 'platform',
      key: 'timezone',
      value: { timezone: 'UTC' },
    },
  ],
};

export const simulationRecentErrorsResponse = simulationRecentErrors;

export function getSimulationResponse(path: string): unknown {
  const cleanPath = path.replace(/\?.*$/, '');
  const normalized = cleanPath.replace(/^\/api\/admin\/v1/, '');

  if (normalized === '/usage/llm') {
    return simulationUsageMetrics;
  }
  if (normalized === '/health') {
    return simulationHealthStatus;
  }
  if (normalized === '/errors/recent') {
    return simulationRecentErrorsResponse;
  }
  if (normalized === '/agents') {
    return simulationAgents;
  }
  if (normalized.startsWith('/agents/')) {
    const [, , agentId, rest] = normalized.split('/');
    const agent = simulationAgents.find((item) => item.id === agentId) ?? simulationAgents[0];
    if (!rest) {
      return agent;
    }
    if (rest === 'metrics') {
      return simulationAgentMetrics;
    }
    if (rest === 'io') {
      return simulationAgentIo;
    }
    return agent;
  }
  if (normalized === '/flows') {
    return {
      items: simulationFlows,
      total: simulationFlows.length,
      limit: simulationFlows.length,
      offset: 0,
    };
  }
  if (normalized.startsWith('/flows/')) {
    const flow = simulationFlows[0];
    if (normalized.endsWith(':validate')) {
      return simulationFlowValidation;
    }
    if (normalized.endsWith(':dryrun')) {
      return simulationFlowDryRun;
    }
    if (normalized.endsWith(':test')) {
      return { status: 'success', logs: ['Flow simulated successfully'], output: { message: 'ok' } };
    }
    if (normalized.endsWith('/log')) {
      return simulationFlowLog;
    }
    return flow;
  }
  if (normalized === '/datasets') {
    return simulationDatasets;
  }
  if (normalized.startsWith('/datasets/')) {
    if (normalized.endsWith('/schema')) {
      return simulationDatasetSchema;
    }
    if (normalized.endsWith('/embeddings')) {
      return simulationDatasetEmbeddings;
    }
    return simulationDatasets[0];
  }
  if (normalized === '/intents/graph') {
    return simulationIntentGraph;
  }
  if (normalized === '/jobs') {
    return simulationJobs;
  }
  if (normalized.startsWith('/jobs/')) {
    return simulationJobs[0];
  }
  if (normalized === '/dlq') {
    return simulationDlqItems;
  }
  if (normalized === '/policies') {
    return simulationPolicies;
  }
  if (normalized.startsWith('/policies/')) {
    if (normalized.endsWith(':simulate')) {
      return { allow: true, violations: [] };
    }
    return simulationPolicies[0];
  }
  if (normalized === '/runs') {
    return simulationRuns;
  }
  if (normalized.startsWith('/runs/')) {
    return simulationRuns[0];
  }
  if (normalized === '/users') {
    return simulationUsers;
  }
  if (normalized === '/roles') {
    return ['admin', 'operator', 'viewer'];
  }
  if (normalized === '/connectors') {
    return simulationConnectors;
  }
  if (normalized.startsWith('/connectors/')) {
    return simulationConnectors[0];
  }
  if (normalized === '/secrets') {
    return simulationSecrets;
  }
  if (normalized === '/audit') {
    return simulationAuditEntries;
  }
  if (normalized.startsWith('/audit/')) {
    if (normalized.endsWith('/export')) {
      return 'simulation-export';
    }
    return simulationAuditEntries[0];
  }
  if (normalized.startsWith('/logs/export')) {
    return 'simulation-log-export';
  }
  if (normalized === '/settings/integrations') {
    return simulationSettings.integrations;
  }
  if (normalized === '/settings/localization') {
    return simulationSettings.localization;
  }
  if (normalized === '/settings/platform') {
    return simulationSettings.platform;
  }
  if (normalized === '/domain-packs') {
    return simulationDomainPacks;
  }

  return undefined;
}
