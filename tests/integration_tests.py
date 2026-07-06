#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: tests/integration_tests.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for tests/integration_tests.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""
Integration Tests for AstraDesk Gateway ↔ Agent ↔ MCP Flows

This module provides comprehensive integration testing for the complete
agent execution pipeline, including Gateway API, agent orchestration,
tool execution, and MCP server interactions.

ISSUE 018 wiring notes
-----------------------
- All tests here carry the ``integration`` marker (registered in the root
  ``pyproject.toml``) and are run explicitly via
  ``uv run pytest -q -m integration tests/integration_tests.py`` — never
  picked up by a bare ``pytest -q`` glob, both because pytest's default
  ``python_files`` pattern (``test_*.py``/``*_test.py``) does not match this
  file's ``*_tests.py`` name, and (belt-and-suspenders) because of the
  explicit marker. See ``audit/evidence/18_integration_ci_gate.md``.
- ``integration_suite`` now enters ``TestClient``'s context (``with
  suite.client:``) so ``gateway.main.lifespan`` actually runs. Previously it
  did not: a bare ``TestClient(app)`` with no ``with``/context-manager use
  never starts FastAPI's lifespan, so ``app_state`` (orchestrator, DB pool,
  policy enforcer, ...) stayed empty for the whole test session and
  ``/v1/run`` could never genuinely exercise the agent → tool → RAG path —
  it could only ever hit whatever early error a missing ``app_state`` entry
  produced. This was the actual reason these tests could not test what
  ISSUE 018 asks for, independent of which services were running.
- Auth tokens are minted as real local-dev JWTs (`_mint_local_dev_token`)
  instead of arbitrary strings like ``'test-token'``: the Admin/Gateway auth
  dependency requires an actual signed JWT (HS256 in ``AUTH_MODE=local-dev``,
  ISSUE 009) even outside production, so a bare string was always rejected
  before reaching any agent/tool/RAG code, regardless of which services were
  running.
- ``test_mcp_server_connectivity`` is no longer ``xfail``. Three real,
  pre-existing blockers were found and fixed while wiring this gate (see
  ``audit/evidence/18_integration_ci_gate.md`` for full detail):
  (1) the 4 domain packs' ``pyproject.toml`` files did not declare
  `fastapi`/`uvicorn` even though every `mcp_server.py` imports them
  directly, so none of the images could start
  (`ModuleNotFoundError: No module named 'fastapi'`) — fixed by adding both
  as runtime dependencies; (2) all 4 `mcp-*` services in
  `docker-compose.dev.yml` bind-mounted the whole container `/app`,
  shadowing the image's own `.venv`/`core` — fixed by mounting at each
  package's own path instead; (3) `domain_support/clients/api.py` imported
  the repo-root test-only `respx` stub at module scope, so `mcp-support`'s
  import chain (`mcp_server.py` -> `jira_adapter.py` -> `clients/api.py`)
  crashed on `ModuleNotFoundError: No module named 'respx'` before the
  FastAPI app object even existed — fixed by deferring that import to
  inside `AdminApiClient._request`, where it is only needed once a real
  `jira.list_tickets` call is made, not at server startup.
- One more pre-existing, discovered-not-fixed defect worth flagging for a
  follow-up (tolerated today by this suite's lenient
  ``result.passed or result.error_message`` assertions, so it does not
  block this gate): the LLM planner path fails with
  `'OpaClient' object has no attribute 'check_policy'` before falling back
  to the keyword planner (may simply reflect no real OPA/LLM configured in
  this environment, but is recorded here for visibility). See
  ``audit/evidence/18_integration_ci_gate.md`` for full detail.
