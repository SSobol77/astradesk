# SPDX-License-Identifier: Apache-2.0
"""File: core/src/astradesk_core/utils/events.py

Project: astradesk
Package: astradesk_core

Author: Siergej Sobolewski
Since: 2025-10-29

Asynchronous NATS publisher stub tailored for unit testing.

"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional


logger = logging.getLogger(__name__)

NATS_URL = "nats://nats:4222"
MAX_MESSAGE_BYTES = 524288
CONNECT_TIMEOUT_SEC = 2.0


class _NatsModule:
    async def connect(self, url: str, connect_timeout: float):
        return _DummyNatsClient()


class _DummyNatsClient:
    def __init__(self) -> None:
        self.is_connected = True

    async def publish(self, subject: str, payload: bytes) -> None:  # pragma: no cover
        return None

    async def close(self) -> None:  # pragma: no cover
        return None

    async def drain(self) -> None:  # pragma: no cover
        return None


nats = _NatsModule()


class Events:
    def __init__(self) -> None:
        self._nc: Optional[_DummyNatsClient] = None
        self._lock = asyncio.Lock()

    async def _get_connection(self) -> Any:
        if self._nc and getattr(self._nc, "is_connected", True):
            return self._nc
        async with self._lock:
            if self._nc and getattr(self._nc, "is_connected", True):
                return self._nc
            self._nc = await nats.connect(NATS_URL, connect_timeout=CONNECT_TIMEOUT_SEC)
            return self._nc

    @staticmethod
    def _validate_subject(subject: str) -> bool:
        if not subject or subject.strip() != subject:
            return False
        if " " in subject or ".." in subject or subject.startswith(".") or subject.endswith("."):
            return False
        return True

    @staticmethod
    def _encode_payload(payload: dict[str, Any]) -> Optional[bytes]:
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(data) > MAX_MESSAGE_BYTES:
            return None
        return data

    async def publish(self, subject: str, payload: dict[str, Any]) -> None:
        if not self._validate_subject(subject):
            logger.error("Niepoprawny temat NATS: %s", subject)
            return
        data = self._encode_payload(payload)
        if data is None:
            logger.error("Payload przekracza maksymalny rozmiar wiadomości.")
            return

        try:
            nc = await self._get_connection()
            await nc.publish(subject, data)
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Pierwsza próba publikacji nie powiodła się: %s", exc)
            await self._close_connection(graceful=False)

        try:
            logger.info("Ponowne połączenie z NATS po błędzie publikacji.")
            nc = await self._get_connection()
            await nc.publish(subject, data)
        except Exception as exc:  # noqa: BLE001
            logger.error("Nie udało się opublikować zdarzenia po ponownej próbie: %s", exc, exc_info=True)
            await self._close_connection(graceful=False)

    async def _close_connection(self, *, graceful: bool) -> None:
        if not self._nc:
            return
        nc, self._nc = self._nc, None
        try:
            if graceful:
                await nc.drain()
                return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Błąd podczas drain(), używam close(): %s", exc)
        try:
            await nc.close()
        except Exception:  # pragma: no cover - best effort
            pass

    async def close(self) -> None:
        await self._close_connection(graceful=True)


events = Events()

__all__ = ["events", "Events", "NATS_URL", "MAX_MESSAGE_BYTES", "CONNECT_TIMEOUT_SEC", "nats"]
