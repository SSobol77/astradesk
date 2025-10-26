# SPDX-License-Identifier: Apache-2.0
# services/api-gateway/src/agents/support.py
"""Production-grade Support Agent for AstraDesk.

Handles technical support queries, ticket management, and knowledge base lookup.
Features:
- Hybrid RAG (PostgreSQL 18+ PGVector + Redis BM25)
- LLM-based self-reflection on snippet relevance
- OPA governance (RBAC/ABAC)
- OTel tracing
- Async-native, hardened validation

Author: Siergej Sobolewski
Since: 2025-10-25
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
from typing import Any, Dict, List, Optional

from .base import BaseAgent
from opentelemetry import trace
from runtime import KeywordPlanner, LLMPlanner, Memory, ToolRegistry
from runtime.models import ToolCall
from runtime.policy import policy as opa_policy
from runtime.rag import RAG, RAGSnippet

logger = logging.getLogger(__name__)


def _as_score(value: object) -> Optional[float]:
    """Return value as float score if numeric, otherwise None (handles Exceptions etc.)."""
    if isinstance(value, (int, float)):
        return float(value)
    return None


async def _maybe_await(value: Any) -> Any:
    """Await value if it's awaitable; otherwise return as-is."""
    return await value if inspect.isawaitable(value) else value


async def _authorize(policy: Any, action: str, claims: Dict[str, Any], payload: Dict[str, Any]) -> None:
    """Generic authorizer that supports various PolicyFacade shapes.

    Tries, in order: authorize / enforce / check / evaluate / eval.
    Accepts sync or async functions. Interprets bool or dict results.
    Raises PermissionError on explicit deny, AttributeError if no method exists.
    """
    for name in ("authorize", "enforce", "check", "evaluate", "eval"):
        fn = getattr(policy, name, None)
        if callable(fn):
            res = await _maybe_await(fn(action, claims, payload))
            # Interpret common patterns
            if isinstance(res, bool):
                if res:
                    return
                raise PermissionError(f"OPA denied: {action}")
            if isinstance(res, dict):
                allow = res.get("allow")
                if allow is None:
                    allow = res.get("result")
                if isinstance(allow, bool):
                    if allow:
                        return
                    raise PermissionError(f"OPA denied: {action}")
                # If dict without explicit allow/result -> treat as success
                return
            # If method returns None or other truthy sentinel, treat as success
            return
    raise AttributeError("Policy facade exposes no authorize/enforce/check/evaluate methods")


