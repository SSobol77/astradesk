# SPDX-License-Identifier: Apache-2.0
# services/api-gateway/src/model_gateway/llm_planner.py
"""LLM-driven planner that generates structured execution plans and user summaries.
Integrates guardrails, OPA, OTel tracing, PII redaction, and self-reflection. Async-native.
Author: Siergej Sobolewski
Since: 2025-10-25
"""

from __future__ import annotations

import logging
from typing import List, Optional

from opentelemetry import trace
from opa_python_client import OPAClient

from .router import provider_router
from .base import ChatParams, LLMMessage
from .guardrails import (
    PlanModel,
    is_safe_input,
    validate_plan_json,
    clip_output,
    redact_sensitive,
    reflect_plan_quality,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_PLAN = (
    "You are a planning agent. Generate a strict JSON plan with 'steps' array. "
    "Each step: {\"name\": \"tool\", \"args\": {}}. "
    "Use only available tools. Return empty steps if none apply. "
    "No extra text."
)

SYSTEM_PROMPT_SUMMARIZE = (
    "You are a helpful assistant. Synthesize a clear, concise answer from query and tool results. "
    "Interpret, don't list."
)


class LLMPlanner:
    """LLM planner with guardrails, governance, and observability."""

    def __init__(self, opa_client: Optional[OPAClient] = None) -> None:
        """Initializes with optional OPA client."""
        self.opa_client = opa_client
        self.tracer = trace.get_tracer(__name__)

    async def make_plan(self, query: str, available_tools: List[str]) -> PlanModel:
        """Generates validated execution plan with reflection."""
        with self.tracer.start_as_current_span("llm_planner.make_plan") as span:
            span.set_attribute("query_preview", query[:100])
            span.set_attribute("tool_count", len(available_tools))

            safe_query = redact_sensitive(query)
            if not await is_safe_input(safe_query, self.opa_client):
                span.add_event("unsafe_input_blocked")
                return PlanModel(steps=[])

            if self.opa_client:
                decision = await self.opa_client.check_policy(
                    input={"query": safe_query, "tools": available_tools},
                    policy_path="astradesk/planner/make_plan"
                )
                if not decision.get("result", True):
                    span.add_event("opa_denied_plan")
                    return PlanModel(steps=[])

            tools_str = ", ".join(sorted(available_tools))
            user_prompt = f"Available tools: [{tools_str}]\nUser query: \"{safe_query}\""

            messages = [
                LLMMessage(role="system", content=SYSTEM_PROMPT_PLAN),
                LLMMessage(role="user", content=user_prompt),
            ]
            params = ChatParams(max_tokens=1024, temperature=0.0)

            try:
                provider = await provider_router.get_provider()
                raw_response = await provider.chat(messages, params=params)
                plan = await validate_plan_json(raw_response, self.opa_client)

                score = await reflect_plan_quality(plan, query, provider)
                span.set_attribute("reflection_score", score)

                if score < 0.7:
                    logger.info(f"Low plan quality ({score:.2f}). Using empty plan.")
                    return PlanModel(steps=[])

                return plan

            except Exception as e:
                logger.error(f"Plan generation failed: {e}", exc_info=True)
                span.record_exception(e)
                return PlanModel(steps=[])

    async def summarize(self, query: str, tool_results: List[str]) -> str:
        """Generates user-friendly summary."""
        with self.tracer.start_as_current_span("llm_planner.summarize") as span:
            span.set_attribute("result_count", len(tool_results))

            if not tool_results:
                return "No results to summarize."

            safe_query = redact_sensitive(query)
            safe_results = [redact_sensitive(res) for res in tool_results]
            results_str = "\n".join(f"- {res}" for res in safe_results)
            user_prompt = (
                f"Original query: \"{safe_query}\"\n\n"
                f"Tool results:\n{results_str}\n\n"
                "Provide a concise answer."
            )

            messages = [
                LLMMessage(role="system", content=SYSTEM_PROMPT_SUMMARIZE),
                LLMMessage(role="user", content=user_prompt),
            ]
            params = ChatParams(max_tokens=1024, temperature=0.2)

            try:
                provider = await provider_router.get_provider()
                summary = await provider.chat(messages, params=params)
                return clip_output(summary)
            except Exception as e:
                logger.error(f"Summarization failed: {e}")
                span.record_exception(e)
                return f"Error: Raw results:\n{results_str}"
