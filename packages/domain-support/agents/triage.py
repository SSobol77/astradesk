"""Support ticket triage agent that works with the testing stubs."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import AsyncIterator, Dict, List

from ..clients.api import AdminApiClient, ProblemDetail
from ..tools.asana_adapter import AsanaAdapter
from ..tools.slack_adapter import SlackAdapter


@dataclass
class TriageResult:
    ticket_id: str
    priority: str
    action: str
    asana_task_id: str | None = None
    slack_message_id: str | None = None


async def triage_tickets(
    tickets: List[Dict],
    api_url: str = "http://localhost:8080/api/admin/v1",
    token: str = "",
) -> AsyncIterator[TriageResult]:
    client = AdminApiClient(api_url, token)
    asana = AsanaAdapter()
    slack = SlackAdapter()

    agent = await client.create_agent({"name": "support_triage", "config": {"type": "triage"}})
    run_id = await client.test_agent(agent["id"], {"tickets": tickets})

    while True:
        run = await client.get_run(run_id)
        if run.get("status") != "completed":
            await asyncio.sleep(1)
            continue

        for raw in run.get("output", []):
            result = TriageResult(**raw)
            if result.priority.lower() == "critical":
                asana_task = await asana.create_task({"ticket_id": result.ticket_id})
                slack_message = await slack.post_message({"ticket_id": result.ticket_id})
                result.asana_task_id = asana_task.get("task_id")
                result.slack_message_id = slack_message.get("message_id")
            yield result
        break
