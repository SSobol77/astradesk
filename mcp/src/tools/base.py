# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: mcp/src/tools/base.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for mcp/src/tools/base.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""
MCP Tool Base Classes

This module defines the base classes for MCP tools.
All tools must inherit from the Tool base class and implement its abstract methods.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SideEffect(str, Enum):
    """Side effect classifications"""

    READ = 'read'
    WRITE = 'write'
    EXECUTE = 'execute'


class ToolResult(BaseModel):
    """Standard tool result format"""

    success: bool = Field(..., description='Whether the tool execution was successful')
    data: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] | None = Field(
        default_factory=lambda: {}, description='Additional metadata'
    )


class Tool(ABC):
    """Base class for all MCP tools"""

    def __init__(self, name: str, side_effect: SideEffect = SideEffect.READ):
        self.name = name
        self.side_effect = side_effect

    @abstractmethod
    async def execute(self, args: dict[str, Any], claims: dict[str, Any]) -> ToolResult:
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
    def get_schema(self) -> dict[str, Any]:
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
