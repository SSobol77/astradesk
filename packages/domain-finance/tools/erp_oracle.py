# SPDX-License-Identifier: Apache-2.0
"""File: packages/domain-finance/tools/erp_oracle.py
Project: AstraDesk Domain Finance Pack
Description:
    Asynchronous tool for interacting with Oracle ERP via Admin API v1.2.0.
    Uses API /connectors for creation and probing, no direct database calls.
    Production-ready with async HTTP, error handling, and retry.

Author: Siergej Sobolewski
Since: 2025-10-16
"""

from typing import AsyncIterator, Dict
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from ..clients.api import AdminApiClient, ProblemDetail

class OracleERPAdapter:
    """Async Oracle ERP adapter integrated with Admin API (/connectors)."""
    def __init__(self, api_url: str = "http://localhost:8080/api/admin/v1", token: str = ""):
        self.client = AdminApiClient(api_url, token)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def fetch_sales(self, query: str) -> AsyncIterator[Dict]:
        """Fetch sales data via API /connectors/{id}:probe after creation.

        Steps:
        1. Create or get connector via POST /connectors or GET /connectors.
        2. Probe connector with query via POST /connectors/{id}:probe.

        :param query: SQL-like query for ERP (e.g., "SELECT revenue, date FROM sales").
        :raises ValueError: If API call fails (parsed as ProblemDetail).
        :yield: Dict for each sales record.
        """
        # Step 1: Create or get connector
        connector_data = {"name": "erp_oracle", "type": "db", "config": {"dsn": "oracle://user:pass@host"}}
        try:
            connector = await self.client.create_connector(connector_data)
        except ValueError as e:
            connectors_resp = await self.client._client.get("/connectors", params={"name": "erp_oracle"})
            if connectors_resp.status_code == 200 and connectors_resp.json():
                connector = connectors_resp.json()[0]
            else:
                raise e

        # Step 2: Probe with query
        probe_data = {"query": query}
        probe_resp = await self.client._client.post(f"/connectors/{connector['id']}:probe", json=probe_data)
        if probe_resp.status_code != 200:
            raise ValueError(ProblemDetail(**probe_resp.json()))

        for item in probe_resp.json()["result"]:  # Assume result is list of dicts
            yield item
