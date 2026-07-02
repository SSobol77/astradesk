# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/src/model_gateway/guardrails.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for services/api-gateway/src/model_gateway/guardrails.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Core guardrails for input validation, plan schema enforcement, and output sanitization.
Integrates OPA governance, OTel tracing, self-reflection, and PII redaction. Async-native.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from astradesk_core.redaction import redact_text, safe_preview
from opa_client.opa import OpaClient
from opentelemetry import trace
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Compiled dangerous patterns
DANGEROUS_PATTERNS = [
    re.compile(r'\bdrop\s+(database|table)\b', re.IGNORECASE),
    re.compile(r'\brm\s+-rf?\b', re.IGNORECASE),
    re.compile(r'\bshutdown\b', re.IGNORECASE),
    re.compile(r'\bformat\s+c:', re.IGNORECASE),
    re.compile(r"['\";]\s*--", re.IGNORECASE),
    re.compile(r'\bexec\s+\w+\s*\(', re.IGNORECASE),
    re.compile(r'\bpasswd\b', re.IGNORECASE),
    re.compile(r'\broot\b', re.IGNORECASE),
]


class PlanStepModel(BaseModel):
    """Pydantic model for a single plan step."""

    name: str = Field(..., description='Tool name')
    args: dict[str, Any] = Field(default_factory=dict, description='Tool arguments')


class PlanModel(BaseModel):
    """Pydantic model for full LLM-generated plan."""

    steps: list[PlanStepModel] = Field(..., description='Execution steps')
    reflection_score: float | None = None


class ProblemDetail(BaseModel):
    """RFC 7807 error detail."""

    type: str = 'https://astradesk.com/errors/validation'
    title: str = 'Validation Error'
    detail: str
    status: int = 400


def redact_sensitive(text: str) -> str:
    """Redacts PII/secrets from text before logging or egress.

    Delegates to the shared, fail-closed redactor in
    :mod:`astradesk_core.redaction` so emails, tokens, secret assignments, API
    keys, private-key markers, IPs, and card/SSN shapes are all covered by one
    deterministic boundary (``INV-NO-RAW-EGRESS``).
    """
    return redact_text(text)


async def is_safe_input(
    text: str,
    opa_client: OpaClient | None = None,
) -> bool:
    """Checks if input is safe. Async for policy checks."""
    with tracer.start_as_current_span('guardrails.is_safe_input') as span:
        safe_text = redact_sensitive(text)
        # Preview is derived from the redacted text and bounded; raw input must
        # never reach the span (INV-PII-1/INV-PII-4).
        span.set_attribute('input_preview', safe_preview(text, 50))
        normalized = ' '.join(safe_text.lower().split())

        if opa_client:
            decision = await opa_client.check_policy(
                input={'input': safe_text}, policy_path='astradesk/guardrails/input'
            )
            if not decision.get('result', True):
                logger.warning('OPA blocked input')
                return False

        for pattern in DANGEROUS_PATTERNS:
            if pattern.search(normalized):
                logger.warning(f'Dangerous pattern: {pattern.pattern}')
                span.add_event('unsafe_input_detected')
                return False
        return True


async def validate_plan_json(
    json_string: str,
    opa_client: OpaClient | None = None,
) -> PlanModel:
    """Validates and parses LLM plan JSON."""
    with tracer.start_as_current_span('guardrails.validate_plan_json'):
        try:
            data = json.loads(json_string)
            if opa_client:
                decision = await opa_client.check_policy(
                    input={'plan': data}, policy_path='astradesk/guardrails/plan'
                )
                if not decision.get('result', True):
                    raise ValueError('Plan denied by policy')
            plan = PlanModel.model_validate(data)
            logger.info(f'Plan validated: {len(plan.steps)} steps')
            return plan
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f'Plan validation failed: {e}')
            raise ValueError('Invalid plan format') from e


async def reflect_plan_quality(
    plan: PlanModel,
    query: str,
    llm_provider: Any,
) -> float:
    """Scores plan relevance using LLM self-reflection."""
    with tracer.start_as_current_span('guardrails.reflect_plan'):
        system = 'Score plan relevance to query (0.0-1.0). JSON: {"score": 0.85}'
        user = f'Query: {query}\nPlan: {plan.model_dump_json(indent=2)}'
        try:
            raw = await llm_provider.chat(
                [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]
            )
            data = json.loads(raw)
            score = float(data.get('score', 0.5))
            plan.reflection_score = score
            return score
        except Exception:
            return 0.5


def clip_output(text: str, max_chars: int = 2000) -> str:
    """Safely clips output text."""
    if max_chars <= 0:
        return '…'
    return text if len(text) <= max_chars else text[: max_chars - 1] + '…'
