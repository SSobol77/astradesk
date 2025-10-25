# SPDX-License-Identifier: Apache-2.0
# services/api-gateway/src/runtime/planner.py
"""Configurable, deterministic keyword-based planner for AstraDesk.

Serves as a lightweight fallback (or primary) when LLM planner is unavailable or
unnecessary. Maps user queries to structured tool invocations using auditable
rules and produces readable, formatted responses.

Author: Siergej Sobolewski
Since: 2025-10-07
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple, Union

# Local import – fallback to minimal dataclass if not available
try:
    from runtime.models import ToolCall  # type: ignore
except Exception:  # pragma: no cover
    from dataclasses import dataclass as _dc

    @_dc(frozen=True)
    class ToolCall:
        """Minimal ToolCall fallback."""
        name: str
        arguments: Dict[str, Any]


# ---------------------------------------------------------------------------
# Rule Definition
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class KeywordRule:
    """Single keyword-based planning rule."""
    keywords: Set[str]  # Lowercased trigger words/phrases
    tool_name: str     # Tool identifier (e.g., 'create_ticket')
    arg_factory: Callable[[str], Dict[str, Any]]  # Factory to build args from query


# --------------------------------------------------------------------------- #
# Planner Core
# --------------------------------------------------------------------------- #
class KeywordPlanner:
    """
    Minimal, deterministic keyword planner.

    Expected API for BaseAgent:
      - make_plan(query: str) -> List[ToolCall]
      - finalize(query: str, tool_results: Any, context: Dict[str, Any]) -> str
    """

    __slots__ = ("_rules",)

    def __init__(self) -> None:
        """Initialize planner with built-in rules."""
        self._rules: List[KeywordRule] = [
            # Ticket / zgłoszenia
            KeywordRule(
                keywords={
                    "ticket", "bilet", "zgłoszen", "zgłoszenie", "incident",
                    "incydent", "utwórz zgłoszenie", "create ticket", "new ticket"
                },
                tool_name="create_ticket",
                arg_factory=self._ticket_arg_factory,
            ),
            # Metrics / monitoring
            KeywordRule(
                keywords={
                    "metrics", "metryki", "cpu", "memory", "p95", "p99",
                    "latency", "show metrics", "pokaż metryki"
                },
                tool_name="get_metrics",
                arg_factory=self._metrics_arg_factory,
            ),
            # Service restart
            KeywordRule(
                keywords={
                    "restart", "uruchom ponownie", "restart service",
                    "restartuj usługę", "bounce"
                },
                tool_name="restart_service",
                arg_factory=self._restart_arg_factory,
            ),
        ]

    # ----------------------------------------------------------------------- #
    # Plan Generation
    # ----------------------------------------------------------------------- #
    def make_plan(self, query: str) -> List[ToolCall]:
        """
        Generate a deterministic plan based on keyword matching.

        Returns a single-step plan if a rule matches, otherwise falls back to
        default behavior (e.g., create_ticket for long queries).

        Args:
            query: User input.

        Returns:
            List with 0 or 1 ToolCall.
        """
        low = query.lower().strip()
        if not low:
            return []

        for rule in self._rules:
            if any(k in low for k in rule.keywords):
                args = rule.arg_factory(query)
                return [ToolCall(name=rule.tool_name, arguments=args)]

        # Fallback: long query → assume ticket creation
        if len(low) > 12:
            return [
                ToolCall(
                    name="create_ticket",
                    arguments={"title": query[:80], "body": query}
                )
            ]

        return []

    # ----------------------------------------------------------------------- #
    # Finalization (Response Composition)
    # ----------------------------------------------------------------------- #
    def finalize(
        self,
        query: str,
        tool_results: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Compose a user-facing response from tool results and optional RAG context.

        Handles multiple result shapes gracefully:
          - str
          - List[str]
          - Dict[tool_name, str]
          - List[Tuple[tool_name, output]]
          - List[Dict{"name": ..., "output": ...}]

        Falls back to polite message if no useful output.

        Args:
            query: Original user query.
            tool_results: Raw output from tool execution.
            context: Optional RAG snippets or metadata.

        Returns:
            Formatted response string.
        """
        if tool_results is None:
            return self._fallback_for(query)

        # 1. Single string
        if isinstance(tool_results, str):
            return tool_results.strip() or self._fallback_for(query)

        # 2. List of strings
        if isinstance(tool_results, list) and all(
            isinstance(x, str) for x in tool_results
        ):
            lines = ["Oto wyniki akcji:", ""]
            for i, s in enumerate(tool_results, start=1):
                s = (s or "").strip()
                if s:
                    lines.append(f"{i}) {s}")
            return "\n".join(lines) if len(lines) > 2 else self._fallback_for(query)

        # 3. Dict {tool_name: output}
        if isinstance(tool_results, dict) and all(
            isinstance(k, str) for k in tool_results.keys()
        ):
            if all(isinstance(v, str) for v in tool_results.values()):
                lines = ["Podsumowanie wykonanych kroków:", ""]
                for name, out in tool_results.items():
                    pretty = (out or "").strip()
                    if not pretty:
                        continue
                    lines.append(f"• {name}:")
                    lines.append(pretty)
                    lines.append("")
                txt = "\n".join(lines).strip()
                return txt or self._fallback_for(query)

        # 4. List of (name, output) or dicts
        if isinstance(tool_results, list):
            normalized: List[Tuple[str, str]] = []
            for item in tool_results:
                if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str):
                    normalized.append((item[0], str(item[1] or "")))
                elif isinstance(item, dict):
                    name = str(item.get("name", ""))
                    out = str(
                        item.get("output") or item.get("result") or ""
                    )
                    if name:
                        normalized.append((name, out))

            if normalized:
                lines = ["Podsumowanie wykonanych kroków:", ""]
                for name, out in normalized:
                    out = out.strip()
                    if not out:
                        continue
                    lines.append(f"• {name}:")
                    lines.append(out)
                    lines.append("")
                txt = "\n".join(lines).strip()
                return txt or self._fallback_for(query)

        # 5. Fallback to str() conversion
        try:
            return str(tool_results).strip() or self._fallback_for(query)
        except Exception:  # pragma: no cover
            return self._fallback_for(query)

    # ----------------------------------------------------------------------- #
    # Argument Factories
    # ----------------------------------------------------------------------- #
    @staticmethod
    def _ticket_arg_factory(query: str) -> Dict[str, Any]:
        """Extract title/body for ticket creation."""
        title = query.strip()[:80]
        body = query if len(query) > 80 else ""
        return {"title": title, "body": body}

    @staticmethod
    def _metrics_arg_factory(query: str) -> Dict[str, Any]:
        """Parse service and time window from metrics query."""
        service = _extract_service(query) or "webapp"
        window = _extract_window(query) or "15m"
        return {"service": service, "window": window}

    @staticmethod
    def _restart_arg_factory(query: str) -> Dict[str, Any]:
        """Extract service name for restart."""
        service = _extract_service(query) or "webapp"
        return {"service": service}

    # ----------------------------------------------------------------------- #
    # Fallback Response
    # ----------------------------------------------------------------------- #
    @staticmethod
    def _fallback_for(query: str) -> str:
        """Generate polite fallback message based on query intent."""
        low = query.lower()
        if any(k in low for k in ("ticket", "zgłoszen", "incident")):
            return (
                "Nie znalazłem dokładnej akcji, ale możesz utworzyć zgłoszenie: "
                "“utwórz zgłoszenie <tytuł>”."
            )
        if any(k in low for k in ("metrics", "metryk", "cpu", "p95")):
            return (
                "Nie udało się pobrać metryk. Spróbuj: "
                "“pokaż metryki dla webapp z ostatnich 15m”."
            )
        return (
            "Nie rozpoznałem polecenia. Opisz proszę, co chcesz osiągnąć."
        )


# --------------------------------------------------------------------------- #
# Helper Regex Patterns (compiled at import)
# --------------------------------------------------------------------------- #
_svc_pat = re.compile(
    r"\b(webapp|payments[- ]?api|search[- ]?service|database|db)\b", re.I
)
_win_pat = re.compile(r"\b(\d+)([smhd])\b", re.I)


def _extract_service(q: str) -> Optional[str]:
    """Extract service name from query."""
    m = _svc_pat.search(q)
    if not m:
        return None
    svc = m.group(1).lower().replace(" ", "-")
    if "payments" in svc:
        return "payments-api"
    if "search" in svc:
        return "search-service"
    if svc in ("database", "db"):
        return "database"
    return svc


def _extract_window(q: str) -> Optional[str]:
    """Extract time window (e.g., 15m)."""
    m = _win_pat.search(q)
    return m.group(0).lower() if m else None
