# SPDX-License-Identifier: Apache-2.0
# services/api-gateway/src/gateway/main.py
"""File: services/api-gateway/src/gateway/main.py
Project: AstraDesk Framework — API Gateway
Description: FastAPI entrypoint (Python 3.11+) exposing HTTP endpoints and
             managing application lifecycle via `lifespan`. Centralizes
             dependency injection, auth, logging, and error handling.
Author: Siergej Sobolewski
Since: 2025-10-07.

Notes (PL):
- Ten moduł jest PUNKTEM WEJŚCIOWYM aplikacji (FastAPI).
- Odpowiedzialność ograniczona do:
  * Definiowania endpointów HTTP (np. `/healthz`, `/v1/agents/run`).
  * Zarządzania cyklem życia (startup/shutdown) przez `lifespan`.
  * Wstrzykiwania zależności (stan aplikacji, autoryzacja) przez `Depends`.
  * Globalnej obsługi wyjątków i logowania.
- Logika biznesowa agentów jest delegowana do modułu `orchestrator`.
"""  # noqa: D205
from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import logging
import os
import uuid
import ssl
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import asyncpg
import redis.asyncio as redis
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from jose import JWTError

# --- Importy z projektu ---
from agents.base import BaseAgent
from packages.domain_ops.agents.ops import OpsAgent
from packages.domain_support.agents.support import SupportAgent
from gateway.orchestrator import AgentOrchestrator
from model_gateway.router import provider_router
from runtime.auth import cfg as auth_config
from runtime.memory import Memory
from runtime.models import AgentRequest, AgentResponse
from runtime.planner import KeywordPlanner
from runtime.rag import RAG
from runtime.registry import ToolRegistry

from packages.domain_ops.tools.actions import restart_service
from packages.domain_support.tools.tickets_proxy import create_ticket
from services.api_gateway.src.tools.metrics import get_metrics
from services.api_gateway.src.tools.weather import get_weather


if TYPE_CHECKING:
    from model_gateway.llm_planner import LLMPlanner

try:
    from model_gateway.llm_planner import LLMPlanner
except ImportError:
    LLMPlanner = None

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(dotenv_path=dotenv_path)
print(f"DEBUG: DATABASE_URL wczytany jako: {os.getenv('DATABASE_URL')}")

# --- Konfiguracja i Logowanie ---
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

DB_URL = os.getenv("DATABASE_URL", "postgresql://astradesk:astrapass@db:5432/astradesk")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")


class AppState:
    """Kontener na współdzielone zasoby i stan aplikacji."""
    __slots__ = (
        "pg_pool", "redis", "rag", "tools", "keyword_planner", "llm_planner", "agents"
    )
    
    pg_pool: asyncpg.Pool
    redis: redis.Redis
    rag: RAG
    tools: ToolRegistry
    keyword_planner: KeywordPlanner
    llm_planner: LLMPlanner | None # type: ignore
    agents: dict[str, BaseAgent]


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Zarządza cyklem życia zasobów aplikacji (startup i shutdown)."""
    logger.info("Uruchamianie aplikacji i inicjalizacja zasobów...")
    # Tworzymy kontekst SSL, który nie weryfikuje certyfikatu serwera
    # (prostsze dla developmentu, w produkcji można użyć certyfikatu CA).
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    app_state.pg_pool = await asyncpg.create_pool(
        dsn=DB_URL,
        min_size=2,
        max_size=10,
        ssl=ssl_context
    )

    app_state.redis = await redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=False)
    
    # --- Inicjalizacja komponentów ---
    app_state.rag = RAG(app_state.pg_pool)
    
    tools = ToolRegistry()
    await tools.register("create_ticket", create_ticket, description="Tworzy nowe zgłoszenie w systemie.")
    await tools.register("get_metrics", get_metrics, description="Pobiera metryki dla podanej usługi.")
    await tools.register("restart_service", restart_service, allowed_roles={"sre"}, description="Restartuje wskazaną usługę.")
    await tools.register("get_weather", get_weather, description="Pobiera pogodę dla wskazanego miasta.")
    app_state.tools = tools
    
    app_state.keyword_planner = KeywordPlanner()
    
    if LLMPlanner:
        try:
            # Inicjalizacja planera LLM.
            app_state.llm_planner = LLMPlanner()
            logger.info("Pomyślnie zainicjalizowano LLMPlanner.")
        except Exception as e:
            app_state.llm_planner = None
            logger.warning(f"Nie udało się zainicjalizować LLMPlanner: {e}. Aplikacja będzie działać w trybie fallback.", exc_info=True)
    else:
        app_state.llm_planner = None
        logger.info("LLMPlanner nie jest dostępny. Aplikacja będzie działać w trybie fallback.")

    memory = Memory(app_state.pg_pool, app_state.redis)
    app_state.agents = {
        "support": SupportAgent(tools, memory, app_state.keyword_planner, app_state.rag),
        "ops": OpsAgent(tools, memory, app_state.keyword_planner, app_state.rag),
    }
    
    logger.info("Inicjalizacja zasobów zakończona. Aplikacja gotowa do pracy.")
    
    yield  # Aplikacja działa
    
    # --- Zamykanie zasobów ---
    logger.info("Zamykanie zasobów aplikacji...")
    
    # Bezpieczne zamknięcie providera LLM
    await provider_router.shutdown()
    
    # Zamknięcie puli połączeń do bazy danych
    if hasattr(app_state, 'pg_pool') and app_state.pg_pool:
        await app_state.pg_pool.close()
        
    # Zamknięcie połączenia z Redis
    if hasattr(app_state, 'redis') and app_state.redis:
        await app_state.redis.close()
        
    logger.info("Wszystkie zasoby zostały pomyślnie zamknięte.")


app = FastAPI(title="AstraDesk API", version="0.2.1", lifespan=lifespan)


# --- Zależności (Dependencies) ---

def get_app_state() -> AppState:
    """Zależność FastAPI zwracająca stan aplikacji."""
    return app_state


async def auth_guard(authorization: str | None = Header(None)) -> dict[str, Any]:
    """Weryfikuje token JWT i zwraca jego claims."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Brak nagłówka autoryzacyjnego Bearer.")
    
    token = authorization.split(" ", 1)[1]
    try:
        claims = await auth_config.verify(token)
        return claims
    except JWTError as e:
        logger.warning(f"Błąd walidacji tokena JWT: {e}")
        raise HTTPException(status_code=401, detail=f"Nieprawidłowy token: {e}")
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd podczas weryfikacji tokena: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Wewnętrzny błąd serwera podczas autoryzacji.")


