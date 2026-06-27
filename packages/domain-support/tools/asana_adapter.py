"""Minimal Asana adapter stub used by tests."""

from __future__ import annotations


class AsanaAdapter:
    async def create_task(self, task_data: dict) -> dict[str, str]:
        ticket = task_data.get('ticket_id', 'unknown')
        return {'task_id': f'asana-{ticket}'}
