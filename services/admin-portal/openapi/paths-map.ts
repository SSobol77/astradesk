export type HttpMethod = 'GET' | 'POST' | 'PUT';

export type QueryParamMeta = {
  key: string;
  label: string;
  type?: 'text' | 'select' | 'date';
  options?: { label: string; value: string }[];
};

export type OperationDescriptor = {
  method: HttpMethod;
  path: string;
  summary?: string;
  query?: readonly QueryParamMeta[];
};

export const pathsMap = {
  dashboard: {
    health: { method: 'GET', path: '/health' },
    usage: { method: 'GET', path: '/usage/llm' },
    errorsRecent: {
      method: 'GET',
      path: '/errors/recent',
      query: [
        {
          key: 'limit',
          label: 'Limit',
          type: 'select',
          options: [
            { label: '10', value: '10' },
            { label: '25', value: '25' },
            { label: '50', value: '50' },
          ],
        },
      ],
    },
  },
  agents: {
    list: { method: 'GET', path: '/agents' },
    detail: { method: 'GET', path: '/agents/{id}' },
    create: { method: 'POST', path: '/agents' },
    update: { method: 'PUT', path: '/agents/{id}' },
    test: { method: 'POST', path: '/agents/{id}:test' },
    clone: { method: 'POST', path: '/agents/{id}:clone' },
    promote: { method: 'POST', path: '/agents/{id}:promote' },
    metrics: {
      method: 'GET',
      path: '/agents/{id}/metrics',
      query: [
        { key: 'p95', label: 'p95', type: 'select', options: [ { label: 'true', value: 'true' }, { label: 'false', value: 'false' } ] },
        { key: 'p99', label: 'p99', type: 'select', options: [ { label: 'true', value: 'true' }, { label: 'false', value: 'false' } ] },
      ],
    },
    io: {
      method: 'GET',
      path: '/agents/{id}/io',
      query: [
        { key: 'tail', label: 'Tail', type: 'select', options: [ { label: '10', value: '10' }, { label: '50', value: '50' }, { label: '100', value: '100' } ] },
      ],
    },
  },
  intentGraph: {
    graph: { method: 'GET', path: '/intents/graph' },
  },
  flows: {
    list: { method: 'GET', path: '/flows' },
    detail: { method: 'GET', path: '/flows/{id}' },
    create: { method: 'POST', path: '/flows' },
    validate: { method: 'POST', path: '/flows/{id}:validate' },
    dryRun: { method: 'POST', path: '/flows/{id}:dryrun' },
    log: { method: 'GET', path: '/flows/{id}/log' },
  },
  datasets: {
    list: { method: 'GET', path: '/datasets' },
    detail: { method: 'GET', path: '/datasets/{id}' },
    create: { method: 'POST', path: '/datasets' },
    reindex: { method: 'POST', path: '/datasets/{id}:reindex' },
    schema: { method: 'GET', path: '/datasets/{id}/schema' },
    embeddings: { method: 'GET', path: '/datasets/{id}/embeddings' },
  },
  tools: {
    list: { method: 'GET', path: '/connectors' },
    detail: { method: 'GET', path: '/connectors/{id}' },
    create: { method: 'POST', path: '/connectors' },
    test: { method: 'POST', path: '/connectors/{id}:test' },
    probe: { method: 'POST', path: '/connectors/{id}:probe' },
  },
  secrets: {
    list: { method: 'GET', path: '/secrets' },
    create: { method: 'POST', path: '/secrets' },
    rotate: { method: 'POST', path: '/secrets/{id}:rotate' },
    disable: { method: 'POST', path: '/secrets/{id}:disable' },
  },
  runs: {
    list: {
      method: 'GET',
      path: '/runs',
      query: [
        { key: 'agent', label: 'Agent' },
        { key: 'intent', label: 'Intent' },
        { key: 'status', label: 'Status' },
        { key: 'from', label: 'From', type: 'date' },
        { key: 'to', label: 'To', type: 'date' },
      ],
    },
    stream: { method: 'GET', path: '/runs/stream' },
    detail: { method: 'GET', path: '/runs/{id}' },
    exportLogs: {
      method: 'GET',
      path: '/logs/export',
      query: [
        { key: 'format', label: 'Format', type: 'select', options: [ { label: 'JSON', value: 'json' }, { label: 'NDJSON', value: 'ndjson' } ] },
      ],
    },
  },
  jobs: {
    list: { method: 'GET', path: '/jobs' },
    detail: { method: 'GET', path: '/jobs/{id}' },
    create: { method: 'POST', path: '/jobs' },
    trigger: { method: 'POST', path: '/jobs/{id}:trigger' },
    pause: { method: 'POST', path: '/jobs/{id}:pause' },
    dlq: { method: 'GET', path: '/dlq' },
  },
  rbac: {
    users: { method: 'GET', path: '/users' },
    invite: { method: 'POST', path: '/users:invite' },
    resetMfa: { method: 'POST', path: '/users/{id}:reset-mfa' },
    updateRole: { method: 'POST', path: '/users/{id}:role' },
    roles: { method: 'GET', path: '/roles' },
  },
  policies: {
    list: { method: 'GET', path: '/policies' },
    detail: { method: 'GET', path: '/policies/{id}' },
    create: { method: 'POST', path: '/policies' },
    update: { method: 'PUT', path: '/policies/{id}' },
    simulate: { method: 'POST', path: '/policies/{id}:simulate' },
  },
  audit: {
    list: {
      method: 'GET',
      path: '/audit',
      query: [
        { key: 'user', label: 'User' },
        { key: 'action', label: 'Action' },
        { key: 'resource', label: 'Resource' },
        { key: 'from', label: 'From', type: 'date' },
        { key: 'to', label: 'To', type: 'date' },
      ],
    },
    export: {
      method: 'GET',
      path: '/audit/export',
      query: [
        { key: 'format', label: 'Format', type: 'select', options: [ { label: 'JSON', value: 'json' }, { label: 'NDJSON', value: 'ndjson' } ] },
      ],
    },
    detail: { method: 'GET', path: '/audit/{id}' },
  },
  settings: {
    integrations: { method: 'GET', path: '/settings/integrations' },
    updateIntegrations: { method: 'PUT', path: '/settings/integrations' },
    localization: { method: 'GET', path: '/settings/localization' },
    updateLocalization: { method: 'PUT', path: '/settings/localization' },
    platform: { method: 'GET', path: '/settings/platform' },
    updatePlatform: { method: 'PUT', path: '/settings/platform' },
  },
} as const;

export type PathsMap = typeof pathsMap;
