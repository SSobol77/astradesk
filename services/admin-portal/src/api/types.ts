import type { components, paths } from './types.gen';

type GetAgentMetricsResponse =
  paths['/agents/{id}/metrics']['get']['responses']['200']['content']['application/json'];
type GetAgentIoResponse =
  paths['/agents/{id}/io']['get']['responses']['200']['content']['application/json'];
type GetErrorsRecentResponse =
  paths['/errors/recent']['get']['responses']['200']['content']['application/json'];
type GetFlowValidateResponse =
  paths['/flows/{id}:validate']['post']['responses']['200']['content']['application/json'];
type GetFlowDryRunResponse =
  paths['/flows/{id}:dryrun']['post']['responses']['200']['content']['application/json'];
type GetFlowTestResponse =
  paths['/flows/{id}:test']['post']['responses']['200']['content']['application/json'];
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
type GetFlowsResponse =
  paths['/flows']['get']['responses']['200']['content']['application/json'];
type GetIntentGraphResponse =
  paths['/intents/graph']['get']['responses']['200']['content']['application/json'];
type DatasetReindexSchema =
  paths['/datasets/{id}:reindex']['post']['responses']['202']['content']['application/json'];
type AgentTestSchema =
  paths['/agents/{id}:test']['post']['responses']['200']['content']['application/json'];
type FlowGenerateRequestSchema =
  paths['/flows/generate']['post']['requestBody']['content']['application/json'];

type FlowUpdateSchema = components['schemas']['FlowUpdateRequest'];

export type FlowCreateRequest = components['schemas']['FlowCreateRequest'];
export type FlowUpdateRequest = FlowUpdateSchema extends Record<string, unknown>
  ? FlowUpdateSchema
  : { name?: string; status?: Flow['status']; config_yaml: string };
export type FlowGenerationRequest = FlowGenerateRequestSchema extends Record<string, unknown>
  ? FlowGenerateRequestSchema
  : { prompt: string; format?: 'yaml' | 'json' };
export type ProblemDetail = components['schemas']['ProblemDetail'];
export type HealthStatus = components['schemas']['HealthStatus'];
export type UsageMetrics = components['schemas']['UsageMetrics'];
export type Agent = components['schemas']['Agent'];
export type AgentConfigRequest = components['schemas']['AgentConfigRequest'];
export type AgentMetrics = Required<GetAgentMetricsResponse>;
export type AgentIoMessage = GetAgentIoResponse[number];
export type Flow = components['schemas']['Flow'];
export type FlowList = GetFlowsResponse;
export type FlowValidation = Required<GetFlowValidateResponse>;
export type FlowDryRunResult = Required<GetFlowDryRunResponse>;
export type FlowTestResult = Required<GetFlowTestResponse>;
export type Dataset = components['schemas']['Dataset'];
export type DatasetSchema = components['schemas']['DatasetSchema'];
export type DatasetEmbedding = components['schemas']['EmbeddingMetadata'];
export type DatasetCreateRequest = components['schemas']['DatasetCreateRequest'];
export type Connector = components['schemas']['Connector'];
export type ConnectorConfigRequest = components['schemas']['ConnectorConfigRequest'];
export type ConnectorTestResult = Required<GetConnectorTestResponse>;
export type ConnectorProbeResult = Required<GetConnectorProbeResponse>;
export type Secret = components['schemas']['SecretMetadata'];
export type SecretCreateRequest = components['schemas']['SecretCreateRequest'];
export type SecretRotationResult = Required<GetSecretsRotateResponse>;
export type DatasetReindexResponse = Required<DatasetReindexSchema>;
export type Run = components['schemas']['Run'];
export type RunStreamEvent = Run;
export type Job = components['schemas']['Job'];
export type JobCreateRequest = components['schemas']['JobCreateRequest'];
export type DlqItem = components['schemas']['DLQItem'];
export type User = components['schemas']['User'];
export type UserCreateRequest = components['schemas']['UserCreateRequest'];
export type Policy = components['schemas']['Policy'];
export type PolicyCreateRequest = components['schemas']['PolicyCreateRequest'];
export type PolicySimulationResult = Required<GetPoliciesSimulateResponse>;
export type PolicySimulationRequest = components['schemas']['PolicySimulationRequest'];
export type AuditEntry = components['schemas']['AuditEntry'];
export type Setting = components['schemas']['Setting'];
export type IntentGraph = Required<GetIntentGraphResponse>;
export type DomainPack = components['schemas']['DomainPack'];
export type RecentError = GetErrorsRecentResponse[number];
export type SettingsResponse = Required<GetSettingsResponse>;
export type ErrorResponse = ProblemDetail;
export type JobTriggerResult = Required<GetJobsTriggerResponse>;
export type AgentTestResult = Required<AgentTestSchema>;
