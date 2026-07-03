# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/tests/runtime/test_policy_choke_point.py
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

"""Policy choke-point tests for ToolRegistry.execute (ISSUE 028).

Exercises the contextual policy gate wired into the single RBAC (ISSUE 016)
and durable-audit (ISSUE 019) choke point. Both the LLM-planned and
keyword-fallback paths call this exact method (see ``test_rbac_invariant.py``
and ``test_audit.py``), so testing it here makes every side-effect attempt
policy-checked regardless of caller (``INV-DUAL-PATH``). RBAC is not
duplicated or weakened by these tests — they assert composition, not
replacement.
"""

from __future__ import annotations

from typing import Any

import pytest
from runtime.audit import AuditDecision, InMemoryAuditWriter
from runtime.authz import RbacDenied, RbacReason, SideEffect
from runtime.planner import KeywordPlanner
from runtime.policy_enforcer import PolicyDecision, PolicyDenied, PolicyReason, PolicyRequest
from runtime.registry import ToolRegistry

pytestmark = pytest.mark.asyncio


class _Spy:
    """Records whether the underlying tool function ran."""

    def __init__(self) -> None:
        self.called = False

    def as_tool(self):
        async def fn(*, service: str = '', **_: object) -> str:
            self.called = True
            return f'executed:{service}'

        return fn


class _RecordingEnforcer:
    """Fake ``PolicyEnforcer`` that records every request it was asked to decide."""

    def __init__(
        self, *, decision: PolicyDecision | None = None, raises: Exception | None = None
    ) -> None:
        self.calls: list[PolicyRequest] = []
        self._decision = decision or PolicyDecision(allow=True)
        self._raises = raises

    async def evaluate(self, request: PolicyRequest) -> PolicyDecision:
        self.calls.append(request)
        if self._raises is not None:
            raise self._raises
        return self._decision


async def _register(
    registry: ToolRegistry,
    spy: _Spy,
    *,
    name: str = 'restart_service',
    side_effect: SideEffect = SideEffect.EXECUTE,
    allowed_roles: set[str] | None = None,
    policy_governed: bool = False,
) -> None:
    await registry.register(
        name,
        spy.as_tool(),
        side_effect=side_effect,
        allowed_roles=allowed_roles if allowed_roles is not None else {'sre'},
        policy_governed=policy_governed,
    )


# === 1 & 2. Successful write/execute call is policy-checked then invoked === #


@pytest.mark.parametrize('side_effect', [SideEffect.WRITE, SideEffect.EXECUTE])
async def test_successful_side_effect_call_is_policy_checked_and_invoked(
    side_effect: SideEffect,
) -> None:
    enforcer = _RecordingEnforcer(decision=PolicyDecision(allow=True))
    registry = ToolRegistry(policy_enforcer=enforcer)
    spy = _Spy()
    await _register(registry, spy, side_effect=side_effect)

    result = await registry.execute(
        'restart_service', roles=('sre',), approval_id='CHG-1001', service='webapp'
    )

    assert result == 'executed:webapp'
    assert spy.called is True
    assert len(enforcer.calls) == 1
    assert enforcer.calls[0].tool == 'restart_service'
    assert enforcer.calls[0].side_effect is side_effect


# === 3 & 4. Policy denial blocks write/execute invocation ================== #


@pytest.mark.parametrize('side_effect', [SideEffect.WRITE, SideEffect.EXECUTE])
async def test_policy_denial_blocks_side_effect_invocation(side_effect: SideEffect) -> None:
    enforcer = _RecordingEnforcer(decision=PolicyDecision(allow=False, reason='blocked_by_rule'))
    registry = ToolRegistry(policy_enforcer=enforcer)
    spy = _Spy()
    await _register(registry, spy, side_effect=side_effect)

    with pytest.raises(PolicyDenied) as excinfo:
        await registry.execute(
            'restart_service', roles=('sre',), approval_id='CHG-1001', service='webapp'
        )

    assert spy.called is False
    assert excinfo.value.reason == 'blocked_by_rule'
    assert excinfo.value.tool == 'restart_service'


# === 5. Policy dependency failure blocks write/execute ====================== #


@pytest.mark.parametrize('side_effect', [SideEffect.WRITE, SideEffect.EXECUTE])
async def test_policy_dependency_failure_blocks_side_effect(side_effect: SideEffect) -> None:
    enforcer = _RecordingEnforcer(raises=ConnectionError('opa unreachable'))
    registry = ToolRegistry(policy_enforcer=enforcer)
    spy = _Spy()
    await _register(registry, spy, side_effect=side_effect)

    with pytest.raises(PolicyDenied) as excinfo:
        await registry.execute(
            'restart_service', roles=('sre',), approval_id='CHG-1001', service='webapp'
        )

    assert spy.called is False
    assert excinfo.value.reason == PolicyReason.UNAVAILABLE.value
    # The underlying dependency error text must never leak into the exception.
    assert 'opa unreachable' not in str(excinfo.value)


