# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: src/runtime/models.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for src/runtime/models.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Pydantic v2 compatibility models for legacy ``src.runtime`` imports."""

from __future__ import annotations

import json
import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_TOOL_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+$')
_META_KEY_PATTERN = re.compile(r'^[a-zA-Z0-9_]+$')
_MAX_FIELD_JSON_SIZE = 8192
_MAX_MODEL_SIZE = 32768


class AstraDeskBaseModel(BaseModel):
    """Base DTO with strict fields, normalized strings, and a total size bound."""

    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

    @model_validator(mode='after')
    def validate_total_size(self) -> AstraDeskBaseModel:
        if len(self.model_dump_json().encode('utf-8')) > _MAX_MODEL_SIZE:
            raise ValueError(f'Model exceeds max size ({_MAX_MODEL_SIZE} bytes).')
        return self


class ToolCall(AstraDeskBaseModel):
    name: str = Field(min_length=1, max_length=128)
    arguments: dict[str, Any] = Field(default_factory=dict)

    @field_validator('name')
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not _TOOL_NAME_PATTERN.fullmatch(value):
            raise ValueError("Tool name must contain only letters, digits, '.', '_', '-'.")
        return value

    @field_validator('arguments', mode='before')
    @classmethod
    def default_arguments(cls, value: Any) -> Any:
        return {} if value is None else value

    @field_validator('arguments')
    @classmethod
    def validate_arguments(cls, value: dict[str, Any]) -> dict[str, Any]:
        try:
            encoded = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        except (TypeError, ValueError) as exc:
            raise ValueError('Tool arguments must be JSON serializable.') from exc
        if len(encoded) > _MAX_FIELD_JSON_SIZE:
            raise ValueError('Tool arguments exceed 8KB limit.')
        return value


class AgentName(str, Enum):
    SUPPORT = 'support'
    OPS = 'ops'


class AgentRequest(AstraDeskBaseModel):
    agent: AgentName
    input: str = Field(min_length=1, max_length=8192)
    meta: dict[str, Any] = Field(default_factory=dict)

    @field_validator('input')
    @classmethod
    def validate_input(cls, value: str) -> str:
        if '<script' in value.lower():
            raise ValueError('Input contains disallowed HTML.')
        return value

    @field_validator('meta', mode='before')
    @classmethod
    def default_meta(cls, value: Any) -> Any:
        return {} if value is None else value

    @field_validator('meta')
    @classmethod
    def validate_meta(cls, value: dict[str, Any]) -> dict[str, Any]:
        for key in value:
            if not isinstance(key, str) or not _META_KEY_PATTERN.fullmatch(key):
                raise ValueError(f'Invalid meta key: {key!r}.')
        try:
            encoded = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        except (TypeError, ValueError) as exc:
            raise ValueError('Meta must be JSON serializable.') from exc
        if len(encoded) > _MAX_FIELD_JSON_SIZE:
            raise ValueError('Meta exceeds 8KB limit.')
        return value


class AgentResponse(AstraDeskBaseModel):
    output: str = Field(min_length=1, max_length=20000)
    reasoning_trace_id: str = Field(min_length=1, max_length=256)
    invoked_tools: list[ToolCall] | None = None
    errors: list[str] | None = Field(default=None, max_length=50)

    @field_validator('invoked_tools')
    @classmethod
    def normalize_invoked_tools(cls, value: list[ToolCall] | None) -> list[ToolCall] | None:
        return value or None

    @field_validator('errors')
    @classmethod
    def normalize_errors(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized = [error for error in value if error]
        return normalized or None


__all__ = ['ToolCall', 'AgentName', 'AgentRequest', 'AgentResponse']
