# SPDX-License-Identifier: Apache-2.0
"""File: services/gateway-python/src/runtime/memory.py
Project: AstraDesk Framework — API Gateway
Description:
    Memory & audit layer for agents. Provides a thin, async abstraction over
    PostgreSQL (durable dialogue/audit logs), Redis (ephemeral working memory
    with TTL), and NATS (best-effort audit event emission). Separates critical
    persistence paths from non-blocking telemetry to protect request latency.

Author: Siergej Sobolewski
Since: 2025-10-07

Overview
--------
- Durable persistence (PostgreSQL via asyncpg):
  * `store_dialogue()` saves user-agent exchanges with contextual metadata.
  * `audit()` records audit entries transactionally; failures are fatal.
- Ephemeral working memory (Redis):
  * `append_work()` appends work buffers with TTL using pipeline (RPUSH+EXPIRE).
  * `get_work()` retrieves the latest N items without mutation.
- Event emission (NATS):
  * `audit()` emits a JSON audit event to NATS on topic `astradesk.audit`
    using best-effort semantics (errors logged, not raised).

Operational contracts
---------------------
- Critical path:
  * PostgreSQL writes inside `audit()` MUST succeed → raise on failure.
- Best-effort:
  * Redis ops and NATS publishes SHOULD NOT block critical paths → log & continue.
- Encodings:
  * All persisted/emitted payloads are JSON (UTF-8), compact separators.

Security & safety
-----------------
- Do not store secrets or PII unredacted in dialogues/audits.
- Validate inputs: non-empty keys/actors/actions; JSON-serializable payloads.
- Prefer least-privilege DB roles and NATS/Redis credentials (TLS where possible).

Performance
-----------
- Use async connection pool (`asyncpg.Pool`) for Postgres.
- Redis pipeline for atomic RPUSH+EXPIRE; bounded list reads.
- NATS publisher is shared and lazy-connected (see `runtime.events`).

Schema expectations (illustrative)
----------------------------------
- `dialogues(agent text, query text, answer text, meta jsonb, created_at timestamptz default now())`
- `audits(actor text, action text, payload jsonb, created_at timestamptz default now())`
(Actual schema may vary; keep JSONB indexed if you query by fields.)

Usage (example)
---------------
>>> mem = Memory(pg_pool, redis_cli)
>>> await mem.store_dialogue(agent="support", query="VPN issue", answer="Try restart", meta={"tenant":"acme"})
>>> await mem.append_work("work:support:session123", "step:normalize", ttl_sec=1800)
>>> last = await mem.get_work("work:support:session123", count=5)
>>> await mem.audit(actor="support-agent", action="ticket.create", payload={"ticketId": 123})

Notes
-----
- `audit()` first persists to Postgres (critical), then emits to NATS (best-effort).
- Keep payload sizes reasonable; very large blobs belong in object storage.

Notes (PL):
------------
 Zapewnienie warstwy pamięci i audytu dla agentów AstraDesk Framework.
 Moduł zapewnia abstrakcję nad PostgreSQL (trwała persystencja dialogów i logów audytowych),
 Redis (ephemeralna pamięć robocza z TTL) oraz NATS (emisja zdarzeń audytowych w trybie
 best-effort). Oddziela krytyczne ścieżki zapisu od nieblokującej telemetrii, aby
 chronić opóźnienia żądań.

Ta warstwa odpowiada za interakcje z systemami przechowywania danych,
zapewniając spójny interfejs do:
- **Trwałej persystencji**: Zapisywanie historii dialogów i logów audytowych
  w bazie danych PostgreSQL. Operacje te są traktowane jako krytyczne.
- **Pamięci roboczej**: Wykorzystanie Redis do krótkotrwałego przechowywania
  danych, takich jak bufory robocze agentów, z mechanizmem TTL.
- **Emisji zdarzeń**: Publikowanie zdarzeń audytowych do systemu NATS w trybie
  "best-effort", aby telemetria nie blokowała krytycznych operacji.

Projekt opiera się na zasadzie separacji odpowiedzialności i "fail fast"
dla operacji krytycznych, zapewniając integralność i obserwowalność systemu.

"""  # noqa: D205

from __future__ import annotations

import json
import logging
from typing import Any

import asyncpg
import redis.asyncio as redis

from runtime.events import events

logger = logging.getLogger(__name__)

# Stała definiująca temat NATS dla zdarzeń audytowych.
AUDIT_SUBJECT: str = "astradesk.audit"


