# src/agents/base.py
"""Moduł definiujący abstrakcyjną klasę bazową dla wszystkich agentów.

Klasa `BaseAgent` implementuje wspólną, niezmienną logikę cyklu życia
przetwarzania zapytania, w tym:
- Tworzenie planu działania.
- Bezpieczne wykonywanie narzędzi z obsługą błędów.
- Wykorzystanie strategii kontekstowej zdefiniowanej przez klasę pochodną.
- Finalizację odpowiedzi i zapis dialogu.

Dzięki temu, konkretne implementacje agentów (np. `OpsAgent`, `SupportAgent`)
muszą jedynie zdefiniować swoją unikalną strategię, a nie implementować
całą pętlę wykonawczą od nowa.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from runtime.memory import Memory
from runtime.models import ToolCall
from runtime.planner import KeywordPlanner
from runtime.rag import RAG
from runtime.registry import ToolRegistry

logger = logging.getLogger(__name__)


class BaseAgent:
    """Abstrakcyjna klasa bazowa dla agentów."""

    __slots__ = ("tools", "memory", "planner", "rag", "agent_name")

    def __init__(
        self,
        tools: ToolRegistry,
        memory: Memory,
        planner: KeywordPlanner,
        rag: RAG,
        agent_name: str,
    ):
        self.tools = tools
        self.memory = memory
        self.planner = planner
        self.rag = rag
        self.agent_name = agent_name

    async def _get_contextual_info(
        self, query: str, tool_results: List[str]
    ) -> List[str]:
        """Metoda strategii, którą muszą zaimplementować klasy pochodne.

        Decyduje, czy i jak użyć RAG na podstawie wyników narzędzi.

        Args:
            query: Oryginalne zapytanie użytkownika.
            tool_results: Wyniki zwrócone przez wykonane narzędzia.

        Returns:
            Lista fragmentów kontekstu z RAG (może być pusta).
        """
        raise NotImplementedError(
            "Klasa pochodna musi zaimplementować metodę _get_contextual_info"
        )

    async def run(
        self, query: str, context: Dict[str, Any]
    ) -> Tuple[str, List[ToolCall]]:
        """Uruchamia główną pętlę wykonawczą agenta.

        Args:
            query: Zapytanie użytkownika.
            context: Słownik kontekstowy zawierający m.in. 'claims' i 'request_id'.

        Returns:
            Krotka zawierająca (finalna_odpowiedź_tekstowa, lista_wywołanych_narzędzi).
        """
        plan = self.planner.make_plan(query)
        
        tool_results: List[str] = []
        invoked_tools: List[ToolCall] = []

        for step in plan:
            try:
                logger.info(f"Wykonywanie kroku planu: wywołanie narzędzia '{step.name}'")
                # `execute` z ToolRegistry centralnie obsługuje RBAC i wywołanie sync/async
                result = await self.tools.execute(
                    step.name, claims=context.get("claims"), **step.arguments
                )
                tool_results.append(str(result))
                invoked_tools.append(step)
            except PermissionError as e:
                logger.warning(f"Odmowa dostępu do narzędzia '{step.name}': {e}")
                tool_results.append(f"Błąd: Brak uprawnień do użycia narzędzia '{step.name}'.")
            except Exception as e:
                logger.error(
                    f"Wystąpił błąd podczas wykonywania narzędzia '{step.name}'. Błąd: {e}",
                    exc_info=True,
                )
                tool_results.append(f"Błąd: Wystąpił problem podczas użycia narzędzia '{step.name}'.")

        contextual_info = await self._get_contextual_info(query, tool_results)
        
        final_response = self.planner.finalize(query, tool_results, contextual_info)
        
        await self.memory.store_dialogue(self.agent_name, query, final_response, context)
        
        return final_response, invoked_tools
