# SPDX-License-Identifier: Apache-2.0
"""File: packages/domain-supply/tools/sap_mm.py
Project: AstraDesk Domain Supply Pack
Description:
    Asynchronous tool for interacting with SAP MM via Admin API v1.2.0.
    Uses API /connectors for creation and probing, no direct SAP calls.
    Production-ready with async HTTP, retry, and structured errors.

Author: Siergej Sobolewski
Since: 2025-10-16
"""

from typing import AsyncIterator, Dict
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from ..clients.api import AdminApiClient, ProblemDetail

class SAPMMAdapter:
    """Async SAP MM adapter integrated with Admin API (/connectors)."""
    def __init__(self, api_url: str = "http://localhost:8080/api/admin/v1", token: str = ""):
        self.client = AdminApiClient(api_url, token)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def fetch_inventory(self, query: str) -> AsyncIterator[Dict]:
        """Fetch inventory data via API /connectors/{id}:probe.

        Steps:
        1. Create or get connector via POST /connectors or GET /connectors.
        2. Probe connector with query via POST /connectors/{id}:probe.

        :param query: SAP query (e.g., "SELECT material, stock FROM MM WHERE plant='PL01'").
        :raises ValueError: If API call fails (parsed as ProblemDetail).
        :yield: Dict for each inventory record.
        """
        connector_data = {"name": "sap_mm", "type": "sap", "config": {"system": "SAP_MM", "plant": "PL01"}}
        try:
            connector = await self.client.create_connector(connector_data)
        except ValueError as e:
            connectors_resp = await self.client._client.get("/connectors", params={"name": "sap_mm"})
            if connectors_resp.status_code == 200 and connectors_resp.json():
                connector = connectors_resp.json()[0]
            else:
                raise e

        probe_data = {"query": query}
        probe_resp = await self.client._client.post(f"/connectors/{connector['id']}:probe", json=probe_data)
        if probe_resp.status_code != 200:
            raise ValueError(ProblemDetail(**probe_resp.json()))

        for item in probe_resp.json()["result"]:
            yield item
