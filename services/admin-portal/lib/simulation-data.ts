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
  Role,
  Run,
  Secret,
  SettingsGroup,
  UsageMetrics,
  User,
} from '@/openapi/openapi-types';

const now = () => new Date().toISOString();

export const simulationAgents: Agent[] = [
  {
    id: 'agent-sim-1',
    name: 'Knowledge Assistant',
    version: '1.4.0',
    env: 'prod',
    status: 'active',
    description: 'Provides contextual answers using the AstraDesk knowledge base.',
    updatedAt: now(),
  },
  {
    id: 'agent-sim-2',
    name: 'Ops Triage Bot',
    version: '0.9.5',
    env: 'staging',
    status: 'degraded',
    description: 'Routes incidents to the correct runbooks during outages.',
    updatedAt: now(),
  },
];

export const simulationAgentMetrics: AgentMetrics = {
  latencyP95Ms: 1200,
  latencyP99Ms: 1500,
  tokensPerMinute: 4200,
};

export const simulationAgentIo: AgentIoMessage[] = [
  {
    timestamp: now(),
    role: 'user',
    content: 'How do I rotate the customer API key?',
  },
  {
    timestamp: now(),
    role: 'assistant',
    content: 'Navigate to Settings → Keys & Secrets, select the API key, then choose “Rotate”.',
  },
];

export const simulationFlows: Flow[] = [
  {
    id: 'flow-sim-1',
    name: 'Daily Reporting',
    yaml: 'steps:\n  - name: export\n    action: export_daily_metrics\n  - name: email\n    action: email_summary',
  },
];

export const simulationFlowValidation: FlowValidation = {
  valid: true,
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
    },
  ],
};

export const simulationDatasets: Dataset[] = [
  {
    id: 'dataset-sim-1',
    name: 'Knowledge Base',
    type: 'git',
    indexing_status: 'idle',
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
    vectorId: 'vec-1',
    dimension: 1536,
    metadata: { source: 'knowledge-base/article-1.md' },
  },
];

export const simulationIntentGraph: IntentGraph = {
  nodes: [
    { id: 'intent-1', label: 'Reset password' },
    { id: 'intent-2', label: 'Rotate API key' },
  ],
  edges: [{ from: 'intent-1', to: 'intent-2', label: 'related' }],
};

export const simulationJobs: Job[] = [
  {
    id: 'job-sim-1',
    name: 'Daily summary email',
    schedule_expr: '0 9 * * *',
    status: 'active',
    last_run_at: now(),
    next_run_at: now(),
  },
];

export const simulationDlqItems: DlqItem[] = [
  {
    id: 'dlq-1',
    job_id: 'job-sim-1',
    failure_reason: 'Temporary SMTP failure',
    created_at: now(),
  },
];

export const simulationPolicies: Policy[] = [
  {
    id: 'policy-sim-1',
    name: 'Support analysts',
    description: 'Allow read access to tickets and knowledge base.',
    raw: 'allow group:support to read resource:tickets',
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
    status: 'active',
  },
];

export const simulationConnectors = [
  { id: 'connector-sim-1', name: 'Zendesk', type: 'zendesk', status: 'healthy' },
];

export const simulationUsers: User[] = [
  {
    id: 'user-sim-1',
    email: 'admin@example.com',
    role: 'admin',
    status: 'active',
    last_active_at: now(),
  },
];

export const simulationRoles: Role[] = [
  {
    id: 'role-sim-1',
    name: 'admin',
    description: 'Full access to administration features.',
  },
];

export const simulationSettingsGroups: SettingsGroup[] = [
  {
    group: 'platform',
    key: 'timezone',
    value: { timezone: 'UTC' },
  },
];

export const simulationUsageMetrics: UsageMetrics = {
  total_requests: 1482,
  cost_usd: 12.45,
  latency_p95_ms: 945,
};

export const simulationHealthStatus: HealthStatus = {
  status: 'healthy',
  components: [
    { name: 'workers', status: 'healthy' },
    { name: 'vector-db', status: 'healthy' },
  ],
};

export const simulationRecentErrors = {
  errors: ['2024-10-12T12:18:04Z connector timeout: zendesk'],
};

export function getSimulationResponse(path: string): unknown {
  const cleanPath = path.replace(/\?.*$/, '');

  if (cleanPath === '/usage/llm') {
    return simulationUsageMetrics;
  }
  if (cleanPath === '/health') {
    return simulationHealthStatus;
  }
  if (cleanPath === '/errors/recent') {
    return simulationRecentErrors;
  }
  if (cleanPath === '/agents') {
    return simulationAgents;
  }
  if (cleanPath.startsWith('/agents/')) {
    const [, , agentId, rest] = cleanPath.split('/');
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
  if (cleanPath === '/flows') {
    return simulationFlows;
  }
  if (cleanPath.startsWith('/flows/')) {
    const flow = simulationFlows[0];
    if (cleanPath.endsWith(':validate')) {
      return simulationFlowValidation;
    }
    if (cleanPath.endsWith(':dryrun')) {
      return simulationFlowDryRun;
    }
    if (cleanPath.endsWith('/log')) {
      return ['2024-10-12T12:17:00Z step export completed'];
    }
    return flow;
  }
  if (cleanPath === '/datasets') {
    return simulationDatasets;
  }
  if (cleanPath.startsWith('/datasets/')) {
    if (cleanPath.endsWith('/schema')) {
      return simulationDatasetSchema;
    }
    if (cleanPath.endsWith('/embeddings')) {
      return simulationDatasetEmbeddings;
    }
    return simulationDatasets[0];
  }
  if (cleanPath === '/intents/graph') {
    return simulationIntentGraph;
  }
  if (cleanPath === '/jobs') {
    return simulationJobs;
  }
  if (cleanPath === '/dlq') {
    return simulationDlqItems;
  }
  if (cleanPath.startsWith('/jobs/')) {
    return simulationJobs[0];
  }
  if (cleanPath === '/policies') {
    return simulationPolicies;
  }
  if (cleanPath.startsWith('/policies/')) {
    if (cleanPath.endsWith(':simulate')) {
      return { allow: true };
    }
    return simulationPolicies[0];
  }
  if (cleanPath === '/runs') {
    return simulationRuns;
  }
  if (cleanPath.startsWith('/runs/')) {
    return simulationRuns[0];
  }
  if (cleanPath === '/users') {
    return simulationUsers;
  }
  if (cleanPath === '/roles') {
    return simulationRoles.map((role) => role.name);
  }
  if (cleanPath === '/connectors') {
    return simulationConnectors;
  }
  if (cleanPath.startsWith('/connectors/')) {
    return simulationConnectors[0];
  }
  if (cleanPath === '/secrets') {
    return simulationSecrets;
  }
  if (cleanPath === '/audit') {
    return simulationAuditEntries;
  }
  if (cleanPath.startsWith('/audit/')) {
    return simulationAuditEntries[0];
  }
  if (cleanPath === '/settings/platform') {
    return simulationSettingsGroups[0];
  }
  if (cleanPath === '/settings/integrations' || cleanPath === '/settings/localization') {
    return simulationSettingsGroups[0];
  }

  return undefined;
}
