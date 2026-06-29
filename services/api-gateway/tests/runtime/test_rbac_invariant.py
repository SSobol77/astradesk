# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/tests/runtime/test_rbac_invariant.py
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

"""RBAC invariant tests for the single tool-execution choke point (ISSUE 016).

These tests verify that authorization is a property of the tool invocation, not
of the code path that produced it. The same ``ToolRegistry.execute`` choke point
is exercised exactly as the LLM-planned path (orchestrator) and the
keyword-fallback path (agents) call it, and the dual-path negative matrix asserts
that an unauthorized side-effect call is denied identically in every cell.
"""

from __future__ import annotations

import pytest
from runtime.authz import (
    AuthorizationError,
    RbacDenied,
    RbacReason,
    RegistryInvariantError,
    SideEffect,
    authorize_tool,
    enforce_registration_invariants,
)
from runtime.planner import KeywordPlanner
from runtime.registry import ToolRegistrationError, ToolRegistry

pytestmark = pytest.mark.asyncio


class _Spy:
    """Records whether the underlying tool function was invoked.

    ``as_tool`` returns a genuine coroutine function so the registry awaits it on
    the real async execution path.
    """

    def __init__(self) -> None:
        self.called = False

    def as_tool(self):  # returns an async tool callable
        async def fn(*, service: str = '', **_: object) -> str:
            self.called = True
            return f'executed:{service}'

        return fn


async def _register_side_effect_tool(
    registry: ToolRegistry,
    spy: _Spy,
    *,
    name: str = 'restart_service',
    side_effect: SideEffect = SideEffect.WRITE,
    allowed_roles: set[str] | None = None,
) -> None:
    await registry.register(
        name,
        spy.as_tool(),
        side_effect=side_effect,
        allowed_roles=allowed_roles if allowed_roles is not None else {'sre'},
    )


# === 1. Authorized side-effect call executes ============================== #


async def test_side_effect_tool_with_matching_role_and_approval_executes() -> None:
    registry = ToolRegistry()
    spy = _Spy()
    await _register_side_effect_tool(registry, spy)

    result = await registry.execute(
        'restart_service', roles=('sre',), approval_id='CHG-1001', service='webapp'
    )

    assert result == 'executed:webapp'
    assert spy.called is True


# === 2 & 6. Unauthorized call denied and underlying fn not invoked ========= #


async def test_side_effect_tool_without_matching_role_is_denied() -> None:
    registry = ToolRegistry()
    spy = _Spy()
    await _register_side_effect_tool(registry, spy)

    with pytest.raises(RbacDenied) as excinfo:
        await registry.execute('restart_service', roles=('viewer',), service='webapp')

    assert excinfo.value.reason is RbacReason.ROLE_DENIED
    assert spy.called is False  # denied before execution


# === 3. Missing allowed_roles on a side-effect tool fails closed =========== #


async def test_side_effect_tool_missing_allowed_roles_is_rejected_at_registration() -> None:
    registry = ToolRegistry()
    spy = _Spy()

    with pytest.raises(ToolRegistrationError):
        await registry.register(
            'restart_service', spy, side_effect=SideEffect.WRITE, allowed_roles=set()
        )


async def test_boot_invariant_aborts_for_roleless_side_effect_tool() -> None:
    # Even if a roleless side-effect tool reached the registry, the boot-time
    # sweep aborts startup (fail-closed) rather than waiting for a call.
    with pytest.raises(RegistryInvariantError):
        enforce_registration_invariants([('rogue_write', SideEffect.WRITE, set(), True)])


# === 4. Missing side_effect metadata is rejected at registry validation ==== #


async def test_missing_side_effect_metadata_is_rejected_at_registration() -> None:
    registry = ToolRegistry()

    async def tool(**_: object) -> str:
        return 'ok'

    with pytest.raises(ToolRegistrationError):
        await registry.register('mystery', tool)  # no side_effect declared


async def test_boot_invariant_aborts_for_missing_side_effect_metadata() -> None:
    with pytest.raises(RegistryInvariantError):
        enforce_registration_invariants([('mystery', None, set(), False)])


