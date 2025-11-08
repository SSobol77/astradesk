"""
MCP Tool Base Classes

This module defines the base classes for MCP tools.
All tools must inherit from the Tool base class and implement its abstract methods.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum


class SideEffect(str, Enum):
    """Side effect classifications"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"


class ToolResult(BaseModel):
    """Standard tool result format"""
    success: bool = Field(..., description="Whether the tool execution was successful")
    data: Optional[Dict[str, Any]] = Field(None, description="Result data if successful")
    error: Optional[str] = Field(None, description="Error message if failed")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class Tool(ABC):
    """Base class for all MCP tools"""
    
    def __init__(self, name: str, side_effect: SideEffect = SideEffect.READ):
        self.name = name
        self.side_effect = side_effect
    
    @abstractmethod
    async def execute(self, args: Dict[str, Any], claims: Dict[str, Any]) -> ToolResult:
        """
        Execute the tool with given arguments
        
        Args:
            args: Tool arguments
            claims: User claims from JWT
            
        Returns:
            ToolResult with execution result
        """
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """
        Get the JSON schema for this tool
        
        Returns:
            JSON schema as dictionary
        """
        pass
    
    def requires_approval(self) -> bool:
        """
        Check if this tool requires approval for execution
        
        Returns:
            True if tool requires approval, False otherwise
        """
        return self.side_effect in [SideEffect.WRITE, SideEffect.EXECUTE]