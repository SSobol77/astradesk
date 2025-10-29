# SPDX-License-Identifier: Apache-2.0
"""File: services/api-gateway/src/runtime/memory.py

Project: astradesk
Pakage: api-gateway

Author: Siergej Sobolewski
Since: 2025-10-29

Memory & audit layer for AstraDesk agents.

Provides async abstraction over:
  - PostgreSQL 18+ (durable dialogue/audit logs)
  - Redis 8+ (ephemeral working memory with TTL)
  - NATS (best-effort audit event emission)

Separates critical persistence (Postgres) from non-blocking telemetry (Redis/NATS)
to protect request latency.

"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import asyncpg
import redis.asyncio as redis

from core.src.astradesk_core.utils.events import events

logger = logging.getLogger(__name__)

# NATS subject for audit events
AUDIT_SUBJECT: str = "astradesk.audit"


class Memory:
    """
    Manages agent memory: dialogue history, working buffers, and audit trail.

    Critical path:
      - PostgreSQL writes (dialogue/audit) → must succeed.
    Best-effort:
      - Redis ops and NATS publish → log & continue on failure.
    """

    __slots__ = ("pg_pool", "redis")

    def __init__(self, pg_pool: asyncpg.Pool, redis_cli: redis.Redis) -> None:
        """
        Initialize memory layer.

        Args:
            pg_pool: Asyncpg connection pool to PostgreSQL 18+.
            redis_cli: Async Redis client.
        """
        if not isinstance(pg_pool, asyncpg.Pool):
            raise TypeError("pg_pool must be asyncpg.Pool")
        if not isinstance(redis_cli, redis.Redis):
            raise TypeError("redis_cli must be redis.asyncio.Redis")

        self.pg_pool = pg_pool
        self.redis = redis_cli

    # ----------------------------------------------------------------------- #
    # Durable Dialogue Storage (PostgreSQL)
    # ----------------------------------------------------------------------- #
    async def store_dialogue(
        self,
        agent: str,
        query: str,
        answer: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Persist agent-user exchange with metadata.

        Schema expectation:
          dialogues(agent text, query text, answer text, meta jsonb, created_at timestamptz)

        Args:
            agent: Agent name (e.g., "support").
            query: User input.
            answer: Agent response.
            meta: Contextual metadata (e.g., session_id, claims).

        Raises:
            asyncpg.PostgresError: On DB failure (critical).
        """
        if not all((agent, query, answer)):
            raise ValueError("agent, query, and answer must be non-empty")

        meta_json = json.dumps(meta or {}, ensure_ascii=False, separators=(",", ":"))

        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO dialogues (agent, query, answer, meta)
                    VALUES ($1, $2, $3, $4)
                    """,
                    agent,
                    query,
                    answer,
                    meta_json,
                )
        except (asyncpg.PostgresError, OSError) as e:
            logger.error(
                f"Failed to store dialogue for agent '{agent}': {e}",
                exc_info=True,
            )
            raise

    # ----------------------------------------------------------------------- #
    # Ephemeral Working Memory (Redis)
    # ----------------------------------------------------------------------- #
    async def append_work(
        self, key: str, value: str, ttl_sec: int = 3600
    ) -> None:
        """
        Append to a Redis list and set TTL atomically.

        Uses pipeline: RPUSH + EXPIRE.
        Best-effort: errors are logged, not raised.

        Args:
            key: Redis list key (e.g., "work:support:session123").
            value: String to append.
            ttl_sec: Time-to-live in seconds.
        """
        if not key or ttl_sec <= 0:
            raise ValueError("key must be non-empty, ttl_sec > 0")

        try:
            pipe = self.redis.pipeline()
            pipe.rpush(key, value.encode("utf-8"))
            pipe.expire(key, ttl_sec)
            await pipe.execute()
        except (redis.RedisError, OSError) as e:
            logger.error(
                f"Failed to append work to Redis key '{key}': {e}", exc_info=True
            )

    async def get_work(self, key: str, count: int = 10) -> List[str]:
        """
        Retrieve latest N items from Redis list (without removal).

        Args:
            key: Redis list key.
            count: Max number of items to return.

        Returns:
            List of strings (most recent first), or empty on error.
        """
        if not key or count <= 0:
            raise ValueError("key must be non-empty, count > 0")

        try:
            raw = await self.redis.lrange(key, -count, -1)
            return [item.decode("utf-8") for item in raw]
        except (redis.RedisError, OSError) as e:
            logger.error(
                f"Failed to get work from Redis key '{key}': {e}", exc_info=True
            )
            return []

    # ----------------------------------------------------------------------- #
    # Audit Trail (PostgreSQL + NATS)
    # ----------------------------------------------------------------------- #
    async def audit(
        self, actor: str, action: str, payload: Dict[str, Any]
    ) -> None:
        """
        Record audit event: first to PostgreSQL (critical), then NATS (best-effort).

        Schema expectation:
          audits(actor text, action text, payload jsonb, created_at timestamptz)

        Args:
            actor: Entity performing action (e.g., "support-agent", "user:alice").
            action: Action name (e.g., "create_ticket").
            payload: Structured event data.

        Raises:
            asyncpg.PostgresError: On PostgreSQL failure.
        """
        if not all((actor, action, payload)):
            raise ValueError("actor, action, and payload must be non-empty")

        payload_json = json.dumps(
            payload, ensure_ascii=False, separators=(",", ":")
        )

        # 1. Critical: PostgreSQL
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO audits (actor, action, payload)
                    VALUES ($1, $2, $3)
                    """,
                    actor,
                    action,
                    payload_json,
                )
        except (asyncpg.PostgresError, OSError) as e:
            logger.critical(
                f"CRITICAL: Failed to write audit for actor='{actor}', action='{action}': {e}",
                exc_info=True,
            )
            raise

        # 2. Best-effort: NATS
        event = {"actor": actor, "action": action, "payload": payload}
        try:
            await events.publish(AUDIT_SUBJECT, event)
        except Exception as e:  # pragma: no cover
            logger.warning(
                f"Best-effort NATS publish failed (subject={AUDIT_SUBJECT}): {e}",
                exc_info=True,
            )
