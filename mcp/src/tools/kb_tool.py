"""
Knowledge Base Tool Implementation

This module implements the knowledge base search tool.
It uses the KnowledgeBaseClient to interact with the actual knowledge base service.
"""

from typing import Any, Dict, List
from .base import Tool, ToolResult, SideEffect
from ..clients.kb_client import KnowledgeBaseClient


class KnowledgeBaseTool(Tool):
    """Knowledge base search tool"""
    
    def __init__(self, kb_client: KnowledgeBaseClient):
        super().__init__("kb.search", SideEffect.READ)
        self.client = kb_client
    
    async def execute(self, args: Dict[str, Any], claims: Dict[str, Any]) -> ToolResult:
        """
        Search the knowledge base
        
        Args:
            args: Arguments containing query and optional top_k
            claims: User claims from JWT
            
        Returns:
            ToolResult with search results
        """
        try:
            query = args.get("q", "")
            top_k = args.get("top_k", 5)
            
            if not query:
                return ToolResult(
                    success=False,
                    error="Missing required argument: q"
                )
            
            # Search using the knowledge base client
            entries = await self.client.search(query, top_k)
            
            # Convert entries to the expected format
            results = []
            for entry in entries:
                results.append({
                    "id": entry.id,
                    "title": entry.title,
                    "content": entry.content,
                    "metadata": entry.metadata
                })
            
            return ToolResult(
                success=True,
                data={
                    "matches": results,
                    "query": query
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to search knowledge base: {str(e)}"
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Get the JSON schema for KB tool
        
        Returns:
            JSON schema as dictionary
        """
        return {
            "$id": "mcp/schemas/kb.search.schema.json",
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "kb.search",
            "type": "object",
            "properties": {
                "q": {
                    "type": "string",
                    "minLength": 2,
                    "description": "Search query"
                },
                "top_k": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 20,
                    "default": 5,
                    "description": "Number of results to return"
                }
            },
            "required": ["q"],
            "additionalProperties": False
        }