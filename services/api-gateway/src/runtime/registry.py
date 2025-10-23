# SPDX-License-Identifier: Apache-2.0
"""File: services/gateway-python/src/runtime/registry.py
Project: AstraDesk Framework — API Gateway
Description:
    Thread-safe runtime Tool Registry for AstraDesk agents. Provides deterministic
    registration/lookup/execution of domain tools (actions) with soft RBAC checks,
    metadata (schema, version, description), and dynamic Domain Pack loading via
    entry points (`astradesk.pack`).

Author: Siergej Sobolewski
Since: 2025-10-17

Overview
--------
- Metadata-first design: each tool is described by `ToolInfo` (name, version,
  description, allowed_roles, schema), enabling auditability and UI introspection.
- Soft RBAC: verifies caller's roles (from `claims`) against `allowed_roles`
  using `runtime.policy.get_roles` when available (with a safe local fallback).
- Unified execution: async callables awaited directly; sync callables executed
  via `asyncio.to_thread`, with exceptions logged and re-raised.
- Domain Packs: discoverable through `importlib.metadata.entry_points(group="astradesk.pack")`;
  each pack exposes `register()` to self-register tools/agents/flows.

Responsibilities
----------------
- Registration API:
  * `register(name, fn, *, description, version, allowed_roles, schema, override)`
  * `unregister(name)`
- Read/Query API:
  * `get(name)`, `get_info(name)`, `exists(name)`, `names()`
- Execution:
  * `execute(name, **kwargs)` — performs RBAC check (if configured), strips
    meta-kwargs (e.g., `claims`) when not accepted by the callable’s signature,
    then runs async/sync accordingly.
- Domain Packs:
  * `load_domain_packs()` — discovers and initializes packs; errors of individual
    packs are logged but do not block startup.

Design principles
-----------------
- Minimal coupling: registry concerns only — metadata, RBAC check, execution.
  Orchestration lives in agents and higher layers.
- Deterministic and auditable: tool names validated by regex `^[A-Za-z0-9._-]{1,128}$`;
  no hidden mutation during execution.
- Concurrency-aware: mutations guarded by `asyncio.Lock`; read paths are lock-free.
- Explicit error taxonomy: `ToolRegistryError`, `ToolRegistrationError`,
  `ToolNotFoundError`, `AuthorizationError` (from policy or local fallback).

Security & safety
-----------------
- RBAC deny-by-default when `allowed_roles` is set and intersection is empty.
- Avoid leaking `claims` into business callables that do not declare such a parameter.
- Log exceptions with context; re-raise to avoid masking failures.
- Keep schemas minimal and non-executable; avoid embedding secrets/PII in metadata.

Performance
-----------
- O(1) lookups for registered tools; registration/deregistration serialized by lock.
- Sync execution offloaded to threads (`asyncio.to_thread`) to keep event loop responsive.
- Domain Pack discovery performed once on startup; failures are isolated and logged.

Usage (example)
---------------
>>> registry = ToolRegistry()
>>> async def create_ticket(title: str, body: str) -> dict: ...
>>> await registry.register(
...     "tickets.create", create_ticket,
...     description="Create a support ticket",
...     allowed_roles={"it.support", "sre"},
... )
>>> result = await registry.execute(
...     "tickets.create", title="VPN issue", body="Cannot connect", claims={"roles": ["sre"]}
... )

Notes
-----
- Prefer narrow `allowed_roles` on sensitive tools; keep schemas descriptive but lean.
- When evolving tool signatures, rely on `get_info(name).signature` for introspection.
- For pack authors: expose a callable/class via entry point returning an object
  with `register()` that registers tools into the registry.

Notes (PL)
----------
- Rejestr narzędzi jest „miękko” zintegrowany z `runtime.policy`; gdy polityka nie jest
  dostępna, używany jest bezpieczny fallback (parsowanie ról z `claims`).
- Rejestr nie importuje warstw UI ani transportu — tylko runtime.
- Błędy pojedynczych Domain Packów nie blokują startu (rejestrowane w logach).

"""  # noqa: D205

from __future__ import annotations

import asyncio
import inspect
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from typing import Any

__all__ = [
    "AuthorizationError",
    "ToolInfo",
    "ToolNotFoundError",
    "ToolRegistrationError",
    "ToolRegistry",
    "ToolRegistryError",
    "load_domain_packs",
]


# RBAC: miękka integracja z runtime.policy
try:
    from runtime.policy import get_roles, AuthorizationError  # type: ignore  # noqa: I001
