export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

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
    delete: { method: 'DELETE', path: '/agents/{id}' },
    test: { method: 'POST', path: '/agents/{id}:test' },
    clone: { method: 'POST', path: '/agents/{id}:clone' },
    promote: { method: 'POST', path: '/agents/{id}:promote' },
    metrics: {
      method: 'GET',
      path: '/agents/{id}/metrics',
      query: [
        {
          key: 'timeWindow',
          label: 'Time window',
          type: 'select',
          options: [
            { label: '1h', value: '1h' },
            { label: '24h', value: '24h' },
            { label: '7d', value: '7d' },
          ],
        },
      ],
    },
    io: {
      method: 'GET',
      path: '/agents/{id}/io',
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
        { key: 'offset', label: 'Offset' },
      ],
    },
  },
  intentGraph: {
    graph: { method: 'GET', path: '/intents/graph' },
  },
  flows: {
    list: {
      method: 'GET',
      path: '/flows',
      query: [
        {
          key: 'status',
          label: 'Status',
          type: 'select',
          options: [
            { label: 'Draft', value: 'draft' },
            { label: 'Active', value: 'active' },
            { label: 'Archived', value: 'archived' },
          ],
        },
        {
          key: 'env',
          label: 'Environment',
          type: 'select',
          options: [
            { label: 'Draft', value: 'draft' },
            { label: 'Dev', value: 'dev' },
            { label: 'Staging', value: 'staging' },
            { label: 'Production', value: 'prod' },
          ],
        },
        { key: 'limit', label: 'Limit' },
        { key: 'offset', label: 'Offset' },
      ],
    },
    detail: { method: 'GET', path: '/flows/{id}' },
    create: { method: 'POST', path: '/flows' },
    update: { method: 'PUT', path: '/flows/{id}' },
    delete: { method: 'DELETE', path: '/flows/{id}' },
    validate: { method: 'POST', path: '/flows/{id}:validate' },
    dryRun: { method: 'POST', path: '/flows/{id}:dryrun' },
    log: {
      method: 'GET',
      path: '/flows/{id}/log',
      query: [
        { key: 'limit', label: 'Limit' },
        { key: 'offset', label: 'Offset' },
      ],
    },
  },
  datasets: {
    list: { method: 'GET', path: '/datasets' },
    detail: { method: 'GET', path: '/datasets/{id}' },
    create: { method: 'POST', path: '/datasets' },
    delete: { method: 'DELETE', path: '/datasets/{id}' },
    reindex: { method: 'POST', path: '/datasets/{id}:reindex' },
    schema: { method: 'GET', path: '/datasets/{id}/schema' },
    embeddings: {
      method: 'GET',
      path: '/datasets/{id}/embeddings',
      query: [
        { key: 'limit', label: 'Limit' },
        { key: 'offset', label: 'Offset' },
      ],
    },
  },
  tools: {
    list: { method: 'GET', path: '/connectors' },
    detail: { method: 'GET', path: '/connectors/{id}' },
    create: { method: 'POST', path: '/connectors' },
    update: { method: 'PUT', path: '/connectors/{id}' },
    delete: { method: 'DELETE', path: '/connectors/{id}' },
    test: { method: 'POST', path: '/connectors/{id}:test' },
    probe: { method: 'POST', path: '/connectors/{id}:probe' },
  },
  secrets: {
    list: { method: 'GET', path: '/secrets' },
    create: { method: 'POST', path: '/secrets' },
    rotate: { method: 'POST', path: '/secrets/{id}:rotate' },
    disable: { method: 'DELETE', path: '/secrets/{id}:disable' },
  },
  runs: {
    list: {
      method: 'GET',
      path: '/runs',
      query: [
        { key: 'agentId', label: 'Agent ID' },
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
        {
          key: 'format',
          label: 'Format',
          type: 'select',
          options: [
            { label: 'JSON', value: 'json' },
            { label: 'NDJSON', value: 'ndjson' },
            { label: 'CSV', value: 'csv' },
          ],
        },
      ],
    },
  },
  jobs: {
    list: { method: 'GET', path: '/jobs' },
    detail: { method: 'GET', path: '/jobs/{id}' },
    create: { method: 'POST', path: '/jobs' },
    update: { method: 'PUT', path: '/jobs/{id}' },
    delete: { method: 'DELETE', path: '/jobs/{id}' },
    trigger: { method: 'POST', path: '/jobs/{id}:trigger' },
    pause: { method: 'POST', path: '/jobs/{id}:pause' },
    resume: { method: 'POST', path: '/jobs/{id}:resume' },
    dlq: { method: 'GET', path: '/dlq' },
  },
  rbac: {
    users: { method: 'GET', path: '/users' },
    create: { method: 'POST', path: '/users' },
    detail: { method: 'GET', path: '/users/{id}' },
    delete: { method: 'DELETE', path: '/users/{id}' },
    resetMfa: { method: 'POST', path: '/users/{id}:reset-mfa' },
    updateRole: { method: 'PUT', path: '/users/{id}/role' },
    roles: { method: 'GET', path: '/roles' },
  },
  policies: {
    list: { method: 'GET', path: '/policies' },
    detail: { method: 'GET', path: '/policies/{id}' },
    create: { method: 'POST', path: '/policies' },
    update: { method: 'PUT', path: '/policies/{id}' },
    delete: { method: 'DELETE', path: '/policies/{id}' },
    simulate: { method: 'POST', path: '/policies/{id}:simulate' },
  },
  audit: {
    list: {
      method: 'GET',
      path: '/audit',
      query: [
        { key: 'userId', label: 'User ID' },
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
        {
          key: 'format',
          label: 'Format',
          type: 'select',
          options: [
            { label: 'JSON', value: 'json' },
            { label: 'NDJSON', value: 'ndjson' },
            { label: 'CSV', value: 'csv' },
          ],
        },
      ],
    },
    detail: { method: 'GET', path: '/audit/{id}' },
  },
  settings: {
    list: { method: 'GET', path: '/settings/{group}' },
    update: { method: 'PUT', path: '/settings/{group}' },
  },
  domainPacks: {
    list: { method: 'GET', path: '/domain-packs' },
    install: { method: 'POST', path: '/domain-packs/{name}:install' },
    uninstall: { method: 'POST', path: '/domain-packs/{name}:uninstall' },
  },
} as const;

export type PathsMap = typeof pathsMap;
