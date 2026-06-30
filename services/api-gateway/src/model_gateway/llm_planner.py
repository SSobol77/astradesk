# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/src/model_gateway/llm_planner.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for services/api-gateway/src/model_gateway/llm_planner.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""LLM-driven planner that generates structured execution plans and user summaries.
Integrates guardrails, OPA, OTel tracing, PII redaction, and self-reflection. Async-native.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from astradesk_core.redaction import safe_preview
from opa_client.opa import OpaClient
from opentelemetry import trace

from model_gateway.router import provider_router

from .base import ChatParams, LLMMessage
from .guardrails import (
    PlanModel,
    clip_output,
    is_safe_input,
    redact_sensitive,
    reflect_plan_quality,
    validate_plan_json,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_PLAN = (
    "You are a planning agent. Generate a strict JSON plan with 'steps' array. "
    'Each step: {"name": "tool", "args": {}}. '
    'Use only available tools. Return empty steps if none apply. '
    'No extra text.'
)

SYSTEM_PROMPT_SUMMARIZE = (
    'You are a helpful assistant. Synthesize a clear, concise answer from query and tool results. '
    "Interpret, don't list."
)


class LLMPlanner:
    """LLM planner with guardrails, governance, and observability."""

    def __init__(self, opa_client: OpaClient | None = None) -> None:
        """Initializes with optional OPA client."""
        self.opa_client = opa_client
        self.tracer = trace.get_tracer(__name__)
        self._available_tools: list[str] = []

    async def chat(
        self,
        messages: Sequence[LLMMessage | dict[str, str]],
        params: ChatParams | dict[str, Any] | None = None,
    ) -> str:
        """Delegate normalized chat requests to the currently routed provider.

        This is the shared model-egress boundary for reflection/scoring calls
        made across the runtime (agents, orchestrator, RAG). Message content is
        redacted here so raw user input cannot reach the external model by a
        call site forgetting to redact (``INV-PII-1``/``INV-PII-4``). Redaction
        is idempotent, so already-redacted planner prompts are unaffected.
        """
        normalized_messages = [
            message
            if isinstance(message, LLMMessage)
            else LLMMessage(role=message['role'], content=message['content'])
            for message in messages
        ]
        normalized_messages = [
            LLMMessage(role=message.role, content=redact_sensitive(message.content))
            for message in normalized_messages
        ]
        normalized_params = (
            params if isinstance(params, ChatParams) else ChatParams.model_validate(params or {})
        )
        provider = await provider_router.get_provider()
        return await provider.chat(normalized_messages, params=normalized_params)

    async def make_plan(self, query: str, available_tools: list[str]) -> PlanModel:
        """Generates validated execution plan with reflection."""
        self._available_tools = list(available_tools)
        with self.tracer.start_as_current_span('llm_planner.make_plan') as span:
            # Classify + redact BEFORE any preview reaches the span; the preview
            # is taken from redacted text, never the raw query (INV-PII-1).
            safe_query = redact_sensitive(query)
            span.set_attribute('query_preview', safe_preview(query, 100))
            span.set_attribute('tool_count', len(available_tools))
            if not await is_safe_input(safe_query, self.opa_client):
                span.add_event('unsafe_input_blocked')
                return PlanModel(steps=[])

            if self.opa_client:
                decision = await self.opa_client.check_policy(
                    input={'query': safe_query, 'tools': available_tools},
                    policy_path='astradesk/planner/make_plan',
                )
                if not decision.get('result', True):
                    span.add_event('opa_denied_plan')
                    return PlanModel(steps=[])

            tools_str = ', '.join(sorted(available_tools))
            user_prompt = f'Available tools: [{tools_str}]\nUser query: "{safe_query}"'

            messages = [
                LLMMessage(role='system', content=SYSTEM_PROMPT_PLAN),
                LLMMessage(role='user', content=user_prompt),
            ]
            params = ChatParams(max_tokens=1024, temperature=0.0)

            try:
                provider = await provider_router.get_provider()
                raw_response = await provider.chat(messages, params=params)
                plan = await validate_plan_json(raw_response, self.opa_client)

                # Pass the redacted query: reflection prompts go straight to
                # provider.chat (bypassing the redaction in this.chat).
                score = await reflect_plan_quality(plan, safe_query, provider)
                span.set_attribute('reflection_score', score)

                if score < 0.7:
                    logger.info(f'Low plan quality ({score:.2f}). Using empty plan.')
                    return PlanModel(steps=[])

                return plan

            except Exception as e:
                logger.error(f'Plan generation failed: {e}', exc_info=True)
                span.record_exception(e)
                return PlanModel(steps=[])

    async def replan(self, query: str, tool_results: list[str]) -> PlanModel:
        """Generate a revised plan using prior tool results as bounded context."""
        results = '\n'.join(tool_results[-5:])
        revised_query = f'{query}\nPrevious tool results:\n{results}'
        return await self.make_plan(revised_query, self._available_tools)

    async def summarize(self, query: str, tool_results: list[str]) -> str:
        """Generates user-friendly summary."""
        with self.tracer.start_as_current_span('llm_planner.summarize') as span:
            span.set_attribute('result_count', len(tool_results))

            if not tool_results:
                return 'No results to summarize.'

            safe_query = redact_sensitive(query)
            safe_results = [redact_sensitive(res) for res in tool_results]
            results_str = '\n'.join(f'- {res}' for res in safe_results)
            user_prompt = (
                f'Original query: "{safe_query}"\n\n'
                f'Tool results:\n{results_str}\n\n'
                'Provide a concise answer.'
            )

            messages = [
                LLMMessage(role='system', content=SYSTEM_PROMPT_SUMMARIZE),
                LLMMessage(role='user', content=user_prompt),
            ]
            params = ChatParams(max_tokens=1024, temperature=0.2)

            try:
                provider = await provider_router.get_provider()
                summary = await provider.chat(messages, params=params)
                return clip_output(summary)
            except Exception as e:
                logger.error(f'Summarization failed: {e}')
                span.record_exception(e)
                return f'Error: Raw results:\n{results_str}'
