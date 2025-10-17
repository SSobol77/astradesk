# SPDX-License-Identifier: Apache-2.0
# -*- coding: utf-8 -*-
"""File: services/gateway-python/src/runtime/__init__.py
Project: AstraDesk Framework — API Gateway (runtime package)
Description:
    Production-facing facade for the `runtime` package. Centralizes the most
    commonly used classes, functions, and singletons (auth, policy, events,
    planners, models, registry, RAG) behind a clean import surface while
    preserving lazy import semantics for heavier modules.

Author: Siergej Sobolewski
Since: 2025-10-07

What this module exposes
------------------------
- Auth (OIDC/JWT):
  * `oidc_cfg` (singleton), `OIDCConfig`
- Events (NATS publisher):
  * `events` (singleton), `Events`
- Policy (RBAC + ABAC):
  * `policy` (facade), `authorize`, `require_role`, `require_any_role`,
    `require_all_roles`, `get_roles`, `AuthorizationError`, `PolicyError`
- Models (Pydantic v2):
  * `AgentName`, `AgentRequest`, `AgentResponse`, `ToolCall`
- Planner (deterministic keyword planner):
  * `KeywordPlanner`
- Tool registry (safe async/sync execution with optional RBAC):
  * `ToolRegistry`, `ToolInfo`
- RAG (vector store + semantic retrieval, pgvector):
  * `RAG` (class)
  * `create_rag(pg_pool, **kwargs)` (lazy factory to avoid heavy imports at startup)

Notes(PL):
------------
Fasada publicznego API pakietu `runtime` dla aplikacji AstraDesk.

Ten moduł pełni rolę centralnego punktu eksportu dla wszystkich kluczowych,
stabilnych komponentów wykonawczych aplikacji. Jego celem jest uproszczenie
importów w innych częściach systemu i zdefiniowanie jasnego, publicznego API.

Główne cechy i zasady projektowe:
- **Leniwe Importy (Lazy Imports)**: Wszystkie komponenty są importowane dopiero
  przy pierwszym użyciu (PEP 562). Minimalizuje to czas startu aplikacji i
  zapobiega cyklom importów, co jest kluczowe w złożonych systemach.
- **Statyczne Typowanie**: Pełne wsparcie dla narzędzi do analizy typów
  (Mypy, Pylance) dzięki warunkowym importom w bloku `TYPE_CHECKING`.
- **Brak Efektów Ubocznych**: Plik nie zawiera logiki biznesowej ani funkcji
  do zarządzania cyklem życia. Odpowiedzialność za tworzenie i zamykanie
  zasobów spoczywa na głównej warstwie aplikacji (`gateway/main.py`).

Przykład użycia:
----------------
# W dowolnym module aplikacji, np. w `gateway/orchestrator.py`:

from runtime import ToolRegistry, Memory, AgentRequest, AuthorizationError

class MyService:
    def __init__(self, registry: ToolRegistry, memory: Memory):
        ...
    def handle_request(self, request: AgentRequest):
        ...
"""  # noqa: D205

from __future__ import annotations

import importlib
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

# -----------------------------------------------------------------------------
# Metadane Pakietu
# -----------------------------------------------------------------------------
__pkg_name__ = "astradesk"
__version__ = "0.2.1"
__author__ = "Siergej Sobolewski"
__license__ = "Apache-2.0"

# -----------------------------------------------------------------------------
# Definicja Publicznego API (`__all__`)
# -----------------------------------------------------------------------------
__all__ = (
    # --- Z modułu `auth` ---
    "oidc_cfg",
    "OIDCConfig",

    # --- Z modułu `events` ---
    "events",

    # --- Z modułu `memory` ---
    "Memory",

    # --- Z modułu `models` ---
    "AgentName",
    "AgentRequest",
    "AgentResponse",
    "ToolCall",

    # --- Z modułu `planner` ---
    "KeywordPlanner",

    # --- Z modułu `policy` ---
    "AuthorizationError",
    "PolicyError",
    "authorize",
    "get_roles",
    "policy",
    "require_all_roles",
    "require_any_role",
    "require_role",

    # --- Z modułu `rag` ---
    "RAG",

    # --- Z modułu `registry` ---
    "ToolInfo",
    "ToolRegistry",
)

# -----------------------------------------------------------------------------
# Importy tylko dla Analizatorów Typów
# -----------------------------------------------------------------------------
if TYPE_CHECKING:  # pragma: no cover
    from .auth import cfg as oidc_cfg, OIDCConfig
    from .events import events
    from .memory import Memory
    from .models import AgentName, AgentRequest, AgentResponse, ToolCall
    from .planner import KeywordPlanner
    from .policy import (
        AuthorizationError,
        PolicyError,
        authorize,
        get_roles,
        policy,
        require_all_roles,
        require_any_role,
        require_role,
    )
    from .rag import RAG
    from .registry import ToolInfo, ToolRegistry

# -----------------------------------------------------------------------------
# Mechanizm Leniwego Ładowania (PEP 562)
# -----------------------------------------------------------------------------
_LAZY_MAPPING = {
    "oidc_cfg": ".auth",
    "OIDCConfig": ".auth",
    "events": ".events",
    "Memory": ".memory",
    "AgentName": ".models",
    "AgentRequest": ".models",
    "AgentResponse": ".models",
    "ToolCall": ".models",
    "KeywordPlanner": ".planner",
    "RAG": ".rag",
    "ToolInfo": ".registry",
    "ToolRegistry": ".registry",
    **{
        symbol: ".policy"
        for symbol in (
            "AuthorizationError",
            "PolicyError",
            "authorize",
            "get_roles",
            "policy",
            "require_all_roles",
            "require_any_role",
            "require_role",
        )
    },
}


def __getattr__(name: str) -> Any:
    """Ładuje eksportowane symbole w sposób leniwy przy pierwszym dostępie."""
    if name in _LAZY_MAPPING:
        module_path = _LAZY_MAPPING[name]
        module = importlib.import_module(module_path, __name__)

        # Dla `oidc_cfg` musimy pobrać atrybut `cfg`
        attr_name = "cfg" if name == "oidc_cfg" else name
        obj = getattr(module, attr_name)

        globals()[name] = obj
        return obj

    raise AttributeError(f"Moduł '{__name__}' nie posiada atrybutu '{name}'.")


def __dir__() -> Iterable[str]:  # pragma: no cover
    """Uzupełnia wynik `dir()` o leniwie ładowane atrybuty."""
    return sorted(set(globals().keys()) | set(__all__))
