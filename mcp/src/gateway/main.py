"""
Main entry point for MCP Gateway
"""

import os
import yaml
import uvicorn
import redis.asyncio as redis
from .gateway import create_gateway
from .config import GatewayConfig, OIDCConfig, AuditConfig, ToolConfig


def load_config_from_file(config_path: str) -> GatewayConfig:
    """Load configuration from a YAML file"""
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)
    
    # Convert to GatewayConfig object
    return GatewayConfig(**config_data)


def create_default_config() -> GatewayConfig:
    """Create a gateway configuration from environment variables or defaults"""
    # OIDC Configuration
    oidc_issuer = os.getenv("OIDC_ISSUER", "https://dev.issuer.com")
    oidc_audience = os.getenv("OIDC_AUDIENCE", "mcp-gateway")
    oidc_jwks_url = os.getenv("OIDC_JWKS_URL", f"{oidc_issuer}/.well-known/jwks.json")
    
    # Audit Configuration
    audit_sink = os.getenv("AUDIT_SINK", "stdout://")
    audit_hash_algo = os.getenv("AUDIT_HASH_ALGO", "sha256")
    audit_retention_days = int(os.getenv("AUDIT_RETENTION_DAYS", "30"))
    
    # Tool configurations (can be extended)
    tools = [
        ToolConfig(
            name="kb.search",
            mcp_endpoint=os.getenv("KB_SERVICE_URL", "http://kb-service:8000"),
            side_effect="read",
            schema_ref=os.getenv("KB_SCHEMA_REF", "sha256:abc123")
        ),
        ToolConfig(
            name="jira.create_issue",
            mcp_endpoint=os.getenv("JIRA_SERVICE_URL", "http://jira-service:8000"),
            side_effect="write",
            schema_ref=os.getenv("JIRA_SCHEMA_REF", "sha256:def456")
        )
    ]
    
    return GatewayConfig(
        env=os.getenv("ENVIRONMENT", "dev"),
        oidc=OIDCConfig(
            issuer=oidc_issuer,
            audience=oidc_audience,
            jwks_url=oidc_jwks_url
        ),
        tools=tools,
        audit=AuditConfig(
            sink=audit_sink,
            hash_algo=audit_hash_algo,
            retention_days=audit_retention_days
        )
    )


def main():
    """Main entry point"""
    # Load configuration
    config_path = os.getenv("CONFIG_PATH")
    if config_path and os.path.exists(config_path):
        config = load_config_from_file(config_path)
    else:
        config = create_default_config()
    
    # Initialize Redis client
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = redis.from_url(redis_url, decode_responses=True)
    
    gateway = create_gateway(config, redis_client)
    
    uvicorn.run(
        gateway.app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


if __name__ == "__main__":
    main()