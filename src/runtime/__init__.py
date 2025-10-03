# src/runtime/__init__.py
# -*- coding: utf-8 -*-
# Program jest objęty licencją Apache-2.0.
# Autor: Siergej Sobolewski
#
# Fasada pakietu `runtime` dla AstraDesk:
# ---------------------------------------
#  - Centralizuje importy najczęściej używanych bytów (Memory, RAG, Planner, ToolRegistry,
#    modele Pydantic, RBAC/policy, OIDC cfg, publisher NATS),
#  - Zapewnia pomocnicze funkcje lifecycle: `create_default_components()` i
#    `shutdown_components()` do startu/stopu warstwy runtime w aplikacji,
#  - Umożliwia opcjonalną (best-effort) rejestrację narzędzi z `tools/*`
#    wraz z RBAC (allowed_roles) na poziomie registry.
#
# Uwaga:
#  - Pakiet nie wymusza obecności wszystkich modułów narzędziowych — jeśli któregoś brakuje,
#    rejestracja pominie go bez przerywania procesu (logiczna tolerancja na brak dependencji).
#  - Helpery lifecycle NIE konfigurują mTLS ani Istio; to domena warstwy deploy/mesh.
#  - Do FastAPI wpinamy te komponenty zwykle w on_startup/on_shutdown.
#
# Przykład użycia (FastAPI):
# --------------------------
# from runtime import create_default_components, shutdown_components, AgentRequest, AgentResponse
#
# app = FastAPI()
# state = {}
#
# @app.on_event("startup")
# async def _startup():
#     state.update(await create_default_components(
#         db_url=os.getenv("DATABASE_URL"),
#         redis_url=os.getenv("REDIS_URL"),
#         register_tools=True
#     ))
#
# @app.on_event("shutdown")
# async def _shutdown():
#     await shutdown_components(state)
#
# # dalej w endpointach: state["pg_pool"], state["redis"], state["rag"], state["registry"], ...
#
# Bezpieczeństwo:
#  - RBAC egzekwujemy na poziomie narzędzi (via runtime.policy.authorize lub allowed_roles w registry),
#  - Autoryzację OIDC realizuje `runtime.auth.cfg` (JWT→claims) – wpinamy w middleware/Depends.

from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

# Publiczne API – klasy i narzędzia najczęściej używane
from .models import AgentRequest, AgentResponse, ToolCall
from .registry import ToolRegistry
from .planner import Planner
from .memory import Memory
from .rag import RAG
from .events import events
from .auth import cfg as oidc_cfg

# RBAC/ABAC – zrozumiałe wyjątki i API autoryzacji
try:
    from .policy import (
        get_roles,
        require_role,
        require_any_role,
        require_all_roles,
        authorize,
        policy,
        AuthorizationError,
        PolicyError,
    )
except Exception:  # pragma: no cover - fallback: gdy policy.py nie jest dostępne
    # Minimalne stuby, aby nie wysypywać pakietu. Zalecane jest posiadanie policy.py!
    def get_roles(claims: dict | None) -> list[str]:
        roles = (claims or {}).get("roles")
        return list(roles) if isinstance(roles, (list, tuple)) else []

    def require_role(claims: dict | None, required: str) -> None:
        if required not in set(get_roles(claims)):
            raise PermissionError(f"Access denied: missing role '{required}'.")

    def require_any_role(claims: dict | None, candidates: list[str]) -> None:
        if not set(get_roles(claims)).intersection(set(candidates)):
            raise PermissionError(f"Access denied: need any of roles {sorted(set(candidates))}.")

    def require_all_roles(claims: dict | None, required: list[str]) -> None:
        missing = set(required) - set(get_roles(claims))
        if missing:
            raise PermissionError(f"Access denied: missing roles {sorted(missing)}.")

    def authorize(action: str, claims: dict | None, attrs: dict[str, Any] | None = None) -> None:
        # Brak ABAC w fallbacku – tylko podstawowe role z claims['roles']
        return None

    class PolicyError(Exception):
        pass

    class AuthorizationError(PermissionError):
        pass

    class _DummyPolicyFacade:
        def refresh_now(self) -> None: ...
        def current(self) -> dict[str, Any]: return {}
    policy = _DummyPolicyFacade()


__all__ = [
    # Wersja/fasada
    "__version__",
    # Modele
    "AgentRequest",
    "AgentResponse",
    "ToolCall",
    # Główne runtime
    "ToolRegistry",
    "Planner",
    "Memory",
    "RAG",
    "events",
    "oidc_cfg",
    # RBAC/ABAC
    "get_roles",
    "require_role",
    "require_any_role",
    "require_all_roles",
    "authorize",
    "policy",
    "AuthorizationError",
    "PolicyError",
    # Helpery lifecycle
    "create_default_components",
    "shutdown_components",
]

# Wersjonowanie pakietu runtime – utrzymuj zgodnie z wersją API.
__version__ = "0.2.1"


# ------------------------------
# Helpery lifecycle (async/await)
# ------------------------------
# Tworzą i zamykają podstawowe zasoby: Postgres pool, Redis client, RAG, Registry.
# Dzięki temu w aplikacji nie trzeba duplikować logiki bootstrapu. Wszystko jest
# odporne na brak opcjonalnych modułów (tools/*).


