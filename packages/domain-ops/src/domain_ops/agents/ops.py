# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: packages/domain-ops/src/domain_ops/agents/ops.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for packages/domain-ops/src/domain_ops/agents/ops.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Implementacja agenta operacyjnego (SRE/DevOps).

`OpsAgent` jest wyspecjalizowanym agentem zaprojektowanym do wykonywania
zadań administracyjnych i operacyjnych, takich jak pobieranie metryk czy
restartowanie usług.
"""

from __future__ import annotations

from typing import Any


class OpsAgent:
    """Agent do zadań operacyjnych, zorientowany na akcje, bez fallbacku RAG."""

    def __init__(
        self,
        tools: Any,
        memory: Any,
        planner: Any,
        rag: Any,
    ) -> None:
        """Inicjalizuje agenta operacyjnego.

        Args:
            tools: Rejestr dostępnych narzędzi.
            memory: Warstwa pamięci i audytu.
            planner: Planer oparty na słowach kluczowych.
            rag: System RAG (nieużywany aktywnie przez tego agenta).
        """
        self.tools = tools
        self.memory = memory
        self.planner = planner
        self.rag = rag
        self.agent_name = 'ops'

    async def _get_contextual_info(self, query: str, tool_results: list[str]) -> list[str]:
        """Implementacja strategii kontekstowej dla OpsAgent.

        Zgodnie ze swoją strategią, ten agent nie korzysta z RAG.
        Zawsze zwraca pustą listę.

        Args:
            query: Oryginalne zapytanie użytkownika.
            tool_results: Wyniki zwrócone przez wykonane narzędzia.

        Returns:
            Pusta lista.
        """
        return []
