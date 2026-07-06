# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/src/gateway/main.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for services/api-gateway/src/gateway/main.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Production-ready FastAPI application for the AstraDesk API Gateway.

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
from collections.abc import AsyncGenerator, Callable, Iterable
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
load_dotenv(os.path.join(project_root, '.env'))

import httpx
import nats
import nats.js.errors
from agents.base import BaseAgent
from agents.billing import BillingAgent
from agents.ops import OpsAgent
from agents.support import SupportAgent
from astradesk_core.utils.oidc import Principal
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from model_gateway.llm_planner import LLMPlanner
from model_gateway.router import provider_router
from opa_client.opa import OpaClient
from runtime.audit import AuditWriter, FileAuditWriter, InMemoryAuditWriter, JetStreamAuditWriter
from runtime.authz import SideEffect, enforce_registration_invariants
from runtime.memory import Memory
from runtime.models import AgentRequest, AgentResponse
from runtime.planner import KeywordPlanner
from runtime.policy_enforcer import PolicyEnforcer, build_policy_enforcer_from_env
from runtime.rag import RAG
from runtime.registry import ToolRegistry, load_domain_packs
from tools import metrics, ops_actions, tickets_proxy

import asyncpg
import redis.asyncio as redis

# AstraDesk imports
from gateway.auth_dependency import (
    install_verifier,
    require_admin_role,
    require_authenticated,
)
from gateway.orchestrator import AgentNotFoundError, AgentOrchestrator, PolicyViolationError

# --- Configuration ---
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

ADMIN_API_URL = os.getenv('ADMIN_API_URL', 'http://localhost:8001')
# Safe local/CI fallbacks: in environments where `.env` is gitignored (e.g. the
# GitHub Actions runner) these variables are often unset. Falling back to dummy
# local placeholders keeps imports and CI green instead of crashing at startup.
# Real deployments MUST override these via environment / secrets.
_DEFAULT_DATABASE_URL = 'postgresql://dummy:dummy@localhost:5432/astradb'
_DEFAULT_REDIS_URL = 'redis://localhost:6379/0'
DATABASE_URL = os.getenv('DATABASE_URL', _DEFAULT_DATABASE_URL)
REDIS_URL = os.getenv('REDIS_URL', _DEFAULT_REDIS_URL)
OPA_URL = os.getenv('OPA_URL', 'http://localhost:8181')

# --- Global State ---
# Use a dictionary for state to avoid global variables
app_state: dict[str, Any] = {}


class AuditConfigError(RuntimeError):
    """Raised at startup when a deployed tier lacks a durable audit sink.

    Mirrors :class:`astradesk_core.utils.oidc.AuthConfigError`: absence of a
    required security/evidence dependency must abort startup, not silently
    downgrade to a weaker mode (``INV-FAIL-CLOSED`` / ``INV-LOCAL-MODE-EXPLICIT``,
    ISSUE 019).
    """


# Tiers considered "deployed" for the audit fail-closed check below — the same
# values as astradesk_core.utils.oidc's deployed-tier check, kept local rather
# than importing that module's private constant for an unrelated concern.
_AUDIT_DEPLOYED_TIERS = frozenset({'production', 'prod', 'staging', 'stage'})

# Defaults for AUDIT_MODE=jetstream (ISSUE 039). AUDIT_NATS_URL falls back to
# the shared NATS_URL (already used by the auditor consumer and runtime.memory)
# when unset, so a single broker address configures the whole event bus unless
# the audit stream is deliberately split onto a different NATS deployment.
_DEFAULT_AUDIT_JETSTREAM_STREAM = 'ASTRADESK_AUDIT'
_DEFAULT_AUDIT_JETSTREAM_SUBJECT = 'astradesk.audit'
_DEFAULT_AUDIT_JETSTREAM_DLQ_SUBJECT = 'astradesk.audit.dlq'
_DEFAULT_AUDIT_PUBLISH_TIMEOUT_MS = 2000
_DEFAULT_AUDIT_PUBLISH_RETRIES = 2
_DEFAULT_AUDIT_CONNECT_TIMEOUT_SEC = 5.0


