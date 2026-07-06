# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/tests/runtime/test_audit_startup.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Verifies AstraDesk behavior for the associated component.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Startup-time audit sink selection tests (ISSUE 019/039).

Verifies that ``gateway.main._resolve_audit_writer`` — called from
``lifespan`` before any external resource (DB/Redis) is touched — fails
closed on a deployed tier without a durable sink, mirrors the OIDC
fail-closed default (``ENVIRONMENT`` unset => ``'production'``), still
allows the non-durable in-process writer for local/dev/test tiers, and
(ISSUE 039) selects the JetStream writer when explicitly configured,
failing closed on any connection/stream-setup problem regardless of tier.

``_resolve_audit_writer`` is ``async`` (needed to actually attempt the
JetStream connection at startup, the same "fail closed before touching
other resources" pattern already used for OIDC/policy), so every test below
awaits it; ``asyncio_mode = "auto"`` (root ``pyproject.toml``) means no
``@pytest.mark.asyncio`` is required, but it is kept for readability,
matching this file's own prior convention on the lifespan test below.
"""

from __future__ import annotations

from typing import Any

import pytest
from gateway import main as gateway_main
from runtime.audit import FileAuditWriter, InMemoryAuditWriter, JetStreamAuditWriter

# === Config-selection unit tests (no ASGI lifespan involved) =============== #


@pytest.mark.asyncio
async def test_resolve_audit_writer_uses_file_writer_when_path_set(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv('AUDIT_LOG_PATH', str(tmp_path / 'audit.jsonl'))
    monkeypatch.setenv('ENVIRONMENT', 'production')

    writer = await gateway_main._resolve_audit_writer()

    assert isinstance(writer, FileAuditWriter)


@pytest.mark.asyncio
@pytest.mark.parametrize('tier', ['production', 'prod', 'staging', 'stage', 'PRODUCTION'])
async def test_resolve_audit_writer_fails_closed_on_deployed_tier_without_path(
    tier: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv('AUDIT_LOG_PATH', raising=False)
    monkeypatch.delenv('AUDIT_MODE', raising=False)
    monkeypatch.setenv('ENVIRONMENT', tier)

    with pytest.raises(gateway_main.AuditConfigError) as excinfo:
        await gateway_main._resolve_audit_writer()

    # The error must name the tier/missing variable, never a secret or payload.
    assert 'AUDIT_LOG_PATH' in str(excinfo.value)


@pytest.mark.asyncio
async def test_resolve_audit_writer_defaults_to_production_when_environment_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # No AUDIT_LOG_PATH, no ENVIRONMENT at all: must fail closed, matching the
    # same fail-closed default as astradesk_core.utils.oidc.build_verifier_from_env.
    monkeypatch.delenv('AUDIT_LOG_PATH', raising=False)
    monkeypatch.delenv('AUDIT_MODE', raising=False)
    monkeypatch.delenv('ENVIRONMENT', raising=False)

    with pytest.raises(gateway_main.AuditConfigError):
        await gateway_main._resolve_audit_writer()


@pytest.mark.asyncio
@pytest.mark.parametrize('tier', ['dev', 'test', 'local', 'ci'])
async def test_resolve_audit_writer_allows_in_memory_writer_outside_deployed_tier(
    tier: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv('AUDIT_LOG_PATH', raising=False)
    monkeypatch.delenv('AUDIT_MODE', raising=False)
    monkeypatch.setenv('ENVIRONMENT', tier)

    writer = await gateway_main._resolve_audit_writer()

    assert isinstance(writer, InMemoryAuditWriter)


@pytest.mark.asyncio
async def test_resolve_audit_writer_warns_when_falling_back_to_in_memory(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.delenv('AUDIT_LOG_PATH', raising=False)
    monkeypatch.delenv('AUDIT_MODE', raising=False)
    monkeypatch.setenv('ENVIRONMENT', 'dev')

    with caplog.at_level('WARNING', logger=gateway_main.logger.name):
        await gateway_main._resolve_audit_writer()

    assert any('AUDIT_LOG_PATH not set' in rec.message for rec in caplog.records)


# === AUDIT_MODE=jetstream selection (ISSUE 039) ============================ #


class _FakeJsContext:
    """Minimal fake satisfying the ``stream_info``/``add_stream`` calls made
    by ``gateway.main._ensure_audit_stream`` — no real NATS connection."""

    def __init__(self, *, stream_exists: bool = False) -> None:
        self.stream_exists = stream_exists
        self.added: dict[str, Any] | None = None

    async def stream_info(self, name: str) -> None:
        if not self.stream_exists:
            import nats.js.errors

            raise nats.js.errors.NotFoundError
        return None

    async def add_stream(self, *, name: str, subjects: list[str]) -> None:
        self.added = {'name': name, 'subjects': subjects}


class _FakeNatsConnection:
    def __init__(self, js: _FakeJsContext) -> None:
        self._js = js
        self.closed = False

    def jetstream(self) -> _FakeJsContext:
        return self._js

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_resolve_audit_writer_selects_jetstream_when_mode_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('AUDIT_MODE', 'jetstream')
    monkeypatch.setenv('ENVIRONMENT', 'production')
    gateway_main.app_state.clear()

    fake_js = _FakeJsContext(stream_exists=False)
    fake_nc = _FakeNatsConnection(fake_js)

    async def fake_connect(*_args: object, **_kwargs: object) -> _FakeNatsConnection:
        return fake_nc

    writer = await gateway_main._build_jetstream_audit_writer(connect=fake_connect)

    assert isinstance(writer, JetStreamAuditWriter)
    # The stream did not exist, so it must have been created (idempotent path).
    assert fake_js.added == {
        'name': gateway_main._DEFAULT_AUDIT_JETSTREAM_STREAM,
        'subjects': [
            gateway_main._DEFAULT_AUDIT_JETSTREAM_SUBJECT,
            gateway_main._DEFAULT_AUDIT_JETSTREAM_DLQ_SUBJECT,
        ],
    }
    assert gateway_main.app_state['audit_nats_connection'] is fake_nc


@pytest.mark.asyncio
async def test_resolve_audit_writer_does_not_recreate_existing_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('AUDIT_MODE', 'jetstream')

    fake_js = _FakeJsContext(stream_exists=True)
    fake_nc = _FakeNatsConnection(fake_js)

    async def fake_connect(*_args: object, **_kwargs: object) -> _FakeNatsConnection:
        return fake_nc

    await gateway_main._build_jetstream_audit_writer(connect=fake_connect)

    assert fake_js.added is None  # stream_info succeeded; add_stream never called


@pytest.mark.asyncio
async def test_resolve_audit_writer_jetstream_fails_closed_on_connect_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('AUDIT_MODE', 'jetstream')
    monkeypatch.setenv('ENVIRONMENT', 'dev')  # even a non-deployed tier must fail closed here

    async def broken_connect(*_args: object, **_kwargs: object) -> None:
        raise ConnectionRefusedError('simulated broker outage')

    with pytest.raises(gateway_main.AuditConfigError) as excinfo:
        await gateway_main._build_jetstream_audit_writer(connect=broken_connect)

    # Names the failure class, never leaks a broker credential or payload.
    assert 'ConnectionRefusedError' in str(excinfo.value)


@pytest.mark.asyncio
async def test_resolve_audit_writer_prefers_jetstream_over_jsonl_when_both_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    """AUDIT_MODE=jetstream is explicit and wins even if AUDIT_LOG_PATH is
    also set — the two modes are mutually exclusive, not layered."""
    monkeypatch.setenv('AUDIT_MODE', 'jetstream')
    monkeypatch.setenv('AUDIT_LOG_PATH', str(tmp_path / 'audit.jsonl'))
    gateway_main.app_state.clear()

    fake_js = _FakeJsContext(stream_exists=True)
    fake_nc = _FakeNatsConnection(fake_js)

    async def fake_connect(*_args: object, **_kwargs: object) -> _FakeNatsConnection:
        return fake_nc

    monkeypatch.setattr(gateway_main.nats, 'connect', fake_connect)

    writer = await gateway_main._resolve_audit_writer()

    assert isinstance(writer, JetStreamAuditWriter)


# === Full lifespan: fail-closed before DB/Redis are touched ================ #


@pytest.mark.asyncio
async def test_lifespan_fails_closed_before_database_when_audit_unconfigured_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv('AUDIT_LOG_PATH', raising=False)
    monkeypatch.setenv('ENVIRONMENT', 'production')
    monkeypatch.setattr(gateway_main, 'install_verifier', lambda app: None)

    async def unexpected_pool_creation(*args: object, **kwargs: object) -> None:
        pytest.fail('database initialization ran before the audit sink check')

    monkeypatch.setattr(gateway_main.asyncpg, 'create_pool', unexpected_pool_creation)

    with pytest.raises(gateway_main.AuditConfigError):
        async with gateway_main.lifespan(gateway_main.app):
            pytest.fail('lifespan yielded despite missing durable audit sink')


# A full-lifespan "dev tier does not fail closed" sanity check is already
# covered end-to-end by ``tests/test_api.py::test_healthz_ok``, which runs the
# real ``lifespan`` with ``ENVIRONMENT=dev`` and no ``AUDIT_LOG_PATH`` and
# succeeds; duplicating that here would mean re-mocking the entire startup
# chain (DB pool, Redis, RAG, domain-pack loading) for no additional signal.