# --- Handlery Błędów ---

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Globalny handler dla nieoczekiwanych błędów."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"Nieobsłużony wyjątek dla żądania {request_id}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Wystąpił wewnętrzny błąd serwera.", "request_id": request_id},
    )

@app.exception_handler(PermissionError)
async def permission_error_handler(request: Request, exc: PermissionError):
    """Handler dla błędów autoryzacji (RBAC)."""
    return JSONResponse(status_code=403, content={"detail": str(exc)})


# --- Endpointy ---

@app.get("/healthz", tags=["Monitoring"])
async def healthz() -> dict[str, str]:
    """Podstawowe sprawdzenie stanu (liveness probe)."""
    return {"status": "ok"}


@app.get("/healthz/deep", tags=["Monitoring"])
async def healthz_deep(state: AppState = Depends(get_app_state)) -> dict[str, str]:
    """Zaawansowane sprawdzenie stanu (readiness probe), weryfikuje połączenie z bazą."""
    try:
        async with state.pg_pool.acquire() as conn:
            await conn.execute("SELECT 1")
        return {"status": "ok", "dependencies": {"postgres": "ok"}}
    except Exception as e:
        logger.error(f"Głębokie sprawdzenie stanu nie powiodło się: {e}")
        raise HTTPException(status_code=503, detail={"postgres": "unavailable"})


# --- Endpoint /v1/agents/run ---
# --- Endpoint /v1/agents/run ---
@app.post("/v1/agents/run", response_model=AgentResponse, tags=["Agents"])
async def run_agent(
    req: AgentRequest,
    # ZMIANA: Przywracamy `request: Request`, ale bez domyślnej wartości.
    # FastAPI wie, jak wstrzyknąć ten obiekt.
    request: Request,
    # UWAGA: Poniższa linia jest wyłączona na potrzeby lokalnego developmentu.
    # Należy ją odkomentować przed wdrożeniem na produkcję.
    # claims: dict[str, Any] = Depends(auth_guard),
    state: AppState = Depends(get_app_state),
) -> AgentResponse:
    """Uruchamia wskazanego agenta i zwraca jego odpowiedź."""
    request_id = str(uuid.uuid4())
    # Ustawiamy request_id w stanie żądania, aby był dostępny
    # w handlerach błędów i potencjalnym middleware.
    request.state.request_id = request_id
    
    logger.info(f"Rozpoczęto przetwarzanie żądania {request_id} dla agenta '{req.agent.value}'")
    
    orchestrator = AgentOrchestrator(
        llm_planner=state.llm_planner,
        agents=state.agents,
        tools=state.tools,
        pg_pool=state.pg_pool,
        redis=state.redis,
    )
    
    # Używamy pustego słownika `claims` na potrzeby testów lokalnych.
    # W środowisku produkcyjnym, `claims` będzie pochodzić z `auth_guard`.
    claims = {} 
    
    response = await orchestrator.run(req, claims, request_id)
    
    logger.info(f"Zakończono przetwarzanie żądania {request_id}")
    return response