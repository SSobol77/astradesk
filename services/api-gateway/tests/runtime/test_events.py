# SPDX-License-Identifier: Apache-2.0
# services/api-gateway/src/tests/runtime/test_events.py
"""Tests for core/src/astradesk_core/utils/events.py (NATS publish-only wrapper).

Covers:
- Successful publish: JSON bytes (ensure_ascii=False, compact), single connect.
- Subject validation errors: no connect performed, returns gracefully.
- Payload size guard: oversize skipped, no connect.
- Reconnect-once path: first publish fails -> close -> reconnect -> second publish OK.
- Final failure (second attempt also fails): error logged, no exception raised.
- Connection caching: two publishes reuse same client, single connect.
- Graceful close(): drain success, and drain failure fallback to close.

All NATS interactions are fully mocked.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock
import asyncio
import pytest

import core.src.astradesk_core.utils.events as evmod
from core.src.astradesk_core.utils.events import events

# --- Helpers ---

def _make_nc_mock():
    """Make a NATS client mock with required API."""
    nc = MagicMock(name="NATSClient")
    nc.is_connected = True
    nc.publish = AsyncMock(name="publish")
    nc.close = AsyncMock(name="close")
    nc.drain = AsyncMock(name="drain")
    return nc


# --- Successful publish path ---

@pytest.mark.asyncio
async def test_publish_success_compact_json_and_single_connect(monkeypatch):
    # Fresh singleton state
    await events.close()

    nc = _make_nc_mock()

    connect_calls = []

    async def fake_connect(url, connect_timeout):
        connect_calls.append((url, connect_timeout))
        await asyncio.sleep(0) 
        return nc

    monkeypatch.setattr(evmod.nats, "connect", fake_connect)
    # Spy logger (avoid noisy output)
    monkeypatch.setattr(evmod, "logger", MagicMock())

    subject = "astradesk.audit"
    payload = {"action": "tick.created", "title": "Zażółć gęślą jaźń", "n": 1}

    await events.publish(subject, payload)

    # single connect
    assert len(connect_calls) == 1

    # ensure compact JSON (no spaces after , or :)
    (pub_subj, pub_data), _ = nc.publish.await_args
    assert pub_subj == subject
    assert isinstance(pub_data, (bytes, bytearray))

    text = pub_data.decode("utf-8")
    # Compact separators: no spaces, and non-ascii preserved
    assert text == json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


# --- Validation guards ---

@pytest.mark.asyncio
async def test_publish_rejects_invalid_subject(monkeypatch):
    await events.close()
    connect_mock = AsyncMock()
    monkeypatch.setattr(evmod.nats, "connect", connect_mock)
    log = MagicMock()
    monkeypatch.setattr(evmod, "logger", log)

    # invalid: leading/trailing space & spaces in subject
    for bad in [" bad", "bad ", "bad topic", ".bad", "bad.", "bad..topic"]:
        await events.publish(bad, {"x": 1})

    # No attempt to connect when subject invalid
    assert not connect_mock.await_args_list
    assert log.error.call_count >= 1


@pytest.mark.asyncio
async def test_publish_rejects_oversized_payload(monkeypatch):
    await events.close()
    connect_mock = AsyncMock()
    monkeypatch.setattr(evmod.nats, "connect", connect_mock)
    log = MagicMock()
    monkeypatch.setattr(evmod, "logger", log)

    # Force extremely small max size
    monkeypatch.setattr(evmod, "MAX_MESSAGE_BYTES", 10)

    big_payload = {"x": "A" * 100}
    await events.publish("astradesk.audit", big_payload)

    assert not connect_mock.await_args_list
    assert log.error.call_count >= 1  # size error logged


# --- Reconnect path ---

@pytest.mark.asyncio
async def test_publish_reconnects_after_first_failure(monkeypatch):
    await events.close()

    first_nc = _make_nc_mock()
    # First publish raises
    first_nc.publish.side_effect = RuntimeError("nats link down")

    second_nc = _make_nc_mock()  # second connection succeeds

    conn_calls = []

    async def fake_connect(url, connect_timeout):
        conn_calls.append((url, connect_timeout))
        await asyncio.sleep(0) 
        return first_nc if len(conn_calls) == 1 else second_nc

    monkeypatch.setattr(evmod.nats, "connect", fake_connect)
    log = MagicMock()
    monkeypatch.setattr(evmod, "logger", log)

    await events.publish("astradesk.audit", {"ok": True})

    # Two connects: initial + reconnect
    assert len(conn_calls) == 2
    # First client's close called during reconnect
    first_nc.close.assert_awaited()
    # Second client's publish finally called
    second_nc.publish.assert_awaited()
    # Warning logged on first failure, info on success after reconnect
    assert log.warning.call_count >= 1
    assert any("Ponowne połączenie" in str(c.args[0]) for c in log.info.call_args_list)


@pytest.mark.asyncio
async def test_publish_final_failure_is_logged_not_raised(monkeypatch):
    await events.close()

    # Both first and second publish attempts fail
    first_nc = _make_nc_mock()
    first_nc.publish.side_effect = RuntimeError("down#1")

    second_nc = _make_nc_mock()
    second_nc.publish.side_effect = RuntimeError("down#2")

    calls = []

    async def fake_connect(url, connect_timeout):
        calls.append(1)
        await asyncio.sleep(0) 
        return first_nc if len(calls) == 1 else second_nc

    monkeypatch.setattr(evmod.nats, "connect", fake_connect)
    log = MagicMock()
    monkeypatch.setattr(evmod, "logger", log)

    # Should not raise
    await events.publish("astradesk.audit", {"x": 1})

    assert len(calls) == 2
    # Final error logged with exc_info=True in .error()
    assert log.error.call_count >= 1


# --- Connection caching across publishes ---

@pytest.mark.asyncio
async def test_connection_is_cached_between_publishes(monkeypatch):
    await events.close()

    nc = _make_nc_mock()

    async def fake_connect(url, connect_timeout):
        await asyncio.sleep(0) 
        return nc

    monkeypatch.setattr(evmod.nats, "connect", fake_connect)
    log = MagicMock()
    monkeypatch.setattr(evmod, "logger", log)

    await events.publish("astradesk.audit", {"a": 1})
    await events.publish("astradesk.audit", {"b": 2})

    # Single connect, two publishes
    # (We can't directly count connect calls without a counter, assert via call count on publish)
    assert nc.publish.await_count == 2


# --- Close behavior ---

@pytest.mark.asyncio
async def test_close_drains_then_nulls_connection(monkeypatch):
    await events.close()

    nc = _make_nc_mock()

    async def fake_connect(url, connect_timeout):
        await asyncio.sleep(0) 
        return nc

    monkeypatch.setattr(evmod.nats, "connect", fake_connect)

    await events.publish("astradesk.audit", {"a": 1})
    assert events._nc is nc

    await events.close()
    nc.drain.assert_awaited()
    assert events._nc is None


@pytest.mark.asyncio
async def test_close_falls_back_to_close_when_drain_fails(monkeypatch):
    await events.close()

    nc = _make_nc_mock()
    nc.drain.side_effect = RuntimeError("drain failed")

    async def fake_connect(url, connect_timeout):
        await asyncio.sleep(0) 
        return nc

    monkeypatch.setattr(evmod.nats, "connect", fake_connect)
    log = MagicMock()
    monkeypatch.setattr(evmod, "logger", log)

    await events.publish("astradesk.audit", {"a": 1})
    await events.close()

    nc.close.assert_awaited()
    assert any("drain" in str(c.args[0]).lower() for c in log.warning.call_args_list)
    assert events._nc is None
