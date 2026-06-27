"""
Minimal asyncpg stub exposing the bits used in the codebase.

It is functional enough to let the API Gateway start up (and tests run) without
a real PostgreSQL server: pools/connections return benign defaults. Real
behaviour is mocked in the unit tests that exercise specific queries.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional


class PostgresError(Exception):
    """Exception type matching asyncpg.PostgresError."""


class Connection:
    """Placeholder connection returning benign defaults for startup checks."""

    async def fetchval(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        return 1

    async def fetch(self, *args: Any, **kwargs: Any) -> list[Any]:  # pragma: no cover
        return []

    async def fetchrow(self, *args: Any, **kwargs: Any) -> Optional[Any]:  # pragma: no cover
        return None

    async def execute(self, *args: Any, **kwargs: Any) -> str:  # pragma: no cover
        return "OK"

    async def executemany(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover
        return None


class _Acquire:
    """Supports both ``await pool.acquire()`` and ``async with pool.acquire()``."""

    def __init__(self, connection: "Connection") -> None:
        self._connection = connection

    def __await__(self):  # pragma: no cover
        async def _get() -> "Connection":
            return self._connection

        return _get().__await__()

    async def __aenter__(self) -> "Connection":  # pragma: no cover
        return self._connection

    async def __aexit__(self, *exc: Any) -> bool:  # pragma: no cover
        return False


class Pool:
    """Placeholder for asyncpg.Pool used strictly for typing/mocking."""

    def acquire(self) -> "_Acquire":  # pragma: no cover
        return _Acquire(Connection())

    async def release(self, connection: Any) -> None:  # pragma: no cover
        return None

    async def execute(self, *args: Any, **kwargs: Any) -> str:  # pragma: no cover
        return "OK"

    async def fetch(self, *args: Any, **kwargs: Any) -> list[Any]:  # pragma: no cover
        return []

    async def fetchval(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        return 1

    async def fetchrow(self, *args: Any, **kwargs: Any) -> Optional[Any]:  # pragma: no cover
        return None

    async def close(self) -> None:  # pragma: no cover
        await asyncio.sleep(0)


async def create_pool(dsn: str, **_: Any) -> Pool:  # pragma: no cover
    await asyncio.sleep(0)
    return Pool()


__all__ = ["Connection", "Pool", "PostgresError", "create_pool"]
