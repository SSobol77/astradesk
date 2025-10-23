# SPDX-License-Identifier: Apache-2.0
# services/api-gateway/src/agents/base.py
"""File: services/api-gateway/src/agents/base.py
Project: AstraDesk Framework — API Gateway
Description:
    Abstract base class (ABC) and lifecycle contract for all agents.
    Encapsulates the end-to-end execution loop (plan → act → finalize) while
    delegating strategy-specific behavior to subclasses via well-defined hooks.

Author: Siergej Sobolewski
Since: 2025-10-07

Design goals
------------
- Single, consistent execution lifecycle across agents (Template Method pattern).
- Clear separation of concerns: orchestration lives here; domain strategy in subclasses.
- Safety first: robust error handling, bounded retries, and structured telemetry.
- Async-native: all I/O must be non-blocking (asyncio), suitable for FastAPI/WebFlux backends.
- Testability: pure logic with injectable dependencies and deterministic hooks.

Public contract (high level)
---------------------------
Subclasses MUST implement/override:
  * `async plan(request: AgentRequest) -> Plan`
      - Build an actionable plan (steps/tools) from the incoming request.
  * `async act(step: PlanStep, ctx: AgentContext) -> StepResult`
      - Execute a single step (tool call / reasoning) with proper timeouts and cancellation.
  * `async finalize(ctx: AgentContext) -> AgentResponse`
      - Assemble final response and side effects (persist dialogue, emit events).

Subclasses MAY override:
  * `async before_run(ctx)` / `async after_run(ctx, response)`
  * `on_error(exc, ctx)` — map exceptions to agent-level failures (no blocking I/O).
  * `select_retry_policy(step)` — customize retry/backoff per step/tool.

Lifecycle (Template Method)
---------------------------
`run(request) -> AgentResponse`:
    1) validate → create context
    2) plan(request)
    3) for each step in plan:
           act(step, ctx) with timeout/RetryPolicy
           update context / collect evidence
    4) finalize(ctx)
    5) return response

Observability & policies
------------------------
- Emit structured events (trace/span) at: plan start, step start/end, errors, finalize.
- Enforce limits: max steps, max tool calls, wall-clock budget, token/size quotas.
- Provide uniform error taxonomy (e.g., ToolTimeout, ToolBadRequest, PolicyViolation).
- Optional redaction layer for PII before logging/telemetry export.

Type hints & data contracts
---------------------------
- Prefer `pydantic` models for request/response/context (json-schema friendly).
- Use `typing.Protocol` for tool runners to keep agents decoupled from concrete I/O.
- Keep serialization boundaries explicit (no implicit `.dict()` in core logic).

Usage (example)
---------------
>>> class SupportAgent(BaseAgent):
...     async def plan(self, request): ...
...     async def act(self, step, ctx): ...
...     async def finalize(self, ctx): ...
...
>>> agent = SupportAgent(tools=my_tools, policy=my_policy, tracer=my_tracer)
>>> resp = await agent.run(AgentRequest(user_input="reset VPN"))

Notes
-----
- No network/filesystem side effects at import time.
- All timeouts should be cancellable (`asyncio.timeout()` in Python 3.11+).
- Keep hook implementations idempotent where feasible to enable safe retries.

Notes PL:
---------
Moduł definiujący abstrakcyjną klasę bazową dla wszystkich agentów.

Klasa `BaseAgent` implementuje wspólną, niezmienną logikę cyklu życia
przetwarzania zapytania, w tym:
- Tworzenie planu działania.
- Bezpieczne wykonywanie narzędzi z obsługą błędów.
- Wykorzystanie strategii kontekstowej zdefiniowanej przez klasę pochodną.
- Finalizację odpowiedzi i zapis dialogu.

Dzięki temu, konkretne implementacje agentów (np. `OpsAgent`, `SupportAgent`)
muszą jedynie zdefiniować swoją unikalną strategię, a nie implementować
całą pętlę wykonawczą od nowa.

"""  # noqa: D205

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple  # noqa: UP035

from runtime.memory import Memory
from runtime.models import ToolCall
from runtime.planner import KeywordPlanner
from runtime.rag import RAG
from runtime.registry import ToolRegistry

logger = logging.getLogger(__name__)


class BaseAgent:
    """Abstrakcyjna klasa bazowa dla agentów."""

    __slots__ = ("agent_name", "memory", "planner", "rag", "tools")

    def __init__(  # noqa: D107
        self,
        tools: ToolRegistry,
        memory: Memory,
        planner: KeywordPlanner,
        rag: RAG,
        agent_name: str,
    ):
        self.tools = tools
        self.memory = memory
        self.planner = planner
        self.rag = rag
        self.agent_name = agent_name

    async def _get_contextual_info(
        self, query: str, tool_results: List[str]
    ) -> List[str]:
        """Metoda strategii, którą muszą zaimplementować klasy pochodne.

        Decyduje, czy i jak użyć RAG na podstawie wyników narzędzi.

        Args:
            query: Oryginalne zapytanie użytkownika.
            tool_results: Wyniki zwrócone przez wykonane narzędzia.

        Returns:
            Lista fragmentów kontekstu z RAG (może być pusta).
        """
        raise NotImplementedError(
            "Klasa pochodna musi zaimplementować metodę _get_contextual_info"
        )

    async def run(
        self, query: str, context: Dict[str, Any]
    ) -> Tuple[str, List[ToolCall]]:
        """Uruchamia główną pętlę wykonawczą agenta.

        Args:
            query: Zapytanie użytkownika.
            context: Słownik kontekstowy zawierający m.in. 'claims' i 'request_id'.

        Returns:
            Krotka zawierająca (finalna_odpowiedź_tekstowa, lista_wywołanych_narzędzi).
        """
        plan = self.planner.make_plan(query)
        
        tool_results: List[str] = []
        invoked_tools: List[ToolCall] = []

        for step in plan:
            try:
                logger.info(f"Wykonywanie kroku planu: wywołanie narzędzia '{step.name}'")
                # `execute` z ToolRegistry centralnie obsługuje RBAC i wywołanie sync/async
                result = await self.tools.execute(
                    step.name, claims=context.get("claims"), **step.arguments
                )
                tool_results.append(str(result))
                invoked_tools.append(step)
            except PermissionError as e:
                logger.warning(f"Odmowa dostępu do narzędzia '{step.name}': {e}")
                tool_results.append(f"Błąd: Brak uprawnień do użycia narzędzia '{step.name}'.")
            except Exception as e:
                logger.error(
                    f"Wystąpił błąd podczas wykonywania narzędzia '{step.name}'. Błąd: {e}",
                    exc_info=True,
                )
                tool_results.append(f"Błąd: Wystąpił problem podczas użycia narzędzia '{step.name}'.")

        contextual_info = await self._get_contextual_info(query, invoked_tools)
        
        final_response = self.planner.finalize(query, tool_results, contextual_info)
        
        await self.memory.store_dialogue(self.agent_name, query, final_response, context)
        
        return final_response, invoked_tools
