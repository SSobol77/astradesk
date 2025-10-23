# SPDX-License-Identifier: Apache-2.0
"""File: services/gateway-python/src/agents/support.py
Project: AstraDesk Framework — API Gateway
Description:
    Knowledge-oriented support agent focused on answering user questions,
    guiding troubleshooting, and interacting with ticketing systems.
    Prefers high-quality grounded answers; uses tools first (when applicable),
    then falls back to Retrieval-Augmented Generation (RAG) if actions
    are not sufficient to resolve the user’s intent.

Author: Siergej Sobolewski
Since: 2025-10-07

Role & responsibilities
-----------------------
- Knowledge-first strategy: deliver accurate, grounded answers with sources.
- Tool-aware: can create/update tickets, look up statuses, or fetch FAQs via tools.
- Smart fallback to RAG: when no tool applies or action doesn’t resolve, query KB.
- Dialogue management: build user-facing responses and guidance next steps.

Differences vs OpsAgent
-----------------------
- Uses RAG fallback (grounded answers with citations); OpsAgent does NOT.
- More conversational; prioritizes explanation and user guidance over raw actions.
- May synthesize multi-source answers; OpsAgent sticks to deterministic runbooks.

RAG & grounding policy
----------------------
- Retrieval: top-k documents with MMR/diversity; configurable confidence threshold.
- Grounding: cite sources (ids/urls/titles) and prefer extractive summaries.
- Hallucination controls: answer only from retrieved content; otherwise escalate/ask.
- Redaction: scrub PII/secrets from prompts, logs, and returned snippets.

Execution model
---------------
1) Try tools first (FAQ search, ticket CRUD, status checks).
2) If tools do not conclude the intent, perform RAG:
   - retrieve → rank → validate → compose grounded answer with citations
3) Assemble final response: answer + actions taken + recommended next steps.
4) Persist dialogue metadata (optional) and emit telemetry.

Security & safety
-----------------
- Enforce tool allowlists and environment scopes (tenant/project).
- Do not echo secrets or internal identifiers; redact on output.
- Respect content policies and rate limits; degrade gracefully on timeouts.

Observability
-------------
- Emit spans: tool_attempt, tool_result, rag_retrieve, rag_compose, finalize.
- Attach attributes: user_id (hashed), locale, tenant, kb_version, ticket_id.
- Record citations (doc ids/urls) alongside the final message for auditability.

Notes (PL)
----------
- Agent wsparcia jest „knowledge-oriented” i ma fallback RAG (w przeciwieństwie do OpsAgent).
- Odpowiedzi powinny zawierać odnośniki do źródeł (cytowania) i jasne kroki „co dalej”.
- Jeśli brak treści w bazie wiedzy — lepiej zaproponować przekierowanie/eskalację niż zgadywać.

Usage (example)
---------------
>>> from agents.base import BaseAgent
>>> class SupportAgent(BaseAgent):
...     async def plan(self, request): ...
...     async def act(self, step, ctx): ...
...     async def finalize(self, ctx): ...
...
>>> agent = SupportAgent(tools=my_tools, retriever=my_retriever, tracer=my_tracer)
>>> reply = await agent.run(AgentRequest(user_input="VPN doesn't connect on Ubuntu 24.04"))

"""  # noqa: D205

from __future__ import annotations

from typing import List  # noqa: UP035

from services.api_gateway.src.agents.base import BaseAgent
from services.api_gateway.src.runtime.memory import Memory
from services.api_gateway.src.runtime import KeywordPlanner, RAG, ToolRegistry

class SupportAgent(BaseAgent):
    """Agent do obsługi zapytań użytkowników i zarządzania zgłoszeniami."""

    def __init__(
        self,
        tools: ToolRegistry,
        memory: Memory,
        planner: KeywordPlanner,
        rag: RAG,
    ):
        """Inicjalizuje agenta wsparcia.

        Args:
            tools: Rejestr dostępnych narzędzi.
            memory: Warstwa pamięci i audytu.
            planner: Planer oparty na słowach kluczowych.
            rag: System RAG do wyszukiwania w bazie wiedzy.

        """
        super().__init__(
            tools=tools,
            memory=memory,
            planner=planner,
            rag=rag,

            agent_name="support",
        )

    async def _get_contextual_info(
        self, query: str, tool_results: List[str]
    ) -> List[str]:
        """Implementacja strategii kontekstowej dla SupportAgent.

        Strategia tego agenta polega na aktywnym korzystaniu z RAG, jeśli
        narzędzia nie dostarczyły ostatecznej odpowiedzi (np. nie utworzono ticketa).

        Args:
            query: Oryginalne zapytanie użytkownika.
            tool_results: Wyniki zwrócone przez wykonane narzędzia.

        Returns:
            Lista fragmentów kontekstu z RAG lub pusta lista.

        """
        # Sprawdzamy, czy którekolwiek z narzędzi zakończyło interakcję
        # (w tym przypadku, czy utworzono ticket).
        is_interaction_complete = any("Utworzono zgłoszenie" in res for res in tool_results)

        # Jeśli interakcja nie jest zakończona, użyj RAG, aby znaleźć dodatkowe informacje.
        if not is_interaction_complete:
            return await self.rag.retrieve(query, k=4)

        # Gdy ticket został utworzony, nie ma potrzeby dalszego szukania w bazie wiedzy.
        return []
