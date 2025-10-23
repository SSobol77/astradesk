# core/src/astradesk_core/exceptions.py
# SPDX-License-Identifier: Apache-2.0
"""Centralna taksonomia wyjątków dla platformy AstraDesk."""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx



# --- Główny Wyjątek Aplikacji ---
@dataclass(slots=True)
class AstraDeskError(Exception):
    """Bazowy wyjątek dla wszystkich błędów specyficznych dla aplikacji AstraDesk."""
    message: str

# --- Wyjątki Domenowe (przeniesione z model_gateway) ---

@dataclass(slots=True)
class ModelGatewayError(AstraDeskError):
    """Bazowy wyjątek dla błędów w warstwie Model Gateway."""
    provider: str | None = None
    status_code: int | None = None
    request_id: str | None = None
    retry_after: float | None = None
    details: Any = None
    raw: Any = None
    # ... (implementacja __str__ i metod fabrycznych, tak jak je stworzyliśmy)

@dataclass(slots=True)
class ProviderTimeoutError(ModelGatewayError):
    """Wyjątek rzucany, gdy zapytanie do dostawcy przekroczyło limit czasu."""
    # ... (pełna implementacja, którą stworzyliśmy)

@dataclass(slots=True)
class ProviderOverloadedError(ModelGatewayError):
    """Wyjątek rzucany, gdy dostawca jest przeciążony (np. HTTP 429)."""
    # ... (pełna implementacja, którą stworzyliśmy)

@dataclass(slots=True)
class ProviderServerError(ModelGatewayError):
    """Wyjątek rzucany w przypadku błędu po stronie serwera dostawcy (5xx)."""
    # ... (pełna implementacja, którą stworzyliśmy)

@dataclass(slots=True)
class TokenLimitExceededError(ModelGatewayError):
    """Wyjątek rzucany, gdy przekroczono limit tokenów modelu."""
    # ... (pełna implementacja, którą stworzyliśmy)

# --- Inne Wyjątki Aplikacji ---

class ToolNotFoundError(KeyError, AstraDeskError):
    """Wyjątek rzucany, gdy narzędzie nie zostanie znalezione w rejestrze."""
    pass

class AuthorizationError(PermissionError, AstraDeskError):
    """Wyjątek rzucany w przypadku nieudanej autoryzacji (RBAC/Policy)."""
    pass
