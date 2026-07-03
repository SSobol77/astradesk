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

"""Startup-time audit sink selection tests (ISSUE 019).

Verifies that ``gateway.main._resolve_audit_writer`` — called from
``lifespan`` before any external resource (DB/Redis) is touched — fails
closed on a deployed tier without a durable sink, mirrors the OIDC
fail-closed default (``ENVIRONMENT`` unset => ``'production'``), and still
allows the non-durable in-process writer for local/dev/test tiers.
"""

from __future__ import annotations

from typing import Any

import pytest
from gateway import main as gateway_main
from runtime.audit import FileAuditWriter, InMemoryAuditWriter

# === Config-selection unit tests (no ASGI lifespan involved) =============== #


def test_resolve_audit_writer_uses_file_writer_when_path_set(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv('AUDIT_LOG_PATH', str(tmp_path / 'audit.jsonl'))
    monkeypatch.setenv('ENVIRONMENT', 'production')

    writer = gateway_main._resolve_audit_writer()

    assert isinstance(writer, FileAuditWriter)


@pytest.mark.parametrize('tier', ['production', 'prod', 'staging', 'stage', 'PRODUCTION'])
def test_resolve_audit_writer_fails_closed_on_deployed_tier_without_path(
    tier: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv('AUDIT_LOG_PATH', raising=False)
    monkeypatch.setenv('ENVIRONMENT', tier)

    with pytest.raises(gateway_main.AuditConfigError) as excinfo:
        gateway_main._resolve_audit_writer()

    # The error must name the tier/missing variable, never a secret or payload.
    assert 'AUDIT_LOG_PATH' in str(excinfo.value)


def test_resolve_audit_writer_defaults_to_production_when_environment_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # No AUDIT_LOG_PATH, no ENVIRONMENT at all: must fail closed, matching the
    # same fail-closed default as astradesk_core.utils.oidc.build_verifier_from_env.
    monkeypatch.delenv('AUDIT_LOG_PATH', raising=False)
    monkeypatch.delenv('ENVIRONMENT', raising=False)

    with pytest.raises(gateway_main.AuditConfigError):
        gateway_main._resolve_audit_writer()


@pytest.mark.parametrize('tier', ['dev', 'test', 'local', 'ci'])
def test_resolve_audit_writer_allows_in_memory_writer_outside_deployed_tier(
    tier: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv('AUDIT_LOG_PATH', raising=False)
    monkeypatch.setenv('ENVIRONMENT', tier)

    writer = gateway_main._resolve_audit_writer()

    assert isinstance(writer, InMemoryAuditWriter)


def test_resolve_audit_writer_warns_when_falling_back_to_in_memory(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.delenv('AUDIT_LOG_PATH', raising=False)
    monkeypatch.setenv('ENVIRONMENT', 'dev')

    with caplog.at_level('WARNING', logger=gateway_main.logger.name):
        gateway_main._resolve_audit_writer()

    assert any('AUDIT_LOG_PATH not set' in rec.message for rec in caplog.records)


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
