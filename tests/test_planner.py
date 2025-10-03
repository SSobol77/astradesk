# tests/test_planner.py

import asyncio
from runtime.planner import Planner

def test_planner_keywords():
    pl = Planner()
    plan = asyncio.run(pl.make("Utwórz ticket na awarię"))
    assert len(plan.steps) == 1
    assert plan.steps[0].tool_name == "create_ticket"

    plan2 = asyncio.run(pl.make("Sprawdź metryki CPU webapp"))
    assert plan2.steps[0].tool_name == "get_metrics"
