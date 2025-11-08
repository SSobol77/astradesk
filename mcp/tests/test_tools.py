"""
Tests for MCP Tools
"""

import pytest
from unittest.mock import AsyncMock, patch
from ..src.tools.jira_tool import JiraTool
from ..src.tools.kb_tool import KnowledgeBaseTool
from ..src.tools.base import SideEffect, ToolResult
from ..src.clients.jira_client import JiraClient


@pytest.fixture
def jira_client():
    """Create a test Jira client"""
    return JiraClient(
        base_url="https://test.atlassian.net",
        username="testuser",
        api_token="testtoken"
    )


@pytest.fixture
def jira_tool(jira_client):
    """Create a test Jira tool"""
    return JiraTool(jira_client)


@pytest.fixture
def kb_tool():
    """Create a test knowledge base tool"""
    return KnowledgeBaseTool()


def test_jira_tool_initialization(jira_tool):
    """Test Jira tool initialization"""
    assert jira_tool.name == "jira.create_issue"
    assert jira_tool.side_effect == SideEffect.WRITE
    assert jira_tool.requires_approval() == True


def test_kb_tool_initialization(kb_tool):
    """Test knowledge base tool initialization"""
    assert kb_tool.name == "kb.search"
    assert kb_tool.side_effect == SideEffect.READ
    assert kb_tool.requires_approval() == False


def test_jira_tool_schema(jira_tool):
    """Test Jira tool schema"""
    schema = jira_tool.get_schema()
    assert schema["title"] == "jira.create_issue"
    assert "project" in schema["properties"]
    assert "summary" in schema["properties"]


def test_kb_tool_schema(kb_tool):
    """Test knowledge base tool schema"""
    schema = kb_tool.get_schema()
    assert schema["title"] == "kb.search"
    assert "q" in schema["properties"]
    assert "top_k" in schema["properties"]


def test_jira_tool_missing_args(jira_client):
    """Test Jira tool with missing arguments"""
    jira_tool = JiraTool(jira_client)
    result = jira_tool.execute({}, {})
    assert isinstance(result, ToolResult)
    assert result.success == False
    assert "Missing required arguments" in result.error


def test_kb_tool_missing_query():
    """Test KB tool with missing query"""
    kb_tool = KnowledgeBaseTool()
    result = kb_tool.execute({}, {})
    assert isinstance(result, ToolResult)
    assert result.success == False
    assert "Missing required argument: q" in result.error