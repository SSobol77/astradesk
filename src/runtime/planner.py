# SPDX-License-Identifier: Apache-2.0
"""File: services/gateway-python/src/runtime/planner.py
Project: AstraDesk Framework — API Gateway
Description:
    Configurable, deterministic keyword-based planner used as a fallback (or a
    lightweight primary) when the LLM planner is unavailable or unnecessary.
    Maps user queries to structured tool invocations using simple, auditable
    rules and produces readable, formatted responses.

Author: Siergej Sobolewski
Since: 2025-10-07

Overview
--------
- Rule architecture: plan generation is driven by `KeywordRule` entries
  (keywords → tool name → argument factory).
- Deterministic behavior: no LLM dependency; outputs are predictable and fast.
- Data model alignment: plans are expressed as `ToolCall` from `runtime.models`.
- Human-friendly finalize: composes a clear response from tool results or RAG
  context when no tools produced output.

Responsibilities
----------------
- `make_plan(query) -> List[ToolCall]`
  * Normalize input; select the first matching rule; build tool arguments via
    the rule’s `arg_factory`.
  * Return a single-step plan or an empty list if no rule matches.
- `finalize(query, tool_results, rag_context) -> str`
  * Prefer tool results; fall back to knowledge snippets; otherwise provide a
    polite “no action/answer” message.

Design principles
-----------------
- Keep rules explicit and easy to extend (additive changes, no hidden magic).
- Favor safe defaults in argument factories (trim lengths, sanitize basics).
- Separation of concerns: planning only; execution/rendering done upstream.

Security & safety
-----------------
- Avoid injecting unvalidated user strings into arguments that may reach shell,
  SQL, or network boundaries; let downstream layers validate/escape properly.
- Keep argument factories conservative (length limits, normalization).
- Do not include secrets or PII in generated arguments or messages.

Performance
-----------
- O( |rules| ) matching with simple substring checks; fast and GC-friendly.
- Zero network I/O; suitable for hot paths and as a resilient fallback.

Usage (example)
---------------
>>> planner = KeywordPlanner()
>>> plan = planner.make_plan("Utwórz ticket dla incydentu VPN")
>>> if plan:
...     results = await run_tools(plan)  # external orchestration
...     reply = planner.finalize("Utwórz ticket...", results, rag_context=[])

Notes
-----
- Add new `KeywordRule` entries to expand coverage (e.g., restart service).
- If you need locale-specific matching or stemming, place it inside rules or
  pre-processing; keep the core planner deterministic and auditable.

Notes (PL):
------------
Implementacja konfigurowalnego, heurystycznego planera opartego na słowach kluczowych.

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
- **Bezpieczeństwo**: Unika wstrzykiwania niesprawdzonych danych użytkownika
  do argumentów narzędzi, stosując bezpieczne domyślne wartości i ograniczenia długości.
"""  # noqa: D205

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
