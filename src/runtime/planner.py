"""
Keyword-based planner used by tests to create deterministic ToolCall plans.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from .models import ToolCall


def _match_any(text: str, keywords: Sequence[str]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


@dataclass(frozen=True)
class _Rule:
    name: str
    keywords: Sequence[str]

    def make_call(self, query: str) -> ToolCall:
        if self.name == "create_ticket":
            stripped = query.strip()
            title = stripped[:80]
            return ToolCall(name="create_ticket", arguments={"title": title, "body": stripped})
        if self.name == "get_metrics":
            return ToolCall(name="get_metrics", arguments={"service": "webapp", "window": "15m"})
        return ToolCall(name=self.name, arguments={})


class KeywordPlanner:
    def __init__(self) -> None:
        self.rules: List[_Rule] = [
            _Rule(
                "create_ticket",
                [
                    "ticket",
                    "zgłos",
                    "zglos",  # fallback without diacritics
                    "zgłoś",
                    "incident",
                    "incydent",
                    "zgłoszenie",
                    "bilet serwisowy",
                ],
            ),
            _Rule(
                "get_metrics",
                [
                    "cpu",
                    "latency",
                    "metryk",
                    "p95",
                    "p99",
                    "użycie",
                    "uzycie",  # fallback without diacritics
                    "pamię",
                    "pamie",  # fallback without diacritics
                ],
            ),
        ]

    def make_plan(self, query: str) -> List[ToolCall]:
        if not query or not query.strip():
            return []
        for rule in self.rules:
            if _match_any(query, rule.keywords):
                return [rule.make_call(query)]
        return []

    def finalize(self, *, query: str, tool_results: Sequence[str], rag_context: Sequence[str]) -> str:
        if tool_results:
            lines = ["✅ **Wyniki Działania Narzędzi**"]
            lines.extend(f"- {item}" for item in tool_results)
            return "\n".join(lines)
        if rag_context:
            header = f"ℹ️ **Informacje z Bazy Wiedzy na temat:** *{query.strip()}*"
            body = "\n\n---\n\n".join(rag_context)
            return f"{header}\n\n{body}"
        return "Przepraszam, nie znalazłem żadnych informacji, które mogłyby pomóc."


__all__ = ["KeywordPlanner"]
