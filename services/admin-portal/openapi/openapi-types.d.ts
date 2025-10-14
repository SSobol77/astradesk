/* eslint-disable @typescript-eslint/no-empty-interface */
/**
 * This file is generated from openapi/OpenAPI.yaml.
 * Run `npm run openapi:gen` after updating the specification.
 */

export type AgentEnvironment = 'draft' | 'dev' | 'staging' | 'prod';
export type AgentStatus = 'inactive' | 'active' | 'degraded' | 'error' | string;

export interface Agent {
  id: string;
  name: string;
  version: string;
  env: AgentEnvironment;
  status: AgentStatus;
  description?: string;
  updatedAt?: string;
}

export interface AgentMetrics {
  latencyP95Ms?: number;
  latencyP99Ms?: number;
  tokensPerMinute?: number;
}

export interface AgentIoMessage {
  timestamp: string;
  role: 'user' | 'assistant' | string;
  content: string;
}

export interface Flow {
  id: string;
  name: string;
  yaml: string;
}

export interface FlowValidation {
  valid: boolean;
  errors?: string[];
}

export interface FlowDryRunResult {
  steps: Array<{
    name: string;
    status: 'success' | 'skipped' | 'failed';
    output?: unknown;
  }>;
}

export interface Dataset {
  id: string;
  name: string;
  type: 's3' | 'postgres' | 'git' | string;
  indexing_status: 'pending' | 'running' | 'idle' | 'failed' | string;
}

export interface DatasetSchema {
  fields: Array<{
    name: string;
    type: string;
    nullable?: boolean;
  }>;
}

export interface DatasetEmbedding {
  vectorId: string;
  dimension: number;
  metadata?: Record<string, unknown>;
}

export interface Connector {
  id: string;
  name: string;
  type: string;
  status?: string;
}

export interface ConnectorProbeResult {
  latency_ms: number;
  reachable: boolean;
}

export interface Secret {
  id: string;
  name: string;
  type: string;
  last_used_at?: string;
  created_at?: string;
  status?: 'active' | 'disabled' | string;
}

export interface Run {
  id: string;
  agent_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | string;
  latency_ms?: number;
  cost_usd?: number;
  created_at?: string;
  completed_at?: string;
}

export interface RunStreamEvent extends Run {}

export interface Job {
  id: string;
  name: string;
  schedule_expr: string;
  status: 'active' | 'paused' | string;
  last_run_at?: string;
  next_run_at?: string;
}

export interface DlqItem {
  id: string;
  job_id: string;
  failure_reason: string;
  created_at: string;
}

export interface User {
  id: string;
  email: string;
  role: 'admin' | 'operator' | 'viewer';
  status?: string;
  last_active_at?: string;
}

export interface Role {
  id: string;
  name: string;
  description?: string;
}

export interface Policy {
  id: string;
  name: string;
  description?: string;
  raw?: string;
}

export interface PolicySimulationResult {
  allow: boolean;
  violations?: string[];
}

export interface AuditEntry {
  id: string;
  user_id: string;
  action: string;
  resource: string;
  when_ts: string;
  signature?: string;
  metadata?: Record<string, unknown>;
}

export interface UsageMetrics {
  total_requests: number;
  cost_usd: number;
  latency_p95_ms: number;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'down';
  components: Array<{
    name: string;
    status: 'healthy' | 'degraded' | 'down';
    message?: string;
  }>;
}

export interface ErrorsRecentResponse {
  errors: string[];
}

export interface ErrorResponse {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  instance?: string;
  [key: string]: unknown;
}

export interface SettingsGroup {
  group: string;
  key: string;
  value: Record<string, unknown>;
}

export interface IntentGraph {
  nodes: Array<{ id: string; label: string }>;
  edges: Array<{ from: string; to: string; label?: string }>;
}

export interface RunsFilters {
  agent?: string;
  intent?: string;
  status?: string;
  from?: string;
  to?: string;
}

export interface AuditFilters {
  user?: string;
  action?: string;
  resource?: string;
  from?: string;
  to?: string;
}

export interface LogsExportFormat {
  format: 'json' | 'ndjson';
}

export interface AuditExportFormat {
  format: 'json' | 'ndjson';
}

export type Paths = typeof import('./paths-map')['pathsMap'];
