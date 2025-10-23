# SPDX-License-Identifier: Apache-2.0
# services/api-gatewaysrc/model_gateway/llm_planner.py
"""File: services/api-gatewaysrc/model_gateway/llm_planner.py
Project: AstraDesk Framework — API Gateway
Description:
    Language-Model–driven planner that converts a user query and a set of
    available tools into a structured execution plan (strict JSON), and
    synthesizes a final user-facing answer from tool results. Integrates
    with Model Gateway providers via `provider_router`, applies guardrails
    before/after LLM calls, and enforces predictable, schema-validated I/O.

Author: Siergej Sobolewski
Since: 2025-10-07

Responsibilities
----------------
- Plan creation:
  * Prompt LLM with system instructions + available tools → JSON `PlanModel`.
  * Reject unsafe inputs up-front using `guardrails.is_safe_input`.
  * Validate LLM output with `guardrails.validate_plan_json` (Pydantic schema).
- Summarization:
  * Prompt LLM to compose a concise, user-friendly summary from tool results.
  * Clip overly long outputs with `guardrails.clip_output`.
- Provider access:
  * Use `provider_router.get_provider()` to obtain the active `LLMProvider`.
  * Pass normalized `ChatParams` (max_tokens, temperature, etc.).

Design principles
-----------------
- Fail-closed: return empty `PlanModel(steps=[])` on any validation or provider error.
- Determinism for plans: temperature defaults to 0.0; no extra prose outside JSON.
- Separation of concerns: orchestration executes the plan; this module only plans
  and summarizes.
- Observability: log warnings/errors with minimal, non-sensitive context.

Security & safety
-----------------
- Guard inputs: normalize and screen user queries for dangerous patterns.
- Strict outputs: accept only schema-conforming JSON; discard free-form text.
- Do not log secrets or raw LLM payloads in production; prefer structured events.

Performance
-----------
- Single provider call per phase (plan/summarize); keep prompts compact.
- Use bounded `max_tokens` to protect latency and cost budgets.

Usage (sketch)
--------------
>>> planner = LLMPlanner()
>>> plan = await planner.make_plan(query="Restart payments-api", available_tools=["service.restart","metrics.fetch"])
>>> if plan.steps:
...     results = await run_steps(plan)  # external orchestration
...     answer = await planner.summarize(query="Restart payments-api", tool_results=results)

Notes
-----
- System prompts (`SYSTEM_PROMPT_PLAN`, `SYSTEM_PROMPT_SUMMARIZE`) are curated for
  strict JSON planning and concise summarization. Update carefully and version them
  if downstream schemas or policies change.
- Planner does not implement retries/backoff; handle them in the provider layer
  or above (or return empty plan on error).

Notes (PL):
-----------
Implementacja planera opartego na modelu językowym (LLM).

Moduł ten dostarcza klasę `LLMPlanner`, która wykorzystuje model LLM do
analizy zapytania użytkownika i tworzenia planu działania w postaci
sekwencji wywołań narzędzi.

Główne funkcjonalności:
- Generowanie planu*: Na podstawie zapytania i listy dostępnych narzędzi,
  model LLM jest instruowany (poprzez system prompt) do wygenerowania
  planu w formacie JSON.
- **Bezpieczeństwo**: Przed wysłaniem zapytania do LLM, dane wejściowe są
  sprawdzane przez `guardrails` pod kątem potencjalnie złośliwych intencji.
- **Walidacja**: Odpowiedź z LLM jest walidowana pod kątem poprawności
  formatu JSON i zgodności ze zdefiniowanym schematem Pydantic.
- **Podsumowanie**: Po wykonaniu narzędzi, LLM jest ponownie wykorzystywany
  do stworzenia spójnej, naturalnej odpowiedzi dla użytkownika.

Ten planer stanowi zaawansowaną alternatywę dla prostego planera
opartego na słowach kluczowych.

"""  # noqa: D205

from __future__ import annotations

import logging
from typing import List

from .router import provider_router
from .base import ChatParams, LLMMessage
from .guardrails import PlanModel, is_safe_input, validate_plan_json, clip_output

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_PLAN = (
    "You are a highly intelligent planning agent. Your task is to analyze a user query "
    "and a list of available tools, then create a step-by-step plan in a strict JSON format. "
    "The JSON object must have a single key 'steps', which is a list of tool calls. "
    "Each tool call is an object with 'name' and 'args'.\n"
    "Example: {\"steps\":[{\"name\":\"tool_name\",\"args\":{\"arg1\":\"value1\"}}]}\n"
    "If no tool is suitable for the query, return an empty list: {\"steps\":[]}.\n"
    "Do not add any explanations or text outside of the JSON object."
)
SYSTEM_PROMPT_SUMMARIZE = (
    "You are a helpful assistant. Your task is to synthesize a final, user-friendly "
    "answer based on the original user query and the results from the tools that were executed. "
    "Respond in a clear, concise, and natural language. Do not just list the results; "
    "interpret them to provide a complete answer."
)


class LLMPlanner:
    """Planer wykorzystujący LLM do tworzenia i podsumowywania planów działania."""

    __slots__ = ()

    async def make_plan(self, query: str, available_tools: List[str]) -> PlanModel:
        """Tworzy plan działania na podstawie zapytania użytkownika."""
        if not is_safe_input(query):
            logger.warning(f"Zablokowano potencjalnie niebezpieczne zapytanie: '{query}'")
            return PlanModel(steps=[])

        tools_list_str = ", ".join(sorted(available_tools))
        user_prompt = f"Available tools: [{tools_list_str}]\nUser query: \"{query}\""

        messages = [
            LLMMessage(role="system", content=SYSTEM_PROMPT_PLAN),
            LLMMessage(role="user", content=user_prompt),
        ]
        params = ChatParams(max_tokens=1024, temperature=0.0)

        try:
            provider = await provider_router.get_provider()
            raw_response = await provider.chat(messages, params=params)
            plan = validate_plan_json(raw_response)
            return plan
        except ValueError as e:
            logger.error(f"Nie udało się zwalidować planu z LLM. Błąd: {e}")
            return PlanModel(steps=[])
        except Exception as e:
            logger.error(f"Wystąpił błąd podczas generowania planu przez LLM. Błąd: {e}", exc_info=True)
            return PlanModel(steps=[])

    async def summarize(self, query: str, tool_results: List[str]) -> str:
        """Tworzy spójną odpowiedź dla użytkownika na podstawie wyników narzędzi."""
        if not tool_results:
            return "Narzędzia nie zwróciły żadnych wyników. Nie mogę wygenerować podsumowania."

        results_str = "\n".join(f"- {res}" for res in tool_results)
        user_prompt = (
            f"Original query: \"{query}\"\n\n"
            f"Tool execution results:\n{results_str}\n\n"
            "Please provide a final, synthesized answer to the user."
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
            logger.error(f"Wystąpił błąd podczas generowania podsumowania przez LLM. Błąd: {e}", exc_info=True)
            return f"Wystąpił błąd podczas generowania odpowiedzi. Surowe wyniki narzędzi:\n{results_str}"
