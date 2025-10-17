# SPDX-License-Identifier: Apache-2.0
"""Testy jednostkowe dla modułu src.runtime.memory (klasa Memory).

Zakres:
- Inicjalizacja i walidacja zależności.
- Operacje na trwałej pamięci (PostgreSQL):
  - Poprawny zapis dialogu.
  - Obsługa błędów bazy danych przy zapisie dialogu (best-effort).
  - Poprawny zapis audytu (ścieżka krytyczna).
  - Obsługa błędów bazy danych przy zapisie audytu (musi rzucić wyjątek).
- Operacje na pamięci roboczej (Redis):
  - Poprawne dopisywanie do listy i ustawianie TTL.
  - Poprawne pobieranie danych z listy.
  - Obsługa błędów Redis (best-effort).
- Emisja zdarzeń (NATS):
  - Poprawne wywołanie publikacji zdarzenia po udanym audycie.
  - Weryfikacja, że błąd NATS nie przerywa operacji.
- Walidacja danych wejściowych dla wszystkich metod publicznych.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest
import redis.asyncio as redis

# Ścieżka do mockowania modułu events
EVENTS_MODULE_PATH = "src.runtime.memory.events"

# Importujemy klasę i stałą do testowania
from src.runtime.memory import AUDIT_SUBJECT, Memory


@pytest.fixture
def mock_pg_pool():
    """Zwraca poprawnie skonfigurowanego mocka dla puli połączeń asyncpg."""
    pool = AsyncMock()
    conn = AsyncMock()
    
    # OSTATECZNA POPRAWKA: Definiujemy jawnie asynchroniczny menedżer kontekstu
    context_manager = AsyncMock()
    context_manager.__aenter__.return_value = conn
    context_manager.__aexit__ = AsyncMock(return_value=None) # To zapobiega zawieszaniu się
    
    pool.acquire = MagicMock(return_value=context_manager)
    return pool


@pytest.fixture
def mock_redis():
    """Zwraca poprawnie skonfigurowanego mocka dla klienta redis.asyncio.Redis."""
    redis_cli = AsyncMock(spec=redis.Redis)
    pipe = AsyncMock()
    pipe.rpush = MagicMock()
    pipe.expire = MagicMock()
    redis_cli.pipeline = MagicMock(return_value=pipe)
    # lrange musi być korutyną
    redis_cli.lrange = AsyncMock()
    return redis_cli


@pytest.fixture
def mock_events():
    """Mockuje globalny obiekt `events` do publikacji w NATS."""
    with patch(EVENTS_MODULE_PATH) as mock:
        mock.publish = AsyncMock()
        yield mock


@pytest.fixture
def memory_instance(mock_pg_pool, mock_redis):
    """Zwraca instancję klasy Memory z zamockowanymi zależnościami."""
    return Memory(pg_pool=mock_pg_pool, redis_cli=mock_redis)


# --- Testy inicjalizacji ---

def test_memory_initialization_success(mock_pg_pool, mock_redis):
    mem = Memory(pg_pool=mock_pg_pool, redis_cli=mock_redis)
    assert mem.pg_pool is mock_pg_pool
    assert mem.redis is mock_redis


def test_memory_initialization_fails_without_pg_pool(mock_redis):
    with pytest.raises(ValueError, match="Pula połączeń PostgreSQL .* jest wymagana"):
        Memory(pg_pool=None, redis_cli=mock_redis)


def test_memory_initialization_fails_without_redis(mock_pg_pool):
    with pytest.raises(ValueError, match="Klient Redis .* jest wymagany"):
        Memory(pg_pool=mock_pg_pool, redis_cli=None)


# --- Testy store_dialogue ---

@pytest.mark.parametrize("agent, query, answer", [("", "q", "a"), ("a", "", "a"), ("a", "q", None)])
async def test_store_dialogue_invalid_args_raises_error(memory_instance, agent, query, answer):
    with pytest.raises(ValueError):
        await memory_instance.store_dialogue(agent, query, answer, meta={})


async def test_store_dialogue_success(memory_instance, mock_pg_pool):
    conn = mock_pg_pool.acquire.return_value.__aenter__.return_value
    meta = {"user": "test", "id": 123}
    await memory_instance.store_dialogue("agent1", "pytanie", "odpowiedź", meta)
    conn.execute.assert_awaited_once_with(
        "INSERT INTO dialogues(agent, query, answer, meta) VALUES($1, $2, $3, $4)",
        "agent1", "pytanie", "odpowiedź", json.dumps(meta, ensure_ascii=False)
    )


async def test_store_dialogue_db_error_is_logged_not_raised(memory_instance, mock_pg_pool, caplog):
    conn = mock_pg_pool.acquire.return_value.__aenter__.return_value
    conn.execute.side_effect = asyncpg.PostgresError("Błąd połączenia")
    await memory_instance.store_dialogue("agent1", "q", "a", {})
    assert "Nie udało się zapisać dialogu" in caplog.text


# --- Testy append_work ---

@pytest.mark.parametrize("key, value, ttl", [("", "val", 3600), ("key", "val", 0), ("key", "val", -1)])
async def test_append_work_invalid_args_raises_error(memory_instance, key, value, ttl):
    with pytest.raises(ValueError):
        await memory_instance.append_work(key, value, ttl_sec=ttl)


async def test_append_work_success(memory_instance, mock_redis):
    pipe = mock_redis.pipeline.return_value
    key, value, ttl = "work:1", "dane", 1800
    await memory_instance.append_work(key, value, ttl_sec=ttl)
    pipe.rpush.assert_called_once_with(key, value.encode("utf-8"))
    pipe.expire.assert_called_once_with(key, ttl)
    pipe.execute.assert_awaited_once()


async def test_append_work_redis_error_is_logged_not_raised(memory_instance, mock_redis, caplog):
    pipe = mock_redis.pipeline.return_value
    pipe.execute.side_effect = redis.RedisError("Błąd Redis")
    await memory_instance.append_work("work:1", "dane")
    assert "Nie udało się zapisać danych roboczych w Redis" in caplog.text


# --- Testy get_work ---

@pytest.mark.parametrize("key, count", [("", 10), ("key", 0), ("key", -1)])
async def test_get_work_invalid_args_raises_error(memory_instance, key, count):
    with pytest.raises(ValueError):
        await memory_instance.get_work(key, count=count)


async def test_get_work_success(memory_instance, mock_redis):
    key, count = "work:1", 5
    redis_return = [b"krok1", b"krok2"]
    mock_redis.lrange.return_value = redis_return
    result = await memory_instance.get_work(key, count=count)
    mock_redis.lrange.assert_awaited_once_with(key, -count, -1)
    assert result == ["krok1", "krok2"]


async def test_get_work_redis_error_returns_empty_list(memory_instance, mock_redis, caplog):
    mock_redis.lrange.side_effect = redis.RedisError("Błąd Redis")
    result = await memory_instance.get_work("work:1")
    assert result == []
    assert "Nie udało się pobrać danych roboczych z Redis" in caplog.text


# --- Testy audit ---

@pytest.mark.parametrize("actor, action, payload", [("", "act", {}), ("act", "", {}), ("act", "act", None)])
async def test_audit_invalid_args_raises_error(memory_instance, actor, action, payload):
    with pytest.raises(ValueError):
        await memory_instance.audit(actor, action, payload)


async def test_audit_success(memory_instance, mock_pg_pool, mock_events):
    conn = mock_pg_pool.acquire.return_value.__aenter__.return_value
    actor, action, payload = "agent1", "create_ticket", {"id": 1}
    expected_event_payload = {"actor": actor, "action": action, "payload": payload}
    await memory_instance.audit(actor, action, payload)
    conn.execute.assert_awaited_once_with(
        "INSERT INTO audits(actor, action, payload) VALUES($1, $2, $3)",
        actor, action, json.dumps(payload, ensure_ascii=False)
    )
    mock_events.publish.assert_awaited_once_with(AUDIT_SUBJECT, expected_event_payload)


async def test_audit_db_error_is_critical_and_raised(memory_instance, mock_pg_pool, mock_events, caplog):
    conn = mock_pg_pool.acquire.return_value.__aenter__.return_value
    conn.execute.side_effect = asyncpg.PostgresError("Krytyczny błąd zapisu")
    with pytest.raises(asyncpg.PostgresError, match="Krytyczny błąd zapisu"):
        await memory_instance.audit("agent1", "action", {})
    assert "KRYTYCZNY BŁĄD" in caplog.text
    mock_events.publish.assert_not_awaited()


async def test_audit_nats_error_is_ignored(memory_instance, mock_pg_pool, mock_events):
    conn = mock_pg_pool.acquire.return_value.__aenter__.return_value
    mock_events.publish.side_effect = Exception("NATS nie działa")
    await memory_instance.audit("agent1", "action", {})
    conn.execute.assert_awaited_once()
    mock_events.publish.assert_awaited_once()
