# SPDX-License-Identifier: Apache-2.0
"""File: core/src/astradesk_core/exceptions.py

Project: astradesk
Package: astradesk_core

Description:
    Central, production-ready exception taxonomy for the AstraDesk platform.
    Provides a clear hierarchy, standardized error reporting via RFC 7807 Problem
    Details, and rich diagnostic context.

"""

from __future__ import annotations

import secrets
import time
from typing import Any, Dict, Optional


class CoreError(Exception):
    """Base exception for all application-specific errors in the AstraDesk ecosystem."""

    def __init__(
        self, message: str, status_code: int = 500, error_code: Optional[str] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.error_id = f"err_{secrets.token_hex(8)}"
        self.timestamp = time.time()

    def to_problem_detail(self) -> Dict[str, Any]:
        """Generates an RFC 7807-compliant Problem Details dictionary."""
        return {
            "type": f"https://astradesk.com/errors/{self.error_code}",
            "title": self.error_code,
            "status": self.status_code,
            "detail": self.message,
            "instance": self.error_id,
        }

    def __str__(self) -> str:
        return f"{self.error_code}: {self.message} (ID: {self.error_id})"


# --- Configuration & State Errors ---

class ConfigurationError(CoreError):
    """Raised when a required configuration is missing or invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=500, error_code="ConfigurationError")


class InvalidStateError(CoreError):
    """Raised when an operation is attempted in an invalid state."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=409, error_code="InvalidStateError")


# --- Model Gateway Errors ---

class ModelGatewayError(CoreError):
    """Base exception for errors in the Model Gateway layer."""

    def __init__(
        self, message: str, provider: Optional[str] = None, status_code: int = 500
    ) -> None:
        super().__init__(message, status_code, error_code="ModelGatewayError")
        self.provider = provider

    def to_problem_detail(self) -> Dict[str, Any]:
        problem = super().to_problem_detail()
        if self.provider:
            problem["provider"] = self.provider
        return problem


class ProviderTimeoutError(ModelGatewayError):
    """Raised when a request to an LLM provider times out."""

    def __init__(self, message: str, provider: str) -> None:
        super().__init__(message, provider, status_code=504)
        self.error_code = "ProviderTimeoutError"


class ProviderOverloadedError(ModelGatewayError):
    """Raised when an LLM provider is overloaded (e.g., HTTP 429)."""

    def __init__(self, message: str, provider: str) -> None:
        super().__init__(message, provider, status_code=429)
        self.error_code = "ProviderOverloadedError"


class ProviderServerError(ModelGatewayError):
    """Raised for a 5xx error from an LLM provider."""

    def __init__(self, message: str, provider: str) -> None:
        super().__init__(message, provider, status_code=502)
        self.error_code = "ProviderServerError"


class TokenLimitExceededError(ModelGatewayError):
    """Raised when a model's token limit is exceeded."""

    def __init__(self, message: str, provider: str) -> None:
        super().__init__(message, provider, status_code=400)
        self.error_code = "TokenLimitExceededError"


# --- Runtime & Tool Errors ---

class ToolNotFoundError(KeyError, CoreError):
    """Raised when a tool is not found in the registry."""

    def __init__(self, tool_name: str) -> None:
        message = f"Tool '{tool_name}' not found in registry."
        # Note: CoreError is not called with super() here because of MRO with KeyError
        CoreError.__init__(self, message, status_code=404, error_code="ToolNotFoundError")
        self.tool_name = tool_name


class AuthorizationError(PermissionError, CoreError):
    """Raised on failed authorization (RBAC/Policy)."""

    def __init__(self, message: str) -> None:
        # Note: CoreError is not called with super() here because of MRO with PermissionError
        CoreError.__init__(self, message, status_code=403, error_code="AuthorizationError")
