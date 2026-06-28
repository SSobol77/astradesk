# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: mcp/src/exceptions.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for mcp/src/exceptions.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""
MCP Exception Classes

This module defines custom exception classes used throughout the MCP implementation.
"""


class MCPException(Exception):
    """Base exception for MCP"""

    pass


class PolicyViolationError(MCPException):
    """Raised when a policy violation occurs"""

    pass


class RateLimitExceededError(MCPException):
    """Raised when rate limit is exceeded"""

    pass
