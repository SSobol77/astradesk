# SPDX-License-Identifier: Apache-2.0
"""File: packages/domain-supply/clients/api.py
Project: AstraDesk Domain Supply Pack
Description:
    Asynchronous reusable client for AstraDesk Admin API v1.2.0.
    Handles JWT auth, error parsing (ProblemDetail), and key endpoints for supply pack.
    Production-ready with retry, timeouts, and Pydantic models.

Author: Siergej Sobolewski
Since: 2025-10-16
"""

from typing import AsyncIterator, Dict, List, Optional
import httpx
from pydantic import BaseModel, HttpUrl
from tenacity import retry, stop_after_attempt, wait_exponential

class ProblemDetail(BaseModel):
    """Pydantic model for RFC 7807 ProblemDetail (OpenAPI schema)."""
    type: HttpUrl
    title: str
    status: int
    detail: str
    instance: Optional[HttpUrl] = None

class ReplenishResult(BaseModel):
    """Pydantic model for replenishment result, aligned with OpenAPI Run schema."""
    item_id: str
    quantity: int
    priority: str

class AdminApiClient:
    """Async client for AstraDesk Admin API v1.2.0 with retry."""
    def __init__(self, base_url: str = "http://localhost:8080/api/admin/v1", token: str = "", timeout: int = 30):
        self.client = httpx.AsyncClient(base_url=base_url, headers={"Authorization": f"Bearer {token}"}, timeout=timeout)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def create_agent(self, agent_data: Dict) -> Dict:
        """Create agent via POST /agents."""
        resp = await self.client.post("/agents", json=agent_data)
        if resp.status_code != 201:
            raise ValueError(ProblemDetail(**resp.json()))
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def test_agent(self, agent_id: str, input_data: Dict) -> str:
        """Test agent via POST /agents/{id}:test."""
        resp = await self.client.post(f"/agents/{agent_id}:test", json=input_data)
        if resp.status_code != 200:
            raise ValueError(ProblemDetail(**resp.json()))
        return resp.json()["run_id"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_run(self, run_id: str) -> Dict:
        """Get run status via GET /runs/{id}."""
        resp = await self.client.get(f"/runs/{run_id}")
        if resp.status_code != 200:
            raise ValueError(ProblemDetail(**resp.json()))
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def create_connector(self, connector_data: Dict) -> Dict:
        """Create connector via POST /connectors."""
        resp = await self.client.post("/connectors", json=connector_data)
        if resp.status_code != 201:
            raise ValueError(ProblemDetail(**resp.json()))
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def upload_flow(self, flow_data: Dict) -> Dict:
        """Upload flow via POST /flows."""
        resp = await self.client.post("/flows", json=flow_data)
        if resp.status_code != 201:
            raise ValueError(ProblemDetail(**resp.json()))
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def upload_policy(self, policy_data: Dict) -> Dict:
        """Upload policy via POST /policies."""
        resp = await self.client.post("/policies", json=policy_data)
        if resp.status_code != 201:
            raise ValueError(ProblemDetail(**resp.json()))
        return resp.json()
