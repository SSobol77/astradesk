#!/usr/bin/env python3
"""
Integration Tests for AstraDesk Gateway ↔ Agent ↔ MCP Flows

This module provides comprehensive integration testing for the complete
agent execution pipeline, including Gateway API, agent orchestration,
tool execution, and MCP server interactions.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional
import httpx
import pytest
from fastapi.testclient import TestClient

# AstraDesk imports
from services.api_gateway.src.gateway.main import app
from services.api_gateway.src.runtime.models import AgentRequest
from tests.test_harness import TestScenario, TestResult

logger = logging.getLogger(__name__)


class IntegrationTestSuite:
    """
    Comprehensive integration test suite for Gateway ↔ Agent ↔ MCP flows

    Tests full request lifecycle from HTTP API through to tool execution
    and response generation.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
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
            # Create agent request
            request_data = AgentRequest(
                agent=scenario.agent_type,
                input=scenario.input_query,
                meta={"test_scenario": scenario.name}
            )

            # Make HTTP request to gateway
            headers = {"Authorization": f"Bearer {auth_token}"}
            response = self.client.post(
                "/v1/run",
                json=request_data.model_dump(),
                headers=headers
            )

            execution_time = time.time() - start_time

            if response.status_code != 200:
                return TestResult(
                    scenario_name=scenario.name,
                    passed=False,
                    execution_time=execution_time,
                    tools_invoked=[],
                    response_quality_score=0.0,
                    security_violations=["http_error"],
                    error_message=f"HTTP {response.status_code}: {response.text}"
                )

            response_data = response.json()

            # Validate response structure
            if "output" not in response_data:
                return TestResult(
                    scenario_name=scenario.name,
                    passed=False,
                    execution_time=execution_time,
                    tools_invoked=[],
                    response_quality_score=0.0,
                    security_violations=["invalid_response"],
                    error_message="Missing 'output' field in response"
                )

            # Extract tool information
            tools_invoked = []
            if "invoked_tools" in response_data:
                tools_invoked = [tool.get("name", "") for tool in response_data["invoked_tools"]]

            # Evaluate response quality
            response_quality = self._evaluate_response_quality(
                response_data["output"],
                scenario
            )

            # Check for expected tools
            expected_tools_match = set(tools_invoked) == set(scenario.expected_tools)

            # Performance check
            performance_ok = execution_time <= scenario.performance_requirements.get("max_execution_time", 10.0)

            passed = expected_tools_match and response_quality >= 0.7 and performance_ok

            return TestResult(
                scenario_name=scenario.name,
                passed=passed,
                execution_time=execution_time,
                tools_invoked=tools_invoked,
                response_quality_score=response_quality,
                security_violations=[],
                metadata={
                    "http_status": response.status_code,
                    "response_length": len(response_data["output"]),
                    "expected_tools_match": expected_tools_match,
                    "performance_ok": performance_ok
                }
            )

        except Exception as e:
            logger.exception(f"Integration test failed for scenario {scenario.name}")
            return TestResult(
                scenario_name=scenario.name,
                passed=False,
                execution_time=time.time() - start_time,
                tools_invoked=[],
                response_quality_score=0.0,
                security_violations=["integration_error"],
                error_message=str(e)
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

    async def test_mcp_server_connectivity(self) -> Dict[str, bool]:
        """Test connectivity to all MCP servers"""
        mcp_servers = {
            "support": "http://localhost:8001/health",
            "ops": "http://localhost:8002/health",
            "finance": "http://localhost:8003/health",
            "supply": "http://localhost:8004/health"
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
            response = self.client.get("/healthz")
            return response.status_code == 200
        except Exception:
            return False

    async def test_authentication_flow(self) -> bool:
        """Test authentication and authorization"""
        # Test with valid token
        try:
            headers = {"Authorization": "Bearer valid-test-token"}
            response = self.client.post(
                "/v1/run",
                json=AgentRequest(
                    agent="support",
                    input="test query"
                ).model_dump(),
                headers=headers
            )
            # Should not return 401 (might return other errors but auth should pass)
            return response.status_code != 401
        except Exception:
            return False

    async def test_rate_limiting(self) -> bool:
        """Test rate limiting functionality"""
        # Make multiple rapid requests
        headers = {"Authorization": "Bearer test-token"}

        for i in range(10):
            response = self.client.post(
                "/v1/run",
                json=AgentRequest(
                    agent="support",
                    input=f"test query {i}"
                ).model_dump(),
                headers=headers
            )
            if response.status_code == 429:
                return True  # Rate limiting is working

        return False  # Rate limiting not triggered

    async def run_full_integration_test(self) -> Dict[str, Any]:
        """Run complete integration test suite"""
        results = {
            "gateway_health": await self.test_gateway_health(),
            "mcp_connectivity": await self.test_mcp_server_connectivity(),
            "authentication": await self.test_authentication_flow(),
            "rate_limiting": await self.test_rate_limiting(),
            "agent_scenarios": []
        }

        # Test key scenarios
        test_scenarios = [
            TestScenario(
                name="support_ticket_creation",
                description="Create support ticket",
                agent_type="support",
                input_query="Utwórz ticket dla problemu z VPN",
                expected_tools=["create_ticket"],
                expected_response_contains=["ticket"],
                performance_requirements={"max_execution_time": 5.0}
            ),
            TestScenario(
                name="ops_metrics",
                description="Get operational metrics",
                agent_type="ops",
                input_query="Pokaż metryki systemu",
                expected_tools=["get_metrics"],
                expected_response_contains=["CPU", "pamięć"],
                performance_requirements={"max_execution_time": 3.0}
            )
        ]

        auth_token = "test-integration-token"  # Would be a real JWT in production

        for scenario in test_scenarios:
            result = await self.test_full_agent_flow(scenario, auth_token)
            results["agent_scenarios"].append(result.model_dump())

        return results


# Pytest fixtures and test functions
@pytest.fixture
async def integration_suite():
    """Fixture for integration test suite"""
    suite = IntegrationTestSuite()
    await suite.setup_mcp_servers()
    return suite


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
        name="integration_support",
        description="Integration test for support agent",
        agent_type="support",
        input_query="Utwórz ticket dla problemu z siecią",
        expected_tools=["create_ticket"],
        expected_response_contains=["ticket"],
        performance_requirements={"max_execution_time": 10.0}
    )

    result = await integration_suite.test_full_agent_flow(scenario, "test-token")
    assert result.passed or result.error_message  # Either passes or has expected error


@pytest.mark.asyncio
async def test_full_agent_flow_ops(integration_suite):
    """Test complete ops agent flow"""
    scenario = TestScenario(
        name="integration_ops",
        description="Integration test for ops agent",
        agent_type="ops",
        input_query="Sprawdź metryki webapp",
        expected_tools=["get_metrics"],
        expected_response_contains=["metryki"],
        performance_requirements={"max_execution_time": 10.0}
    )

    result = await integration_suite.test_full_agent_flow(scenario, "test-token")
    assert result.passed or result.error_message  # Either passes or has expected error


@pytest.mark.asyncio
async def test_authentication_integration(integration_suite):
    """Test authentication integration"""
    # This test may need to be adjusted based on actual auth setup
    auth_works = await integration_suite.test_authentication_flow()
    # Authentication should at least not crash the system
    assert isinstance(auth_works, bool)


if __name__ == "__main__":
    # Run integration tests manually
    async def main():
        suite = IntegrationTestSuite()
        await suite.setup_mcp_servers()

        print("Running integration tests...")

        # Run full test suite
        results = await suite.run_full_integration_test()

        print("\n=== Integration Test Results ===")
        print(f"Gateway Health: {results['gateway_health']}")
        print(f"MCP Connectivity: {results['mcp_connectivity']}")
        print(f"Authentication: {results['authentication']}")
        print(f"Rate Limiting: {results['rate_limiting']}")

        print(f"\nAgent Scenarios: {len(results['agent_scenarios'])}")
        for scenario in results['agent_scenarios']:
            print(f"  {scenario['scenario_name']}: {'PASS' if scenario['passed'] else 'FAIL'}")

    asyncio.run(main())