# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/src/runtime/authz.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for services/api-gateway/src/runtime/authz.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""RBAC authorization choke point for tool execution (ISSUE 016).

This module is the *single* place where a tool invocation is authorized. Both the
LLM-planned path and the deterministic keyword-fallback path funnel every tool
call through :class:`runtime.registry.ToolRegistry.execute`, which delegates the
authorization decision to :func:`authorize_tool` here. Authority is therefore a
property of the invocation, not of the code path that produced it
(``INV-DUAL-PATH``).

Canonical input
---------------
Authorization consumes **normalized roles** only. The OIDC layer
(:mod:`astradesk_core.utils.oidc`) is responsible for turning IdP-specific claim
shapes (``roles``, ``realm_access.roles``, ...) into ``Principal.roles`` via the
``OIDC_ROLES_CLAIM`` configuration. Nothing in this module inspects raw
IdP-specific claims; the only claim-aware helper is :func:`roles_from_claims`, a
thin compatibility adapter that delegates to the existing normalized role helper
and never hardcodes a provider shape.

Fail-closed (``INV-FAIL-CLOSED``)
---------------------------------
- Missing ``side_effect`` metadata -> deny (``RBAC_METADATA_MISSING``).
- ``write``/``execute`` tool with no ``allowed_roles`` -> deny
  (``RBAC_ROLES_NOT_CONFIGURED``); also rejected at registration time so the
  failure surfaces at boot rather than at call time.
- Principal roles do not intersect ``allowed_roles`` -> deny (``RBAC_DENIED``).
- ``write``/``execute`` invoked without an approval/change record -> deny
  (``APPROVAL_REQUIRED``). This is a hard gate (``INV-RBAC-4``): a matching role
  alone is never sufficient for a side-effecting tool. The approval id is read
  from the conservative fields :data:`APPROVAL_FIELDS` in the invocation arguments
  or execution context — no public API contract change.

Denial responses carry a stable reason code and the required role names only.
They never echo the raw token, secrets, credentials, or raw claims.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

__all__ = [
    'APPROVAL_FIELDS',
    'AuthorizationError',
    'RbacDenied',
    'RbacReason',
    'RegistryInvariantError',
    'SideEffect',
    'approval_from_mapping',
    'approval_required_for',
    'authorize_tool',
    'coerce_side_effect',
    'enforce_registration_invariants',
    'normalize_roles',
    'roles_from_claims',
    'validate_tool_metadata',
]

#: Conservative field names accepted as an approval/change-record id, read from
#: the tool invocation arguments or the execution context (ISSUE 016, INV-RBAC-4).
APPROVAL_FIELDS: tuple[str, ...] = ('approval_id', 'change_record', 'change_record_id')


class SideEffect(str, Enum):
    """Declared side-effect class of a tool.

    ``read`` tools observe state and may run without a role restriction. ``write``
    and ``execute`` tools mutate state or trigger actions and therefore require an
    explicit, non-empty ``allowed_roles`` set.
    """

    READ = 'read'
    WRITE = 'write'
    EXECUTE = 'execute'


#: Side-effect classes that require explicit ``allowed_roles`` and stricter gating.
SIDE_EFFECTING: frozenset[SideEffect] = frozenset({SideEffect.WRITE, SideEffect.EXECUTE})


class RbacReason(str, Enum):
    """Stable, audit-friendly denial reason codes (non-leaking)."""

    METADATA_MISSING = 'RBAC_METADATA_MISSING'
    ROLES_NOT_CONFIGURED = 'RBAC_ROLES_NOT_CONFIGURED'
    ROLE_DENIED = 'RBAC_DENIED'
    APPROVAL_REQUIRED = 'APPROVAL_REQUIRED'


class AuthorizationError(PermissionError):
    """Base authorization failure with a stable public exception type."""


class RbacDenied(AuthorizationError):
    """Raised when the RBAC choke point denies a tool invocation.

    The message and attributes expose only the tool name, a stable reason code,
    and the required role names (policy configuration, not secrets). They never
    contain the raw token, credentials, or raw claims.
    """

    def __init__(
        self,
        reason: RbacReason,
        tool: str,
        *,
        needed_roles: Iterable[str] = (),
    ) -> None:
        self.reason = reason
        self.tool = tool
        self.needed_roles: tuple[str, ...] = tuple(sorted({str(r) for r in needed_roles}))
        message = f"Access denied for tool '{tool}' [{reason.value}]"
        if self.needed_roles:
            message += f'; requires any of {list(self.needed_roles)}'
        super().__init__(message)


class RegistryInvariantError(RuntimeError):
    """Raised at startup when a registered tool violates the RBAC metadata invariant.

    Surfacing this aborts process start (fail-closed): a side-effecting tool that
    reaches the registry without role metadata must be caught at boot, not at the
    first unauthorized call.
    """


def coerce_side_effect(value: SideEffect | str | None) -> SideEffect:
    """Coerce a registration input into a :class:`SideEffect`.

    Raises:
        ValueError: if ``value`` is missing (``None``) or is not one of
            ``read``/``write``/``execute``. Missing metadata is never silently
            treated as safe.
    """
    if value is None:
        raise ValueError("side_effect is required: declare one of 'read', 'write', 'execute'.")
    if isinstance(value, SideEffect):
        return value
    try:
        return SideEffect(str(value).strip().lower())
    except ValueError as exc:
        raise ValueError(
            f'invalid side_effect {value!r}; expected one of read/write/execute.'
        ) from exc


def normalize_roles(roles: Iterable[str] | None) -> frozenset[str]:
    """Return a case-folded role set from an already-normalized roles iterable."""
    if not roles:
        return frozenset()
    return frozenset(r.casefold() for r in roles if r)


