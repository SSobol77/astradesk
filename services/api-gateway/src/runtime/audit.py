# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/src/runtime/audit.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for services/api-gateway/src/runtime/audit.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Durable audit trail for side-effecting tool execution (ISSUE 019).

This module defines the typed audit event schema and the writer abstraction
used by :meth:`runtime.registry.ToolRegistry.execute` — the single RBAC choke
point (ISSUE 016) — to record every attempted ``write``/``execute`` tool call.
Audit emission is a property of the invocation, not of the code path that
produced it: the same call in ``ToolRegistry.execute`` is reached by both the
LLM-planned and keyword-fallback paths (``INV-DUAL-PATH``), so wiring it here
makes every side-effect attempt auditable regardless of caller.

Target invariants (ISSUE 019)
------------------------------
- ``INV-AUDIT-1``: every attempted ``write``/``execute`` tool call emits a
  durable audit event.
- ``INV-AUDIT-2``: events are emitted for both allowed and denied attempts.
- ``INV-AUDIT-3``: events contain only redacted/safe fields — no raw user
  input, secrets, tokens, credentials, private keys, or raw claims. Argument
  previews are built through the shared NEW-04 redaction boundary
  (:mod:`astradesk_core.redaction`), never a second, incompatible redactor.
- ``INV-AUDIT-4``: events carry correlation data for incident review
  (``event_id``, ``timestamp``, ``trace_id``, ``request_id``, ``tenant_id``,
  ``principal_id``, normalized ``roles``, ``tool``, ``side_effect``,
  ``decision``, denial ``reason``, ``approval_id``, redacted args preview).
- ``INV-AUDIT-5``: audit failure fails closed for ``write``/``execute`` tools
  — see :class:`AuditWriteError` and the choke-point wiring in
  :mod:`runtime.registry`.
- ``INV-AUDIT-6``: audit is never attempted for ``read`` tools, so a broken
  writer can never block a read (enforced at the call site, not here).
- ``INV-AUDIT-7``: events are deterministic for tests — ``event_id``/clock are
  injectable via :class:`ToolRegistry`'s constructor parameters.

:class:`JetStreamAuditWriter` (ISSUE 039) additionally targets the
JetStream-specific invariants in
``docs/roadmap/issues/ISSUES_019_durable_audit.md`` (``INV-AUD-1``..
``INV-AUD-5``, a distinct numbering scheme from ``INV-AUDIT-*`` above, from
the same source document): ack-after-durable-write, a durable consumer,
bounded-retry-then-DLQ, idempotent writes, and a producer that never blocks
on downstream sink persistence. The producer-side half (this module) and the
consumer-side half (:mod:`services.auditor.main`) are documented together
where each invariant is actually enforced.

Durability strategy
--------------------
:class:`AuditWriter` is a minimal structural protocol (``async def
write(event)``). Three concrete implementations are provided:

- :class:`InMemoryAuditWriter` — deterministic, dependency-free; the default
  writer so existing callers/tests keep working unchanged, and useful for
  introspection in tests.
- :class:`FileAuditWriter` — append-only JSON-Lines sink that survives process
  restarts on the same host; the safe local/production durable mode requested
  by the issue when no external broker is configured.
- :class:`JetStreamAuditWriter` — publishes each event to a NATS JetStream
  stream and awaits the broker's own publish acknowledgement (confirmation
  the event is durably stored in the stream) before returning (ISSUE 039).
  This is the producer-side half of ack-after-durable-write; the choke
  point above already fails the side effect closed if ``write()`` raises,
  so this writer only has to raise correctly on failure. The *consumer*-side
  half (a durable JetStream pull consumer that acks to the broker only
  after its own sink write succeeds, with retry/DLQ/idempotency) is
  :mod:`services.auditor.main`, tracked by the same issue and
  ``docs/roadmap/issues/ISSUES_019_durable_audit.md``. Real NATS/JetStream
  connection setup (``nats.connect()``, ``add_stream``) deliberately lives
  outside this class, in ``gateway.main``'s startup wiring, so
  :class:`JetStreamAuditWriter` itself stays a pure, dependency-free unit
  under test — it only needs an already-connected JetStream publisher.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from astradesk_core.redaction import redact_mapping, safe_preview

from runtime.authz import APPROVAL_FIELDS, SideEffect

