# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: packages/domain-supply/src/domain_supply/tools/sap_mm.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for packages/domain-supply/src/domain_supply/tools/sap_mm.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Asynchronous tool for interacting with SAP MM via Admin API v1.2.0.
Uses API /connectors for creation and probing, no direct SAP calls.
Production-ready with async HTTP, retry, and structured errors.
"""

from collections.abc import AsyncIterator

from tenacity import retry, stop_after_attempt, wait_exponential

from domain_supply.clients.api import AdminApiClient


class SAPMMAdapter:
    """Async SAP MM adapter integrated with Admin API (/connectors)."""

    def __init__(self, api_url: str = 'http://localhost:8080/api/admin/v1', token: str = ''):
        self.client = AdminApiClient(api_url, token)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def fetch_inventory(self, query: str) -> AsyncIterator[dict]:
        """Fetch inventory data via API /connectors/{id}:probe.

        Steps:
        1. Create or get connector via POST /connectors or GET /connectors.
        2. Probe connector with query via POST /connectors/{id}:probe.

        :param query: SAP query (e.g., "SELECT material, stock FROM MM WHERE plant='PL01'").
        :raises ValueError: If API call fails (parsed as ProblemDetail).
        :yield: Dict for each inventory record.
        """
        connector_data = {
            'name': 'sap_mm',
            'type': 'sap',
            'config': {'system': 'SAP_MM', 'plant': 'PL01'},
        }
        try:
            connector = await self.client.create_connector(connector_data)
        except ValueError as e:
            connectors = await self.client.list_connectors(name='sap_mm')
            if connectors:
                connector = connectors[0]
            else:
                raise e

        probe_data = {'query': query}
        probe_result = await self.client.probe_connector(str(connector['id']), probe_data)

        for item in probe_result['result']:
            yield item
