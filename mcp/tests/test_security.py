"""
Tests for MCP Security

This module contains tests for the MCP security components,
including authentication, authorization, and RBAC functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch
from jose import JWTError
from ..src.security.auth import verify_token
from ..src.security.rbac import check_permissions, _get_required_role, _is_side_effect_allowed
from ..src.gateway.config import OIDCConfig, ToolConfig
from ..src.tools.base import SideEffect


@pytest.fixture
def oidc_config():
    """Create a test OIDC configuration"""
    return OIDCConfig(
        issuer="https://test.issuer.com",
        audience="test-audience",
        jwks_url="https://test.issuer.com/.well-known/jwks.json"
    )


@pytest.fixture
def user_claims():
    """Create test user claims"""
    return {
        "sub": "user123",
        "name": "Test User",
        "roles": ["support.agent"],
        "aud": "test-audience",
        "iss": "https://test.issuer.com"
    }


def test_verify_token_valid(oidc_config):
    """Test token verification with valid token"""
    # This is a simplified test since we're not actually verifying tokens in the mock
    auth_header = "Bearer test.token"
    claims = verify_token(auth_header, oidc_config)
    assert "sub" in claims
    assert "roles" in claims


def test_verify_token_invalid_header(oidc_config):
    """Test token verification with invalid header"""
    auth_header = "Invalid test.token"
    with pytest.raises(JWTError):
        verify_token(auth_header, oidc_config)


def test_verify_token_missing_header(oidc_config):
    """Test token verification with missing header"""
    auth_header = ""
    with pytest.raises(JWTError):
        verify_token(auth_header, oidc_config)


def test_get_required_role():
    """Test getting required roles"""
    role = _get_required_role("jira.create_issue", "write")
    assert role == "support.agent"
    
    role = _get_required_role("kb.search", "read")
    assert role == "support.agent"
    
    role = _get_required_role("unknown.tool", "unknown")
    assert role == "admin"


def test_is_side_effect_allowed():
    """Test side effect permissions"""
    # Read should be allowed for all
    assert _is_side_effect_allowed(SideEffect.READ, ["user"]) == True
    
    # Write should be allowed for support.agent and admin
    assert _is_side_effect_allowed(SideEffect.WRITE, ["support.agent"]) == True
    assert _is_side_effect_allowed(SideEffect.WRITE, ["admin"]) == True
    assert _is_side_effect_allowed(SideEffect.WRITE, ["user"]) == False
    
    # Execute should only be allowed for admin
    assert _is_side_effect_allowed(SideEffect.EXECUTE, ["admin"]) == True
    assert _is_side_effect_allowed(SideEffect.EXECUTE, ["support.agent"]) == False