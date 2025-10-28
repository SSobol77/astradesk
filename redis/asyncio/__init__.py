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

    async def close(self) -> None:  # pragma: no cover
        await asyncio.sleep(0)

    def pipeline(self) -> Any:  # pragma: no cover
        raise RuntimeError("pipeline should be mocked in tests")

    async def lrange(self, key: str, start: int, end: int):  # pragma: no cover
        raise RuntimeError("lrange should be mocked in tests")


def from_url(url: str) -> Redis:  # pragma: no cover
    return Redis()


__all__ = ["Redis", "RedisError", "from_url"]
