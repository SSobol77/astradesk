# packages/domain-support/clients/api.py
from typing import AsyncIterator, Dict, List, Optional
import httpx
from pydantic import BaseModel, HttpUrl

class ProblemDetail(BaseModel):
    """Pydantic model for RFC 7807 ProblemDetail (OpenAPI schema)."""
    type: HttpUrl
    title: str
    status: int
    detail: str
    instance: Optional[HttpUrl] = None

class AdminApiClient:
    """Async client for AstraDesk Admin API v1.2.0."""
    def __init__(self, base_url: str = "http://localhost:8080/api/admin/v1", token: str = ""):
        self.client = httpx.AsyncClient(base_url=base_url, headers={"Authorization": f"Bearer {token}"})

    async def create_agent(self, agent_data: Dict) -> Dict:
        """Create agent via POST /agents."""
        resp = await self.client.post("/agents", json=agent_data)
        if resp.status_code != 201:
            raise ValueError(ProblemDetail(**resp.json()))
        return resp.json()

    async def test_agent(self, agent_id: str, input_data: Dict) -> str:
        """Test agent via POST /agents/{id}:test, returns run_id."""
        resp = await self.client.post(f"/agents/{agent_id}:test", json=input_data)
        if resp.status_code != 200:
            raise ValueError(ProblemDetail(**resp.json()))
        return resp.json()["run_id"]

    async def get_run(self, run_id: str) -> Dict:
        """Get run status via GET /runs/{id}."""
        resp = await self.client.get(f"/runs/{run_id}")
        if resp.status_code != 200:
            raise ValueError(ProblemDetail(**resp.json()))
        return resp.json()

    async def upload_flow(self, flow_data: Dict) -> Dict:
        """Upload flow via POST /flows."""
        resp = await self.client.post("/flows", json=flow_data)
        if resp.status_code != 201:
            raise ValueError(ProblemDetail(**resp.json()))
        return resp.json()

    async def upload_policy(self, policy_data: Dict) -> Dict:
        """Upload policy via POST /policies."""
        resp = await self.client.post("/policies", json=policy_data)
        if resp.status_code != 201:
            raise ValueError(ProblemDetail(**resp.json()))
        return resp.json()
