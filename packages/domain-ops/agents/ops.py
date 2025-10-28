# SPDX-License-Identifier: Apache-2.0
# packages/domain-ops/agents/ops.py

"""Implementacja agenta operacyjnego (SRE/DevOps).

`OpsAgent` jest wyspecjalizowanym agentem zaprojektowanym do wykonywania
zadań administracyjnych i operacyjnych, takich jak pobieranie metryk czy
restartowanie usług.
"""
from __future__ import annotations

from typing import Any, List

try:
    from services.api_gateway.src.agents.base import BaseAgent  # type: ignore
except Exception:  # pragma: no cover
    class BaseAgent:
        def __init__(self, *, tools, memory, planner, rag, agent_name: str, **kwargs):
            self.tools = tools
            self.memory = memory
            self.planner = planner
            self.rag = rag
            self.agent_name = agent_name

from src.runtime.memory import Memory
from src.runtime.planner import KeywordPlanner
from src.runtime.rag import RAG
from src.runtime.registry import ToolRegistry


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
