import type { components, paths } from './types.gen';

type GetAgentMetricsResponse =
  paths['/agents/{id}/metrics']['get']['responses']['200']['content']['application/json'];
type GetAgentIoResponse =
  paths['/agents/{id}/io']['get']['responses']['200']['content']['application/json'];
type GetErrorsRecentResponse =
  paths['/errors/recent']['get']['responses']['200']['content']['application/json'];
type GetFlowValidateResponse =
  paths['/flows/{id}:validate']['post']['responses']['200']['content']['application/json'];
type GetFlowLogResponse =
  paths['/flows/{id}/log']['get']['responses']['200']['content']['application/json'];
type GetConnectorTestResponse =
  paths['/connectors/{id}:test']['post']['responses']['200']['content']['application/json'];
type GetConnectorProbeResponse =
  paths['/connectors/{id}:probe']['post']['responses']['200']['content']['application/json'];
type GetSecretsRotateResponse =
  paths['/secrets/{id}:rotate']['post']['responses']['200']['content']['application/json'];
type GetJobsTriggerResponse =
  paths['/jobs/{id}:trigger']['post']['responses']['202']['content']['application/json'];
type GetPoliciesSimulateResponse =
  paths['/policies/{id}:simulate']['post']['responses']['200']['content']['application/json'];
type GetSettingsResponse =
  paths['/settings/{group}']['get']['responses']['200']['content']['application/json'];
type GetIntentGraphResponse =
  paths['/intents/graph']['get']['responses']['200']['content']['application/json'];
type DatasetReindexSchema =
  paths['/datasets/{id}:reindex']['post']['responses']['202']['content']['application/json'];
type AgentTestSchema =
  paths['/agents/{id}:test']['post']['responses']['200']['content']['application/json'];

type FlowUpdateSchema = components['schemas']['FlowUpdateRequest'];

type WithRecord<T, K extends PropertyKey> = Omit<T, Extract<K, keyof T>> & {
  [P in K]?: Record<string, unknown>;
};

type FlowLogResponseItem =
  GetFlowLogResponse extends Array<infer Item> ? Item : Record<string, unknown>;

export type FlowCreateRequest = components['schemas']['FlowCreateRequest'];
export type FlowUpdateRequest = FlowUpdateSchema extends Record<string, unknown>
  ? FlowUpdateSchema
  : { name?: string; status?: Flow['status']; config_yaml: string };
export type ProblemDetail = components['schemas']['ProblemDetail'];
export type HealthStatus = components['schemas']['HealthStatus'];
export type UsageMetrics = components['schemas']['UsageMetrics'];

type AgentBase = components['schemas']['Agent'];
export type Agent = WithRecord<AgentBase, 'config'>;

type AgentConfigBase = components['schemas']['AgentConfigRequest'];
export type AgentConfigRequest = WithRecord<AgentConfigBase, 'config'>;

export type AgentMetrics = Required<GetAgentMetricsResponse>;
export type AgentIoMessage = GetAgentIoResponse[number];

export type Flow = components['schemas']['Flow'];
export type FlowList = Flow[];
export type FlowValidation = Required<GetFlowValidateResponse>;
export type FlowDryRunStep = {
  name?: string;
  status?: string;
  output?: Record<string, unknown>;
};
export type FlowDryRunResult = {
  steps?: FlowDryRunStep[];
};
export type FlowLogEntry = FlowLogResponseItem extends Record<string, unknown>
  ? FlowLogResponseItem & {
      timestamp?: string;
      level?: string;
      message?: string;
    }
  : {
      timestamp?: string;
      level?: string;
      message?: string;
    };

export type Dataset = components['schemas']['Dataset'];
export type DatasetSchema = Record<string, unknown>;
export type DatasetEmbedding = components['schemas']['EmbeddingMetadata'];
export type DatasetCreateRequest = components['schemas']['DatasetCreateRequest'];

type ConnectorBase = components['schemas']['Connector'];
export type Connector = ConnectorBase & { status?: string };

export type ConnectorConfigRequest = WithRecord<components['schemas']['ConnectorConfigRequest'], 'config'>;
export type ConnectorTestResult = Required<GetConnectorTestResponse>;
export type ConnectorProbeResult = Required<GetConnectorProbeResponse>;

type SecretBase = components['schemas']['SecretMetadata'];
export type Secret = SecretBase & { created_at?: string };
export type SecretCreateRequest = components['schemas']['SecretCreateRequest'];
export type SecretRotationResult = Required<GetSecretsRotateResponse>;

export type DatasetReindexResponse = Required<DatasetReindexSchema> & { job_id?: string };

type RunBase = components['schemas']['Run'];
export type Run = RunBase & {
  created_at?: string;
  completed_at?: string;
};

export interface RunStreamEvent {
  type: 'start' | 'update' | 'complete' | 'error';
  data: Run;
  timestamp?: string;
}

export interface StreamParams {
  agentId?: string;
  status?: Run['status'];
}

export interface StreamHandlers {
  onOpen?: () => void;
  onMessage?: (event: RunStreamEvent) => void;
  onError?: (error: Event) => void;
  onClose?: () => void;
}

type JobBase = components['schemas']['Job'];
export type Job = WithRecord<JobBase, 'task_definition'>;

type JobCreateBase = components['schemas']['JobCreateRequest'];
export type JobCreateRequest = WithRecord<JobCreateBase, 'task_definition'>;

type DlqBase = components['schemas']['DLQItem'];
export type DlqItem = WithRecord<DlqBase, 'original_message'>;

export type User = components['schemas']['User'];
export type UserCreateRequest = components['schemas']['UserCreateRequest'];
export type Policy = components['schemas']['Policy'];
export type PolicyCreateRequest = components['schemas']['PolicyCreateRequest'];
export type PolicySimulationResult = Required<GetPoliciesSimulateResponse>;
export type PolicySimulationRequest = components['schemas']['PolicySimulationRequest'];
export type AuditEntry = components['schemas']['AuditEntry'];

type SettingBase = components['schemas']['Setting'];
export type Setting = WithRecord<SettingBase, 'value'> & { group?: string; key?: string };

export type IntentGraph = Required<GetIntentGraphResponse>;
export type DomainPack = components['schemas']['DomainPack'];
export type RecentError = GetErrorsRecentResponse[number];
export type SettingsResponse = GetSettingsResponse extends Array<Setting> ? Setting[] : Setting[];
export type ErrorResponse = ProblemDetail;
export type JobTriggerResult = Required<GetJobsTriggerResponse>;
export type AgentTestResult = Required<AgentTestSchema>;
