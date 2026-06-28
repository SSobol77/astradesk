# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: mcp/src/clients/jira_client.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for mcp/src/clients/jira_client.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""
Jira Client Implementation

This module provides a client for interacting with Jira through its REST API.
It supports creating and retrieving issues with proper authentication.
"""

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class JiraIssue:
    """Jira issue representation"""

    key: str
    project: str
    summary: str
    url: str


class JiraClient:
    """Client for interacting with Jira"""

    def __init__(self, base_url: str, username: str, api_token: str):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.api_token = api_token
        self.http_client = httpx.AsyncClient(
            auth=(username, api_token), headers={'Content-Type': 'application/json'}
        )

    async def create_issue(
        self,
        project: str,
        summary: str,
        description: str | None = None,
        labels: list[str] | None = None,
    ) -> JiraIssue:
        """
        Create a new Jira issue

        Args:
            project: Project key
            summary: Issue summary
            description: Issue description
            labels: Issue labels

        Returns:
            Created JiraIssue
        """
        # Prepare the request payload
        payload: dict[str, Any] = {
            'fields': {
                'project': {'key': project},
                'summary': summary,
                'issuetype': {'name': 'Task'},
            }
        }

        if description:
            payload['fields']['description'] = description

        if labels:
            payload['fields']['labels'] = [{'add': label} for label in labels]

        # Make HTTP request to Jira API
        response = await self.http_client.post(f'{self.base_url}/rest/api/2/issue/', json=payload)

        response.raise_for_status()
        data = response.json()

        issue_key = data['key']
        url = f'{self.base_url}/browse/{issue_key}'

        return JiraIssue(key=issue_key, project=project, summary=summary, url=url)

    async def get_issue(self, issue_key: str) -> JiraIssue | None:
        """
        Get a Jira issue by key

        Args:
            issue_key: Issue key

        Returns:
            JiraIssue if found, None otherwise
        """
        try:
            # Make HTTP request to Jira API
            response = await self.http_client.get(f'{self.base_url}/rest/api/2/issue/{issue_key}')

            response.raise_for_status()
            data = response.json()

            return JiraIssue(
                key=data['key'],
                project=data['fields']['project']['key'],
                summary=data['fields']['summary'],
                url=f'{self.base_url}/browse/{issue_key}',
            )
        except httpx.HTTPError:
            # Issue not found or other HTTP error
            return None
