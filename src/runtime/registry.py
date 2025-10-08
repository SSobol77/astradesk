# SPDX-License-Identifier: Apache-2.0
"""File: services/gateway-python/src/runtime/registry.py
Project: AstraDesk Framework — API Gateway
Description:
    Central tool (action) registry for AstraDesk agents. Stores callable
    references with rich metadata, enforces optional RBAC, and provides a
    unified, safe `execute()` path that works for both async and sync tools
    (the latter run via `asyncio.to_thread` to avoid blocking the event loop).

Author: Siergej Sobolewski
Since: 2025-10-07

Overview
--------
- Metadata-first:
  * `ToolInfo`: name, function, description, version, allowed roles (RBAC),
    and a lightweight argument schema for UI/validation.
- Safe execution:
  * Optional RBAC gate (any-of roles) based on JWT claims (via `runtime.policy`).
  * Sync→async bridge for CPU-bound or legacy functions.
  * Gentle kwargs handling: `claims` is stripped if the tool does not accept it.
- Concurrent mutations:
  * Registration/unregistration guarded by an asyncio lock.

Public API
----------
- Registration & mutations:
  * `await register(name, fn, *, description="", version="1.0.0", allowed_roles=None, schema=None, override=False)`
  * `await unregister(name)`
- Lookup & enumeration:
  * `get(name) -> Callable`
  * `get_info(name) -> ToolInfo`
  * `names() -> list[str]`
  * `list_info() -> list[ToolInfo]`
  * `exists(name) -> bool`
- Execution:
  * `await execute(name, **kwargs) -> Any` — RBAC (if configured) + sync/async handling.

Tool contract
-------------
- Callables should accept **named** arguments (`**kwargs`) and return either:
  * `str` (human-readable result), or
  * JSON-serializable structures (rendered upstream as text/JSON).
- For RBAC-aware tools, pass `claims` (OIDC/JWT claims dict) in `kwargs`.
  The registry removes `claims` if the callable does not declare it.

RBAC integration
----------------
- If `ToolInfo.allowed_roles` is non-empty, `execute()` requires that
  the caller holds at least one of those roles.
- Role extraction uses `runtime.policy.get_roles(claims)` when available.
  If the policy module is absent, a safe fallback reads `claims["roles"]`.

Security & safety
-----------------
- Tool names validated by regex: `[A-Za-z0-9._-]{1,128}`.
- Fail-closed RBAC: missing or empty roles deny access when required.
- Avoid leaking sensitive data in exceptions; raise concise, actionable errors.

Performance
-----------
- O(1) lookups by name; lock scope is tight (only for mutations).
- Sync tools run in a thread to keep the event loop responsive.
- Metadata accessors (`get_info`, `list_info`) are zero-alloc copies of dict/list.

Usage (example)
---------------
>>> registry = ToolRegistry()
>>> async def create_ticket(title: str, body: str, **_): return f"Created: {title}"
>>> await registry.register(
...     "create_ticket",
...     create_ticket,
...     description="Creates a ticket in the system",
...     allowed_roles={"it.support", "sre"},
...     version="1.0.0",
...     schema={"title": "str", "body": "str"},
... )
>>> result = await registry.execute(
...     "create_ticket",
...     title="VPN down",
...     body="Users cannot connect",
...     claims={"roles": ["sre"]},
... )

Notes
-----
- Keep schemas lightweight; deep validation belongs to a dedicated layer.
- Prefer idempotent tool semantics where possible; callers may retry.
- Version field is informational; use it to drive UI/help and analytics.

Notes (PL):
----------
Centralny rejestr narzędzi (tools) agentów:
 - przechowuje referencje do funkcji narzędzi (async lub sync),
 - udostępnia metadane (opis, wersja, polityka RBAC, schema argumentów),
 - zapewnia bezpieczne, zunifikowane wywołanie (execute),
 - opcjonalnie egzekwuje RBAC na podstawie `allowed_roles` i `claims`.

Wytyczne:
 - Narzędzia powinny przyjmować argumenty nazwane (**kwargs) oraz zwracać tekst (str)
   lub serializowalny JSON (który i tak wyżej zostanie zrenderowany do str).
 - Jeżeli narzędzie jest funkcją *sync*, zostanie uruchomione w wątku
   z użyciem `asyncio.to_thread`, aby nie blokować event-loopa.

Integracja RBAC:
 - Jeżeli podczas rejestracji ustawisz `allowed_roles={"sre", "it.support"}`,
   metoda `execute()` sprawdzi, czy użytkownik (claims) ma *co najmniej jedną*
   z tych ról. Wymagane jest przekazanie `claims` w **kwargs (np. z middleware OIDC).
 - Sprawdzanie ról używa `runtime.policy.get_roles` (jeśli dostępne). Gdy moduł
   policy nie jest dostępny, fallback: oczekuje `claims["roles"]` (lista).

Bezpieczeństwo i stabilność:
 - walidacja nazw narzędzi (litery/cyfry/._-),
 - prywatny lock podczas rejestracji/wyrejestrowania,
 - jasne wyjątki i docstringi do szybkiej diagnozy błędów.

Przykład:
---------
registry = ToolRegistry()
async def create_ticket(title: str, body: str, **_): ...
registry.register(
    "create_ticket", create_ticket,
    description="Creates a ticket in the system",
    allowed_roles={"it.support","sre"},
    version="1.0.0",
    schema={"title":"str","body":"str"}
)
result = await registry.execute("create_ticket", title="VPN down", body="Users cannot connect", claims=claims)

"""  # noqa: D205

