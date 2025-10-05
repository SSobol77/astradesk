# src/tools/tickets_proxy.py
"""Niezawodne proxy do serwisu zarządzania zgłoszeniami (ticketami).

Moduł ten pełni rolę klienta HTTP dla wewnętrznego serwisu `ticket-adapter`,
który zarządza cyklem życia zgłoszeń.
"""
from __future__ import annotations

import logging
import os

import httpx
from httpx import (
    ConnectError,
    ConnectTimeout,
    HTTPStatusError,
    PoolTimeout,
    ReadTimeout,
    RequestError,
)

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# --- Konfiguracja ---
TICKETS_BASE_URL: str = os.getenv("TICKETS_BASE_URL", "http://ticket-adapter:8081")
RETRY_ATTEMPTS: int = 3
RETRY_WAIT_MULTIPLIER: float = 0.5
RETRY_MAX_WAIT: float = 4.0

# --- Współdzielony klient HTTP ---
_http_client = httpx.AsyncClient(
    base_url=TICKETS_BASE_URL,
    timeout=httpx.Timeout(5.0, read=15.0),
)

# --- Konfiguracja Retry ---
RETRYABLE_EXCEPTIONS = (
    ConnectError,
    ReadTimeout,
    ConnectTimeout,
    PoolTimeout,
)

@retry_if_exception
def _is_server_error(exc: BaseException) -> bool:
    """Zwraca True, jeśli wyjątek to błąd HTTP 5xx."""
    return isinstance(exc, HTTPStatusError) and exc.response.status_code >= 500

@retry(
    reraise=True,
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=RETRY_WAIT_MULTIPLIER, max=RETRY_MAX_WAIT),
    retry=(retry_if_exception_type(RETRYABLE_EXCEPTIONS) | _is_server_error),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
async def create_ticket(
    title: str, body: str, *, claims: dict | None = None, request_id: str | None = None
) -> str:
    """Tworzy nowe zgłoszenie (ticket) poprzez wywołanie serwisu ticket-adapter."""
    logger.info(f"Wysyłanie żądania utworzenia ticketa z tytułem: '{title[:50]}...'")
    
    payload = {"title": title, "body": body}
    headers = {}
    if request_id:
        headers["X-Request-ID"] = request_id
    if claims and "sub" in claims:
        headers["X-User-ID"] = claims["sub"]

    try:
        response = await _http_client.post("/api/tickets", json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        ticket_id = data.get("id", "N/A")
        ticket_title = data.get("title", "")
        
        logger.info(f"Pomyślnie utworzono ticket #{ticket_id}")
        return f"Utworzono zgłoszenie #{ticket_id}: '{ticket_title}'"

    # ZMIANA: Użycie bezpośrednich nazw klas
    except HTTPStatusError as e:
        logger.error(
            f"Błąd HTTP {e.response.status_code} podczas tworzenia ticketa. "
            f"Odpowiedź serwera: {e.response.text}"
        )
        raise
    except RequestError as e:
        logger.error(f"Błąd sieciowy podczas tworzenia ticketa: {e}")
        raise
    except Exception as e:
        logger.critical(f"Nieoczekiwany błąd podczas tworzenia ticketa: {e}", exc_info=True)
        raise
