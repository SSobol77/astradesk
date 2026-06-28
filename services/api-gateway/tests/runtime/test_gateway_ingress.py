# SPDX-License-Identifier: GPL-2.0-only
# File: services/api-gateway/tests/runtime/test_gateway_ingress.py
#
# Active API Gateway ingress tests for ISSUE 009.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from astradesk_core.utils.oidc import AuthError, Principal
from fastapi.testclient import TestClient
from gateway import main as gateway_main
from runtime.models import AgentRequest, AgentResponse

_AGENT_REQUEST = {
    'agent': 'support',
    'input': 'Check the active ingress authentication boundary.',
    'meta': {},
}

_PRINCIPAL = Principal(
    subject='operator-1',
    roles=('operator',),
    scopes=('agents:run',),
    claims={'sub': 'operator-1', 'roles': ['operator'], 'scope': 'agents:run'},
)

_REQUEST_ID = '00000000-0000-4000-8000-000000000009'


class _RecordingVerifier:
    def __init__(self) -> None:
        self.tokens: list[str] = []

    def verify(self, token: str) -> Principal:
        self.tokens.append(token)
        if token != 'valid-token':
            raise AuthError('invalid_token', 'test verifier rejected token')
        return _PRINCIPAL


class _RecordingOrchestrator:
    def __init__(self) -> None:
        self.calls: list[tuple[AgentRequest, dict[str, Any], str]] = []

    async def run(
        self, request: AgentRequest, claims: dict[str, Any], request_id: str
    ) -> AgentResponse:
        self.calls.append((request, claims, request_id))
        return AgentResponse(
            output='Ingress accepted the authenticated request.',
            reasoning_trace_id=request_id,
            invoked_tools=[],
        )


@pytest.fixture
def ingress_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, _RecordingVerifier, _RecordingOrchestrator]]:
    verifier = _RecordingVerifier()
    orchestrator = _RecordingOrchestrator()
    monkeypatch.setattr(
        gateway_main.app.state, 'token_verifier', verifier, raising=False
    )
    monkeypatch.setitem(gateway_main.app_state, 'orchestrator', orchestrator)
    client = TestClient(gateway_main.app)
    yield client, verifier, orchestrator
    client.close()


def test_missing_authorization_returns_401_before_handler(
    ingress_client: tuple[TestClient, _RecordingVerifier, _RecordingOrchestrator],
) -> None:
    client, verifier, orchestrator = ingress_client

    response = client.post('/v1/run', json=_AGENT_REQUEST)

    assert response.status_code == 401
    assert response.json()['detail']['error'] == 'missing_token'
    assert verifier.tokens == []
    assert orchestrator.calls == []


def test_invalid_authorization_returns_401_before_handler(
    ingress_client: tuple[TestClient, _RecordingVerifier, _RecordingOrchestrator],
) -> None:
    client, verifier, orchestrator = ingress_client

    response = client.post(
        '/v1/run',
        json=_AGENT_REQUEST,
        headers={'Authorization': 'Bearer invalid-token'},
    )

    assert response.status_code == 401
    assert response.json()['detail']['error'] == 'invalid_token'
    assert verifier.tokens == ['invalid-token']
    assert orchestrator.calls == []


def test_authenticated_request_reaches_handler_with_verified_claims(
    ingress_client: tuple[TestClient, _RecordingVerifier, _RecordingOrchestrator],
) -> None:
    client, verifier, orchestrator = ingress_client

    response = client.post(
        '/v1/run',
        json=_AGENT_REQUEST,
        headers={
            'Authorization': 'Bearer valid-token',
            'X-Request-ID': _REQUEST_ID,
        },
    )

    assert response.status_code == 200
    assert verifier.tokens == ['valid-token']
    assert len(orchestrator.calls) == 1
    request, claims, request_id = orchestrator.calls[0]
    assert request.agent.value == 'support'
    assert claims == dict(_PRINCIPAL.claims)
    assert request_id == _REQUEST_ID


def test_healthz_remains_public_and_bypasses_verifier(
    ingress_client: tuple[TestClient, _RecordingVerifier, _RecordingOrchestrator],
) -> None:
    client, verifier, orchestrator = ingress_client

    response = client.get('/healthz')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}
    assert verifier.tokens == []
    assert orchestrator.calls == []


@pytest.mark.asyncio
async def test_lifespan_installs_verifier_before_external_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed_on: list[object] = []

    class _VerifierInstallFailed(RuntimeError):
        pass

    def fail_install(app: object) -> None:
        installed_on.append(app)
        raise _VerifierInstallFailed

    async def unexpected_pool_creation(*args: object, **kwargs: object) -> None:
        pytest.fail('database initialization ran before verifier installation')

    monkeypatch.setattr(gateway_main, 'install_verifier', fail_install)
    monkeypatch.setattr(gateway_main.asyncpg, 'create_pool', unexpected_pool_creation)

    with pytest.raises(_VerifierInstallFailed):
        async with gateway_main.lifespan(gateway_main.app):
            pytest.fail('lifespan yielded after verifier installation failed')

    assert installed_on == [gateway_main.app]