async def test_boot_invariant_aborts_when_side_effect_tool_bypasses_approval() -> None:
    # A write/execute tool registered without approval enforcement is a bypass
    # of INV-RBAC-4 and must abort startup.
    with pytest.raises(RegistryInvariantError):
        enforce_registration_invariants([('rogue_exec', SideEffect.EXECUTE, {'sre'}, False)])


# === 5. Read-only tool with side_effect=read works without roles =========== #


async def test_read_only_tool_without_roles_executes() -> None:
    registry = ToolRegistry()
    spy = _Spy()
    await registry.register(
        'get_metrics',
        spy.as_tool(),
        side_effect=SideEffect.READ,
        description='read-only',
    )

    result = await registry.execute('get_metrics', roles=(), service='webapp')

    assert result == 'executed:webapp'
    assert spy.called is True


# === 7 & 8. Dual-path negative matrix: LLM-planned vs keyword-fallback ===== #


async def _invoke_as_agent_path(
    registry: ToolRegistry,
    name: str,
    roles: tuple[str, ...],
    *,
    approval_id: str | None = None,
    **args: object,
) -> object:
    """Mirror the exact call both runtime paths make to the choke point.

    The orchestrator (LLM path) and BaseAgent/OpsAgent/... (keyword-fallback
    path) both call
    ``self.tools.execute(step.name, roles=..., approval_id=..., claims=..., **args)``.
    Routing the test through this single helper proves authority does not depend
    on which planner produced the step (``INV-DUAL-PATH``).
    """
    return await registry.execute(name, roles=roles, approval_id=approval_id, claims={}, **args)


@pytest.mark.parametrize('path', ['llm_planned', 'keyword_fallback'])
async def test_dual_path_unauthorized_side_effect_is_denied(path: str) -> None:
    registry = ToolRegistry()
    spy = _Spy()
    await _register_side_effect_tool(registry, spy)

    if path == 'keyword_fallback':
        # The deterministic planner resolves the side-effecting step itself.
        steps = KeywordPlanner().make_plan('please restart webapp now')
        assert steps and steps[0].name == 'restart_service'
        name, args = steps[0].name, steps[0].arguments
    else:
        # The LLM planner would emit an equivalent resolved step.
        name, args = 'restart_service', {'service': 'webapp'}

    with pytest.raises(RbacDenied) as excinfo:
        await _invoke_as_agent_path(registry, name, ('viewer',), **args)

    assert excinfo.value.reason is RbacReason.ROLE_DENIED
    assert spy.called is False


@pytest.mark.parametrize('path', ['llm_planned', 'keyword_fallback'])
async def test_dual_path_authorized_side_effect_executes(path: str) -> None:
    registry = ToolRegistry()
    spy = _Spy()
    await _register_side_effect_tool(registry, spy)

    if path == 'keyword_fallback':
        steps = KeywordPlanner().make_plan('please restart webapp now')
        name, args = steps[0].name, steps[0].arguments
    else:
        name, args = 'restart_service', {'service': 'webapp'}

    result = await _invoke_as_agent_path(registry, name, ('sre',), approval_id='CHG-2002', **args)

    assert result == 'executed:webapp'
    assert spy.called is True


# === INV-RBAC-4: approval/change-record hard gate on both paths =========== #


@pytest.mark.parametrize('path', ['llm_planned', 'keyword_fallback'])
@pytest.mark.parametrize('side_effect', [SideEffect.WRITE, SideEffect.EXECUTE])
async def test_dual_path_authorized_role_missing_approval_is_denied(
    path: str, side_effect: SideEffect
) -> None:
    # A matching role is NOT sufficient for write/execute: absence of an
    # approval/change record denies before the tool function runs (INV-RBAC-4).
    registry = ToolRegistry()
    spy = _Spy()
    await _register_side_effect_tool(registry, spy, side_effect=side_effect, allowed_roles={'sre'})

    if path == 'keyword_fallback':
        steps = KeywordPlanner().make_plan('please restart webapp now')
        name, args = steps[0].name, steps[0].arguments
    else:
        name, args = 'restart_service', {'service': 'webapp'}

    with pytest.raises(RbacDenied) as excinfo:
        await _invoke_as_agent_path(registry, name, ('sre',), **args)  # no approval

    assert excinfo.value.reason is RbacReason.APPROVAL_REQUIRED
    assert spy.called is False