async def _ensure_audit_stream(js: Any, *, stream: str, subject: str, dlq_subject: str) -> None:
    """Idempotently ensure the JetStream stream backing the audit subjects exists.

    Checks first rather than always calling ``add_stream`` so an
    already-provisioned stream with operator-tuned settings (retention,
    replicas, etc.) is never silently reconfigured by application startup.
    """
    try:
        await js.stream_info(stream)
    except nats.js.errors.NotFoundError:
        await js.add_stream(name=stream, subjects=[subject, dlq_subject])


async def _build_jetstream_audit_writer(
    *, connect: Callable[..., Any] | None = None
) -> JetStreamAuditWriter:
    """Connect to NATS JetStream and return a ready, durable writer (ISSUE 039).

    ``connect`` is injectable so tests can supply a fake without a real NATS
    server; production code resolves the real ``nats.connect`` when omitted.
    Resolved lazily inside the function body (not as a default parameter
    value) so monkeypatching ``gateway_main.nats.connect`` in a test takes
    effect even when the caller does not pass ``connect=`` explicitly — a
    default bound at function-definition time would capture the original
    function object and silently ignore such patching. Fails closed (raises
    :class:`AuditConfigError`) on any connection or stream-setup failure,
    unconditionally — ``AUDIT_MODE=jetstream`` is an explicit opt-in
    (``INV-LOCAL-MODE-EXPLICIT`` counterpart: the *strong* mode, not a
    convenience), so it must never silently degrade to a weaker writer, on
    any tier. The live connection is stashed on ``app_state`` for orderly
    shutdown; the error message never includes the broker URL's credentials
    (NATS URLs in this codebase carry no embedded auth) or any event payload.
    """
    connect = connect or nats.connect
    nats_url = os.getenv('AUDIT_NATS_URL', '').strip() or os.getenv('NATS_URL', 'nats://nats:4222')
    stream = os.getenv('AUDIT_JETSTREAM_STREAM', _DEFAULT_AUDIT_JETSTREAM_STREAM).strip()
    subject = os.getenv('AUDIT_JETSTREAM_SUBJECT', _DEFAULT_AUDIT_JETSTREAM_SUBJECT).strip()
    dlq_subject = os.getenv(
        'AUDIT_JETSTREAM_DLQ_SUBJECT', _DEFAULT_AUDIT_JETSTREAM_DLQ_SUBJECT
    ).strip()
    try:
        timeout_ms = int(
            os.getenv('AUDIT_PUBLISH_TIMEOUT_MS', str(_DEFAULT_AUDIT_PUBLISH_TIMEOUT_MS))
        )
        retries = int(os.getenv('AUDIT_PUBLISH_RETRIES', str(_DEFAULT_AUDIT_PUBLISH_RETRIES)))
    except ValueError as exc:
        raise AuditConfigError(
            'AUDIT_PUBLISH_TIMEOUT_MS/AUDIT_PUBLISH_RETRIES must be integers.'
        ) from exc

    try:
        nc = await connect(nats_url, connect_timeout=_DEFAULT_AUDIT_CONNECT_TIMEOUT_SEC)
        js = nc.jetstream()
        await _ensure_audit_stream(js, stream=stream, subject=subject, dlq_subject=dlq_subject)
    except Exception as exc:
        raise AuditConfigError(
            'AUDIT_MODE=jetstream but could not connect to NATS/JetStream or '
            f"prepare stream '{stream}': {type(exc).__name__}. Refusing to start "
            'without a durable audit sink for write/execute tools.'
        ) from exc

    app_state['audit_nats_connection'] = nc
    return JetStreamAuditWriter(
        js,
        subject=subject,
        dlq_subject=dlq_subject,
        publish_timeout=timeout_ms / 1000.0,
        publish_retries=retries,
    )


