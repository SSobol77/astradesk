"""
Persistence and audit utilities for the mocked runtime.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import asyncpg
import redis.asyncio as redis

from core.src.astradesk_core.utils import events

logger = logging.getLogger(__name__)

AUDIT_SUBJECT = "astradesk.audit"


class Memory:
    def __init__(self, *, pg_pool: asyncpg.Pool, redis_cli: redis.Redis) -> None:
        if pg_pool is None:
            raise ValueError("Pula połączeń PostgreSQL (pg_pool) jest wymagana.")
        if redis_cli is None:
            raise ValueError("Klient Redis (redis_cli) jest wymagany.")
        self.pg_pool = pg_pool
        self.redis = redis_cli

    async def store_dialogue(self, agent: str, query: str, answer: str, meta: Optional[Dict[str, Any]]) -> None:
        if not agent or not query or not answer or meta is None:
            raise ValueError("agent, query, answer oraz meta muszą być podane.")
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO dialogues(agent, query, answer, meta) VALUES($1, $2, $3, $4)",
                    agent,
                    query,
                    answer,
                    json.dumps(meta, ensure_ascii=False),
                )
        except asyncpg.PostgresError as exc:
            logger.error("Nie udało się zapisać dialogu: %s", exc)

    async def append_work(self, key: str, value: str, ttl_sec: int = 3600) -> None:
        if not key or not value or ttl_sec <= 0:
            raise ValueError("key i value muszą być niepuste, ttl_sec > 0.")
        pipe = self.redis.pipeline()
        try:
            pipe.rpush(key, value.encode("utf-8"))
            pipe.expire(key, ttl_sec)
            await pipe.execute()
        except redis.RedisError as exc:
            logger.error("Nie udało się zapisać danych roboczych w Redis: %s", exc)

    async def get_work(self, key: str, count: int = 10) -> List[str]:
        if not key or count <= 0:
            raise ValueError("key musi być niepusty, count > 0.")
        try:
            entries = await self.redis.lrange(key, -count, -1)
            return [entry.decode("utf-8") for entry in entries]
        except redis.RedisError as exc:
            logger.error("Nie udało się pobrać danych roboczych z Redis: %s", exc)
            return []

    async def audit(self, actor: str, action: str, payload: Dict[str, Any]) -> None:
        if not actor or not action or payload is None:
            raise ValueError("actor, action oraz payload muszą być podane.")
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO audits(actor, action, payload) VALUES($1, $2, $3)",
                    actor,
                    action,
                    json.dumps(payload, ensure_ascii=False),
                )
        except asyncpg.PostgresError as exc:
            logger.critical("KRYTYCZNY BŁĄD zapisu audytu: %s", exc)
            raise

        try:
            await events.publish(AUDIT_SUBJECT, {"actor": actor, "action": action, "payload": payload})
        except Exception as exc:  # noqa: BLE001 - best-effort semantics
            logger.warning("NATS publish failed, kontynuuję bez przerywania: %s", exc)
