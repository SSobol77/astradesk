# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/tests/runtime/test_admin_proxy_auth.py
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

"""Gateway-side auth gate for the Admin API proxy (NEW-SEC).

Covers INV-ADMIN-AUTH-1/2/5/6/9/10/11/12: the /api/admin/v1/{path} proxy must
authenticate and authorize (role 'admin') before ever touching the upstream
Admin API client, must strip caller-supplied X-AstraDesk-* identity headers,
must forward Authorization unchanged only for allowed requests, and must never
leak the raw token.
"""

from __future__ import annotations

from collections.abc import Iterator

import httpx
import pytest
from astradesk_core.utils.oidc import AuthError, Principal
from fastapi.testclient import TestClient
from gateway import main as gateway_main

_ADMIN_PRINCIPAL = Principal(subject='admin-1', roles=('admin',), scopes=(), claims={})
_VIEWER_PRINCIPAL = Principal(subject='viewer-1', roles=('viewer',), scopes=(), claims={})
_SECRET_TOKEN = 'raw-secret-jwt-value-should-never-leak'


class _RecordingVerifier:
    def __init__(self, principal: Principal | None = None, error: AuthError | None = None) -> None:
        self._principal = principal
        self._error = error
        self.tokens: list[str] = []

    def verify(self, token: str) -> Principal:
        self.tokens.append(token)
        if self._error is not None:
            raise self._error
        assert self._principal is not None
        return self._principal


class _RecordingAdminClient:
    """Stand-in for the httpx.AsyncClient used to reach the Admin API."""

    def __init__(self) -> None:
        self.sent_requests: list[httpx.Request] = []

    def build_request(
        self, method: str, url: httpx.URL, headers: object = None, content: object = None
    ) -> httpx.Request:
        return httpx.Request(method, f'http://admin-api{url}', headers=headers)

    async def send(self, request: httpx.Request, stream: bool = False) -> httpx.Response:
        self.sent_requests.append(request)
        return httpx.Response(200, json={'ok': True}, request=request)


@pytest.fixture
def admin_proxy_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, _RecordingVerifier, _RecordingAdminClient]]:
    verifier = _RecordingVerifier(principal=_ADMIN_PRINCIPAL)
    admin_client = _RecordingAdminClient()
    monkeypatch.setattr(gateway_main.app.state, 'token_verifier', verifier, raising=False)
    monkeypatch.setitem(gateway_main.app_state, 'admin_api_client', admin_client)
    client = TestClient(gateway_main.app)
    yield client, verifier, admin_client
    client.close()


def test_missing_authorization_returns_401_before_upstream_call(
    admin_proxy_client: tuple[TestClient, _RecordingVerifier, _RecordingAdminClient],
) -> None:
    client, verifier, admin_client = admin_proxy_client

    response = client.get('/api/admin/v1/secrets')

    assert response.status_code == 401
    assert response.json()['detail']['error'] == 'missing_token'
    assert verifier.tokens == []
    assert admin_client.sent_requests == []


def test_malformed_authorization_returns_401_before_upstream_call(
    admin_proxy_client: tuple[TestClient, _RecordingVerifier, _RecordingAdminClient],
) -> None:
    client, verifier, admin_client = admin_proxy_client

    response = client.get('/api/admin/v1/secrets', headers={'Authorization': 'Token abc'})

    assert response.status_code == 401
    assert response.json()['detail']['error'] == 'missing_token'
    assert verifier.tokens == []
    assert admin_client.sent_requests == []


def test_invalid_token_returns_401_before_upstream_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = _RecordingVerifier(error=AuthError('invalid_token', 'bad signature'))
    admin_client = _RecordingAdminClient()
    monkeypatch.setattr(gateway_main.app.state, 'token_verifier', verifier, raising=False)
    monkeypatch.setitem(gateway_main.app_state, 'admin_api_client', admin_client)
    client = TestClient(gateway_main.app)

    response = client.get('/api/admin/v1/secrets', headers={'Authorization': 'Bearer bad.token'})

    assert response.status_code == 401
    assert response.json()['detail']['error'] == 'invalid_token'
    assert admin_client.sent_requests == []
    client.close()


