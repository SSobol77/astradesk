# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/src/runtime/registry.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for services/api-gateway/src/runtime/registry.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Thread-safe runtime Tool Registry for AstraDesk agents. Provides deterministic
    registration/lookup/execution of domain tools (actions) and is the single RBAC
    choke point (ISSUE 016), with metadata (side_effect, allowed_roles, schema,
    version, description) and dynamic Domain Pack loading via entry points
    (`astradesk.pack`).


Overview
--------
- Metadata-first design: each tool is described by `ToolInfo` (name, side_effect,
  allowed_roles, requires_approval, version, description, schema), enabling
  auditability and UI introspection.
- Fail-closed RBAC choke point: `execute()` authorizes every invocation through
  `runtime.authz.authorize_tool` from *normalized roles* (never raw IdP claims),
  so the LLM-planned and keyword-fallback paths enforce identically
  (`INV-DUAL-PATH`). `side_effect` is mandatory at registration; a `write`/
  `execute` tool without `allowed_roles` is rejected at registration (fail fast).
- Unified execution: async callables awaited directly; sync callables executed
  via `asyncio.to_thread`, with exceptions logged and re-raised.
- Domain Packs: discoverable through `importlib.metadata.entry_points(group="astradesk.pack")`;
  each pack exposes `register()` to self-register tools/agents/flows.

Responsibilities
----------------
- Registration API:
  * `register(name, fn, *, side_effect, description, version, allowed_roles,
    requires_approval, schema, override)`
  * `unregister(name)`
- Read/Query API:
  * `get(name)`, `get_info(name)`, `exists(name)`, `names()`, `infos()`
- Execution:
  * `execute(name, *, roles=None, approval_id=None, **kwargs)` — authorizes via
    the shared RBAC choke point (fail-closed), strips meta-kwargs (e.g., `claims`)
    when not accepted by the callable’s signature, then runs async/sync.
- Domain Packs:
  * `load_domain_packs()` — discovers and initializes packs; errors of individual
    packs are logged but do not block startup.

Design principles
-----------------
- Minimal coupling: registry concerns only — metadata, RBAC check, execution.
  Orchestration lives in agents and higher layers.
- Deterministic and auditable: tool names validated by regex `^[A-Za-z0-9._-]{1,128}$`;
  no hidden mutation during execution.
- Concurrency-aware: mutations guarded by `asyncio.Lock`; read paths are lock-free.
- Explicit error taxonomy: `ToolRegistryError`, `ToolRegistrationError`,
  `ToolNotFoundError`, `AuthorizationError` (from policy or local fallback).

Security & safety
-----------------
- RBAC deny-by-default when `allowed_roles` is set and intersection is empty.
- Avoid leaking `claims` into business callables that do not declare such a parameter.
- Log exceptions with context; re-raise to avoid masking failures.
- Keep schemas minimal and non-executable; avoid embedding secrets/PII in metadata.

Performance
-----------
- O(1) lookups for registered tools; registration/deregistration serialized by lock.
- Sync execution offloaded to threads (`asyncio.to_thread`) to keep event loop responsive.
- Domain Pack discovery performed once on startup; failures are isolated and logged.

Usage (example)
---------------
>>> registry = ToolRegistry()
>>> async def create_ticket(title: str, body: str) -> dict: ...
>>> await registry.register(
...     "tickets.create", create_ticket,
...     description="Create a support ticket",
...     allowed_roles={"it.support", "sre"},
... )
>>> result = await registry.execute(
...     "tickets.create", title="VPN issue", body="Cannot connect", claims={"roles": ["sre"]}
... )

Notes
-----
- Prefer narrow `allowed_roles` on sensitive tools; keep schemas descriptive but lean.
- When evolving tool signatures, rely on `get_info(name).signature` for introspection.
- For pack authors: expose a callable/class via entry point returning an object
  with `register()` that registers tools into the registry.

Notes (PL)
----------
- Rejestr narzędzi jest „miękko” zintegrowany z `runtime.policy`; gdy polityka nie jest
  dostępna, używany jest bezpieczny fallback (parsowanie ról z `claims`).
- Rejestr nie importuje warstw UI ani transportu — tylko runtime.
- Błędy pojedynczych Domain Packów nie blokują startu (rejestrowane w logach).
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from typing import Any

__all__ = [
    'AuditWriteError',
    'AuthorizationError',
    'RbacDenied',
    'SideEffect',
    'ToolInfo',
    'ToolNotFoundError',
    'ToolRegistrationError',
    'ToolRegistry',
    'ToolRegistryError',
    'load_domain_packs',
]


