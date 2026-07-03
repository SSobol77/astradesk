# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/tests/runtime/test_policy_enforcer.py
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

"""Tests for src/runtime/policy_enforcer.py (ISSUE 028 fail-closed policy).

Covers:
- LocalPolicyEnforcer: deterministic allow-all (explicit local/dev/test/ci mode).
- OpaHttpPolicyEnforcer: allow/deny decisions, and fail-closed behavior on
  transport errors, timeouts, non-2xx responses, and ambiguous decisions —
  exercised against ``httpx.MockTransport`` so no real OPA server is required
  (INV-POLICY-10).
- PolicyRequest.to_input(): structurally cannot carry raw claims/tokens.
- build_policy_enforcer_from_env(): the full fail-closed tier/mode matrix,
  mirroring astradesk_core.utils.oidc.build_verifier_from_env and
  gateway.main._resolve_audit_writer.
"""

from __future__ import annotations

import httpx
import pytest
from runtime.authz import SideEffect
from runtime.policy_enforcer import (
    LocalPolicyEnforcer,
    OpaHttpPolicyEnforcer,
    PolicyConfigError,
    PolicyReason,
    PolicyRequest,
    build_policy_enforcer_from_env,
)

# NOTE: no blanket `pytestmark = pytest.mark.asyncio` here — this module mixes
# async (enforcer) and sync (factory-function) tests, and asyncio_mode="auto"
# (root pyproject.toml) already detects async tests without a marker.


def _request(**overrides: object) -> PolicyRequest:
    defaults: dict[str, object] = {
        'tool': 'restart_service',
        'side_effect': SideEffect.EXECUTE,
        'roles': ('sre',),
        'principal_id': 'user-1',
        'tenant_id': 'acme',
        'trace_id': 'trace-1',
        'request_id': 'req-1',
        'approval_id': 'CHG-1001',
        'args_preview': {'service': 'webapp'},
    }
    defaults.update(overrides)
    return PolicyRequest(**defaults)  # type: ignore[arg-type]


# === LocalPolicyEnforcer ===================================================== #


async def test_local_policy_enforcer_always_allows() -> None:
    enforcer = LocalPolicyEnforcer()
    decision = await enforcer.evaluate(_request())
    assert decision.allow is True
    assert decision.reason is None


# === PolicyRequest.to_input() shape ========================================= #


def test_policy_request_to_input_carries_only_safe_fields() -> None:
    request = _request()
    payload = request.to_input()

    assert payload['tool'] == {'name': 'restart_service', 'side_effect': 'execute'}
    assert payload['auth'] == {'roles': ['sre'], 'principal_id': 'user-1'}
    assert payload['context']['tenant_id'] == 'acme'
    assert payload['context']['approval_id'] == 'CHG-1001'
    assert payload['args_preview'] == {'service': 'webapp'}
    # Structurally impossible to leak: there is no field for raw claims/token.
    blob = str(payload)
    assert 'claims' not in blob
    assert 'token' not in blob
    assert 'password' not in blob


# === OpaHttpPolicyEnforcer: allow/deny decisions ============================ #


def _client_with_handler(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_opa_enforcer_allows_on_boolean_true_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == '/v1/data/astradesk/tools/allow'
        return httpx.Response(200, json={'result': True})

    enforcer = OpaHttpPolicyEnforcer(
        base_url='http://opa.local:8181', client=_client_with_handler(handler)
    )
    decision = await enforcer.evaluate(_request())
    assert decision.allow is True


async def test_opa_enforcer_allows_on_dict_allow_true() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={'result': {'allow': True}})

    enforcer = OpaHttpPolicyEnforcer(
        base_url='http://opa.local:8181', client=_client_with_handler(handler)
    )
    decision = await enforcer.evaluate(_request())
    assert decision.allow is True


async def test_opa_enforcer_denies_and_surfaces_reason() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={'result': {'allow': False, 'reason': 'no_capacity'}})

    enforcer = OpaHttpPolicyEnforcer(
        base_url='http://opa.local:8181', client=_client_with_handler(handler)
    )
    decision = await enforcer.evaluate(_request())
    assert decision.allow is False
    assert decision.reason == 'no_capacity'


