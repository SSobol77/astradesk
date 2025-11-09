# packages/domain-support/tools/mcp_server.py
"""MCP Server for Support Domain Pack"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from .jira_adapter import JiraAdapter
from .asana_adapter import AsanaAdapter
from .slack_adapter import SlackAdapter

logger = logging.getLogger(__name__)

app = FastAPI(title="Support Domain MCP Server", version="1.0.0")

# Initialize adapters
jira_adapter = JiraAdapter()
asana_adapter = AsanaAdapter()
slack_adapter = SlackAdapter()


class ToolRequest(BaseModel):
    """MCP tool request model"""
    tool_name: str
    arguments: Dict[str, Any]
    claims: Optional[Dict[str, Any]] = None


class ToolResponse(BaseModel):
    """MCP tool response model"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@app.post("/execute", response_model=ToolResponse)
async def execute_tool(request: ToolRequest) -> ToolResponse:
    """Execute a tool in the support domain"""
    try:
        if request.tool_name == "jira.list_tickets":
            # Execute JIRA ticket listing
            jql = request.arguments.get("jql", "project=SUPPORT")
            tickets = []
            async for ticket in jira_adapter.list_tickets(jql):
                tickets.append(ticket)
            return ToolResponse(success=True, data={"tickets": tickets})

        elif request.tool_name == "asana.create_task":
            # Execute Asana task creation
            task_data = request.arguments
            result = await asana_adapter.create_task(task_data)
            return ToolResponse(success=True, data=result)

        elif request.tool_name == "slack.post_message":
            # Execute Slack message posting
            message_data = request.arguments
            result = await slack_adapter.post_message(message_data)
            return ToolResponse(success=True, data=result)

        else:
            return ToolResponse(
                success=False,
                error=f"Unknown tool: {request.tool_name}"
            )

    except Exception as e:
        logger.exception(f"Tool execution failed: {request.tool_name}")
        return ToolResponse(
            success=False,
            error=f"Tool execution failed: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "support-mcp-server"}


@app.get("/tools")
async def list_tools():
    """List available tools"""
    return {
        "tools": [
            {
                "name": "jira.list_tickets",
                "description": "List JIRA tickets matching JQL query",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "jql": {"type": "string", "description": "JQL query string"}
                    },
                    "required": ["jql"]
                }
            },
            {
                "name": "asana.create_task",
                "description": "Create a task in Asana",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Task name"},
                        "notes": {"type": "string", "description": "Task notes"},
                        "project_gid": {"type": "string", "description": "Project GID"}
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "slack.post_message",
                "description": "Post a message to Slack",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string", "description": "Slack channel"},
                        "text": {"type": "string", "description": "Message text"}
                    },
                    "required": ["channel", "text"]
                }
            }
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)