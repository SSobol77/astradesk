"""Support domain Admin API shim built on the respx stub."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from respx import dispatch


@dataclass
class ProblemDetail(Exception):
    title: str
    detail: str
    status: int
    type: str = "about:blank"


class AdminApiClient:
    def __init__(self, base_url: str = "http://localhost:8080/api/admin/v1", token: str = ""):
        self.base_path = base_url.rstrip("/")
        self.token = token

    def _normalize_path(self, path: str) -> str:
        if path.startswith(self.base_path):
            path = path[len(self.base_path):]
        if not path.startswith("/"):
            path = "/" + path
        return path

    async def _request(self, method: str, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        route = self._normalize_path(path)
        response = dispatch(method, route, payload)
        if response.status_code >= 400:
            data = response.json() or {}
            raise ValueError(ProblemDetail(**data))
        return response.json() or {}

    async def create_agent(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("POST", "/agents", agent_data)

    async def test_agent(self, agent_id: str, input_data: Dict[str, Any]) -> str:
        data = await self._request("POST", f"/agents/{agent_id}:test", input_data)
        return data.get("run_id", "")

    async def get_run(self, run_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"/runs/{run_id}", {})
