"""Minimal Slack adapter stub used by tests."""

from __future__ import annotations

from typing import Dict


class SlackAdapter:
    async def post_message(self, message_data: Dict) -> Dict[str, str]:
        ticket = message_data.get("ticket_id", "unknown")
        return {"message_id": f"slack-{ticket}"}
