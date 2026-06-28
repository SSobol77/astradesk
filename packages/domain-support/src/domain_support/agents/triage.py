# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: packages/domain-support/src/domain_support/agents/triage.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for packages/domain-support/src/domain_support/agents/triage.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Support ticket triage agent that works with the testing stubs."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass

from domain_support.clients.api import AdminApiClient
from domain_support.tools.asana_adapter import AsanaAdapter
from domain_support.tools.slack_adapter import SlackAdapter


@dataclass
class TriageResult:
    ticket_id: str
    priority: str
    action: str
    asana_task_id: str | None = None
    slack_message_id: str | None = None


async def triage_tickets(
    tickets: list[dict],
    api_url: str = 'http://localhost:8080/api/admin/v1',
    token: str = '',
) -> AsyncIterator[TriageResult]:
    client = AdminApiClient(api_url, token)
    asana = AsanaAdapter()
    slack = SlackAdapter()

    agent = await client.create_agent({'name': 'support_triage', 'config': {'type': 'triage'}})
    run_id = await client.test_agent(agent['id'], {'tickets': tickets})

    while True:
        run = await client.get_run(run_id)
        if run.get('status') != 'completed':
            await asyncio.sleep(1)
            continue

        for raw in run.get('output', []):
            result = TriageResult(**raw)
            if result.priority.lower() == 'critical':
                asana_task = await asana.create_task({'ticket_id': result.ticket_id})
                slack_message = await slack.post_message({'ticket_id': result.ticket_id})
                result.asana_task_id = asana_task.get('task_id')
                result.slack_message_id = slack_message.get('message_id')
            yield result
        break
