# SPDX-License-Identifier: Apache-2.0
# services/api-gateway/src/gateway/orchestrator.py
"""File: services/api-gateway/src/gateway/orchestrator.py
Project: AstraDesk Framework — API Gateway
Description: Business logic layer for agent orchestration: agent selection,
             planner choice (LLM vs. keyword), tool execution, fallback
             handling, and final response assembly.
Author: Siergej Sobolewski
Since: 2025-10-07.

Notes (PL):
- Warstwa czysto domenowa: brak zależności od FastAPI/HTTP. Dzięki temu łatwo testować.
- Odpowiedzialności:
  * Wybór agenta i strategii (heurystyki/LLM).
  * Decyzja o użyciu planera (LLM vs. keyword/rules).
  * Wykonanie planu: orkiestracja narzędzi/akcji, kolejkowanie kroków.
  * Fallback i retry (np. backoff, circuit breaker) oraz agregacja wyników.
  * Budowa finalnej odpowiedzi dla warstwy webowej.
- Zalecenia:
  * Interfejsy/porty dla narzędzi (np. ToolRunner), DI przez konstruktory.
  * Deterministyczne testy jednostkowe z dublami (fakes/mocks).
  * Telemetria: eventy/traces przekazywane przez adapter obserwowalności.
"""  # noqa: D205
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import asyncpg
import redis.asyncio as redis
from fastapi import HTTPException

from agents.base import BaseAgent
from runtime.memory import Memory
from runtime.models import AgentName, AgentRequest, AgentResponse, ToolCall
from runtime.planner import KeywordPlanner
from runtime.registry import ToolRegistry

# --- Standardowy i poprawny sposób na opcjonalne importy dla typowania ---

# Ten blok jest widoczny tylko dla analizatorów typów (np. Pylance, mypy).
# Definiuje on typy, aby Pylance wiedział, czym są "LLMPlanner" i "LLMPlan".
if TYPE_CHECKING:
    from model_gateway.llm_planner import LLMPlan, LLMPlanner

# Ten blok jest wykonywany w trakcie działania programu (runtime).
try:
    from model_gateway.llm_planner import LLMPlan, LLMPlanner
except ImportError:
    # Jeśli import się nie powiedzie, w runtime `LLMPlanner` będzie miało wartość None.
    LLMPlanner = None
    LLMPlan = None


logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Orkiestruje pełny cykl życia żądania wykonania agenta."""

    def __init__(
        self,
        # Użycie stringa ("forward reference") ostatecznie rozwiązuje problem.
        llm_planner: Optional["LLMPlanner"], # type: ignore
        agents: Dict[str, BaseAgent],
        tools: ToolRegistry,
        pg_pool: asyncpg.Pool,
        redis: redis.Redis,
    ):
        self.llm_planner = llm_planner
        self.agents = agents
        self.tools = tools
        self.pg_pool = pg_pool
        self.redis = redis

    async def run(
        self, req: AgentRequest, claims: dict[str, Any], request_id: str
    ) -> AgentResponse:
        """Główna metoda wykonawcza."""
        context = {**req.meta, "claims": claims, "request_id": request_id}
        memory = Memory(self.pg_pool, self.redis)

        if self.llm_planner:
            response = await self._try_llm_path(req, context, memory, request_id)
            if response:
                return response

        return await self._run_fallback_path(req, context, memory, request_id)

    async def _try_llm_path(
        self, req: AgentRequest, context: dict, memory: Memory, request_id: str
    ) -> AgentResponse | None:
        """Próbuje wykonać zadanie przy użyciu planera LLM."""
        # Sprawdzamy, czy klasa LLMPlan została zaimportowana, zanim użyjemy jej typu.
        if not LLMPlan:
            return None
            
        try:
            logger.info(f"[{request_id}] Próba użycia LLMPlanner.")
            # Użycie stringa jako adnotacji typu ("forward reference").
            llm_plan: "LLMPlan" = await self.llm_planner.make_plan( # type: ignore
                req.input, available_tools=self.tools.names()
            )

            if not llm_plan or not llm_plan.steps:
                logger.info(f"[{request_id}] LLMPlanner nie wygenerował planu. Przejście do fallbacku.")
                return None

            logger.info(f"[{request_id}] LLMPlanner wygenerował plan z {len(llm_plan.steps)} krokami.")
            results: List[str] = []
            invoked_tools: List[ToolCall] = []

            for step in llm_plan.steps:
                tool_call = ToolCall(name=step.name, arguments=step.args)
                res = await self.tools.execute(
                    step.name, claims=context.get("claims"), **step.args
                )
                results.append(str(res))
                invoked_tools.append(tool_call)

            output = await self.llm_planner.summarize(req.input, results)
            await memory.store_dialogue(req.agent.value, req.input, output, context)

            return AgentResponse(
                output=output,
                reasoning_trace_id=request_id,
                # Konwertujemy każdy obiekt ToolCall na słownik
                invoked_tools=[tool.model_dump() for tool in invoked_tools],
            )
        except Exception as e:
            logger.warning(
                f"[{request_id}] Wystąpił błąd podczas ścieżki LLM: {e}. Przejście do fallbacku.",
                exc_info=True,
            )
            return None

    async def _run_fallback_path(
        self, req: AgentRequest, context: dict, memory: Memory, request_id: str
    ) -> AgentResponse:
        """Wykonuje zadanie przy użyciu agenta z planerem słów kluczowych."""
        logger.info(f"[{request_id}] Uruchamianie ścieżki fallback (KeywordPlanner).")
        
        agent = self.agents.get(req.agent.value)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{req.agent.value}' nie został znaleziony.")

        output, invoked_tools = await agent.run(req.input, context)
        
        return AgentResponse(
            output=output,
            reasoning_trace_id=request_id,
            invoked_tools=[tool.model_dump() for tool in invoked_tools],
        )
