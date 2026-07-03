# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/admin_api/src/astradesk_admin/auth.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for services/admin_api/src/astradesk_admin/auth.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Admin API ingress authentication and authorization (NEW-SEC).

The Admin API is a separate service boundary from the API Gateway (see
``docs/en/02_architecture_overview.md`` section 5). It must independently
authenticate and authorize every sensitive operation rather than trusting the
Gateway's decision, network placement/Compose isolation, or any caller-supplied
``X-AstraDesk-*`` header as a substitute for a verified bearer token
(INV-ADMIN-AUTH-3/4/9).

This module mirrors ``services/api-gateway/src/gateway/auth_dependency.py``
(ISSUE 009) and reuses the same ``astradesk_core.utils.oidc`` verifier /
``Principal`` contract — it does not redesign OIDC/JWKS verification. Role
normalization is deliberately re-implemented locally (a one-line case-fold)
rather than imported from ``services/api-gateway/src/runtime/authz.py``: that
module is API Gateway runtime internals, and the Admin API must not import
across that service boundary.
"""

from __future__ import annotations

from collections.abc import Iterable

from astradesk_core.utils.oidc import (
    AuthError,
    Principal,
    Verifier,
    build_verifier_from_env,
)
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

__all__ = [
    "get_principal",
    "install_verifier",
    "require_admin",
    "require_authenticated",
]

_BEARER_PREFIX = "bearer "
_ADMIN_ROLE = "admin"


def install_verifier(app: FastAPI) -> None:
    """Build and attach the OIDC verifier during Admin API startup.

    Call from the lifespan/startup handler. Raises ``AuthConfigError`` if
    required OIDC configuration is missing, which aborts process start
    (fail-closed, INV-FAIL-CLOSED) rather than silently serving an
    unauthenticated Admin API. This verifier instance is independent of the API
    Gateway's own verifier; each service verifies the bearer JWT for itself.
    """
    app.state.token_verifier = build_verifier_from_env()


def _extract_bearer(request: Request) -> str:
    header = request.headers.get("authorization", "")
    if not header or not header.lower().startswith(_BEARER_PREFIX):
        raise AuthError("missing_token", "missing or malformed Authorization header")
    return header[len(_BEARER_PREFIX) :].strip()


def _normalize_roles(roles: Iterable[str]) -> frozenset[str]:
    """Case-fold a principal's roles for comparison."""
    return frozenset(r.casefold() for r in roles if r)


async def require_authenticated(request: Request) -> Principal:
    """Admin API ingress auth gate (INV-ADMIN-AUTH-3/7).

    Independently verifies the Bearer JWT presented to the Admin API — it does
    not trust the API Gateway's decision or any forwarded ``X-AstraDesk-*``
    header (INV-ADMIN-AUTH-9). On failure: 401 with a stable, non-leaking
    error code; the detail body never echoes token contents
    (INV-ADMIN-AUTH-12).
    """
    verifier: Verifier = request.app.state.token_verifier
    try:
        token = _extract_bearer(request)
        principal = verifier.verify(token)
    except AuthError as exc:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail={"error": exc.code},
            headers={"WWW-Authenticate": f'Bearer error="{exc.code}"'},
        ) from exc
    request.state.principal = principal
    return principal


async def require_admin(principal: Principal = Depends(require_authenticated)) -> Principal:
    """Admin API authorization gate: require the normalized ``admin`` role.

    Runs after ``require_authenticated``, so a missing/invalid token is already
    rejected with 401. An authenticated principal without the ``admin`` role is
    rejected with 403 (INV-ADMIN-AUTH-4/8) — independent of any authorization
    decision already made by the API Gateway.
    """
    if _ADMIN_ROLE not in _normalize_roles(principal.roles):
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail={"error": "admin_role_required"},
        )
    return principal


def get_principal(request: Request) -> Principal:
    """Retrieve the Principal attached by require_authenticated (downstream use)."""
    principal = getattr(request.state, "principal", None)
    if principal is None:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail={"error": "unauthenticated"})
    return principal
