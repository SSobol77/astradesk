from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4
from pathlib import Path
import tomllib

from fastapi import FastAPI, HTTPException, Query, Response, status
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, EmailStr, Field


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Pydantic models mirroring the OpenAPI schema ---


class HealthStatus(BaseModel):
    status: Literal["healthy", "degraded", "down"]
    components: Dict[str, str]


class UsageMetrics(BaseModel):
    total_requests: int
    cost_usd: float
    latency_p95_ms: float


class RecentError(BaseModel):
    timestamp: str
    message: str
    trace_id: str


class Agent(BaseModel):
    id: str
    name: str
    version: str
    env: Literal["draft", "dev", "staging", "prod"]
    status: str
    config: Dict[str, Any] = Field(default_factory=dict)


class AgentConfigRequest(BaseModel):
    name: str
    config: Dict[str, Any]


class AgentMetrics(BaseModel):
    p95_latency_ms: float
    p99_latency_ms: float
    request_count: int


class AgentIoMessage(BaseModel):
    timestamp: str
    input: str
    output: str


class GraphNode(BaseModel):
    id: str
    label: str
    type: Literal["intent", "entity", "tool"]


class GraphEdge(BaseModel):
    source: str
    target: str
    label: Optional[str] = None


class IntentGraph(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class Flow(BaseModel):
    id: str
    name: str
    version: str
    status: Literal["active", "draft", "archived"]
    env: Literal["draft", "dev", "staging", "prod"]
    config_yaml: str
    created_at: str
    updated_at: str


class FlowCreateRequest(BaseModel):
    name: str
    graph: Dict[str, Any]


class FlowUpdateRequest(BaseModel):
    name: Optional[str] = None
    status: Optional[Literal["active", "draft", "archived"]] = None
    config_yaml: str


class FlowValidationResult(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)


class FlowDryRunStep(BaseModel):
    name: str
    status: Literal["success", "failure", "skipped"]
    output: Optional[Dict[str, Any]] = None


class FlowDryRunResult(BaseModel):
    steps: List[FlowDryRunStep]


class FlowTestResult(BaseModel):
    status: Literal["success", "failure"]
    logs: List[str]
    output: Dict[str, Any]


class FlowLogEntry(BaseModel):
    timestamp: str
    level: Literal["INFO", "WARN", "ERROR"]
    message: str


class FlowListResponse(BaseModel):
    items: List[Flow]
    total: int
    limit: int
    offset: int


class Dataset(BaseModel):
    id: str
    name: str
    type: Literal["s3", "postgres", "git"]
    indexing_status: str


class DatasetCreateRequest(BaseModel):
    name: str
    type: Literal["s3", "postgres", "git"]


class DatasetField(BaseModel):
    name: str
    type: str
    nullable: Optional[bool] = None


class DatasetSchema(BaseModel):
    fields: List[DatasetField]


class EmbeddingMetadata(BaseModel):
    id: str
    source: str
    created_at: str


class Connector(BaseModel):
    id: str
    name: str
    type: str
    status: Optional[str] = None


class ConnectorConfigRequest(BaseModel):
    name: str
    type: str
    config: Dict[str, Any]


class SecretMetadata(BaseModel):
    id: str
    name: str
    type: Optional[str] = None
    last_used_at: Optional[str] = None
    created_at: Optional[str] = None


class SecretCreateRequest(BaseModel):
    name: str
    value: str
    type: Optional[str] = None


class Run(BaseModel):
    id: str
    agent_id: str
    status: str
    latency_ms: Optional[float] = None
    cost_usd: Optional[float] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class Job(BaseModel):
    id: str
    name: str
    schedule_expr: str
    status: str
    task_definition: Optional[Dict[str, Any]] = None


class JobCreateRequest(BaseModel):
    name: str
    schedule_expr: str
    task_definition: Dict[str, Any]


class DLQItem(BaseModel):
    id: str
    original_message: Dict[str, Any]
    error_message: str
    failed_at: str


class User(BaseModel):
    id: str
    email: EmailStr
    role: Literal["admin", "operator", "viewer"]


class UserCreateRequest(BaseModel):
    email: EmailStr
    role: Literal["admin", "operator", "viewer"]


class UserRoleUpdateRequest(BaseModel):
    role: Literal["admin", "operator", "viewer"]


class Policy(BaseModel):
    id: str
    name: str
    rego_text: str


class PolicyCreateRequest(BaseModel):
    name: str
    rego_text: str


class PolicySimulationRequest(BaseModel):
    input: Dict[str, Any]


class PolicySimulationResult(BaseModel):
    allow: bool
    violations: List[str] = Field(default_factory=list)


class AuditEntry(BaseModel):
    id: str
    when_ts: str
    user_id: str
    action: str
    resource: str
    signature: Optional[str] = None


class Setting(BaseModel):
    group: str
    key: str
    value: Dict[str, Any]


class SettingUpdateRequest(BaseModel):
    key: str
    value: Dict[str, Any]


class DomainPack(BaseModel):
    name: str
    version: str
    status: Literal["installed", "error", "disabled"]


class FlowGenerationRequest(BaseModel):
    prompt: str
    format: Literal["yaml", "json"] = "yaml"


# --- In-memory store with sample data ---


class DataStore:
    def __init__(self) -> None:
        self.health = HealthStatus(
            status="healthy",
            components={
                "database": "healthy",
                "vector_store": "healthy",
                "cache": "degraded",
            },
        )
        self.usage = UsageMetrics(total_requests=18452, cost_usd=128.37, latency_p95_ms=932.4)
        self.recent_errors: List[RecentError] = [
            RecentError(timestamp=iso_now(), message="Connector timeout: zendesk", trace_id=str(uuid4())),
            RecentError(timestamp=iso_now(), message="Flow dry run failure", trace_id=str(uuid4())),
        ]

        agent_id = str(uuid4())
        self.agents: Dict[str, Agent] = {
            agent_id: Agent(
                id=agent_id,
                name="Support Triage Agent",
                version="1.4.2",
                env="prod",
                status="active",
                config={"model": "gpt-4o-mini", "temperature": 0.2},
            )
        }
        self.agent_metrics: Dict[str, AgentMetrics] = {
            agent_id: AgentMetrics(p95_latency_ms=842.0, p99_latency_ms=1220.0, request_count=1421)
        }
        self.agent_io: Dict[str, List[AgentIoMessage]] = {
            agent_id: [
                AgentIoMessage(
                    timestamp=iso_now(),
                    input="How do I rotate the API key?",
                    output="Go to Settings → Keys & Secrets, select the key, and click Rotate.",
                )
            ]
        }

        self.intent_graph = IntentGraph(
            nodes=[
                GraphNode(id="intent-reset", label="Reset password", type="intent"),
                GraphNode(id="tool-zendesk", label="Zendesk", type="tool"),
            ],
            edges=[GraphEdge(source="intent-reset", target="tool-zendesk", label="uses")],
        )

        flow_id = str(uuid4())
        self.flows: Dict[str, Flow] = {
            flow_id: Flow(
                id=flow_id,
                name="Daily Reporting",
                version="1.0.0",
                status="active",
                env="prod",
                config_yaml="steps:\n  - id: export\n    action: export_daily_metrics\n  - id: email\n    action: email_summary\n",
                created_at=iso_now(),
                updated_at=iso_now(),
            )
        }
        self.flow_logs: Dict[str, List[FlowLogEntry]] = {
            flow_id: [
                FlowLogEntry(timestamp=iso_now(), level="INFO", message="Flow execution started"),
                FlowLogEntry(timestamp=iso_now(), level="INFO", message="Step export completed"),
            ]
        }

        dataset_id = str(uuid4())
        self.datasets: Dict[str, Dataset] = {
            dataset_id: Dataset(id=dataset_id, name="Knowledge Base", type="git", indexing_status="indexed")
        }
        self.dataset_schemas: Dict[str, DatasetSchema] = {
            dataset_id: DatasetSchema(
                fields=[
                    DatasetField(name="id", type="string"),
                    DatasetField(name="title", type="string"),
                    DatasetField(name="body", type="text", nullable=True),
                ]
            )
        }
        self.dataset_embeddings: Dict[str, List[EmbeddingMetadata]] = {
            dataset_id: [
                EmbeddingMetadata(id=str(uuid4()), source="knowledge/customers.md", created_at=iso_now())
            ]
        }

        connector_id = str(uuid4())
        self.connectors: Dict[str, Connector] = {
            connector_id: Connector(id=connector_id, name="Zendesk", type="zendesk", status="healthy")
        }

        secret_id = str(uuid4())
        self.secrets: Dict[str, SecretMetadata] = {
            secret_id: SecretMetadata(
                id=secret_id,
                name="openai-api-key",
                type="api-key",
                last_used_at=iso_now(),
                created_at=iso_now(),
            )
        }

        run_id = str(uuid4())
        self.runs: Dict[str, Run] = {
            run_id: Run(
                id=run_id,
                agent_id=agent_id,
                status="completed",
                latency_ms=834.0,
                cost_usd=0.013,
                created_at=iso_now(),
                completed_at=iso_now(),
            )
        }

        job_id = str(uuid4())
        self.jobs: Dict[str, Job] = {
            job_id: Job(
                id=job_id,
                name="Nightly reindex",
                schedule_expr="0 2 * * *",
                status="active",
                task_definition={"type": "dataset-reindex", "dataset_id": dataset_id},
            )
        }

        self.dlq_items: Dict[str, DLQItem] = {
            str(uuid4()): DLQItem(
                id=str(uuid4()),
                original_message={"job_id": job_id},
                error_message="Temporary SMTP failure",
                failed_at=iso_now(),
            )
        }

        user_id = str(uuid4())
        self.users: Dict[str, User] = {
            user_id: User(id=user_id, email="admin@astradesk.com", role="admin")
        }

        policy_id = str(uuid4())
        self.policies: Dict[str, Policy] = {
            policy_id: Policy(id=policy_id, name="Support Analysts", rego_text='package astradesk.authz\nallow = true')
        }

        audit_id = str(uuid4())
        self.audit_entries: Dict[str, AuditEntry] = {
            audit_id: AuditEntry(
                id=audit_id,
                when_ts=iso_now(),
                user_id=user_id,
                action="secret.rotate",
                resource=f"secret:{secret_id}",
                signature="simulation-signature",
            )
        }

        self.settings: Dict[str, Dict[str, Setting]] = {
            "platform": {
                "timezone": Setting(group="platform", key="timezone", value={"tz": "UTC"}),
                "release_channel": Setting(group="platform", key="release_channel", value={"channel": "stable"}),
            },
            "integrations": {
                "zendesk": Setting(group="integrations", key="zendesk", value={"subdomain": "astradesk"}),
            },
            "localization": {
                "default_locale": Setting(group="localization", key="default_locale", value={"locale": "en-US"}),
            },
        }

        self.domain_packs: List[DomainPack] = self._load_domain_packs()

    def _load_domain_packs(self) -> List[DomainPack]:
        """Discover local domain packs from the monorepo workspace."""
        repo_root = Path(__file__).resolve().parents[2]

        packages_dir = repo_root / "packages"
        if not packages_dir.is_dir():
            return []

        domain_packs: List[DomainPack] = []
        for candidate in sorted(packages_dir.glob("domain-*")):
            if not candidate.is_dir():
                continue

            pyproject = candidate / "pyproject.toml"
            version = "0.0.0"
            if pyproject.is_file():
                try:
                    with pyproject.open("rb") as fh:
                        data = tomllib.load(fh)
                    version = data.get("project", {}).get("version", version)
                except Exception:
                    pass

            domain_packs.append(
                DomainPack(
                    name=candidate.name,
                    version=version,
                    status="installed",
                )
            )

        return domain_packs


store = DataStore()


# --- FastAPI application ---

app = FastAPI(
    title="AstraDesk Admin API",
    description="API for AstraDesk Admin v1.2 - operational and governance panel for agents, data, policies, and audits.",
    version="0.3.0",
    root_path="/api/admin/v1",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)


# --- Dashboard endpoints ---


@app.get("/health", response_model=HealthStatus, tags=["Dashboard"])
async def get_health() -> HealthStatus:
    return store.health


@app.get("/usage/llm", response_model=UsageMetrics, tags=["Dashboard"])
async def get_usage() -> UsageMetrics:
    return store.usage


@app.get("/errors/recent", response_model=List[RecentError], tags=["Dashboard"])
async def get_recent_errors(limit: int = 25, offset: int = 0) -> List[RecentError]:
    return store.recent_errors[offset : offset + limit]


# --- Agent endpoints ---


@app.get("/agents", response_model=List[Agent], tags=["Agents"])
async def list_agents(limit: int = 25, offset: int = 0) -> List[Agent]:
    agents = list(store.agents.values())
    return agents[offset : offset + limit]


@app.post("/agents", response_model=Agent, status_code=status.HTTP_201_CREATED, tags=["Agents"])
async def create_agent(payload: AgentConfigRequest) -> Agent:
    agent_id = str(uuid4())
    agent = Agent(
        id=agent_id,
        name=payload.name,
        version="1.0.0",
        env="draft",
        status="inactive",
        config=payload.config,
    )
    store.agents[agent_id] = agent
    store.agent_metrics[agent_id] = AgentMetrics(p95_latency_ms=0.0, p99_latency_ms=0.0, request_count=0)
    store.agent_io[agent_id] = []
    return agent


def _get_agent_or_404(agent_id: str) -> Agent:
    agent = store.agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


@app.get("/agents/{agent_id}", response_model=Agent, tags=["Agents"])
async def get_agent(agent_id: str) -> Agent:
    return _get_agent_or_404(agent_id)


@app.put("/agents/{agent_id}", response_model=Agent, tags=["Agents"])
async def update_agent(agent_id: str, payload: AgentConfigRequest) -> Agent:
    agent = _get_agent_or_404(agent_id)
    updated = agent.model_copy(update={"name": payload.name, "config": payload.config, "status": "active"})
    updated.config = payload.config
    updated.status = "active"
    store.agents[agent_id] = updated
    return updated


@app.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Agents"])
async def delete_agent(agent_id: str) -> Response:
    if agent_id not in store.agents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    store.agents.pop(agent_id)
    store.agent_metrics.pop(agent_id, None)
    store.agent_io.pop(agent_id, None)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/agents/{agent_id}:test", tags=["Agents"])
async def test_agent(agent_id: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    _get_agent_or_404(agent_id)
    return {
        "status": "success",
        "output": {"echo": payload or {"message": "Test executed"}},
        "logs": ["Agent test executed successfully."],
    }


@app.post("/agents/{agent_id}:clone", response_model=Agent, tags=["Agents"])
async def clone_agent(agent_id: str) -> Agent:
    agent = _get_agent_or_404(agent_id)
    clone_id = str(uuid4())
    clone = agent.model_copy(update={"id": clone_id, "name": f"{agent.name} (clone)", "env": "dev"})
    store.agents[clone_id] = clone
    store.agent_metrics[clone_id] = store.agent_metrics.get(agent_id, AgentMetrics(p95_latency_ms=0, p99_latency_ms=0, request_count=0))
    store.agent_io[clone_id] = store.agent_io.get(agent_id, []).copy()
    return clone


@app.post("/agents/{agent_id}:promote", response_model=Agent, tags=["Agents"])
async def promote_agent(agent_id: str) -> Agent:
    agent = _get_agent_or_404(agent_id)
    promoted = agent.model_copy(update={"env": "prod", "status": "active"})
    store.agents[agent_id] = promoted
    return promoted


@app.get("/agents/{agent_id}/metrics", response_model=AgentMetrics, tags=["Agents"])
async def get_agent_metrics(agent_id: str, timeWindow: Optional[str] = None) -> AgentMetrics:  # noqa: N803
    _get_agent_or_404(agent_id)
    metrics = store.agent_metrics.get(agent_id)
    if not metrics:
        metrics = AgentMetrics(p95_latency_ms=0.0, p99_latency_ms=0.0, request_count=0)
    return metrics


@app.get("/agents/{agent_id}/io", response_model=List[AgentIoMessage], tags=["Agents"])
async def get_agent_io(agent_id: str, limit: int = 25, offset: int = 0) -> List[AgentIoMessage]:
    _get_agent_or_404(agent_id)
    messages = store.agent_io.get(agent_id, [])
    return messages[offset : offset + limit]


# --- Intent graph ---


@app.get("/intents/graph", response_model=IntentGraph, tags=["Intent Graph"])
async def get_intent_graph() -> IntentGraph:
    return store.intent_graph


# --- Flow endpoints ---


def _get_flow_or_404(flow_id: str) -> Flow:
    flow = store.flows.get(flow_id)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found")
    return flow


@app.get("/flows", response_model=FlowListResponse, tags=["Flows"])
async def list_flows(
    limit: int = 25,
    offset: int = 0,
    status: Optional[Literal["active", "draft", "archived"]] = None,
    env: Optional[Literal["draft", "dev", "staging", "prod"]] = None,
) -> FlowListResponse:
    items = list(store.flows.values())
    if status:
        items = [flow for flow in items if flow.status == status]
    if env:
        items = [flow for flow in items if flow.env == env]
    total = len(items)
    sliced = items[offset : offset + limit]
    return FlowListResponse(items=sliced, total=total, limit=limit, offset=offset)


@app.post("/flows", response_model=Flow, status_code=status.HTTP_201_CREATED, tags=["Flows"])
async def create_flow(payload: FlowCreateRequest) -> Flow:
    flow_id = str(uuid4())
    config_yaml = json.dumps(payload.graph, indent=2)
    flow = Flow(
        id=flow_id,
        name=payload.name,
        version="1.0.0",
        status="draft",
        env="draft",
        config_yaml=config_yaml,
        created_at=iso_now(),
        updated_at=iso_now(),
    )
    store.flows[flow_id] = flow
    store.flow_logs[flow_id] = []
    return flow


@app.get("/flows/{flow_id}", response_model=Flow, tags=["Flows"])
async def get_flow(flow_id: str) -> Flow:
    return _get_flow_or_404(flow_id)


@app.put("/flows/{flow_id}", response_model=Flow, tags=["Flows"])
async def update_flow(flow_id: str, payload: FlowUpdateRequest) -> Flow:
    flow = _get_flow_or_404(flow_id)
    updated = flow.model_copy(
        update={
            "name": payload.name or flow.name,
            "status": payload.status or flow.status,
            "config_yaml": payload.config_yaml,
            "updated_at": iso_now(),
        }
    )
    store.flows[flow_id] = updated
    return updated


@app.delete("/flows/{flow_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Flows"])
async def delete_flow(flow_id: str) -> Response:
    if flow_id not in store.flows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found")
    store.flows.pop(flow_id)
    store.flow_logs.pop(flow_id, None)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/flows/{flow_id}:validate", response_model=FlowValidationResult, tags=["Flows"])
async def validate_flow(flow_id: str) -> FlowValidationResult:
    _get_flow_or_404(flow_id)
    return FlowValidationResult(valid=True, errors=[])


@app.post("/flows/{flow_id}:dryrun", response_model=FlowDryRunResult, tags=["Flows"])
async def dry_run_flow(flow_id: str) -> FlowDryRunResult:
    _get_flow_or_404(flow_id)
    steps = [
        FlowDryRunStep(name="export", status="success", output={"records": 128}),
        FlowDryRunStep(name="email", status="success", output={"recipients": 12}),
    ]
    return FlowDryRunResult(steps=steps)


@app.post("/flows/{flow_id}:test", response_model=FlowTestResult, tags=["Flows"])
async def test_flow(flow_id: str, payload: Optional[Dict[str, Any]] = None) -> FlowTestResult:
    _get_flow_or_404(flow_id)
    return FlowTestResult(
        status="success",
        logs=["Flow executed in simulation mode.", "All steps completed successfully."],
        output=payload or {"result": "ok"},
    )


@app.get("/flows/{flow_id}/log", response_model=List[FlowLogEntry], tags=["Flows"])
async def get_flow_log(flow_id: str, limit: int = 25, offset: int = 0) -> List[FlowLogEntry]:
    _get_flow_or_404(flow_id)
    logs = store.flow_logs.get(flow_id, [])
    return logs[offset : offset + limit]


@app.post("/flows/generate", tags=["Flows"])
async def generate_flow(payload: FlowGenerationRequest) -> PlainTextResponse:
    generated = {
        "flow": {
            "name": payload.prompt.lower().replace(" ", "_")[:32],
            "steps": ["draft_step_1", "draft_step_2"],
        }
    }
    if payload.format == "json":
        body = json.dumps(generated, indent=2)
        media_type = "application/json"
    else:
        body = f"flow:\n  name: {generated['flow']['name']}\n  steps:\n    - {generated['flow']['steps'][0]}\n    - {generated['flow']['steps'][1]}\n"
        media_type = "application/yaml"
    return PlainTextResponse(content=body, media_type=media_type)


# --- Dataset endpoints ---


def _get_dataset_or_404(dataset_id: str) -> Dataset:
    dataset = store.datasets.get(dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return dataset


@app.get("/datasets", response_model=List[Dataset], tags=["Datasets"])
async def list_datasets(limit: int = 25, offset: int = 0) -> List[Dataset]:
    datasets = list(store.datasets.values())
    return datasets[offset : offset + limit]


@app.post("/datasets", response_model=Dataset, status_code=status.HTTP_201_CREATED, tags=["Datasets"])
async def create_dataset(payload: DatasetCreateRequest) -> Dataset:
    dataset_id = str(uuid4())
    dataset = Dataset(
        id=dataset_id, name=payload.name, type=payload.type, indexing_status="pending"
    )
    store.datasets[dataset_id] = dataset
    store.dataset_schemas[dataset_id] = DatasetSchema(fields=[])
    store.dataset_embeddings[dataset_id] = []
    return dataset


@app.get("/datasets/{dataset_id}", response_model=Dataset, tags=["Datasets"])
async def get_dataset(dataset_id: str) -> Dataset:
    return _get_dataset_or_404(dataset_id)


@app.delete("/datasets/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Datasets"])
async def delete_dataset(dataset_id: str) -> Response:
    if dataset_id not in store.datasets:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    store.datasets.pop(dataset_id)
    store.dataset_schemas.pop(dataset_id, None)
    store.dataset_embeddings.pop(dataset_id, None)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/datasets/{dataset_id}/schema", response_model=DatasetSchema, tags=["Datasets"])
async def get_dataset_schema(dataset_id: str) -> DatasetSchema:
    _get_dataset_or_404(dataset_id)
    schema = store.dataset_schemas.get(dataset_id)
    if not schema:
        schema = DatasetSchema(fields=[])
    return schema


@app.get("/datasets/{dataset_id}/embeddings", response_model=List[EmbeddingMetadata], tags=["Datasets"])
async def get_dataset_embeddings(dataset_id: str, limit: int = 25, offset: int = 0) -> List[EmbeddingMetadata]:
    _get_dataset_or_404(dataset_id)
    embeddings = store.dataset_embeddings.get(dataset_id, [])
    return embeddings[offset : offset + limit]


@app.post("/datasets/{dataset_id}:reindex", status_code=status.HTTP_202_ACCEPTED, tags=["Datasets"])
async def reindex_dataset(dataset_id: str) -> Dict[str, str]:
    _get_dataset_or_404(dataset_id)
    return {"job_id": str(uuid4())}


# --- Connector endpoints ---


def _get_connector_or_404(connector_id: str) -> Connector:
    connector = store.connectors.get(connector_id)
    if not connector:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found")
    return connector


@app.get("/connectors", response_model=List[Connector], tags=["Tools/Connectors"])
async def list_connectors(limit: int = 25, offset: int = 0) -> List[Connector]:
    connectors = list(store.connectors.values())
    return connectors[offset : offset + limit]


@app.post("/connectors", response_model=Connector, status_code=status.HTTP_201_CREATED, tags=["Tools/Connectors"])
async def create_connector(payload: ConnectorConfigRequest) -> Connector:
    connector_id = str(uuid4())
    connector = Connector(id=connector_id, name=payload.name, type=payload.type, status="healthy")
    store.connectors[connector_id] = connector
    return connector


@app.get("/connectors/{connector_id}", response_model=Connector, tags=["Tools/Connectors"])
async def get_connector(connector_id: str) -> Connector:
    return _get_connector_or_404(connector_id)


@app.put("/connectors/{connector_id}", response_model=Connector, tags=["Tools/Connectors"])
async def update_connector(connector_id: str, payload: ConnectorConfigRequest) -> Connector:
    connector = _get_connector_or_404(connector_id)
    updated = connector.model_copy(update={"name": payload.name, "type": payload.type, "status": "healthy"})
    store.connectors[connector_id] = updated
    return updated


@app.delete("/connectors/{connector_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tools/Connectors"])
async def delete_connector(connector_id: str) -> Response:
    if connector_id not in store.connectors:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found")
    store.connectors.pop(connector_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/connectors/{connector_id}:test", tags=["Tools/Connectors"])
async def test_connector(connector_id: str) -> Dict[str, Any]:
    _get_connector_or_404(connector_id)
    return {"success": True, "message": "Connector authentication succeeded."}


@app.post("/connectors/{connector_id}:probe", tags=["Tools/Connectors"])
async def probe_connector(connector_id: str) -> Dict[str, Any]:
    _get_connector_or_404(connector_id)
    return {"success": True, "latency_ms": 128.0}


# --- Secrets endpoints ---


def _get_secret_or_404(secret_id: str) -> SecretMetadata:
    secret = store.secrets.get(secret_id)
    if not secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")
    return secret


@app.get("/secrets", response_model=List[SecretMetadata], tags=["Keys & Secrets"])
async def list_secrets(limit: int = 25, offset: int = 0) -> List[SecretMetadata]:
    secrets = list(store.secrets.values())
    return secrets[offset : offset + limit]


@app.post("/secrets", response_model=SecretMetadata, status_code=status.HTTP_201_CREATED, tags=["Keys & Secrets"])
async def create_secret(payload: SecretCreateRequest) -> SecretMetadata:
    secret_id = str(uuid4())
    metadata = SecretMetadata(
        id=secret_id,
        name=payload.name,
        type=payload.type,
        last_used_at=None,
        created_at=iso_now(),
    )
    store.secrets[secret_id] = metadata
    return metadata


@app.post("/secrets/{secret_id}:rotate", response_model=SecretCreateRequest, tags=["Keys & Secrets"])
async def rotate_secret(secret_id: str) -> SecretCreateRequest:
    secret = _get_secret_or_404(secret_id)
    secret.last_used_at = iso_now()
    store.secrets[secret_id] = secret
    return SecretCreateRequest(name=secret.name, value=f"rotated-{uuid4()}", type=secret.type)


@app.delete("/secrets/{secret_id}:disable", status_code=status.HTTP_204_NO_CONTENT, tags=["Keys & Secrets"])
async def disable_secret(secret_id: str) -> Response:
    if secret_id not in store.secrets:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")
    store.secrets.pop(secret_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Run endpoints ---


def _get_run_or_404(run_id: str) -> Run:
    run = store.runs.get(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


@app.get("/runs", response_model=List[Run], tags=["Runs & Logs"])
async def list_runs(
    agentId: Optional[str] = None,  # noqa: N803
    status: Optional[str] = None,
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None, alias="to"),
    limit: int = 25,
    offset: int = 0,
) -> List[Run]:
    runs = list(store.runs.values())
    if agentId:
        runs = [run for run in runs if run.agent_id == agentId]
    if status:
        runs = [run for run in runs if run.status == status]
    return runs[offset : offset + limit]


@app.get("/runs/{run_id}", response_model=Run, tags=["Runs & Logs"])
async def get_run(run_id: str) -> Run:
    return _get_run_or_404(run_id)


@app.get("/runs/stream", tags=["Runs & Logs"])
async def stream_runs(
    agentId: Optional[str] = None,  # noqa: N803
    status: Optional[str] = None,
) -> StreamingResponse:
    runs = list(store.runs.values())
    if agentId:
        runs = [run for run in runs if run.agent_id == agentId]
    if status:
        runs = [run for run in runs if run.status == status]

    async def event_generator() -> Any:
        for run in runs:
            payload = json.dumps(run.model_dump())
            yield f"data: {payload}\n\n"
            await asyncio.sleep(0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/logs/export", tags=["Runs & Logs"])
async def export_logs(format: Literal["json", "ndjson", "csv"], agentId: Optional[str] = None) -> PlainTextResponse:  # noqa: N803
    runs = list(store.runs.values())
    if agentId:
        runs = [run for run in runs if run.agent_id == agentId]
    if format == "ndjson":
        body = "\n".join(json.dumps(run.model_dump()) for run in runs)
        media_type = "application/x-ndjson"
    elif format == "csv":
        body = "id,agent_id,status\n" + "\n".join(f"{run.id},{run.agent_id},{run.status}" for run in runs)
        media_type = "text/csv"
    else:
        body = json.dumps([run.model_dump() for run in runs], indent=2)
        media_type = "application/json"
    return PlainTextResponse(content=body, media_type=media_type)


# --- Job endpoints ---


def _get_job_or_404(job_id: str) -> Job:
    job = store.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@app.get("/jobs", response_model=List[Job], tags=["Jobs & Schedules"])
async def list_jobs(limit: int = 25, offset: int = 0) -> List[Job]:
    jobs = list(store.jobs.values())
    return jobs[offset : offset + limit]


@app.post("/jobs", response_model=Job, status_code=status.HTTP_201_CREATED, tags=["Jobs & Schedules"])
async def create_job(payload: JobCreateRequest) -> Job:
    job_id = str(uuid4())
    job = Job(
        id=job_id,
        name=payload.name,
        schedule_expr=payload.schedule_expr,
        status="scheduled",
        task_definition=payload.task_definition,
    )
    store.jobs[job_id] = job
    return job


@app.get("/jobs/{job_id}", response_model=Job, tags=["Jobs & Schedules"])
async def get_job(job_id: str) -> Job:
    return _get_job_or_404(job_id)


@app.put("/jobs/{job_id}", response_model=Job, tags=["Jobs & Schedules"])
async def update_job(job_id: str, payload: JobCreateRequest) -> Job:
    _get_job_or_404(job_id)
    job = Job(
        id=job_id,
        name=payload.name,
        schedule_expr=payload.schedule_expr,
        status="scheduled",
        task_definition=payload.task_definition,
    )
    store.jobs[job_id] = job
    return job


@app.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Jobs & Schedules"])
async def delete_job(job_id: str) -> Response:
    if job_id not in store.jobs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    store.jobs.pop(job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/jobs/{job_id}:trigger", status_code=status.HTTP_202_ACCEPTED, tags=["Jobs & Schedules"])
async def trigger_job(job_id: str) -> Dict[str, str]:
    _get_job_or_404(job_id)
    run_id = str(uuid4())
    return {"run_id": run_id}


@app.post("/jobs/{job_id}:pause", response_model=Job, tags=["Jobs & Schedules"])
async def pause_job(job_id: str) -> Job:
    job = _get_job_or_404(job_id)
    paused = job.model_copy(update={"status": "paused"})
    store.jobs[job_id] = paused
    return paused


@app.post("/jobs/{job_id}:resume", response_model=Job, tags=["Jobs & Schedules"])
async def resume_job(job_id: str) -> Job:
    job = _get_job_or_404(job_id)
    resumed = job.model_copy(update={"status": "active"})
    store.jobs[job_id] = resumed
    return resumed


@app.get("/dlq", response_model=List[DLQItem], tags=["Jobs & Schedules"])
async def list_dlq(limit: int = 25, offset: int = 0) -> List[DLQItem]:
    items = list(store.dlq_items.values())
    return items[offset : offset + limit]


# --- RBAC endpoints ---


def _get_user_or_404(user_id: str) -> User:
    user = store.users.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@app.get("/users", response_model=List[User], tags=["Users & Roles"])
async def list_users(limit: int = 25, offset: int = 0) -> List[User]:
    users = list(store.users.values())
    return users[offset : offset + limit]


@app.post("/users", response_model=User, status_code=status.HTTP_201_CREATED, tags=["Users & Roles"])
async def create_user(payload: UserCreateRequest) -> User:
    if any(user.email == payload.email for user in store.users.values()):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
    user_id = str(uuid4())
    user = User(id=user_id, email=payload.email, role=payload.role)
    store.users[user_id] = user
    return user


@app.get("/users/{user_id}", response_model=User, tags=["Users & Roles"])
async def get_user(user_id: str) -> User:
    return _get_user_or_404(user_id)


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Users & Roles"])
async def delete_user(user_id: str) -> Response:
    if user_id not in store.users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    store.users.pop(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/users/{user_id}:reset-mfa", tags=["Users & Roles"])
async def reset_mfa(user_id: str) -> Dict[str, bool]:
    _get_user_or_404(user_id)
    return {"success": True}


@app.put("/users/{user_id}/role", response_model=User, tags=["Users & Roles"])
async def update_user_role(user_id: str, payload: UserRoleUpdateRequest) -> User:
    user = _get_user_or_404(user_id)
    updated = user.model_copy(update={"role": payload.role})
    store.users[user_id] = updated
    return updated


@app.get("/roles", response_model=List[str], tags=["Users & Roles"])
async def list_roles() -> List[str]:
    return ["admin", "operator", "viewer"]


# --- Policy endpoints ---


def _get_policy_or_404(policy_id: str) -> Policy:
    policy = store.policies.get(policy_id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return policy


@app.get("/policies", response_model=List[Policy], tags=["Policies"])
async def list_policies(limit: int = 25, offset: int = 0) -> List[Policy]:
    policies = list(store.policies.values())
    return policies[offset : offset + limit]


@app.post("/policies", response_model=Policy, status_code=status.HTTP_201_CREATED, tags=["Policies"])
async def create_policy(payload: PolicyCreateRequest) -> Policy:
    policy_id = str(uuid4())
    policy = Policy(id=policy_id, name=payload.name, rego_text=payload.rego_text)
    store.policies[policy_id] = policy
    return policy


@app.get("/policies/{policy_id}", response_model=Policy, tags=["Policies"])
async def get_policy(policy_id: str) -> Policy:
    return _get_policy_or_404(policy_id)


@app.put("/policies/{policy_id}", response_model=Policy, tags=["Policies"])
async def update_policy(policy_id: str, payload: PolicyCreateRequest) -> Policy:
    _get_policy_or_404(policy_id)
    policy = Policy(id=policy_id, name=payload.name, rego_text=payload.rego_text)
    store.policies[policy_id] = policy
    return policy


@app.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Policies"])
async def delete_policy(policy_id: str) -> Response:
    if policy_id not in store.policies:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    store.policies.pop(policy_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/policies/{policy_id}:simulate", response_model=PolicySimulationResult, tags=["Policies"])
async def simulate_policy(policy_id: str, payload: PolicySimulationRequest) -> PolicySimulationResult:
    _get_policy_or_404(policy_id)
    allow = payload.input.get("action") != "deny"
    violations = [] if allow else ["Denied by simulation rule"]
    return PolicySimulationResult(allow=allow, violations=violations)


# --- Audit endpoints ---


def _get_audit_or_404(audit_id: str) -> AuditEntry:
    entry = store.audit_entries.get(audit_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit entry not found")
    return entry


@app.get("/audit", response_model=List[AuditEntry], tags=["Audit Trail"])
async def list_audit(
    userId: Optional[str] = None,  # noqa: N803
    action: Optional[str] = None,
    resource: Optional[str] = None,
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None, alias="to"),
    limit: int = 25,
    offset: int = 0,
) -> List[AuditEntry]:
    entries = list(store.audit_entries.values())
    if userId:
        entries = [entry for entry in entries if entry.user_id == userId]
    if action:
        entries = [entry for entry in entries if entry.action == action]
    if resource:
        entries = [entry for entry in entries if entry.resource == resource]
    return entries[offset : offset + limit]


@app.get("/audit/{audit_id}", response_model=AuditEntry, tags=["Audit Trail"])
async def get_audit_entry(audit_id: str) -> AuditEntry:
    return _get_audit_or_404(audit_id)


@app.get("/audit/export", tags=["Audit Trail"])
async def export_audit(
    format: Literal["json", "ndjson", "csv"],
    userId: Optional[str] = None,  # noqa: N803
    action: Optional[str] = None,
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None, alias="to"),
) -> PlainTextResponse:
    entries = await list_audit(  # type: ignore[arg-type]
        userId=userId,
        action=action,
        resource=None,
        from_=from_,
        to=to,
        limit=10,
        offset=0,
    )
    if format == "ndjson":
        body = "\n".join(json.dumps(entry.model_dump()) for entry in entries)
        media_type = "application/x-ndjson"
    elif format == "csv":
        body = "id,user_id,action,resource\n" + "\n".join(
            f"{entry.id},{entry.user_id},{entry.action},{entry.resource}" for entry in entries
        )
        media_type = "text/csv"
    else:
        body = json.dumps([entry.model_dump() for entry in entries], indent=2)
        media_type = "application/json"
    headers = {"Content-Disposition": 'attachment; filename="astradesk-audit-export.ndjson"'}
    return PlainTextResponse(content=body, media_type=media_type, headers=headers)


# --- Settings endpoints ---


def _get_settings_group_or_404(group: str) -> Dict[str, Setting]:
    settings = store.settings.get(group)
    if settings is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settings group not found")
    return settings


@app.get("/settings/{group}", response_model=List[Setting], tags=["Settings"])
async def list_settings(group: Literal["integrations", "localization", "platform"]) -> List[Setting]:
    settings = _get_settings_group_or_404(group)
    return list(settings.values())


@app.put("/settings/{group}", response_model=Setting, tags=["Settings"])
async def update_setting(group: Literal["integrations", "localization", "platform"], payload: SettingUpdateRequest) -> Setting:
    settings = _get_settings_group_or_404(group)
    if payload.key not in settings:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown setting key")
    updated = settings[payload.key].model_copy(update={"value": payload.value})
    settings[payload.key] = updated
    store.settings[group] = settings
    return updated


# --- Domain packs ---


@app.get("/domain-packs", response_model=List[DomainPack], tags=["Domain Packs"])
async def list_domain_packs() -> List[DomainPack]:
    return store.domain_packs


@app.post("/domain-packs/{name}:install", status_code=status.HTTP_202_ACCEPTED, tags=["Domain Packs"])
async def install_domain_pack(name: str) -> Dict[str, str]:
    return {"job_id": str(uuid4()), "pack": name}


@app.post("/domain-packs/{name}:uninstall", status_code=status.HTTP_202_ACCEPTED, tags=["Domain Packs"])
async def uninstall_domain_pack(name: str) -> Dict[str, str]:
    return {"job_id": str(uuid4()), "pack": name}
