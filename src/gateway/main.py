# src/gateway/main.py
"""
AstraDesk API Gateway (FastAPI, Python 3.11)

Funkcje:
- Health check,
- Endpoint /v1/agents/run: uruchamianie agentów (support/ops) z autoryzacją OIDC/JWT,
- Wstrzykiwanie zależności (Postgres, Redis, RAG, rejestr narzędzi),
- Integracja z Model Gateway (LLM planner) + fallback na keyword planner.

Bezpieczeństwo:
- Guard (Bearer JWT) weryfikuje podpis i claims przez JWKS.

Uwaga:
- Ten plik zakłada obecność modułów: runtime.(auth|memory|rag|planner|registry),
  agents.(support|ops), tools.(tickets_proxy|metrics|ops_actions|weather),
  oraz opcjonalnie model_gateway (LLM router dla planera).
- Redis używany przez pipeline dla atomowych list/TTL.
  
# Copyright (c) 2024 Astradesk Sp. z o.o.
# License: Apache-2.0 
"""

from __future__ import annotations

import os
import asyncpg
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from typing import Any

from runtime.models import AgentRequest, AgentResponse
from runtime.registry import ToolRegistry
from runtime.memory import Memory
from runtime.planner import Planner
from runtime.rag import RAG
from runtime.auth import cfg  # OIDC config/verify

# Narzędzia (tools)
from tools.tickets_proxy import create_ticket
from tools.metrics import get_metrics
from tools.ops_actions import restart_service
from tools.weather import get_weather  # demo tool

# Agenci
from agents.support import SupportAgent
from agents.ops import OpsAgent

# Opcjonalny planner LLM (Model Gateway)
try:
    from model_gateway.llm_planner import LLMPlanner
except Exception:  # pragma: no cover
    LLMPlanner = None  # jeżeli brak zależności, fallback na Planner keywordowy

DB_URL = os.getenv("DATABASE_URL", "postgresql://astradesk:astrapass@db:5432/astradesk")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Konfiguracja OIDC (envy ustawia runtime.auth.cfg)
# OIDC_ISSUER, OIDC_AUDIENCE, OIDC_JWKS_URL

app = FastAPI(title="AstraDesk API", version="0.2.1")

_pg_pool: asyncpg.Pool | None = None
_redis: redis.Redis | None = None
_rag: RAG | None = None
_tools: ToolRegistry | None = None
_keyword_planner = Planner()
_llm_planner: Any | None = None  # instancja LLMPlanner, jeśli dostępna


async def auth_guard(authorization: str | None = Header(None)) -> dict:
    """
    Middleware-dependency: wymusza Bearer JWT; weryfikuje token przez JWKS.

    Zwraca słownik claims (sub, roles, itp.), wykorzystywany m.in. do RBAC.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        claims = await cfg.verify(token)
        return claims
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


@app.on_event("startup")
async def on_startup() -> None:
    """Inicjalizacja połączeń (Postgres, Redis), RAG, rejestru tooli, planera LLM."""
    global _pg_pool, _redis, _rag, _tools, _llm_planner

    _pg_pool = await asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=5)
    _redis = await redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=False)

    _rag = RAG(_pg_pool)

    # Rejestr tooli
    _tools = ToolRegistry()
    _tools.register("create_ticket", create_ticket)
    _tools.register("get_metrics", get_metrics)
    _tools.register("restart_service", restart_service)
    _tools.register("get_weather", get_weather)

    # Opcjonalny planner LLM (wymaga model_gateway i skonfigurowanego providera)
    if LLMPlanner is not None:
        try:
            _llm_planner = LLMPlanner()  # provider wybierany przez env: MODEL_PROVIDER/MODEL_NAME
        except Exception:
            _llm_planner = None  # brak providera → fallback na keyword planner


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Zamyka pule/klientów przy zamykaniu procesu."""
    global _pg_pool, _redis
    if _pg_pool:
        await _pg_pool.close()
    if _redis:
        await _redis.close()


def deps() -> tuple[Memory, RAG, ToolRegistry]:
    """
    Wstrzykiwanie zależności na żądanie (po starcie aplikacji).
    Ułatwia testowanie i zapobiega użyciu niezainicjalizowanych zasobów.
    """
    if not (_pg_pool and _redis and _rag and _tools):
        raise HTTPException(status_code=503, detail="Startup in progress")
    memory = Memory(_pg_pool, _redis)
    return memory, _rag, _tools


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Lekki healthcheck (liveness)."""
    return {"status": "ok"}


@app.post("/v1/agents/run", response_model=AgentResponse)
async def run_agent(req: AgentRequest, claims: dict = Depends(auth_guard)) -> AgentResponse:
    """
    Uruchamia wskazanego agenta z wejściem użytkownika.
    - Autoryzacja: Bearer JWT (claims dostępne do RBAC i audytu).
    - Planner: LLM (jeśli dostępny) → fallback: keyword planner.
    - RAG: fallback kontekstowy.
    """
    memory, rag, tools = deps()

    # RBAC: przekazujemy claims do kontekstu (np. roles → polityki narzędzi)
    context = dict(req.meta)
    context["claims"] = claims

    # Wybór agenta
    if req.agent == "support":
        agent = SupportAgent(tools, memory, _keyword_planner, rag)
    elif req.agent == "ops":
        agent = OpsAgent(tools, memory, _keyword_planner, rag)
    else:
        raise HTTPException(status_code=400, detail="Unknown agent")

    # Planner LLM (opcjonalnie) → jeżeli podejmie decyzję o toolach, agent je wykona,
    # w przeciwnym razie agent użyje keyword-plannera i/lub RAG.
    if _llm_planner:
        try:
            llm_plan = await _llm_planner.make_plan(req.input, available_tools=tools.names(), claims=claims)
            if llm_plan and llm_plan.steps:
                # Wykonanie planu LLM bezpośrednio (z zachowaniem audytu w Memory)
                results = []
                for step in llm_plan.steps:
                    tool = tools.get(step.name)
                    res = await tool(**step.args)
                    results.append(res)
                output = await _llm_planner.summarize(req.input, results)
                await memory.store_dialogue(req.agent, req.input, output, context)
                return AgentResponse(output=output, reasoning_trace_id=f"rt-{req.agent}", used_tools=tools.names())
        except Exception:
            # ciche zejście do klasycznego przebiegu
            pass

    # Klasyczny przebieg agenta (keyword planner + RAG fallback)
    output = await agent.run(req.input, context)
    return AgentResponse(output=output, reasoning_trace_id=f"rt-{req.agent}", used_tools=tools.names())


@app.exception_handler(PermissionError)
async def permission_error_handler(request: Request, exc: PermissionError):
    return JSONResponse(status_code=403, content={"detail": str(exc)})

