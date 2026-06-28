# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: mcp/tests/test_tools.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Verifies AstraDesk behavior for the associated component.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""
Tests for MCP Tools

This module contains tests for the MCP tools and their implementations,
including error handling and validation tests.
"""

import pytest

from mcp.src.clients.jira_client import JiraClient
from mcp.src.clients.kb_client import KnowledgeBaseClient
from mcp.src.tools.base import SideEffect, ToolResult
from mcp.src.tools.jira_tool import JiraTool
from mcp.src.tools.kb_tool import KnowledgeBaseTool


@pytest.fixture
def jira_client():
    """Create a test Jira client"""
    return JiraClient(
        base_url='https://test.atlassian.net', username='testuser', api_token='testtoken'
    )


@pytest.fixture
def jira_tool(jira_client):
    """Create a test Jira tool"""
    return JiraTool(jira_client)


@pytest.fixture
def kb_tool():
    """Create a test knowledge base tool"""
    return KnowledgeBaseTool(KnowledgeBaseClient('https://kb.test'))


def test_jira_tool_initialization(jira_tool):
    """Test Jira tool initialization"""
    assert jira_tool.name == 'jira.create_issue'
    assert jira_tool.side_effect == SideEffect.WRITE
    assert jira_tool.requires_approval() is True


def test_kb_tool_initialization(kb_tool):
    """Test knowledge base tool initialization"""
    assert kb_tool.name == 'kb.search'
    assert kb_tool.side_effect == SideEffect.READ
    assert kb_tool.requires_approval() is False


def test_jira_tool_schema(jira_tool):
    """Test Jira tool schema"""
    schema = jira_tool.get_schema()
    assert schema['title'] == 'jira.create_issue'
    assert 'project' in schema['properties']
    assert 'summary' in schema['properties']


def test_kb_tool_schema(kb_tool):
    """Test knowledge base tool schema"""
    schema = kb_tool.get_schema()
    assert schema['title'] == 'kb.search'
    assert 'q' in schema['properties']
    assert 'top_k' in schema['properties']


@pytest.mark.asyncio
async def test_jira_tool_missing_args(jira_client):
    """Test Jira tool with missing arguments"""
    jira_tool = JiraTool(jira_client)
    result = await jira_tool.execute({}, {})
    assert isinstance(result, ToolResult)
    assert result.success is False
    assert 'Missing required arguments' in result.error


@pytest.mark.asyncio
async def test_kb_tool_missing_query():
    """Test KB tool with missing query"""
    kb_tool = KnowledgeBaseTool(KnowledgeBaseClient('https://kb.test'))
    result = await kb_tool.execute({}, {})
    assert isinstance(result, ToolResult)
    assert result.success is False
    assert 'Missing required argument: q' in result.error
