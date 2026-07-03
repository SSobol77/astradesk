# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/admin_api/tests/test_admin_auth.py
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

"""Admin API's own authentication/authorization gate (NEW-SEC).

Covers INV-ADMIN-AUTH-3/4/7/8/9/12/13: every sensitive Admin API operation
independently requires a verified Bearer JWT and the normalized 'admin' role,
regardless of any decision already made by the API Gateway proxy. /health
stays public. No caller-supplied X-AstraDesk-* header is trusted as identity.
No raw token is ever echoed back.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

import pytest
from astradesk_core.utils.oidc import AuthConfigError, AuthError, Principal
from fastapi.testclient import TestClient

from astradesk_admin.auth import install_verifier
from astradesk_admin.main import admin_router, app

_ADMIN_PRINCIPAL = Principal(subject="admin-1", roles=("admin",), scopes=(), claims={})
_VIEWER_PRINCIPAL = Principal(subject="viewer-1", roles=("viewer",), scopes=(), claims={})
_SECRET_TOKEN = "raw-secret-jwt-value-should-never-leak"

_PATH_PARAM_RE = re.compile(r"\{[^/]+\}")


class _RecordingVerifier:
    """Deterministic stand-in for the real OIDC verifier on app.state."""

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


@pytest.fixture
def admin_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, _RecordingVerifier]]:
    verifier = _RecordingVerifier(principal=_ADMIN_PRINCIPAL)
    monkeypatch.setattr(app.state, "token_verifier", verifier, raising=False)
    client = TestClient(app)
    yield client, verifier
    client.close()


def test_health_remains_public(
    admin_client: tuple[TestClient, _RecordingVerifier],
) -> None:
    client, verifier = admin_client

    response = client.get("/health")

    assert response.status_code == 200
    assert verifier.tokens == []


def test_sensitive_endpoint_rejects_missing_authorization(
    admin_client: tuple[TestClient, _RecordingVerifier],
) -> None:
    client, verifier = admin_client

    response = client.get("/secrets")

    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "missing_token"
    assert verifier.tokens == []


def test_sensitive_endpoint_rejects_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    verifier = _RecordingVerifier(error=AuthError("invalid_token", "bad signature"))
    monkeypatch.setattr(app.state, "token_verifier", verifier, raising=False)
    client = TestClient(app)

    response = client.get("/secrets", headers={"Authorization": "Bearer bad.token"})

    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "invalid_token"
    client.close()


def test_sensitive_endpoint_rejects_authenticated_non_admin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = _RecordingVerifier(principal=_VIEWER_PRINCIPAL)
    monkeypatch.setattr(app.state, "token_verifier", verifier, raising=False)
    client = TestClient(app)

    response = client.get("/secrets", headers={"Authorization": "Bearer viewer.token"})

    assert response.status_code == 403
    assert response.json()["detail"]["error"] == "admin_role_required"
    client.close()


def test_sensitive_endpoint_allows_authenticated_admin(
    admin_client: tuple[TestClient, _RecordingVerifier],
) -> None:
    client, verifier = admin_client

    response = client.get("/secrets", headers={"Authorization": "Bearer good.token"})

    assert response.status_code == 200
    assert verifier.tokens == ["good.token"]


@pytest.mark.parametrize(
    "path",
    ["/users", "/roles", "/policies", "/audit", "/jobs", "/dlq", "/usage/llm"],
)
def test_representative_sensitive_endpoints_reject_unauthenticated(
    admin_client: tuple[TestClient, _RecordingVerifier], path: str
) -> None:
    client, _verifier = admin_client

    response = client.get(path)

    assert response.status_code == 401


def test_does_not_trust_spoofed_identity_headers(
    admin_client: tuple[TestClient, _RecordingVerifier],
) -> None:
    client, verifier = admin_client

    response = client.get(
        "/secrets",
        headers={
            "X-AstraDesk-Principal": "spoofed-user",
            "X-AstraDesk-Tenant": "spoofed-tenant",
            "X-AstraDesk-Roles": "admin",
        },
    )

    assert response.status_code == 401
    assert verifier.tokens == []


def test_401_and_403_responses_never_echo_raw_token(monkeypatch: pytest.MonkeyPatch) -> None:
    bad_verifier = _RecordingVerifier(
        error=AuthError("invalid_token", f"rejected: {_SECRET_TOKEN}")
    )
    monkeypatch.setattr(app.state, "token_verifier", bad_verifier, raising=False)
    client = TestClient(app)

    response = client.get("/secrets", headers={"Authorization": f"Bearer {_SECRET_TOKEN}"})

    assert response.status_code == 401
    assert _SECRET_TOKEN not in response.text
    assert _SECRET_TOKEN not in str(response.headers)
    client.close()


def test_all_admin_router_routes_reject_unauthenticated_requests(
    admin_client: tuple[TestClient, _RecordingVerifier],
) -> None:
    """Blanket regression guard: every route registered on ``admin_router``
    (i.e. every Admin API operation except /health and the auto-generated
    docs/OpenAPI routes) must require authentication. This fails loudly if a
    future endpoint is ever added directly on ``app`` instead of
    ``admin_router``, bypassing the 'admin' gate (INV-ADMIN-AUTH-3/4)."""
    client, _verifier = admin_client

    assert len(admin_router.routes) > 0
    checked = 0
    for route in admin_router.routes:
        path = _PATH_PARAM_RE.sub("placeholder", route.path)
        methods = route.methods - {"HEAD", "OPTIONS"}
        method = sorted(methods)[0]
        response = client.request(method, path)
        assert (
            response.status_code == 401
        ), f"{method} {path} did not require authentication (got {response.status_code})"
        checked += 1

    assert checked == len(admin_router.routes)


def test_install_verifier_is_fail_closed_without_oidc_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mirrors gateway.auth_dependency's fail-closed startup contract
    (ISSUE 009, INV-FAIL-CLOSED): missing OIDC configuration must abort
    Admin API startup, not silently serve an unauthenticated API."""
    monkeypatch.delenv("AUTH_MODE", raising=False)
    monkeypatch.delenv("OIDC_ISSUER", raising=False)
    monkeypatch.delenv("OIDC_AUDIENCE", raising=False)
    monkeypatch.delenv("OIDC_JWKS_URL", raising=False)

    with pytest.raises(AuthConfigError):
        install_verifier(app)