# === 6. Policy dependency failure does not block an ordinary read tool ===== #


async def test_policy_dependency_failure_does_not_block_unconfigured_read_tool() -> None:
    enforcer = _RecordingEnforcer(raises=ConnectionError('opa unreachable'))
    registry = ToolRegistry(policy_enforcer=enforcer)
    spy = _Spy()
    await registry.register('get_metrics', spy.as_tool(), side_effect=SideEffect.READ)

    result = await registry.execute('get_metrics', roles=(), service='webapp')

    assert result == 'executed:webapp'
    assert spy.called is True
    assert enforcer.calls == []  # policy is never even consulted for a plain read


async def test_policy_dependency_failure_blocks_explicitly_governed_read_tool() -> None:
    enforcer = _RecordingEnforcer(raises=ConnectionError('opa unreachable'))
    registry = ToolRegistry(policy_enforcer=enforcer)
    spy = _Spy()
    await registry.register(
        'get_metrics', spy.as_tool(), side_effect=SideEffect.READ, policy_governed=True
    )

    with pytest.raises(PolicyDenied):
        await registry.execute('get_metrics', roles=(), service='webapp')

    assert spy.called is False


# === 9. LLM-planned and keyword-fallback paths hit the same enforcement === #


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
async def test_dual_path_policy_denial_is_identical(path: str) -> None:
    enforcer = _RecordingEnforcer(decision=PolicyDecision(allow=False, reason='ctx_blocked'))
    registry = ToolRegistry(policy_enforcer=enforcer)
    spy = _Spy()
    await _register(registry, spy)

    if path == 'keyword_fallback':
        steps = KeywordPlanner().make_plan('please restart webapp now')
        name, args = steps[0].name, steps[0].arguments
    else:
        name, args = 'restart_service', {'service': 'webapp'}

    with pytest.raises(PolicyDenied) as excinfo:
        await _invoke_as_agent_path(registry, name, ('sre',), approval_id='CHG-2002', **args)

    assert excinfo.value.reason == 'ctx_blocked'
    assert spy.called is False
    assert len(enforcer.calls) == 1


@pytest.mark.parametrize('path', ['llm_planned', 'keyword_fallback'])
async def test_dual_path_policy_allow_executes(path: str) -> None:
    enforcer = _RecordingEnforcer(decision=PolicyDecision(allow=True))
    registry = ToolRegistry(policy_enforcer=enforcer)
    spy = _Spy()
    await _register(registry, spy)

    if path == 'keyword_fallback':
        steps = KeywordPlanner().make_plan('please restart webapp now')
        name, args = steps[0].name, steps[0].arguments
    else:
        name, args = 'restart_service', {'service': 'webapp'}

    result = await _invoke_as_agent_path(registry, name, ('sre',), approval_id='CHG-2003', **args)

    assert result == 'executed:webapp'
    assert len(enforcer.calls) == 1


# === 10. Policy input uses normalized subject/roles, not raw claim shapes == #


async def test_policy_request_uses_normalized_roles_and_safe_principal() -> None:
    enforcer = _RecordingEnforcer(decision=PolicyDecision(allow=True))
    registry = ToolRegistry(policy_enforcer=enforcer)
    spy = _Spy()
    await _register(registry, spy)

    await registry.execute(
        'restart_service',
        roles=('SRE',),  # raw-cased input; normalized before policy sees it
        approval_id='CHG-3001',
        claims={'sub': 'user-42', 'tenant': 'acme-corp', 'realm_access': {'roles': ['SRE']}},
        service='webapp',
    )

    request = enforcer.calls[0]
    assert request.roles == ('sre',)
    assert request.principal_id == 'user-42'
    assert request.tenant_id == 'acme-corp'
    # The raw claims container itself must never reach the policy request.
    assert not hasattr(request, 'claims')


# === 11 & 12. Policy input is redacted and bounded; no raw leak corpus ===== #


async def test_policy_request_args_preview_is_redacted() -> None:
    enforcer = _RecordingEnforcer(decision=PolicyDecision(allow=True))
    registry = ToolRegistry(policy_enforcer=enforcer)
    spy = _Spy()
    await _register(registry, spy, name='create_ticket', side_effect=SideEffect.WRITE)

    await registry.execute(
        'create_ticket',
        roles=('sre',),
        approval_id='CHG-4001',
        claims={'sub': 'user-1', 'access_token': 'super-secret-token-value'},
        service='contact victim@example.com about ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345',
    )

    request = enforcer.calls[0]
    rendered = str(request.args_preview)
    assert 'victim@example.com' not in rendered
    assert 'ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345' not in rendered
    assert 'super-secret-token-value' not in rendered
    assert 'access_token' not in rendered


