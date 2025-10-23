# SPDX-License-Identifier: Apache-2.0
"""File: services/gateway-python/src/runtime/events.py
Project: AstraDesk Framework — API Gateway
Description:
    Lightweight, async NATS publisher (publish-only) with lazy connection,
    concurrency-safe access, and best-effort delivery semantics. Designed to
    minimize latency impact on API request paths while still emitting useful
    operational/audit events.

Author: Siergej Sobolewski
Since: 2025-10-07

Overview
--------
- Lazy connect: establish NATS connection on first publish, not at import/startup.
- Concurrency-safe: guard connection lifecycle with an `asyncio.Lock`.
- Best-effort delivery: on publish failure, attempt a single reconnect + retry;
  errors are logged and not raised to callers on the hot path.
- Validation: subject format and message size are enforced before send.

Configuration (env)
-------------------
- NATS_URL                 : NATS server URL (default: "nats://nats:4222").
- NATS_MAX_MESSAGE_BYTES   : max serialized payload size in bytes (default: 524288).
- NATS_CONNECT_TIMEOUT_SEC : connection timeout in seconds (default: 2.0).

Responsibilities
----------------
- `_get_connection()` : obtain a connected `nats.NATS` client (lazy, shared).
- `_validate_subject(subject)` : basic NATS subject sanity checks.
- `_encode_payload(payload)`  : compact JSON serialization with size guard.
- `publish(subject, payload)` : best-effort JSON publish with reconnect-once.
- `close()`                   : graceful shutdown (`drain` → fallback `close`).

Security & safety
-----------------
- Do not log secrets; redact sensitive fields before calling `publish`.
- Validate subject and payload size to avoid malformed or excessive messages.
- Keep reconnect logic bounded to avoid cascading failures during outages.

Performance
-----------
- Minimal overhead in success path (single publish call after cached connect).
- Compact JSON encoding (no whitespace) to reduce payload size.
- Connection reuse via a module-scoped shared publisher instance.

Usage (example)
---------------
>>> from runtime.events import events
>>> await events.publish("astradesk.audit", {"action": "ticket.created", "ticketId": 123})
# On application shutdown:
>>> await events.close()

Notes
-----
- This module focuses on publish-only semantics. For subscriptions/streams,
  implement separate consumers with backpressure and retry policies.
- Consider circuit breaking and rate limiting upstream if event volumes spike.

Notes (PL):
-----------
Moduł do publikacji zdarzeń w systemie NATS.

Ten moduł dostarcza lekką, asynchroniczną warstwę do publikowania zdarzeń
(publish-only) w systemie NATS. Jest zaprojektowany z myślą o niezawodności
i minimalnym wpływie na wydajność krytycznych ścieżek aplikacji, takich jak
przetwarzanie żądań API.

Główne cechy:
- **Leniwe połączenie**: Połączenie z serwerem NATS jest nawiązywane dopiero
  przy pierwszej próbie publikacji, co przyspiesza start aplikacji.
- **Bezpieczeństwo współbieżności**: Używa `asyncio.Lock` do ochrony przed
  wyścigami (race conditions) podczas zarządzania połączeniem.
- **Logika "Best-Effort"**: W przypadku problemów z połączeniem, moduł podejmuje
  jedną próbę ponownego nawiązania połączenia. Błędy nie są propagowane wyżej,
  aby nie blokować działania aplikacji, ale są rejestrowane w logach.
- **Walidacja**: Sprawdza poprawność formatu tematu (subject) oraz limit
  rozmiaru wiadomości przed wysłaniem.

Konfiguracja (zmienne środowiskowe):
- `NATS_URL`: URL serwera NATS (domyślnie: "nats://nats:4222").
- `NATS_MAX_MESSAGE_BYTES`: Maksymalny rozmiar wiadomości w bajtach (domyślnie: 512 KB).
- `NATS_CONNECT_TIMEOUT_SEC`: Timeout dla nawiązania połączenia (domyślnie: 2s).

"""  # noqa: D205

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

import nats
from nats.aio.client import Client as NATSClient

# --- Konfiguracja ---
NATS_URL: str = os.getenv("NATS_URL", "nats://nats:4222").strip()
MAX_MESSAGE_BYTES: int = int(os.getenv("NATS_MAX_MESSAGE_BYTES", "524288"))  # 512 KiB
CONNECT_TIMEOUT_SEC: float = float(os.getenv("NATS_CONNECT_TIMEOUT_SEC", "2.0"))

logger = logging.getLogger(__name__)


