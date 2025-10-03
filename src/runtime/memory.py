# src/runtime/memory.py
# -*- coding: utf-8 -*-
# Program jest objęty licencją Apache-2.0.
# Copyright 2024
# Autor: Siergej Sobolewski
#
# Cel modułu
# ----------
# Warstwa pamięci i audytu dla AstraDesk:
#  - Postgres (asyncpg): trwałe przechowywanie dialogów i wpisów audytowych,
#  - Redis (redis.asyncio): pamięć robocza (listy, krótkotrwałe bufory, TTL),
#  - NATS (publish-only): emisja zdarzeń audytowych (best-effort) do dalszej obróbki
#    przez subskrybentów (np. mikroserwis Auditor → S3/Elasticsearch).
#
# Projektowe założenia:
#  - Operacje na Postgres realizowane są przez współdzieloną pulę połączeń (asyncpg.Pool),
#  - Operacje Redis wykonywane są przez pipeliny, aby zapewnić atomowość i wydajność,
#  - Emisja eventu audytowego nie blokuje ścieżki krytycznej (błędy są ignorowane),
#  - Do baz zapisujemy *minimalnie potrzebny* kontekst (zasada minimalizacji danych).
#
# Zależności:
#  - Tabela `dialogues(agent, query, answer, meta, created_at)`,
#  - Tabela `audits(actor, action, payload, created_at)`.
#
# Uwaga:
#  - Logika RBAC nie jest częścią tego modułu; RBAC egzekwują narzędzia (tools/*)
#    lub warstwa wyżej (gateway/agents) na podstawie claims z OIDC.
#

from __future__ import annotations

import json
from typing import Any, Optional

import asyncpg
import redis.asyncio as redis

from runtime.events import events


# Stała z tematem NATS do publikacji wpisów audytowych.
AUDIT_SUBJECT: str = "astradesk.audit"


class Memory:
    """
    Klasa odpowiedzialna za persystencję dialogów, buforowanie pracy oraz audyt.

    Atrybuty:
        pg_pool (asyncpg.Pool): współdzielona pula połączeń do Postgresa,
        redis (redis.asyncio.Redis): asynchroniczny klient Redis.

    Przykład użycia (FastAPI dependency):
        memory = Memory(pg_pool, redis_cli)
        await memory.store_dialogue("support", "Jak zrestartować?", "Instrukcja...", {"user":"alice"})
        await memory.audit("support", "create_ticket", {"ticket_id":"TCK-123"})
    """

    def __init__(self, pg_pool: asyncpg.Pool, redis_cli: redis.Redis):
        """
        Inicjalizuje warstwę pamięci.

        :param pg_pool: pula połączeń asyncpg do bazy Postgres
        :param redis_cli: klient Redis (asynchroniczny)
        """
        if pg_pool is None:
            raise ValueError("pg_pool must not be None")
        if redis_cli is None:
            raise ValueError("redis_cli must not be None")

        self.pg_pool = pg_pool
        self.redis = redis_cli

    # -------------------
    # Dialogi (Postgres)
    # -------------------
    async def store_dialogue(
        self,
        agent: str,
        query: str,
        answer: str,
        meta: dict[str, Any],
    ) -> None:
        """
        Zapisuje pełny dialog (zapytanie + odpowiedź) w bazie Postgres.

        :param agent: nazwa agenta (np. 'support' / 'ops')
        :param query: pytanie użytkownika (tekst wejściowy)
        :param answer: odpowiedź wygenerowana przez agenta
        :param meta: metadane kontekstu (np. claims z OIDC, identyfikatory sesji)
        """
        if not agent:
            raise ValueError("agent must not be empty")
        if not query:
            raise ValueError("query must not be empty")
        if answer is None:
            raise ValueError("answer must not be None")

        # Wstawiamy rekord — meta serializowane do JSON (ensure_ascii=False, by zachować polskie znaki).
        async with self.pg_pool.acquire() as con:
            await con.execute(
                "INSERT INTO dialogues(agent, query, answer, meta) VALUES($1, $2, $3, $4)",
                agent,
                query,
                answer,
                json.dumps(meta, ensure_ascii=False),
            )

    # -------------------
    # Pamięć robocza (Redis)
    # -------------------
    async def append_work(self, key: str, value: str, ttl_sec: int = 3600) -> None:
        """
        Dopisuje element do listy roboczej i ustawia TTL na klucz.

        Typowe zastosowania:
          - bufor kroków/rezultatów pracy agenta dla debugowania,
          - krótkotrwałe kolejki zadań (lekki FIFO per klucz).

        :param key: nazwa klucza listy w Redis (np. 'work:support:alice')
        :param value: element tekstowy do dopisania na koniec listy
        :param ttl_sec: czas życia klucza (sekundy), domyślnie 3600
        """
        if not key:
            raise ValueError("key must not be empty")
        if ttl_sec <= 0:
            raise ValueError("ttl_sec must be > 0")

        # Pipelina zapewnia atomowość (rpush + expire).
        pipe = self.redis.pipeline()
        pipe.rpush(key, value.encode("utf-8"))
        pipe.expire(key, ttl_sec)
        await pipe.execute()

    async def get_work(self, key: str, count: int = 10) -> list[str]:
        """
        Pobiera ostatnie `count` elementów z listy roboczej (bez konsumowania).

        :param key: nazwa klucza listy
        :param count: ile elementów pobrać (od końca listy); musi być > 0
        :return: lista wartości (str)
        """
        if not key:
            raise ValueError("key must not be empty")
        if count <= 0:
            raise ValueError("count must be > 0")

        # lrange(-count, -1) → zwraca 'count' ostatnich elementów.
        vals = await self.redis.lrange(key, -count, -1)
        return [v.decode("utf-8") for v in vals]

    # -------------
    # Audyt
    # -------------
    async def audit(self, actor: str, action: str, payload: dict[str, Any]) -> None:
        """
        Zapisuje wpis audytu w Postgres i publikuje event do NATS (best-effort).

        :param actor: wykonawca (np. 'support', 'ops' lub identyfikator użytkownika)
        :param action: nazwa akcji (np. 'create_ticket', 'restart_service')
        :param payload: szczegóły akcji (serializowalne do JSON)

        Gwarancje:
          - zapis do bazy jest *trwały* (transakcja INSERT),
          - publikacja eventu jest *best-effort* (błędy emisji ignorowane),
            dzięki czemu audyt nie blokuje ścieżki użytkownika przy awarii NATS.
        """
        if not actor:
            raise ValueError("actor must not be empty")
        if not action:
            raise ValueError("action must not be empty")
        if payload is None:
            raise ValueError("payload must not be None")

        # 1) Trwały zapis w bazie (Postgres)
        async with self.pg_pool.acquire() as con:
            await con.execute(
                "INSERT INTO audits(actor, action, payload) VALUES($1, $2, $3)",
                actor,
                action,
                json.dumps(payload, ensure_ascii=False),
            )

        # 2) Asynchroniczna publikacja zdarzenia (best-effort).
        #    Nie podnosimy wyjątku – to jest ścieżka telemetryjna, nie krytyczna.
        try:
            await events.publish(
                subject=AUDIT_SUBJECT,
                payload={"actor": actor, "action": action, "payload": payload},
            )
        except Exception:
            # Tu celowo brak re-raise; w realnym systemie dodałbyś log.warning(...)
            # by mieć widoczność problemu z telemetrią.
            pass
