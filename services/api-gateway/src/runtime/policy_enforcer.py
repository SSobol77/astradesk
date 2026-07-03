# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/src/runtime/policy_enforcer.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for services/api-gateway/src/runtime/policy_enforcer.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Deployable, fail-closed contextual policy enforcement (ISSUE 028).

This module adds a second, independent governance gate to the single tool
invocation choke point already established by RBAC (ISSUE 016,
:mod:`runtime.authz`) and durable audit (ISSUE 019, :mod:`runtime.audit`) in
:meth:`runtime.registry.ToolRegistry.execute`. RBAC answers *who may execute
this class of tool*; this module answers *does external policy (OPA/Rego)
additionally permit this specific attempt right now*. Neither replaces the
other, and neither is duplicated here (``INV-DUAL-PATH`` composition, not
redesign).

Target invariants (ISSUE 028)
------------------------------
- ``INV-POLICY-1``: every attempted ``write``/``execute`` tool call passes
  through :class:`PolicyEnforcer.evaluate`.
- ``INV-POLICY-2``: the LLM-planned and keyword-fallback paths reach the same
  enforcement point identically, because both call
  :meth:`runtime.registry.ToolRegistry.execute` (``INV-DUAL-PATH``).
- ``INV-POLICY-3``: a denial (``PolicyDecision.allow is False``) raises
  :class:`PolicyDenied` before the tool function runs.
- ``INV-POLICY-4``/``INV-POLICY-5``: on a deployed tier (``production``,
  ``prod``, ``staging``, ``stage`` — ``ENVIRONMENT`` unset defaults to
  ``production``, mirroring :func:`astradesk_core.utils.oidc.build_verifier_from_env`
  and ``gateway.main._resolve_audit_writer``), missing/invalid OPA
  configuration aborts startup (:class:`PolicyConfigError`), and an OPA
  request that fails/times out/returns an ambiguous decision at call time
  denies rather than allows.
- ``INV-POLICY-6``: ``read`` tools are only policy-checked when a tool is
  explicitly registered with ``policy_governed=True``
  (:data:`runtime.registry.ToolInfo.policy_governed`); by default a broken
  policy dependency can never block a plain read.
- ``INV-POLICY-8``: the request built for the enforcer
  (:class:`PolicyRequest`) carries only normalized/redacted/bounded fields —
  the same safe fields already computed for the ISSUE 019 audit event, reused
  here rather than re-derived from raw kwargs/claims.
- ``INV-POLICY-9``: roles/subject are the already-normalized values RBAC uses
  (:mod:`runtime.authz`), never raw IdP claim shapes.
- ``INV-POLICY-10``: :class:`LocalPolicyEnforcer` is deterministic and
  dependency-free; :class:`OpaHttpPolicyEnforcer` accepts an injectable HTTP
  client so unit tests never require a real OPA server.
- ``INV-LOCAL-MODE-EXPLICIT``: the permissive local mode is reachable only via
  an explicit, non-default ``POLICY_MODE=local`` (or the safe non-deployed-tier
  default) and is refused on a deployed tier.

Design
------
:class:`PolicyEnforcer` is a minimal structural protocol (``async def
evaluate(request) -> PolicyDecision``), mirroring :class:`runtime.audit.AuditWriter`.
Two implementations are provided:

- :class:`LocalPolicyEnforcer` — deterministic allow-all. The safe default for
  :class:`~runtime.registry.ToolRegistry` (so existing callers/tests that do
  not configure an explicit enforcer keep working unchanged, exactly like
  :class:`runtime.audit.InMemoryAuditWriter`) and the explicit mode for
  ``development``/``dev``/``test``/``local``/``ci`` tiers.
- :class:`OpaHttpPolicyEnforcer` — calls a real OPA server's Data API
  (``POST {OPA_URL}/v1/data/{policy_path}``) over HTTP. Fail-closed on any
  transport error, timeout, non-2xx response, or a decision that is not
  unambiguously boolean.

:func:`build_policy_enforcer_from_env` selects between them at startup,
fail-closed, mirroring :func:`astradesk_core.utils.oidc.build_verifier_from_env`.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import httpx

if TYPE_CHECKING:
    from runtime.authz import SideEffect

__all__ = [
    'LocalPolicyEnforcer',
    'OpaHttpPolicyEnforcer',
    'PolicyConfigError',
    'PolicyDecision',
    'PolicyDenied',
    'PolicyEnforcer',
    'PolicyReason',
    'PolicyRequest',
    'build_policy_enforcer_from_env',
]

