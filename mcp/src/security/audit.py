"""
MCP Audit Module

This module implements audit logging functionality with support for multiple sinks:
- stdout:// - Print to standard output
- redis:// - Store in Redis with expiration
- http:// or https:// - Send to HTTP endpoint
- kafka:// - Kafka support (planned)
"""

from typing import Dict, Any, Optional
import json
import hashlib
import time
import httpx
import redis.asyncio as redis
from ..gateway.config import AuditConfig


class AuditLogger:
    """Audit logger for MCP operations"""
    
    def __init__(self, config: AuditConfig, redis_client: redis.Redis = None):
        self.config = config
        self.redis_client = redis_client
        self.http_client = httpx.AsyncClient()
        
        # Parse sink configuration
        if config.sink.startswith("kafka://"):
            self.sink_type = "kafka"
            self.sink_target = config.sink[8:]  # Remove "kafka://" prefix
        elif config.sink.startswith("http://") or config.sink.startswith("https://"):
            self.sink_type = "http"
            self.sink_target = config.sink
        elif config.sink.startswith("redis://"):
            self.sink_type = "redis"
            self.sink_target = config.sink[8:]  # Remove "redis://" prefix
        else:
            self.sink_type = "stdout"
            self.sink_target = None
    
    async def log_invocation(
        self,
        tool_name: str,
        args_digest: str,
        result_digest: str,
        claims: Dict[str, Any],
        side_effect: str
    ) -> str:
        """
        Log a successful tool invocation
        
        Args:
            tool_name: Name of the tool
            args_digest: SHA256 digest of arguments
            result_digest: SHA256 digest of result
            claims: User claims from JWT
            side_effect: Side effect class
            
        Returns:
            Audit ID
        """
        audit_event = {
            "audit_id": self._generate_audit_id(),
            "ts": time.time(),
            "tool": {
                "name": tool_name,
                "side_effect": side_effect
            },
            "auth": {
                "actor_type": "user",
                "user_id": claims.get("sub"),
                "roles": claims.get("roles", []),
                "tenant": claims.get("tenant", "default")
            },
            "args_digest": args_digest,
            "result_digest": result_digest,
            "decision": {
                "allow": True
            },
            "latency_ms": 0  # In a real implementation, you would measure this
        }
        
        await self._send_to_sink(audit_event)
        
        return audit_event["audit_id"]
    
    async def log_invocation_failure(
        self,
        tool_name: str,
        args_digest: str,
        error: str,
        claims: Dict[str, Any],
        side_effect: str
    ):
        """
        Log a failed tool invocation
        
        Args:
            tool_name: Name of the tool
            args_digest: SHA256 digest of arguments
            error: Error message
            claims: User claims from JWT
            side_effect: Side effect class
        """
        audit_event = {
            "audit_id": self._generate_audit_id(),
            "ts": time.time(),
            "tool": {
                "name": tool_name,
                "side_effect": side_effect
            },
            "auth": {
                "actor_type": "user",
                "user_id": claims.get("sub"),
                "roles": claims.get("roles", []),
                "tenant": claims.get("tenant", "default")
            },
            "args_digest": args_digest,
            "error": error,
            "decision": {
                "allow": True
            }
        }
        
        await self._send_to_sink(audit_event)
    
    async def log_violation(
        self,
        tool_name: str,
        args: Dict[str, Any],
        claims: Dict[str, Any],
        violation: str
    ):
        """
        Log a policy violation
        
        Args:
            tool_name: Name of the tool
            args: Tool arguments
            claims: User claims from JWT
            violation: Violation description
        """
        args_str = json.dumps(args, sort_keys=True)
        args_digest = hashlib.sha256(args_str.encode()).hexdigest()
        
        audit_event = {
            "audit_id": self._generate_audit_id(),
            "ts": time.time(),
            "tool": {
                "name": tool_name
            },
            "auth": {
                "actor_type": "user",
                "user_id": claims.get("sub"),
                "roles": claims.get("roles", []),
                "tenant": claims.get("tenant", "default")
            },
            "args_digest": args_digest,
            "violation": violation,
            "decision": {
                "allow": False
            }
        }
        
        await self._send_to_sink(audit_event)
    
    async def log_rate_limit_exceeded(
        self,
        tool_name: str,
        claims: Dict[str, Any]
    ):
        """
        Log a rate limit exceeded event
        
        Args:
            tool_name: Name of the tool
            claims: User claims from JWT
        """
        audit_event = {
            "audit_id": self._generate_audit_id(),
            "ts": time.time(),
            "tool": {
                "name": tool_name
            },
            "auth": {
                "actor_type": "user",
                "user_id": claims.get("sub"),
                "roles": claims.get("roles", []),
                "tenant": claims.get("tenant", "default")
            },
            "decision": {
                "allow": False,
                "reason": "rate_limit_exceeded"
            }
        }
        
        await self._send_to_sink(audit_event)
    
    async def _send_to_sink(self, audit_event: Dict[str, Any]):
        """
        Send audit event to the configured sink
        
        Args:
            audit_event: The audit event to send
        """
        if self.sink_type == "stdout":
            print(f"Audit log: {json.dumps(audit_event, indent=2)}")
        elif self.sink_type == "http":
            try:
                await self.http_client.post(
                    self.sink_target,
                    json=audit_event,
                    timeout=5.0
                )
            except Exception as e:
                print(f"Failed to send audit log to HTTP endpoint: {e}")
        elif self.sink_type == "redis" and self.redis_client:
            try:
                key = f"audit:{audit_event['audit_id']}"
                await self.redis_client.setex(
                    key,
                    self.config.retention_days * 24 * 60 * 60,  # Convert days to seconds
                    json.dumps(audit_event)
                )
            except Exception as e:
                print(f"Failed to send audit log to Redis: {e}")
        else:
            # Default to stdout if sink type is not supported
            print(f"Audit log: {json.dumps(audit_event, indent=2)}")
    
    def _generate_audit_id(self) -> str:
        """
        Generate a unique audit ID
        
        Returns:
            Audit ID
        """
        # In a real implementation, you would use a more robust ID generation method
        return f"audit-{int(time.time() * 1000000)}"