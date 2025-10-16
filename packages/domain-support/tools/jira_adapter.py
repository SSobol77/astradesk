# packages/domain-support/tools/jira_adapter.py
from typing import AsyncIterator
from .clients.api import AdminApiClient

class JiraAdapter:
    """JIRA client via Admin API."""
    def __init__(self, api_url: str = "http://localhost:8080/api/admin/v1", token: str = ""):
        self.client = AdminApiClient(api_url, token)

    async def list_tickets(self, jql: str) -> AsyncIterator[dict]:
        """Fetch tickets via /connectors."""
        connector_data = {"name": "jira", "type": "api", "config": {"jql": jql}}
        connector = await self.client.create_connector(connector_data)
        probe_resp = await self.client.client.post(f"/connectors/{connector['id']}:probe")
        if probe_resp.status_code != 200:
            raise ValueError(ProblemDetail(**probe_resp.json()))
        for issue in probe_resp.json()["result"]:
            yield issue