from runtime.audit import (
    AuditDecision,
    AuditEvent,
    AuditWriteError,
    AuditWriter,
    ClockFn,
    EventIdFn,
    InMemoryAuditWriter,
    build_args_preview,
    default_clock,
    default_event_id,
    principal_from_claims,
    tenant_from_claims,
)
from runtime.authz import (
    APPROVAL_FIELDS,
    AuthorizationError,
    RbacDenied,
    SideEffect,
    approval_from_mapping,
    authorize_tool,
    coerce_side_effect,
    normalize_roles,
    roles_from_claims,
    validate_tool_metadata,
)
from runtime.authz import (
    SIDE_EFFECTING as _SIDE_EFFECTING,
)

# Logowanie
_logger = logging.getLogger(__name__)

# Utils
_TOOL_NAME_RE = re.compile(r'^[A-Za-z0-9._-]{1,128}$')


def load_domain_packs(registry: ToolRegistry) -> list[tuple[str, Any]]:
    """Ładuje i rejestruje Domain Packs poprzez entry points (group='astradesk.pack').

    Zabezpieczenia:
    - Zgodność z różnymi wersjami API importlib.metadata.entry_points.
    - Błąd pojedynczego packa nie wstrzymuje startu systemu (logujemy i lecimy dalej).

    Args:
        registry: The ToolRegistry instance to register tools with.

    Returns:
        list[tuple[str, Any]]: lista (nazwa_entry_pointu, obiekt_packa)
    """
    discovered = entry_points()
    selected: Iterable[Any]
    if hasattr(discovered, 'select'):
        selected = discovered.select(group='astradesk.pack')
    else:  # pragma: no cover - compatibility with Python <= 3.10
        selected = (ep for ep in discovered if getattr(ep, 'group', None) == 'astradesk.pack')

    loaded: list[tuple[str, Any]] = []
    for ep in selected:
        try:
            factory = ep.load()  # type: ignore
            pack = factory()  # preferowana fabryka: klasa/closure zwracająca obiekt packa
            # Konwencja: pack.register() rejestruje agentów/tools/flows w Intent Graph/registry
            pack.register(registry)
            loaded.append((getattr(ep, 'name', '<unknown>'), pack))
            _logger.info("Loaded domain pack '%s'", getattr(ep, 'name', '<unknown>'))
        except Exception as exc:  # nie blokuj całego systemu przez pojedynczy pack
            _logger.exception(
                "Failed to load/register domain pack '%s': %s",
                getattr(ep, 'name', '<unknown>'),
                exc,
            )
    return loaded


# Wyjątki specyficzne dla rejestru narzędzi
class ToolRegistryError(Exception):
    """Baza wyjątków rejestru narzędzi."""


class ToolRegistrationError(ToolRegistryError):
    """Błąd podczas rejestracji narzędzia."""


class ToolNotFoundError(ToolRegistryError, KeyError):
    """Żądane narzędzie nie istnieje."""


# Model metadanych pojedynczego narzędzia
ToolCallable = Callable[..., Any]


@dataclass
class ToolInfo:
    """Metadane zarejestrowanego narzędzia runtime.

    ``side_effect`` and ``allowed_roles`` are the source of truth for the RBAC
    choke point (ISSUE 016). ``side_effect`` is mandatory at registration; a
    ``write``/``execute`` tool must also carry a non-empty ``allowed_roles``.
    """

    name: str
    fn: ToolCallable
    side_effect: SideEffect
    description: str = ''
    version: str = '1.0.0'
    allowed_roles: set[str] = field(default_factory=set)
    requires_approval: bool = False
    schema: dict[str, Any] = field(default_factory=dict)

    # Cache techniczny - nie eksponujemy w repr, ustawiany podczas register()
    signature: inspect.Signature | None = field(default=None, repr=False)
    is_coroutine: bool = field(default=False, repr=False)


