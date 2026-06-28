# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: packages/domain-support/src/domain_support/tools/jira_adapter.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for packages/domain-support/src/domain_support/tools/jira_adapter.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

# packages/domain-support/tools/jira_adapter.py
from collections.abc import AsyncIterator

from domain_support.clients.api import AdminApiClient


class JiraAdapter:
    """JIRA client via Admin API."""

    def __init__(self, api_url: str = 'http://localhost:8080/api/admin/v1', token: str = ''):
        self.client = AdminApiClient(api_url, token)

    async def list_tickets(self, jql: str) -> AsyncIterator[dict]:
        """Fetch tickets via /connectors."""
        connector_data = {'name': 'jira', 'type': 'api', 'config': {'jql': jql}}
        connector = await self.client.create_connector(connector_data)
        probe_result = await self.client.probe_connector(str(connector['id']))
        for issue in probe_result['result']:
            yield issue
