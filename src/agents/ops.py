# SPDX-License-Identifier: Apache-2.0
"""File: services/gateway-python/src/agents/ops.py
Project: AstraDesk Framework — API Gateway
Description:
    Operational (SRE/DevOps) agent implementation focused on action execution:
    fetching metrics, triggering deploys, restarting services, running checks,
    and enforcing runbooks/policies. Prioritizes reliable tool invocation over
    generative answers.

Author: Siergej Sobolewski
Since: 2025-10-07

Role & responsibilities
-----------------------
- Action-first strategy: execute concrete operational tasks defined in the plan.
- Deterministic behavior: explicit tools, explicit parameters, explicit outcomes.
- Policy enforcement: guardrails for allowed tools, scopes, and environments.
- Telemetry: emit structured traces/events for each step (start/end/error).

Non-goals / differences vs SupportAgent
---------------------------------------
- No RAG fallback: if a tool is missing/fails, report the state with diagnostics.
- No conversational elaboration unless explicitly requested by the plan/policy.
- Avoid speculative remediation; adhere strictly to runbook constraints.

Execution model
---------------
- Plans are composed of actionable steps (tool name + args + budget + policy tags).
- Each step is executed with timeouts and bounded retries (backoff/jitter).
- Results are validated and normalized before aggregation into the final response.
- Fail-fast for policy violations; continue-on-error only if policy allows.

Security & safety
-----------------
- Enforce allowlists/denylists for tools and targets (env/project/namespace).
- Redact secrets from logs/telemetry; never echo credential material.
- Impose budgets: max steps, max tool calls, wall-clock, per-step timeout.
- Record provenance for audit: who/when/what/tool/version/params (hashed).

Observability
-------------
- Emit spans: plan_start, step_start/step_end, policy_violation, tool_error, finalize.
- Attach standard attributes: env, service, cluster, region, runbook_id, step_id.
- Provide machine-readable statuses for CI/CD and runbook automation.

Notes (PL)
----------
Agentjest wyspecjalizowanym agentem zaprojektowanym do wykonywania
zadań administracyjnych i operacyjnych, takich jak pobieranie metryk czy
restartowanie usług.

- Agent operacyjny ma „priorytet akcji”: nie używa fallbacku RAG jak SupportAgent.
- W przypadku braku narzędzia / błędu wykonania — zwraca precyzyjny raport błędu.
- Integruj polityki (np. „prod requires approval”) przez warstwę Policy/Guard.

Strategia działania:
- Priorytet dla akcji: Ten agent jest zorientowany na wykonywanie zadań.
  Jego głównym celem jest pomyślne wywołanie narzędzi zdefiniowanych w planie.
- Brak fallbacku RAG: W przeciwieństwie do `SupportAgent`, `OpsAgent`
  celowo nie używa systemu RAG jako fallbacku. Jeśli narzędzie nie zostanie
  znalezione lub jego wykonanie się nie powiedzie, agent po prostu raportuje
  ten stan, zamiast próbować odpowiadać na pytania z bazy wiedzy.
- Egzekwowanie polityk: Agent powinien ściśle przestrzegać polityk
  i runbooków. Na przykład, jeśli polityka stanowi, że pewne narzędzia
  mogą być używane tylko w określonych środowiskach lub przez
  określonych użytkowników, agent powinien egzekwować te zasady
  i zgłaszać naruszenia.
- Telemetria i śledzenie: Każdy krok planu powinien być
  śledzony za pomocą spandów i zdarzeń. Powinno to obejmować
  rozpoczęcie i zakończenie każdego kroku, a także wszelkie
  błędy lub naruszenia polityk.
- Walidacja i normalizacja wyników: Wyniki zwrócone przez
  narzędzia powinny być walidowane i normalizowane przed
  włączeniem ich do ostatecznej odpowiedzi. Obejmuje to
  usuwanie wszelkich poufnych informacji i zapewnienie, że
  wyniki są w oczekiwanym formacie.

Usage (example)
---------------
>>> from agents.base import BaseAgent
>>> class OpsAgent(BaseAgent):
...     async def plan(self, request): ...
...     async def act(self, step, ctx): ...
...     async def finalize(self, ctx): ...
...
>>> agent = OpsAgent(tools=my_tools, policy=my_policy, tracer=my_tracer)
>>> response = await agent.run(AgentRequest(command="service:restart", target="payments-api"))

"""  # noqa: D205

from __future__ import annotations

from typing import List

from agents.base import BaseAgent
from runtime.memory import Memory
from runtime.planner import KeywordPlanner
from runtime.rag import RAG
from runtime.registry import ToolRegistry


class OpsAgent(BaseAgent):
    """Agent do zadań operacyjnych SRE/DevOps."""

    def __init__(
        self,
        tools: ToolRegistry,
        memory: Memory,
        planner: KeywordPlanner,
        rag: RAG,
    ):
        """Inicjalizuje agenta operacyjnego.

        Args:
            tools: Rejestr dostępnych narzędzi.
            memory: Warstwa pamięci i audytu.
            planner: Planer oparty na słowach kluczowych.
            rag: System RAG (nieużywany aktywnie przez tego agenta).

        """
        super().__init__(
            tools=tools,
            memory=memory,
            planner=planner,
            rag=rag,
            agent_name="ops",
        )

    async def _get_contextual_info(
        self, query: str, tool_results: List[str]
    ) -> List[str]:
        """Implementacja strategii kontekstowej dla OpsAgent.

        Zgodnie ze swoją strategią, ten agent nie korzysta z RAG.
        Zawsze zwraca pustą listę.

        Args:
            query: Oryginalne zapytanie użytkownika.
            tool_results: Wyniki zwrócone przez wykonane narzędzia.

        Returns:
            Pusta lista.

        """
        return []