from __future__ import annotations

import asyncio
import inspect
import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Coroutine, Dict, Optional

# Próba miękkiej integracji z warstwą polityk (RBAC). Jeśli brak — fallback.
try:
    from runtime.policy import get_roles, AuthorizationError  # type: ignore
except Exception:  # pragma: no cover
    def get_roles(claims: dict | None) -> list[str]:  # type: ignore
        if not claims:
            return []
        # fallback: najczęstsze pole
        roles = claims.get("roles")
        return list(roles) if isinstance(roles, (list, tuple)) else []

    class AuthorizationError(PermissionError):  # type: ignore
        pass


# -------------------------------------------
# Typy i model metadanych pojedynczego narzędzia
# -------------------------------------------

ToolCallable = Callable[..., Any]  # dopuszczamy async i sync; opakujemy to w execute()

_TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


@dataclass
class ToolInfo:
    """Metadane zarejestrowanego narzędzia.
    Pola:
        name: unikalna nazwa narzędzia (w rejestrze),
        fn: funkcja wywoływana przy użyciu execute(),
        description: krótki opis (do UI/Docs),
        version: wersja narzędzia (semver; informacyjnie),
        allowed_roles: zbiór ról uprawniających do użycia (RBAC „any-of”),
        schema: lekka specyfikacja argumentów (np. do walidacji/UI).
    """  # noqa: D205

    name: str
    fn: ToolCallable
    description: str = ""
    version: str = "1.0.0"
    allowed_roles: set[str] = field(default_factory=set)
    schema: Dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    """Rejestr asynchronicznych narzędzi agentów.

    Funkcje:
      - register(name, fn, ...): rejestracja narzędzia z metadanymi,
      - get(name) / get_info(name): pobranie funkcji lub pełnych metadanych,
      - names() / list_info(): enumeracja,
      - unregister(name): wyrejestrowanie,
      - execute(name, **kwargs): bezpieczne uruchomienie (RBAC + sync→async).

    Uwaga dot. RBAC:
      - Aby aktywować RBAC na poziomie rejestru, ustaw `allowed_roles` przy rejestracji
        i przekazuj `claims` (dict) w **kwargs podczas `execute()`.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolInfo] = {}
        self._lock = asyncio.Lock()

    # -------------------------
    # Rejestracja i mutacje
    # -------------------------

    async def register(
        self,
        name: str,
        fn: ToolCallable,
        *,
        description: str = "",
        version: str = "1.0.0",
        allowed_roles: Optional[set[str]] = None,
        schema: Optional[Dict[str, Any]] = None,
        override: bool = False,
    ) -> None:
        """Rejestruje narzędzie `name` → `fn` z metadanymi.

        :param name: identyfikator narzędzia (A-Za-z0-9._-; max 128)
        :param fn:   funkcja narzędzia (async lub sync)
        :param description: opis użyteczny dla UI/dokumentacji
        :param version: semver narzędzia (informacyjnie)
        :param allowed_roles: zbiorek ról uprawniających do użycia (RBAC)
        :param schema: opcjonalny opis argumentów (np. {"title":"str","body":"str"})
        :param override: jeśli True – nadpisze istniejące narzędzie o tej nazwie
        :raises ValueError: zła nazwa lub duplikat bez override
        """
        if not name or not _TOOL_NAME_RE.fullmatch(name):
            raise ValueError(
                "Invalid tool name. Allowed chars: letters, digits, '.', '_' and '-'; max 128."
            )
        if not callable(fn):
            raise ValueError("fn must be callable")

        info = ToolInfo(
            name=name,
            fn=fn,
            description=description or "",
            version=version or "1.0.0",
            allowed_roles=set(allowed_roles or set()),
            schema=dict(schema or {}),
        )

        async with self._lock:
            if name in self._tools and not override:
                raise ValueError(f"Tool '{name}' already exists (use override=True to replace).")
            self._tools[name] = info

    async def unregister(self, name: str) -> None:
        """Wyrejestrowuje narzędzie.
        :raises KeyError: gdy nie istnieje.
        """
        async with self._lock:
            try:
                del self._tools[name]
            except KeyError as e:
                raise KeyError(f"Tool '{name}' not found") from e

    # -------------------------
    # Odczyt / enumeracja
    # -------------------------

    def get(self, name: str) -> ToolCallable:
        """Zwraca funkcję narzędzia (bez metadanych)."""
        try:
            return self._tools[name].fn
        except KeyError as e:
            raise KeyError(f"Tool '{name}' not found") from e

    def get_info(self, name: str) -> ToolInfo:
        """Zwraca pełne metadane narzędzia."""
        try:
            return self._tools[name]
        except KeyError as e:
            raise KeyError(f"Tool '{name}' not found") from e

    def names(self) -> list[str]:
        """Lista nazw zarejestrowanych narzędzi."""
        return list(self._tools.keys())

    def list_info(self) -> list[ToolInfo]:
        """Lista metadanych wszystkich narzędzi."""
        return list(self._tools.values())

    def exists(self, name: str) -> bool:
        """Sprawdzamy czy narzędzie istnieje w rejestrze."""
        return name in self._tools

    # -------------------------
    # Wykonanie z RBAC i sync→async
    # -------------------------

    async def execute(self, name: str, **kwargs: Any) -> Any:
        """Wykonuje narzędzie o nazwie `name` z przekazanymi argumentami nazwanymi.

        Funkcje bezpieczeństwa:
          - RBAC: jeżeli `allowed_roles` jest ustawione, wymaga co najmniej jednej z tych ról
            w `claims` (kwargs). W razie braku uprawnień rzuca `AuthorizationError`.
          - sync→async: jeżeli funkcja narzędzia jest synchroniczna, uruchamiamy ją w wątku
            (`asyncio.to_thread`) aby nie blokować pętli zdarzeń.

        Konwencja:
          - jeśli wywołujesz `execute(...)`, w kwargs możesz przekazać `claims` (dict),
            który pochodzi z middleware OIDC/JWT; nie zostanie on przekazany do `fn`,
            jeśli `fn` nie deklaruje takiego argumentu (bezpieczne `kwargs.pop`).

        :return: wynik zwrócony przez narzędzie (zwykle str lub struktura JSON).
        :raises KeyError: brak narzędzia o danej nazwie,
        :raises AuthorizationError: brak wymaganych ról (RBAC).
        """
        info = self.get_info(name)

        # 1) Egzekwowanie RBAC (jeśli skonfigurowano allowed_roles)
        if info.allowed_roles:
            # claims może pochodzić z FastAPI dependency (auth_guard)
            claims = kwargs.get("claims")
            roles = set(get_roles(claims))
            if not roles.intersection(info.allowed_roles):
                needed = sorted(info.allowed_roles)
                raise AuthorizationError(
                    f"Access denied: need any of roles {needed} for tool '{name}'."
                )

        # 2) Delikatne czyszczenie kwargs: `claims` to meta – narzędzie może go nie przyjmować
        #    (większość narzędzi go nie potrzebuje).
        sig = None
        try:
            sig = inspect.signature(info.fn)
        except Exception:
            pass
        if sig is not None and "claims" not in sig.parameters and "claims" in kwargs:
            # nie przekazujemy 'claims' gdy funkcja go nie posiada
            kwargs = dict(kwargs)  # kopia
            kwargs.pop("claims", None)

        # 3) Uruchomienie narzędzia: poprawna obsługa sync/async
        if inspect.iscoroutinefunction(info.fn):
            # Funkcja jest asynchroniczna, można ją 'await'
            return await info.fn(**kwargs)
        else:
            # Funkcja jest synchroniczna, uruchom w osobnym wątku
            return await asyncio.to_thread(info.fn, **kwargs)
