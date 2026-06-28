# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: packages/domain-finance/src/domain_finance/tools/erp_oracle.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for packages/domain-finance/src/domain_finance/tools/erp_oracle.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Asynchronous tool for interacting with Oracle ERP via Admin API v1.2.0.
Uses API /connectors for creation and probing, no direct database calls.
Production-ready with async HTTP, error handling, and retry.
"""

from collections.abc import AsyncIterator

from tenacity import retry, stop_after_attempt, wait_exponential

from domain_finance.clients.api import AdminApiClient


class OracleERPAdapter:
    """Async Oracle ERP adapter integrated with Admin API (/connectors)."""

    def __init__(self, api_url: str = 'http://localhost:8080/api/admin/v1', token: str = ''):
        self.client = AdminApiClient(api_url, token)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def fetch_sales(self, query: str) -> AsyncIterator[dict]:
        """Fetch sales data via API /connectors/{id}:probe after creation.

        Steps:
        1. Create or get connector via POST /connectors or GET /connectors.
        2. Probe connector with query via POST /connectors/{id}:probe.

        :param query: SQL-like query for ERP (e.g., "SELECT revenue, date FROM sales").
        :raises ValueError: If API call fails (parsed as ProblemDetail).
        :yield: Dict for each sales record.
        """
        # Step 1: Create or get connector
        connector_data = {
            'name': 'erp_oracle',
            'type': 'db',
            'config': {'dsn': 'oracle://user:pass@host'},
        }
        try:
            connector = await self.client.create_connector(connector_data)
        except ValueError as e:
            connectors = await self.client.list_connectors(name='erp_oracle')
            if connectors:
                connector = connectors[0]
            else:
                raise e

        # Step 2: Probe with query
        probe_data = {'query': query}
        probe_result = await self.client.probe_connector(str(connector['id']), probe_data)

        for item in probe_result['result']:  # Assume result is list of dicts
            yield item
