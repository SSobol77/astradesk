# SPDX-License-Identifier: Apache-2.0
"""File: services/api-gateway/src/agents/billing.py

Project: astradesk
Pakage: api-gateway

Author: Siergej Sobolewski
Since: 2025-10-29

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

"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

import networkx as nx
from opentelemetry import trace

from runtime import KeywordPlanner, LLMPlanner, Memory, ToolRegistry
from runtime.models import ToolCall
from runtime.policy import policy as opa_policy
from runtime.rag import RAG, RAGSnippet

if TYPE_CHECKING:
    from .base import BaseAgent, Plan, PlanStep

logger = logging.getLogger(__name__)

# Configurable thresholds and retries for production
REFLECTION_THRESHOLD = 0.6
MAX_REFLECTIONS = 3
RAG_RETRY_COUNT = 2
TOOL_TIMEOUT_SEC = 30.0
MAX_GRAPH_NODES = 20


def _as_score(value: object) -> Optional[float]:
    """Return value as float score if numeric, otherwise None."""
    if isinstance(value, (int, float)):
        return float(value)
    return None


async def _maybe_await(value: Any) -> Any:
    """Await value if it's awaitable; otherwise return as-is."""
    return await value if inspect.isawaitable(value) else value


async def _authorize(policy: Any, action: str, claims: Dict[str, Any], payload: Dict[str, Any]) -> None:
    """Generic authorizer that supports various PolicyFacade shapes."""
    for name in ("authorize", "enforce", "check", "evaluate", "eval"):
        fn = getattr(policy, name, None)
        if callable(fn):
            res = await _maybe_await(fn(action, claims, payload))
            if isinstance(res, bool):
                if res:
                    return
                raise PermissionError(f"OPA denied: {action}")
            if isinstance(res, dict):
                allow = res.get("allow") or res.get("result")
                if isinstance(allow, bool):
                    if allow:
                        return
                    raise PermissionError(f"OPA denied: {action}")
                return
            return
    raise AttributeError("Policy facade exposes no authorize/enforce/check/evaluate methods")


