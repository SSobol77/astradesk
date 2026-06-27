# SPDX-License-Identifier: Apache-2.0
# packages/domain-ops/agents/ops.py

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
