# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/src/gateway/orchestrator.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for services/api-gateway/src/gateway/orchestrator.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Business logic layer for agent orchestration: agent selection, planner choice (LLM vs. keyword),
tool execution with governance, fallback handling, Intent Graph with self-reflection, and final response assembly.

**Pure domain layer** - no FastAPI/HTTP dependencies. Fully testable, async-native, OTel-traced.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import networkx as nx  # Intent Graph
from agents.base import BaseAgent
from model_gateway.guardrails import PlanModel
from model_gateway.llm_planner import LLMPlanner
from opa_client.opa import OpaClient  # Governance
from opentelemetry import trace  # AstraOps/OTel
from runtime.authz import approval_from_mapping
from runtime.memory import Memory
from runtime.models import AgentRequest, AgentResponse, ToolCall
from runtime.pii import attach_classification, safe_preview
from runtime.registry import ToolRegistry

import asyncpg
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class DomainError(Exception):
    """Base exception for domain-level errors."""

    pass


class AgentNotFoundError(DomainError):
    """Raised when requested agent is not available."""

    def __init__(self, agent_name: str):
        super().__init__(f"Agent '{agent_name}' not found")
        self.agent_name = agent_name


class PolicyViolationError(DomainError):
    """Raised when OPA denies access."""

    def __init__(self, action: str):
        super().__init__(f'Access denied by policy for action: {action}')
        self.action = action


