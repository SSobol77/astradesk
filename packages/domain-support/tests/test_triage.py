# SPDX-License-Identifier: Apache-2.0
"""File: packages/domain-support/tests/test_triage.py
Project: AstraDesk Domain Support Pack
Description:
    Production-level tests for triage agent with Asana/Slack.
    Uses respx for API mocking.

Author: Siergej Sobolewski
Since: 2025-10-16
"""

import pytest
import httpx
from respx import MockRouter
from ..agents.triage import triage_tickets
from ..clients.api import ProblemDetail

@pytest.mark.asyncio
async def test_triage_success(respx_mock: MockRouter):
    """Test successful triage with mocked API, Asana, Slack."""
    respx_mock.post("/agents").respond(201, json={"id": "sup1"})
    respx_mock.post("/agents/sup1:test").respond(200, json={"run_id": "run_sup1"})
    respx_mock.get("/runs/run_sup1").respond(200, json={"status": "completed", "output": [{"ticket_id": "T1", "priority": "Critical", "action": "escalate"}]})

    results = [res async for res in triage_tickets([{"id": "T1", "summary": "Urgent"}], api_url="http://mock", token="fake")]
    assert len(results) == 1
    assert results[0].priority == "Critical"
    assert results[0].asana_task_id is not None  # Mocked
    assert results[0].slack_message_id is not None

@pytest.mark.asyncio
async def test_triage_api_error(respx_mock: MockRouter):
    """Test API error handling."""
    respx_mock.post("/agents").respond(400, json={"type": "https://error", "title": "Bad Request", "status": 400, "detail": "Invalid config"})

    with pytest.raises(ValueError) as exc:
        async for _ in triage_tickets([{"id": "T1", "summary": "Urgent"}], api_url="http://mock", token="fake"):
            pass
    assert isinstance(exc.value.args[0], ProblemDetail)
    assert exc.value.args[0].status == 400
