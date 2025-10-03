# src/runtime/planner.py
# -*- coding: utf-8 -*-
# Program jest objęty licencją Apache-2.0.
# Copyright 2024
# Autor: Siergej Sobolewski
#
# Cel modułu
# ----------
# Minimalny planer (MVP) dla AstraDesk:
#  - Na podstawie zapytania użytkownika wybiera, które narzędzia (tools) wywołać.
#  - Jeżeli żadne narzędzie nie pasuje, pozostawia decyzję warstwie RAG (pusty plan).
#
# Główne założenia:
#  - Prosty, heurystyczny dobór po słowach-kluczach (bez LLM).
#  - Preferencja narzędzi (np. ticketing, metryki) nad RAG.
#  - Łatwość rozszerzenia (dodawanie nowych reguł/kluczy).
#
# Uwaga:
#  - Ten moduł nie wykonuje narzędzi i nie łączy się z RAG — zwraca tylko plan.
#  - Finalizacja (scalenie wyników tooli / kontekstu RAG) odbywa się w metodzie `finalize`.
#
# Zależności: brak zewnętrznych (czysty Python).

from __future__ import annotations

from typing import Any, Iterable


# -------------------------
# Stałe „tuningowe” planera
# -------------------------

# Heurystyki dla rozpoznawania intencji „ticket”.
KEYWORDS_TICKET: tuple[str, ...] = (
    "ticket", "bilet", "zgłosz", "zgłoszenie", "incident", "incydent", "otwórz zgłoszenie"
)

# Heurystyki dla rozpoznawania intencji „metryki/observability”.
KEYWORDS_METRICS: tuple[str, ...] = (
    "metric", "metryk", "cpu", "latency", "uptime", "availability", "p95", "p99"
)

# Domyślne parametry do narzędzia metryk — proste, ale wystarczające w MVP.
DEFAULT_SERVICE: str = "webapp"
DEFAULT_WINDOW: str = "15m"

# Limit tytułu zgłoszenia (zabezpieczenie przycinające wejście użytkownika).
TITLE_MAX: int = 60


class PlanStep:
    """
    Pojedynczy krok planu — wywołanie konkretnego narzędzia z argumentami.

    Atrybuty:
        tool_name: nazwa narzędzia (identyfikator w ToolRegistry),
        args:      słownik argumentów przekazywanych do narzędzia.
    """

    def __init__(self, tool_name: str, args: dict[str, Any]) -> None:
        if not tool_name:
            raise ValueError("tool_name must not be empty")
        self.tool_name = tool_name
        self.args = args


class Plan:
    """
    Plan wykonania złożony z listy kroków (może być pusty).

    Atrybuty:
        steps: lista kroków (PlanStep) do wykonania przez warstwę agenta.
    """

    def __init__(self, steps: list[PlanStep]) -> None:
        self.steps = steps


class Planner:
    """
    Minimalny planer heurystyczny.

    Zasada działania:
      1) Jeżeli zapytanie sugeruje utworzenie zgłoszenia → `create_ticket`.
      2) Jeżeli zapytanie dotyczy metryk/observability → `get_metrics`.
      3) W przeciwnym razie zwróć pusty plan (agent użyje RAG).

    Przykład:
        planner = Planner()
        plan = await planner.make("Utwórz ticket dla awarii VPN")
        # -> Plan([PlanStep("create_ticket", {...})])
    """

    @staticmethod
    def _contains_any(haystack: str, needles: Iterable[str]) -> bool:
        """
        Zwraca True, jeśli którakolwiek fraza z `needles` występuje w `haystack`.

        Uwaga:
          - Zakłada, że `haystack` jest już znormalizowany (np. lower()).
        """
        return any(w in haystack for w in needles)

    async def make(self, query: str) -> Plan:
        """
        Buduje plan dla zapytania użytkownika.

        Krok po kroku:
          - normalizuje wejście (lowercase),
          - dopasowuje słowa-klucze do zestawów (ticket / metrics),
          - zwraca plan z jednym krokiem (MVP) lub pusty (RAG fallback).

        :param query: treść zapytania użytkownika
        :return: Plan z listą kroków (może być pusta)
        """
        if not query or not query.strip():
            # Pusty input → nic nie planujemy (warstwa wyżej zwróci błąd albo fallback).
            return Plan([])

        ql = query.lower()

        # (1) Intencja „ticket”: utworzenie zgłoszenia w systemie
        if self._contains_any(ql, KEYWORDS_TICKET):
            title = query.strip()[:TITLE_MAX]
            return Plan([PlanStep("create_ticket", {"title": title, "body": query.strip()})])

        # (2) Intencja „metryki”: pobranie metryk dla domyślnej usługi w domyślnym oknie
        if self._contains_any(ql, KEYWORDS_METRICS):
            return Plan([PlanStep("get_metrics", {"service": DEFAULT_SERVICE, "window": DEFAULT_WINDOW})])

        # (3) Brak dopasowania → zostaw RAG/inna logika po stronie agenta
        return Plan([])

    async def finalize(self, query: str, tool_results: list[str], rag_ctx: list[str]) -> str:
        """
        Składa finalną odpowiedź dla użytkownika na podstawie wyników narzędzi
        i/lub kontekstu RAG.

        Heurystyka:
          - Jeśli są wyniki narzędzi → priorytet dla nich (zwracamy listę wyników).
          - W przeciwnym razie, jeśli jest kontekst RAG → złącz i zwróć.
          - Jeśli brak obu → zwróć prosty komunikat MVP.

        :param query: oryginalne zapytanie (pomocne w treści odpowiedzi)
        :param tool_results: lista stringów zwróconych przez narzędzia
        :param rag_ctx: lista stringów (fragmenty dokumentów/odpowiedzi z RAG)
        :return: finalny string do zwrócenia użytkownikowi
        """
        # Wyniki narzędzi (np. nr ticketa / odczyty metryk) — pokazujemy najpierw.
        if tool_results:
            return "Wyniki narzędzi:\n" + "\n".join(tool_results)

        # Fallback na RAG — wyświetlamy złączony kontekst (MVP).
        if rag_ctx:
            return f"Odpowiedź na '{query}'\n\n" + "\n---\n".join(rag_ctx)

        # Ostateczny fallback — brak jakiegokolwiek kontekstu.
        return f"Brak kontekstu; odpowiedź na '{query}': (MVP)"
