# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/src/gateway/auth_dependency.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for services/api-gateway/src/gateway/auth_dependency.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

from __future__ import annotations

from astradesk_core.utils.oidc import (
    AuthError,
    Principal,
    Verifier,
    build_verifier_from_env,
)
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import HTTPException
from runtime.authz import normalize_roles
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

__all__ = [
    'get_principal',
    'install_verifier',
    'require_admin_role',
    'require_authenticated',
]

_BEARER_PREFIX = 'bearer '
_ADMIN_ROLE = 'admin'


def install_verifier(app: FastAPI) -> None:
    """Build and attach the verifier during startup.

    Call from the lifespan/startup handler. Raises AuthConfigError if required
    auth configuration is missing, which aborts process start (fail-closed).
    """
    app.state.token_verifier = build_verifier_from_env()


def _extract_bearer(request: Request) -> str:
    header = request.headers.get('authorization', '')
    if not header or not header.lower().startswith(_BEARER_PREFIX):
        raise AuthError('missing_token', 'missing or malformed Authorization header')
    return header[len(_BEARER_PREFIX) :].strip()


async def require_authenticated(request: Request) -> Principal:
    """Ingress auth dependency. Use as ``Depends(require_authenticated)``.

    On success: returns the Principal and stores it on request.state.principal.
    On failure: 401 with a stable WWW-Authenticate error code; the detail body
    never echoes token contents.
    """
    verifier: Verifier = request.app.state.token_verifier
    try:
        token = _extract_bearer(request)
        principal = verifier.verify(token)
    except AuthError as exc:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail={'error': exc.code},
            headers={'WWW-Authenticate': f'Bearer error="{exc.code}"'},
        ) from exc
    request.state.principal = principal
    return principal


async def require_admin_role(
    principal: Principal = Depends(require_authenticated),
) -> Principal:
    """Gateway authorization gate for the Admin API proxy (INV-ADMIN-AUTH-2/6).

    Runs after ``require_authenticated``, so a missing/invalid token is already
    rejected with 401 before this check. An authenticated principal without the
    normalized ``admin`` role is rejected with 403 — before the request reaches
    the Admin API upstream (NEW-SEC). Reuses the same case-fold role convention
    as the RBAC choke point (ISSUE 016, :func:`runtime.authz.normalize_roles`)
    rather than inventing a second one.
    """
    if _ADMIN_ROLE not in normalize_roles(principal.roles):
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail={'error': 'admin_role_required'},
        )
    return principal


def get_principal(request: Request) -> Principal:
    """Retrieve the Principal attached by require_authenticated (downstream use)."""
    principal = getattr(request.state, 'principal', None)
    if principal is None:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail={'error': 'unauthenticated'})
    return principal
