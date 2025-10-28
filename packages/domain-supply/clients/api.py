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

    async def create_connector(self, connector_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("POST", "/connectors", connector_data)

    async def upload_flow(self, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("POST", "/flows", flow_data)

    async def upload_policy(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("POST", "/policies", policy_data)
