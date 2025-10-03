# src/agents/ops.py
from __future__ import annotations
from typing import Dict, Any
from runtime.planner import Planner
from runtime.registry import ToolRegistry
from runtime.memory import Memory
from runtime.rag import RAG

class OpsAgent:
    def __init__(self, tools: ToolRegistry, memory: Memory, planner: Planner, rag: RAG):
        self.tools, self.memory, self.planner, self.rag = tools, memory, planner, rag

    async def run(self, query: str, context: Dict[str, Any]) -> str:
        plan = await self.planner.make(query)
        results: list[str] = []
        for step in plan.steps:
            results.append(await self.tools.get(step.tool_name)(**step.args))
        if not results:
            results = await self.rag.retrieve(query, 3)
        final = await self.planner.finalize(query, results, [])
        await self.memory.store_dialogue("ops", query, final, context)
        return final

    # fragment pętli wykonywania planu)
    async def run(self, query: str, context: Dict[str, Any]) -> str:
        plan = await self.planner.make(query)
        results: list[str] = []
        for step in plan.steps:
            tool = self.tools.get(step.tool_name)
            # PRZEKAZUJEMY claims do toola (RBAC)
            args = {**step.args, "claims": context.get("claims")}
            res = await tool(**args)
            results.append(res)
        # ...