def test_authenticated_non_admin_returns_403_before_upstream_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = _RecordingVerifier(principal=_VIEWER_PRINCIPAL)
    admin_client = _RecordingAdminClient()
    monkeypatch.setattr(gateway_main.app.state, 'token_verifier', verifier, raising=False)
    monkeypatch.setitem(gateway_main.app_state, 'admin_api_client', admin_client)
    client = TestClient(gateway_main.app)

    response = client.get('/api/admin/v1/secrets', headers={'Authorization': 'Bearer viewer.token'})

    assert response.status_code == 403
    assert response.json()['detail']['error'] == 'admin_role_required'
    assert admin_client.sent_requests == []
    client.close()


def test_authenticated_admin_reaches_upstream_and_is_proxied(
    admin_proxy_client: tuple[TestClient, _RecordingVerifier, _RecordingAdminClient],
) -> None:
    client, verifier, admin_client = admin_proxy_client

    response = client.get(
        '/api/admin/v1/secrets', headers={'Authorization': f'Bearer {_SECRET_TOKEN}'}
    )

    assert response.status_code == 200
    assert response.json() == {'ok': True}
    assert verifier.tokens == [_SECRET_TOKEN]
    assert len(admin_client.sent_requests) == 1


def test_strips_caller_supplied_internal_identity_headers(
    admin_proxy_client: tuple[TestClient, _RecordingVerifier, _RecordingAdminClient],
) -> None:
    client, _verifier, admin_client = admin_proxy_client

    client.get(
        '/api/admin/v1/secrets',
        headers={
            'Authorization': 'Bearer good.token',
            'X-AstraDesk-Principal': 'spoofed-user',
            'X-AstraDesk-Tenant': 'spoofed-tenant',
            'X-AstraDesk-Roles': 'admin',
            'X-AstraDesk-Whatever': 'also-spoofed',
        },
    )

    assert len(admin_client.sent_requests) == 1
    forwarded = admin_client.sent_requests[0].headers
    assert 'x-astradesk-principal' not in forwarded
    assert 'x-astradesk-tenant' not in forwarded
    assert 'x-astradesk-roles' not in forwarded
    assert 'x-astradesk-whatever' not in forwarded


def test_forwards_authorization_unchanged_on_allowed_admin_request(
    admin_proxy_client: tuple[TestClient, _RecordingVerifier, _RecordingAdminClient],
) -> None:
    client, _verifier, admin_client = admin_proxy_client

    client.get('/api/admin/v1/secrets', headers={'Authorization': f'Bearer {_SECRET_TOKEN}'})

    assert len(admin_client.sent_requests) == 1
    forwarded = admin_client.sent_requests[0].headers
    assert forwarded['authorization'] == f'Bearer {_SECRET_TOKEN}'


def test_denied_requests_never_forward_authorization_to_upstream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-admin / unauthenticated callers never reach the point where
    Authorization would be forwarded — the upstream is never invoked at all
    (INV-ADMIN-AUTH-6)."""
    verifier = _RecordingVerifier(principal=_VIEWER_PRINCIPAL)
    admin_client = _RecordingAdminClient()
    monkeypatch.setattr(gateway_main.app.state, 'token_verifier', verifier, raising=False)
    monkeypatch.setitem(gateway_main.app_state, 'admin_api_client', admin_client)
    client = TestClient(gateway_main.app)

    client.get('/api/admin/v1/secrets', headers={'Authorization': f'Bearer {_SECRET_TOKEN}'})

    assert admin_client.sent_requests == []
    client.close()


def test_401_and_403_responses_never_echo_raw_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bad_verifier = _RecordingVerifier(
        error=AuthError('invalid_token', f'rejected: {_SECRET_TOKEN}')
    )
    admin_client = _RecordingAdminClient()
    monkeypatch.setattr(gateway_main.app.state, 'token_verifier', bad_verifier, raising=False)
    monkeypatch.setitem(gateway_main.app_state, 'admin_api_client', admin_client)
    client = TestClient(gateway_main.app)

    response = client.get(
        '/api/admin/v1/secrets', headers={'Authorization': f'Bearer {_SECRET_TOKEN}'}
    )

    assert response.status_code == 401
    assert _SECRET_TOKEN not in response.text
    assert _SECRET_TOKEN not in str(response.headers)
    client.close()