# Rejestr narzędzi
class ToolRegistry:
    """Prosty, bezpieczny wątkowo rejestr narzędzi dla runtime."""

    def __init__(
        self,
        *,
        audit_writer: AuditWriter | None = None,
        audit_event_id: EventIdFn = default_event_id,
        audit_clock: ClockFn = default_clock,
    ) -> None:
        """Inicjalizacja klasa.

        Args:
            audit_writer: Durable(-compatible) sink for side-effect audit
                events (ISSUE 019). Defaults to :class:`InMemoryAuditWriter`,
                which never raises, so existing callers/tests that do not
                configure a sink keep working unchanged. Production wiring
                should inject a durable writer (e.g. ``FileAuditWriter``).
            audit_event_id: Injectable event-id generator (``INV-AUDIT-7``);
                override in tests for deterministic ids.
            audit_clock: Injectable UTC clock (``INV-AUDIT-7``); override in
                tests for deterministic timestamps.

        """
        self._tools: dict[str, ToolInfo] = {}
        self._lock = asyncio.Lock()
        self._audit_writer: AuditWriter = audit_writer or InMemoryAuditWriter()
        self._audit_event_id = audit_event_id
        self._audit_clock = audit_clock

    # Mutacje
    async def register(
        self,
        name: str,
        fn: ToolCallable,
        *,
        side_effect: SideEffect | str | None = None,
        description: str = '',
        version: str = '1.0.0',
        allowed_roles: set[str] | None = None,
        requires_approval: bool = False,
        schema: dict[str, Any] | None = None,
        override: bool = False,
    ) -> None:
        """Rejestruje narzędzie; użyj override=True aby zastąpić istniejące.

        RBAC metadata (ISSUE 016):
            ``side_effect`` is mandatory and must be one of ``read``/``write``/
            ``execute``. A ``write``/``execute`` tool must declare a non-empty
            ``allowed_roles`` set, and approval enforcement is forced on for it
            (``requires_approval`` is set by invariant regardless of the argument)
            so a side-effecting tool can never be registered in a way that bypasses
            the approval/change-record gate (``INV-RBAC-4``). All invariants are
            enforced here so a mis-declared tool fails fast at boot, not at the
            first unauthorized call (``INV-FAIL-CLOSED``).

        Raises:
            ToolRegistrationError: niepoprawna nazwa/funkcja, brakujące lub
                niepoprawne metadane RBAC, lub konflikt bez override.

        """
        if not name or not _TOOL_NAME_RE.fullmatch(name):
            raise ToolRegistrationError(
                "Invalid tool name. Allowed chars: letters, digits, '.', '_' and '-'; max 128."
            )
        if not callable(fn):
            raise ToolRegistrationError('fn must be callable')

        roles = set(allowed_roles or set())
        try:
            effect = coerce_side_effect(side_effect)
            validate_tool_metadata(name, effect, roles)
        except ValueError as exc:
            raise ToolRegistrationError(str(exc)) from exc

        # Side-effecting tools always require an approval/change record (INV-RBAC-4);
        # the flag can only ever be strengthened, never relaxed, at registration.
        effective_requires_approval = bool(requires_approval) or effect in _SIDE_EFFECTING

        info = ToolInfo(
            name=name,
            fn=fn,
            side_effect=effect,
            description=description or '',
            version=version or '1.0.0',
            allowed_roles=roles,
            requires_approval=effective_requires_approval,
            schema=dict(schema or {}),
        )

        # Cache sygnatury i coroutine-ness (tu, zamiast robić to w hot-path execute()).
        try:
            info.signature = inspect.signature(fn)
        except Exception:
            info.signature = None
        info.is_coroutine = inspect.iscoroutinefunction(fn)

        async with self._lock:
            if name in self._tools and not override:
                raise ToolRegistrationError(
                    f"Tool '{name}' already exists (use override=True to replace)."
                )
            self._tools[name] = info
            _logger.info("Registered tool '%s' (override=%s)", name, override)

    async def unregister(self, name: str) -> None:
        """Wyrejestrowuje narzędzie.

        Raises:
            ToolNotFoundError: gdy narzędzie nie istnieje.

        """
        async with self._lock:
            try:
                del self._tools[name]
            except KeyError as e:
                _logger.error("Unregister failed: '%s' not found", name)
                raise ToolNotFoundError(f"Tool '{name}' not found") from e
            else:
                _logger.info("Unregistered tool '%s'", name)

    # Odczyt/enumeracja
    def get(self, name: str) -> ToolCallable:
        """Zwraca funkcję narzędzia (bez metadanych)."""
        try:
            return self._tools[name].fn
        except KeyError as e:
            _logger.error("get('%s'): not found", name)
            raise ToolNotFoundError(f"Tool '{name}' not found") from e

    def get_info(self, name: str) -> ToolInfo:
        """Zwraca pełne metadane narzędzia."""
        try:
            return self._tools[name]
        except KeyError as e:
            _logger.error("get_info('%s'): not found", name)
            raise ToolNotFoundError(f"Tool '{name}' not found") from e

    def names(self) -> list[str]:
        """Lista nazw zarejestrowanych narzędzi."""
        return list(self._tools.keys())

    def infos(self) -> list[ToolInfo]:
        """Snapshot of all registered tool metadata (for boot-time invariants)."""
        return list(self._tools.values())

    def exists(self, name: str) -> bool:
        """Czy narzędzie jest zarejestrowane?"""
        return name in self._tools

    async def _emit_audit(
        self,
        *,
        tool: str,
        side_effect: SideEffect,
        decision: AuditDecision,
        roles: tuple[str, ...],
        trace_id: str | None,
        request_id: str | None,
        tenant_id: str | None,
        principal_id: str | None,
        approval_id: str | None,
        args_preview: dict[str, Any],
        reason: str | None = None,
        error_type: str | None = None,
        fail_closed: bool,
    ) -> None:
        """Durably record one audit event (ISSUE 019); fail-closed when asked.

        ``fail_closed`` gates whether a writer failure is escalated into
        :class:`AuditWriteError` (``INV-AUDIT-5``, ``write``/``execute`` only)
        or merely logged and swallowed (best-effort, used for the post-execution
        error record so a tool's real exception is never masked by an audit
        write problem).
        """
        event = AuditEvent(
            event_id=self._audit_event_id(),
            timestamp=self._audit_clock(),
            tool=tool,
            side_effect=side_effect,
            decision=decision,
            roles=roles,
            trace_id=trace_id,
            request_id=request_id,
            tenant_id=tenant_id,
            principal_id=principal_id,
            reason=reason,
            approval_id=approval_id,
            args_preview=args_preview,
            error_type=error_type,
        )
        try:
            await self._audit_writer.write(event)
        except Exception as exc:
            _logger.critical(
                "Audit write failed: tool='%s' decision=%s writer=%s: %s",
                tool,
                decision.value,
                type(self._audit_writer).__name__,
                type(exc).__name__,
            )
            if fail_closed:
                raise AuditWriteError(tool) from exc

    @staticmethod
    def _strip_meta_kwargs(kwargs: dict[str, Any], sig: inspect.Signature | None) -> dict[str, Any]:
        """Strip ``claims``/approval meta keys the callable does not declare."""
        if sig is None:
            return kwargs
        meta_keys = [k for k in ('claims', *APPROVAL_FIELDS) if k in kwargs]
        to_strip = [k for k in meta_keys if k not in sig.parameters]
        if not to_strip:
            return kwargs
        kwargs = dict(kwargs)  # płytka kopia
        for key in to_strip:
            kwargs.pop(key, None)
        return kwargs

    async def _invoke_tool(
        self,
        name: str,
        info: ToolInfo,
        kwargs: dict[str, Any],
        *,
        is_side_effecting: bool,
        emit: Callable[..., Any],
    ) -> Any:
        """Run the tool's callable (sync/async) and audit an ``ERROR`` outcome.

        A writer failure here is best-effort (``fail_closed=False``): the
        tool's own exception is what the caller needs to see, so an audit
        write problem is logged but never masks it.
        """
        try:
            if info.is_coroutine:
                return await info.fn(**kwargs)
            return await asyncio.to_thread(info.fn, **kwargs)
        except Exception as exc:  # logujemy, nie maskujemy
            _logger.exception("Tool '%s' failed: %s", name, exc)
            if is_side_effecting:
                await emit(AuditDecision.ERROR, error_type=type(exc).__name__, fail_closed=False)
            raise

    # Wykonanie
    async def execute(
        self,
        name: str,
        *,
        roles: Iterable[str] | None = None,
        approval_id: str | None = None,
        trace_id: str | None = None,
        request_id: str | None = None,
        tenant_id: str | None = None,
        principal_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Uruchamia narzędzie — jedyny punkt egzekwowania RBAC (ISSUE 016)
        i durable audytu dla narzędzi side-effecting (ISSUE 019).

        This is the single authorization choke point that both the LLM-planned
        and keyword-fallback paths traverse (``INV-DUAL-PATH``). The decision is
        delegated to :func:`runtime.authz.authorize_tool` and made from
        *normalized roles only*. For ``write``/``execute`` tools, every attempt
        — denied, allowed, or erroring — is durably recorded through the
        configured :class:`~runtime.audit.AuditWriter` before the caller
        observes the outcome (``INV-AUDIT-1``/``INV-AUDIT-2``). ``read`` tools
        never touch the audit writer, so a broken sink can never block a read
        (``INV-AUDIT-6``).

        Args:
            roles: The principal's normalized roles. When ``None`` (legacy
                callers) they are derived from ``claims`` via the compatibility
                adapter; RBAC never inspects raw IdP claim shapes directly.
            approval_id: Optional explicit approval/change-record id. When not
                given, one is resolved from the invocation arguments / context via
                the accepted fields (``approval_id``/``change_record``/
                ``change_record_id``). ``write``/``execute`` tools are denied
                (``APPROVAL_REQUIRED``) before execution if none is present
                (``INV-RBAC-4``).
            trace_id: Optional OTel/request trace id, recorded on the audit
                event for incident correlation when supplied (``INV-AUDIT-4``).
            request_id: Optional request correlation id, recorded on the audit
                event when supplied.
            tenant_id: Optional explicit tenant id. When not given, derived
                from ``claims`` (``tenant``/``tenant_id``) if present.
            principal_id: Optional explicit safe subject id. When not given,
                derived from ``claims['sub']`` if present.

        Sync/Async:
            - Funkcje asynchroniczne awaitujemy bezpośrednio.
            - Funkcje synchroniczne odpalamy w wątku (`asyncio.to_thread`).

        Raises:
            RbacDenied: gdy wywołanie nie jest autoryzowane (przed wykonaniem fn).
            ToolNotFoundError: gdy narzędzie nie istnieje.
            AuditWriteError: gdy audyt narzędzia side-effecting nie mógł zostać
                trwale zapisany (``write``/``execute`` fail-closed, ISSUE 019).
            Dowolny wyjątek biznesowy narzędzia (przepuszczamy, ale logujemy).

        """
        info = self.get_info(name)
        is_side_effecting = info.side_effect in _SIDE_EFFECTING

        # 1 RBAC choke point (shared by every execution path; fail-closed).
        effective_roles = roles_from_claims(kwargs.get('claims')) if roles is None else roles
        # Approval/change-record id may arrive explicitly or in the invocation
        # arguments/context; the explicit value takes precedence.
        effective_approval_id = approval_id or approval_from_mapping(kwargs)

        # Audit correlation data (ISSUE 019) is captured once, from the
        # original invocation kwargs, *before* any RBAC decision or meta-kwarg
        # stripping — so DENIED/ALLOWED/ERROR events for the same call always
        # report identical roles/principal/tenant/args_preview regardless of
        # what the tool's own signature does with ``claims``. Only computed
        # for side-effecting tools; the read-tool path never touches this.
        audit_fields: dict[str, Any] = {}
        if is_side_effecting:
            claims = kwargs.get('claims')
            audit_fields = {
                'roles': tuple(sorted(normalize_roles(effective_roles))),
                'tenant_id': tenant_id or tenant_from_claims(claims),
                'principal_id': principal_id or principal_from_claims(claims),
                'args_preview': build_args_preview(kwargs),
            }

        async def _emit(decision: AuditDecision, *, fail_closed: bool, **overrides: Any) -> None:
            await self._emit_audit(
                tool=name,
                side_effect=info.side_effect,
                decision=decision,
                trace_id=trace_id,
                request_id=request_id,
                approval_id=effective_approval_id,
                fail_closed=fail_closed,
                **audit_fields,
                **overrides,
            )

        try:
            authorize_tool(
                tool=name,
                side_effect=info.side_effect,
                allowed_roles=info.allowed_roles,
                roles=effective_roles,
                requires_approval=info.requires_approval,
                approval_id=effective_approval_id,
            )
        except RbacDenied as exc:
            _logger.warning(
                "RBAC deny: tool='%s' reason=%s need_any=%s",
                name,
                exc.reason.value,
                list(exc.needed_roles),
            )
            if is_side_effecting:
                await _emit(AuditDecision.DENIED, reason=exc.reason.value, fail_closed=True)
            raise

        # 2 Czyszczenie kwargs: meta keys ('claims' and the approval fields) are
        #    stripped when the callable does not declare them, so they never leak
        #    into business tool signatures.
        kwargs = self._strip_meta_kwargs(kwargs, info.signature)

        # 2b Fail-closed pre-execution audit for authorized side-effecting
        #    attempts (INV-AUDIT-5): the durable ALLOWED record is written
        #    *before* the tool runs. If the writer fails, the tool function is
        #    never invoked and AuditWriteError propagates instead.
        if is_side_effecting:
            await _emit(AuditDecision.ALLOWED, fail_closed=True)

        # 3 Uruchomienie narzędzia obsługa sync/async
        return await self._invoke_tool(
            name, info, kwargs, is_side_effecting=is_side_effecting, emit=_emit
        )
