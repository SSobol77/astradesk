# SPDX-License-Identifier: Apache-2.0
"""
#tools/tickets_proxy.py

Narzędzie 'create_ticket' z bezpiecznym retry i kontrolowanym fallbackiem STUB,
gdy adapter biletów nie jest osiągalny (np. lokalny dev bez backendu).

tools.tickets_proxy — create_ticket z retry i STUB fallbackiem, jeśli adapter nieosiągalny.
Env:
  - TICKETS_BASE_URL (np. http://localhost:8082)
  - TICKETS_API_TOKEN (opcjonalnie)
  - TICKETS_DISABLE_STUB=1 aby wyłączyć fallback i zwracać błąd
"""

from __future__ import annotations

import os
import uuid
import logging
from typing import Any, Dict, Optional

import httpx
from httpx import ConnectError, ConnectTimeout, ReadTimeout, PoolTimeout, HTTPStatusError, RequestError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential, before_sleep_log

logger = logging.getLogger(__name__)

TICKETS_BASE_URL: str = os.getenv("TICKETS_BASE_URL", "http://localhost:8082").rstrip("/")
TICKETS_API_TOKEN: Optional[str] = os.getenv("TICKETS_API_TOKEN")
TICKETS_DISABLE_STUB: bool = os.getenv("TICKETS_DISABLE_STUB", "0").lower() in ("1", "true", "yes")

_http: httpx.AsyncClient | None = None


def _client() -> httpx.AsyncClient:
    global _http
    if _http is None:
        _http = httpx.AsyncClient(
            base_url=TICKETS_BASE_URL,
            timeout=httpx.Timeout(connect=3.0, read=15.0, write=15.0, pool=3.0),
        )
    return _http


def _stub_ticket(title: str, body: str) -> str:
    fake_id = f"TCK-{uuid.uuid4().hex[:8].upper()}"
    logger.info("tickets_proxy: STUB aktywny → %s", fake_id)
    return (
        f"✅ Utworzono zgłoszenie (STUB): {fake_id}\n"
        f"Tytuł: {title}\n"
        f"Opis: {body or '(brak)'}\n"
        f"Uwaga: backend ticketów nieosiągalny ({TICKETS_BASE_URL})."
    )


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, max=4.0),
    retry=retry_if_exception_type((ConnectError, ConnectTimeout, ReadTimeout, PoolTimeout, HTTPStatusError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
async def _call_adapter(title: str, body: str, *, claims: dict | None, request_id: str | None) -> str:
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if TICKETS_API_TOKEN:
        headers["Authorization"] = f"Bearer {TICKETS_API_TOKEN}"
    if request_id:
        headers["X-Request-ID"] = request_id
    if claims and "sub" in claims:
        headers["X-User-ID"] = str(claims["sub"])

    payload = {"title": title, "body": body}
    resp = await _client().post("/api/tickets", json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json() if resp.content else {}
    ticket_id = data.get("id") or data.get("ticketId") or f"TCK-{uuid.uuid4().hex[:8].upper()}"
    url = data.get("url") or f"{TICKETS_BASE_URL}/tickets/{ticket_id}"
    title_echo = data.get("title", title)
    return f"✅ Utworzono zgłoszenie: {ticket_id}\nLink: {url}\nTytuł: {title_echo}"


async def create_ticket(title: str, body: str, *, claims: dict | None = None, request_id: str | None = None) -> str:
    try:
        logger.info("Wysyłanie żądania utworzenia ticketa z tytułem: %r",
                    (title[:80] + "...") if len(title) > 80 else title)
        return await _call_adapter(title, body, claims=claims, request_id=request_id)

    except HTTPStatusError as e:
        logger.error("tickets_proxy: HTTP %s: %s", e.response.status_code, e.response.text)
        return f"❌ System zgłoszeń odrzucił żądanie (HTTP {e.response.status_code})."

    except (ConnectError, ConnectTimeout, ReadTimeout, PoolTimeout, RequestError) as e:
        logger.error("tickets_proxy: backend nieosiągalny %s — %s", TICKETS_BASE_URL, e)
        if not TICKETS_DISABLE_STUB:
            return _stub_ticket(title, body)
        return "❌ Błąd: system zgłoszeń jest chwilowo nieosiągalny. Spróbuj ponownie później."

    except Exception as e:
        logger.exception("tickets_proxy: nieoczekiwany błąd: %s", e)
        return "❌ Błąd: nieoczekiwany problem podczas tworzenia zgłoszenia."
