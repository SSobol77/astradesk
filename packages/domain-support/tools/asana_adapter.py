# SPDX-License-Identifier: Apache-2.0
"""File: packages/domain-support/tools/asana_adapter.py
Project: AstraDesk Domain Support Pack
Description:
    Asynchronous tool with OAuth refresh for Asana integration via Admin API v1.2.0.
    Uses API /connectors for creation and probing, no direct Asana calls.
    Production-ready with async HTTP, retry, and structured errors.
    Auth: Uses PAT or OAuth token from config.

Author: Siergej Sobolewski
Since: 2025-10-16
"""
from typing import AsyncIterator, Dict
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from ..clients.api import AdminApiClient, ProblemDetail

class AsanaAdapter:
    def __init__(self, api_url: str = "http://localhost:8080/api/admin/v1", token: str = ""):
        self.client = AdminApiClient(api_url, token)
        self.asana_token = self._get_asana_token()  # Pobierz z /secrets

    def _get_asana_token(self):
        # GET /secrets/asana_oauth
        resp = self.client._client.get("/secrets/asana_oauth")
        if resp.status_code != 200:
            raise ValueError(ProblemDetail(**resp.json()))
        return resp.json()["value"]

    async def _refresh_asana_token(self):
        # POST /secrets/asana_oauth:rotate
        resp = await self.client._client.post("/secrets/asana_oauth:rotate")
        if resp.status_code != 200:
            raise ValueError(ProblemDetail(**resp.json()))
        self.asana_token = resp.json()["value"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def create_task(self, task_data: Dict) -> Dict:
        connector_data = {"name": "asana", "type": "asana", "config": {"token": self.asana_token}}
        connector = await self.client.create_connector(connector_data)

        probe_data = {"action": "create_task", "data": task_data}
        probe_resp = await self.client.client.post(f"/connectors/{connector['id']}:probe", json=probe_data)
        if probe_resp.status_code == 401:  # Token expired
            await self._refresh_asana_token()
            return await self.create_task(task_data)  # Retry with new token
        if probe_resp.status_code != 200:
            raise ValueError(ProblemDetail(**probe_resp.json()))

        return probe_resp.json()["result"]
