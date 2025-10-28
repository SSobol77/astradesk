# SPDX-License-Identifier: Apache-2.0
"""File: services/auditor/main.py
Project: AstraDesk Framework — Mikroserwis Auditor.

Author: Siergej Sobolewski
Since: 2025-10-28

Asynchronous, production-grade microservice responsible solely for **reliably
persisting audit events** to Elasticsearch and AWS S3 while consuming from NATS.

Scope & Responsibilities
------------------------
- Subscribe to the audit subject on **NATS** (publish-only producer lives elsewhere).
- **Buffer** incoming events in-memory and **flush** them periodically or by size.
- **Persist** events concurrently to:
  - **Elasticsearch** (bulk NDJSON via `_bulk` API) for search/analytics,
  - **AWS S3** (NDJSON object) for durable, cost-efficient long-term storage.
- Implement **graceful shutdown** (SIGINT/SIGTERM) ensuring buffers are flushed.
- Provide **structured JSON logging** and conservative **error handling**:
  a failure in one sink never blocks the other.

Design Principles
-----------------
- End-to-end **async I/O** using `nats-py`, `httpx`, and `aioboto3`.
- **Backpressure-friendly** buffering with periodic/size-based flushing.
- **Observability-first**: concise, structured logs with context.
- **Single responsibility**: no business logic beyond reliable persistence.

Environment
-----------
- `NATS_URL`                 : NATS server URL (default: `nats://nats:4222`)
- `S3_BUCKET`                : Target S3 bucket (default: `astradesk-audit`)
- `AWS_REGION`               : AWS region (default: `eu-central-1`)
- `ES_URL`                   : Elasticsearch URL (default: `http://elasticsearch:9200`)
- `ES_INDEX`                 : Elasticsearch index (default: `astradesk-audit`)
- `FLUSH_SIZE`               : Flush when buffer size reaches N records (default: `100`)
- `FLUSH_INTERVAL_SEC`       : Flush when last flush older than N seconds (default: `10`)

Notes
-----
- This is the **entrypoint** of the Auditor service (FastAPI not required here).
- Use `async with Auditor():` to guarantee proper lifecycle and final flush.


Notes (PL):
- Ten moduł jest PUNKTEM WEJŚCIOWYM aplikacji (mikroserwis FastAPI).
- Odpowiedzialność ograniczona do:
  * Subskrybowania zdarzeń audytowych z NATS.
  * Buforowania zdarzeń w pamięci.
  * Niezawodnego zapisywania zdarzeń do Elasticsearch i AWS S3.
  * Implementacji logiki "graceful shutdown" do obsługi sygnałów SIGINT/SIGTERM.
- Ustrukturyzowanego logowania w formacie JSON.
- Obsługi błędów z logowaniem.
- Wydajnej, nieblokującej obsługi I/O przy użyciu asynchronicznych bibliotek.
- Logika biznesowa jest ograniczona do minimum, koncentrując się na niezawodnym
  zapisie danych.

Serwis ten działa jako asynchroniczny konsument zdarzeń, subskrybując
temat audytowy w NATS. Jego jedyną odpowiedzialnością jest niezawodne
odbieranie, buforowanie i zapisywanie zdarzeń audytowych do długoterminowych
systemów przechowywania danych (Elasticsearch i AWS S3).

Kluczowe cechy i zasady projektowe:
- **Niezawodność i Odporność**: Implementuje logikę "graceful shutdown" do
  obsługi sygnałów SIGINT/SIGTERM, zapewniając zapisanie wszystkich danych
  z bufora przed zamknięciem. Awaria zapisu do jednego systemu (np. ES)
  nie wpływa na próbę zapisu do drugiego (np. S3).
- **Wydajność**: Używa w pełni asynchronicznych bibliotek (`nats-py`,
  `aioboto3`, `httpx`) i współdzielonych klientów do nieblokującej obsługi I/O.
- **Obserwowalność**: Wykorzystuje ustrukturyzowane logowanie w formacie JSON,
  co jest standardem w nowoczesnych systemach opartych na kontenerach i
  ułatwia analizę logów w systemach takich jak ELK czy Grafana Loki.
- **Zarządzanie Cyklem Życia**: Klasa `Auditor` jest asynchronicznym
  menedżerem kontekstu, co zapewnia prawidłową inicjalizację i zamykanie
  wszystkich zasobów (połączeń sieciowych).

"""  # noqa: D205

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import time
from types import FrameType
from typing import Any

import aioboto3
import httpx
import nats
from botocore.exceptions import BotoCoreError
from nats.aio.client import Client as NATSClient
from python_json_logger import jsonlogger

