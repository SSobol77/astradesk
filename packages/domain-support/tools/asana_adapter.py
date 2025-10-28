"""Minimal Asana adapter stub used by tests."""

from __future__ import annotations

from typing import Dict


class AsanaAdapter:
    async def create_task(self, task_data: Dict) -> Dict[str, str]:
        ticket = task_data.get("ticket_id", "unknown")
        return {"task_id": f"asana-{ticket}"}
