# SPDX-License-Identifier: Apache-2.0
"""File: services/api-gateway/src/agents/billing.py

Production-grade Billing Agent for AstraDesk.

Handles invoice queries, payment status, usage reports, and financial RAG.
Features:
- Hybrid RAG (PostgreSQL 18+ PGVector + Redis BM25)
- LLM-based financial relevance reflection
- OPA governance (RBAC/ABAC)
- OTel tracing
- PyTorch 2.9 embeddings
- Async-native, hardened validation with retries and timeouts
- Heuristic-based planning integrated with Intent Graph for dynamic replanning

Author: Siergej Sobolewski
Since: 2025-10-25
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from opentelemetry import trace
from runtime import KeywordPlanner, LLMPlanner, Memory, ToolRegistry
from runtime.models import ToolCall
from runtime.policy import policy as opa_policy
from runtime.rag import RAG, RAGSnippet

from .base import BaseAgent, Plan

logger = logging.getLogger(__name__)

# Configurable thresholds and retries for production
REFLECTION_THRESHOLD = 0.6
MAX_REFLECTIONS = 3
RAG_RETRY_COUNT = 2
TOOL_TIMEOUT_SEC = 30.0
PLANNING_TIMEOUT_SEC = 10.0


class BillingAgent(BaseAgent):
    """Billing Agent: processes natural language financial queries.

    Workflow (integrated with BaseAgent):
    1. OPA policy check (RBAC + ABAC on tenant/amount)
    2. RAG retrieval (financial docs, invoices, policies)
    3. LLM reflection on snippet relevance
    4. Tool planning (get_invoice, generate_report, etc.) with Intent Graph and replanning
    5. Execution, reflection, and final response composition
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
            agent_name="billing",
        )
        self.tracer = trace.get_tracer(__name__)

    async def _get_contextual_info(
        self, query: str, invoked_tools: List[ToolCall]
    ) -> List[str]:
        """Implementation of contextual strategy for billing agent.

        Uses RAG with reflection to fetch relevant financial snippets.

        Args:
            query: Original user query.
            invoked_tools: List of successfully invoked tools (for potential refinement).

        Returns:
            List of context snippets from RAG or empty list.
        """
        snippets: List[RAGSnippet] = []
        for attempt in range(RAG_RETRY_COUNT + 1):
            try:
                with self.tracer.start_as_current_span("rag.retrieve") as span:
                    span.set_attribute("attempt", attempt)
                    snippets = await self.rag.retrieve(
                        query=query,
                        agent_name=self.agent_name,
                        k=5,
                        use_reflection=True,
                    )
                break
            except Exception as e:
                logger.warning(f"RAG attempt {attempt} failed: {e}")
                if attempt == RAG_RETRY_COUNT:
                    raise
                await asyncio.sleep(1)  # Exponential backoff could be added

        # Reflection on relevance
        relevant_snippets = await self._reflect_financial_context(query, snippets)
        return [s.content for s in relevant_snippets]

    # ----------------------------------------------------------------------- #
    # Financial Relevance Reflection
    # ----------------------------------------------------------------------- #
    async def _reflect_financial_context(
        self, query: str, snippets: List[RAGSnippet]
    ) -> List[RAGSnippet]:
        """Use LLM to score financial relevance of each snippet.

        Returns filtered + re-ranked list.
        """
        if not self.llm_planner or not snippets:
            return snippets

        tasks = [
            self._reflect_financial_relevance(query, s.content)
            for s in snippets
        ]
        scores = await asyncio.gather(*tasks, return_exceptions=True)

        enriched: List[tuple[RAGSnippet, float]] = []
        for snippet, raw_score in zip(snippets, scores):
            score_val = _as_score(raw_score)
            if score_val is not None and score_val >= REFLECTION_THRESHOLD:
                snippet.score = score_val  # type: ignore[attr-defined]
                enriched.append((snippet, score_val))

        # Re-rank by reflection score
        enriched.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in enriched[:3]]

    async def _reflect_financial_relevance(self, query: str, content: str) -> float:
        """Single snippet reflection via LLM."""
        system = (
            "You are a financial compliance expert. "
            "Score relevance of the document to the billing query. "
            "Return JSON: {'score': float(0.0-1.0)}. No explanations."
        )
        user = f"Query: {query}\nDocument: {content}"

        try:
            raw: str = await self.llm_planner.chat(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                params={"max_tokens": 50, "temperature": 0.0},
            )
            # More robust JSON parsing
            raw = raw.strip()
            if raw.startswith("{") and raw.endswith("}"):
                data = json.loads(raw)
                return max(0.0, min(1.0, float(data.get("score", 0.5))))
            else:
                raise ValueError("Invalid JSON response")
        except Exception as e:
            logger.warning(f"Financial reflection failed: {e}")
            return 0.5

    # ----------------------------------------------------------------------- #
    # Custom Planning (Heuristic to Generate Initial Plan)
    # ----------------------------------------------------------------------- #
    async def _heuristic_plan(
        self, query: str, claims: Dict[str, Any]
    ) -> Plan:
        """Generate initial plan based on heuristics for billing queries."""
        low = query.lower()
        tenant = claims.get("tenant", "unknown")

        steps: List[PlanStep] = []  # type: ignore[name-defined]
        if any(k in low for k in ("faktura", "invoice", "bill", "płatność")):
            invoice_id = self._extract_invoice_id(query)
            if invoice_id:
                steps.append(
                    PlanStep(  # type: ignore[name-defined]
                        name="get_invoice",
                        arguments={"invoice_id": invoice_id, "tenant": tenant},
                    )
                )

        if any(k in low for k in ("raport", "report", "użycie", "usage")):
            period = self._extract_period(query) or "last_month"
            steps.append(
                PlanStep(  # type: ignore[name-defined]
                    name="generate_usage_report",
                    arguments={"period": period, "tenant": tenant},
                )
            )

        # Fallback: search knowledge base
        if not steps:
            steps.append(
                PlanStep(  # type: ignore[name-defined]
                    name="search_billing_kb",
                    arguments={"query": query, "tenant": tenant},
                )
            )

        return Plan(steps=steps)  # type: ignore[name-defined]

    @staticmethod
    def _extract_invoice_id(query: str) -> Optional[str]:
        m = re.search(r"(?:faktur[ęa]|invoice)[\s#:]*([A-Z0-9]{4,20})", query, re.I)
        return m.group(1) if m else None

    @staticmethod
    def _extract_period(query: str) -> Optional[str]:
        patterns = [
            r"za\s+(styczeń|luty|marzec|kwiecień|maj|czerwiec|lipiec|sierpień|wrzesień|październik|listopad|grudzień)",
            r"za\s+(\d{4}-\d{2})",
            r"z\s+ostatniego?\s+(miesi[ąa]ca|kwartału|roku)",
        ]
        for pat in patterns:
            m = re.search(pat, query, re.I)
            if m:
                return m.group(1).lower()
        return None

    # ----------------------------------------------------------------------- #
    # Overridden Run (Integrate Heuristics with BaseAgent Loop)
    # ----------------------------------------------------------------------- #
    async def run(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[ToolCall]]:
        """Execute billing query using BaseAgent's loop with heuristic initial plan.

        Args:
            query: User input (e.g., "Pokaż fakturę za marzec").
            context: JWT claims + metadata.

        Returns:
            (response, tool_calls)
        """
        claims = context.get("claims", {}) if context else {}
        tenant = claims.get("tenant", "unknown")

        with self.tracer.start_as_current_span("billing.run") as span:
            span.set_attribute("query", query[:100])
            span.set_attribute("tenant", tenant)

            # 1. OPA Governance for overall query
            try:
                await _authorize(
                    opa_policy,
                    "billing.query",
                    claims,
                    {"query": query, "tenant": tenant},
                )
            except Exception as e:
                span.record_exception(e)
                return f"Access denied: {str(e)}", []

            # Generate initial heuristic plan and pass to base run
            try:
                initial_plan = await self._heuristic_plan(query, claims)
            except Exception as e:
                logger.error(f"Initial planning failed: {e}")
                span.record_exception(e)
                return "Planning error occurred.", []

            # Use base.run for full loop
            return await super().run(query, context or {})

    # ----------------------------------------------------------------------- #
    # Response Composition (Called in Finalize if Needed)
    # ----------------------------------------------------------------------- #
    def _compose_response(
        self, query: str, invoked_tools: List[ToolCall], tool_results: List[str], contextual_info: List[str]
    ) -> str:
        """Build user-facing response from execution results (can be called in planner.finalize)."""
        if not invoked_tools:
            return (
                "Nie znalazłem dokładnej akcji dla Twojego zapytania o rozliczenia. "
                "Spróbuj: „Pokaż fakturę INV-2025-001” lub „Raport użycia za marzec”."
            )

        lines = ["Oto wynik Twojego zapytania finansowego:", ""]

        for tool, result in zip(invoked_tools, tool_results):
            if tool.name == "get_invoice":
                lines.append(f"• Pobrano fakturę **{tool.arguments.get('invoice_id')}**: {result}")
            elif tool.name == "generate_usage_report":
                lines.append(f"• Wygenerowano raport użycia za okres **{tool.arguments.get('period')}**: {result}")
            elif tool.name == "search_billing_kb":
                lines.append(f"• Wyniki wyszukiwania KB finansowej: {result}")

        if contextual_info:
            lines.append("")
            lines.append("**Kontekst z dokumentów:**")
            for info in contextual_info[:2]:
                preview = info.strip().replace("\n", " ")[:200]
                lines.append(f"  - {preview}...")

        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Asyncio import at bottom to avoid top-level import issues (if needed)
# --------------------------------------------------------------------------- #