async def _resolve_audit_writer() -> AuditWriter:
    """Select the durable audit sink for side-effecting tools (ISSUE 019/039).

    ``AUDIT_MODE=jetstream``: explicit, strong mode — connects to NATS
    JetStream and durably publishes every audit event, failing startup
    closed (any tier) if the broker or stream cannot be prepared. Any other
    value (including unset, the default) preserves the original ISSUE 019
    behavior unchanged: ``AUDIT_LOG_PATH`` set is always used — an
    append-only JSON-Lines file, regardless of tier; unset is allowed only
    outside a deployed tier. ``ENVIRONMENT`` defaults to ``'production'``
    when unset, the same fail-closed default used by
    :func:`astradesk_core.utils.oidc.build_verifier_from_env`, so a deployed
    environment can never silently start with a non-durable sink for
    ``write``/``execute`` tools — it aborts startup instead
    (``INV-AUDIT-5``/``INV-FAIL-CLOSED``). Error messages name only the tier
    or the missing variable, never a secret.
    """
    audit_mode = os.getenv('AUDIT_MODE', '').strip().lower()
    if audit_mode == 'jetstream':
        return await _build_jetstream_audit_writer()

    audit_log_path = os.getenv('AUDIT_LOG_PATH', '').strip()
    if audit_log_path:
        return FileAuditWriter(audit_log_path)

    environment = os.getenv('ENVIRONMENT', 'production').strip().lower()
    if environment in _AUDIT_DEPLOYED_TIERS:
        raise AuditConfigError(
            f"AUDIT_LOG_PATH is required on tier '{environment}': refusing to "
            'start without a durable audit sink for write/execute tools.'
        )
    logger.warning(
        'AUDIT_LOG_PATH not set; using in-process audit writer '
        '(events do not survive a restart). Do not use this in production.'
    )
    return InMemoryAuditWriter()


