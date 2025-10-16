# SPDX-License-Identifier: Apache-2.0
"""File: packages/domain-support/agents/triage.py
Project: AstraDesk Domain Support Pack
Description:
    Asynchronous agent with Asana/Slack for ticket triage with Asana and Slack integration.
    Integrates via Admin API v1.2.0 for agent creation, testing, and run monitoring.
    No direct imports from core modules; all interactions through HTTP calls.

Author: Siergej Sobolewski
Since: 2025-10-16
"""

from typing import AsyncIterator, List, Dict
from ..clients.api import AdminApiClient, ProblemDetail
from ..tools.asana_adapter import AsanaAdapter
from ..tools.slack_adapter import SlackAdapter

class TriageResult(BaseModel):
    ticket_id: str
    priority: str
    action: str

async def triage_tickets(tickets: List[Dict], api_url: str = "http://localhost:8080/api/admin/v1", token: str = "") -> AsyncIterator[TriageResult]:
    client = AdminApiClient(api_url, token)
    asana = AsanaAdapter(api_url, token)
    slack = SlackAdapter(api_url, token)

    agent_data = {"name": "support_triage", "config": {"type": "triage"}}
    agent = await client.create_agent(agent_data)

    input_data = {"tickets": tickets}
    run_id = await client.test_agent(agent["id"], input_data)

    while True:
        run = await client.get_run(run_id)
        if run["status"] == "completed":
            for result in run["output"]:
                triage = TriageResult(**result)
                if triage.priority == "Critical":
                    await asana.create_task({"name": f"Ticket {triage.ticket_id}", "project_gid": "your_gid"})
                    await slack.post_message({"channel": "#support", "text": f"Critical: {triage.ticket_id}"})
                yield triage
            break
        await asyncio.sleep(1)