__all__ = [
    'AuditDecision',
    'AuditEvent',
    'AuditWriteError',
    'AuditWriter',
    'ClockFn',
    'JetStreamAuditWriter',
    'JetStreamPublishError',
    'JetStreamPublisher',
    'EventIdFn',
    'FileAuditWriter',
    'InMemoryAuditWriter',
    'build_args_preview',
    'default_clock',
    'default_event_id',
    'principal_from_claims',
    'tenant_from_claims',
]

logger = logging.getLogger(__name__)

# Bounds for the redacted argument preview (``INV-AUDIT-3``): a preview, never
# the full payload.
_ARGS_PREVIEW_MAX_KEYS = 20
_ARGS_PREVIEW_MAX_CHARS = 200
_PRINCIPAL_PREVIEW_MAX_CHARS = 100

# Meta kwargs carrying raw claims / approval identifiers. These are never
# echoed into the argument preview as a container; the audit layer instead
# surfaces safe, dedicated fields (``principal_id``, ``tenant_id``,
# ``approval_id``) derived from them.
_AUDIT_META_KEYS: frozenset[str] = frozenset({'claims', *APPROVAL_FIELDS})


class AuditDecision(str, Enum):
    """Final outcome recorded on an audit event."""

    ALLOWED = 'allowed'
    DENIED = 'denied'
    ERROR = 'error'


class AuditWriteError(RuntimeError):
    """Fail-closed signal: a durable audit record could not be written.

    Raised by the ``ToolRegistry.execute`` choke point for ``write``/
    ``execute`` tools when the configured :class:`AuditWriter` raises
    (``INV-AUDIT-5``). The underlying tool function must not run once this is
    raised. The message intentionally carries only the tool name and a stable
    reason code — never the writer's raw exception text, which could
    theoretically echo the event payload back.
    """

    code = 'AUDIT_SINK_UNAVAILABLE'

    def __init__(self, tool: str) -> None:
        self.tool = tool
        super().__init__(f"{self.code}: audit sink unavailable for tool '{tool}'")


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Durable, structured record of one attempted tool invocation.

    Every field is either a stable identifier, a policy-configuration value
    (tool name, roles, reason code), or a value that has already passed
    through the shared redaction boundary. Nothing here may carry raw user
    input, secrets, tokens, credentials, private keys, or raw claims
    (``INV-AUDIT-3``).
    """

    event_id: str
    timestamp: datetime
    tool: str
    side_effect: SideEffect
    decision: AuditDecision
    roles: tuple[str, ...] = ()
    trace_id: str | None = None
    request_id: str | None = None
    tenant_id: str | None = None
    principal_id: str | None = None
    reason: str | None = None
    approval_id: str | None = None
    args_preview: dict[str, Any] = field(default_factory=dict)
    error_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation (stable key order)."""
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'tool': self.tool,
            'side_effect': self.side_effect.value,
            'decision': self.decision.value,
            'roles': list(self.roles),
            'trace_id': self.trace_id,
            'request_id': self.request_id,
            'tenant_id': self.tenant_id,
            'principal_id': self.principal_id,
            'reason': self.reason,
            'approval_id': self.approval_id,
            'args_preview': self.args_preview,
            'error_type': self.error_type,
        }


@runtime_checkable
class AuditWriter(Protocol):
    """Structural contract for a durable(-compatible) audit sink."""

    async def write(self, event: AuditEvent) -> None:
        """Persist ``event``. Must raise on failure — never swallow silently."""
        ...


class InMemoryAuditWriter:
    """Deterministic, dependency-free writer; the default for ``ToolRegistry``.

    Never raises, so it never changes existing RBAC (#016) behavior for
    callers that do not configure an explicit durable sink. Recorded events
    are readable via :attr:`events`, which makes it the natural writer for
    unit tests as well.
    """

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []
        self._lock = asyncio.Lock()

    async def write(self, event: AuditEvent) -> None:
        async with self._lock:
            self.events.append(event)


