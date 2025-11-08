"""
Jira Tool Implementation

This module implements the Jira tool for creating and managing issues.
It uses the JiraClient to interact with the actual Jira service.
"""

from typing import Any, Dict
from .base import Tool, ToolResult, SideEffect
from ..clients.jira_client import JiraClient


class JiraTool(Tool):
    """Jira tool for creating and managing issues"""
    
    def __init__(self, jira_client: JiraClient):
        super().__init__("jira.create_issue", SideEffect.WRITE)
        self.client = jira_client
    
    async def execute(self, args: Dict[str, Any], claims: Dict[str, Any]) -> ToolResult:
        """
        Create a Jira issue
        
        Args:
            args: Arguments containing project, summary, and optional labels
            claims: User claims from JWT
            
        Returns:
            ToolResult with created issue details
        """
        try:
            # Validate required arguments
            project = args.get("project")
            summary = args.get("summary")
            
            if not project or not summary:
                return ToolResult(
                    success=False,
                    error="Missing required arguments: project and summary"
                )
            
            # Create issue using Jira client
            issue = await self.client.create_issue(
                project=project,
                summary=summary,
                labels=args.get("labels", [])
            )
            
            return ToolResult(
                success=True,
                data={
                    "issue_id": issue.key,
                    "project": issue.project,
                    "summary": issue.summary,
                    "url": issue.url
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to create Jira issue: {str(e)}"
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Get the JSON schema for Jira tool
        
        Returns:
            JSON schema as dictionary
        """
        return {
            "$id": "mcp/schemas/jira.create_issue.schema.json",
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "jira.create_issue",
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "minLength": 2,
                    "description": "Jira project key"
                },
                "summary": {
                    "type": "string",
                    "minLength": 3,
                    "description": "Issue summary"
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                    "description": "Issue labels"
                }
            },
            "required": ["project", "summary"],
            "additionalProperties": False
        }