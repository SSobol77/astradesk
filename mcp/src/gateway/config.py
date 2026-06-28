# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: mcp/src/gateway/config.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for mcp/src/gateway/config.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""
MCP Gateway Configuration

This module defines the Pydantic models for configuring the MCP Gateway.
Configuration can be loaded from environment variables or YAML files.
"""

from pydantic import BaseModel, Field


class OIDCConfig(BaseModel):
    """OIDC configuration for authentication"""

    issuer: str = Field(..., description='OIDC issuer URL')
    audience: str = Field(..., description='Expected audience')
    jwks_url: str = Field(..., description='JWKS URL for token verification')


class RateLimitConfig(BaseModel):
    """Rate limiting configuration"""

    default_rpm: int = 600
    per_tool: dict[str, int] = Field(default_factory=lambda: {}, description='Per-tool rate limits')


class ToolConfig(BaseModel):
    """Tool configuration"""

    name: str = Field(..., description='Tool name')
    mcp_endpoint: str = Field(..., description='MCP endpoint URL')
    side_effect: str = Field(..., description='Side effect class (read|write|execute)')
    schema_ref: str | None = Field(None, description='Schema reference hash')


class AuditConfig(BaseModel):
    """Audit configuration"""

    sink: str = Field(..., description='Audit sink (e.g., kafka://topic)')
    hash_algo: str = Field('sha256', description='Hash algorithm for digests')
    retention_days: int = Field(365, description='Retention period in days')


class GatewayConfig(BaseModel):
    """Main gateway configuration"""

    env: str = Field('dev', description='Environment (dev|stage|prod)')
    oidc: OIDCConfig = Field(..., description='OIDC configuration')
    rate_limits: RateLimitConfig = Field(
        default_factory=lambda: RateLimitConfig(), description='Rate limiting configuration'
    )
    tools: list[ToolConfig] = Field(default_factory=lambda: [], description='Tool configurations')
    audit: AuditConfig = Field(..., description='Audit configuration')