class Events:
    """Prosty publisher NATS z leniwym łączeniem i logiką "best-effort".

    Zarządza współdzielonym połączeniem NATS i udostępnia interfejs do
    publikowania zdarzeń w bezpieczny sposób.

    Attributes
    ----------
        _nc: Aktywny klient NATS lub None, jeśli nie połączono.
        _lock: Blokada asyncio zapewniająca bezpieczeństwo współbieżności.

    """

    __slots__ = ("_lock", "_nc")

    def __init__(self) -> None:
        """Inicjalizuje instancję publishera."""
        self._nc: NATSClient | None = None
        self._lock = asyncio.Lock()

    async def _get_connection(self) -> NATSClient:
        """Zapewnia aktywne połączenie z NATS (leniwie tworzone i współdzielone).

        Returns
        -------
            Aktywny, połączony klient nats.NATS.

        Raises
        ------
            nats.errors.Error: W przypadku problemów z nawiązaniem połączenia.

        """
        if self._nc and self._nc.is_connected:
            return self._nc

        async with self._lock:
            if self._nc and self._nc.is_connected:
                return self._nc

            logger.info(f"Nawiązywanie połączenia z NATS pod adresem: {NATS_URL}")
            # `nats.connect` zwraca instancję `nats.aio.client.Client`,
            # która jest otypowana jako `NATSClient`.
            self._nc = await nats.connect(
                NATS_URL, connect_timeout=CONNECT_TIMEOUT_SEC
            )
            logger.info("Połączenie z NATS zostało pomyślnie nawiązane.")
            return self._nc

    @staticmethod
    def _validate_subject(subject: str) -> None:
        """Waliduje temat NATS pod kątem zgodności z podstawowymi zasadami.

        Args:
        ----
            subject: Temat do walidacji.

        Raises:
        ------
            ValueError: Jeśli temat jest niepoprawny.

        """
        if not subject or subject.strip() != subject:
            raise ValueError(
                "Temat nie może być pusty i nie może zawierać skrajnych białych znaków."
            )
        if " " in subject:
            raise ValueError("Temat nie może zawierać spacji.")
        if ".." in subject or subject.startswith(".") or subject.endswith("."):
            raise ValueError(
                "Temat nie może zawierać pustych segmentów ani zaczynać/kończyć się kropką."
            )

    @staticmethod
    def _encode_payload(payload: dict[str, Any]) -> bytes:
        """Serializuje payload do JSON (UTF-8) i weryfikuje jego rozmiar.

        Args:
        ----
            payload: Słownik do serializacji.

        Returns:
        -------
            Zserializowany payload jako ciąg bajtów.

        Raises:
        ------
            ValueError: Jeśli zserializowany payload przekracza `MAX_MESSAGE_BYTES`.

        """
        data = json.dumps(
            payload, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        if len(data) > MAX_MESSAGE_BYTES:
            raise ValueError(
                f"Rozmiar wiadomości ({len(data)} B) przekracza limit ({MAX_MESSAGE_BYTES} B)."
            )
        return data

    async def publish(self, subject: str, payload: dict[str, Any]) -> None:
        """Publikuje komunikat JSON na wskazany temat NATS ("best-effort").

        Proces obejmuje walidację, serializację, a następnie próbę publikacji.
        W razie błędu podejmowana jest jedna próba ponownego nawiązania
        połączenia i ponownej publikacji. Błędy są logowane, ale nie są
        propagowane wyżej, aby nie blokować ścieżki krytycznej aplikacji.

        Args:
        ----
            subject: Temat NATS (np. "astradesk.audit").
            payload: Słownik do zserializowania i opublikowania.

        """
        try:
            self._validate_subject(subject)
            data = self._encode_payload(payload)
        except ValueError as e:
            logger.error(f"Błąd walidacji wiadomości dla tematu '{subject}': {e}")
            return

        try:
            nc = await self._get_connection()
            if nc:
                await nc.publish(subject, data)
            else:
                raise ConnectionError("Nie udało się uzyskać połączenia z NATS.")
        except Exception as e:
            logger.warning(
                f"Nie udało się opublikować wiadomości w NATS dla tematu '{subject}'. "
                f"Próba ponownego połączenia. Błąd: {e}"
            )
            # Druga, ostateczna próba
            try:
                async with self._lock:
                    if self._nc:
                        try:
                            await self._nc.close()
                        except Exception as close_exc:
                            logger.debug(
                                "Wystąpił niekrytyczny błąd podczas zamykania starego połączenia NATS.",
                                exc_info=close_exc
                            )

                    self._nc = await nats.connect(
                        NATS_URL, connect_timeout=CONNECT_TIMEOUT_SEC
                    )

                logger.info("Ponowne połączenie z NATS zostało pomyślnie nawiązane.")
                if self._nc:
                    await self._nc.publish(subject, data)
                    logger.info(f"Wiadomość dla tematu '{subject}' została pomyślnie opublikowana po ponownym połączeniu.")
                else:
                    raise ConnectionError("Nie udało się uzyskać połączenia z NATS po ponownej próbie.")
            except Exception as final_e:
                logger.error(
                    f"Ostateczne niepowodzenie publikacji w NATS dla tematu '{subject}' "
                    f"po próbie ponownego połączenia. Błąd: {final_e}",
                    exc_info=True,
                )

    async def close(self) -> None:
        """Zamyka aktywne połączenie z NATS w sposób bezpieczny.

        Najpierw próbuje opróżnić bufor (`drain`), a w razie błędu
        przechodzi do twardego zamknięcia (`close`).
        """
        async with self._lock:
            if self._nc:
                logger.info("Zamykanie połączenia z NATS...")
                try:
                    await self._nc.drain()
                    logger.info("Połączenie z NATS zostało pomyślnie zamknięte (drain).")
                except Exception as e:
                    logger.warning(f"Nie udało się wykonać 'drain' na połączeniu NATS: {e}. Próba 'close'.")
                    try:
                        await self._nc.close()
                        logger.info("Połączenie z NATS zostało zamknięte (close).")
                    except Exception as close_e:
                        logger.error(f"Nie udało się zamknąć połączenia NATS: {close_e}", exc_info=True)
                finally:
                    self._nc = None


# Globalna, współdzielona instancja publishera.
events = Events()
