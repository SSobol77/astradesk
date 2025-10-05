# src/agents/support.py
"""Implementacja agenta wsparcia technicznego (Support).

`SupportAgent` jest wyspecjalizowanym agentem zaprojektowanym do obsługi
zapytań użytkowników, udzielania odpowiedzi na podstawie bazy wiedzy oraz
zarządzania zgłoszeniami w systemach ticketowych.

Strategia działania:
- **Priorytet dla wiedzy (Knowledge-Oriented)**: Głównym celem tego agenta jest
  dostarczenie użytkownikowi jak najlepszej odpowiedzi.
- **Inteligentny Fallback na RAG**: Agent najpierw próbuje wykonać akcje za pomocą
  narzędzi (np. utworzyć ticket). Jeśli żadne narzędzie nie zostanie użyte,
  lub jeśli wykonane narzędzia nie kończą interakcji (np. nie utworzono ticketa),
  agent aktywnie korzysta z systemu RAG (Retrieval-Augmented Generation),
  aby znaleźć odpowiedź w wewnętrznej bazie wiedzy.
"""
from __future__ import annotations

from typing import Any, Dict, List

from agents.base import BaseAgent
from runtime.memory import Memory
from runtime.planner import KeywordPlanner
from runtime.rag import RAG
from runtime.registry import ToolRegistry


class SupportAgent(BaseAgent):
    """Agent do obsługi zapytań użytkowników i zarządzania zgłoszeniami."""

    def __init__(
        self,
        tools: ToolRegistry,
        memory: Memory,
        planner: KeywordPlanner,
        rag: RAG,
    ):
        """Inicjalizuje agenta wsparcia.

        Args:
            tools: Rejestr dostępnych narzędzi.
            memory: Warstwa pamięci i audytu.
            planner: Planer oparty na słowach kluczowych.
            rag: System RAG do wyszukiwania w bazie wiedzy.
        """
        super().__init__(
            tools=tools,
            memory=memory,
            planner=planner,
            rag=rag,

            agent_name="support",
        )

    async def _get_contextual_info(
        self, query: str, tool_results: List[str]
    ) -> List[str]:
        """Implementacja strategii kontekstowej dla SupportAgent.

        Strategia tego agenta polega na aktywnym korzystaniu z RAG, jeśli
        narzędzia nie dostarczyły ostatecznej odpowiedzi (np. nie utworzono ticketa).

        Args:
            query: Oryginalne zapytanie użytkownika.
            tool_results: Wyniki zwrócone przez wykonane narzędzia.

        Returns:
            Lista fragmentów kontekstu z RAG lub pusta lista.
        """
        # Sprawdzamy, czy którekolwiek z narzędzi zakończyło interakcję
        # (w tym przypadku, czy utworzono ticket).
        is_interaction_complete = any("Utworzono zgłoszenie" in res for res in tool_results)

        # Jeśli interakcja nie jest zakończona, użyj RAG, aby znaleźć dodatkowe informacje.
        if not is_interaction_complete:
            return await self.rag.retrieve(query, k=4)
        
        # Jeśli ticket został utworzony, nie ma potrzeby dalszego szukania w bazie wiedzy.
        return []
