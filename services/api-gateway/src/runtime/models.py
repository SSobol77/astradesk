# SPDX-License-Identifier: Apache-2.0
# services/api-gateway/src/runtime/models.py
"""Centralized Pydantic v2 data models for AstraDesk API contracts and internal flows.

Provides **hardened**, production-grade validation with:
- Size limits (DoS protection)
- Regex patterns (XSS/SQLi mitigation)
- Schema-level constraints
- OpenAPI v1.2.0 compliance

Author: Siergej Sobolewski
Since: 2025-10-07
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
    EmailStr,
    HttpUrl,
)

# --------------------------------------------------------------------------- #
# Security Regex Patterns (compiled at import for performance)
# --------------------------------------------------------------------------- #
# Tool name: alphanumeric + . _ - (no spaces, no /)
_TOOL_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")

# Safe string: no control chars, no excessive whitespace
_SAFE_STRING_PATTERN = re.compile(r"^[\p{L}\p{N}\p{P}\p{Z}]+$", re.UNICODE)

# XSS-safe: block common script tags
_XSS_BLOCK_PATTERN = re.compile(r"<(script|iframe|object|embed|link|meta)", re.IGNORECASE)

# Max JSON string size for any field (8KB)
_MAX_FIELD_JSON_SIZE = 8192

# Max total model size (32KB)
_MAX_MODEL_SIZE = 32768


# --------------------------------------------------------------------------- #
# Base Model with Hardened Config
# --------------------------------------------------------------------------- #
class AstraDeskBaseModel(BaseModel):
    """
    Hardened base model with production security defaults.

    - extra="forbid": Reject unknown fields.
    - str_strip_whitespace: Normalize input.
    - populate_by_name: Allow alias usage.
    - frozen: Prevent runtime mutation.
    - validate_assignment: Enforce on setattr.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
        frozen=True,
        validate_assignment=True,
        json_encoders={dict: lambda v: v},
    )

    @model_validator(mode="after")
    def check_total_size(self) -> "AstraDeskBaseModel":
        """Reject models exceeding total serialized size (DoS protection)."""
        try:
            serialized = self.model_dump_json().encode("utf-8")
            if len(serialized) > _MAX_MODEL_SIZE:
                raise ValueError(f"Model exceeds max size ({_MAX_MODEL_SIZE} bytes).")
        except Exception as e:
            raise ValueError(f"Failed to serialize model for size check: {e}")
        return self


