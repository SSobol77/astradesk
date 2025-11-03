import { assertSpecOperation } from '@/api/spec-operations.gen';

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

const createOperation = (
  tag: string,
  method: HttpMethod,
  path: string,
  descriptor: Omit<OperationDescriptor, 'method' | 'path'> = {},
): OperationDescriptor => {
  assertSpecOperation(tag, method, path);
  return { method, path, ...descriptor };
};

export const pathsMap = {
  dashboard: {
    health: createOperation('Dashboard', 'GET', '/health'),
    usage: createOperation('Dashboard', 'GET', '/usage/llm'),
    errorsRecent: createOperation('Dashboard', 'GET', '/errors/recent', {
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
    }),
  },
  agents: {
    list: createOperation('Agents', 'GET', '/agents'),
    detail: createOperation('Agents', 'GET', '/agents/{id}'),
    create: createOperation('Agents', 'POST', '/agents'),
    update: createOperation('Agents', 'PUT', '/agents/{id}'),
    delete: createOperation('Agents', 'DELETE', '/agents/{id}'),
    test: createOperation('Agents', 'POST', '/agents/{id}:test'),
    clone: createOperation('Agents', 'POST', '/agents/{id}:clone'),
    promote: createOperation('Agents', 'POST', '/agents/{id}:promote'),
    metrics: createOperation('Agents', 'GET', '/agents/{id}/metrics', {
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
    }),
    io: createOperation('Agents', 'GET', '/agents/{id}/io', {
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
    }),
  },
  intentGraph: {
    graph: createOperation('Intent Graph', 'GET', '/intents/graph'),
  },
  flows: {
    list: createOperation('Flows', 'GET', '/flows', {
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
    }),
    detail: createOperation('Flows', 'GET', '/flows/{id}'),
    create: createOperation('Flows', 'POST', '/flows'),
    update: createOperation('Flows', 'PUT', '/flows/{id}'),
    delete: createOperation('Flows', 'DELETE', '/flows/{id}'),
    validate: createOperation('Flows', 'POST', '/flows/{id}:validate'),
    dryRun: createOperation('Flows', 'POST', '/flows/{id}:dryrun'),
    log: createOperation('Flows', 'GET', '/flows/{id}/log', {
      query: [
        { key: 'limit', label: 'Limit' },
        { key: 'offset', label: 'Offset' },
      ],
    }),
  },
  datasets: {
    list: createOperation('Datasets', 'GET', '/datasets'),
    detail: createOperation('Datasets', 'GET', '/datasets/{id}'),
    create: createOperation('Datasets', 'POST', '/datasets'),
    delete: createOperation('Datasets', 'DELETE', '/datasets/{id}'),
    reindex: createOperation('Datasets', 'POST', '/datasets/{id}:reindex'),
    schema: createOperation('Datasets', 'GET', '/datasets/{id}/schema'),
    embeddings: createOperation('Datasets', 'GET', '/datasets/{id}/embeddings', {
      query: [
        { key: 'limit', label: 'Limit' },
        { key: 'offset', label: 'Offset' },
      ],
    }),
  },
  tools: {
    list: createOperation('Tools/Connectors', 'GET', '/connectors'),
    detail: createOperation('Tools/Connectors', 'GET', '/connectors/{id}'),
    create: createOperation('Tools/Connectors', 'POST', '/connectors'),
    update: createOperation('Tools/Connectors', 'PUT', '/connectors/{id}'),
    delete: createOperation('Tools/Connectors', 'DELETE', '/connectors/{id}'),
    test: createOperation('Tools/Connectors', 'POST', '/connectors/{id}:test'),
    probe: createOperation('Tools/Connectors', 'POST', '/connectors/{id}:probe'),
  },
  secrets: {
    list: createOperation('Keys & Secrets', 'GET', '/secrets'),
    create: createOperation('Keys & Secrets', 'POST', '/secrets'),
    rotate: createOperation('Keys & Secrets', 'POST', '/secrets/{id}:rotate'),
    disable: createOperation('Keys & Secrets', 'DELETE', '/secrets/{id}:disable'),
  },
  runs: {
    list: createOperation('Runs & Logs', 'GET', '/runs', {
      query: [
        { key: 'agentId', label: 'Agent ID' },
        { key: 'status', label: 'Status' },
        { key: 'from', label: 'From', type: 'date' },
        { key: 'to', label: 'To', type: 'date' },
      ],
    }),
    stream: createOperation('Runs & Logs', 'GET', '/runs/stream'),
    detail: createOperation('Runs & Logs', 'GET', '/runs/{id}'),
    exportLogs: createOperation('Runs & Logs', 'GET', '/logs/export', {
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
    }),
  },
  jobs: {
    list: createOperation('Jobs & Schedules', 'GET', '/jobs'),
    detail: createOperation('Jobs & Schedules', 'GET', '/jobs/{id}'),
    create: createOperation('Jobs & Schedules', 'POST', '/jobs'),
    update: createOperation('Jobs & Schedules', 'PUT', '/jobs/{id}'),
    delete: createOperation('Jobs & Schedules', 'DELETE', '/jobs/{id}'),
    trigger: createOperation('Jobs & Schedules', 'POST', '/jobs/{id}:trigger'),
    pause: createOperation('Jobs & Schedules', 'POST', '/jobs/{id}:pause'),
    resume: createOperation('Jobs & Schedules', 'POST', '/jobs/{id}:resume'),
    dlq: createOperation('Jobs & Schedules', 'GET', '/dlq'),
  },
  rbac: {
    users: createOperation('Users & Roles', 'GET', '/users'),
    create: createOperation('Users & Roles', 'POST', '/users'),
    detail: createOperation('Users & Roles', 'GET', '/users/{id}'),
    delete: createOperation('Users & Roles', 'DELETE', '/users/{id}'),
    resetMfa: createOperation('Users & Roles', 'POST', '/users/{id}:reset-mfa'),
    updateRole: createOperation('Users & Roles', 'PUT', '/users/{id}/role'),
    roles: createOperation('Users & Roles', 'GET', '/roles'),
  },
  policies: {
    list: createOperation('Policies', 'GET', '/policies'),
    detail: createOperation('Policies', 'GET', '/policies/{id}'),
    create: createOperation('Policies', 'POST', '/policies'),
    update: createOperation('Policies', 'PUT', '/policies/{id}'),
    delete: createOperation('Policies', 'DELETE', '/policies/{id}'),
    simulate: createOperation('Policies', 'POST', '/policies/{id}:simulate'),
  },
  audit: {
    list: createOperation('Audit Trail', 'GET', '/audit', {
      query: [
        { key: 'userId', label: 'User ID' },
        { key: 'action', label: 'Action' },
        { key: 'resource', label: 'Resource' },
        { key: 'from', label: 'From', type: 'date' },
        { key: 'to', label: 'To', type: 'date' },
      ],
    }),
    get: createOperation('Audit Trail', 'GET', '/audit/{id}'),
    exportData: createOperation('Audit Trail', 'GET', '/audit/export', {
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
    }),
  },
  settings: {
    list: createOperation('Settings', 'GET', '/settings/{group}'),
    update: createOperation('Settings', 'PUT', '/settings/{group}'),
  },
  domainPacks: {
    list: createOperation('Domain Packs', 'GET', '/domain-packs'),
    install: createOperation('Domain Packs', 'POST', '/domain-packs/{name}:install'),
    uninstall: createOperation('Domain Packs', 'POST', '/domain-packs/{name}:uninstall'),
  },
} as const;

export type PathsMap = typeof pathsMap;
