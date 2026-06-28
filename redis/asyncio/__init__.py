# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: redis/asyncio/__init__.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Declares the associated AstraDesk Python package.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""
Minimal stub for redis.asyncio used in the tests.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
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

    async def setex(
        self, key: str, seconds: int | timedelta, value: Any
    ) -> bool:  # pragma: no cover
        await asyncio.sleep(0)
        return True

    async def delete(self, *keys: str) -> int:  # pragma: no cover
        await asyncio.sleep(0)
        return len(keys)

    async def keys(self, pattern: str = '*') -> list[str]:  # pragma: no cover
        await asyncio.sleep(0)
        return []

    async def incr(self, key: str) -> int:  # pragma: no cover
        await asyncio.sleep(0)
        return 1

    async def expire(self, key: str, seconds: int) -> bool:  # pragma: no cover
        await asyncio.sleep(0)
        return True

    async def close(self) -> None:  # pragma: no cover
        await asyncio.sleep(0)

    async def aclose(self) -> None:  # pragma: no cover
        await asyncio.sleep(0)

    def pipeline(self) -> Any:  # pragma: no cover
        raise RuntimeError("pipeline should be mocked in tests")

    async def lrange(self, key: str, start: int, end: int) -> list[Any]:  # pragma: no cover
        raise RuntimeError("lrange should be mocked in tests")


def from_url(url: str, **kwargs: Any) -> Redis:  # pragma: no cover
    # Accept and ignore real-redis kwargs (e.g. single_connection_client,
    # decode_responses) so the stub matches the API surface used by the app.
    return Redis()


__all__: list[str] = ["Redis", "RedisError", "from_url"]