class SupportAgent(BaseAgent):
    """Support Agent: processes natural language support queries.

    Workflow:
    1. OPA policy check (RBAC + ABAC on user/ticket)
    2. RAG retrieval (KB articles, docs, tickets)
    3. LLM reflection on snippet relevance
    4. Tool planning (create_ticket, search_kb, etc.)
    5. Final response composition
    """

    def __init__(
        self,
        tools: ToolRegistry,
        memory: Memory,
        planner: KeywordPlanner,
        rag: RAG,
        llm_planner: LLMPlanner,
    ) -> None:
        super().__init__(
            tools=tools,
            memory=memory,
            planner=planner,
            rag=rag,
            llm_planner=llm_planner,
            agent_name="support",
        )
        self.tracer = trace.get_tracer(__name__)

    # ----------------------------------------------------------------------- #
    # Core Execution
    # ----------------------------------------------------------------------- #
    async def run(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> tuple[str, List[ToolCall]]:
        """Execute support query with RAG + reflection.

        Args:
            query: User input (e.g., "Problem z VPN").
            context: JWT claims + metadata.

        Returns:
            (response, tool_calls)
        """
        claims = context.get("claims", {}) if context else {}
        user_id = claims.get("user_id", "unknown")

        with self.tracer.start_as_current_span("support.run") as span:
            span.set_attribute("query", query[:100])
            span.set_attribute("user_id", user_id)

            # 1. OPA Governance
            try:
                await _authorize(
                    opa_policy,
                    "support.query",
                    claims,
                    {"query": query, "user_id": user_id},
                )
            except Exception as e:
                span.record_exception(e)
                return f"Access denied: {str(e)}", []

            # 2. RAG Retrieval
            snippets: List[RAGSnippet] = []
            try:
                with self.tracer.start_as_current_span("rag.retrieve"):
                    snippets = await self.rag.retrieve(
                        query=query,
                        agent_name=self.agent_name,
                        k=5,
                        use_reflection=True,
                    )
                span.set_attribute("rag_hits", len(snippets))
            except Exception as e:
                span.record_exception(e)
                logger.warning(f"RAG failed: {e}")

            # 3. Reflection on relevance
            relevant_snippets = await self._reflect_support_context(query, snippets)

            # 4. Planning
            plan = await self._make_plan(query, relevant_snippets, claims)

            # 5. Response
            response = self._compose_response(query, plan, relevant_snippets)
            return response, plan

    # ----------------------------------------------------------------------- #
    # Support Relevance Reflection
    # ----------------------------------------------------------------------- #
    async def _reflect_support_context(
        self, query: str, snippets: List[RAGSnippet]
    ) -> List[RAGSnippet]:
        """Use LLM to score support relevance of each snippet.

        Returns filtered + re-ranked list.
        """
        if not self.llm_planner or not snippets:
            return snippets

        tasks = [self._reflect_support_relevance(query, s.content) for s in snippets]
        scores = await asyncio.gather(*tasks, return_exceptions=True)

        enriched: List[tuple[RAGSnippet, float]] = []
        for snippet, raw_score in zip(snippets, scores):
            score_val = _as_score(raw_score)
            if score_val is not None and score_val >= 0.7:
                snippet.score = score_val  # type: ignore[attr-defined]
                enriched.append((snippet, score_val))

        # Re-rank by reflection score
        enriched.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in enriched[:3]]

    async def _reflect_support_relevance(self, query: str, content: str) -> float:
        """Single snippet reflection via LLM."""
        system = (
            "You are a technical support expert. "
            "Score how well this KB article resolves the query. "
            "Return JSON: {'score': float(0.0-1.0)}. No explanations."
        )
        user = f"Query: {query}\nArticle: {content}"

        try:
            raw: str = await self.llm_planner.chat(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                params={"max_tokens": 50, "temperature": 0.0},
            )
            data = json.loads(raw.strip())
            return max(0.0, min(1.0, float(data.get("score", 0.5))))
        except Exception as e:
            logger.warning(f"Support reflection failed: {e}")
            return 0.5

    # ----------------------------------------------------------------------- #
    # Planning
    # ----------------------------------------------------------------------- #
    async def _make_plan(
        self, query: str, snippets: List[RAGSnippet], claims: Dict[str, Any]
    ) -> List[ToolCall]:
        """Generate tool calls based on query + RAG context."""
        low = query.lower()
        user_id = claims.get("user_id", "unknown")

        if any(k in low for k in ("ticket", "zgłoszenie", "incydent", "create ticket")):
            title = self._extract_ticket_title(query)
            body = self._extract_ticket_body(query)
            return [
                ToolCall(
                    name="create_ticket",
                    arguments={
                        "title": title or query[:80],
                        "body": body or query,
                        "user_id": user_id,
                    },
                )
            ]

        if any(k in low for k in ("status", "sprawdź", "check ticket")):
            ticket_id = self._extract_ticket_id(query)
            if ticket_id:
                return [
                    ToolCall(
                        name="get_ticket_status",
                        arguments={"ticket_id": ticket_id, "user_id": user_id},
                    )
                ]

        # Fallback: search knowledge base
        if snippets:
            return [
                ToolCall(
                    name="search_support_kb",
                    arguments={"query": query, "user_id": user_id},
                )
            ]

        return []

    @staticmethod
    def _extract_ticket_title(query: str) -> Optional[str]:
        import re

        m = re.search(r"(?:tytuł|title)[\s:]*([^\.]+)", query, re.I)
        return m.group(1).strip() if m else None

    @staticmethod
    def _extract_ticket_body(query: str) -> Optional[str]:
        import re

        m = re.search(r"(?:opis|body|description)[\s:]*([^\.]+)", query, re.I)
        return m.group(1).strip() if m else None

    @staticmethod
    def _extract_ticket_id(query: str) -> Optional[str]:
        import re

        m = re.search(r"(?:ticket|zgłoszenie)[\s#:]*([A-Z0-9]{4,20})", query, re.I)
        return m.group(1) if m else None

    # ----------------------------------------------------------------------- #
    # Response Composition
    # ----------------------------------------------------------------------- #
    def _compose_response(
        self, query: str, plan: List[ToolCall], snippets: List[RAGSnippet]
    ) -> str:
        """Build user-facing response."""
        if not plan:
            return (
                "Nie znalazłem dokładnej akcji dla Twojego zapytania supportowego. "
                "Spróbuj: „Utwórz ticket dla problemu z VPN” lub „Sprawdź status ticket TKT-123”."
            )

        lines = ["Oto wynik Twojego zapytania supportowego:", ""]

        for tool in plan:
            if tool.name == "create_ticket":
                lines.append(f"• Tworzę ticket z tytułem: **{tool.arguments.get('title')}**.")
            elif tool.name == "get_ticket_status":
                lines.append(f"• Sprawdzam status ticket **{tool.arguments.get('ticket_id')}**.")
            elif tool.name == "search_support_kb":
                lines.append("• Przeszukuję bazę wiedzy supportowej...")

        if snippets:
            lines.append("")
            lines.append("**Pomocne artykuły z KB:**")
            for s in snippets[:2]:
                preview = s.content.strip().replace("\n", " ")[:200]
                lines.append(f"  - {preview}...")

        return "\n".join(lines)
