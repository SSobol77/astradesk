# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/auditor/tests/test_auditor.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Verifies AstraDesk behavior for the associated component.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Consumer-side durable audit tests for the Auditor JetStream pull consumer
(ISSUE 039).

``main`` (`services/auditor/main.py`) is editable-installed as a top-level
module (see `astradesk_auditor.egg-info/top_level.txt`), so it is imported
directly, matching the sibling `services/admin_api`/`services/api-gateway`
test conventions of importing the installed package rather than manipulating
``sys.path``.

All sink I/O (`Auditor._persist_to_es` / `_persist_to_s3`) is replaced with
deterministic fakes at the class level (``Auditor.__slots__`` forbids
instance-level method overrides), and the JetStream publish client
(``Auditor._js``) is a fake satisfying only the ``publish`` surface actually
used by `_publish_to_dlq`/`_ensure_stream` — no real NATS/JetStream
connection is needed for any test in this file.
"""

from __future__ import annotations

import json

import main
import nats.js.errors
import pytest
from main import Auditor

# === Fakes ================================================================== #


class _FakeMsg:
    """Minimal fake satisfying the ``nats.aio.msg.Msg`` surface used here."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.acked = False

    async def ack(self) -> None:
        self.acked = True


class _FakeJsPublisher:
    """Fake JetStream client: records ``publish`` calls, optionally fails."""

    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[tuple[str, bytes, dict[str, str]]] = []
        self.fail = fail

    async def publish(self, subject: str, payload: bytes, *, headers: dict | None = None) -> None:
        self.calls.append((subject, payload, dict(headers or {})))
        if self.fail:
            raise OSError('simulated DLQ broker outage')


class _FakeJsStreamMgmt:
    """Fake JetStream client exposing only ``stream_info``/``add_stream``."""

    def __init__(self, *, exists: bool) -> None:
        self.exists = exists
        self.added: dict | None = None

    async def stream_info(self, name: str) -> None:
        if not self.exists:
            raise nats.js.errors.NotFoundError
        return None

    async def add_stream(self, *, name: str, subjects: list[str]) -> None:
        self.added = {'name': name, 'subjects': subjects}


def _make_auditor(*, dlq_fail: bool = False) -> tuple[Auditor, _FakeJsPublisher]:
    auditor = Auditor()
    fake_js = _FakeJsPublisher(fail=dlq_fail)
    auditor._js = fake_js  # type: ignore[assignment]
    return auditor, fake_js


def _event(event_id: str = 'audit-1', **overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        'event_id': event_id,
        'tool': 'restart_service',
        'decision': 'ALLOWED',
    }
    base.update(overrides)
    return base


def _msg_for(event: dict[str, object]) -> _FakeMsg:
    return _FakeMsg(json.dumps(event).encode('utf-8'))


# === 1. Success: ack only after both sinks durably accept the batch ======== #


@pytest.mark.asyncio
async def test_process_batch_acks_after_both_sinks_succeed(monkeypatch: pytest.MonkeyPatch) -> None:
    es_calls: list[list[dict]] = []
    s3_calls: list[list[dict]] = []

    async def fake_es(self: Auditor, batch: list[dict]) -> None:
        es_calls.append(list(batch))

    async def fake_s3(self: Auditor, batch: list[dict]) -> None:
        s3_calls.append(list(batch))

    monkeypatch.setattr(Auditor, '_persist_to_es', fake_es)
    monkeypatch.setattr(Auditor, '_persist_to_s3', fake_s3)

    auditor, fake_js = _make_auditor()
    event = _event()
    msg = _msg_for(event)

    await auditor._process_batch([msg])

    assert msg.acked is True
    assert es_calls == [[event]]
    assert s3_calls == [[event]]
    assert fake_js.calls == []  # no DLQ involvement on the happy path


# === 2. Retry then success: transient failure recovers without DLQ ========= #


@pytest.mark.asyncio
async def test_process_batch_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, 'SINK_RETRY_BACKOFF_SEC', 0.0)
    attempts = {'es': 0}

    async def flaky_es(self: Auditor, batch: list[dict]) -> None:
        attempts['es'] += 1
        if attempts['es'] < 2:
            raise OSError('simulated transient ES outage')

    async def ok_s3(self: Auditor, batch: list[dict]) -> None:
        return None

    monkeypatch.setattr(Auditor, '_persist_to_es', flaky_es)
    monkeypatch.setattr(Auditor, '_persist_to_s3', ok_s3)

    auditor, fake_js = _make_auditor()
    msg = _msg_for(_event())

    await auditor._process_batch([msg])

    assert msg.acked is True
    assert attempts['es'] == 2
    assert fake_js.calls == []  # recovered before DLQ was ever needed


# === 3. DLQ routing: bounded retries exhausted, DLQ accepts the batch ====== #


