# src/runtime/events.py
# -*- coding: utf-8 -*-
# Program jest objęty licencją Apache-2.0.
# Copyright 2024
# Autor: Siergej Sobolewski
#
# Cel modułu:
# ------------
# Lekka warstwa pub (publish-only) do NATS wykorzystywana przez resztę systemu
# (np. do publikacji zdarzeń audytowych). Moduł utrzymuje leniwe połączenie
# z serwerem NATS, zapewnia prostą serializację JSON oraz minimalną ochronę:
# - walidacja nazwy tematu (subject),
# - limit rozmiaru komunikatu,
# - best-effort reconnect przy publikacji.
#
# Założenia:
# ----------
# - Zależność: nats-py (async), JSON payload (UTF-8).
# - Subskrypcje i JetStream nie są tu obsługiwane (to inna odpowiedzialność).
#
# Przykład użycia:
# ----------------
#   from runtime.events import events
#   await events.publish("astradesk.audit", {"actor":"support","action":"create_ticket"})
#
# Zmienna środowiskowa:
# ---------------------
#   NATS_URL = "nats://nats:4222"  # domyślnie; ustaw wg swojej infrastruktury
#

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Optional

import nats

# ---------------------------------------------------------------------------
# Konfiguracja
# ---------------------------------------------------------------------------

NATS_URL: str = os.getenv("NATS_URL", "nats://nats:4222").strip()

# Twardy limit rozmiaru publikowanego komunikatu (w bajtach).
# NATS domyślnie dopuszcza do ~1MB, ale warto mieć własny "bezpiecznik".
MAX_MESSAGE_BYTES: int = int(os.getenv("NATS_MAX_MESSAGE_BYTES", "524288"))  # 512 KiB

# Timeout ustanowienia połączenia (sekundy).
CONNECT_TIMEOUT_SEC: float = float(os.getenv("NATS_CONNECT_TIMEOUT_SEC", "2"))

# ---------------------------------------------------------------------------
# Implementacja
# ---------------------------------------------------------------------------


class Events:
    """
    Prosty publisher NATS z leniwym łączeniem i minimalnymi zabezpieczeniami.

    Atrybuty:
        _nc:   aktualny klient NATS (lub None, jeśli niepołączony),
        _lock: asynchroniczna blokada chroniąca sekcję łączenia (race-safety).

    Uwaga:
        - Klasa jest *bezpieczna współbieżnie* (wewnętrzny lock).
        - Publikacja jest "best-effort": wyjątków z reconnect nie propagujemy
          dalej jeśli samo ponowienie też się nie powiedzie (żeby nie blokować
          ścieżek krytycznych). Logowanie błędów zostawiamy warstwie wyżej.
    """

    def __init__(self) -> None:
        self._nc: Optional[nats.NATS] = None
        self._lock = asyncio.Lock()

    async def _ensure(self) -> nats.NATS:
        """
        Zapewnia aktywne połączenie z NATS (leniwie tworzone i współdzielone).

        Zwraca:
            nats.NATS: aktywny klient.

        Wyjątki:
            nats.errors.Error – w przypadku problemów z połączeniem (pierwsza próba).
        """
        async with self._lock:
            if self._nc and self._nc.is_connected:
                return self._nc
            # Tworzymy nowe połączenie (connect_timeout chroni przed wiszeniem).
            self._nc = await nats.connect(NATS_URL, connect_timeout=CONNECT_TIMEOUT_SEC)
            return self._nc

    @staticmethod
    def _validate_subject(subject: str) -> None:
        """
        Waliduje temat NATS (prosta walidacja formatu).

        Zasady NATS:
            - segmenty rozdzielone kropką, bez pustych segmentów,
            - brak znaków białych; '*' i '>' są wildcardami (tu nie używamy).

        :raises ValueError: jeśli temat jest niepoprawny.
        """
        if not subject or subject.strip() != subject:
            raise ValueError("Subject must be non-empty and must not contain leading/trailing spaces.")
        if " " in subject:
            raise ValueError("Subject must not contain whitespace.")
        if ".." in subject or subject.startswith(".") or subject.endswith("."):
            raise ValueError("Subject must not contain empty segments (double dots) or start/end with '.'.")
        # (Jeśli chcesz zabronić wildcardów: odkomentuj poniżej)
        # if "*" in subject or ">" in subject:
        #     raise ValueError("Wildcards (*, >) are not allowed for publisher subjects in this context.")

    @staticmethod
    def _encode_payload(payload: dict[str, Any]) -> bytes:
        """
        Serializuje payload do JSON (UTF-8) i pilnuje limitu rozmiaru.

        :param payload: słownik do wysłania
        :return: bajty JSON (UTF-8)
        :raises ValueError: gdy payload przekracza MAX_MESSAGE_BYTES
        """
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(data) > MAX_MESSAGE_BYTES:
            raise ValueError(
                f"Payload too large: {len(data)} bytes > limit {MAX_MESSAGE_BYTES} bytes."
            )
        return data

    async def publish(self, subject: str, payload: dict[str, Any]) -> None:
        """
        Publikuje komunikat JSON na wskazany temat NATS.

        Kroki:
            1) Walidacja tematu (format),
            2) Serializacja JSON + weryfikacja rozmiaru,
            3) Zapewnienie połączenia (leniwie),
            4) publish() — w razie błędu próba lekkiego reconnect i ponowienie.

        :param subject: temat NATS (np. "astradesk.audit")
        :param payload: słownik serializowany do JSON

        :raises ValueError: przy błędnym temacie lub zbyt dużym payloadzie.
        :note: błędy NATS po nieudanym reconnect NIE są podnoszone dalej (best-effort).
        """
        # 1) walidacja tematu
        self._validate_subject(subject)
        # 2) serializacja JSON (z limitem rozmiaru)
        data = self._encode_payload(payload)

        # 3) upewniamy się, że mamy połączenie i publikujemy
        try:
            nc = await self._ensure()
            await nc.publish(subject, data)
            return
        except Exception:
            # 4) spróbuj odświeżyć połączenie i ponowić publikację (best-effort)
            try:
                async with self._lock:
                    # Zamknij stare połączenie, jeśli istnieje
                    try:
                        if self._nc and self._nc.is_connected:
                            await self._nc.close()
                    except Exception:
                        pass
                    # Nawiąż nowe i opublikuj
                    self._nc = await nats.connect(NATS_URL, connect_timeout=CONNECT_TIMEOUT_SEC)
                    await self._nc.publish(subject, data)
            except Exception:
                # Ostatecznie: nie podnosimy wyjątku dalej — nie blokujemy ścieżek krytycznych.
                # W praktyce warto dodać logowanie na poziomie wyżej (logger).
                return

    async def close(self) -> None:
        """
        Zamyka aktywne połączenie z NATS. Wywołaj podczas zamykania aplikacji
        (np. w handlerze FastAPI `on_shutdown`), aby zrobić czyste domknięcie.
        """
        async with self._lock:
            if self._nc:
                try:
                    await self._nc.drain()  # grzeczne domknięcie (flush + close)
                except Exception:
                    # jeśli drain nie powiedzie się, spróbuj zwykłe close
                    try:
                        await self._nc.close()
                    except Exception:
                        pass
                finally:
                    self._nc = None


# Pojedyncza, współdzielona instancja publish-only, gotowa do użycia.
events = Events()