# --- Application Lifespan (Startup/Shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Handles application startup and shutdown events to manage resources.
    """
    logger.info('API Gateway starting up...')
    install_verifier(app)
    # Fail-closed before any external resource is touched (ISSUE 019): a
    # deployed tier without a durable audit sink must never start, mirroring
    # how the OIDC verifier above already aborts before DB/Redis are touched.
    audit_writer = await _resolve_audit_writer()
    # Fail-closed before any external resource is touched (ISSUE 028): a
    # deployed tier without valid policy (OPA) configuration must never
    # start, mirroring the audit sink and OIDC verifier checks above.
    policy_enforcer: PolicyEnforcer = build_policy_enforcer_from_env()
    app_state['policy_enforcer'] = policy_enforcer

    # --- Initialize connections ---
    # DATABASE_URL/REDIS_URL always resolve (to real values or safe dummy
    # placeholders). Warn instead of crashing when only the fallbacks are in use
    # so local/CI import-time checks stay green.
    if DATABASE_URL == _DEFAULT_DATABASE_URL or REDIS_URL == _DEFAULT_REDIS_URL:
        logger.warning(
            'DATABASE_URL/REDIS_URL not set; using local dummy defaults. '
            'Do not use these in production.'
        )
    pg_pool = await asyncpg.create_pool(DATABASE_URL)
    if not pg_pool:
        raise RuntimeError('Failed to create PostgreSQL connection pool.')
    # decode_responses removed for compatibility with redis 5.x
    redis_client = redis.from_url(REDIS_URL, single_connection_client=True)
    opa_client = OpaClient(url=OPA_URL)

    # --- Initialize core components ---
    # audit_writer/policy_enforcer were already resolved fail-closed above,
    # before any external resource was touched.
    tool_registry = ToolRegistry(audit_writer=audit_writer, policy_enforcer=policy_enforcer)
    # Register built-in tools with mandatory RBAC metadata (ISSUE 016).
    # side_effect + allowed_roles are the source of truth for the choke point;
    # the OIDC layer normalizes identity/roles, RBAC authorizes from those roles.
    await tool_registry.register(
        'get_metrics',
        metrics.get_metrics,
        side_effect=SideEffect.READ,
        description='Get service performance metrics.',
    )
    await tool_registry.register(
        'restart_service',
        ops_actions.restart_service,
        side_effect=SideEffect.EXECUTE,
        allowed_roles={'sre'},
        description='Restart a service deployment.',
    )
    await tool_registry.register(
        'create_ticket',
        tickets_proxy.create_ticket,
        side_effect=SideEffect.WRITE,
        allowed_roles={'it.support', 'sre'},
        description='Create a support ticket.',
    )
    # Discover and load tools from external domain packs.
    load_domain_packs(tool_registry)

    # Boot-time RBAC invariant: abort startup if any registered tool lacks
    # side_effect metadata or any side-effecting tool lacks allowed_roles
    # (fail-closed; catch at boot, not at the first unauthorized call).
    enforce_registration_invariants(
        (info.name, info.side_effect, info.allowed_roles, info.requires_approval)
        for info in tool_registry.infos()
    )

    # llm_planner = LLMPlanner(opa_client=opa_client)
    # rag = RAG(pg_pool=pg_pool, llm_planner=llm_planner)

    llm_planner = LLMPlanner(opa_client=opa_client)
    rag = RAG(llm_planner=llm_planner)
    await rag.ainit()

    memory = Memory(pg_pool=pg_pool, redis_cli=redis_client)
    keyword_planner = KeywordPlanner()

    # --- Initialize agents ---
    agents: dict[str, BaseAgent] = {
        'support': SupportAgent(tool_registry, memory, keyword_planner, rag, llm_planner),
        'billing': BillingAgent(tool_registry, memory, keyword_planner, rag, llm_planner),
        'ops': OpsAgent(tool_registry, memory, keyword_planner, rag, llm_planner),
    }

    # --- Create and store the main orchestrator ---
    app_state['orchestrator'] = AgentOrchestrator(
        llm_planner=llm_planner,
        agents=agents,
        tools=tool_registry,
        pg_pool=pg_pool,
        redis=redis_client,
        opa_client=opa_client,
    )
    logger.info('Agent Orchestrator initialized successfully.')

    # --- Initialize client for Admin API proxy ---
    app_state['admin_api_client'] = httpx.AsyncClient(base_url=ADMIN_API_URL)
    logger.info(f'Admin API client initialized for {ADMIN_API_URL}')

    yield  # Application is now running

    # --- Shutdown logic ---
    logger.info('API Gateway shutting down...')
    if 'orchestrator' in app_state:
        orchestrator = app_state['orchestrator']
        await orchestrator.pg_pool.close()
        await orchestrator.redis.close()
        await provider_router.shutdown()

    if 'audit_nats_connection' in app_state:
        await app_state['audit_nats_connection'].close()
        logger.info('Audit JetStream connection closed.')

    if 'admin_api_client' in app_state:
        await app_state['admin_api_client'].aclose()
        logger.info('Admin API client shut down.')

    if 'policy_enforcer' in app_state:
        aclose = getattr(app_state['policy_enforcer'], 'aclose', None)
        if callable(aclose):
            await aclose()

    logger.info('Resources cleaned up.')


# --- FastAPI Application ---
app = FastAPI(
    title='AstraDesk API Gateway',
    description='Central API for orchestrating AI agents and tools.',
    version='1.2.0',
    lifespan=lifespan,
)


# --- API Endpoints ---


@app.get('/healthz', tags=['Health'])
def healthz() -> dict[str, str]:
    """Provides a simple health check endpoint."""
    return {'status': 'ok'}


# Caller-supplied identity headers that must never be trusted from the inbound
# request: the gateway is the only party permitted to assert them, and only
# after its own OIDC + RBAC gate has run (INV-ADMIN-AUTH-9/11).
_SPOOFABLE_HEADER_PREFIX = b'x-astradesk-'


def _strip_spoofable_headers(
    raw_headers: Iterable[tuple[bytes, bytes]],
) -> list[tuple[bytes, bytes]]:
    """Drop caller-supplied ``X-AstraDesk-*`` headers before proxying upstream.

    These headers would otherwise let a caller self-assert principal/tenant/role
    identity to the Admin API out-of-band of the verified bearer token
    (INV-ADMIN-AUTH-9/11). The ``Authorization`` header is preserved unchanged:
    it is forwarded only because the caller has already been authenticated and
    authorized as ``admin`` by :func:`gateway.auth_dependency.require_admin_role`
    above, and the Admin API independently re-verifies the same JWT
    (INV-ADMIN-AUTH-10).
    """
    return [
        (name, value)
        for name, value in raw_headers
        if not name.lower().startswith(_SPOOFABLE_HEADER_PREFIX)
    ]


@app.api_route(
    '/api/admin/v1/{path:path}',
    methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
    tags=['Admin Proxy'],
    summary='Proxy for the Admin API service',
    description=(
        'Reverse proxy to the Admin API microservice. Requires an authenticated '
        "principal with the 'admin' role before any request reaches the Admin "
        'API (NEW-SEC); the Admin API independently re-verifies the same '
        'bearer token rather than trusting this proxy or network placement.'
    ),
)
async def proxy_to_admin_service(
    request: Request,
    principal: Principal = Depends(require_admin_role),
) -> Response:
    """
    Reverse proxies all requests for /api/admin/v1 to the Admin API service.

    Gated by ``require_admin_role`` (INV-ADMIN-AUTH-1/2/5/6): a missing or
    invalid token is rejected with 401, and an authenticated non-admin caller
    is rejected with 403 — both before any upstream connection is attempted.
    Caller-supplied ``X-AstraDesk-*`` identity headers are stripped from the
    forwarded request; the verified ``Authorization`` header is forwarded
    unchanged (INV-ADMIN-AUTH-9/10/11).
    """
    client: httpx.AsyncClient | None = app_state.get('admin_api_client')
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Admin API client is not initialized.',
        )

    # Construct the URL for the downstream service
    url = httpx.URL(
        path=f"/{request.path_params['path']}",
        query=request.url.query.encode('utf-8'),
    )

    # Build the downstream request
    proxied_req = client.build_request(
        method=request.method,
        url=url,
        headers=_strip_spoofable_headers(request.headers.raw),
        content=request.stream(),
    )

    # Send the request and get the response
    try:
        proxied_resp = await client.send(proxied_req, stream=True)
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Unable to connect to the Admin API service.',
        )

    # Stream the response back to the client. StreamingResponse (not the base
    # Response) is required here: Starlette's base Response only renders
    # bytes/memoryview and cannot accept an async-generator body such as
    # ``aiter_bytes()`` — using it would raise on every successful proxy call,
    # independent of authentication.
    return StreamingResponse(
        content=proxied_resp.aiter_bytes(),
        status_code=proxied_resp.status_code,
        headers=proxied_resp.headers,
    )


@app.post(
    '/v1/run',
    response_model=AgentResponse,
    tags=['Agents'],
    summary='Execute an agent with a given query',
    description='Receives a user query, routes it to the appropriate agent, orchestrates tool execution, and returns a final response.',
)
async def execute_agent(
    agent_request: AgentRequest,
    request: Request,
    principal: Principal = Depends(require_authenticated),
) -> AgentResponse:
    """
    Main endpoint to run an agent.
    - Authenticates the user via JWT.
    - Passes the request to the orchestrator.
    - Handles errors and returns a structured response.
    """
    orchestrator: AgentOrchestrator | None = app_state.get('orchestrator')
    if not orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Orchestrator is not initialized.',
        )

    request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))

    try:
        response = await orchestrator.run(
            agent_request,
            dict(principal.claims),
            request_id,
            roles=tuple(principal.roles),
        )
        return response
    except AgentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PolicyViolationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.exception(f'[{request_id}] Unexpected error during agent execution')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'An internal error occurred: {e}',
        )