class Memory:
    """Zarządza persystencją dialogów, pamięcią roboczą i audytem.

    Enkapsuluje logikę interakcji z PostgreSQL, Redis i NATS,
    udostępniając wysokopoziomowe metody dla warstwy agentów.

    Attributes
    ----------
        pg_pool: Współdzielona, asynchroniczna pula połączeń do PostgreSQL.
        redis: Asynchroniczny klient do serwera Redis.

    """

    __slots__ = ("pg_pool", "redis")

    def __init__(self, pg_pool: asyncpg.Pool, redis_cli: redis.Redis) -> None:
        """Inicjalizuje warstwę pamięci.

        Args:
        ----
            pg_pool: Skonfigurowana pula połączeń `asyncpg` do bazy Postgres.
            redis_cli: Skonfigurowany, asynchroniczny klient Redis.

        Raises:
        ------
            ValueError: Jeśli `pg_pool` lub `redis_cli` nie zostaną dostarczone.

        """
        if pg_pool is None:
            raise ValueError("Pula połączeń PostgreSQL (pg_pool) jest wymagana.")
        if redis_cli is None:
            raise ValueError("Klient Redis (redis_cli) jest wymagany.")

        self.pg_pool = pg_pool
        self.redis = redis_cli

    async def store_dialogue(
        self, agent: str, query: str, answer: str, meta: dict[str, Any]
    ) -> None:
        """Zapisuje pełny dialog (zapytanie + odpowiedź) w bazie Postgres.

        Jest to operacja "best-effort" - w razie błędu problem jest logowany,
        ale aplikacja nie jest przerywana.

        Args:
        ----
            agent: Nazwa agenta (np. 'support', 'ops').
            query: Pytanie użytkownika.
            answer: Odpowiedź wygenerowana przez agenta.
            meta: Metadane kontekstowe (np. claims z OIDC, ID sesji).

        """
        if not all((agent, query, answer is not None)):
            raise ValueError("Argumenty agent, query i answer nie mogą być puste.")

        try:
            async with self.pg_pool.acquire() as con:
                await con.execute(
                    "INSERT INTO dialogues(agent, query, answer, meta) VALUES($1, $2, $3, $4)",
                    agent,
                    query,
                    answer,
                    json.dumps(meta, ensure_ascii=False),
                )
        except (asyncpg.PostgresError, OSError) as e:
            logger.error(
                f"Nie udało się zapisać dialogu dla agenta '{agent}'. Błąd: {e}",
                exc_info=True,
            )

    async def append_work(self, key: str, value: str, ttl_sec: int = 3600) -> None:
        """Dopisuje element do listy w Redis i ustawia na niej TTL.

        Używa pipeliny Redis, aby zapewnić atomowość operacji `RPUSH` i `EXPIRE`.
        Operacja "best-effort".

        Args:
        ----
            key: Klucz listy w Redis (np. 'work:support:session123').
            value: Wartość tekstowa do dopisania na koniec listy.
            ttl_sec: Czas życia klucza w sekundach.

        """
        if not key or ttl_sec <= 0:
            raise ValueError("Klucz nie może być pusty, a ttl_sec musi być dodatnie.")

        try:
            pipe = self.redis.pipeline()
            pipe.rpush(key, value.encode("utf-8"))
            pipe.expire(key, ttl_sec)
            await pipe.execute()
        except (redis.RedisError, OSError) as e:
            logger.error(f"Nie udało się zapisać danych roboczych w Redis dla klucza '{key}'. Błąd: {e}", exc_info=True)

    async def get_work(self, key: str, count: int = 10) -> list[str]:
        """Pobiera ostatnie `count` elementów z listy w Redis (bez ich usuwania).

        Args:
        ----
            key: Klucz listy w Redis.
            count: Liczba elementów do pobrania z końca listy.

        Returns:
        -------
            Lista wartości (str), od najstarszej do najnowszej, lub pusta lista w razie błędu.

        """
        if not key or count <= 0:
            raise ValueError("Klucz nie może być pusty, a count musi być dodatnie.")

        try:
            vals = await self.redis.lrange(key, -count, -1)
            return [v.decode("utf-8") for v in vals]
        except (redis.RedisError, OSError) as e:
            logger.error(f"Nie udało się pobrać danych roboczych z Redis dla klucza '{key}'. Błąd: {e}", exc_info=True)
            return []

    async def audit(self, actor: str, action: str, payload: dict[str, Any]) -> None:
        """Zapisuje wpis audytowy w Postgres i emituje zdarzenie do NATS.

        Zapis do bazy danych jest **operacją krytyczną**. Jej niepowodzenie
        spowoduje rzucenie wyjątku i przerwanie operacji. Publikacja do NATS
        jest realizowana w trybie "best-effort".

        Args:
        ----
            actor: Identyfikator wykonawcy akcji (np. nazwa agenta, ID użytkownika).
            action: Nazwa wykonanej akcji (np. 'create_ticket').
            payload: Szczegóły akcji w formacie serializowalnym do JSON.

        Raises:
        ------
            asyncpg.PostgresError: W przypadku błędu zapisu do bazy danych.

        """
        if not all((actor, action, payload is not None)):
            raise ValueError("Argumenty actor, action i payload nie mogą być puste.")

        # 1. Trwały zapis w bazie danych (operacja krytyczna)
        try:
            async with self.pg_pool.acquire() as con:
                await con.execute(
                    "INSERT INTO audits(actor, action, payload) VALUES($1, $2, $3)",
                    actor,
                    action,
                    json.dumps(payload, ensure_ascii=False),
                )
        except (asyncpg.PostgresError, OSError) as e:
            logger.critical(
                f"KRYTYCZNY BŁĄD: Nie udało się zapisać wpisu audytowego dla aktora '{actor}' "
                f"i akcji '{action}'. Operacja zostanie przerwana. Błąd: {e}",
                exc_info=True,
            )
            raise  # Rzuć wyjątek dalej, aby zatrzymać operację.

        # 2. Publikacja zdarzenia do NATS (operacja "best-effort")
        event_payload = {"actor": actor, "action": action, "payload": payload}
        # Moduł `events` ma już wbudowaną logikę "best-effort" i logowanie.
        await events.publish(AUDIT_SUBJECT, event_payload)
