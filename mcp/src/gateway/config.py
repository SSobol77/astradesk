"""
MCP Gateway Configuration
"""

import os
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class OIDCConfig(BaseModel):
    """OIDC configuration for authentication"""
    issuer: str = Field(..., description="OIDC issuer URL")
    audience: str = Field(..., description="Expected audience")
    jwks_url: str = Field(..., description="JWKS URL for token verification")


class RateLimitConfig(BaseModel):
    """Rate limiting configuration"""
    default_rpm: int = Field(600, description="Default requests per minute")
    per_tool: Dict[str, int] = Field(default_factory=dict, description="Per-tool rate limits")


class ToolConfig(BaseModel):
    """Tool configuration"""
    name: str = Field(..., description="Tool name")
    mcp_endpoint: str = Field(..., description="MCP endpoint URL")
    side_effect: str = Field(..., description="Side effect class (read|write|execute)")
    schema_ref: Optional[str] = Field(None, description="Schema reference hash")


class AuditConfig(BaseModel):
    """Audit configuration"""
    sink: str = Field(..., description="Audit sink (e.g., kafka://topic)")
    hash_algo: str = Field("sha256", description="Hash algorithm for digests")
    retention_days: int = Field(365, description="Retention period in days")


class GatewayConfig(BaseModel):
    """Main gateway configuration"""
    env: str = Field("dev", description="Environment (dev|stage|prod)")
    oidc: OIDCConfig = Field(..., description="OIDC configuration")
    rate_limits: RateLimitConfig = Field(default_factory=RateLimitConfig, description="Rate limiting configuration")
    tools: List[ToolConfig] = Field(default_factory=list, description="Tool configurations")
    audit: AuditConfig = Field(..., description="Audit configuration")