@pytest.mark.asyncio
async def test_process_batch_routes_to_dlq_after_retries_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main, 'SINK_RETRY_BACKOFF_SEC', 0.0)
    monkeypatch.setattr(main, 'SINK_RETRIES', 1)

    async def always_fail_es(self: Auditor, batch: list[dict]) -> None:
        raise OSError('simulated persistent ES outage')

    async def ok_s3(self: Auditor, batch: list[dict]) -> None:
        return None

    monkeypatch.setattr(Auditor, '_persist_to_es', always_fail_es)
    monkeypatch.setattr(Auditor, '_persist_to_s3', ok_s3)

    auditor, fake_js = _make_auditor()  # DLQ succeeds by default
    event = _event(event_id='dlq-1')
    msg = _msg_for(event)

    await auditor._process_batch([msg])

    # Acked only because the DLQ broker confirmed durable storage — the
    # event is not lost, merely rerouted (INV-AUD-3).
    assert msg.acked is True
    assert len(fake_js.calls) == 1
    subject, payload, headers = fake_js.calls[0]
    assert subject == main.AUDIT_DLQ_SUBJECT
    # A distinct dedup id (`dlq:<event_id>`) is required: the primary and
    # DLQ subjects share one stream, and JetStream's `Nats-Msg-Id` dedup
    # window is stream-wide, so reusing the bare event id would make the
    # broker silently discard this publish as a duplicate.
    assert headers == {'Nats-Msg-Id': 'dlq:dlq-1'}
    assert json.loads(payload)['event_id'] == 'dlq-1'


# === 4. DLQ failure: never silently drop, leave unacked for redelivery ===== #


@pytest.mark.asyncio
async def test_process_batch_leaves_unacked_when_dlq_also_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main, 'SINK_RETRY_BACKOFF_SEC', 0.0)
    monkeypatch.setattr(main, 'SINK_RETRIES', 0)

    async def always_fail_es(self: Auditor, batch: list[dict]) -> None:
        raise OSError('simulated persistent ES outage')

    async def ok_s3(self: Auditor, batch: list[dict]) -> None:
        return None

    monkeypatch.setattr(Auditor, '_persist_to_es', always_fail_es)
    monkeypatch.setattr(Auditor, '_persist_to_s3', ok_s3)

    auditor, fake_js = _make_auditor(dlq_fail=True)
    msg = _msg_for(_event())

    await auditor._process_batch([msg])

    # Neither sink nor DLQ confirmed durable storage: must not ack, so
    # JetStream redelivers the message later instead of losing it silently.
    assert msg.acked is False
    assert len(fake_js.calls) == 1  # the DLQ attempt itself is still evidenced


# === 5. Idempotent redelivery: same event content -> same sink keys ======= #


def test_batch_s3_key_is_deterministic_regardless_of_order() -> None:
    batch_a = [{'event_id': 'e1'}, {'event_id': 'e2'}]
    batch_b = [{'event_id': 'e2'}, {'event_id': 'e1'}]

    assert main._batch_s3_key(batch_a) == main._batch_s3_key(batch_b)


@pytest.mark.asyncio
async def test_redelivered_event_persists_to_same_sink_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s3_keys: list[str] = []
    es_ids: list[list[str]] = []

    async def capture_es(self: Auditor, batch: list[dict]) -> None:
        es_ids.append(sorted(str(d['event_id']) for d in batch))

    async def capture_s3(self: Auditor, batch: list[dict]) -> None:
        s3_keys.append(main._batch_s3_key(batch))

    monkeypatch.setattr(Auditor, '_persist_to_es', capture_es)
    monkeypatch.setattr(Auditor, '_persist_to_s3', capture_s3)

    auditor, _ = _make_auditor()
    event = _event(event_id='redeliver-1')

    # First delivery, then a simulated redelivery of the identical event
    # (e.g. the process crashed after a successful sink write but before
    # the JetStream ack was confirmed).
    await auditor._process_batch([_msg_for(event)])
    await auditor._process_batch([_msg_for(event)])

    assert s3_keys[0] == s3_keys[1]
    assert es_ids[0] == es_ids[1]


# === 6. Poison messages: routed to DLQ immediately, never retried ========== #


@pytest.mark.asyncio
async def test_poison_message_is_routed_to_dlq_and_acked() -> None:
    auditor, fake_js = _make_auditor()
    msg = _FakeMsg(b'not-json{{{')

    await auditor._process_batch([msg])

    assert msg.acked is True
    assert len(fake_js.calls) == 1
    subject, payload, _headers = fake_js.calls[0]
    assert subject == main.AUDIT_DLQ_SUBJECT
    assert payload == b'not-json{{{'


# === 7. Stream provisioning is idempotent ================================== #


@pytest.mark.asyncio
async def test_ensure_stream_creates_when_missing() -> None:
    auditor = Auditor()
    fake = _FakeJsStreamMgmt(exists=False)
    auditor._js = fake  # type: ignore[assignment]

    await auditor._ensure_stream()

    assert fake.added == {
        'name': main.AUDIT_JETSTREAM_STREAM,
        'subjects': [main.AUDIT_SUBJECT, main.AUDIT_DLQ_SUBJECT],
    }


@pytest.mark.asyncio
async def test_ensure_stream_does_not_recreate_existing_stream() -> None:
    auditor = Auditor()
    fake = _FakeJsStreamMgmt(exists=True)
    auditor._js = fake  # type: ignore[assignment]

    await auditor._ensure_stream()

    assert fake.added is None
