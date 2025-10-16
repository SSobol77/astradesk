# SPDX-License-Identifier: Apache-2.0
"""File: packages/domain-support/tools/slack_adapter.py
Project: AstraDesk Domain Support Pack
Description:
    Asynchronous tool for Slack messaging with OAuth refresh integration via Admin API v1.2.0.
    Uses API /connectors for creation and probing, no direct Slack calls.
    Production-ready with async HTTP, retry, and structured errors.
    Auth: Uses OAuth token from config, rate limits handled.

Author: Siergej Sobolewski
Since: 2025-10-16
"""
from typing import Dict
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from ..clients.api import AdminApiClient, ProblemDetail

class SlackAdapter:
    def __init__(self, api_url: str = "http://localhost:8080/api/admin/v1", token: str = ""):
        self.client = AdminApiClient(api_url, token)
        self.slack_token = self._get_slack_token()

    def _get_slack_token(self):
        resp = self.client._client.get("/secrets/slack_oauth")
        if resp.status_code != 200:
            raise ValueError(ProblemDetail(**resp.json()))
        return resp.json()["value"]

    async def _refresh_slack_token(self):
        resp = await self.client._client.post("/secrets/slack_oauth:rotate")
        if resp.status_code != 200:
            raise ValueError(ProblemDetail(**resp.json()))
        self.slack_token = resp.json()["value"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def post_message(self, message_data: Dict) -> Dict:
        connector_data = {"name": "slack", "type": "slack", "config": {"token": self.slack_token}}
        connector = await self.client.create_connector(connector_data)

        probe_data = {"action": "post_message", "data": message_data}
        probe_resp = await self.client.client.post(f"/connectors/{connector['id']}:probe", json=probe_data)
        if probe_resp.status_code == 401:  # Token expired
            await self._refresh_slack_token()
            return await self.post_message(message_data)
        if probe_resp.status_code != 200:
            raise ValueError(ProblemDetail(**probe_resp.json()))

        return probe_resp.json()["result"]