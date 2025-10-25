# SPDX-License-Identifier: Apache-2.0
# services/api-gateway/src/gateway/main.py
"""File: services/api-gateway/src/gateway/main.py
Project: AstraDesk Framework — API Gateway
Description: FastAPI entrypoint (Python 3.14+) exposing HTTP endpoints and managing application lifecycle via `lifespan`.
Centralizes dependency injection, auth, logging, error handling, OPA governance, and OTel tracing.
Integrates agent orchestration with OpenAPI v1.2.0 endpoints for /v1/agents/{name}/run.
Author: Siergej Sobolewski
Since: 2025-10-25
"""  # noqa: D205

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import logging
import os
import uuid
from dotenv import load_dotenv
load_dotenv()

import asyncpg
import redis.asyncio as redis
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from opa_python_client import OPAClient  # OPA middleware
from opentelemetry import trace  # OTel
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel

# Project imports
from services.api_gateway.src.agents.base import BaseAgent
from services.api_gateway.src.agents.support import SupportAgent
from services.api_gateway.src.agents.billing import BillingAgent  # New
from services.api_gateway.src.gateway.orchestrator import AgentOrchestrator
from services.api_gateway.src.model_gateway.router import provider_router
from services.api_gateway.src.runtime.auth import cfg as auth_config
from services.api_gateway.src.runtime.memory import Memory
from services.api_gateway.src.runtime.models import AgentRequest, AgentResponse
from services.api_gateway.src.runtime.planner import KeywordPlanner
from services.api_gateway.src.runtime.rag import RAG
from services.api_gateway.src.runtime.registry import ToolRegistry

logger = logging.getLogger(__name__)

security = HTTPBearer()

class ProblemDetail(BaseModel):  # RFC 7807
    type: str
    title: str
    detail: str
    status: int

app = FastAPI(title="AstraDesk API Gateway", version="1.2.0")

# App state
class AppState:
    pg_pool: asyncpg.Pool
    redis: redis.Redis
    tools: ToolRegistry
    memory: Memory
    planner: KeywordPlanner
    rag: RAG
    llm_planner: Any  # From model_gateway
    opa_client: OPAClient
    agents: Dict[str, BaseAgent]

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan: startup (init deps, OTel, OPA) and shutdown."""
    # Startup
    app.state.pg_pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"))
    app.state.redis = redis.from_url(os.getenv("REDIS_URL"))
    app.state.tools = ToolRegistry()  # Init with tools
    app.state.memory = Memory(pg_pool=app.state.pg_pool, redis=app.state.redis)
    app.state.planner = KeywordPlanner()
    app.state.rag = RAG()  # From earlier
    app.state.agents = {
        "support": SupportAgent(
            tools=app.state.tools,
            memory=app.state.memory,
            planner=app.state.planner,
            rag=app.state.rag,
            llm_planner=app.state.llm_planner,
            opa_client=app.state.opa_client,
        ),
        "billing": BillingAgent(  # New agent
            tools=app.state.tools,
            memory=app.state.memory,
            planner=app.state.planner,
            rag=app.state.rag,
            llm_planner=app.state.llm_planner,
            opa_client=app.state.opa_client,
        ),
    }
    app.state.opa_client = OPAClient(url=os.getenv("OPA_URL", "http://opa:8181"))
    app.state.llm_planner = await provider_router.get_provider()  # Lazy

    # OTel instrumentation
    tracer_provider = trace.get_tracer_provider()
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)

    yield

    # Shutdown
    await app.state.pg_pool.close()
    await app.state.redis.close()
    await provider_router.shutdown()

app.router.lifespan_context = lifespan

# Auth guard (JWT + OPA)
async def auth_guard(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Auth guard: Validate JWT and OPA policy."""
    try:
        claims = jwt.decode(credentials.credentials, auth_config.SECRET_KEY, algorithms=[auth_config.ALGORITHM])
        # OPA check
        decision = await app.state.opa_client.check_policy(
            input={"user": claims, "action": "agent_run"},
            policy_path="astradesk/auth"
        )
        if not decision["result"]:
            raise HTTPException(status_code=403, detail="Access denied by policy")
        return claims
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid JWT")

# Error handler (RFC 7807)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    detail = {"type": "https://astradesk.com/errors/internal", "title": "Internal Error", "status": 500}
    return JSONResponse(status_code=500, content=detail, media_type="application/problem+json")

# Health endpoint
@app.get("/health", tags=["Health"])
async def health() -> Dict[str, str]:
    """Basic health check."""
    return {"status": "ok"}

@app.get("/ready", tags=["Health"])
async def ready(state: AppState = Depends(lambda: app.state)) -> Dict[str, str]:
    """Readiness probe: Verify DB connections."""
    try:
        async with state.pg_pool.acquire() as conn:
            await conn.execute("SELECT 1")
        return {"status": "ready", "dependencies": {"postgres": "ok", "redis": "ok"}}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail={"dependencies": {"postgres": "unavailable"}})

# Integrated agent endpoint (OpenAPI v1.2.0)
@app.post(
    "/v1/agents/{agent_name}/run",
    response_model=AgentResponse,
    tags=["Agents"],
    summary="Run a specific agent",
    description="Executes the named agent with the provided request. Supports SupportAgent, BillingAgent, etc.",
    security=[{"BearerAuth": []}],
)
async def run_agent(
    agent_name: str,
    req: AgentRequest,
    request: Request,
    claims: Dict[str, Any] = Depends(auth_guard),
    state: AppState = Depends(lambda: app.state),
) -> AgentResponse:
    """Runs the specified agent and returns its response.
    
    Integrates with ticketing system via tools (e.g., create_ticket calls HTTP to ticket-adapter-java:8081).
    
    Args:
        agent_name: Name of the agent (e.g., 'support', 'billing').
        req: Agent request payload.
        claims: JWT claims from auth.
    
    Returns:
        AgentResponse with output, trace_id, invoked_tools.
    """
    with trace.get_tracer(__name__).start_as_current_span("run_agent") as span:
        span.set_attribute("agent_name", agent_name)
        span.set_attribute("request_id", str(uuid.uuid4()))

        if agent_name not in state.agents:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        agent = state.agents[agent_name]
        context = {"claims": claims, "request_id": span.get_span_context().span_id}
        response = await agent.run(req.input, context)

        # Ticketing integration: If create_ticket invoked, log to adapter
        if any(tool.name == "create_ticket" for tool in response.invoked_tools):
            # Async call to ticket-adapter-java
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post("http://ticket-adapter:8081/tickets/confirm", json={"request_id": context["request_id"]})

        return response
