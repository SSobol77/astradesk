"""
MCP Exception Classes

This module defines custom exception classes used throughout the MCP implementation.
"""

class MCPException(Exception):
    """Base exception for MCP"""
    pass


class PolicyViolationError(MCPException):
    """Raised when a policy violation occurs"""
    pass


class RateLimitExceededError(MCPException):
    """Raised when rate limit is exceeded"""
    pass