# SPDX-License-Identifier: Apache-2.0
# services/api-gateway/src/agents/billing.py
"""Production-grade Billing Agent for AstraDesk.

Handles invoice queries, payment status, usage reports, and financial RAG.
Features:
- Hybrid RAG (PostgreSQL 18+ PGVector + Redis BM25)
- LLM-based financial relevance reflection
- OPA governance (RBAC/ABAC)
- OTel tracing
- PyTorch 2.9 embeddings
- Async-native, hardened validation

Author: Siergej Sobolewski
Since: 2025-10-25
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import torch
from opentelemetry import trace

from runtime.models import ToolCall
from runtime.rag import RAG, RAGSnippet
from runtime.policy import policy as opa_policy
from agents.base import BaseAgent

logger = logging.getLogger(__name__)


class BillingAgent(BaseAgent):
    """
    Billing Agent: processes natural language financial queries.

    Workflow:
    1. OPA policy check (RBAC + ABAC on tenant/amount)
    2. RAG retrieval (financial docs, invoices, policies)
    3. LLM reflection on snippet relevance
    4. Tool planning (get_invoice, generate_report, etc.)
    5. Final response composition
    """

    def __init__(
        self,
        rag: RAG,
        llm_planner: Any,  # LLMPlannerProtocol
        tools: Dict[str, Any],
    ) -> None:
        super().__init__(name="billing", tools=tools)
        self.rag = rag
        self.llm_planner = llm_planner
        self.tracer = trace.get_tracer(__name__)

    # ----------------------------------------------------------------------- #
    # Core Execution
    # ----------------------------------------------------------------------- #
    async def run(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> tuple[str, List[ToolCall]]:
        """
        Execute billing query with RAG + reflection.

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

            # 1. OPA Governance
            try:
                opa_policy.authorize(
                    "billing.query",
                    claims,
                    {"query": query, "tenant": tenant},
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
                        agent_name=self.name,
                        k=5,
                        use_reflection=True,
                    )
                span.set_attribute("rag_hits", len(snippets))
            except Exception as e:
                span.record_exception(e)
                logger.warning(f"RAG failed: {e}")

            # 3. Reflection on financial relevance
            relevant_snippets = await self._reflect_financial_context(query, snippets)

            # 4. Planning
            plan = await self._make_plan(query, relevant_snippets, claims)

            # 5. Response
            response = self._compose_response(query, plan, relevant_snippets)
            return response, plan

    # ----------------------------------------------------------------------- #
    # Financial Relevance Reflection
    # ----------------------------------------------------------------------- #
    async def _reflect_financial_context(
        self, query: str, snippets: List[RAGSnippet]
    ) -> List[RAGSnippet]:
        """
        Use LLM to score financial relevance of each snippet.

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
        for snippet, score in zip(snippets, scores):
            if isinstance(score, Exception):
                logger.warning(f"Reflection failed for snippet: {score}")
                continue
            if score >= 0.6:  # Threshold
                snippet.score = score
                enriched.append((snippet, score))

        # Re-rank by reflection score
        enriched.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in enriched[:3]]

    async def _reflect_financial_relevance(self, query: str, content: str) -> float:
        """
        Single snippet reflection via LLM.
        """
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
            data = json.loads(raw.strip())
            return max(0.0, min(1.0, float(data.get("score", 0.5))))
        except Exception as e:
            logger.warning(f"Financial reflection failed: {e}")
            return 0.5

    # ----------------------------------------------------------------------- #
    # Planning
    # ----------------------------------------------------------------------- #
    async def _make_plan(
        self, query: str, snippets: List[RAGSnippet], claims: Dict[str, Any]
    ) -> List[ToolCall]:
        """
        Generate tool calls based on query + RAG context.
        """
        # Simple keyword + RAG heuristic
        low = query.lower()
        tenant = claims.get("tenant", "unknown")

        if any(k in low for k in ("faktura", "invoice", "bill", "płatność")):
            invoice_id = self._extract_invoice_id(query)
            if invoice_id:
                return [
                    ToolCall(
                        name="get_invoice",
                        arguments={"invoice_id": invoice_id, "tenant": tenant},
                    )
                ]

        if any(k in low for k in ("raport", "report", "użycie", "usage")):
            period = self._extract_period(query) or "last_month"
            return [
                ToolCall(
                    name="generate_usage_report",
                    arguments={"period": period, "tenant": tenant},
                )
            ]

        # Fallback: search knowledge base
        if snippets:
            return [
                ToolCall(
                    name="search_billing_kb",
                    arguments={"query": query, "tenant": tenant},
                )
            ]

        return []

    @staticmethod
    def _extract_invoice_id(query: str) -> Optional[str]:
        import re
        m = re.search(r"(?:faktur[ęa]|invoice)[\s#:]*([A-Z0-9]{4,20})", query, re.I)
        return m.group(1) if m else None

    @staticmethod
    def _extract_period(query: str) -> Optional[str]:
        import re
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
    # Response Composition
    # ----------------------------------------------------------------------- #
    def _compose_response(
        self, query: str, plan: List[ToolCall], snippets: List[RAGSnippet]
    ) -> str:
        """
        Build user-facing response.
        """
        if not plan:
            return (
                "Nie znalazłem dokładnej akcji dla Twojego zapytania o rozliczenia. "
                "Spróbuj: „Pokaż fakturę INV-2025-001” lub „Raport użycia za marzec”."
            )

        lines = ["Oto wynik Twojego zapytania finansowego:", ""]

        for tool in plan:
            if tool.name == "get_invoice":
                lines.append(f"• Pobieram fakturę **{tool.arguments.get('invoice_id')}**.")
            elif tool.name == "generate_usage_report":
                lines.append(f"• Generuję raport użycia za okres **{tool.arguments.get('period')}**.")
            elif tool.name == "search_billing_kb":
                lines.append("• Przeszukuję bazę wiedzy finansowej...")

        if snippets:
            lines.append("")
            lines.append("**Kontekst z dokumentów:**")
            for s in snippets[:2]:
                preview = s.content.strip().replace("\n", " ")[:200]
                lines.append(f"  - {preview}...")

        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Asyncio import at bottom to avoid top-level import issues
# --------------------------------------------------------------------------- #
import asyncio
