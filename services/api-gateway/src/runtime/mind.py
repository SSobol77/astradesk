# SPDX-License-Identifier: Apache-2.0
# services/api-gateway/src/runtime/mind.py
"""AstraMind Engine: Meta-controller for LLM routing, intent graph planning, and self-reflection.

Handles dynamic intent graph generation from natural language, provider routing
based on cost/quality/latency, and RLHF-style evaluation of step results.
Integrates with OPA for policy enforcement and OTel for observability.

Author: Siergej Sobolewski
Since: 2025-10-25
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Tuple

import torch  # PyTorch 2.9 for embeddings & reward model
from opentelemetry import trace  # AstraOps/OTel tracing
from pydantic import BaseModel, Field

from runtime.policy import policy as opa_policy  # OPA facade

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# LLM Provider Protocol (decoupled from concrete impl)
# --------------------------------------------------------------------------- #
class LLMProvider(Protocol):
    """Minimal interface for LLM providers (OpenAI, Bedrock, vLLM, etc.)."""

    async def generate_graph(
        self, prompt: str, embeddings: Optional[torch.Tensor] = None
    ) -> "IntentGraph": ...
    async def chat(
        self,
        messages: List[Dict[str, str]],
        params: Optional[Dict[str, Any]] = None,
    ) -> str: ...
    async def embed(self, text: str) -> torch.Tensor: ...


# --------------------------------------------------------------------------- #
# Intent Graph Models
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class IntentNode:
    """Single node in the intent graph."""
    id: str
    action: str
    arguments: Dict[str, Any]
    dependencies: List[str] = None  # Node IDs


class IntentGraph(BaseModel):
    """Directed acyclic graph of tool invocations."""
    nodes: List[IntentNode] = Field(..., description="List of intent nodes")
    start_node: str = Field(..., description="Entry point node ID")

    def topological_order(self) -> List[IntentNode]:
        """Return nodes in execution order."""
        import networkx as nx

        G = nx.DiGraph()
        for node in self.nodes:
            G.add_node(node.id)
            for dep in node.dependencies or []:
                G.add_edge(dep, node.id)
        return [G.nodes[n]["data"] for n in nx.topological_sort(G)]


# --------------------------------------------------------------------------- #
# AstraMind Core
# --------------------------------------------------------------------------- #
class AstraMind:
    """
    AstraMind Engine: Intelligent orchestrator for multi-step agent flows.

    Features:
    - Dynamic Intent Graph planning via LLM.
    - Provider routing (cost, latency, quality).
    - Self-reflection with local reward model (PyTorch 2.9).
    - OPA governance on planning.
    - OTel tracing.
    """

    def __init__(self, providers: Dict[str, LLMProvider]) -> None:
        """Initialize with available LLM providers.

        Args:
            providers: Mapping of provider names to implementations.
        """
        self.providers = providers
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.reward_model = self._load_reward_model()
        self.tracer = trace.get_tracer(__name__)

    # ----------------------------------------------------------------------- #
    # Provider Routing
    # ----------------------------------------------------------------------- #
    def _route_provider(self, prompt: str, claims: Optional[Dict[str, Any]] = None) -> LLMProvider:
        """Route to best provider based on policy, cost, and prompt characteristics."""
        with self.tracer.start_as_current_span("mind.route_provider"):
            # OPA check: e.g., restrict high-cost models
            if claims:
                try:
                    opa_policy.authorize("mind.plan", claims, {"prompt_length": len(prompt)})
                except Exception:
                    logger.info("OPA restricted high-tier model, falling back to default")
                    return self.providers.get("openai", list(self.providers.values())[0])

            # Simple heuristic: short prompt → cheap, long → quality
            if len(prompt) < 100 and "vllm" in self.providers:
                return self.providers["vllm"]
            return self.providers.get("openai", list(self.providers.values())[0])

    # ----------------------------------------------------------------------- #
    # Intent Graph Planning
    # ----------------------------------------------------------------------- #
    async def plan(
        self, prompt: str, claims: Optional[Dict[str, Any]] = None
    ) -> IntentGraph:
        """
        Generate Intent Graph from natural language prompt.

        Workflow:
        1. OPA governance check.
        2. Route to LLM provider.
        3. Generate structured graph.
        4. Validate and return.

        Args:
            prompt: User intent in natural language.
            claims: JWT claims for RBAC/ABAC.

        Returns:
            IntentGraph with execution plan.
        """
        with self.tracer.start_as_current_span("mind.plan") as span:
            span.set_attribute("prompt", prompt[:100])
            span.set_attribute("prompt_length", len(prompt))

            # Governance
            if claims:
                opa_policy.authorize("mind.plan", claims, {"prompt": prompt})

            provider = self._route_provider(prompt, claims)

            try:
                # Optional: embed prompt for semantic routing
                embeddings = await provider.embed(prompt) if hasattr(provider, "embed") else None

                with self.tracer.start_as_current_span("llm.generate_graph"):
                    graph = await provider.generate_graph(prompt, embeddings)

                span.set_attribute("node_count", len(graph.nodes))
                return graph

            except Exception as e:
                span.record_exception(e)
                logger.error(f"Planning failed: {e}", exc_info=True)
                raise RuntimeError(f"Intent planning failed: {str(e)}") from e

    # ----------------------------------------------------------------------- #
    # Self-Reflection & Evaluation
    # ----------------------------------------------------------------------- #
    def _load_reward_model(self) -> torch.nn.Module:
        """Load lightweight reward model for step evaluation (PyTorch 2.9)."""
        # Placeholder: in production, load from HF or local checkpoint
        class RewardModel(torch.nn.Module):
            def forward(self, x: torch.Tensor) -> torch.Tensor:
                return torch.sigmoid(torch.randn(1) * 0.1 + 0.8)  # Mock

        model = RewardModel().to(self.device)
        model.eval()
        return torch.compile(model, mode="reduce-overhead", fullgraph=True)

    async def evaluate(
        self,
        step_result: str,
        expected: Optional[Dict[str, Any]] = None,
        query: Optional[str] = None,
    ) -> float:
        """
        Score step quality using local reward model (RLHF-style).

        Args:
            step_result: Tool output.
            expected: Optional expected schema.
            query: Original user query for context.

        Returns:
            Score in [0.0, 1.0].
        """
        with self.tracer.start_as_current_span("mind.evaluate"):
            try:
                # Simple heuristic + reward model
                inputs = torch.tensor([len(step_result)], device=self.device).float()
                with torch.no_grad():
                    score = self.reward_model(inputs).item()

                # Boost if matches expected
                if expected and isinstance(step_result, str):
                    try:
                        data = json.loads(step_result)
                        if all(k in data for k in expected):
                            score = min(1.0, score + 0.2)
                    except json.JSONDecodeError:
                        pass

                return max(0.0, min(1.0, score))
            except Exception as e:  # pragma: no cover
                logger.warning(f"Evaluation failed: {e}")
                return 0.5  # Neutral

    # ----------------------------------------------------------------------- #
    # Reflection via LLM
    # ----------------------------------------------------------------------- #
    async def reflect(
        self,
        query: str,
        result: str,
        provider_name: str = "openai",
    ) -> float:
        """LLM-based reflection on result relevance."""
        provider = self.providers.get(provider_name)
        if not provider:
            return 0.5

        system = (
            "Evaluate how well the result answers the query. "
            "Return JSON: {'score': float(0.0-1.0)}. No explanations."
        )
        user = f"Query: {query}\nResult: {result}"

        try:
            raw = await provider.chat(
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                {"max_tokens": 50, "temperature": 0.0},
            )
            data = json.loads(raw.strip())
            return max(0.0, min(1.0, float(data.get("score", 0.5))))
        except Exception:
            return 0.5
