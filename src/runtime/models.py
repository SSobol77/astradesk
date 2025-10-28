"""
Lightweight data models with validation tailored for the unit tests.
"""

from __future__ import annotations

import json
import re
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence

from pydantic import ValidationError

_TOOL_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")
_META_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")


class AstraDeskBaseModel:
    """Simplified stand-in for selected Pydantic behaviours."""

    _max_json_size = 32768

    def _dump(self) -> Dict[str, Any]:
        raise NotImplementedError

    def _ensure_json_size(self) -> None:
        blob = json.dumps(self._dump(), ensure_ascii=False)
        if len(blob.encode("utf-8")) > self._max_json_size:
            raise ValidationError("Model exceeds max JSON size.")

    def model_dump_json(self) -> str:
        self._ensure_json_size()
        return json.dumps(self._dump(), ensure_ascii=False)


class ToolCall(AstraDeskBaseModel):
    def __init__(self, *, name: str, arguments: Optional[Dict[str, Any]] = None, **extra: Any):
        if extra:
            raise ValidationError(f"Unexpected fields: {sorted(extra.keys())}")
        self.name = self._validate_name(name.strip())
        self.arguments = self._validate_arguments(arguments or {})
        self._ensure_json_size()

    @staticmethod
    def _validate_name(value: str) -> str:
        if not (1 <= len(value) <= 128):
            raise ValidationError("Tool name must be between 1 and 128 characters.")
        if not _TOOL_NAME_PATTERN.fullmatch(value):
            raise ValidationError("Tool name contains invalid characters.")
        if value.startswith(".") or value.endswith(".") or ".." in value:
            raise ValidationError("Tool name cannot start/end with '.' or contain consecutive dots.")
        return value

    @staticmethod
    def _validate_arguments(arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            raise ValidationError("arguments must be a dictionary.")
        blob = json.dumps(arguments, ensure_ascii=False)
        if len(blob.encode("utf-8")) > 8192:
            raise ValidationError("Tool arguments exceed 8KB.")
        return arguments

    def _dump(self) -> Dict[str, Any]:
        return {"name": self.name, "arguments": self.arguments}


class AgentName(str, Enum):
    SUPPORT = "support"
    OPS = "ops"


class AgentRequest(AstraDeskBaseModel):
    def __init__(
        self,
        *,
        agent: AgentName,
        input: str,
        meta: Optional[Dict[str, Any]] = None,
        **extra: Any,
    ):
        if extra:
            raise ValidationError(f"Unexpected fields: {sorted(extra.keys())}")
        if not isinstance(agent, AgentName):
            raise ValidationError("agent must be an AgentName.")
        self.agent = agent

        cleaned_input = input.strip()
        if not cleaned_input:
            raise ValidationError("input must not be empty.")
        if len(cleaned_input) > 8192:
            raise ValidationError("input exceeds 8192 characters.")
        if "<script" in cleaned_input.lower():
            raise ValidationError("input contains disallowed HTML.")
        self.input = cleaned_input

        meta = meta or {}
        if not isinstance(meta, dict):
            raise ValidationError("meta must be a dictionary.")
        for key in meta.keys():
            if not isinstance(key, str) or not _META_KEY_PATTERN.fullmatch(key):
                raise ValidationError(f"Invalid meta key: {key!r}")
        self.meta = meta
        self._ensure_json_size()

    def _dump(self) -> Dict[str, Any]:
        return {"agent": self.agent.value, "input": self.input, "meta": self.meta}


class AgentResponse(AstraDeskBaseModel):
    def __init__(
        self,
        *,
        output: str,
        reasoning_trace_id: str,
        invoked_tools: Optional[Sequence[Dict[str, Any] | ToolCall]] = None,
        errors: Optional[Sequence[str]] = None,
        **extra: Any,
    ):
        if extra:
            raise ValidationError(f"Unexpected fields: {sorted(extra.keys())}")

        output_clean = output.strip()
        trace_clean = reasoning_trace_id.strip()
        if not output_clean:
            raise ValidationError("output must not be empty.")
        if not trace_clean:
            raise ValidationError("reasoning_trace_id must not be empty.")
        if len(output_clean) > 20000:
            raise ValidationError("output exceeds 20000 characters.")
        self.output = output_clean
        self.reasoning_trace_id = trace_clean

        tool_objs: List[ToolCall] = []
        for item in invoked_tools or []:
            if isinstance(item, ToolCall):
                tool_objs.append(item)
            elif isinstance(item, dict):
                tool_objs.append(ToolCall(**item))
            else:
                raise ValidationError("invoked_tools entries must be ToolCall or dict.")
        self.invoked_tools = tool_objs if tool_objs else None

        if errors is not None:
            cleaned_errors: List[str] = []
            for err in errors:
                if not isinstance(err, str):
                    raise ValidationError("errors must be a list of strings.")
                cleaned = err.strip()
                if cleaned:
                    cleaned_errors.append(cleaned)
            self.errors = cleaned_errors if cleaned_errors else None
        else:
            self.errors = None
        self._ensure_json_size()

    def _dump(self) -> Dict[str, Any]:
        payload = {
            "output": self.output,
            "reasoning_trace_id": self.reasoning_trace_id,
            "invoked_tools": [tool._dump() for tool in self.invoked_tools] if self.invoked_tools else None,
            "errors": self.errors,
        }
        # Remove None entries to align with expected JSON output.
        return {k: v for k, v in payload.items() if v is not None}


__all__ = ["ToolCall", "AgentName", "AgentRequest", "AgentResponse"]