class AgentOrchestrator:
    """Orchestrates the full agent execution lifecycle with governance, reflection, and fallback."""

    def __init__(
        self,
        llm_planner: LLMPlanner | None,
        agents: dict[str, BaseAgent],
        tools: ToolRegistry,
        pg_pool: asyncpg.Pool,
        redis: redis.Redis,
        opa_client: OpaClient,
    ) -> None:
        """Initializes the orchestrator with all dependencies.

        Args:
            llm_planner: Optional LLM-based planner (can be None for fallback-only mode).
            agents: Mapping of agent names to initialized BaseAgent instances.
            tools: Central tool registry.
            pg_pool: PostgreSQL connection pool.
            redis: Redis async client.
            opa_client: OPA client for policy enforcement.
        """
        self.llm_planner = llm_planner
        self.agents = agents
        self.tools = tools
        self.pg_pool = pg_pool
        self.redis = redis
        self.opa_client = opa_client
        self.tracer = trace.get_tracer(__name__)

    async def run(
        self,
        req: AgentRequest,
        claims: dict[str, Any],
        request_id: str,
        roles: tuple[str, ...] = (),
    ) -> AgentResponse:
        """Main execution entrypoint with LLM → Keyword → Fallback strategy.

        Args:
            req: Incoming agent request.
            claims: JWT claims from auth layer.
            request_id: Unique trace ID.
            roles: Normalized principal roles from the OIDC layer. These — not the
                raw claims — feed the RBAC choke point, and they are propagated
                identically to the LLM-planned and keyword-fallback paths
                (``INV-DUAL-PATH``).

        Returns:
            AgentResponse with output and invoked tools.

        Raises:
            AgentNotFoundError: If agent not found.
            PolicyViolationError: If OPA denies access.
        """
        with self.tracer.start_as_current_span('orchestrator.run') as span:
            # Ingress boundary: classify the raw input once and propagate the
            # classification with the request (INV-PII-2). Only a redacted,
            # bounded preview reaches the span (INV-PII-1/INV-PII-4).
            classification = attach_classification(req.input)
            span.set_attribute('request_id', request_id)
            span.set_attribute('agent', req.agent.value)
            span.set_attribute('input_preview', safe_preview(req.input, 100))
            span.set_attribute('input_classification', sorted(classification))

            context = {
                **req.meta,
                'claims': claims,
                'roles': tuple(roles),
                'request_id': request_id,
                'data_classification': sorted(classification),
            }
            memory = Memory(self.pg_pool, self.redis)

            # Try LLM path first
            if self.llm_planner:
                with self.tracer.start_as_current_span('orchestrator.llm_path'):
                    response = await self._try_llm_path(req, context, memory, request_id)
                    if response:
                        return response

            # Fallback to keyword-based agent
            with self.tracer.start_as_current_span('orchestrator.fallback_path'):
                return await self._run_fallback_path(req, context, request_id)

    async def _try_llm_path(
        self, req: AgentRequest, context: dict[str, Any], memory: Memory, request_id: str
    ) -> AgentResponse | None:
        """Attempts execution using LLMPlanner with Intent Graph and self-reflection."""
        if not self.llm_planner:
            return None

        with self.tracer.start_as_current_span('llm_planner.make_plan') as span:
            try:
                llm_plan: PlanModel = await asyncio.wait_for(
                    self.llm_planner.make_plan(req.input, available_tools=self.tools.names()),
                    timeout=15.0,
                )
            except TimeoutError:
                span.record_exception(TimeoutError('LLM plan generation timeout'))
                return None
            except Exception as e:
                span.record_exception(e)
                logger.warning(f'[{request_id}] LLM plan failed: {e}')
                return None

        if not llm_plan or not llm_plan.steps:
            logger.info(f'[{request_id}] LLM generated empty plan. Falling back.')
            return None

        logger.info(f'[{request_id}] LLM plan: {len(llm_plan.steps)} steps')

        # Build Intent Graph
        graph = nx.DiGraph()
        for i, step in enumerate(llm_plan.steps):
            graph.add_node(i, step=step, executed=False)

        results: list[str] = []
        invoked_tools: list[ToolCall] = []

        # Execute with reflection and replan
        for node_id in graph.nodes:
            step = graph.nodes[node_id]['step']
            tool_call = ToolCall(name=step.name, arguments=step.args)

            # OPA governance
            decision = await self.opa_client.check_policy(
                input={'user': context['claims'], 'action': step.name},
                policy_path='astradesk/tools',
            )
            if not decision.get('result', False):
                raise PolicyViolationError(step.name)

            # Execute with timeout (RBAC enforced inside tools.execute from
            # normalized roles + approval id — identical to the keyword-fallback
            # path). write/execute tools deny without an approval/change record.
            try:
                result = await asyncio.wait_for(
                    self.tools.execute(
                        step.name,
                        roles=context.get('roles', ()),
                        approval_id=approval_from_mapping(context),
                        claims=context['claims'],
                        **step.args,
                    ),
                    timeout=30.0,
                )
            except TimeoutError:
                result = 'Tool execution timeout'
            except Exception as e:
                result = f'Tool error: {e!s}'

            results.append(str(result))
            invoked_tools.append(tool_call)
            graph.nodes[node_id]['executed'] = True
            graph.nodes[node_id]['result'] = result

            # Self-reflection
            score = await self._reflect_step(req.input, result, request_id)

            if score < 0.7:
                logger.info(f'[{request_id}] Low reflection score ({score:.2f}). Replanning...')
                with self.tracer.start_as_current_span('llm_planner.replan'):
                    new_plan = await self.llm_planner.replan(req.input, results)
                    if new_plan and new_plan.steps:
                        # Add new branch to graph
                        base = len(graph.nodes)
                        for j, new_step in enumerate(new_plan.steps):
                            new_node = base + j
                            graph.add_node(new_node, step=new_step, executed=False)
                            graph.add_edge(node_id, new_node)

        # Final summarization
        with self.tracer.start_as_current_span('llm_planner.summarize'):
            output = await self.llm_planner.summarize(req.input, results)

        await memory.store_dialogue(req.agent.value, req.input, output, context)

        return AgentResponse(
            output=output,
            reasoning_trace_id=request_id,
            invoked_tools=invoked_tools,
        )

    async def _run_fallback_path(
        self, req: AgentRequest, context: dict[str, Any], request_id: str
    ) -> AgentResponse:
        """Executes fallback using keyword-based agent (SupportAgent, BillingAgent, etc.)."""
        agent = self.agents.get(req.agent.value)
        if not agent:
            raise AgentNotFoundError(req.agent.value)

        logger.info(f'[{request_id}] Running fallback agent: {req.agent.value}')

        output, invoked_tools = await agent.run(req.input, context)

        return AgentResponse(
            output=output,
            reasoning_trace_id=request_id,
            invoked_tools=invoked_tools,
        )

    async def _reflect_step(self, query: str, result: str, request_id: str) -> float:
        """Evaluates step quality using LLMPlanner (self-reflection)."""
        if not self.llm_planner:
            return 1.0

        with self.tracer.start_as_current_span('reflection.step'):
            system = (
                'Evaluate how well this tool result addresses the user query. '
                'Return JSON: {"score": float(0.0-1.0)}. No explanation.'
            )
            user = f'Query: "{query}"\nResult: "{result}"'

            try:
                raw = await self.llm_planner.chat(
                    [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
                    params={'max_tokens': 50, 'temperature': 0.0},
                )
                data = json.loads(raw.strip())
                score = float(data.get('score', 0.5))
                return max(0.0, min(1.0, score))
            except Exception as e:
                logger.warning(f'[{request_id}] Reflection failed: {e}')
                return 0.5