async def test_opa_enforcer_denies_without_reason_uses_stable_code() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={'result': False})

    enforcer = OpaHttpPolicyEnforcer(
        base_url='http://opa.local:8181', client=_client_with_handler(handler)
    )
    decision = await enforcer.evaluate(_request())
    assert decision.allow is False
    assert decision.reason == PolicyReason.DENIED.value


async def test_opa_enforcer_sends_only_the_policy_request_shape() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        captured['body'] = json.loads(request.content)
        return httpx.Response(200, json={'result': True})

    enforcer = OpaHttpPolicyEnforcer(
        base_url='http://opa.local:8181', client=_client_with_handler(handler)
    )
    await enforcer.evaluate(_request())

    sent = captured['body']
    assert sent == {'input': _request().to_input()}


# === OpaHttpPolicyEnforcer: fail-closed behavior ============================ #


async def test_opa_enforcer_fails_closed_on_connection_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError('connection refused', request=request)

    enforcer = OpaHttpPolicyEnforcer(
        base_url='http://opa.local:8181', client=_client_with_handler(handler)
    )
    decision = await enforcer.evaluate(_request())
    assert decision.allow is False
    assert decision.reason == PolicyReason.UNAVAILABLE.value


async def test_opa_enforcer_fails_closed_on_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout('timed out', request=request)

    enforcer = OpaHttpPolicyEnforcer(
        base_url='http://opa.local:8181', client=_client_with_handler(handler)
    )
    decision = await enforcer.evaluate(_request())
    assert decision.allow is False
    assert decision.reason == PolicyReason.UNAVAILABLE.value


async def test_opa_enforcer_fails_closed_on_non_2xx_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={'error': 'internal'})

    enforcer = OpaHttpPolicyEnforcer(
        base_url='http://opa.local:8181', client=_client_with_handler(handler)
    )
    decision = await enforcer.evaluate(_request())
    assert decision.allow is False
    assert decision.reason == PolicyReason.UNAVAILABLE.value


@pytest.mark.parametrize(
    'body',
    [
        {'result': {}},
        {'result': {'allow': 'yes'}},
        {'result': None},
        {},
    ],
)
async def test_opa_enforcer_fails_closed_on_ambiguous_decision(body: dict[str, object]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    enforcer = OpaHttpPolicyEnforcer(
        base_url='http://opa.local:8181', client=_client_with_handler(handler)
    )
    decision = await enforcer.evaluate(_request())
    assert decision.allow is False
    assert decision.reason == PolicyReason.UNAVAILABLE.value


async def test_opa_enforcer_fails_closed_on_non_json_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b'not json')

    enforcer = OpaHttpPolicyEnforcer(
        base_url='http://opa.local:8181', client=_client_with_handler(handler)
    )
    decision = await enforcer.evaluate(_request())
    assert decision.allow is False
    assert decision.reason == PolicyReason.UNAVAILABLE.value


async def test_opa_enforcer_custom_policy_path_used_in_url() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == '/v1/data/custom/pkg/allow'
        return httpx.Response(200, json={'result': True})

    enforcer = OpaHttpPolicyEnforcer(
        base_url='http://opa.local:8181',
        policy_path='custom.pkg.allow',
        client=_client_with_handler(handler),
    )
    decision = await enforcer.evaluate(_request())
    assert decision.allow is True


async def test_opa_enforcer_aclose_closes_owned_client() -> None:
    enforcer = OpaHttpPolicyEnforcer(base_url='http://opa.local:8181')  # no client injected
    assert enforcer._client.is_closed is False
    await enforcer.aclose()
    assert enforcer._client.is_closed is True


async def test_opa_enforcer_aclose_is_noop_for_injected_client() -> None:
    client = _client_with_handler(lambda r: httpx.Response(200, json={'result': True}))
    enforcer = OpaHttpPolicyEnforcer(base_url='http://opa.local:8181', client=client)
    await enforcer.aclose()
    assert client.is_closed is False  # injected client is owned by the caller
    await client.aclose()


