# src/runtime/registry.py
# -*- coding: utf-8 -*-
# Program jest objęty licencją Apache-2.0.
# Autor: Siergej Sobolewski
#
# Cel modułu
# ----------
# Centralny rejestr narzędzi (tools) agentów:
#  - przechowuje referencje do funkcji narzędzi (async lub sync),
#  - udostępnia metadane (opis, wersja, polityka RBAC, schema argumentów),
#  - zapewnia bezpieczne, zunifikowane wywołanie (execute),
#  - opcjonalnie egzekwuje RBAC na podstawie `allowed_roles` i `claims`.
#
# Wytyczne:
#  - Narzędzia powinny przyjmować argumenty nazwane (**kwargs) oraz zwracać tekst (str)
#    lub serializowalny JSON (który i tak wyżej zostanie zrenderowany do str).
#  - Jeżeli narzędzie jest funkcją *sync*, zostanie uruchomione w wątku
#    z użyciem `asyncio.to_thread`, aby nie blokować event-loopa.
#
# Integracja RBAC:
#  - Jeżeli podczas rejestracji ustawisz `allowed_roles={"sre", "it.support"}`,
#    metoda `execute()` sprawdzi, czy użytkownik (claims) ma *co najmniej jedną*
#    z tych ról. Wymagane jest przekazanie `claims` w **kwargs (np. z middleware OIDC).
#  - Sprawdzanie ról używa `runtime.policy.get_roles` (jeśli dostępne). Gdy moduł
#    policy nie jest dostępny, fallback: oczekuje `claims["roles"]` (lista).
#
# Bezpieczeństwo i stabilność:
#  - walidacja nazw narzędzi (litery/cyfry/._-),
#  - prywatny lock podczas rejestracji/wyrejestrowania,
#  - jasne wyjątki i docstringi do szybkiej diagnozy błędów.
#
# Przykład:
# ---------
# registry = ToolRegistry()
# async def create_ticket(title: str, body: str, **_): ...
# registry.register(
#     "create_ticket", create_ticket,
#     description="Creates a ticket in the system",
#     allowed_roles={"it.support","sre"},
#     version="1.0.0",
#     schema={"title":"str","body":"str"}
# )
# result = await registry.execute("create_ticket", title="VPN down", body="Users cannot connect", claims=claims)

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
    """
    Metadane zarejestrowanego narzędzia.

    Pola:
        name:          unikalna nazwa narzędzia (w rejestrze),
        fn:            funkcja wywoływana przy użyciu execute(),
        description:   krótki opis (do UI/Docs),
        version:       wersja narzędzia (semver; informacyjnie),
        allowed_roles: zbiór ról uprawniających do użycia (RBAC „any-of”),
        schema:        lekka specyfikacja argumentów (np. do walidacji/UI).
    """
    name: str
    fn: ToolCallable
    description: str = ""
    version: str = "1.0.0"
    allowed_roles: set[str] = field(default_factory=set)
    schema: Dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    """
    Rejestr asynchronicznych narzędzi agentów.

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
        """
        Rejestruje narzędzie `name` → `fn` z metadanymi.

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
        """
        Wyrejestrowuje narzędzie.
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
        """Czy narzędzie istnieje w rejestrze?"""
        return name in self._tools

    # -------------------------
    # Wykonanie z RBAC i sync→async
    # -------------------------

    async def execute(self, name: str, **kwargs: Any) -> Any:
        """
        Wykonuje narzędzie o nazwie `name` z przekazanymi argumentami nazwanymi.

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
