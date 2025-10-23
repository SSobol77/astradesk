# SPDX-License-Identifier: Apache-2.0
# packages/domain-ops/agents/ops.py

"""Implementacja agenta operacyjnego (SRE/DevOps).

`OpsAgent` jest wyspecjalizowanym agentem zaprojektowanym do wykonywania
zadań administracyjnych i operacyjnych, takich jak pobieranie metryk czy
restartowanie usług.
"""
from __future__ import annotations

from typing import Any, List

from services.api_gateway.src.agents.base import BaseAgent
from services.api_gateway.src.runtime import KeywordPlanner, Memory, RAG, ToolRegistry


class OpsAgent(BaseAgent):
    """Agent do zadań operacyjnych, zorientowany na akcje, bez fallbacku RAG."""

    def __init__(
        self,
        tools: ToolRegistry,
        memory: Memory,
        planner: KeywordPlanner,
        rag: RAG,
    ):
        """Inicjalizuje agenta operacyjnego.

        Args:
            tools: Rejestr dostępnych narzędzi.
            memory: Warstwa pamięci i audytu.
            planner: Planer oparty na słowach kluczowych.
            rag: System RAG (nieużywany aktywnie przez tego agenta).
        """
        super().__init__(
            tools=tools,
            memory=memory,
            planner=planner,
            rag=rag,
            agent_name="ops",
        )

    async def _get_contextual_info(
        self, query: str, tool_results: List[str]
    ) -> List[str]:
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
