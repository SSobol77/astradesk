"""
Simplified policy engine with caching semantics mirroring the tests.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set


class PolicyError(Exception):
    pass


class AuthorizationError(Exception):
    pass


@dataclass(frozen=True)
class PolicySnapshot:
    roles_required: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)
    abac: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    idp_role_mapping: Dict[str, Any] = field(default_factory=lambda: {"from": ["roles"], "prefix_strip": [], "lowercase": True})


_DEFAULT_POLICY = PolicySnapshot()
_POLICY_ENV = ""


class PolicyStore:
    def __init__(self) -> None:
        self._compiled: PolicySnapshot = _DEFAULT_POLICY

    def refresh_now(self) -> None:
        global _POLICY_ENV
        if not _POLICY_ENV:
            self._compiled = _DEFAULT_POLICY
            return
        data = json.loads(_POLICY_ENV)
        roles_required = data.get("roles_required", {})
        abac = data.get("abac", {})
        idp_map = data.get("idp_role_mapping", {})
        self._compiled = PolicySnapshot(roles_required=roles_required, abac=abac, idp_role_mapping=idp_map)

    def current(self) -> PolicySnapshot:
        return self._compiled


policy = PolicyStore()
policy.refresh_now()


def _extract_from_claims(data: Any, path: str) -> Iterable[str]:
    if not data:
        return []
    parts = path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            current = None
        if current is None:
            return []
    if isinstance(current, list):
        return [str(item) for item in current]
    if isinstance(current, str):
        return [current]
    return []


def get_roles(claims: Optional[Dict[str, Any]]) -> Set[str]:
    mapping = policy.current().idp_role_mapping
    sources = mapping.get("from", ["roles"])
    prefixes = mapping.get("prefix_strip", [])
    lowercase = mapping.get("lowercase", False)

    result: Set[str] = set()
    for source in sources:
        for role in _extract_from_claims(claims or {}, source):
            cleaned = role
            for prefix in prefixes:
                if cleaned.startswith(prefix):
                    cleaned = cleaned[len(prefix):]
            if lowercase:
                cleaned = cleaned.lower()
            result.add(cleaned)
    return result


def has_role(claims: Optional[Dict[str, Any]], role: str) -> bool:
    return role.lower() in {r.lower() for r in get_roles(claims)}


def require_role(claims: Optional[Dict[str, Any]], role: str) -> None:
    if not has_role(claims, role):
        raise AuthorizationError(f"Role '{role}' required.")


def require_any_role(claims: Optional[Dict[str, Any]], roles: Iterable[str]) -> None:
    available = {r.lower() for r in get_roles(claims)}
    if not any(role.lower() in available for role in roles):
        raise AuthorizationError("Missing any of the required roles.")


def require_all_roles(claims: Optional[Dict[str, Any]], roles: Iterable[str]) -> None:
    available = {r.lower() for r in get_roles(claims)}
    if not all(role.lower() in available for role in roles):
        raise AuthorizationError("Missing required roles.")


def _check_rbac(action: str, claims: Optional[Dict[str, Any]], snapshot: PolicySnapshot) -> None:
    gate = snapshot.roles_required.get(action)
    if gate is None:
        for pattern, candidate in snapshot.roles_required.items():
            if pattern.endswith("*") and action.startswith(pattern[:-1]):
                gate = candidate
                break
    if not gate:
        return
    available = {r.lower() for r in get_roles(claims)}
    required_any = [role.lower() for role in gate.get("any", [])]
    required_all = [role.lower() for role in gate.get("all", [])]

    if required_any and not any(role in available for role in required_any):
        raise AuthorizationError("RBAC any-of requirement failed.")
    if required_all and not all(role in available for role in required_all):
        raise AuthorizationError("RBAC all-of requirement failed.")


def _check_abac(action: str, attrs: Optional[Dict[str, Any]], snapshot: PolicySnapshot) -> None:
    constraints = snapshot.abac.get(action)
    if not constraints:
        return
    attrs = attrs or {}
    for rule in constraints:
        attr = rule.get("attr")
        if attr is None:
            continue
        if attr not in attrs:
            raise AuthorizationError("ABAC attribute missing.")
        value = attrs[attr]
        if "equals" in rule and value != rule["equals"]:
            raise AuthorizationError("ABAC equals requirement failed.")
        if "in" in rule:
            allowed = rule["in"]
            if value not in allowed:
                raise AuthorizationError("ABAC membership requirement failed.")


def authorize(action: str, claims: Optional[Dict[str, Any]], attrs: Optional[Dict[str, Any]] = None) -> None:
    if not action:
        raise PolicyError("Action must be provided.")
    snapshot = policy.current()
    _check_rbac(action, claims, snapshot)
    _check_abac(action, attrs, snapshot)


__all__ = [
    "AuthorizationError",
    "PolicyError",
    "authorize",
    "get_roles",
    "has_role",
    "policy",
    "require_role",
    "require_any_role",
    "require_all_roles",
]