logger = logging.getLogger(__name__)

# Tiers on which the permissive local policy mode must never be reachable —
# the same values used by astradesk_core.utils.oidc._DEPLOYED_TIERS and
# gateway.main._AUDIT_DEPLOYED_TIERS, kept local rather than importing either
# module's private constant for an unrelated concern.
_POLICY_DEPLOYED_TIERS = frozenset({'production', 'prod', 'staging', 'stage'})

_DEFAULT_POLICY_PATH = 'astradesk/tools/allow'
_DEFAULT_TIMEOUT_SECONDS = 2.0


class PolicyReason(str, Enum):
    """Stable, audit-friendly reason codes for a policy denial."""

    DENIED = 'POLICY_DENIED'
    UNAVAILABLE = 'POLICY_UNAVAILABLE'


class PolicyConfigError(RuntimeError):
    """Raised at startup when policy configuration is missing/invalid.

    Surfacing this aborts process start (fail-closed), mirroring
    :class:`astradesk_core.utils.oidc.AuthConfigError` and
    ``gateway.main.AuditConfigError``. It must never be caught and downgraded
    to a permissive default.
    """


class PolicyDenied(PermissionError):
    """Raised when the policy choke point denies a tool invocation.

    Carries only the tool name and a stable reason code (either a synthetic
    :class:`PolicyReason` or a short reason string returned by the enforcer
    itself, e.g. a Rego ``deny`` message) — never raw payload, claims, or
    secrets.
    """

    def __init__(self, reason: str, tool: str) -> None:
        self.reason = reason
        self.tool = tool
        super().__init__(f"Access denied for tool '{tool}' [{reason}]")


@dataclass(frozen=True, slots=True)
class PolicyRequest:
    """Bounded, redacted input to a policy decision (``INV-POLICY-8``/``-9``).

    Every field is either a stable identifier, normalized role data, or a
    value that already passed through the shared NEW-04 redaction/bounding
    boundary via :func:`runtime.audit.build_args_preview`. Nothing here may
    carry a raw token, Authorization header, secret, private key, raw PII, or
    an unbounded argument payload.
    """

    tool: str
    side_effect: SideEffect
    roles: tuple[str, ...] = ()
    principal_id: str | None = None
    tenant_id: str | None = None
    trace_id: str | None = None
    request_id: str | None = None
    approval_id: str | None = None
    args_preview: dict[str, Any] = field(default_factory=dict)

    def to_input(self) -> dict[str, Any]:
        """Render as the ``input`` document sent to an external policy engine."""
        return {
            'tool': {'name': self.tool, 'side_effect': self.side_effect.value},
            'auth': {'roles': list(self.roles), 'principal_id': self.principal_id},
            'context': {
                'tenant_id': self.tenant_id,
                'trace_id': self.trace_id,
                'request_id': self.request_id,
                'approval_id': self.approval_id,
            },
            'args_preview': self.args_preview,
        }


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    """The outcome of one policy evaluation."""

    allow: bool
    reason: str | None = None


@runtime_checkable
class PolicyEnforcer(Protocol):
    """Structural contract for the ISSUE 028 policy choke point."""

    async def evaluate(self, request: PolicyRequest) -> PolicyDecision:
        """Decide ``request``. Must not raise for an ordinary deny — return
        ``PolicyDecision(allow=False, ...)`` instead. Raising is reserved for
        truly unexpected errors, which the caller treats as fail-closed."""
        ...


class LocalPolicyEnforcer:
    """Deterministic, dependency-free enforcer: always allows.

    The explicit, non-default local/dev/test/ci mode (``INV-LOCAL-MODE-EXPLICIT``)
    and the safe default for :class:`~runtime.registry.ToolRegistry` when no
    enforcer is configured. It never weakens RBAC, approval, or audit — those
    remain fully enforced at the same choke point regardless of the policy
    decision (``INV-POLICY-*`` compose with, never replace, ISSUE 016/019).
    """

    async def evaluate(self, request: PolicyRequest) -> PolicyDecision:
        return PolicyDecision(allow=True)