except ImportError:
    # Jeśli nie ma runtime.policy, użyj fallbacka
    def get_roles(claims: dict | None) -> list[str]:
        if not claims:
            return []
        roles = claims.get("roles")
        if isinstance(roles, str):
            parts = [p.strip() for p in roles.split(",") if p.strip()]
            return parts or [roles]
        if isinstance(roles, (list, tuple, set)):
            return [str(r) for r in roles]
        return []

    class AuthorizationError(PermissionError):
        pass

# Logowanie
_logger = logging.getLogger(__name__)

# Utils
_TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


def _normalize_roles(value: Any) -> list[str]:
    """Ujednolica kształt ról do list[str]. Akceptuje str (CSV), list/tuple/set."""
    if value is None:
        return []
    if isinstance(value, str):
        parts = [p.strip() for p in value.split(",") if p.strip()]
        return parts or [value]
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value]
    return []


def load_domain_packs() -> list[tuple[str, Any]]:
    """Ładuje i rejestruje Domain Packs poprzez entry points (group='astradesk.pack').

    Zabezpieczenia:
    - Zgodność z różnymi wersjami API importlib.metadata.entry_points.
    - Błąd pojedynczego packa nie wstrzymuje startu systemu (logujemy i lecimy dalej).

    Returns:
        list[tuple[str, Any]]: lista (nazwa_entry_pointu, obiekt_packa)
    """
    eps = entry_points()
    if hasattr(eps, "select"):
        # Python 3.11+
        eps = eps.select(group="astradesk.pack")  # type: ignore[assignment]
    else:
        # Python 3.10 i wcześniejsze
        eps = [ep for ep in eps if getattr(ep, "group", None) == "astradesk.pack"]

    loaded: list[tuple[str, Any]] = []
    for ep in eps:
        try:
            factory = ep.load() # type: ignore
            pack = factory()  # preferowana fabryka: klasa/closure zwracająca obiekt packa
            # Konwencja: pack.register() rejestruje agentów/tools/flows w Intent Graph/registry
            pack.register()
            loaded.append((getattr(ep, "name", "<unknown>"), pack))
            _logger.info("Loaded domain pack '%s'", getattr(ep, "name", "<unknown>"))
        except Exception as exc:  # nie blokuj całego systemu przez pojedynczy pack
            _logger.exception(
                "Failed to load/register domain pack '%s': %s",
                getattr(ep, "name", "<unknown>"),
                exc,
            )
    return loaded

# Wyjątki specyficzne dla rejestru narzędzi
class ToolRegistryError(Exception):
    """Baza wyjątków rejestru narzędzi."""

class ToolRegistrationError(ToolRegistryError):
    """Błąd podczas rejestracji narzędzia."""

class ToolNotFoundError(ToolRegistryError, KeyError):
    """Żądane narzędzie nie istnieje."""

# Model metadanych pojedynczego narzędzia
ToolCallable = Callable[..., Any]

@dataclass
class ToolInfo:
    """Metadane zarejestrowanego narzędzia runtime."""

    name: str
    fn: ToolCallable
    description: str = ""
    version: str = "1.0.0"
    allowed_roles: set[str] = field(default_factory=set)
    schema: dict[str, Any] = field(default_factory=dict)

    # Cache techniczny - nie eksponujemy w repr, ustawiany podczas register()
    signature: inspect.Signature | None = field(default=None, repr=False)
    is_coroutine: bool = field(default=False, repr=False)