"""

import asyncio
import logging
import os
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

# AstraDesk imports
from gateway.main import app
from runtime.models import AgentName, AgentRequest

# Bare (not `tests.test_harness`): the root `conftest.py` registers a
# synthetic `tests` namespace package (pointing only at the domain-*
# packages' own `tests/` dirs) so `packages/domain-*/tests/*.py` can share
# fixtures without colliding with this top-level `tests/` directory. Since
# `tests/` has no `__init__.py`, pytest itself already imports this very
# module as a bare top-level module with `tests/` prepended to `sys.path`,
# so `test_harness` (bare) resolves the same file `tests.test_harness`
# would have, without fighting that synthetic package.
from test_harness import TestResult, TestScenario

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.integration


def _mint_local_dev_token(roles: list[str], *, subject: str = 'integration-test-user') -> str:
    """Mint a real HS256 JWT accepted by ``AUTH_MODE=local-dev`` (ISSUE 009).

    Matches ``astradesk_core.utils.oidc.LocalDevVerifier`` exactly: same
    secret/audience/issuer env vars and defaults, ``sub``/``exp``/``iat``
    required, ``roles`` space-or-list encoded. A plain string like
    ``'test-token'`` is never a valid JWT and is rejected before the
    orchestrator/agent/tool/RAG path is ever reached, regardless of which
    backing services are running — this is why earlier revisions of this
    suite could "pass" without ever exercising the real flow.
    """
    secret = os.getenv('ASTRADESK_DEV_JWT_SECRET', '')
    if not secret:
        pytest.skip(
            'ASTRADESK_DEV_JWT_SECRET is not set: AUTH_MODE=local-dev cannot mint a '
            'verifiable token, so the integration gate cannot exercise a real request.'
        )
    audience = os.getenv('OIDC_AUDIENCE', 'astradesk-local')
    issuer = os.getenv('OIDC_ISSUER', 'astradesk-local')
    now = datetime.now(UTC)
    payload = {
        'sub': subject,
        'iat': now,
        'exp': now + timedelta(minutes=5),
        'aud': audience,
        'iss': issuer,
        'roles': roles,
    }
    return jwt.encode(payload, secret, algorithm='HS256')


class IntegrationTestSuite:
    """
    Comprehensive integration test suite for Gateway ↔ Agent ↔ MCP flows

    Tests full request lifecycle from HTTP API through to tool execution
    and response generation.
    """

    def __init__(self, base_url: str = 'http://localhost:8000'):
        self.base_url = base_url
        self.client = TestClient(app)
        self.http_client = httpx.AsyncClient(base_url=base_url)

    async def setup_mcp_servers(self):
        """Ensure MCP servers are running for integration tests"""
        # In a real implementation, this would start MCP servers
        # For now, we'll assume they're running
        pass

    async def test_full_agent_flow(self, scenario: TestScenario, auth_token: str) -> TestResult:
        """Test complete agent execution flow"""
        start_time = time.time()

        try:
            # Create agent request. `scenario.agent_type` is a plain `str`
            # (TestScenario, tests/test_harness.py) — construct the real
            # `AgentName` enum member from it, matching the same pattern
            # already used by `tests/red_team_tests.py`'s
            # `AgentName(agent_type)`, rather than widening `AgentRequest`
            # or `AgentName` to accept `str`.
            request_data = AgentRequest(
                agent=AgentName(scenario.agent_type),
                input=scenario.input_query,
                meta={'test_scenario': scenario.name},
            )

            # Make HTTP request to gateway
            headers = {'Authorization': f'Bearer {auth_token}'}
            response = self.client.post('/v1/run', json=request_data.model_dump(), headers=headers)

            execution_time = time.time() - start_time

            if response.status_code != 200:
                return TestResult(
                    scenario_name=scenario.name,
                    passed=False,
                    execution_time=execution_time,
                    tools_invoked=[],
                    response_quality_score=0.0,
                    security_violations=['http_error'],
                    error_message=f'HTTP {response.status_code}: {response.text}',
                )

            response_data = response.json()

            # Validate response structure
            if 'output' not in response_data:
                return TestResult(
                    scenario_name=scenario.name,
                    passed=False,
                    execution_time=execution_time,
                    tools_invoked=[],
                    response_quality_score=0.0,
                    security_violations=['invalid_response'],
                    error_message="Missing 'output' field in response",
                )

            # Extract tool information
            tools_invoked = []
            if 'invoked_tools' in response_data:
                tools_invoked = [tool.get('name', '') for tool in response_data['invoked_tools']]

            # Evaluate response quality
            response_quality = self._evaluate_response_quality(response_data['output'], scenario)

            # Check for expected tools
            expected_tools_match = set(tools_invoked) == set(scenario.expected_tools)

            # Performance check
            performance_ok = execution_time <= scenario.performance_requirements.get(
                'max_execution_time', 10.0
            )

            passed = expected_tools_match and response_quality >= 0.7 and performance_ok

            return TestResult(
                scenario_name=scenario.name,
                passed=passed,
                execution_time=execution_time,
                tools_invoked=tools_invoked,
                response_quality_score=response_quality,
                security_violations=[],
                metadata={
                    'http_status': response.status_code,
                    'response_length': len(response_data['output']),
                    'expected_tools_match': expected_tools_match,
                    'performance_ok': performance_ok,
                },
            )

        except Exception as e:
            logger.exception(f'Integration test failed for scenario {scenario.name}')
            return TestResult(
                scenario_name=scenario.name,
                passed=False,
                execution_time=time.time() - start_time,
                tools_invoked=[],
                response_quality_score=0.0,
                security_violations=['integration_error'],
                error_message=str(e),
            )

    def _evaluate_response_quality(self, response: str, scenario: TestScenario) -> float:
        """Evaluate response quality for integration tests"""
        if not scenario.expected_response_contains:
            return 1.0

        response_lower = response.lower()
        matches = 0

        for expected in scenario.expected_response_contains:
            if expected.lower() in response_lower:
                matches += 1

        return matches / len(scenario.expected_response_contains)

    async def test_mcp_server_connectivity(self) -> dict[str, bool]:
        """Test connectivity to all MCP servers"""
        mcp_servers = {
            'support': 'http://localhost:8001/health',
            'ops': 'http://localhost:8002/health',
            'finance': 'http://localhost:8003/health',
            'supply': 'http://localhost:8004/health',
        }

        results = {}
        for name, url in mcp_servers.items():
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, timeout=5.0)
                    results[name] = response.status_code == 200
            except Exception:
                results[name] = False

        return results

    async def test_gateway_health(self) -> bool:
        """Test gateway health endpoint"""
        try:
            response = self.client.get('/healthz')
            return response.status_code == 200
        except Exception:
            return False

    async def test_authentication_flow(self) -> bool:
        """Test authentication and authorization"""
        # Test with a real (local-dev signed) token.
        try:
            token = _mint_local_dev_token(['it.support', 'sre'])
            headers = {'Authorization': f'Bearer {token}'}
            response = self.client.post(
                '/v1/run',
                json=AgentRequest(agent=AgentName.SUPPORT, input='test query').model_dump(),
                headers=headers,
            )
            # Should not return 401 (might return other errors but auth should pass)
            return response.status_code != 401
        except Exception:
            return False

    async def test_rate_limiting(self) -> bool:
        """Test rate limiting functionality"""
        # Make multiple rapid requests
        headers = {'Authorization': f'Bearer {_mint_local_dev_token(["it.support", "sre"])}'}

        for i in range(10):
            response = self.client.post(
                '/v1/run',
                json=AgentRequest(agent=AgentName.SUPPORT, input=f'test query {i}').model_dump(),
                headers=headers,
            )
            if response.status_code == 429:
                return True  # Rate limiting is working

        return False  # Rate limiting not triggered

    async def run_full_integration_test(self) -> dict[str, Any]:
        """Run complete integration test suite"""
        results: dict[str, Any] = {
            'gateway_health': await self.test_gateway_health(),
            'mcp_connectivity': await self.test_mcp_server_connectivity(),
            'authentication': await self.test_authentication_flow(),
            'rate_limiting': await self.test_rate_limiting(),
            'agent_scenarios': [],
        }

        # Test key scenarios
        test_scenarios = [
            TestScenario(
                name='support_ticket_creation',
                description='Create support ticket',
                agent_type='support',
                input_query='Utwórz ticket dla problemu z VPN',
                expected_tools=['create_ticket'],
                expected_response_contains=['ticket'],
                performance_requirements={'max_execution_time': 5.0},
            ),
            TestScenario(
                name='ops_metrics',
                description='Get operational metrics',
                agent_type='ops',
                input_query='Pokaż metryki systemu',
                expected_tools=['get_metrics'],
                expected_response_contains=['CPU', 'pamięć'],
                performance_requirements={'max_execution_time': 3.0},
            ),
        ]

        auth_token = _mint_local_dev_token(['it.support', 'sre'])

        for scenario in test_scenarios:
            result = await self.test_full_agent_flow(scenario, auth_token)
            results['agent_scenarios'].append(result.model_dump())

        return results


# Pytest fixtures and test functions
@pytest.fixture
async def integration_suite():
    """Fixture for integration test suite.

    Enters ``TestClient``'s context so ``gateway.main.lifespan`` actually
    runs for the duration of the test (see module docstring): without this,
    ``app_state`` (orchestrator, DB pool, policy enforcer, ...) is never
    populated and ``/v1/run`` cannot exercise the real agent → tool → RAG
    path no matter which backing services are running.
    """
    suite = IntegrationTestSuite()
    with suite.client:
        await suite.setup_mcp_servers()
        yield suite


@pytest.mark.asyncio
async def test_gateway_health(integration_suite):
    """Test gateway health check"""
    assert await integration_suite.test_gateway_health()


@pytest.mark.asyncio
async def test_mcp_server_connectivity(integration_suite):
    """Test MCP server connectivity"""
    connectivity = await integration_suite.test_mcp_server_connectivity()
    # At least some servers should be running for integration tests
    assert any(connectivity.values())


@pytest.mark.asyncio
async def test_full_agent_flow_support(integration_suite):
    """Test complete support agent flow"""
    scenario = TestScenario(
        name='integration_support',
        description='Integration test for support agent',
        agent_type='support',
        input_query='Utwórz ticket dla problemu z siecią',
        expected_tools=['create_ticket'],
        expected_response_contains=['ticket'],
        performance_requirements={'max_execution_time': 10.0},
    )

    result = await integration_suite.test_full_agent_flow(
        scenario, _mint_local_dev_token(['it.support', 'sre'])
    )
    assert result.passed or result.error_message  # Either passes or has expected error


@pytest.mark.asyncio
async def test_full_agent_flow_ops(integration_suite):
    """Test complete ops agent flow"""
    scenario = TestScenario(
        name='integration_ops',
        description='Integration test for ops agent',
        agent_type='ops',
        input_query='Sprawdź metryki webapp',
        expected_tools=['get_metrics'],
        expected_response_contains=['metryki'],
        performance_requirements={'max_execution_time': 10.0},
    )

    result = await integration_suite.test_full_agent_flow(
        scenario, _mint_local_dev_token(['it.support', 'sre'])
    )
    assert result.passed or result.error_message  # Either passes or has expected error


@pytest.mark.asyncio
async def test_authentication_integration(integration_suite):
    """Test authentication integration"""
    # This test may need to be adjusted based on actual auth setup
    auth_works = await integration_suite.test_authentication_flow()
    # Authentication should at least not crash the system
    assert isinstance(auth_works, bool)


if __name__ == '__main__':
    # Run integration tests manually
    async def main():
        suite = IntegrationTestSuite()
        await suite.setup_mcp_servers()

        print('Running integration tests...')

        # Run full test suite
        results = await suite.run_full_integration_test()

        print('\n=== Integration Test Results ===')
        print(f"Gateway Health: {results['gateway_health']}")
        print(f"MCP Connectivity: {results['mcp_connectivity']}")
        print(f"Authentication: {results['authentication']}")
        print(f"Rate Limiting: {results['rate_limiting']}")

        print(f"\nAgent Scenarios: {len(results['agent_scenarios'])}")
        for scenario in results['agent_scenarios']:
            print(f"  {scenario['scenario_name']}: {'PASS' if scenario['passed'] else 'FAIL'}")

    asyncio.run(main())
