"""
Minimal stub for redis.asyncio used in the tests.
"""

from __future__ import annotations

import asyncio
from typing import Any


class RedisError(Exception):
    """Base exception compatible with redis.RedisError."""


class Redis:
    """Simple Redis placeholder. Real behaviour is mocked within the tests."""

    async def ping(self) -> bool:  # pragma: no cover
        await asyncio.sleep(0)
        return True

    async def get(self, key: str) -> Any:  # pragma: no cover
        await asyncio.sleep(0)
        return None

    async def set(self, key: str, value: Any, **kwargs: Any) -> bool:  # pragma: no cover
        await asyncio.sleep(0)
        return True

    async def close(self) -> None:  # pragma: no cover
        await asyncio.sleep(0)

    async def aclose(self) -> None:  # pragma: no cover
        await asyncio.sleep(0)

    def pipeline(self) -> Any:  # pragma: no cover
        raise RuntimeError("pipeline should be mocked in tests")

    async def lrange(self, key: str, start: int, end: int):  # pragma: no cover
        raise RuntimeError("lrange should be mocked in tests")


def from_url(url: str, **kwargs: Any) -> Redis:  # pragma: no cover
    # Accept and ignore real-redis kwargs (e.g. single_connection_client,
    # decode_responses) so the stub matches the API surface used by the app.
    return Redis()


__all__ = ["Redis", "RedisError", "from_url"]
