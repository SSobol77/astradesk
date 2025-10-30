from fastapi import FastAPI, HTTPException, status, Response
from pydantic import BaseModel, Field, EmailStr
from enum import Enum
from typing import Dict, Optional, List, Any
import uuid
from datetime import datetime, timezone

# --- Manual Model Definition ---
# NOTE: These models are defined manually. They should be replaced by generated models.

class StatusEnum(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    ERROR = "error"

class ComponentHealth(BaseModel):
    status: StatusEnum
    message: Optional[str] = None

class HealthStatus(BaseModel):
    status: StatusEnum
    components: Dict[str, ComponentHealth]

# --- Agent Models ---

class AgentEnv(str, Enum):
    DRAFT = "draft"
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"

class AgentStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"

class Agent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    version: str = "1.0.0"
    env: AgentEnv = AgentEnv.DRAFT
    status: AgentStatus = AgentStatus.ACTIVE
    config: Dict[str, Any]
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class AgentConfigRequest(BaseModel):
    name: str
    config: Dict[str, Any]

# --- Dataset Models ---

class DatasetType(str, Enum):
    S3 = "s3"
    POSTGRES = "postgres"
    GIT = "git"

class IndexingStatus(str, Enum):
    INDEXED = "indexed"
    PENDING = "pending"
    FAILED = "failed"

class Dataset(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: DatasetType
    indexing_status: IndexingStatus = IndexingStatus.PENDING
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class DatasetCreateRequest(BaseModel):
    name: str
    type: DatasetType

# --- Flow Models ---

class FlowStatus(str, Enum):
    ACTIVE = "active"
    DRAFT = "draft"
    ARCHIVED = "archived"

class Flow(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    version: str = "1.0.0"
    status: FlowStatus = FlowStatus.DRAFT
    env: AgentEnv = AgentEnv.DRAFT
    config_yaml: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class FlowCreateRequest(BaseModel):
    name: str
    config_yaml: str

class FlowUpdateRequest(BaseModel):
    name: Optional[str] = None
    status: Optional[FlowStatus] = None
    config_yaml: Optional[str] = None

# --- User Models ---

class UserRole(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    role: UserRole
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class UserCreateRequest(BaseModel):
    email: EmailStr
    role: UserRole

class UserRoleUpdateRequest(BaseModel):
    role: UserRole

# --- Policy Models ---

class Policy(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    rego_text: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class PolicyCreateRequest(BaseModel):
    name: str
    rego_text: str

class PolicyUpdateRequest(BaseModel):
    name: Optional[str] = None
    rego_text: Optional[str] = None

# --- In-Memory Database ---

DB_AGENTS: Dict[str, Agent] = {}
DB_DATASETS: Dict[str, Dataset] = {}
DB_FLOWS: Dict[str, Flow] = {}
DB_USERS: Dict[str, User] = {}
DB_POLICIES: Dict[str, Policy] = {}

# Pre-populate with sample data
sample_agent_id = str(uuid.uuid4())
DB_AGENTS[sample_agent_id] = Agent(
    id=sample_agent_id,
    name="Support Triage Agent",
    config={"model": "gpt-4", "temperature": 0.7},
)

sample_dataset_id = str(uuid.uuid4())
DB_DATASETS[sample_dataset_id] = Dataset(
    id=sample_dataset_id,
    name="FAQ Documents",
    type=DatasetType.S3,
    indexing_status=IndexingStatus.INDEXED,
)

sample_flow_id = str(uuid.uuid4())
DB_FLOWS[sample_flow_id] = Flow(
    id=sample_flow_id,
    name="Customer Onboarding Flow",
    config_yaml="- id: start\n  type: event\n- id: triage\n  type: agent\n  agent_id: {}".format(sample_agent_id),
)

sample_user_id = str(uuid.uuid4())
DB_USERS[sample_user_id] = User(
    id=sample_user_id,
    email="admin@astradesk.com",
    role=UserRole.ADMIN,
)

sample_policy_id = str(uuid.uuid4())
DB_POLICIES[sample_policy_id] = Policy(
    id=sample_policy_id,
    name="AllowAdmins",
    rego_text='''package astradesk.authz\n\nallow = { \"admin\" in input.user.roles }''',
)


# --- FastAPI Application ---

app = FastAPI(
    title="AstraDesk Admin API",
    description="Provides administrative endpoints for the AstraDesk platform.",
    version="1.2.0",
)

# --- Health Endpoints ---

@app.get("/health/status", response_model=HealthStatus, tags=["Health"])
async def get_health_status():
    return HealthStatus(
        status=StatusEnum.OK,
        components={
            "database": ComponentHealth(status=StatusEnum.OK),
            "vector_store": ComponentHealth(status=StatusEnum.OK),
            "cache": ComponentHealth(status=StatusEnum.DEGRADED, message="Cache latency is high"),
        }
    )

@app.get("/healthz", tags=["Health"])
async def healthz():
    return {"status": "ok"}

# --- Agent Endpoints ---

@app.get("/agents", response_model=List[Agent], tags=["Agents"])
async def list_agents(limit: int = 25, offset: int = 0):
    agents_list = list(DB_AGENTS.values())
    return agents_list[offset : offset + limit]

@app.post("/agents", response_model=Agent, status_code=status.HTTP_201_CREATED, tags=["Agents"])
async def create_agent(agent_config: AgentConfigRequest):
    new_agent = Agent(name=agent_config.name, config=agent_config.config)
    DB_AGENTS[new_agent.id] = new_agent
    return new_agent

@app.get("/agents/{agent_id}", response_model=Agent, tags=["Agents"])
async def get_agent(agent_id: str):
    agent = DB_AGENTS.get(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent

@app.put("/agents/{agent_id}", response_model=Agent, tags=["Agents"])
async def update_agent(agent_id: str, agent_config: AgentConfigRequest):
    agent = DB_AGENTS.get(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    agent.name = agent_config.name
    agent.config = agent_config.config
    agent.updated_at = datetime.now(timezone.utc).isoformat()
    DB_AGENTS[agent_id] = agent
    return agent

@app.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Agents"])
async def delete_agent(agent_id: str):
    if agent_id not in DB_AGENTS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    del DB_AGENTS[agent_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- Dataset Endpoints ---

@app.get("/datasets", response_model=List[Dataset], tags=["Datasets"])
async def list_datasets(limit: int = 25, offset: int = 0):
    datasets_list = list(DB_DATASETS.values())
    return datasets_list[offset : offset + limit]

@app.post("/datasets", response_model=Dataset, status_code=status.HTTP_201_CREATED, tags=["Datasets"])
async def create_dataset(dataset_create: DatasetCreateRequest):
    new_dataset = Dataset(name=dataset_create.name, type=dataset_create.type)
    DB_DATASETS[new_dataset.id] = new_dataset
    return new_dataset

@app.get("/datasets/{dataset_id}", response_model=Dataset, tags=["Datasets"])
async def get_dataset(dataset_id: str):
    dataset = DB_DATASETS.get(dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return dataset

@app.delete("/datasets/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Datasets"])
async def delete_dataset(dataset_id: str):
    if dataset_id not in DB_DATASETS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    del DB_DATASETS[dataset_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- Flow Endpoints ---

@app.get("/flows", response_model=List[Flow], tags=["Flows"])
async def list_flows(limit: int = 25, offset: int = 0):
    flows_list = list(DB_FLOWS.values())
    return flows_list[offset : offset + limit]

@app.post("/flows", response_model=Flow, status_code=status.HTTP_201_CREATED, tags=["Flows"])
async def create_flow(flow_create: FlowCreateRequest):
    new_flow = Flow(name=flow_create.name, config_yaml=flow_create.config_yaml)
    DB_FLOWS[new_flow.id] = new_flow
    return new_flow

@app.get("/flows/{flow_id}", response_model=Flow, tags=["Flows"])
async def get_flow(flow_id: str):
    flow = DB_FLOWS.get(flow_id)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found")
    return flow

@app.put("/flows/{flow_id}", response_model=Flow, tags=["Flows"])
async def update_flow(flow_id: str, flow_update: FlowUpdateRequest):
    flow = DB_FLOWS.get(flow_id)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found")
    
    if flow_update.name is not None:
        flow.name = flow_update.name
    if flow_update.status is not None:
        flow.status = flow_update.status
    if flow_update.config_yaml is not None:
        flow.config_yaml = flow_update.config_yaml
    
    flow.updated_at = datetime.now(timezone.utc).isoformat()
    DB_FLOWS[flow_id] = flow
    return flow

@app.delete("/flows/{flow_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Flows"])
async def delete_flow(flow_id: str):
    if flow_id not in DB_FLOWS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found")
    del DB_FLOWS[flow_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- User Endpoints ---

@app.get("/users", response_model=List[User], tags=["Users"])
async def list_users(limit: int = 25, offset: int = 0):
    users_list = list(DB_USERS.values())
    return users_list[offset : offset + limit]

@app.post("/users", response_model=User, status_code=status.HTTP_201_CREATED, tags=["Users"])
async def create_user(user_create: UserCreateRequest):
    # Check for existing email
    for user in DB_USERS.values():
        if user.email == user_create.email:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User with this email already exists")
    new_user = User(email=user_create.email, role=user_create.role)
    DB_USERS[new_user.id] = new_user
    return new_user

@app.get("/users/{user_id}", response_model=User, tags=["Users"])
async def get_user(user_id: str):
    user = DB_USERS.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@app.put("/users/{user_id}/role", response_model=User, tags=["Users"])
async def update_user_role(user_id: str, role_update: UserRoleUpdateRequest):
    user = DB_USERS.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.role = role_update.role
    DB_USERS[user_id] = user
    return user

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Users"])
async def delete_user(user_id: str):
    if user_id not in DB_USERS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    del DB_USERS[user_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- Policy Endpoints ---

@app.get("/policies", response_model=List[Policy], tags=["Policies"])
async def list_policies(limit: int = 25, offset: int = 0):
    policies_list = list(DB_POLICIES.values())
    return policies_list[offset : offset + limit]

@app.post("/policies", response_model=Policy, status_code=status.HTTP_201_CREATED, tags=["Policies"])
async def create_policy(policy_create: PolicyCreateRequest):
    new_policy = Policy(name=policy_create.name, rego_text=policy_create.rego_text)
    DB_POLICIES[new_policy.id] = new_policy
    return new_policy

@app.get("/policies/{policy_id}", response_model=Policy, tags=["Policies"])
async def get_policy(policy_id: str):
    policy = DB_POLICIES.get(policy_id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return policy

@app.put("/policies/{policy_id}", response_model=Policy, tags=["Policies"])
async def update_policy(policy_id: str, policy_update: PolicyUpdateRequest):
    policy = DB_POLICIES.get(policy_id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    
    if policy_update.name is not None:
        policy.name = policy_update.name
    if policy_update.rego_text is not None:
        policy.rego_text = policy_update.rego_text
    
    DB_POLICIES[policy_id] = policy
    return policy

@app.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Policies"])
async def delete_policy(policy_id: str):
    if policy_id not in DB_POLICIES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    del DB_POLICIES[policy_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)
