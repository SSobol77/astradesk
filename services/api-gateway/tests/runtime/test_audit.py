# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/tests/runtime/test_audit.py
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

"""Durable audit trail tests for side-effecting tool execution (ISSUE 019).

Exercises the audit choke point wired into ``ToolRegistry.execute`` (ISSUE
016's shared RBAC choke point). Both the LLM-planned and keyword-fallback
paths call this exact method (see ``test_rbac_invariant.py``), so auditing it
here makes every side-effect attempt auditable regardless of caller
(``INV-DUAL-PATH``).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from astradesk_core.redaction import (
    PLACEHOLDER_EMAIL,
    PLACEHOLDER_PRIVATE_KEY,
    PLACEHOLDER_SECRET,
    PLACEHOLDER_TOKEN,
)
from runtime.audit import (
    AuditDecision,
    AuditEvent,
    AuditWriteError,
    FileAuditWriter,
    InMemoryAuditWriter,
    build_args_preview,
    principal_from_claims,
    tenant_from_claims,
)
from runtime.authz import RbacDenied, RbacReason, SideEffect
from runtime.planner import KeywordPlanner
from runtime.registry import ToolRegistry

# A representative leak corpus: (secret_fragment, raw_value, expected_placeholder).
_LEAK_CORPUS = [
    ('victim@example.com', 'contact victim@example.com about this', PLACEHOLDER_EMAIL),
    (
        'ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345',
        'token ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345',
        PLACEHOLDER_TOKEN,
    ),
    ('hunter2secret', 'password=hunter2secret', PLACEHOLDER_SECRET),
    (
        'MIIEowIBAAKCAQEA1234567890abcdef',
        '-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA1234567890abcdef\n-----END RSA PRIVATE KEY-----',
        PLACEHOLDER_PRIVATE_KEY,
    ),
]


class _BrokenWriter:
    """An ``AuditWriter`` that always fails; used for fail-closed tests."""

    def __init__(self) -> None:
        self.calls = 0

    async def write(self, event: AuditEvent) -> None:
        self.calls += 1
        raise OSError('simulated audit sink outage')


class _Spy:
    """Records whether the underlying tool function ran, mirroring the
    dual-path helper in ``test_rbac_invariant.py``."""

    def __init__(self, *, raises: Exception | None = None) -> None:
        self.called = False
        self._raises = raises

    def as_tool(self):
        async def fn(*, service: str = '', **_: object) -> str:
            self.called = True
            if self._raises is not None:
                raise self._raises
            return f'executed:{service}'

        return fn


async def _register(
    registry: ToolRegistry,
    spy: _Spy,
    *,
    name: str = 'restart_service',
    side_effect: SideEffect = SideEffect.EXECUTE,
    allowed_roles: set[str] | None = None,
) -> None:
    await registry.register(
        name,
        spy.as_tool(),
        side_effect=side_effect,
        allowed_roles=allowed_roles if allowed_roles is not None else {'sre'},
    )


# === 1 & 2. Successful write/execute tool emits exactly one audit event ==== #


@pytest.mark.parametrize('side_effect', [SideEffect.WRITE, SideEffect.EXECUTE])
@pytest.mark.asyncio
async def test_successful_side_effect_tool_emits_one_audit_event(side_effect: SideEffect) -> None:
    writer = InMemoryAuditWriter()
    registry = ToolRegistry(audit_writer=writer)
    spy = _Spy()
    await _register(registry, spy, side_effect=side_effect)

    result = await registry.execute(
        'restart_service', roles=('sre',), approval_id='CHG-1001', service='webapp'
    )

    assert result == 'executed:webapp'
    assert spy.called is True
    assert len(writer.events) == 1
    event = writer.events[0]
    assert event.decision is AuditDecision.ALLOWED
    assert event.tool == 'restart_service'
    assert event.side_effect is side_effect
    assert event.approval_id == 'CHG-1001'


# === 3 & 4. RBAC-denied / missing-approval side-effect attempts audited ==== #


@pytest.mark.asyncio
async def test_rbac_denied_side_effect_emits_denied_audit_event() -> None:
    writer = InMemoryAuditWriter()
    registry = ToolRegistry(audit_writer=writer)
    spy = _Spy()
    await _register(registry, spy)

    with pytest.raises(RbacDenied) as excinfo:
        await registry.execute('restart_service', roles=('viewer',), service='webapp')

    assert spy.called is False
    assert len(writer.events) == 1
    event = writer.events[0]
    assert event.decision is AuditDecision.DENIED
    assert event.reason == excinfo.value.reason.value == RbacReason.ROLE_DENIED.value


@pytest.mark.asyncio
async def test_missing_approval_emits_denied_audit_event() -> None:
    writer = InMemoryAuditWriter()
    registry = ToolRegistry(audit_writer=writer)
    spy = _Spy()
    await _register(registry, spy)

    with pytest.raises(RbacDenied):
        # Matching role, but no approval/change record (INV-RBAC-4).
        await registry.execute('restart_service', roles=('sre',), service='webapp')

    assert spy.called is False
    assert len(writer.events) == 1
    assert writer.events[0].decision is AuditDecision.DENIED
    assert writer.events[0].reason == RbacReason.APPROVAL_REQUIRED.value


# === 5. Tool execution exception emits an error audit event =============== #


@pytest.mark.asyncio
async def test_tool_exception_emits_error_audit_event() -> None:
    writer = InMemoryAuditWriter()
    registry = ToolRegistry(audit_writer=writer)
    spy = _Spy(raises=RuntimeError('boom'))
    await _register(registry, spy)

    with pytest.raises(RuntimeError, match='boom'):
        await registry.execute(
            'restart_service', roles=('sre',), approval_id='CHG-1002', service='webapp'
        )

    assert spy.called is True
    error_events = [e for e in writer.events if e.decision is AuditDecision.ERROR]
    assert len(error_events) == 1
    assert error_events[0].error_type == 'RuntimeError'
    # The exception message ('boom') must never appear in the audit record.
    assert 'boom' not in str(error_events[0].args_preview)


# === 6. Audit writer failure blocks write/execute tools (fail-closed) ====== #


@pytest.mark.parametrize('side_effect', [SideEffect.WRITE, SideEffect.EXECUTE])
@pytest.mark.asyncio
async def test_audit_writer_failure_blocks_side_effect_tool(side_effect: SideEffect) -> None:
    writer = _BrokenWriter()
    registry = ToolRegistry(audit_writer=writer)
    spy = _Spy()
    await _register(registry, spy, side_effect=side_effect)

    with pytest.raises(AuditWriteError):
        await registry.execute(
            'restart_service', roles=('sre',), approval_id='CHG-1003', service='webapp'
        )

    assert spy.called is False  # tool must never run without durable evidence
    assert writer.calls == 1


@pytest.mark.asyncio
async def test_audit_writer_failure_error_does_not_leak_writer_exception_text() -> None:
    writer = _BrokenWriter()
    registry = ToolRegistry(audit_writer=writer)
    spy = _Spy()
    await _register(registry, spy)

    with pytest.raises(AuditWriteError) as excinfo:
        await registry.execute(
            'restart_service', roles=('sre',), approval_id='CHG-1004', service='webapp'
        )

    assert 'simulated audit sink outage' not in str(excinfo.value)
    assert excinfo.value.code == 'AUDIT_SINK_UNAVAILABLE'


# === 7. Audit writer failure never blocks a read tool ====================== #


@pytest.mark.asyncio
async def test_audit_writer_failure_does_not_block_read_tool() -> None:
    writer = _BrokenWriter()
    registry = ToolRegistry(audit_writer=writer)
    spy = _Spy()
    await registry.register('get_metrics', spy.as_tool(), side_effect=SideEffect.READ)

    result = await registry.execute('get_metrics', roles=(), service='webapp')

    assert result == 'executed:webapp'
    assert spy.called is True
    assert writer.calls == 0  # read tools never touch the audit writer


# === 8 & 11. Argument preview / audit payload redaction ==================== #


@pytest.mark.parametrize('fragment,raw,placeholder', _LEAK_CORPUS)
@pytest.mark.asyncio
async def test_args_preview_redacts_leak_corpus(fragment: str, raw: str, placeholder: str) -> None:
    writer = InMemoryAuditWriter()
    registry = ToolRegistry(audit_writer=writer)
    spy = _Spy()
    await _register(registry, spy, name='create_ticket', side_effect=SideEffect.WRITE)

    await registry.execute(
        'create_ticket',
        roles=('sre',),
        approval_id='CHG-2001',
        claims={'sub': 'user-1', 'access_token': 'super-secret-token-value'},
        service=raw,
    )

    event = writer.events[0]
    rendered = str(event.args_preview)
    assert fragment not in rendered, 'raw leak-corpus fragment survived into the audit preview'
    assert placeholder in rendered
    # The raw claims container itself must never be echoed into the preview.
    assert 'super-secret-token-value' not in rendered
    assert 'access_token' not in event.args_preview


@pytest.mark.asyncio
async def test_no_audit_event_contains_raw_leak_corpus_values() -> None:
    """Regression: across every emitted event (denied/allowed/error), no raw
    leak-corpus fragment survives, whatever the outcome (INV-AUDIT-3)."""
    writer = InMemoryAuditWriter()
    registry = ToolRegistry(audit_writer=writer)

    secret_claims = {
        'sub': 'user-1',
        'password': 'hunter2secret',
        'access_token': 'eyJhbGci.abc.def',
    }

    denied_spy = _Spy()
    await _register(registry, denied_spy, name='denied_tool')
    with pytest.raises(RbacDenied):
        await registry.execute(
            'denied_tool', roles=('viewer',), claims=secret_claims, service='alice@example.com'
        )

    allowed_spy = _Spy()
    await _register(registry, allowed_spy, name='allowed_tool')
    await registry.execute(
        'allowed_tool',
        roles=('sre',),
        approval_id='CHG-3001',
        claims=secret_claims,
        service='alice@example.com',
    )

    error_spy = _Spy(raises=ValueError('leak alice@example.com in error'))
    await _register(registry, error_spy, name='error_tool')
    with pytest.raises(ValueError, match='leak'):
        await registry.execute(
            'error_tool',
            roles=('sre',),
            approval_id='CHG-3002',
            claims=secret_claims,
            service='alice@example.com',
        )

    # denied_tool -> 1 DENIED event. allowed_tool (succeeds) -> 1 pre-execution
    # ALLOWED event. error_tool (RBAC allows, then raises) -> the pre-execution
    # ALLOWED event plus a post-execution ERROR event. 4 events total.
    assert len(writer.events) == 4
    blob = '\n'.join(str(e.to_dict()) for e in writer.events)
    assert 'hunter2secret' not in blob
    assert 'eyJhbGci.abc.def' not in blob
    assert 'alice@example.com' not in blob


def test_build_args_preview_excludes_meta_keys() -> None:
    preview = build_args_preview(
        {
            'claims': {'sub': 'user-1', 'password': 'hunter2'},
            'approval_id': 'CHG-9001',
            'change_record': 'CHG-9002',
            'service': 'webapp',
        }
    )
    assert 'claims' not in preview
    assert 'approval_id' not in preview
    assert 'change_record' not in preview
    assert preview['service'] == 'webapp'


def test_build_args_preview_is_bounded() -> None:
    huge = {f'k{i}': 'x' * 5000 for i in range(50)}
    preview = build_args_preview(huge)
    assert preview.get('_truncated') is True
    assert len(preview) <= 21  # 20 keys + the truncation marker
    for value in preview.values():
        if isinstance(value, str):
            assert len(value) <= 201  # bounded chars + ellipsis


# === 9. Correlation fields present when provided (or safely derived) ======= #


@pytest.mark.asyncio
async def test_audit_event_includes_correlation_fields_when_provided() -> None:
    writer = InMemoryAuditWriter()
    registry = ToolRegistry(audit_writer=writer)
    spy = _Spy()
    await _register(registry, spy)

    await registry.execute(
        'restart_service',
        roles=('sre',),
        approval_id='CHG-4001',
        trace_id='trace-abc',
        request_id='req-xyz',
        tenant_id='acme',
        principal_id='user-explicit',
        service='webapp',
    )

    event = writer.events[0]
    assert event.trace_id == 'trace-abc'
    assert event.request_id == 'req-xyz'
    assert event.tenant_id == 'acme'
    assert event.principal_id == 'user-explicit'
    assert event.roles == ('sre',)
    assert event.tool == 'restart_service'
    assert event.side_effect is SideEffect.EXECUTE
    assert event.decision is AuditDecision.ALLOWED
    assert event.event_id
    assert isinstance(event.timestamp, datetime)
    assert event.timestamp.tzinfo is not None  # timezone-aware UTC (INV-AUDIT-7)


@pytest.mark.asyncio
async def test_audit_event_derives_principal_and_tenant_from_claims_when_not_explicit() -> None:
    writer = InMemoryAuditWriter()
    registry = ToolRegistry(audit_writer=writer)
    spy = _Spy()
    await _register(registry, spy)

    await registry.execute(
        'restart_service',
        roles=('sre',),
        approval_id='CHG-4002',
        claims={'sub': 'user-42', 'tenant': 'acme-corp'},
        service='webapp',
    )

    event = writer.events[0]
    assert event.principal_id == 'user-42'
    assert event.tenant_id == 'acme-corp'


@pytest.mark.asyncio
async def test_denied_and_allowed_events_report_identical_correlation_fields() -> None:
    """Regression: correlation fields must not depend on whether the tool's
    signature happens to declare ``claims`` (kwargs stripping must not change
    what the audit layer observes)."""
    writer = InMemoryAuditWriter()
    registry = ToolRegistry(audit_writer=writer)

    denied_spy = _Spy()
    await _register(registry, denied_spy, name='deny_me')
    with pytest.raises(RbacDenied):
        await registry.execute(
            'deny_me', roles=('viewer',), claims={'sub': 'user-7', 'tenant': 'acme'}, service='x'
        )

    allowed_spy = _Spy()
    await _register(registry, allowed_spy, name='allow_me')
    await registry.execute(
        'allow_me',
        roles=('sre',),
        approval_id='CHG-5001',
        claims={'sub': 'user-7', 'tenant': 'acme'},
        service='x',
    )

    denied_event, allowed_event = writer.events
    assert denied_event.principal_id == allowed_event.principal_id == 'user-7'
    assert denied_event.tenant_id == allowed_event.tenant_id == 'acme'


def test_principal_and_tenant_from_claims_helpers() -> None:
    assert principal_from_claims(None) is None
    assert principal_from_claims({}) is None
    assert principal_from_claims({'sub': 'user-1'}) == 'user-1'
    assert tenant_from_claims({'tenant': 'acme'}) == 'acme'
    assert tenant_from_claims({'tenant_id': 'acme-2'}) == 'acme-2'
    assert tenant_from_claims({}) is None


# === 10. Both LLM-planned and keyword-fallback paths are auditable ========= #


async def _invoke_as_agent_path(
    registry: ToolRegistry,
    name: str,
    roles: tuple[str, ...],
    *,
    approval_id: str | None = None,
    **args: Any,
) -> object:
    """Mirror the exact call both runtime paths make to the choke point (see
    ``test_rbac_invariant.py::_invoke_as_agent_path``)."""
    return await registry.execute(name, roles=roles, approval_id=approval_id, claims={}, **args)


@pytest.mark.parametrize('path', ['llm_planned', 'keyword_fallback'])
@pytest.mark.asyncio
async def test_dual_path_authorized_side_effect_is_audited(path: str) -> None:
    writer = InMemoryAuditWriter()
    registry = ToolRegistry(audit_writer=writer)
    spy = _Spy()
    await _register(registry, spy)

    if path == 'keyword_fallback':
        steps = KeywordPlanner().make_plan('please restart webapp now')
        name, args = steps[0].name, steps[0].arguments
    else:
        name, args = 'restart_service', {'service': 'webapp'}

    result = await _invoke_as_agent_path(registry, name, ('sre',), approval_id='CHG-6001', **args)

    assert result == 'executed:webapp'
    assert len(writer.events) == 1
    assert writer.events[0].decision is AuditDecision.ALLOWED


@pytest.mark.parametrize('path', ['llm_planned', 'keyword_fallback'])
@pytest.mark.asyncio
async def test_dual_path_unauthorized_side_effect_is_audited(path: str) -> None:
    writer = InMemoryAuditWriter()
    registry = ToolRegistry(audit_writer=writer)
    spy = _Spy()
    await _register(registry, spy)

    if path == 'keyword_fallback':
        steps = KeywordPlanner().make_plan('please restart webapp now')
        name, args = steps[0].name, steps[0].arguments
    else:
        name, args = 'restart_service', {'service': 'webapp'}

    with pytest.raises(RbacDenied):
        await _invoke_as_agent_path(registry, name, ('viewer',), **args)

    assert spy.called is False
    assert len(writer.events) == 1
    assert writer.events[0].decision is AuditDecision.DENIED


# === FileAuditWriter: real append-only local durability ==================== #


@pytest.mark.asyncio
async def test_file_audit_writer_appends_json_lines(tmp_path: Any) -> None:
    path = tmp_path / 'audit' / 'events.jsonl'
    writer = FileAuditWriter(path)
    event = AuditEvent(
        event_id='audit-1',
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        tool='restart_service',
        side_effect=SideEffect.EXECUTE,
        decision=AuditDecision.ALLOWED,
        roles=('sre',),
        approval_id='CHG-1',
    )

    await writer.write(event)
    await writer.write(event)

    lines = path.read_text(encoding='utf-8').strip().splitlines()
    assert len(lines) == 2
    assert '"tool":"restart_service"' in lines[0]
    assert '"decision":"allowed"' in lines[0]


@pytest.mark.asyncio
async def test_file_audit_writer_survives_reinstantiation(tmp_path: Any) -> None:
    """A fresh writer instance appends rather than truncating (durability
    across process restarts on the same host)."""
    path = tmp_path / 'events.jsonl'
    event = AuditEvent(
        event_id='audit-1',
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        tool='t',
        side_effect=SideEffect.WRITE,
        decision=AuditDecision.ALLOWED,
    )

    await FileAuditWriter(path).write(event)
    await FileAuditWriter(path).write(event)

    lines = path.read_text(encoding='utf-8').strip().splitlines()
    assert len(lines) == 2


# === Default writer wiring: existing/legacy callers keep working =========== #


@pytest.mark.asyncio
async def test_default_registry_uses_in_memory_audit_writer_and_never_blocks() -> None:
    registry = ToolRegistry()  # no audit_writer supplied — legacy construction
    spy = _Spy()
    await _register(registry, spy)

    result = await registry.execute(
        'restart_service', roles=('sre',), approval_id='CHG-7001', service='webapp'
    )

    assert result == 'executed:webapp'
    assert isinstance(registry._audit_writer, InMemoryAuditWriter)  # type: ignore[attr-defined]
    assert len(registry._audit_writer.events) == 1  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_injected_clock_and_event_id_are_deterministic() -> None:
    writer = InMemoryAuditWriter()
    fixed_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    registry = ToolRegistry(
        audit_writer=writer,
        audit_event_id=lambda: 'audit-fixed-id',
        audit_clock=lambda: fixed_time,
    )
    spy = _Spy()
    await _register(registry, spy)

    await registry.execute(
        'restart_service', roles=('sre',), approval_id='CHG-8001', service='webapp'
    )

    event = writer.events[0]
    assert event.event_id == 'audit-fixed-id'
    assert event.timestamp == fixed_time