def roles_from_claims(claims: Mapping[str, Any] | None) -> frozenset[str]:
    """Compatibility adapter: derive normalized roles from verified claims.

    Used only when an explicit normalized roles list is not supplied to the choke
    point. It delegates to the existing normalized role helper
    (:func:`runtime.policy.get_roles`) and never hardcodes a provider-specific
    claim shape. RBAC logic proper (:func:`authorize_tool`) operates on the
    resulting role set, not on the claims.
    """
    if not claims:
        return frozenset()
    # Imported lazily to keep the authorization core free of policy-store imports.
    from runtime.policy import get_roles

    return normalize_roles(get_roles(dict(claims)))


def validate_tool_metadata(
    tool: str,
    side_effect: SideEffect,
    allowed_roles: Iterable[str],
) -> None:
    """Registration-time invariant: a side-effecting tool must declare roles.

    Raises:
        ValueError: if a ``write``/``execute`` tool has an empty ``allowed_roles``.
    """
    if side_effect in SIDE_EFFECTING and not set(allowed_roles):
        raise ValueError(
            f"tool '{tool}' is side-effecting ({side_effect.value}) and must "
            'declare a non-empty allowed_roles set.'
        )


def approval_required_for(side_effect: SideEffect | None, requires_approval: bool) -> bool:
    """The effective approval rule for ISSUE 016 (``INV-RBAC-4``).

    A ``write``/``execute`` invocation *always* requires an approval/change record,
    independent of the per-tool ``requires_approval`` flag. The flag may additionally
    force approval on a ``read`` tool, but it can never relax a side-effecting one.
    """
    return side_effect in SIDE_EFFECTING or bool(requires_approval)


def approval_from_mapping(source: Mapping[str, Any] | None) -> str | None:
    """Extract an approval/change-record id from invocation args or context.

    Accepts the conservative field names :data:`APPROVAL_FIELDS`
    (``approval_id`` / ``change_record`` / ``change_record_id``). Returns the first
    present, non-empty value, or ``None``. This reads only well-known scalar fields;
    it never inspects IdP-specific claim shapes.
    """
    if not source:
        return None
    for field_name in APPROVAL_FIELDS:
        value = source.get(field_name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def authorize_tool(
    *,
    tool: str,
    side_effect: SideEffect | None,
    allowed_roles: Iterable[str],
    roles: Iterable[str],
    requires_approval: bool = False,
    approval_id: str | None = None,
) -> None:
    """Authorize a single tool invocation from normalized roles. Fail-closed.

    Enforcement order (each step denies before the tool runs):

    1. Missing ``side_effect`` metadata -> ``RBAC_METADATA_MISSING``.
    2. ``write``/``execute`` without configured roles -> ``RBAC_ROLES_NOT_CONFIGURED``.
    3. Principal roles do not satisfy ``allowed_roles`` -> ``RBAC_DENIED``.
    4. ``write``/``execute`` (``INV-RBAC-4``) without an approval/change record, or
       any tool flagged ``requires_approval`` -> ``APPROVAL_REQUIRED``. A matching
       role alone is therefore never sufficient for a side-effecting tool.

    Args:
        tool: Tool name (for the denial reason; not a secret).
        side_effect: Declared side-effect class, or ``None`` if metadata is absent.
        allowed_roles: Roles permitted to invoke the tool (policy configuration).
        roles: The principal's normalized roles.
        requires_approval: Per-tool flag; may force approval on a ``read`` tool but
            cannot relax the side-effecting rule.
        approval_id: The approval/change record id, if supplied by the caller.

    Raises:
        RbacDenied: with a stable :class:`RbacReason` whenever the invocation is
            not authorized. The underlying tool function must not run.
    """
    if side_effect is None:
        raise RbacDenied(RbacReason.METADATA_MISSING, tool)

    allowed = normalize_roles(allowed_roles)
    principal_roles = normalize_roles(roles)

    if side_effect in SIDE_EFFECTING and not allowed:
        raise RbacDenied(RbacReason.ROLES_NOT_CONFIGURED, tool)

    if allowed and not (principal_roles & allowed):
        raise RbacDenied(RbacReason.ROLE_DENIED, tool, needed_roles=allowed)

    if approval_required_for(side_effect, requires_approval) and not (
        approval_id and str(approval_id).strip()
    ):
        raise RbacDenied(RbacReason.APPROVAL_REQUIRED, tool, needed_roles=allowed)


def enforce_registration_invariants(
    tools: Iterable[tuple[str, SideEffect | None, Iterable[str], bool]],
) -> None:
    """Boot-time invariant sweep over registered tools (``INV-RBAC``). Fail-closed.

    Args:
        tools: An iterable of ``(name, side_effect, allowed_roles, requires_approval)``
            quadruples.

    Raises:
        RegistryInvariantError: if any tool lacks ``side_effect`` metadata, any
            ``write``/``execute`` tool lacks ``allowed_roles``, or any
            ``write``/``execute`` tool is registered in a way that bypasses approval
            enforcement (``requires_approval`` not set). Aggregated so the operator
            sees every offending tool at once.
    """
    offenders: list[str] = []
    for name, side_effect, allowed_roles, requires_approval in tools:
        if side_effect is None:
            offenders.append(f'{name}: missing side_effect metadata')
            continue
        if side_effect in SIDE_EFFECTING and not set(allowed_roles):
            offenders.append(f'{name}: side-effecting ({side_effect.value}) without allowed_roles')
        if side_effect in SIDE_EFFECTING and not requires_approval:
            offenders.append(
                f'{name}: side-effecting ({side_effect.value}) bypasses approval enforcement'
            )
    if offenders:
        raise RegistryInvariantError(
            'RBAC metadata invariant violated for: ' + '; '.join(sorted(offenders))
        )