@pytest.mark.parametrize('path', ['llm_planned', 'keyword_fallback'])
@pytest.mark.parametrize('side_effect', [SideEffect.WRITE, SideEffect.EXECUTE])
@pytest.mark.parametrize('approval_field', ['approval_id', 'change_record', 'change_record_id'])
async def test_dual_path_authorized_role_with_approval_executes(
    path: str, side_effect: SideEffect, approval_field: str
) -> None:
    # Authorized role + approval/change record (supplied via any accepted field
    # name, here through the invocation arguments) executes on both paths.
    registry = ToolRegistry()
    spy = _Spy()
    await _register_side_effect_tool(registry, spy, side_effect=side_effect, allowed_roles={'sre'})

    if path == 'keyword_fallback':
        steps = KeywordPlanner().make_plan('please restart webapp now')
        name, args = steps[0].name, dict(steps[0].arguments)
    else:
        name, args = 'restart_service', {'service': 'webapp'}

    args[approval_field] = 'CHG-3003'  # approval id arriving via invocation args

    result = await _invoke_as_agent_path(registry, name, ('sre',), **args)

    assert result == 'executed:webapp'
    assert spy.called is True


# === 9. Empty-role principal denied for write/execute ====================== #


async def test_empty_roles_denied_for_write_and_execute() -> None:
    registry = ToolRegistry()
    write_spy, exec_spy = _Spy(), _Spy()
    await _register_side_effect_tool(
        registry,
        write_spy,
        name='create_ticket',
        side_effect=SideEffect.WRITE,
        allowed_roles={'it.support'},
    )
    await _register_side_effect_tool(
        registry,
        exec_spy,
        name='restart_service',
        side_effect=SideEffect.EXECUTE,
        allowed_roles={'sre'},
    )

    with pytest.raises(RbacDenied):
        await registry.execute('create_ticket', roles=(), service='x')
    with pytest.raises(RbacDenied):
        await registry.execute('restart_service', roles=(), service='x')

    assert write_spy.called is False
    assert exec_spy.called is False


# === 10. Denial response does not leak claims/token/secrets ================ #


async def test_denial_does_not_leak_claims_or_secrets() -> None:
    registry = ToolRegistry()
    spy = _Spy()
    await _register_side_effect_tool(registry, spy)

    secret_token = 'eyJhbGciOiJ.SUPER-SECRET-TOKEN.sig'
    leaky_claims = {
        'sub': 'user-1',
        'roles': ['viewer'],
        'access_token': secret_token,
        'password': 'hunter2',
    }

    with pytest.raises(RbacDenied) as excinfo:
        await registry.execute(
            'restart_service', roles=('viewer',), claims=leaky_claims, service='webapp'
        )

    rendered = f'{excinfo.value!s} {excinfo.value!r}'
    assert secret_token not in rendered
    assert 'SUPER-SECRET-TOKEN' not in rendered
    assert 'hunter2' not in rendered
    assert 'access_token' not in rendered
    # Only the tool name, the stable reason code, and required roles are exposed.
    assert 'restart_service' in rendered
    assert excinfo.value.reason.value == 'RBAC_DENIED'


# === Choke-point unit coverage: reasons and approval gating ================ #


async def test_authorize_tool_missing_metadata_denies() -> None:
    with pytest.raises(RbacDenied) as excinfo:
        authorize_tool(tool='x', side_effect=None, allowed_roles=set(), roles=('sre',))
    assert excinfo.value.reason is RbacReason.METADATA_MISSING


async def test_authorize_tool_requires_approval_when_marked() -> None:
    with pytest.raises(RbacDenied) as excinfo:
        authorize_tool(
            tool='restart_service',
            side_effect=SideEffect.EXECUTE,
            allowed_roles={'sre'},
            roles=('sre',),
            requires_approval=True,
            approval_id=None,
        )
    assert excinfo.value.reason is RbacReason.APPROVAL_REQUIRED

    # With an approval id present, the same authorized principal passes.
    authorize_tool(
        tool='restart_service',
        side_effect=SideEffect.EXECUTE,
        allowed_roles={'sre'},
        roles=('sre',),
        requires_approval=True,
        approval_id='CHG-123',
    )


async def test_rbac_denied_is_authorization_error() -> None:
    # Backward-compatible exception hierarchy for existing call sites.
    assert issubclass(RbacDenied, AuthorizationError)
