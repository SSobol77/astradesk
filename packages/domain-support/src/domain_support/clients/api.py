# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: packages/domain-support/src/domain_support/clients/api.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for packages/domain-support/src/domain_support/clients/api.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Support domain Admin API shim built on the respx stub."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast


@dataclass
class ProblemDetail(Exception):
    title: str
    detail: str
    status: int
    type: str = 'about:blank'


class AdminApiClient:
    def __init__(self, base_url: str = 'http://localhost:8080/api/admin/v1', token: str = ''):
        self.base_path = base_url.rstrip('/')
        self.token = token

    def _normalize_path(self, path: str) -> str:
        if path.startswith(self.base_path):
            path = path[len(self.base_path) :]
        if not path.startswith('/'):
            path = '/' + path
        return path

    async def _request(self, method: str, path: str, payload: dict[str, Any]) -> Any:
        # Imported lazily: `respx` here is the repo-root test-only stub
        # (respx/__init__.py, "used in the tests" — see root conftest.py's
        # sys.path wiring), not the real PyPI package. It is not shipped into
        # any service's Docker image, so this dispatch call only resolves
        # under pytest. A module-level import broke `mcp-support`'s
        # container startup outright (ModuleNotFoundError at import time,
        # before the FastAPI app object even existed, discovered while
        # wiring ISSUE 018's integration gate — see
        # audit/evidence/18_integration_ci_gate.md): `JiraAdapter()` is
        # constructed at `mcp_server.py` module scope but never calls
        # `_request` until a real `jira.list_tickets` tool invocation, so
        # deferring the import here lets the server start and serve
        # `/health` while leaving this method's existing test-only behavior
        # unchanged.
        from respx import dispatch

        route = self._normalize_path(path)
        response = dispatch(method, route, payload)
        if response.status_code >= 400:
            data = response.json() or {}
            raise ValueError(ProblemDetail(**data))
        return response.json() or {}

    async def create_agent(self, agent_data: dict[str, Any]) -> dict[str, Any]:
        return cast(dict[str, Any], await self._request('POST', '/agents', agent_data))

    async def test_agent(self, agent_id: str, input_data: dict[str, Any]) -> str:
        data = await self._request('POST', f'/agents/{agent_id}:test', input_data)
        return data.get('run_id', '')

    async def get_run(self, run_id: str) -> dict[str, Any]:
        return cast(dict[str, Any], await self._request('GET', f'/runs/{run_id}', {}))

    async def create_connector(self, connector_data: dict[str, Any]) -> dict[str, Any]:
        return cast(dict[str, Any], await self._request('POST', '/connectors', connector_data))

    async def list_connectors(self, name: str | None = None) -> list[dict[str, Any]]:
        data = await self._request('GET', '/connectors', {'name': name} if name else {})
        return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []

    async def probe_connector(
        self, connector_id: str, probe_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self._request('POST', f'/connectors/{connector_id}:probe', probe_data or {}),
        )
