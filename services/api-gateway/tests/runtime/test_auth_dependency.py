# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/tests/runtime/test_auth_dependency.py
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

from __future__ import annotations

from astradesk_core.utils.oidc import AuthError, Principal
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient
from gateway.auth_dependency import get_principal, require_authenticated

HANDLER_MARKER = {"handler_ran": True}


class _FakeVerifier:
    """Deterministic stand-in for the real verifier on app.state."""

    def __init__(self, principal: Principal | None = None, error: AuthError | None = None):
        self._principal = principal
        self._error = error

    def verify(self, token: str) -> Principal:
        if self._error is not None:
            raise self._error
        assert self._principal is not None
        return self._principal


def _make_app(verifier: _FakeVerifier) -> FastAPI:
    app = FastAPI()
    app.state.token_verifier = verifier

    @app.get("/protected")
    async def protected(
        request: Request, principal: Principal = Depends(require_authenticated)
    ):
        # Reaching here means the gate let the request through.
        attached = get_principal(request)
        return {"handler_ran": True, "sub": principal.subject, "attached": attached.subject}

    return app


_VALID_PRINCIPAL = Principal(subject="user-1", roles=("operator",), scopes=(), claims={})


def test_missing_header_returns_401_and_skips_handler():
    client = TestClient(_make_app(_FakeVerifier(principal=_VALID_PRINCIPAL)))
    resp = client.get("/protected")
    assert resp.status_code == 401
    assert resp.json()["detail"]["error"] == "missing_token"


def test_malformed_header_returns_401():
    client = TestClient(_make_app(_FakeVerifier(principal=_VALID_PRINCIPAL)))
    resp = client.get("/protected", headers={"Authorization": "Token abc"})
    assert resp.status_code == 401
    assert resp.json()["detail"]["error"] == "missing_token"


def test_verifier_autherror_maps_to_401():
    bad = _FakeVerifier(error=AuthError("token_expired", "expired"))
    client = TestClient(_make_app(bad))
    resp = client.get("/protected", headers={"Authorization": "Bearer x.y.z"})
    assert resp.status_code == 401
    assert resp.json()["detail"]["error"] == "token_expired"
    assert resp.headers.get("WWW-Authenticate") == 'Bearer error="token_expired"'


def test_valid_token_reaches_handler_and_attaches_principal():
    client = TestClient(_make_app(_FakeVerifier(principal=_VALID_PRINCIPAL)))
    resp = client.get("/protected", headers={"Authorization": "Bearer good.token"})
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"handler_ran": True, "sub": "user-1", "attached": "user-1"}
