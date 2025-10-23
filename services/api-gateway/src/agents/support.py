# SPDX-License-Identifier: Apache-2.0
# services/api-gateway/src/agents/support.py
"""Implementacja agenta wsparcia technicznego (Support).

`SupportAgent` jest wyspecjalizowanym agentem zaprojektowanym do obsługi
zapytań użytkowników, udzielania odpowiedzi na podstawie bazy wiedzy oraz
zarządzania zgłoszeniami w systemach ticketowych.
"""
from __future__ import annotations

from typing import Any, Dict

# ZMIANA: Importy zorganizowane w logiczne grupy
# Importy z własnego projektu
from services.api_gateway.src.agents.base import BaseAgent
from services.api_gateway.src.runtime import (
    KeywordPlanner,
    Memory,
    RAG,
    ToolRegistry,
    ToolCall, # ZMIANA: Importujemy ToolCall
)


class SupportAgent(BaseAgent):
    """Agent zorientowany na wiedzę, z inteligentnym fallbackiem na RAG."""

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
        self, query: str, invoked_tools: list[ToolCall]
    ) -> list[str]:
        """Implementacja strategii kontekstowej dla SupportAgent.

        Strategia tego agenta polega na aktywnym korzystaniu z RAG, chyba że
        została wykonana akcja kończąca, taka jak utworzenie ticketa.

        Args:
            query: Oryginalne zapytanie użytkownika.
            invoked_tools: Lista narzędzi, które zostały pomyślnie wywołane.

        Returns:
            Lista fragmentów kontekstu z RAG lub pusta lista.
        """
        # ZMIANA: Sprawdzamy, czy narzędzie 'create_ticket' zostało wywołane,
        # a nie czy jego wynik zawiera określony tekst. Jest to znacznie
        # bardziej niezawodne i odporne na zmiany.
        ticket_was_created = any(
            tool.name == "create_ticket" for tool in invoked_tools
        )

        # Jeśli interakcja nie jest zakończona (nie utworzono ticketa),
        # użyj RAG, aby znaleźć dodatkowe informacje.
        if not ticket_was_created:
            return await self.rag.retrieve(query, agent_name=self.agent_name, k=4)

        # Gdy ticket został utworzony, nie ma potrzeby dalszego szukania w bazie wiedzy.
        return []