class FileAuditWriter:
    """Append-only JSON-Lines audit sink that survives process restarts.

    The safe, explicit local/production durable mode (``INV-LOCAL-MODE-EXPLICIT``
    counterpart for audit): a developer or operator opts in by pointing
    ``AUDIT_LOG_PATH`` at a writable file. Each event is one JSON line, written
    with the shared redaction boundary already applied by the caller
    (:class:`AuditEvent` fields are safe by construction).
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def write(self, event: AuditEvent) -> None:
        line = json.dumps(
            event.to_dict(), ensure_ascii=False, separators=(',', ':'), sort_keys=True
        )
        async with self._lock:
            await asyncio.to_thread(self._append_line, line)

    def _append_line(self, line: str) -> None:
        with self._path.open('a', encoding='utf-8') as fh:
            fh.write(line + '\n')


@runtime_checkable
class JetStreamPublisher(Protocol):
    """Structural contract for an already-connected JetStream publish client.

    Matches ``nats.js.client.JetStreamContext.publish``'s call shape closely
    enough that a real ``nc.jetstream()`` object satisfies this Protocol
    directly, while tests can inject a deterministic fake with no NATS
    connection at all. Deliberately excludes connection setup (``connect``,
    ``add_stream``) — that lives in the async factory that constructs
    :class:`JetStreamAuditWriter`, not in the writer itself.
    """

    async def publish(
        self,
        subject: str,
        payload: bytes = b'',
        timeout: float | None = None,
        stream: str | None = None,
        headers: dict[Any, Any] | None = None,
    ) -> Any:
        """Publish and return once the broker acks durable storage; raise otherwise."""
        ...


class JetStreamPublishError(RuntimeError):
    """Raised when neither the primary subject nor the DLQ could be confirmed.

    Carries whether a DLQ publish was attempted and whether it succeeded, for
    logging/metrics — never the event payload itself (``INV-AUDIT-3``).
    """

    code = 'JETSTREAM_PUBLISH_FAILED'

    def __init__(self, subject: str, *, dlq_attempted: bool, dlq_succeeded: bool | None) -> None:
        self.subject = subject
        self.dlq_attempted = dlq_attempted
        self.dlq_succeeded = dlq_succeeded
        if not dlq_attempted:
            dlq_detail = 'not attempted'
        else:
            dlq_detail = 'succeeded' if dlq_succeeded else 'failed'
        super().__init__(
            f"{self.code}: could not durably publish to '{subject}' (dlq: {dlq_detail})"
        )


def _encode_audit_event(event: AuditEvent) -> bytes:
    """Serialize an already-redacted :class:`AuditEvent` for JetStream publish."""
    return json.dumps(
        event.to_dict(), ensure_ascii=False, separators=(',', ':'), sort_keys=True
    ).encode('utf-8')


class JetStreamAuditWriter:
    """Durable, JetStream-backed :class:`AuditWriter` (ISSUE 039).

    ``write()`` publishes the event to ``subject`` and awaits the broker's
    own publish acknowledgement — confirmation the event is now durably
    stored in the JetStream stream itself, independent of whether any
    consumer (e.g. :mod:`services.auditor.main`) has processed it yet. This
    is the producer-side half of ack-after-durable-write (``INV-AUD-1``):
    ``ToolRegistry``'s existing choke point already fails the side effect
    closed whenever ``write()`` raises (``INV-AUDIT-5``), so no change to
    the choke point itself is needed — this class only has to raise
    correctly on failure.

    Bounded, not indefinite: each publish attempt is wrapped in
    ``asyncio.wait_for(..., timeout=publish_timeout)``, retried up to
    ``publish_retries`` additional times. If every primary attempt fails,
    one best-effort publish to ``dlq_subject`` is attempted so the event is
    not silently discarded outright — but per the acceptance contract's
    default fail-closed behavior for side-effect success paths, a
    successful DLQ write does **not** change the outcome: ``write()``
    always raises :class:`JetStreamPublishError` when the primary publish
    could not be confirmed, regardless of whether the DLQ fallback
    succeeded. The DLQ exists so an operator can inspect/replay the event
    later, not to unlock the side effect that was waiting on this call.
    """

    def __init__(
        self,
        js: JetStreamPublisher,
        *,
        subject: str,
        dlq_subject: str,
        publish_timeout: float = 2.0,
        publish_retries: int = 2,
    ) -> None:
        self._js = js
        self._subject = subject
        self._dlq_subject = dlq_subject
        self._publish_timeout = publish_timeout
        self._publish_retries = max(0, publish_retries)

    async def write(self, event: AuditEvent) -> None:
        payload = _encode_audit_event(event)
        headers = {'Nats-Msg-Id': event.event_id}

        last_exc: BaseException | None = None
        for attempt in range(self._publish_retries + 1):
            try:
                await asyncio.wait_for(
                    self._js.publish(self._subject, payload, headers=headers),
                    timeout=self._publish_timeout,
                )
                return
            except Exception as exc:  # broker error, timeout, or connection loss
                last_exc = exc
                logger.warning(
                    "JetStream publish attempt %d/%d failed for subject '%s': %s",
                    attempt + 1,
                    self._publish_retries + 1,
                    self._subject,
                    type(exc).__name__,
                )

        dlq_succeeded: bool | None = None
        # A distinct dedup id is required here: JetStream's `Nats-Msg-Id`
        # deduplication window is scoped to the whole stream, and the
        # primary subject and the DLQ subject share one stream. If the
        # primary publish above actually landed despite the client-side
        # timeout/error (e.g. an ack that was lost in transit), reusing the
        # bare event id would make the broker silently drop this DLQ
        # publish as a duplicate — the exact silent-loss failure mode the
        # DLQ exists to prevent.
        dlq_headers = {'Nats-Msg-Id': f'dlq:{event.event_id}'}
        try:
            await asyncio.wait_for(
                self._js.publish(self._dlq_subject, payload, headers=dlq_headers),
                timeout=self._publish_timeout,
            )
            dlq_succeeded = True
        except Exception as dlq_exc:
            dlq_succeeded = False
            logger.error(
                "JetStream DLQ publish also failed for subject '%s': %s",
                self._dlq_subject,
                type(dlq_exc).__name__,
            )

        raise JetStreamPublishError(
            self._subject, dlq_attempted=True, dlq_succeeded=dlq_succeeded
        ) from last_exc


EventIdFn = Callable[[], str]
ClockFn = Callable[[], datetime]


def default_event_id() -> str:
    """Generate a unique, non-guessable audit event id."""
    return f'audit-{uuid.uuid4()}'


def default_clock() -> datetime:
    """Return the current UTC time (timezone-aware, per ``INV-AUDIT-7``)."""
    return datetime.now(UTC)


def _bound(value: object) -> object:
    """Recursively bound a redacted value for a safe, size-limited preview."""
    if isinstance(value, str):
        if len(value) <= _ARGS_PREVIEW_MAX_CHARS:
            return value
        return value[:_ARGS_PREVIEW_MAX_CHARS] + '…'
    if isinstance(value, Mapping):
        return {k: _bound(v) for k, v in list(value.items())[:_ARGS_PREVIEW_MAX_KEYS]}
    if isinstance(value, list | tuple):
        return [_bound(v) for v in list(value)[:_ARGS_PREVIEW_MAX_KEYS]]
    if value is None or isinstance(value, bool | int | float):
        return value
    return _bound(str(value))


def build_args_preview(kwargs: Mapping[str, Any]) -> dict[str, Any]:
    """Build a bounded, redacted preview of tool invocation arguments.

    Meta kwargs (``claims`` and the approval-id field names) are dropped
    entirely rather than redacted-in-place: they are raw-claim containers, not
    business arguments, and are surfaced instead through the dedicated
    ``principal_id``/``tenant_id``/``approval_id`` fields on
    :class:`AuditEvent`. Everything else is passed through the shared NEW-04
    redaction boundary and then size-bounded. Fail-closed on internal error:
    never the raw arguments.
    """
    business = {k: v for k, v in kwargs.items() if k not in _AUDIT_META_KEYS}
    try:
        redacted = redact_mapping(business)
    except Exception:  # pragma: no cover - redact_mapping already fails closed
        return {'_redaction': 'REDACTION_FAILED'}

    bounded: dict[str, Any] = {}
    for i, (key, value) in enumerate(redacted.items()):
        if i >= _ARGS_PREVIEW_MAX_KEYS:
            bounded['_truncated'] = True
            break
        bounded[key] = _bound(value)
    return bounded


def principal_from_claims(claims: Mapping[str, Any] | None) -> str | None:
    """Derive a safe subject identifier from verified claims, if present.

    Reads the standard OIDC ``sub`` claim only and passes it through the
    shared redaction/bounding helper — defense in depth in case an IdP ever
    puts an email-shaped value in ``sub``. Never inspects other claim shapes.
    """
    if not claims:
        return None
    sub = claims.get('sub')
    if not sub:
        return None
    preview = safe_preview(str(sub), _PRINCIPAL_PREVIEW_MAX_CHARS)
    return preview or None


def tenant_from_claims(claims: Mapping[str, Any] | None) -> str | None:
    """Derive a safe tenant identifier from verified claims, if present."""
    if not claims:
        return None
    tenant = claims.get('tenant') or claims.get('tenant_id')
    if not tenant:
        return None
    preview = safe_preview(str(tenant), _PRINCIPAL_PREVIEW_MAX_CHARS)
    return preview or None
