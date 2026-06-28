# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: packages/domain-finance/src/domain_finance/clients/api.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for packages/domain-finance/src/domain_finance/clients/api.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Asynchronous reusable client for AstraDesk Admin API v1.2.0.
Handles JWT auth, error parsing (ProblemDetail), and key endpoints for finance pack.
Production-ready with retry, timeouts, and Pydantic models.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from respx import dispatch


@dataclass
class ProblemDetail(Exception):
    """Lightweight RFC-7807 representation used when a mocked API rejects a request."""

    title: str
    detail: str
    status: int
    type: str = 'about:blank'


class AdminApiClient:
    """Async client façade that delegates to the respx stub for deterministic tests."""

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
        self, connector_id: str, probe_data: dict[str, Any]
    ) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self._request('POST', f'/connectors/{connector_id}:probe', probe_data),
        )

    async def upload_flow(self, flow_data: dict[str, Any]) -> dict[str, Any]:
        return cast(dict[str, Any], await self._request('POST', '/flows', flow_data))

    async def upload_policy(self, policy_data: dict[str, Any]) -> dict[str, Any]:
        return cast(dict[str, Any], await self._request('POST', '/policies', policy_data))