# Rejestr narzędzi
class ToolRegistry:
    """Prosty, bezpieczny wątkowo rejestr narzędzi dla runtime."""

    def __init__(self) -> None:
        """Inicjalizacja klasa."""
        self._tools: dict[str, ToolInfo] = {}
        self._lock = asyncio.Lock()

    # Mutacje
    async def register(
        self,
        name: str,
        fn: ToolCallable,
        *,
        description: str = "",
        version: str = "1.0.0",
        allowed_roles: set[str] | None = None,
        schema: dict[str, Any] | None = None,
        override: bool = False,
    ) -> None:
        """Rejestruje narzędzie; użyj override=True aby zastąpić istniejące.

        Raises:
            ToolRegistrationError: niepoprawna nazwa/funkcja lub konflikt bez override.

        """
        if not name or not _TOOL_NAME_RE.fullmatch(name):
            raise ToolRegistrationError(
                "Invalid tool name. Allowed chars: letters, digits, '.', '_' and '-'; max 128."
            )
        if not callable(fn):
            raise ToolRegistrationError("fn must be callable")

        info = ToolInfo(
            name=name,
            fn=fn,
            description=description or "",
            version=version or "1.0.0",
            allowed_roles=set(allowed_roles or set()),
            schema=dict(schema or {}),
        )

        # Cache sygnatury i coroutine-ness (tu, zamiast robić to w hot-path execute()).
        try:
            info.signature = inspect.signature(fn)
        except Exception:
            info.signature = None
        info.is_coroutine = inspect.iscoroutinefunction(fn)

        async with self._lock:
            if name in self._tools and not override:
                raise ToolRegistrationError(
                    f"Tool '{name}' already exists (use override=True to replace)."
                )
            self._tools[name] = info
            _logger.info("Registered tool '%s' (override=%s)", name, override)

    async def unregister(self, name: str) -> None:
        """Wyrejestrowuje narzędzie.

        Raises:
            ToolNotFoundError: gdy narzędzie nie istnieje.

        """
        async with self._lock:
            try:
                del self._tools[name]
            except KeyError as e:
                _logger.error("Unregister failed: '%s' not found", name)
                raise ToolNotFoundError(f"Tool '{name}' not found") from e
            else:
                _logger.info("Unregistered tool '%s'", name)

    # Odczyt/enumeracja
    def get(self, name: str) -> ToolCallable:
        """Zwraca funkcję narzędzia (bez metadanych)."""
        try:
            return self._tools[name].fn
        except KeyError as e:
            _logger.error("get('%s'): not found", name)
            raise ToolNotFoundError(f"Tool '{name}' not found") from e

    def get_info(self, name: str) -> ToolInfo:
        """Zwraca pełne metadane narzędzia."""
        try:
            return self._tools[name]
        except KeyError as e:
            _logger.error("get_info('%s'): not found", name)
            raise ToolNotFoundError(f"Tool '{name}' not found") from e

    def names(self) -> list[str]:
        """Lista nazw zarejestrowanych narzędzi."""
        return list(self._tools.keys())

    def exists(self, name: str) -> bool:
        """Czy narzędzie jest zarejestrowane?"""  # noqa: D400
        return name in self._tools

    # Wykonanie
    async def execute(self, name: str, **kwargs: Any) -> Any:
        """Uruchamia narzędzie z przekazanymi argumentami.

        RBAC:
            Jeśli ToolInfo.allowed_roles nie jest puste, wymagamy co najmniej jednej
            roli wspólnej z rolami wyciągniętymi z `claims` (np. z JWT).

        Sync/Async:
            - Funkcje asynchroniczne awaitujemy bezpośrednio.
            - Funkcje synchroniczne odpalamy w wątku (`asyncio.to_thread`).

        Raises:
            AuthorizationError: brak wymaganej roli.
            ToolNotFoundError: gdy narzędzie nie istnieje.
            Dowolny wyjątek biznesowy narzędzia (przepuszczamy, ale logujemy).

        """
        info = self.get_info(name)

        #1 RBAC (jeśli skonfigurowano allowed_roles)
        if info.allowed_roles:
            claims = kwargs.get("claims")
            roles = set(_normalize_roles(get_roles(claims)))
            if not roles.intersection(info.allowed_roles):
                needed = sorted(info.allowed_roles)
                _logger.warning(
                    "RBAC deny: tool='%s' user_roles=%s need_any=%s",
                    name,
                    sorted(roles),
                    needed,
                )
                raise AuthorizationError(
                    f"Access denied: need any of roles {needed} for tool '{name}'."
                )

        #2 Delikatne czyszczenie kwargs:
        #    'claims' to meta - jeśli funkcja nie przyjmuje 'claims', nie przekazujemy go.
        sig = info.signature
        if sig is not None and "claims" not in sig.parameters and "claims" in kwargs:
            kwargs = dict(kwargs)  # płytka kopia
            kwargs.pop("claims", None)

        #3 Uruchomienie narzędzia: obsługa sync/async
        if info.is_coroutine:
            try:
                return await info.fn(**kwargs)
            except Exception as exc:  # logujemy, nie maskujemy
                _logger.exception("Async tool '%s' failed: %s", name, exc)
                raise
        else:
            try:
                return await asyncio.to_thread(info.fn, **kwargs)
            except Exception as exc:
                _logger.exception("Sync tool '%s' failed: %s", name, exc)
                raise
