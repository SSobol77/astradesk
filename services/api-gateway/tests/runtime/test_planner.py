# SPDX-License-Identifier: Apache-2.0
# services/api-gateway/src/tests/runtime/test_planner.py
"""Tests for src/runtime/planner.py (KeywordPlanner).

Covers:
- make_plan(): keyword matching (case-insensitive, substring-based),
  rule ordering (first match wins), argument factories (trim & title <= 80),
  no-match behavior for empty/irrelevant input.
- finalize(): preference order -> tool_results > rag_context > polite fallback,
  plus formatting checks for headers and list items.

Notes:
- planner.py imports ToolCall from `runtime.models`, while the project usually imports from
  `src.runtime.models`. To avoid class-identity mismatch, we assert on attributes instead of isinstance().

"""

from __future__ import annotations

import re

import pytest

from src.runtime.planner import KeywordPlanner


# make_plan(): ticket rule
@pytest.mark.parametrize(
    "query",
    [
        "Utwórz ticket dla incydentu VPN",
        "  proszę zgłoszenie o dostęp  ",
        "Zgłoś problem z drukarką",
        "Zgłoszenie: bilet serwisowy",
        "Incident: SSO login failure",
        "INCYDENT: API 500",
    ],
)
def test_make_plan_ticket_rule_basic(query: str) -> None:
    planner = KeywordPlanner()
    plan = planner.make_plan(query)
    assert isinstance(plan, list) and len(plan) == 1
    call = plan[0]
    # Duck-typing instead of isinstance (class identity differs across import paths)
    assert getattr(call, "name", None) == "create_ticket"
    assert isinstance(getattr(call, "arguments", None), dict)
    # arg_factory: title is stripped and at most 80 chars, body is stripped
    assert call.arguments["body"] == query.strip()
    assert len(call.arguments["title"]) <= 80
    assert query.strip().startswith(call.arguments["title"])


def test_make_plan_ticket_title_is_truncated_to_80() -> None:
    planner = KeywordPlanner()
    long_payload = "A" * 200
    # MUST include a ticket keyword so the rule triggers
    long_query = "  Zgłoszenie: " + long_payload + "  "
    plan = planner.make_plan(long_query)
    assert plan and getattr(plan[0], "name", None) == "create_ticket"
    title = plan[0].arguments["title"]
    body = plan[0].arguments["body"]
    # Expected title is first 80 chars of stripped input
    stripped = long_query.strip()
    assert title == stripped[:80]
    assert body == stripped


def test_make_plan_ticket_substring_match_polish_inflection() -> None:
    """Keyword 'incydent' should match 'incydentu' by substring rule."""
    planner = KeywordPlanner()
    q = "Proszę utworzyć ticket dla incydentu w sieci"
    plan = planner.make_plan(q)
    assert plan and getattr(plan[0], "name", None) == "create_ticket"


def test_make_plan_ignores_leading_trailing_spaces() -> None:
    planner = KeywordPlanner()
    q = "   zgłoszenie: dostęp do VPN   "
    plan = planner.make_plan(q)
    assert plan and getattr(plan[0], "name", None) == "create_ticket"
    assert plan[0].arguments["body"] == "zgłoszenie: dostęp do VPN"
    assert plan[0].arguments["title"] == "zgłoszenie: dostęp do VPN"[:80]


# make_plan()- metrics rule
@pytest.mark.parametrize("query", ["pokaż cpu", "metryki p95 web", "latency p99", "użycie pamięć 15m"])
def test_make_plan_metrics_rule_basic(query: str) -> None:
    planner = KeywordPlanner()
    plan = planner.make_plan(query)
    assert plan and getattr(plan[0], "name", None) == "get_metrics"
    args = plan[0].arguments
    assert args == {"service": "webapp", "window": "15m"}


def test_make_plan_rule_order_first_match_wins() -> None:
    """If a query contains keywords for multiple rules, the first defined wins (ticket first)."""
    planner = KeywordPlanner()
    q = "Zgłoś ticket i pokaż cpu"
    plan = planner.make_plan(q)
    assert plan and getattr(plan[0], "name", None) == "create_ticket"


# make_plan(): no match / empty inputs
@pytest.mark.parametrize("query", ["", "   ", "brak słów kluczowych tutaj"])
def test_make_plan_no_match_returns_empty(query: str) -> None:
    planner = KeywordPlanner()
    plan = planner.make_plan(query)
    assert plan == []


# finalize() tool_results > rag_context > fallback
def test_finalize_prefers_tool_results_over_rag() -> None:
    planner = KeywordPlanner()
    out = planner.finalize(
        query="pokaż cpu",
        tool_results=["CPU: 42%", "Memory: 1.2GiB"],
        rag_context=["nota o metrykach", "inna nota"],
    )
    # Starts with the tools header and lists items as '- ...'
    assert out.startswith("✅ **Wyniki Działania Narzędzi**")
    assert "- CPU: 42%" in out and "- Memory: 1.2GiB" in out
    # Must not include the RAG header if tool_results present
    assert "ℹ️ **Informacje z Bazy Wiedzy" not in out


def test_finalize_uses_rag_when_no_tool_results() -> None:
    planner = KeywordPlanner()
    out = planner.finalize(
        query="Jak działa SSO?",
        tool_results=[],
        rag_context=["SSO działa na OAuth2/OIDC", "Używa refresh tokenów"],
    )
    assert out.startswith("ℹ️ **Informacje z Bazy Wiedzy na temat:** *Jak działa SSO?*")
    # RAG snippets separated by a markdown divider
    assert re.search(r"SSO działa.*\n\n---\n\n.*Używa refresh tokenów", out, flags=re.S)


def test_finalize_fallback_message_when_nothing_available() -> None:
    planner = KeywordPlanner()
    out = planner.finalize(query="??", tool_results=[], rag_context=[])
    assert "Przepraszam" in out  # polite fallback present
