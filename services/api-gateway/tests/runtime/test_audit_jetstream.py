# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/tests/runtime/test_audit_jetstream.py
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

"""JetStream producer-side durable audit tests (ISSUE 039).

Exercises :class:`runtime.audit.JetStreamAuditWriter` directly (deterministic
fake publisher, no real NATS/JetStream connection needed) and, for the
choke-point integration cases, through ``ToolRegistry.execute`` exactly as
``test_audit.py`` does for the JSONL/in-memory writers — the choke point
itself (``services/api-gateway/src/runtime/registry.py``) is unmodified by
this issue; it already fails a side-effecting tool closed whenever
``AuditWriter.write()`` raises (``INV-AUDIT-5``), so these tests confirm the
new writer raises correctly, not that the choke point works (that is
``test_audit.py``'s job).
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime

import pytest
from astradesk_core.redaction import PLACEHOLDER_SECRET, PLACEHOLDER_TOKEN
from runtime.audit import (
    AuditDecision,
    AuditEvent,
    AuditWriteError,
    JetStreamAuditWriter,
    JetStreamPublishError,
)
from runtime.authz import RbacDenied, RbacReason, SideEffect
from runtime.registry import ToolRegistry

_SUBJECT = 'astradesk.audit.test'
_DLQ_SUBJECT = 'astradesk.audit.test.dlq'


class _FakeJetStreamPublisher:
    """Deterministic fake satisfying :class:`runtime.audit.JetStreamPublisher`.

    ``primary_outcomes`` is a queue of outcomes consumed in order for calls
    to ``subject``: ``None`` means "ack immediately", an ``Exception``
    instance means "raise it", and the sentinel ``_HANG`` means "never
    return" (used to exercise the bounded-timeout path deterministically,
    without a real network stall).
    """

    _HANG = object()

    def __init__(
        self,
        *,
        primary_outcomes: list[object] | None = None,
        dlq_outcome: Exception | None = None,
    ) -> None:
        self.calls: list[tuple[str, bytes, dict[str, str]]] = []
        self._primary_outcomes = list(primary_outcomes or [])
        self._dlq_outcome = dlq_outcome

    async def publish(
        self, subject: str, payload: bytes, *, headers: dict[str, str] | None = None
    ) -> None:
        self.calls.append((subject, payload, dict(headers or {})))
        if subject == _DLQ_SUBJECT:
            if self._dlq_outcome is not None:
                raise self._dlq_outcome
            return None
        # Primary subject.
        if self._primary_outcomes:
            outcome = self._primary_outcomes.pop(0)
            if outcome is self._HANG:
                await asyncio.sleep(999)
                return None
            if isinstance(outcome, Exception):
                raise outcome
            return None
        return None


def _event(**overrides: object) -> AuditEvent:
    base: dict[str, object] = {
        'event_id': 'audit-test-1',
        'timestamp': datetime.now(UTC),
        'tool': 'restart_service',
        'side_effect': SideEffect.EXECUTE,
        'decision': AuditDecision.ALLOWED,
        'roles': ('sre',),
        'args_preview': {},
    }
    base.update(overrides)
    return AuditEvent(**base)  # type: ignore[arg-type]


def _writer(
    fake: _FakeJetStreamPublisher, *, timeout: float = 0.2, retries: int = 2
) -> JetStreamAuditWriter:
    return JetStreamAuditWriter(
        fake,
        subject=_SUBJECT,
        dlq_subject=_DLQ_SUBJECT,
        publish_timeout=timeout,
        publish_retries=retries,
    )


# === 1. Publish ack success ================================================ #


@pytest.mark.asyncio
async def test_write_succeeds_on_first_publish_ack() -> None:
    fake = _FakeJetStreamPublisher(primary_outcomes=[None])
    writer = _writer(fake)

    await writer.write(_event())

    assert len(fake.calls) == 1
    subject, payload, headers = fake.calls[0]
    assert subject == _SUBJECT
    assert headers == {'Nats-Msg-Id': 'audit-test-1'}
    assert json.loads(payload)['event_id'] == 'audit-test-1'


# === 2. Publish retried then succeeds ====================================== #


@pytest.mark.asyncio
async def test_write_retries_then_succeeds() -> None:
    fake = _FakeJetStreamPublisher(primary_outcomes=[TimeoutError('slow'), None])
    writer = _writer(fake, retries=2)

    await writer.write(_event())

    # First attempt failed, second succeeded; no DLQ publish should occur.
    assert len(fake.calls) == 2
    assert all(subject == _SUBJECT for subject, _, _ in fake.calls)


# === 3. Publish timeout/failure exhausts retries =========================== #


@pytest.mark.asyncio
async def test_write_raises_after_exhausting_retries() -> None:
    fake = _FakeJetStreamPublisher(
        primary_outcomes=[OSError('down'), OSError('down'), OSError('down')],
        dlq_outcome=None,  # DLQ succeeds
    )
    writer = _writer(fake, retries=2)  # 1 initial + 2 retries = 3 primary attempts

    with pytest.raises(JetStreamPublishError):
        await writer.write(_event())

    primary_calls = [c for c in fake.calls if c[0] == _SUBJECT]
    assert len(primary_calls) == 3


@pytest.mark.asyncio
async def test_write_bounded_timeout_not_indefinite_hang() -> None:
    """A publish that never returns must still fail within the configured
    timeout, not hang indefinitely (requirement: bounded timeouts)."""
    fake = _FakeJetStreamPublisher(primary_outcomes=[_FakeJetStreamPublisher._HANG])
    writer = _writer(fake, timeout=0.05, retries=0)

    started = time.monotonic()
    with pytest.raises(JetStreamPublishError):
        await writer.write(_event())
    elapsed = time.monotonic() - started

    # Bounded by ~2x the configured timeout (primary + DLQ attempt), nowhere
    # near the 999s the fake would otherwise sleep for.
    assert elapsed < 2.0


# === 4. DLQ write success — still fails closed ============================= #


@pytest.mark.asyncio
async def test_write_raises_even_when_dlq_publish_succeeds() -> None:
    """DLQ must not silently make the side-effect successful: even a
    successful DLQ write leaves write() raising (default fail-closed)."""
    fake = _FakeJetStreamPublisher(
        primary_outcomes=[OSError('down')],
        dlq_outcome=None,  # DLQ succeeds
    )
    writer = _writer(fake, retries=0)

    with pytest.raises(JetStreamPublishError) as excinfo:
        await writer.write(_event())

    assert excinfo.value.dlq_attempted is True
    assert excinfo.value.dlq_succeeded is True
    dlq_calls = [c for c in fake.calls if c[0] == _DLQ_SUBJECT]
    assert len(dlq_calls) == 1
    # DLQ uses a distinct dedup id (`dlq:<event_id>`), not the bare event id:
    # the primary and DLQ subjects share one stream, and JetStream's
    # `Nats-Msg-Id` dedup window is stream-wide, so reusing the primary's id
    # here would make the broker silently discard the DLQ publish as a
    # duplicate of the (failed) primary attempt.
    assert dlq_calls[0][2] == {'Nats-Msg-Id': 'dlq:audit-test-1'}


# === 5. DLQ write failure =================================================== #


@pytest.mark.asyncio
async def test_write_raises_when_dlq_publish_also_fails() -> None:
    fake = _FakeJetStreamPublisher(
        primary_outcomes=[OSError('down')],
        dlq_outcome=OSError('dlq also down'),
    )
    writer = _writer(fake, retries=0)

    with pytest.raises(JetStreamPublishError) as excinfo:
        await writer.write(_event())

    assert excinfo.value.dlq_attempted is True
    assert excinfo.value.dlq_succeeded is False
    # Neither the primary nor the DLQ exception text leaks into the raised error.
    assert 'down' not in str(excinfo.value)


# === 6. Side-effect success only after durable audit ack =================== #


class _Spy:
    def __init__(self) -> None:
        self.called = False

    def as_tool(self):
        async def fn(*, service: str = '', **_: object) -> str:
            self.called = True
            return f'executed:{service}'

        return fn


@pytest.mark.asyncio
async def test_side_effect_succeeds_only_after_jetstream_ack() -> None:
    fake = _FakeJetStreamPublisher(primary_outcomes=[None])
    writer = _writer(fake)
    registry = ToolRegistry(audit_writer=writer)
    spy = _Spy()
    await registry.register(
        'restart_service', spy.as_tool(), side_effect=SideEffect.EXECUTE, allowed_roles={'sre'}
    )

    result = await registry.execute(
        'restart_service', roles=('sre',), approval_id='CHG-2001', service='webapp'
    )

    assert result == 'executed:webapp'
    assert spy.called is True
    assert len(fake.calls) == 1  # the pre-execution ALLOWED event was durably acked


@pytest.mark.asyncio
async def test_side_effect_fails_closed_when_jetstream_publish_never_acks() -> None:
    fake = _FakeJetStreamPublisher(primary_outcomes=[OSError('down')], dlq_outcome=OSError('down'))
    writer = _writer(fake, retries=0)
    registry = ToolRegistry(audit_writer=writer)
    spy = _Spy()
    await registry.register(
        'restart_service', spy.as_tool(), side_effect=SideEffect.EXECUTE, allowed_roles={'sre'}
    )

    with pytest.raises(AuditWriteError):
        await registry.execute(
            'restart_service', roles=('sre',), approval_id='CHG-2002', service='webapp'
        )

    assert spy.called is False  # tool must never run without durable evidence


# === 7. No raw PII/secrets in the emitted (published) payload ============== #


@pytest.mark.asyncio
async def test_no_raw_secret_in_jetstream_payload() -> None:
    fake = _FakeJetStreamPublisher(primary_outcomes=[None])
    writer = _writer(fake)
    registry = ToolRegistry(audit_writer=writer)
    spy = _Spy()
    await registry.register(
        'restart_service', spy.as_tool(), side_effect=SideEffect.EXECUTE, allowed_roles={'sre'}
    )

    await registry.execute(
        'restart_service',
        roles=('sre',),
        approval_id='CHG-2003',
        service='webapp',
        api_token='ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345',
        note='password=hunter2secret',
    )

    assert len(fake.calls) == 1
    _, payload, _ = fake.calls[0]
    raw = payload.decode('utf-8')
    assert 'ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345' not in raw
    assert 'hunter2secret' not in raw
    assert PLACEHOLDER_TOKEN in raw or PLACEHOLDER_SECRET in raw


# === 8. Deny audit still recorded (published) via JetStream ================ #


@pytest.mark.asyncio
async def test_rbac_denied_side_effect_still_published_via_jetstream() -> None:
    fake = _FakeJetStreamPublisher(primary_outcomes=[None])
    writer = _writer(fake)
    registry = ToolRegistry(audit_writer=writer)
    spy = _Spy()
    await registry.register(
        'restart_service', spy.as_tool(), side_effect=SideEffect.EXECUTE, allowed_roles={'sre'}
    )

    with pytest.raises(RbacDenied) as excinfo:
        await registry.execute('restart_service', roles=('viewer',), service='webapp')

    assert spy.called is False
    assert len(fake.calls) == 1  # the DENIED event was durably published
    published = json.loads(fake.calls[0][1])
    assert published['decision'] == AuditDecision.DENIED.value
    assert published['reason'] == excinfo.value.reason.value == RbacReason.ROLE_DENIED.value
