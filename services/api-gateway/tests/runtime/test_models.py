# SPDX-License-Identifier: Apache-2.0
"""Tests for src/runtime/models.py (AstraDesk Pydantic v2 models).

Covers:
- ToolCall name validation (regex, length bounds) and arguments typing.
- AgentName enum values.
- AgentRequest validation: required fields, trimming, max length, meta default.
- AgentResponse validation: required fields, nested ToolCall list, errors optional.
- Base config behavior: extra="forbid", str_strip_whitespace, populate_by_name.
"""

from __future__ import annotations

import json
import string
from typing import Any

import pytest
from pydantic import ValidationError

from src.runtime.models import (
    AgentName,
    AgentRequest,
    AgentResponse,
    ToolCall,
)

# -- ToolCall --

@pytest.mark.parametrize(
    "name",
    [
        "create_ticket",
        "ops.restart_service",
        "metrics-get",
        "A1_b2.C-3",
        "X",  # minimal valid length (>=1)
        "a" * 128,  # max length boundary
    ],
)
def test_toolcall_name_valid(name: str) -> None:
    tc = ToolCall(name=name, arguments={"x": 1})
    assert tc.name == name
    assert tc.arguments == {"x": 1}


@pytest.mark.parametrize(
    "name",
    [
        "",  # empty -> min_length violated
        "a" * 129,  # > 128
        " with spaces ",
        "slash/not_allowed",
        "pipe|not",
        "quotes\"",
        "semicolon;",
        "😊",  # non-ascii allowed? -> not in [a-zA-Z0-9._-]
        "white space",
    ],
)
def test_toolcall_name_invalid(name: str) -> None:
    with pytest.raises(ValidationError):
        ToolCall(name=name, arguments={})


def test_toolcall_arguments_default_is_dict() -> None:
    tc = ToolCall(name="get_metrics")
    assert isinstance(tc.arguments, dict)
    assert tc.arguments == {}


def test_toolcall_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ToolCall(name="n", arguments={}, unexpected="x")  # type: ignore[arg-type]

# -- AgentName enum --

def test_agentname_values() -> None:
    assert AgentName.SUPPORT.value == "support"
    assert AgentName.OPS.value == "ops"
    assert set(item.value for item in AgentName) == {"support", "ops"}

# -- AgentRequest --

def test_agentrequest_minimal_valid() -> None:
    req = AgentRequest(agent=AgentName.SUPPORT, input="Create a VPN ticket")
    assert req.agent == AgentName.SUPPORT
    assert req.input == "Create a VPN ticket"
    assert isinstance(req.meta, dict) and req.meta == {}


def test_agentrequest_trims_input() -> None:
    req = AgentRequest(agent=AgentName.OPS, input="   restart web   \n\t")
    assert req.input == "restart web"


def test_agentrequest_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        AgentRequest(agent=AgentName.SUPPORT, input="x", extra_field="nope")  # type: ignore[arg-type]


def test_agentrequest_input_required_and_bounded() -> None:
    with pytest.raises(ValidationError):
        AgentRequest(agent=AgentName.SUPPORT, input="")  # min_length=1

    # build too long string (> 8192)
    too_long = "x" * 8193
    with pytest.raises(ValidationError):
        AgentRequest(agent=AgentName.SUPPORT, input=too_long)


def test_agentrequest_meta_roundtrip_json() -> None:
    req = AgentRequest(agent=AgentName.SUPPORT, input="ok", meta={"user_id": "alice", "n": 1})
    blob = req.model_dump_json()
    data = json.loads(blob)
    assert data["agent"] == "support"
    assert data["input"] == "ok"
    assert data["meta"] == {"user_id": "alice", "n": 1}

# -- AgentResponse --

def test_agentresponse_minimal_valid() -> None:
    resp = AgentResponse(output="Ticket created #123", reasoning_trace_id="trace-1")
    assert resp.output == "Ticket created #123"
    assert resp.reasoning_trace_id == "trace-1"
    assert resp.invoked_tools is None
    assert resp.errors is None


def test_agentresponse_trims_output_and_trace_id() -> None:
    resp = AgentResponse(output="  done  \n", reasoning_trace_id="  t-1  ")
    assert resp.output == "done"
    assert resp.reasoning_trace_id == "t-1"


def test_agentresponse_with_nested_toolcalls_from_dicts() -> None:
    # Pydantic should coerce dicts to ToolCall instances
    tools: list[dict[str, Any]] = [
        {"name": "create_ticket", "arguments": {"title": "VPN outage"}},
        {"name": "ops.restart_service", "arguments": {"service": "web"}},
    ]
    resp = AgentResponse(
        output="executed",
        reasoning_trace_id="trace-abc",
        invoked_tools=tools,  # type: ignore[arg-type]
    )
    assert resp.invoked_tools is not None
    assert all(isinstance(t, ToolCall) for t in resp.invoked_tools)
    assert resp.invoked_tools[0].name == "create_ticket"
    assert resp.invoked_tools[1].arguments == {"service": "web"}


def test_agentresponse_errors_optional_and_trimmed() -> None:
    resp = AgentResponse(
        output="ok",
        reasoning_trace_id="t",
        errors=["  minor issue  ", "legacy adapter  "],
    )
    # str_strip_whitespace applies to list[str] members as well
    assert resp.errors == ["minor issue", "legacy adapter"]


def test_agentresponse_bounds_enforced() -> None:
    with pytest.raises(ValidationError):
        AgentResponse(output="", reasoning_trace_id="t")  # output min_length=1
    with pytest.raises(ValidationError):
        AgentResponse(output="ok", reasoning_trace_id="")  # trace id min_length=1

    # Construct very long output (> 20000)
    very_long = "y" * 20001
    with pytest.raises(ValidationError):
        AgentResponse(output=very_long, reasoning_trace_id="t")


def test_agentresponse_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        AgentResponse(output="ok", reasoning_trace_id="t", extra="nope")  # type: ignore[arg-type]


def test_agentresponse_json_roundtrip_invoked_tools() -> None:
    resp = AgentResponse(
        output="OK",
        reasoning_trace_id="r-42",
        invoked_tools=[ToolCall(name="get_metrics", arguments={"ns": "prod"})],
    )
    data = json.loads(resp.model_dump_json())
    assert data["output"] == "OK"
    assert data["reasoning_trace_id"] == "r-42"
    assert data["invoked_tools"][0]["name"] == "get_metrics"
    assert data["invoked_tools"][0]["arguments"] == {"ns": "prod"}


# Extra: stress a bit the allowed characters for ToolCall names
@pytest.mark.parametrize(
    "char",
    list(string.ascii_letters + string.digits + "._-"),
)
def test_toolcall_name_all_allowed_characters(char: str) -> None:
    # Use a short single-character name to validate all allowed symbols individually
    tc = ToolCall(name=char, arguments={})
    assert tc.name == char
