# src/runtime/planner.py
# -*- coding: utf-8 -*-
# Program jest objęty licencją Apache-2.0.
# Copyright 2025
# Autor: Siergej Sobolewski
"""Implementacja konfigurowalnego, heurystycznego planera opartego na słowach kluczowych.

Ten moduł dostarcza implementację planera, który pełni rolę "fallbacku"
lub podstawowego mechanizmu decyzyjnego w sytuacji, gdy zaawansowany planer
oparty na LLM jest niedostępny lub nie jest wymagany.

Główne cechy:
- **Architektura oparta na regułach**: Logika planowania jest zdefiniowana jako
  lista konfigurowalnych reguł (`KeywordRule`), co ułatwia rozszerzanie
  i utrzymanie planera.
- **Brak zależności od LLM**: Działa w pełni deterministycznie na podstawie
  zdefiniowanych słów kluczowych i heurystyk.
- **Spójność z modelami danych**: Wykorzystuje model `ToolCall` z `runtime.models`,
  zapewniając spójny kontrakt z resztą systemu.
- **Ustrukturyzowane odpowiedzi**: Metoda `finalize` tworzy czytelne,
  sformatowane odpowiedzi dla użytkownika na podstawie wyników narzędzi i RAG.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Set

from runtime.models import ToolCall

# Typ dla funkcji, która generuje argumenty dla narzędzia na podstawie zapytania.
ArgFactory = Callable[[str], Dict[str, Any]]


@dataclass(frozen=True)
class KeywordRule:
    """Definiuje regułę dopasowania słów kluczowych do wywołania narzędzia.

    Attributes:
        keywords: Zbiór słów kluczowych, które aktywują regułę.
        tool_name: Nazwa narzędzia do wywołania (zgodna z ToolRegistry).
        arg_factory: Funkcja, która tworzy słownik argumentów dla narzędzia.
    """

    keywords: Set[str]
    tool_name: str
    arg_factory: ArgFactory


class KeywordPlanner:
    """Deterministyczny planer oparty na predefiniowanych regułach słów kluczowych.

    Jego zadaniem jest analiza zapytania użytkownika i, na podstawie
    prostych heurystyk, stworzenie planu składającego się z jednego
    wywołania narzędzia (`ToolCall`). Jeśli żadna reguła nie pasuje,
    zwraca pusty plan, sygnalizując potrzebę użycia RAG.
    """

    __slots__ = ("_rules",)

    def __init__(self) -> None:
        """Inicjalizuje planer z predefiniowanym zestawem reguł."""
        self._rules: List[KeywordRule] = [
            # Reguła 1: Tworzenie zgłoszeń (ticketów)
            KeywordRule(
                keywords={"ticket", "bilet", "zgłoś", "zgłoszenie", "incident", "incydent"},
                tool_name="create_ticket",
                arg_factory=lambda query: {
                    "title": query.strip()[:80],  # Bezpieczne obcięcie tytułu
                    "body": query.strip(),
                },
            ),
            # Reguła 2: Pobieranie metryk
            KeywordRule(
                keywords={"metryki", "metryk", "cpu", "pamięć", "latency", "p95", "p99"},
                tool_name="get_metrics",
                arg_factory=lambda _: {
                    "service": "webapp",  # Domyślna usługa
                    "window": "15m",      # Domyślne okno czasowe
                },
            ),
            # Dodaj kolejne reguły tutaj, np. dla restartu usług.
            # KeywordRule(
            #     keywords={"restart", "zrestartuj", "uruchom ponownie"},
            #     tool_name="ops.restart_service",
            #     arg_factory=...
            # ),
        ]

    def make_plan(self, query: str) -> List[ToolCall]:
        """Tworzy plan wykonania na podstawie zapytania użytkownika.

        Iteruje przez zdefiniowane reguły i zwraca plan dla pierwszej
        pasującej reguły.

        Args:
            query: Zapytanie użytkownika.

        Returns:
            Lista zawierająca jeden `ToolCall` lub pusta lista, jeśli
            żadna reguła nie została dopasowana.
        """
        if not query or not query.strip():
            return []

        normalized_query = query.lower()

        for rule in self._rules:
            if any(keyword in normalized_query for keyword in rule.keywords):
                arguments = rule.arg_factory(query)
                return [ToolCall(name=rule.tool_name, arguments=arguments)]

        # Jeśli żadna reguła nie pasuje, zwróć pusty plan.
        return []

    def finalize(
        self, query: str, tool_results: List[str], rag_context: List[str]
    ) -> str:
        """Tworzy finalną, sformatowaną odpowiedź dla użytkownika.

        Priorytetyzuje wyniki narzędzi. Jeśli ich nie ma, używa kontekstu z RAG.
        Jeśli brak jakichkolwiek danych, zwraca grzeczną informację.

        Args:
            query: Oryginalne zapytanie użytkownika.
            tool_results: Lista wyników (jako stringi) zwróconych przez narzędzia.
            rag_context: Lista fragmentów tekstu (kontekst) z systemu RAG.

        Returns:
            Sformatowana, czytelna odpowiedź tekstowa dla użytkownika.
        """
        if tool_results:
            header = "✅ **Wyniki Działania Narzędzi**"
            body = "\n".join(f"- {res}" for res in tool_results)
            return f"{header}\n{body}"

        if rag_context:
            header = f"ℹ️ **Informacje z Bazy Wiedzy na temat:** *{query.strip()}*"
            body = "\n\n---\n\n".join(rag_context)
            return f"{header}\n\n{body}"

        return (
            "Przepraszam, nie udało mi się znaleźć konkretnej odpowiedzi ani "
            "wykonać odpowiedniej akcji na podstawie Twojego zapytania."
        )
