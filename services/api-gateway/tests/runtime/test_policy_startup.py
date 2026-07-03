# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/tests/runtime/test_policy_startup.py
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

"""Startup-time policy enforcer selection tests (ISSUE 028).

Verifies that ``gateway.main.lifespan`` calls
``runtime.policy_enforcer.build_policy_enforcer_from_env`` fail-closed —
before any external resource (DB/Redis) is touched — mirroring the existing
OIDC (ISSUE 009) and audit (ISSUE 019) fail-closed startup checks in the same
function. The full tier/mode decision matrix itself is covered by
``test_policy_enforcer.py``; this file only exercises the gateway wiring.
"""

from __future__ import annotations

from typing import Any

import pytest
from gateway import main as gateway_main
from runtime.policy_enforcer import PolicyConfigError


@pytest.mark.asyncio
async def test_lifespan_fails_closed_before_database_when_policy_unconfigured_in_production(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Audit is configured so the failure below is unambiguously attributable
    # to the policy check, not the audit check that runs immediately before it.
    monkeypatch.setenv('AUDIT_LOG_PATH', str(tmp_path / 'audit.jsonl'))
    monkeypatch.setenv('ENVIRONMENT', 'production')
    monkeypatch.delenv('POLICY_MODE', raising=False)
    monkeypatch.delenv('OPA_URL', raising=False)
    monkeypatch.setattr(gateway_main, 'install_verifier', lambda app: None)

    async def unexpected_pool_creation(*args: object, **kwargs: object) -> None:
        pytest.fail('database initialization ran before the policy config check')

    monkeypatch.setattr(gateway_main.asyncpg, 'create_pool', unexpected_pool_creation)

    with pytest.raises(PolicyConfigError):
        async with gateway_main.lifespan(gateway_main.app):
            pytest.fail('lifespan yielded despite missing policy configuration')


@pytest.mark.asyncio
async def test_lifespan_fails_closed_when_policy_mode_local_forbidden_in_production(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv('AUDIT_LOG_PATH', str(tmp_path / 'audit.jsonl'))
    monkeypatch.setenv('ENVIRONMENT', 'production')
    monkeypatch.setenv('POLICY_MODE', 'local')
    monkeypatch.setattr(gateway_main, 'install_verifier', lambda app: None)

    async def unexpected_pool_creation(*args: object, **kwargs: object) -> None:
        pytest.fail('database initialization ran before the policy config check')

    monkeypatch.setattr(gateway_main.asyncpg, 'create_pool', unexpected_pool_creation)

    with pytest.raises(PolicyConfigError):
        async with gateway_main.lifespan(gateway_main.app):
            pytest.fail('lifespan yielded despite POLICY_MODE=local on a deployed tier')


# A full-lifespan "dev tier does not fail closed" sanity check is already
# covered end-to-end by ``tests/test_api.py::test_healthz_ok``, which runs the
# real ``lifespan`` with ``ENVIRONMENT=dev`` (no ``POLICY_MODE``/``OPA_URL``)
# and succeeds; duplicating that here would mean re-mocking the entire startup
# chain (DB pool, Redis, RAG, domain-pack loading) for no additional signal —
# the same reasoning ``test_audit_startup.py`` already documents for ISSUE 019.
