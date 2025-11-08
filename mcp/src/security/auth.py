"""
MCP Authentication Module

This module handles JWT verification with JWKS caching using Redis.
It provides functions to verify tokens and fetch JWKS with caching.
"""

from typing import Dict, Any
import httpx
from jose import jwt, JWTError
import redis.asyncio as redis
import json
import time
from ..gateway.config import OIDCConfig


async def fetch_jwks(jwks_url: str, redis_client: redis.Redis = None, cache_key: str = None) -> Dict[str, Any]:
    """
    Fetch JWKS from the given URL with Redis caching
    
    Args:
        jwks_url: URL to fetch JWKS from
        redis_client: Redis client for caching
        cache_key: Redis cache key
        
    Returns:
        JWKS as dictionary
    """
    # Try to get from cache first
    if redis_client and cache_key:
        cached_jwks = await redis_client.get(cache_key)
        if cached_jwks:
            return json.loads(cached_jwks)
        
    # Fetch from URL
    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
        jwks = response.json()
        
    # Cache the result
    if redis_client and cache_key:
        await redis_client.setex(cache_key, 3600, json.dumps(jwks))  # Cache for 1 hour
        
    return jwks


async def verify_token(auth_header: str, oidc_config: OIDCConfig, redis_client: redis.Redis = None) -> Dict[str, Any]:
    """
    Verify JWT token from authorization header
    
    Args:
        auth_header: Authorization header value
        oidc_config: OIDC configuration
        redis_client: Redis client for caching JWKS
        
    Returns:
        Decoded token claims
        
    Raises:
        JWTError: If token verification fails
    """
    if not auth_header.startswith("Bearer "):
        raise JWTError("Invalid authorization header")
    
    token = auth_header[7:]  # Remove "Bearer " prefix
    
    # Create cache key for JWKS
    cache_key = f"jwks:{oidc_config.jwks_url}" if redis_client else None
    
    # Fetch JWKS with caching
    jwks = await fetch_jwks(oidc_config.jwks_url, redis_client, cache_key)
    
    # Verify token
    claims = jwt.decode(
        token, 
        jwks, 
        algorithms=["RS256"], 
        audience=oidc_config.audience, 
        issuer=oidc_config.issuer
    )
    
    return claims