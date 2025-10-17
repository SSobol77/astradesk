# SPDX-License-Identifier: Apache-2.0
"""Tests for src/runtime/policy.py (AstraDesk RBAC+ABAC).

Covers:
- Policy source via POLICY_JSON (no file I/O), TTL cache, refresh_now().
- Role extraction from heterogeneous IdPs: roles / groups / realm_access.roles.
- Normalization: prefix_strip, lowercase.
- RBAC gates: any / all, helpers: require_role/any/all, has_role.
- ABAC: equals / in, AND semantics, missing attrs => denial (fail-closed).
- Safe defaults & errors: empty action -> PolicyError.

Notes:
- The module reads env into module-level vars at import; tests set `policy._POLICY_ENV`
  directly and call `policy.policy.refresh_now()` to recompile.

"""

from __future__ import annotations

import json
import typing as t

import pytest

import src.runtime.policy as policy_mod  # for accessing module-level _POLICY_ENV/_policy_store  # type: ignore
from src.runtime.policy import (  # type: ignore
    AuthorizationError,
    PolicyError,
    authorize,
    get_roles,
    has_role,
    policy,
    require_all_roles,
    require_any_role,
    require_role,
)

# --- Test utilities ---

@pytest.fixture(autouse=True)
def _restore_policy_env_after_test():
    """Ensure we leave module-level POLICY env in a clean state after each test."""
    old_env = policy_mod._POLICY_ENV
    try:
        yield
    finally:
        # Reset to empty/default and clear cache
        policy_mod._POLICY_ENV = ""
        policy.refresh_now()


def _set_inline_policy(policy_dict: dict) -> None:
    """Set inline JSON policy and force recompilation."""
    policy_mod._POLICY_ENV = json.dumps(policy_dict)
    policy.refresh_now()


def _allow_everything_policy() -> dict:
    """Convenient policy that allows any action without RBAC/ABAC (for isolated tests)."""
    return {
        "roles_required": {},
        "abac": {},
        "idp_role_mapping": {"from": ["roles", "groups", "realm_access.roles"], "prefix_strip": [], "lowercase": True},
    }


# --- ole extraction & normalization ---

def test_get_roles_from_roles_groups_realm_access_with_prefix_strip_and_lowercase():
    pol = _allow_everything_policy()
    pol["idp_role_mapping"]["prefix_strip"] = ["ROLE_"]
    pol["idp_role_mapping"]["lowercase"] = True
    _set_inline_policy(pol)

    claims = {
        "roles": ["ROLE_SRE", "ROLE_IT.SUPPORT"],
        "groups": ["ROLE_Admins"],
        "realm_access": {"roles": ["ROLE_readOnly", "ROLE_DEVOPS"]},
    }

    roles = get_roles(claims)
    # All should be lowercased and prefix-stripped
    assert "sre" in roles
    assert "it.support" in roles
    assert "admins" in roles
    assert "readonly" in roles
    assert "devops" in roles


def test_has_and_require_role_helpers():
    _set_inline_policy(_allow_everything_policy())
    claims = {"roles": ["SRE"]}

    # Normalization default: lowercase=True
    assert has_role(claims, "sre")
    require_role(claims, "sre")  # should not raise

    with pytest.raises(AuthorizationError):
        require_role(claims, "it.support")


def test_require_any_and_all_roles():
    _set_inline_policy(_allow_everything_policy())
    claims = {"roles": ["sre", "ops"]}

    # any-of
    require_any_role(claims, ["it.support", "sre"])  # ok
    with pytest.raises(AuthorizationError):
        require_any_role(claims, ["it.support", "finance"])

    # all-of
    require_all_roles(claims, ["sre", "ops"])  # ok
    with pytest.raises(AuthorizationError):
        require_all_roles(claims, ["sre", "ops", "admin"])


# --- RBAC ---

def test_authorize_rbac_any_pass_and_fail():
    pol = {
        "roles_required": {
            "tickets.create": {"any": ["it.support", "sre"]},
        },
        "abac": {},
        "idp_role_mapping": {"from": ["roles"], "prefix_strip": [], "lowercase": True},
    }
    _set_inline_policy(pol)

    authorize("tickets.create", {"roles": ["sre"]})  # pass

    with pytest.raises(AuthorizationError):
        authorize("tickets.create", {"roles": ["guest"]})


def test_authorize_rbac_all_pass_and_fail():
    pol = {
        "roles_required": {
            # JSON must use arrays, not sets
            "ops.restart_service": {"all": ["sre", "ops"]},
        },
        "abac": {},
        "idp_role_mapping": {"from": ["roles"], "prefix_strip": [], "lowercase": True},
    }
    _set_inline_policy(pol)

    authorize("ops.restart_service", {"roles": ["SRE", "OPS"]})  # pass (lowercased)

    with pytest.raises(AuthorizationError):
        authorize("ops.restart_service", {"roles": ["sre"]})


