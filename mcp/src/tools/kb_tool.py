# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: mcp/src/tools/kb_tool.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for mcp/src/tools/kb_tool.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""
Knowledge Base Tool Implementation

This module implements the knowledge base search tool.
It uses the KnowledgeBaseClient to interact with the actual knowledge base service.
"""

from typing import Any

from mcp.src.clients.kb_client import KnowledgeBaseClient
from mcp.src.tools.base import SideEffect, Tool, ToolResult


class KnowledgeBaseTool(Tool):
    """Knowledge base search tool"""

    def __init__(self, kb_client: KnowledgeBaseClient):
        super().__init__('kb.search', SideEffect.READ)
        self.client = kb_client

    async def execute(self, args: dict[str, Any], claims: dict[str, Any]) -> ToolResult:
        """
        Search the knowledge base

        Args:
            args: Arguments containing query and optional top_k
            claims: User claims from JWT

        Returns:
            ToolResult with search results
        """
        try:
            query = args.get('q', '')
            top_k = args.get('top_k', 5)

            if not query:
                return ToolResult(success=False, error='Missing required argument: q')

            # Search using the knowledge base client
            entries = await self.client.search(query, top_k)

            # Convert entries to the expected format
            results = []
            for entry in entries:
                results.append(
                    {
                        'id': entry.id,
                        'title': entry.title,
                        'content': entry.content,
                        'metadata': entry.metadata,
                    }
                )

            return ToolResult(success=True, data={'matches': results, 'query': query})
        except Exception as e:
            return ToolResult(success=False, error=f'Failed to search knowledge base: {e!s}')

    def get_schema(self) -> dict[str, Any]:
        """
        Get the JSON schema for KB tool

        Returns:
            JSON schema as dictionary
        """
        return {
            '$id': 'mcp/schemas/kb.search.schema.json',
            '$schema': 'https://json-schema.org/draft/2020-12/schema',
            'title': 'kb.search',
            'type': 'object',
            'properties': {
                'q': {'type': 'string', 'minLength': 2, 'description': 'Search query'},
                'top_k': {
                    'type': 'integer',
                    'minimum': 1,
                    'maximum': 20,
                    'default': 5,
                    'description': 'Number of results to return',
                },
            },
            'required': ['q'],
            'additionalProperties': False,
        }
