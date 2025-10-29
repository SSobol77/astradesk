# SPDX-License-Identifier: Apache-2.0
"""File: services/api-gateway/src/gateway/main.py

Project: astradesk
Pakage: api-gateway

Author: Siergej Sobolewski
Since: 2025-10-29

Production-ready FastAPI application for the AstraDesk API Gateway.

This module sets up the FastAPI application, including:
- Lifespan management for resource initialization and cleanup.
- A secure dependency for JWT-based authentication and authorization.
- The main API endpoint to process agent requests.
- Centralized error handling.
- Health check endpoints.

"""

from __future__ import annotations

import logging
import os
import uuid
import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional

import asyncpg
import redis.asyncio as redis
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from opa_python_client import OPAClient

# AstraDesk imports
from gateway.orchestrator import (
    AgentOrchestrator,
    AgentNotFoundError,
    PolicyViolationError,
)
from model_gateway.llm_planner import LLMPlanner
from model_gateway.router import provider_router
from runtime.memory import Memory
from runtime.models import AgentRequest, AgentResponse
from runtime.planner import KeywordPlanner
from runtime.rag import RAG
from runtime.registry import ToolRegistry, load_domain_packs
from agents.base import BaseAgent
from agents.support import SupportAgent
from agents.billing import BillingAgent
from tools import metrics, ops_actions, tickets_proxy

# --- Configuration ---
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")
OPA_URL = os.getenv("OPA_URL", "http://localhost:8181")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-key-for-dev")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# --- Global State ---
# Use a dictionary for state to avoid global variables
app_state: Dict[str, Any] = {}
http_bearer = HTTPBearer(
    description="Bearer token for authentication with JWT claims.",
    scheme_name="Bearer",
)


# --- Authentication ---
async def get_current_user_claims(
    token: HTTPAuthorizationCredentials = Depends(http_bearer),
) -> Dict[str, Any]:
    """
    Dependency to decode and validate JWT, returning user claims.
    This is a best-practice user loader function.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM]
        )
        if "sub" not in payload or "roles" not in payload:
            raise credentials_exception
        await asyncio.sleep(0)
        return payload
    except JWTError:
        raise credentials_exception
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing credentials.",
        )


# --- Application Lifespan (Startup/Shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Handles application startup and shutdown events to manage resources.
    """
    logger.info("API Gateway starting up...")

    # --- Initialize connections ---
    if not DATABASE_URL or not REDIS_URL:
        raise RuntimeError("DATABASE_URL and REDIS_URL must be set.")
    pg_pool = await asyncpg.create_pool(DATABASE_URL)
    if not pg_pool:
        raise RuntimeError("Failed to create PostgreSQL connection pool.")
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    opa_client = OPAClient(url=OPA_URL)

    # --- Initialize core components ---
    tool_registry = ToolRegistry()
    # Register built-in tools
    await tool_registry.register("get_metrics", metrics.get_metrics, description="Get service performance metrics.")
    await tool_registry.register("restart_service", ops_actions.restart_service, description="Restart a service deployment.")
    await tool_registry.register("create_ticket", tickets_proxy.create_ticket, description="Create a support ticket.")
    # Discover and load tools from external domain packs
    load_domain_packs(tool_registry)

    llm_planner = LLMPlanner(opa_client=opa_client)
    rag = RAG(pg_pool=pg_pool, llm_planner=llm_planner)
    memory = Memory(pg_pool=pg_pool, redis_cli=redis_client)
    keyword_planner = KeywordPlanner()

    # --- Initialize agents ---
    agents: Dict[str, BaseAgent] = {
        "support": SupportAgent(tool_registry, memory, keyword_planner, rag, llm_planner),
        "billing": BillingAgent(tool_registry, memory, keyword_planner, rag, llm_planner),
    }

    # --- Create and store the main orchestrator ---
    app_state["orchestrator"] = AgentOrchestrator(
        llm_planner=llm_planner,
        agents=agents,
        tools=tool_registry,
        pg_pool=pg_pool,
        redis=redis_client,
        opa_client=opa_client,
    )
    logger.info("Agent Orchestrator initialized successfully.")

    yield  # Application is now running

    # --- Shutdown logic ---
    logger.info("API Gateway shutting down...")
    if "orchestrator" in app_state:
        orchestrator = app_state["orchestrator"]
        await orchestrator.pg_pool.close()
        await orchestrator.redis.close()
        await provider_router.shutdown()
    logger.info("Resources cleaned up.")


# --- FastAPI Application ---
app = FastAPI(
    title="AstraDesk API Gateway",
    description="Central API for orchestrating AI agents and tools.",
    version="1.2.0",
    lifespan=lifespan,
)


# --- API Endpoints ---
@app.get("/healthz", tags=["Health"])
def healthz() -> Dict[str, str]:
    """Provides a simple health check endpoint."""
    return {"status": "ok"}


@app.post(
    "/v1/run",
    response_model=AgentResponse,
    tags=["Agents"],
    summary="Execute an agent with a given query",
    description="Receives a user query, routes it to the appropriate agent, orchestrates tool execution, and returns a final response.",
)
async def execute_agent(
    agent_request: AgentRequest,
    request: Request,
    claims: Dict[str, Any] = Depends(get_current_user_claims),
) -> AgentResponse:
    """
    Main endpoint to run an agent.
    - Authenticates the user via JWT.
    - Passes the request to the orchestrator.
    - Handles errors and returns a structured response.
    """
    orchestrator: Optional[AgentOrchestrator] = app_state.get("orchestrator")
    if not orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Orchestrator is not initialized.",
        )

    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    try:
        response = await orchestrator.run(agent_request, claims, request_id)
        return response
    except AgentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PolicyViolationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.exception(f"[{request_id}] Unexpected error during agent execution")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred: {e}",
        )