class BillingAgent(BaseAgent):
    """Billing Agent: processes natural language financial queries."""

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
        """Implementation of contextual strategy for billing agent."""
        snippets: List[RAGSnippet] = []
        for attempt in range(RAG_RETRY_COUNT + 1):
            try:
                with self.tracer.start_as_current_span("rag.retrieve") as span:
                    span.set_attribute("attempt", attempt)
                    snippets = await self.rag.retrieve(
                        query=query, agent_name=self.agent_name, k=5, use_reflection=True
                    )
                break
            except Exception as e:
                logger.warning(f"RAG attempt {attempt} failed: {e}")
                if attempt == RAG_RETRY_COUNT:
                    raise
                await asyncio.sleep(1)

        relevant_snippets = await self._reflect_financial_context(query, snippets)
        return [s.content for s in relevant_snippets]

    async def _reflect_financial_context(
        self, query: str, snippets: List[RAGSnippet]
    ) -> List[RAGSnippet]:
        """Use LLM to score financial relevance of each snippet."""
        if not self.llm_planner or not snippets:
            return snippets

        tasks = [self._reflect_financial_relevance(query, s.content) for s in snippets]
        scores = await asyncio.gather(*tasks, return_exceptions=True)

        enriched: List[tuple[RAGSnippet, float]] = []
        for snippet, raw_score in zip(snippets, scores):
            score_val = _as_score(raw_score)
            if score_val is not None and score_val >= REFLECTION_THRESHOLD:
                snippet.score = score_val
                enriched.append((snippet, score_val))

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
            raw = raw.strip()
            if raw.startswith("{") and raw.endswith("}"):
                data = json.loads(raw)
                return max(0.0, min(1.0, float(data.get("score", 0.5))))
            raise ValueError("Invalid JSON response")
        except Exception as e:
            logger.warning(f"Financial reflection failed: {e}")
            return 0.5

    async def _heuristic_plan(self, query: str, claims: Dict[str, Any]) -> Plan:
        """Generate initial plan based on heuristics for billing queries."""
        from .base import Plan, PlanStep
        low = query.lower()
        tenant = claims.get("tenant", "unknown")

        steps: List[PlanStep] = []
        if any(k in low for k in ("faktura", "invoice", "bill", "płatność")):
            invoice_id = self._extract_invoice_id(query)
            if invoice_id:
                steps.append(
                    PlanStep(
                        name="get_invoice",
                        arguments={"invoice_id": invoice_id, "tenant": tenant},
                    )
                )

        if any(k in low for k in ("raport", "report", "użycie", "usage")):
            period = self._extract_period(query) or "last_month"
            steps.append(
                PlanStep(
                    name="generate_usage_report",
                    arguments={"period": period, "tenant": tenant},
                )
            )

        if not steps:
            steps.append(
                PlanStep(
                    name="search_billing_kb",
                    arguments={"query": query, "tenant": tenant},
                )
            )

        return Plan(steps=steps)

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

    def _compose_response(
        self, query: str, invoked_tools: List[ToolCall], tool_results: List[str], contextual_info: List[str]
    ) -> str:
        """Build user-facing response from execution results."""
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

    async def run(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[ToolCall]]:
        """Executes the billing agent workflow with specialized planning and finalization."""
        context = context or {}
        claims = context.get("claims", {})
        tenant = claims.get("tenant", "unknown")

        with self.tracer.start_as_current_span("billing.run") as span:
            span.set_attribute("query", query[:100])
            span.set_attribute("tenant", tenant)

            try:
                await _authorize(
                    opa_policy, "billing.query", claims, {"query": query, "tenant": tenant}
                )
            except Exception as e:
                span.record_exception(e)
                return f"Access denied: {str(e)}", []

            try:
                initial_plan = await self._heuristic_plan(query, claims)
            except Exception as e:
                logger.error(f"Heuristic planning failed: {e}")
                span.record_exception(e)
                return "An error occurred during planning.", []

            intent_graph = nx.DiGraph()
            for i, step in enumerate(initial_plan.steps):
                intent_graph.add_node(i, step=step)
                if i > 0:
                    intent_graph.add_edge(i - 1, i)

            tool_results: List[str] = []
            invoked_tools: List[ToolCall] = []
            reflection_count = 0

            queue = list(intent_graph.nodes)
            idx = 0
            while idx < len(queue):
                node = queue[idx]

                if len(intent_graph.nodes) > MAX_GRAPH_NODES:
                    raise RuntimeError("Graph size exceeded max nodes")
                if nx.has_cycles(intent_graph):
                    raise RuntimeError("Cycle detected in Intent Graph")

                step = intent_graph.nodes[node]["step"]
                tool_call = ToolCall(name=step.name, arguments=step.arguments)

                try:
                    await _authorize(self.opa_policy, "tools.invoke", claims, {"action": step.name})
                except Exception as e:
                    span.record_exception(e)
                    tool_results.append(f"Authorization error: {str(e)}")
                    invoked_tools.append(tool_call)
                    idx += 1
                    continue

                try:
                    result = await asyncio.wait_for(
                        self.tools.execute(step.name, claims=claims, **step.arguments),
                        timeout=TOOL_TIMEOUT_SEC,
                    )
                except asyncio.TimeoutError:
                    result = "Timeout during execution"
                except Exception as e:
                    result = f"Error: {str(e)}"

                tool_results.append(str(result))
                invoked_tools.append(tool_call)

                score = await self._reflect(result, query)
                reflection_count += 1
                span.set_attribute(f"step_{node}_score", score)

                if score < REFLECTION_THRESHOLD and reflection_count < MAX_REFLECTIONS:
                    span.add_event("Replanning due to low score")
                    new_plan = await self.planner.replan(query, tool_results)
                    if new_plan and new_plan.steps:
                        new_start = len(intent_graph.nodes)
                        for j, new_step in enumerate(new_plan.steps):
                            new_node = new_start + j
                            intent_graph.add_node(new_node, step=new_step)
                            intent_graph.add_edge(node, new_node)
                            queue.append(new_node)
                idx += 1

            contextual_info = await self._get_contextual_info(query, invoked_tools)
            final_response = self._compose_response(
                query, invoked_tools, tool_results, contextual_info
            )
            await self.memory.store_dialogue(self.agent_name, query, final_response, context)
            return final_response, invoked_tools


# --------------------------------------------------------------------------- #
# Asyncio import at bottom to avoid top-level import issues (if needed)
# --------------------------------------------------------------------------- #