async def _create_pg_pool(db_url: str):
    """
    Tworzy pulę połączeń do Postgresa (asyncpg).

    :param db_url: URI, np. postgresql://user:pass@host:5432/dbname
    :return: asyncpg.Pool
    """
    if not db_url:
        raise ValueError("db_url must not be empty")
    import asyncpg

    # Zachowaj rozsądne domyślne rozmiary – można nadpisać w aplikacji.
    return await asyncpg.create_pool(dsn=db_url, min_size=1, max_size=5)


async def _create_redis(redis_url: str):
    """
    Tworzy klienta Redis (redis.asyncio).

    :param redis_url: URI, np. redis://host:6379/0
    :return: redis.asyncio.Redis
    """
    if not redis_url:
        raise ValueError("redis_url must not be empty")
    import redis.asyncio as redis

    return await redis.from_url(redis_url, encoding="utf-8", decode_responses=False)


async def _register_default_tools(registry: ToolRegistry) -> None:
    """
    Rejestruje domyślne narzędzia (best-effort). Jeżeli jakiś moduł jest nieobecny
    w środowisku, rejestracja go pomija bez błędu. Gdy policy jest dostępne, możesz
    użyć RBAC na poziomie registry przez `allowed_roles`.

    Domyślnie próbujemy zarejestrować:
      - tools.tickets_proxy.create_ticket
      - tools.metrics.get_metrics
      - tools.ops_actions.restart_service
      - tools.weather.get_weather (demo)

    Wszystkie wpisy RBAC są *przykładowe* – dopasuj role do własnych polityk.
    """
    # Uwaga: ToolRegistry.register jest async (w naszej wersji). Dlatego await.
    try:
        from tools.tickets_proxy import create_ticket
        await registry.register(
            "create_ticket",
            create_ticket,
            description="Create a ticket in the ticketing system.",
            version="1.0.0",
            allowed_roles={"it.support", "sre"},  # RBAC: kto może tworzyć ticket
            schema={"title": "str", "body": "str"},
        )
    except Exception:
        pass

    try:
        from tools.metrics import get_metrics
        await registry.register(
            "get_metrics",
            get_metrics,
            description="Fetch service metrics for a time window.",
            version="1.0.0",
            allowed_roles=set(),  # dostęp do odczytu metryk często jest publiczny dla pracowników
            schema={"service": "str", "window": "str"},
        )
    except Exception:
        pass

    try:
        from tools.ops_actions import restart_service
        await registry.register(
            "restart_service",
            restart_service,
            description="Restart a service (SRE-only).",
            version="1.0.0",
            allowed_roles={"sre"},  # RBAC: tylko SRE
            schema={"service": "str"},
        )
    except Exception:
        pass

    try:
        from tools.weather import get_weather
        await registry.register(
            "get_weather",
            get_weather,
            description="Demo weather tool (mock).",
            version="1.0.0",
            allowed_roles=set(),
            schema={"city": "str", "unit": "str?"},
        )
    except Exception:
        pass


async def create_default_components(
    *,
    db_url: str,
    redis_url: str,
    register_tools: bool = True,
    rag_model: str = "sentence-transformers/all-MiniLM-L6-v2",
) -> Dict[str, Any]:
    """
    Tworzy standardowy zestaw komponentów runtime:

    - `pg_pool`:  asyncpg.Pool
    - `redis`:    redis.asyncio.Redis
    - `rag`:      runtime.RAG (z podanym modelem)
    - `registry`: ToolRegistry (opcjonalnie zarejestrowane domyślne narzędzia)

    :param db_url: DSN do Postgresa
    :param redis_url: URL do Redis
    :param register_tools: czy rejestrować domyślne narzędzia z `tools/*`
    :param rag_model: nazwa modelu SentenceTransformer dla RAG
    :return: dict z komponentami, gotowy do włożenia w app.state / global
    """
    # 1) Postgres pool
    pg_pool = await _create_pg_pool(db_url)

    # 2) Redis client
    redis_cli = await _create_redis(redis_url)

    # 3) RAG (embed+retrieve) oparty o pg_pool
    rag = RAG(pg_pool, model=rag_model)

    # 4) Rejestr narzędzi + opcjonalna rejestracja domyślnych tooli
    registry = ToolRegistry()
    if register_tools:
        await _register_default_tools(registry)

    return {
        "pg_pool": pg_pool,
        "redis": redis_cli,
        "rag": rag,
        "registry": registry,
    }


async def shutdown_components(components: Dict[str, Any]) -> None:
    """
    Zamyka/zwalnia komponenty utworzone przez `create_default_components()`.

    Obsługiwane klucze:
      - "pg_pool":  asyncpg.Pool → .close()
      - "redis":    redis.asyncio.Redis → .close()
      - "rag":      runtime.RAG (bez zamykania – trzyma tylko referencje)
      - "registry": ToolRegistry (bez zamykania – czysta pamięć)
      - `events`:   runtime.events (publisher NATS) – jeśli aplikacja go używa globalnie,
                    zalecane jest wywołanie `events.close()` w on_shutdown FastAPI.

    Funkcja jest defensywna – ignoruje brak kluczy/atrybutów.
    """
    # Zamknij Postgres pool
    try:
        pg_pool = components.get("pg_pool")
        if pg_pool:
            await pg_pool.close()
    except Exception:
        pass

    # Zamknij Redis klienta
    try:
        redis_cli = components.get("redis")
        if redis_cli:
            await redis_cli.close()
    except Exception:
        pass

    # RAG i Registry nie wymagają zamykania.
    # NATS publisher (events) możesz domknąć tutaj, jeśli chcesz:
    try:
        await events.close()  # grzeczne zamknięcie połączenia z NATS
    except Exception:
        pass
