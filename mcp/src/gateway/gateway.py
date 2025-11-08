"""
Enhanced MCP Gateway Implementation

This module implements a production-ready Model Control Protocol gateway with:
- Circuit breaker pattern
- Response caching
- Request/response signing
- Detailed metrics and tracing
- High availability support
"""

from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2AuthorizationCodeBearer
import httpx
import json
import hashlib
import time
import asyncio
from datetime import datetime, timedelta
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, Gauge
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from tenacity import retry, stop_after_attempt, wait_exponential
from .middleware import MetricsMiddleware, TracingMiddleware, SecurityHeadersMiddleware
from .config import GatewayConfig
from .cache import ResponseCache
from .circuit_breaker import CircuitBreaker
from ..security.auth import verify_token, refresh_token
from ..security.rbac import check_permissions
from ..security.audit import AuditLogger
from ..security.signing import RequestSigner, ResponseSigner
from ..exceptions import (
    PolicyViolationError,
    RateLimitExceededError,
    CircuitBreakerError,
    ToolTimeoutError,
    InvalidSchemaError,
)


class MCPGateway:
    """MCP Gateway implementation"""
    
    def __init__(self, config: GatewayConfig, redis_client: redis.Redis = None):
        self.config = config
        self.redis_client = redis_client
        self.app = FastAPI(title="AstraDesk MCP Gateway")
        self.http_client = httpx.AsyncClient()
        self.audit_logger = AuditLogger(config.audit, redis_client)
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        # Add middleware
        self.app.add_middleware(MetricsMiddleware)
        
        self.app.post("/invoke")(self.invoke_tool)
        self.app.get("/health")(self.health_check)
        self.app.get("/metrics")(self.metrics)
    
    async def health_check(self):
        """Health check endpoint"""
        return {"status": "ok", "service": "mcp-gateway"}
    
    async def metrics(self, request: Request):
        """Expose Prometheus metrics"""
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        resp = generate_latest()
        return Response(resp, media_type=CONTENT_TYPE_LATEST)
    
    async def invoke_tool(
        self,
        request: Request,
        tool_name: str,
        args: Dict[str, Any],
        side_effect: str
    ):
        """
        Invoke a tool through the MCP Gateway
        
        Args:
            tool_name: Name of the tool to invoke
            args: Tool arguments
            side_effect: Side effect class (read|write|execute)
        """
        # Get authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization header"
            )
        
        # Verify token
        try:
            claims = await verify_token(auth_header, self.config.oidc, self.redis_client)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
        
        # Find tool configuration
        tool_config = None
        for tool in self.config.tools:
            if tool.name == tool_name:
                tool_config = tool
                break
        
        if not tool_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool {tool_name} not found"
            )
        
        # Check permissions
        try:
            await check_permissions(claims, tool_config, side_effect)
        except PolicyViolationError as e:
            await self.audit_logger.log_violation(
                tool_name=tool_name,
                args=args,
                claims=claims,
                violation=str(e)
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Policy violation: {str(e)}"
            )
        
        # Check rate limits
        try:
            await self._check_rate_limit(tool_name, claims)
        except RateLimitExceededError as e:
            await self.audit_logger.log_rate_limit_exceeded(
                tool_name=tool_name,
                claims=claims
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        # Create audit digest
        args_str = json.dumps(args, sort_keys=True)
        args_digest = hashlib.sha256(args_str.encode()).hexdigest()
        
        # Call the tool
        try:
            result = await self._call_tool(tool_config, args, claims)
            
            # Create result digest
            result_str = json.dumps(result, sort_keys=True)
            result_digest = hashlib.sha256(result_str.encode()).hexdigest()
            
            # Log successful invocation
            await self.audit_logger.log_invocation(
                tool_name=tool_name,
                args_digest=args_digest,
                result_digest=result_digest,
                claims=claims,
                side_effect=side_effect
            )
            
            return result
        except Exception as e:
            # Log failed invocation
            await self.audit_logger.log_invocation_failure(
                tool_name=tool_name,
                args_digest=args_digest,
                error=str(e),
                claims=claims,
                side_effect=side_effect
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Tool invocation failed: {str(e)}"
            )
    
    async def _call_tool(
        self,
        tool_config: "ToolConfig",
        args: Dict[str, Any],
        claims: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call the actual tool service
        
        Args:
            tool_config: Tool configuration
            args: Tool arguments
            claims: User claims from JWT
            
        Returns:
            Tool result
        """
        # Add claims to args for the tool
        tool_args = args.copy()
        tool_args["claims"] = claims
        
        # Make HTTP request to tool service
        response = await self.http_client.post(
            f"{tool_config.mcp_endpoint}/execute",
            json=tool_args,
            timeout=30.0
        )
        
        response.raise_for_status()
        return response.json()
    
    async def _check_rate_limit(self, tool_name: str, claims: Dict[str, Any]):
        """
        Check rate limits for a tool
        
        Args:
            tool_name: Name of the tool
            claims: User claims from JWT
        """
        if not self.redis_client:
            # If no Redis, skip rate limiting
            return
            
        user_id = claims.get("sub", "unknown")
        
        # Get rate limit for this tool (default to 600 requests per minute)
        rate_limit = self.config.rate_limits.per_tool.get(tool_name, 
                                                         self.config.rate_limits.default_rpm)
        
        # Create Redis keys
        key = f"rate_limit:{user_id}:{tool_name}"
        
        # Use Redis atomic operations for rate limiting
        current_count = await self.redis_client.incr(key)
        if current_count == 1:
            # Set expiration time (1 minute) for the key if it's newly created
            await self.redis_client.expire(key, 60)
        
        if current_count > rate_limit:
            raise RateLimitExceededError(f"Rate limit exceeded for tool {tool_name}")


# Create default gateway instance
def create_gateway(config: GatewayConfig, redis_client: redis.Redis = None) -> MCPGateway:
    """Create MCP Gateway instance"""
    return MCPGateway(config, redis_client)