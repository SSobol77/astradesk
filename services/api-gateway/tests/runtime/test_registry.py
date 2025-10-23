# SPDX-License-Identifier: Apache-2.0
"""Testy jednostkowe dla ToolRegistry.

Plik: tests/test_registry.py

Zakres:
- Rejestracja i wykonywanie narzędzi (sync/async).
- Kontrola dostępu RBAC (role).
- Obsługa metadanych (schema, allowed_roles).
- Obsługa błędów (ToolNotFoundError, AuthorizationError).
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from src.runtime.registry import (
    AuthorizationError,
    ToolInfo,
    ToolNotFoundError,
    ToolRegistry,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
def registry() -> ToolRegistry:
    """Zwraca świeżą instancję ToolRegistry dla każdego testu."""
    return ToolRegistry()


# === Testy podstawowego funkcjonalności ===

async def test_register_and_execute_async_tool(registry: ToolRegistry) -> None:
    """Testuje zarejestrowanie i wykonanie asynchronicznego narzędzia."""
    async def double(a: int, **_: dict[str, Any]) -> int:
        await asyncio.sleep(0)  # symulacja async
        return a * 2

    await registry.register("double", double, description="x2")
    assert registry.exists("double")
    assert "double" in registry.names()

    result: int = await registry.execute("double", a=21)
    assert result == 42


async def test_register_and_execute_sync_tool(registry: ToolRegistry) -> None:
    """Testuje zarejestrowanie i wykonanie synchronicznego narzędzia."""
    def inc(a: int, **_: dict[str, Any]) -> int:
        return a + 1

    await registry.register("inc", inc)

    result: int = await registry.execute("inc", a=1)
    assert result == 2


# === Testy RBAC ===

async def test_rbac_access_denied(registry: ToolRegistry) -> None:
    """Testuje odmowę dostępu przy niewystarczających rolach."""
    def secret(**_: dict[str, Any]) -> str:
        return "ok"

    await registry.register("secret", secret, allowed_roles={"admin"})

    with pytest.raises(AuthorizationError):
        await registry.execute("secret", claims={"roles": ["user"]})


async def test_rbac_access_allowed_with_single_role_in_list(registry: ToolRegistry) -> None:
    """Testuje dostęp przy roli przekazanej jako lista z jedną rolą."""
    def secret(**_: dict[str, Any]) -> str:
        return "ok"

    await registry.register("secret", secret, allowed_roles={"admin"})

    result: str = await registry.execute("secret", claims={"roles": ["admin"]})
    assert result == "ok"


async def test_rbac_access_allowed_with_multiple_roles_in_list(registry: ToolRegistry) -> None:
    """Testuje dostęp przy wielu rolach przekazanych jako lista (jedna pasuje)."""
    def secret(**_: dict[str, Any]) -> str:
        return "ok"

    await registry.register("secret", secret, allowed_roles={"admin"})

    result: str = await registry.execute("secret", claims={"roles": ["user", "admin"]})
    assert result == "ok"


# === Testy przekazywania argumentów ===

async def test_claims_are_not_passed_if_not_in_signature(registry: ToolRegistry) -> None:
    """Testuje, że 'claims' nie jest przekazywane do narzędzia, jeśli nie ma w sygnaturze."""
    def echo(*, x: int) -> int:
        return x

    await registry.register("echo", echo)

    result: int = await registry.execute("echo", x=7, claims={"roles": ["admin"]})
    assert result == 7


async def test_claims_are_passed_if_in_signature(registry: ToolRegistry) -> None:
    """Testuje, że 'claims' jest przekazywane, jeśli występuje w sygnaturze."""
    def echo_with_claims(*, x: int, claims: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"x": x, "claims": claims}

    await registry.register("echo_with_claims", echo_with_claims)

    result: dict[str, Any] = await registry.execute("echo_with_claims", x=5, claims={"user": "alice"})
    assert result == {"x": 5, "claims": {"user": "alice"}}


# === Testy błędów ===

async def test_get_nonexistent_tool_raises_not_found_error(registry: ToolRegistry) -> None:
    """Testuje, że pobranie nieistniejącego narzędzia rzuca ToolNotFoundError."""
    with pytest.raises(ToolNotFoundError):
        registry.get("missing")


async def test_get_info_nonexistent_tool_raises_not_found_error(registry: ToolRegistry) -> None:
    """Testuje, że pobranie info o nieistniejącym narzędziu rzuca ToolNotFoundError."""
    with pytest.raises(ToolNotFoundError):
        registry.get_info("missing")


async def test_unregister_nonexistent_tool_raises_not_found_error(registry: ToolRegistry) -> None:
    """Testuje, że wyrejestrowanie nieistniejącego narzędzia rzuca ToolNotFoundError."""
    with pytest.raises(ToolNotFoundError):
        await registry.unregister("missing")


# === Testy metadanych ===

async def test_tool_info_contains_correct_metadata(registry: ToolRegistry) -> None:
    """Testuje, że zarejestrowane narzędzie ma poprawne metadane."""
    def example_tool(x: int) -> int:
        return x

    schema: dict[str, Any] = {"x": {"type": "integer", "default": 1}}
    allowed_roles: set[str] = {"admin", "user"}

    await registry.register(
        "example",
        example_tool,
        description="An example tool.",
        version="2.0.0",
        schema=schema,
        allowed_roles=allowed_roles,
    )

    info: ToolInfo = registry.get_info("example")
    assert info.name == "example"
    assert info.description == "An example tool."
    assert info.version == "2.0.0"
    assert info.schema == schema
    assert info.allowed_roles == allowed_roles
    assert info.is_coroutine is False


# === Testy brzegowe ===

async def test_register_tool_with_invalid_name_raises_error(registry: ToolRegistry) -> None:
    """Testuje, że rejestracja narzędzia z niepoprawną nazwą rzuca ToolRegistrationError."""
    from src.runtime.registry import ToolRegistrationError

    def tool() -> None:
        pass

    with pytest.raises(ToolRegistrationError):
        await registry.register("invalid name!", tool)


async def test_register_non_callable_raises_error(registry: ToolRegistry) -> None:
    """Testuje, że rejestracja nie-callable obiektu rzuca ToolRegistrationError."""
    from src.runtime.registry import ToolRegistrationError

    with pytest.raises(ToolRegistrationError):
        await registry.register("bad_tool", "not a function")  # type: ignore[arg-type]


# === Testy asynchroniczności ===

async def test_async_tool_execution_awaits_properly(registry: ToolRegistry) -> None:
    """Testuje, że narzędzie async jest poprawnie awaitowane."""
    async def delayed_echo(x: int) -> int:
        await asyncio.sleep(0.01)
        return x

    await registry.register("delayed", delayed_echo)

    result: int = await registry.execute("delayed", x=99)
    assert result == 99


async def test_sync_tool_execution_runs_in_thread(registry: ToolRegistry) -> None:
    """Testuje, że narzędzie sync jest wykonywane w wątku."""
    def blocking_operation(x: int) -> int:
        import time
        time.sleep(0.01)  # symulacja operacji blokującej
        return x * 2

    await registry.register("blocking", blocking_operation)

    result: int = await registry.execute("blocking", x=5)
    assert result == 10


# === Testy współbieżności ===

async def test_concurrent_registration_and_execution(registry: ToolRegistry) -> None:
    """Testuje bezpieczne działanie w środowisku współbieżnym."""
    async def tool_a() -> str:
        return "A"

    async def tool_b() -> str:
        return "B"

    # Zarejestruj dwa narzędzia współbieżnie
    await asyncio.gather(
        registry.register("tool_a", tool_a),
        registry.register("tool_b", tool_b),
    )

    # Wykonaj je współbieżnie
    results = await asyncio.gather(
        registry.execute("tool_a"),
        registry.execute("tool_b"),
    )

    assert set(results) == {"A", "B"}
