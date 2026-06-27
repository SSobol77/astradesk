"""Dependency-free RBAC helpers shared by standalone domain packs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


class AuthorizationError(PermissionError):
    """Raised when a caller lacks a required role."""


def _claim_values(claims: Mapping[str, Any], path: tuple[str, ...]) -> list[str]:
    value: Any = claims
    for part in path:
        if not isinstance(value, Mapping) or part not in value:
            return []
        value = value[part]
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        return [str(item) for item in value]
    return []


def get_roles(claims: Mapping[str, Any] | None) -> set[str]:
    """Return normalized roles from common OIDC and Keycloak claim paths."""
    if not claims:
        return set()
    roles: set[str] = set()
    for path in (('roles',), ('groups',), ('realm_access', 'roles')):
        roles.update(role.casefold() for role in _claim_values(claims, path) if role)
    return roles


def require_role(claims: Mapping[str, Any] | None, required: str) -> None:
    """Fail closed unless the normalized role set contains ``required``."""
    if required.casefold() not in get_roles(claims):
        raise AuthorizationError(f"Access denied: missing role '{required}'.")
