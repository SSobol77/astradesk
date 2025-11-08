"""
Knowledge Base Client Implementation

This module provides a client for interacting with a knowledge base service through HTTP.
It supports searching for entries and retrieving specific entries by ID.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import httpx


@dataclass
class KnowledgeBaseEntry:
    """Knowledge base entry"""
    id: str
    title: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


class KnowledgeBaseClient:
    """Client for interacting with the knowledge base"""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        
        # Setup HTTP client with authentication if provided
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            
        self.http_client = httpx.AsyncClient(headers=headers)
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[KnowledgeBaseEntry]:
        """
        Search the knowledge base
        
        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional filters to apply
            
        Returns:
            List of knowledge base entries
        """
        # Prepare the request payload
        payload = {
            "query": query,
            "top_k": top_k
        }
        
        if filters:
            payload["filters"] = filters
        
        # Make HTTP request to knowledge base API
        response = await self.http_client.post(
            f"{self.base_url}/search",
            json=payload
        )
        
        response.raise_for_status()
        data = response.json()
        
        entries = []
        for item in data.get("results", []):
            entries.append(KnowledgeBaseEntry(
                id=item["id"],
                title=item["title"],
                content=item["content"],
                metadata=item.get("metadata")
            ))
            
        return entries
    
    async def get_entry(self, entry_id: str) -> Optional[KnowledgeBaseEntry]:
        """
        Get a specific knowledge base entry
        
        Args:
            entry_id: Entry ID
            
        Returns:
            KnowledgeBaseEntry if found, None otherwise
        """
        try:
            # Make HTTP request to knowledge base API
            response = await self.http_client.get(
                f"{self.base_url}/entries/{entry_id}"
            )
            
            response.raise_for_status()
            data = response.json()
            
            return KnowledgeBaseEntry(
                id=data["id"],
                title=data["title"],
                content=data["content"],
                metadata=data.get("metadata")
            )
        except httpx.HTTPError:
            # Entry not found or other HTTP error
            return None