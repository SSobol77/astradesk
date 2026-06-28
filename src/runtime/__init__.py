# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: src/runtime/__init__.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Declares the associated AstraDesk Python package.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Convenience exports for runtime components used in tests."""

from .memory import Memory, AUDIT_SUBJECT
from .models import AgentName, AgentRequest, AgentResponse, ToolCall
from .planner import KeywordPlanner
from .policy import (  # noqa: F401 - re-export for backwards compatibility
    AuthorizationError,
    PolicyError,
    authorize,
    get_roles,
    has_role,
    require_any_role,
    require_all_roles,
    require_role,
)
from .rag import RAG
from .registry import ToolRegistry

__all__ = [
    "Memory",
    "AUDIT_SUBJECT",
    "ToolCall",
    "AgentName",
    "AgentRequest",
    "AgentResponse",
    "KeywordPlanner",
    "AuthorizationError",
    "PolicyError",
    "authorize",
    "get_roles",
    "has_role",
    "require_role",
    "require_any_role",
    "require_all_roles",
    "RAG",
    "ToolRegistry",
]
