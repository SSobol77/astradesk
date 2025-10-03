# src/tools/tickets_proxy.py

# 
# Proxy do serwisu zarządzania ticketami (np. GitHub Issues, Jira, itp.)
# Używa httpx i tenacity do obsługi retry
# 

from __future__ import annotations
import os, httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

BASE = os.getenv("TICKETS_BASE_URL","http://ticket-adapter:8081")

@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type((httpx.HTTPError,))
)
async def create_ticket(title: str, body: str) -> str:
    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, read=10.0)) as client:
        r = await client.post(f"{BASE}/api/tickets", json={"title": title, "body": body})
        r.raise_for_status()
        data = r.json()
        return f"Ticket #{data['id']}: {data['title']}"