async def test_policy_request_args_preview_is_bounded() -> None:
    enforcer = _RecordingEnforcer(decision=PolicyDecision(allow=True))
    registry = ToolRegistry(policy_enforcer=enforcer)
    spy = _Spy()
    await _register(registry, spy, name='create_ticket', side_effect=SideEffect.WRITE)

    huge_kwargs = {f'k{i}': 'x' * 5000 for i in range(50)}
    await registry.execute('create_ticket', roles=('sre',), approval_id='CHG-4002', **huge_kwargs)

    preview = enforcer.calls[0].args_preview
    assert preview.get('_truncated') is True
    assert len(preview) <= 21


# === 13. Policy denial emits durable audit evidence (ISSUE 019 path) ======= #


@pytest.mark.parametrize('side_effect', [SideEffect.WRITE, SideEffect.EXECUTE])
async def test_policy_denial_emits_durable_audit_event(side_effect: SideEffect) -> None:
    writer = InMemoryAuditWriter()
    enforcer = _RecordingEnforcer(decision=PolicyDecision(allow=False, reason='ctx_blocked'))
    registry = ToolRegistry(audit_writer=writer, policy_enforcer=enforcer)
    spy = _Spy()
    await _register(registry, spy, side_effect=side_effect)

    with pytest.raises(PolicyDenied):
        await registry.execute(
            'restart_service', roles=('sre',), approval_id='CHG-5001', service='webapp'
        )

    assert len(writer.events) == 1
    event = writer.events[0]
    assert event.decision is AuditDecision.DENIED
    assert event.reason == 'ctx_blocked'


async def test_policy_dependency_failure_emits_durable_audit_event() -> None:
    writer = InMemoryAuditWriter()
    enforcer = _RecordingEnforcer(raises=RuntimeError('opa down'))
    registry = ToolRegistry(audit_writer=writer, policy_enforcer=enforcer)
    spy = _Spy()
    await _register(registry, spy)

    with pytest.raises(PolicyDenied):
        await registry.execute(
            'restart_service', roles=('sre',), approval_id='CHG-5002', service='webapp'
        )

    assert len(writer.events) == 1
    assert writer.events[0].decision is AuditDecision.DENIED
    assert writer.events[0].reason == PolicyReason.UNAVAILABLE.value
    assert 'opa down' not in str(writer.events[0].to_dict())


# === 14. RBAC denial still audited; RBAC is not weakened by policy ========= #


async def test_rbac_denial_short_circuits_before_policy_is_consulted() -> None:
    writer = InMemoryAuditWriter()
    enforcer = _RecordingEnforcer(decision=PolicyDecision(allow=True))
    registry = ToolRegistry(audit_writer=writer, policy_enforcer=enforcer)
    spy = _Spy()
    await _register(registry, spy)

    with pytest.raises(RbacDenied) as excinfo:
        await registry.execute('restart_service', roles=('viewer',), service='webapp')

    assert excinfo.value.reason is RbacReason.ROLE_DENIED
    assert spy.called is False
    assert enforcer.calls == []  # policy is never reached once RBAC denies
    assert len(writer.events) == 1
    assert writer.events[0].decision is AuditDecision.DENIED
    assert writer.events[0].reason == RbacReason.ROLE_DENIED.value


# === 15. Missing approval/change record still denies and is audited ======= #


async def test_missing_approval_denies_before_policy_and_is_audited() -> None:
    writer = InMemoryAuditWriter()
    enforcer = _RecordingEnforcer(decision=PolicyDecision(allow=True))
    registry = ToolRegistry(audit_writer=writer, policy_enforcer=enforcer)
    spy = _Spy()
    await _register(registry, spy)

    with pytest.raises(RbacDenied) as excinfo:
        # Matching role, but no approval/change record (INV-RBAC-4).
        await registry.execute('restart_service', roles=('sre',), service='webapp')

    assert excinfo.value.reason is RbacReason.APPROVAL_REQUIRED
    assert spy.called is False
    assert enforcer.calls == []
    assert len(writer.events) == 1
    assert writer.events[0].reason == RbacReason.APPROVAL_REQUIRED.value


# === Default wiring: unconfigured registry keeps existing behavior ========= #


async def test_default_registry_without_explicit_enforcer_allows_side_effects() -> None:
    """No policy_enforcer supplied -> LocalPolicyEnforcer default -> existing
    RBAC-only behavior is fully preserved (RBAC #016 / audit #019 regression)."""
    writer = InMemoryAuditWriter()
    registry = ToolRegistry(audit_writer=writer)  # no policy_enforcer kwarg
    spy = _Spy()
    await _register(registry, spy)

    result = await registry.execute(
        'restart_service', roles=('sre',), approval_id='CHG-6001', service='webapp'
    )

    assert result == 'executed:webapp'
    assert spy.called is True
    assert len(writer.events) == 1
    assert writer.events[0].decision is AuditDecision.ALLOWED