# --- Konfiguracja ---
NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")
AUDIT_SUBJECT = "astradesk.audit"
S3_BUCKET = os.getenv("S3_BUCKET", "astradesk-audit")
AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
ES_URL = os.getenv("ES_URL", "http://elasticsearch:9200")
ES_INDEX = os.getenv("ES_INDEX", "astradesk-audit")
FLUSH_SIZE = int(os.getenv("FLUSH_SIZE", "100"))
FLUSH_INTERVAL_SEC = int(os.getenv("FLUSH_INTERVAL_SEC", "10"))

# --- Konfiguracja Logowania ---
logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
log_handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s')
log_handler.setFormatter(formatter)
logger.addHandler(log_handler)


class Auditor:
    """Audit events consumer/persister with concurrent sinks and graceful shutdown.

    Manages a shared async NATS subscription, an in-memory buffer, and dual
    persistence backends (Elasticsearch & S3). Ensures that:
    - writes are **concurrent** but **isolated** (one failure doesn't block the other),
    - buffer is **periodically** or **size-triggered** flushed,
    - shutdown **drains** remaining events before closing I/O resources.

    Attributes
    ----------
        _buf: In-memory list buffer holding decoded event dicts.
        _lock: Async mutex guarding buffer and state transitions.
        _last_flush_time: Monotonic timestamp of the last successful flush.
        _shutdown_event: Async event signaling termination.
        _nc: Active NATS client or `None` if not initialized.
        _http_client: Shared `httpx.AsyncClient` for Elasticsearch.
        _s3_session: Shared `aioboto3.Session` for S3 operations.

    """

    __slots__ = ("_buf", "_lock", "_last_flush_time", "_shutdown_event", "_nc", "_http_client", "_s3_session")

    def __init__(self) -> None:
        """Initialize internal state without performing any I/O.

        The actual network resources (NATS/httpx/aioboto3) are created in
        `__aenter__`, allowing deterministic lifecycle management with `async with`.
        """
        self._buf: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._last_flush_time = time.monotonic()
        self._shutdown_event = asyncio.Event()
        self._nc: NATSClient | None = None
        self._http_client: httpx.AsyncClient | None = None
        self._s3_session: aioboto3.Session | None = None

    async def __aenter__(self) -> "Auditor":  # noqa: UP037
        """Provision network clients (NATS/HTTP/S3) and return a ready instance.

        Returns
        -------
            Self, with active connections and ready to subscribe/flush.

        """
        logger.info("Initializing Auditor resources...")
        self._nc = await nats.connect(NATS_URL)
        self._http_client = httpx.AsyncClient(timeout=10.0)
        self._s3_session = aioboto3.Session()
        logger.info("Auditor resources initialized.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Gracefully flush remaining buffer and close network resources.

        Always attempts a final flush if the buffer is non-empty, then closes
        NATS and HTTP resources. Errors while closing are logged and suppressed.
        """
        logger.info("Starting Auditor graceful shutdown...")
        if self._buf:
            logger.info(f"Flushing final {len(self._buf)} buffered events before exit...")
            await self._flush()

        if self._nc:
            await self._nc.close()
        if self._http_client:
            await self._http_client.aclose()
        logger.info("Auditor shutdown complete.")

    async def _persist_to_es(self, batch: list[dict[str, Any]]) -> None:
        """Persist a batch to Elasticsearch using the `_bulk` NDJSON API.

        Builds a valid NDJSON payload (`index` action + document lines) and posts
        it to `{ES_URL}/_bulk`. HTTP errors are logged with status and body.

        Args:
        ----
            batch: List of event documents to index.

        """
        if not self._http_client:
            logger.error("HTTP client not initialized; skipping Elasticsearch write.")
            return
        try:
            ndjson_lines = []
            for doc in batch:
                ndjson_lines.append(json.dumps({"index": {"_index": ES_INDEX}}))
                ndjson_lines.append(json.dumps(doc, ensure_ascii=False))
            payload = "\n".join(ndjson_lines) + "\n"

            resp = await self._http_client.post(
                f"{ES_URL}/_bulk",
                content=payload,
                headers={"Content-Type": "application/x-ndjson"},
            )
            resp.raise_for_status()
            logger.info(f"Elasticsearch persisted batch size={len(batch)}.")
        except httpx.HTTPStatusError as e:
            logger.error(
                "Elasticsearch HTTP error.",
                extra={"status_code": e.response.status_code, "response": e.response.text},
            )
        except Exception:
            logger.error("Unexpected error while writing to Elasticsearch.", exc_info=True)

    async def _persist_to_s3(self, batch: list[dict[str, Any]]) -> None:
        """Persist a batch as an NDJSON object in S3.

        Creates a time-based key under `audit/` and uploads the NDJSON body.

        Args:
        ----
            batch: List of event documents to upload.

        """
        if not self._s3_session:
            logger.error("aioboto3 session not initialized; skipping S3 write.")
            return
        try:
            async with self._s3_session.client("s3", region_name=AWS_REGION) as s3_client:  # type: ignore[attr-defined]
                key = f"audit/{int(time.time())}-{len(batch)}.ndjson"
                body = "\n".join(json.dumps(d, ensure_ascii=False) for d in batch)

                await s3_client.put_object(Bucket=S3_BUCKET, Key=key, Body=body.encode("utf-8"))
                logger.info(f"S3 persisted batch size={len(batch)} to key={key}.")
        except BotoCoreError:
            logger.error("BotoCore error while writing to S3.", exc_info=True)
        except Exception:
            logger.error("Unexpected error while writing to S3.", exc_info=True)

    async def _flush(self) -> None:
        """Atomically drain the buffer and persist the batch to both sinks.

        Drains the buffer under a lock, then concurrently triggers ES and S3 writes.
        Failures are collected via `asyncio.gather` and logged individually; one sink
        failure does not block the other.
        """
        async with self._lock:
            if not self._buf:
                return
            batch_to_flush = self._buf
            self._buf = []
            self._last_flush_time = time.monotonic()

        logger.info(f"Flushing batch size={len(batch_to_flush)} to sinks...")
        results = await asyncio.gather(
            self._persist_to_es(batch_to_flush),
            self._persist_to_s3(batch_to_flush),
            return_exceptions=True,
        )
        for res in results:
            if isinstance(res, Exception):
                logger.error("Flush sink raised an exception.", exc_info=res)

    async def _message_handler(self, msg: nats.aio.msg.Msg) -> None:
        """Decode a single NATS message and append it to the buffer.

        Invalid JSON messages are discarded with a warning (best-effort).

        Args:
        ----
            msg: Incoming NATS message.

        """
        try:
            data = json.loads(msg.data)
            async with self._lock:
                self._buf.append(data)
        except json.JSONDecodeError:
            logger.warning(
                "Received invalid JSON from NATS.",
                extra={"raw_data": msg.data.decode("utf-8", "ignore")},
            )

    async def _periodic_flush(self) -> None:
        """Background task that triggers time/size-based flushes.

        Flushes when:
          - buffer length ≥ `FLUSH_SIZE`, or
          - buffer non-empty and `FLUSH_INTERVAL_SEC` elapsed since last flush.
        """
        while not self._shutdown_event.is_set():
            await asyncio.sleep(1)
            async with self._lock:
                buffer_size = len(self._buf)
                time_since_flush = time.monotonic() - self._last_flush_time

            if buffer_size >= FLUSH_SIZE or (buffer_size > 0 and time_since_flush >= FLUSH_INTERVAL_SEC):
                await self._flush()

    def _handle_shutdown_signal(self, signum: int, frame: FrameType | None) -> None:
        """Signal handler to initiate graceful shutdown.

        Sets the internal `_shutdown_event`, causing the main `run` loop to stop
        and perform a final flush in `__aexit__`.

        Args:
        ----
            signum: OS signal number (e.g., SIGINT, SIGTERM).
            frame: Current stack frame (unused).

        """
        logger.info(f"Received signal {signal.Signals(signum).name}; starting graceful shutdown...")
        self._shutdown_event.set()

    async def run(self) -> None:
        """Run the main service loop.

        Subscribe to NATS and wait for shutdown.

        Subscribes to `AUDIT_SUBJECT`, starts the periodic flush task,
        and blocks until `_shutdown_event` is set by a signal handler.
        """
        if not self._nc:
            raise RuntimeError("Auditor not initialized. Use 'async with Auditor()'.")

        await self._nc.subscribe(AUDIT_SUBJECT, cb=self._message_handler)
        logger.info(f"Subscribed to NATS subject: '{AUDIT_SUBJECT}'")

        flush_task = asyncio.create_task(self._periodic_flush())

        await self._shutdown_event.wait()

        # Stop periodic flush to avoid races with final shutdown flush.
        flush_task.cancel()
        try:
            await flush_task
        except asyncio.CancelledError:
            pass  # expected on shutdown


async def main():
    """Process entrypoint: set up signal handlers and run the Auditor.

    Creates an `Auditor` instance via async context manager, registers
    SIGINT/SIGTERM handlers to trigger graceful shutdown, and runs the main loop.
    """
    loop = asyncio.get_running_loop()

    try:
        async with Auditor() as auditor:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, auditor._handle_shutdown_signal, sig, None)

            await auditor.run()
    except Exception:
        logger.critical("Auditor terminated due to an unexpected error.", exc_info=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user.")