# --------------------------------------------------------------------------- #
# Tool & Planning Models
# --------------------------------------------------------------------------- #
class ToolCall(AstraDeskBaseModel):
    """
    Structured tool invocation with strict validation.

    - name: DNS-safe identifier
    - arguments: JSON object, max 8KB
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Unique tool identifier (e.g., 'create_ticket').",
        examples=["create_ticket", "get_metrics"],
    )
    arguments: Dict[str, Any] = Field(
        default_factory=dict,
        description="Tool arguments as JSON object.",
        examples=[{"title": "VPN outage", "body": "Cannot connect"}],
    )

    @field_validator("name")
    @classmethod
    def validate_name_format(cls, v: str) -> str:
        if not _TOOL_NAME_PATTERN.fullmatch(v):
            raise ValueError("Tool name must contain only letters, digits, '.', '_', '-'.")
        if v.startswith(".") or v.endswith(".") or ".." in v:
            raise ValueError("Tool name cannot start/end with '.' or contain '..'.")
        return v

    @field_validator("arguments")
    @classmethod
    def validate_arguments(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if len(str(v).encode("utf-8")) > _MAX_FIELD_JSON_SIZE:
            raise ValueError("Tool arguments exceed 8KB limit.")
        # Recursively validate nested strings
        def _scrub(d):
            for k, val in d.items():
                if isinstance(val, str):
                    if _XSS_BLOCK_PATTERN.search(val):
                        raise ValueError(f"Invalid content in arguments['{k}']: potential XSS.")
                    if not _SAFE_STRING_PATTERN.match(val):
                        raise ValueError(f"Invalid characters in arguments['{k}'].")
                elif isinstance(val, dict):
                    _scrub(val)
                elif isinstance(val, list):
                    for i, item in enumerate(val):
                        if isinstance(item, (str, dict)):
                            if isinstance(item, dict):
                                _scrub(item)
                            elif isinstance(item, str) and _XSS_BLOCK_PATTERN.search(item):
                                raise ValueError(f"Invalid content in arguments list[{i}].")
            return d
        return _scrub(v)


# --------------------------------------------------------------------------- #
# Agent Enums & Contracts
# --------------------------------------------------------------------------- #
class AgentName(str, Enum):
    """Supported agent types (strict enum)."""
    SUPPORT = "support"
    OPS = "ops"
    BILLING = "billing"


class AgentRequest(AstraDeskBaseModel):
    """
    Incoming agent execution request.

    - input: max 8KB, XSS-safe
    - meta: optional, hardened
    """

    agent: AgentName = Field(
        ...,
        description="Target agent.",
        examples=[AgentName.SUPPORT],
    )
    input: str = Field(
        ...,
        min_length=1,
        max_length=8192,
        description="User query in natural language.",
        examples=["Utwórz ticket dla incydentu VPN"],
    )
    meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata (session_id, user_id, tenant).",
        examples=[{"user_id": "alice", "session_id": "sess-123"}],
    )

    @field_validator("input")
    @classmethod
    def validate_input(cls, v: str) -> str:
        if _XSS_BLOCK_PATTERN.search(v):
            raise ValueError("Input contains blocked HTML tags (XSS protection).")
        if not _SAFE_STRING_PATTERN.match(v):
            raise ValueError("Input contains invalid characters.")
        return v

    @field_validator("meta")
    @classmethod
    def validate_meta(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if len(str(v).encode("utf-8")) > _MAX_FIELD_JSON_SIZE:
            raise ValueError("Meta exceeds 8KB limit.")
        # Allow only safe keys: alphanumeric + _
        for k in v.keys():
            if not isinstance(k, str) or not re.fullmatch(r"[a-zA-Z0-9_]+", k):
                raise ValueError(f"Invalid meta key: '{k}'.")
        return v


class AgentResponse(AstraDeskBaseModel):
    """
    Final agent response with audit fields.
    """

    output: str = Field(
        ...,
        min_length=1,
        max_length=20000,
        description="User-facing response.",
        examples=["Ticket #123 created."],
    )
    reasoning_trace_id: str = Field(
        ...,
        min_length=32,
        max_length=256,
        description="OTel trace ID.",
        examples=["trace-b7a3c1e9-f8d2-4e1a-9c3d-8b2f0a1d4e5c"],
    )
    invoked_tools: Optional[List[ToolCall]] = Field(
        default=None,
        description="Executed tools.",
    )
    errors: Optional[List[str]] = Field(
        default=None,
        description="Non-fatal errors.",
        max_items=50,
    )

    @field_validator("output")
    @classmethod
    def validate_output(cls, v: str) -> str:
        if _XSS_BLOCK_PATTERN.search(v):
            raise ValueError("Output contains blocked HTML tags.")
        return v

    @field_validator("reasoning_trace_id")
    @classmethod
    def validate_trace_id(cls, v: str) -> str:
        if not re.fullmatch(r"[0-9a-fA-F-]+", v):
            raise ValueError("Invalid trace ID format (hex + hyphen).")
        return v

    @field_validator("errors")
    @classmethod
    def validate_errors(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        for i, err in enumerate(v):
            if not isinstance(err, str) or len(err) > 1024:
                raise ValueError(f"Error message at index {i} is invalid or too long.")
        return v


# --------------------------------------------------------------------------- #
# RAG & Memory Models
# --------------------------------------------------------------------------- #
class RAGSnippet(AstraDeskBaseModel):
    content: str = Field(..., max_length=4000)
    score: float = Field(..., ge=0.0, le=1.0)
    source: str = Field(..., max_length=64)
    agent_name: Optional[str] = Field(default=None, max_length=64)

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if _XSS_BLOCK_PATTERN.search(v):
            raise ValueError("RAG snippet contains blocked HTML.")
        return v

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        if not _TOOL_NAME_PATTERN.fullmatch(v):
            raise ValueError("Invalid source identifier.")
        return v


class AuditEvent(AstraDeskBaseModel):
    actor: str = Field(..., max_length=256)
    action: str = Field(..., max_length=128)
    payload: Dict[str, Any] = Field(...)

    @field_validator("actor", "action")
    @classmethod
    def validate_actor_action(cls, v: str) -> str:
        if not _SAFE_STRING_PATTERN.match(v):
            raise ValueError(f"Invalid characters in {v}.")
        return v

    @field_validator("payload")
    @classmethod
    def validate_payload(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if len(str(v).encode("utf-8")) > _MAX_FIELD_JSON_SIZE:
            raise ValueError("Audit payload exceeds 8KB.")
        return v


# --------------------------------------------------------------------------- #
# Intent Graph Models
# --------------------------------------------------------------------------- #
class IntentNode(AstraDeskBaseModel):
    id: str = Field(..., max_length=128)
    action: str = Field(..., max_length=128)
    arguments: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list, max_items=50)

    @field_validator("id", "action")
    @classmethod
    def validate_ids(cls, v: str) -> str:
        if not _TOOL_NAME_PATTERN.fullmatch(v):
            raise ValueError("Invalid node ID or action.")
        return v

    @field_validator("dependencies")
    @classmethod
    def validate_deps(cls, v: List[str]) -> List[str]:
        for dep in v:
            if not _TOOL_NAME_PATTERN.fullmatch(dep):
                raise ValueError(f"Invalid dependency ID: '{dep}'.")
        return v


class IntentGraph(AstraDeskBaseModel):
    nodes: List[IntentNode] = Field(..., min_length=1, max_items=100)
    start_node: str = Field(...)

    @field_validator("start_node")
    @classmethod
    def validate_start_node(cls, v: str, info) -> str:
        node_ids = {n.id for n in info.data.get("nodes", [])}
        if v not in node_ids:
            raise ValueError("start_node must reference an existing node ID.")
        return v


# --------------------------------------------------------------------------- #
# OpenAPI v1.2.0 Compliance
# --------------------------------------------------------------------------- #
"""
OpenAPI v1.2.0 Mapping (enhanced with security):

definitions:
  ToolCall:
    type: object
    required: [name]
    properties:
      name:
        type: string
        pattern: ^[a-zA-Z0-9._-]+$
        minLength: 1
        maxLength: 128
      arguments:
        type: object
        additionalProperties: true
        x-max-size: 8192

  AgentRequest:
    type: object
    required: [agent, input]
    properties:
      input:
        type: string
        minLength: 1
        maxLength: 8192
        x-xss-protection: block
"""
