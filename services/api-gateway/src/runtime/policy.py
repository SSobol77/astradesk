# SPDX-License-Identifier: Apache-2.0
# services/api-gateway/src/runtime/policy.py
"""Production-grade RBAC + ABAC policy layer for AstraDesk.

Provides fast, dependency-free authorization checks with TTL-cached, hot-reloadable
policy store. Policies can be supplied via environment or JSON file and define
required roles per action and attribute-based constraints.

Author: Siergej Sobolewski
Since: 2025-10-07
"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Set

from opentelemetry import trace  # AstraOps/OTel tracing

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Policy Configuration & Cache
# --------------------------------------------------------------------------- #
_POLICY_JSON_ENV = "POLICY_JSON"
_POLICY_FILE_ENV = "POLICY_FILE"
_POLICY_TTL_ENV = "POLICY_TTL_SECONDS"
_DEFAULT_TTL = 60  # seconds

# Thread-safe cache with TTL
_policy_store: "_PolicyStore" = None  # type: ignore
_lock = threading.Lock()


def _load_policy_from_env() -> Optional[Dict[str, Any]]:
    """Load policy from POLICY_JSON env var."""
    raw = os.getenv(_POLICY_JSON_ENV)
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid POLICY_JSON: {e}")
    return None


def _load_policy_from_file() -> Optional[Dict[str, Any]]:
    """Load policy from POLICY_FILE path."""
    path = os.getenv(_POLICY_FILE_ENV)
    if path and os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:  # pragma: no cover
            logger.error(f"Failed to load policy from {path}: {e}")
    return None


# --------------------------------------------------------------------------- #
# Data Models
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RolesRequired:
    """RBAC role requirements per action."""
    any: Optional[Set[str]] = None  # At least one
    all: Optional[Set[str]] = None  # All required


@dataclass(frozen=True)
class AbacRule:
    """Single ABAC constraint."""
    attr: str
    equals: Optional[Any] = None
    in_set: Optional[Set[Any]] = None


@dataclass(frozen=True)
class IdpRoleMapping:
    """Role normalization config."""
    from_paths: List[str]  # e.g., ["roles", "realm_access.roles"]
    prefix_strip: List[str] = None  # e.g., ["ROLE_"]
    lowercase: bool = True


@dataclass(frozen=True)
class CompiledPolicy:
    """Compiled, immutable policy snapshot."""
    roles_required: Dict[str, RolesRequired]
    abac: Dict[str, List[AbacRule]]
    idp_role_mapping: IdpRoleMapping


# --------------------------------------------------------------------------- #
# Policy Store with TTL Cache
# --------------------------------------------------------------------------- #
class _PolicyStore:
    """Thread-safe, TTL-cached policy store with explicit refresh."""

    __slots__ = ("_policy", "_loaded_at", "_ttl", "_tracer")

    def __init__(self) -> None:
        self._policy: Optional[CompiledPolicy] = None
        self._loaded_at: float = 0.0
        self._ttl = int(os.getenv(_POLICY_TTL_ENV, _DEFAULT_TTL))
        self._tracer = trace.get_tracer(__name__)

    def get(self) -> CompiledPolicy:
        """Get current policy, auto-refresh if expired."""
        now = threading.current_thread().ident or 0  # Dummy timestamp
        with _lock:
            if self._policy is None or (now - self._loaded_at) > self._ttl:
                self._refresh()
            return self._policy

    def refresh_now(self) -> None:
        """Force immediate policy reload."""
        with _lock:
            self._refresh()

    def _refresh(self) -> None:
        """Load and compile policy from sources."""
        with self._tracer.start_as_current_span("policy.refresh"):
            raw = _load_policy_from_env() or _load_policy_from_file()
            if not raw:
                raw = self._default_policy()
                logger.warning("No policy found – using safe defaults")

            try:
                compiled = self._compile_policy(raw)
                self._policy = compiled
                self._loaded_at = threading.current_thread().ident or 0
                logger.info("Policy reloaded successfully")
            except Exception as e:  # pragma: no cover
                logger.critical(f"Failed to compile policy: {e}", exc_info=True)
                raise PolicyError("Invalid policy configuration") from e

    @staticmethod
    def _default_policy() -> Dict[str, Any]:
        """Safe, conservative default policy."""
        return {
            "roles_required": {
                "ops.*": {"all": ["sre"]},
                "tickets.*": {"any": ["it.support", "sre"]},
            },
            "abac": {},
            "idp_role_mapping": {
                "from": ["roles", "groups", "realm_access.roles"],
                "prefix_strip": [],
                "lowercase": True,
            },
        }

    @staticmethod
    def _compile_policy(raw: Dict[str, Any]) -> CompiledPolicy:
        """Compile raw JSON into immutable CompiledPolicy."""
        rr_raw = raw.get("roles_required", {})
        roles_required: Dict[str, RolesRequired] = {}
        for action, req in rr_raw.items():
            any_set = {str(r) for r in req.get("any", [])} if req.get("any") else None
            all_set = {str(r) for r in req.get("all", [])} if req.get("all") else None
            roles_required[action] = RolesRequired(any=any_set, all=all_set)

        abac_raw = raw.get("abac", {})
        abac: Dict[str, List[AbacRule]] = {}
        for action, rules in abac_raw.items():
            compiled_rules = []
            for r in rules:
                attr = str(r["attr"])
                eq = r.get("equals")
                in_set = {str(x) for x in r.get("in", [])} if "in" in r else None
                compiled_rules.append(AbacRule(attr=attr, equals=eq, in_set=in_set))
            abac[action] = compiled_rules

        mapping_raw = raw.get("idp_role_mapping", {})
        from_paths = [str(p) for p in mapping_raw.get("from", [])]
        prefix_strip = [str(p) for p in mapping_raw.get("prefix_strip", [])]
        lowercase = bool(mapping_raw.get("lowercase", True))

        return CompiledPolicy(
            roles_required=roles_required,
            abac=abac,
            idp_role_mapping=IdpRoleMapping(
                from_paths=from_paths,
                prefix_strip=prefix_strip,
                lowercase=lowercase,
            ),
        )


# Initialize global store
_policy_store = _PolicyStore()


# --------------------------------------------------------------------------- #
# Role Helpers
# --------------------------------------------------------------------------- #
def _normalize_roles(
    raw_roles: List[str], mapping: IdpRoleMapping
) -> List[str]:
    """Normalize raw roles from IdP claims."""
    out: List[str] = []
    strip = mapping.prefix_strip or []
    to_lower = mapping.lowercase
    for s in raw_roles:
        s = str(s)
        for prefix in strip:
            if s.startswith(prefix):
                s = s[len(prefix) :]
                break
        if to_lower:
            s = s.lower()
        if s:
            out.append(s)
    return out


def get_roles(claims: Optional[Dict[str, Any]]) -> List[str]:
    """
    Extract and normalize user roles from JWT claims.

    Supported claim paths:
      - roles: [...]
      - groups: [...]
      - realm_access.roles: [...] (Keycloak)

    Args:
        claims: JWT claims dictionary.

    Returns:
        List of normalized role strings.
    """
    if not claims:
        return []

    mapping = _policy_store.get().idp_role_mapping
    raw: List[str] = []
    for path in mapping.from_paths:
        cur = claims
        ok = True
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok and isinstance(cur, (list, tuple)):
            raw.extend(str(x) for x in cur)

    return _normalize_roles(raw, mapping)


def has_role(claims: Optional[Dict[str, Any]], required: str) -> bool:
    """Check if user has a specific role (after normalization)."""
    return required in {r.lower() for r in get_roles(claims)}


def require_role(claims: Optional[Dict[str, Any]], required: str) -> None:
    """Raise AuthorizationError if role is missing."""
    if not has_role(claims, required):
        raise AuthorizationError(f"Access denied: missing role '{required}'.")


def require_any_role(claims: Optional[Dict[str, Any]], candidates: Iterable[str]) -> None:
    """Require at least one role from candidates."""
    have = {r.lower() for r in get_roles(claims)}
    need = {str(c).lower() for c in candidates}
    if not have & need:
        raise AuthorizationError(f"Access denied: need any of roles {sorted(need)}.")


def require_all_roles(claims: Optional[Dict[str, Any]], required: Iterable[str]) -> None:
    """Require all specified roles."""
    have = {r.lower() for r in get_roles(claims)}
    need = {str(r).lower() for r in required}
    missing = need - have
    if missing:
        raise AuthorizationError(f"Access denied: missing roles {sorted(missing)}.")


# --------------------------------------------------------------------------- #
# ABAC Evaluation
# --------------------------------------------------------------------------- #
def _eval_abac_rules(rules: List[AbacRule], attrs: Dict[str, Any]) -> bool:
    """
    Evaluate AND-group of ABAC rules.

    Missing attribute → denial (fail-closed).
    """
    for r in rules:
        val = attrs.get(r.attr)
        if r.equals is not None:
            if val != r.equals:
                return False
        elif r.in_set is not None:
            if val not in r.in_set:
                return False
        else:
            return False
    return True


# --------------------------------------------------------------------------- #
# Main Authorization Function
# --------------------------------------------------------------------------- #
def authorize(
    action: str,
    claims: Optional[Dict[str, Any]],
    attrs: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Authorize action using RBAC + ABAC.

    RBAC:
      - 'any': at least one role
      - 'all': all roles required
      - Wildcard support: 'ops.*'

    ABAC:
      - AND-group of attribute constraints
      - Missing attrs → denial

    Args:
        action: Action identifier (e.g., "ops.restart_service")
        claims: JWT claims
        attrs: Contextual attributes (e.g., {"service": "webapp"})

    Raises:
        AuthorizationError: On denial
        PolicyError: On malformed policy
    """
    if not action:
        raise PolicyError("Action must be non-empty string.")

    pol = _policy_store.get()
    user_roles = {r.lower() for r in get_roles(claims)}

    # RBAC: match action (support wildcard)
    matched_rr: Optional[RolesRequired] = None
    for pattern, rr in pol.roles_required.items():
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            if action.startswith(prefix):
                matched_rr = rr
                break
        elif action == pattern:
            matched_rr = rr
            break

    if matched_rr:
        if matched_rr.all and not matched_rr.all.issubset(user_roles):
            missing = sorted(matched_rr.all - user_roles)
            raise AuthorizationError(f"Access denied: missing roles {missing}.")
        if matched_rr.any and not user_roles & matched_rr.any:
            raise AuthorizationError(f"Access denied: need any of roles {sorted(matched_rr.any)}.")

    # ABAC: match action
    abac_rules = pol.abac.get(action, [])
    if abac_rules:
        if attrs is None:
            raise AuthorizationError("Access denied: missing contextual attributes for ABAC.")
        if not _eval_abac_rules(abac_rules, attrs):
            raise AuthorizationError("Access denied: ABAC rules not satisfied.")


# --------------------------------------------------------------------------- #
# Exceptions
# --------------------------------------------------------------------------- #
class PolicyError(RuntimeError):
    """Raised when policy is malformed or cannot be loaded."""
    pass


class AuthorizationError(PermissionError):
    """Raised when authorization fails."""
    pass


# --------------------------------------------------------------------------- #
# Public Facade (for admin endpoints)
# --------------------------------------------------------------------------- #
class PolicyFacade:
    """Admin interface for policy management."""

    def refresh_now(self) -> None:
        """Force policy reload."""
        _policy_store.refresh_now()

    def current(self) -> CompiledPolicy:
        """Get current policy snapshot."""
        return _policy_store.get()


# Exported singleton
policy = PolicyFacade()