# === build_policy_enforcer_from_env(): fail-closed tier/mode matrix ========= #


@pytest.mark.parametrize('tier', ['production', 'prod', 'staging', 'stage', 'PRODUCTION'])
def test_deployed_tier_without_opa_url_fails_closed(
    tier: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv('POLICY_MODE', raising=False)
    monkeypatch.delenv('OPA_URL', raising=False)
    monkeypatch.setenv('ENVIRONMENT', tier)

    with pytest.raises(PolicyConfigError):
        build_policy_enforcer_from_env()


def test_environment_unset_defaults_to_deployed_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    """ENVIRONMENT absent entirely must behave like ENVIRONMENT=production,
    matching the fail-closed default used by OIDC/audit (ISSUE 009/019)."""
    monkeypatch.delenv('ENVIRONMENT', raising=False)
    monkeypatch.delenv('POLICY_MODE', raising=False)
    monkeypatch.delenv('OPA_URL', raising=False)

    with pytest.raises(PolicyConfigError):
        build_policy_enforcer_from_env()


@pytest.mark.parametrize('tier', ['production', 'prod', 'staging', 'stage'])
def test_deployed_tier_with_opa_url_builds_opa_enforcer(
    tier: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv('POLICY_MODE', raising=False)
    monkeypatch.setenv('OPA_URL', 'http://opa.internal:8181')
    monkeypatch.setenv('ENVIRONMENT', tier)

    enforcer = build_policy_enforcer_from_env()
    assert isinstance(enforcer, OpaHttpPolicyEnforcer)


@pytest.mark.parametrize('tier', ['dev', 'development', 'test', 'local', 'ci'])
def test_non_deployed_tier_defaults_to_local_enforcer(
    tier: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv('POLICY_MODE', raising=False)
    monkeypatch.delenv('OPA_URL', raising=False)
    monkeypatch.setenv('ENVIRONMENT', tier)

    enforcer = build_policy_enforcer_from_env()
    assert isinstance(enforcer, LocalPolicyEnforcer)


def test_policy_mode_local_forbidden_on_deployed_tier(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('POLICY_MODE', 'local')
    monkeypatch.setenv('ENVIRONMENT', 'production')

    with pytest.raises(PolicyConfigError):
        build_policy_enforcer_from_env()


def test_policy_mode_local_allowed_on_non_deployed_tier(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('POLICY_MODE', 'local')
    monkeypatch.setenv('ENVIRONMENT', 'dev')

    enforcer = build_policy_enforcer_from_env()
    assert isinstance(enforcer, LocalPolicyEnforcer)


def test_policy_mode_opa_requires_opa_url_regardless_of_tier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('POLICY_MODE', 'opa')
    monkeypatch.delenv('OPA_URL', raising=False)
    monkeypatch.setenv('ENVIRONMENT', 'dev')

    with pytest.raises(PolicyConfigError):
        build_policy_enforcer_from_env()


def test_policy_mode_opa_builds_enforcer_even_on_dev_tier(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('POLICY_MODE', 'opa')
    monkeypatch.setenv('OPA_URL', 'http://opa.internal:8181')
    monkeypatch.setenv('ENVIRONMENT', 'dev')

    enforcer = build_policy_enforcer_from_env()
    assert isinstance(enforcer, OpaHttpPolicyEnforcer)


def test_unknown_policy_mode_aborts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('POLICY_MODE', 'anything-goes')

    with pytest.raises(PolicyConfigError):
        build_policy_enforcer_from_env()


def test_invalid_opa_timeout_seconds_aborts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('POLICY_MODE', 'opa')
    monkeypatch.setenv('OPA_URL', 'http://opa.internal:8181')
    monkeypatch.setenv('OPA_TIMEOUT_SECONDS', 'not-a-number')

    with pytest.raises(PolicyConfigError):
        build_policy_enforcer_from_env()
