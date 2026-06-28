# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: mcp/src/gateway/cache.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for mcp/src/gateway/cache.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""
MCP Response Cache Implementation

Provides caching functionality for MCP tool responses with Redis backend.
"""

import json
from datetime import timedelta
from typing import Any

import redis.asyncio as redis


class CacheConfig:
    """Cache configuration settings"""

    def __init__(
        self,
        enabled: bool = True,
        default_ttl: int = 300,
        max_size_mb: int = 1024,
        per_tool: dict[str, int] | None = None,
    ):
        self.enabled = enabled
        self.default_ttl = default_ttl
        self.max_size_mb = max_size_mb
        self.per_tool = per_tool or {}


class ResponseCache:
    """Cache implementation for MCP responses"""

    def __init__(self, config: CacheConfig, redis_client: redis.Redis):
        self.config = config
        self.redis_client = redis_client

    async def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve cached response"""
        if not self.config.enabled:
            return None

        try:
            cached = await self.redis_client.get(f'mcp:cache:{key}')
            return json.loads(cached) if cached else None
        except Exception:
            return None

    async def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> bool:
        """Cache response with TTL"""
        if not self.config.enabled:
            return False

        try:
            serialized = json.dumps(value)
            if len(serialized) > self.config.max_size_mb * 1024 * 1024:
                return False

            ttl = ttl or self.config.default_ttl
            await self.redis_client.setex(f'mcp:cache:{key}', timedelta(seconds=ttl), serialized)
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        """Remove cached response"""
        try:
            await self.redis_client.delete(f'mcp:cache:{key}')
            return True
        except Exception:
            return False

    async def clear(self) -> bool:
        """Clear all cached responses"""
        try:
            keys = await self.redis_client.keys('mcp:cache:*')
            if keys:
                await self.redis_client.delete(*keys)
            return True
        except Exception:
            return False
