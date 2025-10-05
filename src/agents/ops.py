# src/agents/ops.py
"""Implementacja agenta operacyjnego (SRE/DevOps).

`OpsAgent` jest wyspecjalizowanym agentem zaprojektowanym do wykonywania
zadań administracyjnych i operacyjnych, takich jak pobieranie metryk czy
restartowanie usług.

Strategia działania:
- **Priorytet dla akcji**: Ten agent jest zorientowany na wykonywanie zadań.
  Jego głównym celem jest pomyślne wywołanie narzędzi zdefiniowanych w planie.
- **Brak fallbacku RAG**: W przeciwieństwie do `SupportAgent`, `OpsAgent`
  celowo nie używa systemu RAG jako fallbacku. Jeśli narzędzie nie zostanie
  znalezione lub jego wykonanie się nie powiedzie, agent po prostu raportuje
  ten stan, zamiast próbować odpowiadać na pytania z bazy wiedzy.
"""
from __future__ import annotations

from typing import Any, Dict, List

from agents.base import BaseAgent
from runtime.memory import Memory
from runtime.planner import KeywordPlanner
from runtime.rag import RAG
from runtime.registry import ToolRegistry


class OpsAgent(BaseAgent):
    """Agent do zadań operacyjnych SRE/DevOps."""

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
