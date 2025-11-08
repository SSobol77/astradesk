"""
MCP RBAC (Role-Based Access Control) Module

This module implements role-based access control for MCP tools.
It checks if a user has permissions to execute a specific tool with a given side effect.
"""

from typing import Dict, Any
from ..gateway.config import ToolConfig
from ..tools.base import SideEffect
from ..exceptions import PolicyViolationError


async def check_permissions(
    claims: Dict[str, Any],
    tool_config: ToolConfig,
    side_effect: str
) -> None:
    """
    Check if user has permissions to execute the tool
    
    Args:
        claims: User claims from JWT
        tool_config: Tool configuration
        side_effect: Requested side effect
        
    Raises:
        PolicyViolationError: If user doesn't have required permissions
    """
    # Extract user roles from claims
    user_roles = []
    if isinstance(claims.get("roles"), list):
        user_roles = [str(role).lower() for role in claims["roles"]]
    elif isinstance(claims.get("roles"), str):
        user_roles = [claims["roles"].lower()]
    
    # Check if user has required role for this tool
    # In a real implementation, you would have more sophisticated RBAC rules
    required_role = _get_required_role(tool_config.name, side_effect)
    
    if required_role and required_role not in user_roles:
        raise PolicyViolationError(
            f"User lacks required role '{required_role}' for tool '{tool_config.name}' "
            f"with side effect '{side_effect}'"
        )
    
    # Check side effect permissions
    if not _is_side_effect_allowed(side_effect, user_roles):
        raise PolicyViolationError(
            f"User not allowed to perform '{side_effect}' operations"
        )


def _get_required_role(tool_name: str, side_effect: str) -> str:
    """
    Get required role for a tool and side effect
    
    Args:
        tool_name: Name of the tool
        side_effect: Side effect class
        
    Returns:
        Required role
    """
    # In a real implementation, this would be configurable
    # For now, we'll use simple rules
    if tool_name == "jira.create_issue" and side_effect == "write":
        return "support.agent"
    elif tool_name == "kb.search" and side_effect == "read":
        return "support.agent"
    else:
        return "admin"


def _is_side_effect_allowed(side_effect: str, user_roles: list) -> bool:
    """
    Check if side effect is allowed for user roles
    
    Args:
        side_effect: Side effect class
        user_roles: User roles
        
    Returns:
        True if allowed, False otherwise
    """
    # In a real implementation, this would be more sophisticated
    # For now, we'll use simple rules:
    # - All users can perform read operations
    # - Only support.agent and higher can perform write operations
    # - Only admin can perform execute operations
    
    if side_effect == SideEffect.READ:
        return True
    elif side_effect == SideEffect.WRITE:
        return any(role in user_roles for role in ["support.agent", "admin"])
    elif side_effect == SideEffect.EXECUTE:
        return "admin" in user_roles
    else:
        return False