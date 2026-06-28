# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: packages/domain-support/tests/test_triage.py
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

"""Production-level tests for triage agent with Asana/Slack.
Uses respx for API mocking.
"""

import pytest
from domain_support.agents.triage import triage_tickets
from domain_support.clients.api import ProblemDetail

from respx import MockRouter


@pytest.mark.asyncio
async def test_triage_success(respx_mock: MockRouter):
    """Test successful triage with mocked API, Asana, Slack."""
    respx_mock.post('/agents').respond(201, json={'id': 'sup1'})
    respx_mock.post('/agents/sup1:test').respond(200, json={'run_id': 'run_sup1'})
    respx_mock.get('/runs/run_sup1').respond(
        200,
        json={
            'status': 'completed',
            'output': [{'ticket_id': 'T1', 'priority': 'Critical', 'action': 'escalate'}],
        },
    )

    results = [
        res
        async for res in triage_tickets(
            [{'id': 'T1', 'summary': 'Urgent'}], api_url='http://mock', token='fake'
        )
    ]
    assert len(results) == 1
    assert results[0].priority == 'Critical'
    assert results[0].asana_task_id is not None  # Mocked
    assert results[0].slack_message_id is not None


@pytest.mark.asyncio
async def test_triage_api_error(respx_mock: MockRouter):
    """Test API error handling."""
    respx_mock.post('/agents').respond(
        400,
        json={
            'type': 'https://error',
            'title': 'Bad Request',
            'status': 400,
            'detail': 'Invalid config',
        },
    )

    with pytest.raises(ValueError) as exc:
        async for _ in triage_tickets(
            [{'id': 'T1', 'summary': 'Urgent'}], api_url='http://mock', token='fake'
        ):
            pass
    assert isinstance(exc.value.args[0], ProblemDetail)
    assert exc.value.args[0].status == 400