def test_authorize_rbac_any_and_all_combined():
    pol = {
        "roles_required": {
            "ops.deploy": {"all": ["devops"], "any": ["release.manager", "sre"]},
        },
        "abac": {},
        "idp_role_mapping": {"from": ["roles"], "prefix_strip": [], "lowercase": True},
    }
    _set_inline_policy(pol)

    # must have devops AND at least one from (release.manager, sre)
    authorize("ops.deploy", {"roles": ["devops", "sre"]})  # pass

    with pytest.raises(AuthorizationError):
        authorize("ops.deploy", {"roles": ["sre"]})  # missing 'devops'

    with pytest.raises(AuthorizationError):
        authorize("ops.deploy", {"roles": ["devops"]})  # missing any-of

   
# ABAC   


def test_authorize_abac_equals_pass_and_fail():
    pol = {
        "roles_required": {},  # no RBAC gate
        "abac": {
            "ops.restart_service": [
                {"attr": "service", "equals": "webapp"},
                {"attr": "env", "in": ["dev", "staging", "prod"]},
            ]
        },
        "idp_role_mapping": {"from": ["roles"], "prefix_strip": [], "lowercase": True},
    }
    _set_inline_policy(pol)

    # pass: matches 'equals' and 'in'
    authorize("ops.restart_service", claims={}, attrs={"service": "webapp", "env": "prod"})

    # fail: equals mismatch
    with pytest.raises(AuthorizationError):
        authorize("ops.restart_service", claims={}, attrs={"service": "payments", "env": "prod"})

    # fail: missing attrs -> fail-closed
    with pytest.raises(AuthorizationError):
        authorize("ops.restart_service", claims={}, attrs={"service": "webapp"})


def test_authorize_abac_in_only_pass_and_fail():
    pol = {
        "roles_required": {},
        "abac": {
            "tickets.read": [
                {"attr": "owner", "in": ["alice", "bob", "carol"]},
            ]
        },
        "idp_role_mapping": {"from": ["roles"], "prefix_strip": [], "lowercase": True},
    }
    _set_inline_policy(pol)

    authorize("tickets.read", claims=None, attrs={"owner": "bob"})  # pass

    with pytest.raises(AuthorizationError):
        authorize("tickets.read", claims=None, attrs={"owner": "dave"})

   
# Safe defaults, errors, and cache behavior   


def test_authorize_empty_action_raises_policyerror():
    _set_inline_policy(_allow_everything_policy())
    with pytest.raises(PolicyError):
        authorize("", claims={}, attrs={})


def test_policy_cache_and_refresh_now_changes_effect(monkeypatch):
    """
    Show that compiled policy is cached until refresh_now() is called.
    - First policy: deny unless role 'sre' is present.
    - Second policy: allow with 'it.support' (no sre).
    """
    pol1 = {
        "roles_required": {"tickets.create": {"any": ["sre"]}},
        "abac": {},
        "idp_role_mapping": {"from": ["roles"], "prefix_strip": [], "lowercase": True},
    }
    _set_inline_policy(pol1)

    # With only it.support -> should FAIL under pol1
    with pytest.raises(AuthorizationError):
        authorize("tickets.create", {"roles": ["it.support"]})

    # Change inline policy (module-level string), but do NOT refresh yet
    pol2 = {
        "roles_required": {"tickets.create": {"any": ["it.support"]}},
        "abac": {},
        "idp_role_mapping": {"from": ["roles"], "prefix_strip": [], "lowercase": True},
    }
    policy_mod._POLICY_ENV = json.dumps(pol2)

    # Still using cached compiled policy -> still FAILS
    with pytest.raises(AuthorizationError):
        authorize("tickets.create", {"roles": ["it.support"]})

    # Now force reload -> should PASS
    policy.refresh_now()
    authorize("tickets.create", {"roles": ["it.support"]})


def test_policy_current_returns_compiled_snapshot():
    pol = {
        "roles_required": {"ops.restart_service": {"all": ["sre"]}},
        "abac": {
            "ops.restart_service": [{"attr": "service", "in": ["webapp", "payments"]}],
        },
        "idp_role_mapping": {"from": ["roles"], "prefix_strip": ["ROLE_"], "lowercase": True},
    }
    _set_inline_policy(pol)

    snap = policy.current()
    assert "ops.restart_service" in snap.roles_required
    assert "ops.restart_service" in snap.abac
    assert snap.idp_role_mapping["lowercase"] is True
