from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from .base import LLMMessage
from .router import get_provider
from .guardrails import profanity_filter, validate_plan_json, clip_output

@dataclass
class LLMPlanStep:
    name: str
    args: Dict[str, Any]

@dataclass
class LLMPlan:
    steps: List[LLMPlanStep]

SYSTEM_PROMPT = (
    "You are a planning agent. Given a user query and a list of available tools, "
    "produce a STRICT JSON object with shape: {\"steps\":[{\"name\":\"tool_name\",\"args\":{...}}, ...]} "
    "Use only tools from the list if they are helpful; otherwise return {\"steps\":[]}. "
    "Do not include explanations. Output JSON only."
)

class LLMPlanner:
    """
    Prosty planer LLM:
    - prompt z listą tooli i pytaniem,
    - guardrails: blocklist i walidacja JSON,
    - zwrot listy kroków.
    """
    def __init__(self) -> None:
        self.provider = get_provider()

    async def make_plan(self, query: str, available_tools: List[str], claims: Dict[str, Any] | None = None) -> LLMPlan:
        if profanity_filter(query):
            # blokujemy wykonanie; plan pusty
            return LLMPlan(steps=[])

        tools_line = ", ".join(sorted(available_tools))
        messages = [
            LLMMessage(role="system", content=SYSTEM_PROMPT),
            LLMMessage(role="user", content=f"TOOLS: [{tools_line}]\nQUERY: {query}"),
        ]
        raw = await self.provider.chat(messages, max_tokens=256, temperature=0.0)
        plan = validate_plan_json(raw)

        return LLMPlan(steps=[LLMPlanStep(name=s.name, args=s.args) for s in plan.steps])

    async def summarize(self, query: str, results: List[str]) -> str:
        joined = "\n".join(results)
        content = f"Odpowiedź na: {query}\n\nWyniki narzędzi:\n{joined}"
        return clip_output(content)