class OpaHttpPolicyEnforcer:
    """Fail-closed HTTP enforcer backed by a real OPA server's Data API.

    Queries ``POST {base_url}/v1/data/{policy_path}`` with ``{"input": ...}``
    and expects a decision shaped as ``{"result": {"allow": bool, ...}}`` or
    ``{"result": bool}``. Any transport error, timeout, non-2xx response, or a
    ``result`` that is not unambiguously boolean is treated as an unavailable
    decision and denies (``INV-OPA-1``/``INV-FAIL-CLOSED``) — this method
    never raises for those cases, so the registry choke point cannot
    accidentally fail open on an uncaught exception.

    An HTTP client can be injected (``client``) so unit tests exercise this
    class against ``httpx.MockTransport`` — no real OPA server is required in
    CI (``INV-POLICY-10``).
    """

    def __init__(
        self,
        *,
        base_url: str,
        policy_path: str = _DEFAULT_POLICY_PATH,
        timeout: float = _DEFAULT_TIMEOUT_SECONDS,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._url = f'{base_url.rstrip("/")}/v1/data/{policy_path.strip("/").replace(".", "/")}'
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def evaluate(self, request: PolicyRequest) -> PolicyDecision:
        try:
            response = await self._client.post(self._url, json={'input': request.to_input()})
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.warning(
                "OPA policy check unavailable for tool='%s': %s",
                request.tool,
                type(exc).__name__,
            )
            return PolicyDecision(allow=False, reason=PolicyReason.UNAVAILABLE.value)

        result = data.get('result') if isinstance(data, dict) else None
        allow = result.get('allow') if isinstance(result, dict) else result
        if not isinstance(allow, bool):
            logger.warning(
                "OPA policy decision ambiguous for tool='%s': result=%r", request.tool, result
            )
            return PolicyDecision(allow=False, reason=PolicyReason.UNAVAILABLE.value)

        reason = None
        if not allow and isinstance(result, dict):
            raw_reason = result.get('reason')
            reason = str(raw_reason)[:200] if raw_reason else None
        return PolicyDecision(
            allow=allow, reason=reason or (None if allow else PolicyReason.DENIED.value)
        )

    async def aclose(self) -> None:
        """Release the owned HTTP client (no-op for an injected client)."""
        if self._owns_client:
            await self._client.aclose()


def _opa_enforcer_from_env() -> OpaHttpPolicyEnforcer:
    """Build the OPA enforcer from environment, fail-closed on missing config."""
    base_url = os.getenv('OPA_URL', '').strip()
    if not base_url:
        raise PolicyConfigError(
            'OPA_URL is required to build the OPA policy enforcer on this tier.'
        )
    policy_path = os.getenv('OPA_POLICY_PATH', '').strip() or _DEFAULT_POLICY_PATH
    try:
        timeout = float(os.getenv('OPA_TIMEOUT_SECONDS', str(_DEFAULT_TIMEOUT_SECONDS)))
    except ValueError as exc:
        raise PolicyConfigError('OPA_TIMEOUT_SECONDS must be a number') from exc
    return OpaHttpPolicyEnforcer(base_url=base_url, policy_path=policy_path, timeout=timeout)


def build_policy_enforcer_from_env() -> PolicyEnforcer:
    """Construct the ISSUE 028 policy enforcer from environment, fail-closed.

    ``POLICY_MODE`` (optional):
      - ``local``: explicit local mode. Refused (:class:`PolicyConfigError`) on
        a deployed tier (``INV-LOCAL-MODE-EXPLICIT``).
      - ``opa``: builds :class:`OpaHttpPolicyEnforcer` from ``OPA_URL`` (and
        optional ``OPA_POLICY_PATH``/``OPA_TIMEOUT_SECONDS``), regardless of
        tier. Missing/invalid config aborts startup.
      - unset: safe default — deployed tiers require OPA (same fail-closed
        default as :func:`astradesk_core.utils.oidc.build_verifier_from_env`
        and ``gateway.main._resolve_audit_writer``: ``ENVIRONMENT`` unset
        behaves like ``production``); non-deployed tiers get
        :class:`LocalPolicyEnforcer`.
      - any other value: aborts startup.
    """
    mode = os.getenv('POLICY_MODE', '').strip().lower()
    environment = os.getenv('ENVIRONMENT', 'production').strip().lower()
    deployed = environment in _POLICY_DEPLOYED_TIERS

    if mode == 'local':
        if deployed:
            raise PolicyConfigError(f"POLICY_MODE=local is forbidden on tier '{environment}'")
        return LocalPolicyEnforcer()

    if mode == 'opa':
        return _opa_enforcer_from_env()

    if mode:
        raise PolicyConfigError(f'unknown POLICY_MODE: {mode!r}')

    if deployed:
        return _opa_enforcer_from_env()
    return LocalPolicyEnforcer()
