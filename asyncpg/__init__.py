"""
Minimal asyncpg stub exposing the bits used in the codebase.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional


class PostgresError(Exception):
    """Exception type matching asyncpg.PostgresError."""


class Pool:
    """Placeholder for asyncpg.Pool used strictly for typing/mocking."""

    async def acquire(self) -> Any:  # pragma: no cover - runtime provides mocks in tests
        raise RuntimeError("Pool.acquire should be mocked in tests.")

    async def release(self, connection: Any) -> None:  # pragma: no cover
        return None


async def create_pool(dsn: str, **_: Any) -> Pool:  # pragma: no cover
    await asyncio.sleep(0)
    return Pool()


__all__ = ["Pool", "PostgresError", "create_pool"]
