# SPDX-License-Identifier: Apache-2.0
# -*- coding: utf-8 -*-
"""File: services/gateway-python/src/model_gateway/__init__.py
Project: AstraDesk Framework — API Gateway
Description:
    Top-level package initializer for the Model Gateway. Exposes core contracts,
    types, guardrails, planner, and provider routing behind a clean, lazily
    loaded public API. Designed to be transport-agnostic and side-effect free
    on import.

Author: Siergej Sobolewski
Since: 2025-10-07

Responsibilities
----------------
- Define a stable public surface (`__all__`) for callers (apps, services).
- Re-export core types (messages/params/usage/streaming), provider protocol,
  domain exceptions, guardrails utilities/schemas, planner, and router.
- Provide package metadata (`__version__`, `__description__`, etc.).
- Use lazy imports (PEP 562) to keep import time minimal and avoid cycles.
- Never perform I/O or start network clients at import time.

Package layout (excerpt)
------------------------
model_gateway/
  __init__.py       - you are here
  base.py           - contracts, types, domain exceptions, adapters
  guardrails.py     - input/output guardrails and schemas
  llm_planner.py    - LLM-driven planner (plan/summarize)
  router.py         - singleton provider router (lifecycle)
  providers/        - concrete providers (OpenAI/Bedrock/vLLM)

Notes (PL):
------------
Inicjalizator pakietu `model_gateway` dla aplikacji AstraDesk.

Ten plik pełni rolę fasady, definiując publiczne API dla całego pakietu
`model_gateway`. Wykorzystuje zaawansowane techniki, takie jak leniwe importy,
w celu optymalizacji wydajności i unikania zależności cyklicznych.

"""  # noqa: D205

from __future__ import annotations

import importlib
import importlib.metadata as _metadata
import sys
from typing import TYPE_CHECKING, Any, Iterable

# -----------------------------------------------------------------------------
# Metadane Pakietu
# -----------------------------------------------------------------------------
__pkg_name__ = "astradesk"
__description__ = "AstraDesk Model Gateway — contracts, guardrails, planner, and provider routing."
__author__ = "Siergej Sobolewski"
__license__ = "Apache-2.0"

try:
    __version__ = _metadata.version(__pkg_name__)
except _metadata.PackageNotFoundError:
    __version__ = "0.0.0-dev"

# -----------------------------------------------------------------------------
# Definicja Publicznego API (`__all__`)
# -----------------------------------------------------------------------------
# Ta lista definiuje, które symbole są eksportowane, gdy ktoś użyje
# `from model_gateway import *`. Jest zorganizowana w logiczne,
# posortowane alfabetycznie grupy dla maksymalnej czytelności.
__all__ = (
    # --- Z modułu `base` (Kontrakty, Typy, Wyjątki) ---
    "ChatChunk",
    "ChatParams",
    "LLMMessage",
    # --- Z modułu `llm_planner` ---
    "LLMPlanner",
    "LLMProvider",
    "ModelGatewayError",
    "NoopTokenizer",
    # --- Z modułu `guardrails` (Zabezpieczenia i Schematy) ---
    "PlanModel",
    "PlanStepModel",
    "ProviderOverloaded",
    "ProviderServerError",
    "ProviderTimeout",
    "TokenLimitExceeded",
    "Tokenizer",
    "Usage",
    "clip_output",
    # --- Z tego modułu (`__init__.py`) ---
    "get_package_info",
    "is_safe_input",
    # --- Z modułu `router` ---
    "provider_router",
    "to_anthropic_messages",
    "to_openai_messages",
    "validate_conversation",
    "validate_plan_json",
)

# -----------------------------------------------------------------------------
# Importy tylko dla Analizatorów Typów
# -----------------------------------------------------------------------------
if TYPE_CHECKING:  # pragma: no cover
    from .base import (
        ChatChunk, ChatParams, LLMMessage, LLMProvider, ModelGatewayError,
        NoopTokenizer, ProviderOverloaded, ProviderServerError, ProviderTimeout,
        TokenLimitExceeded, Tokenizer, Usage, to_anthropic_messages,
        to_openai_messages, validate_conversation,
    )
    from .guardrails import (
        PlanModel, PlanStepModel, clip_output, is_safe_input, validate_plan_json,
    )
    from .llm_planner import LLMPlanner
    from .router import provider_router


# -----------------------------------------------------------------------------
# Mechanizm Leniwego Ładowania (PEP 562)
# -----------------------------------------------------------------------------
_LAZY_MAPPING = {
    "LLMPlanner": ".llm_planner",
    "provider_router": ".router",
    **{
        symbol: ".base"
        for symbol in (
            "ChatChunk", "ChatParams", "LLMMessage", "LLMProvider",
            "ModelGatewayError", "NoopTokenizer", "ProviderOverloaded",
            "ProviderServerError", "ProviderTimeout", "TokenLimitExceeded",
            "Tokenizer", "Usage", "to_anthropic_messages",
            "to_openai_messages", "validate_conversation",
        )
    },
    **{
        symbol: ".guardrails"
        for symbol in (
            "PlanModel", "PlanStepModel", "clip_output", "is_safe_input",
            "validate_plan_json",
        )
    },
}

def __getattr__(name: str) -> Any:
    """Ładuje eksportowane symbole w sposób leniwy przy pierwszym dostępie."""
    if name in _LAZY_MAPPING:
        module_path = _LAZY_MAPPING[name]
        module = importlib.import_module(module_path, __name__)
        obj = getattr(module, name)
        globals()[name] = obj
        return obj
    raise AttributeError(f"Moduł '{__name__}' nie posiada atrybutu '{name}'.")


def __dir__() -> Iterable[str]:  # pragma: no cover
    """Uzupełnia wynik `dir()` o leniwie ładowane atrybuty."""
    return sorted(set(globals().keys()) | set(__all__))


# -----------------------------------------------------------------------------
# Funkcje Pomocnicze
# -----------------------------------------------------------------------------
def get_package_info() -> dict[str, str]:
    """Zwraca słownik z metadanymi pakietu dla celów diagnostycznych."""
    return {
        "name": __pkg_name__,
        "version": __version__,
        "license": __license__,
        "description": __description__,
        "python_version": sys.version.split()[0],
    }
