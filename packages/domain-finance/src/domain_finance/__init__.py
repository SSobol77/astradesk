# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: packages/domain-finance/src/domain_finance/__init__.py
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

"""Finance domain pack discovery contract."""

from __future__ import annotations


class Pack:
    """Discovery adapter for the standalone finance MCP server."""

    name = 'domain_finance'

    def register(self, registry: object) -> None:
        """Preserve discovery without bypassing the MCP policy boundary."""
        if registry is None:
            raise TypeError('registry must not be None')
