# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/auditor/main.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for services/auditor/main.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Asynchronous, production-grade microservice responsible solely for **reliably
persisting audit events** to Elasticsearch and AWS S3, consumed durably from a
NATS JetStream stream (ISSUE 039).

Scope & Responsibilities
------------------------
- Consume the audit subject from a **JetStream durable pull consumer**
  (`AckPolicy.EXPLICIT`): a crash or restart resumes from the last unacked
  message because JetStream — not this process — owns the durable backlog.
- **Persist** each fetched batch concurrently to:
  - **Elasticsearch** (bulk NDJSON via `_bulk` API, one document per event,
    with an explicit deterministic `_id` for idempotent redelivery),
  - **AWS S3** (one NDJSON object per batch, keyed by a deterministic digest
    of the batch's event ids, so redelivering the same batch overwrites the
    same object instead of creating a duplicate).
- Only **ack** a fetched message once *both* sinks have durably accepted the
  batch it belongs to (`INV-AUD-1`/`INV-AUD-2` in
  `docs/roadmap/issues/ISSUES_019_durable_audit.md`).
- On bounded sink-retry exhaustion, route the batch to the **DLQ subject**
  (`INV-AUD-3`) and ack only after the DLQ publish itself is confirmed; if
  the DLQ publish also fails, the batch is left **unacked** so JetStream
  redelivers it later — the service never silently drops an accepted event.
- Provide **structured JSON logging** with no raw exception text (only
  `type(exc).__name__`), matching the security-conscious logging convention
  used by the API Gateway's audit choke point
  (`services/api-gateway/src/runtime/registry.py`).

Design Principles
------------------
- End-to-end **async I/O** using `nats-py`, `httpx`, and `aioboto3`.
- **No in-process buffering**: unlike the previous core-NATS push subscriber,
  nothing lives only in this process's memory between fetch and ack, so a
  crash between fetch and ack loses nothing — the message simply redelivers.
- **Idempotent sink writes**: retrying a batch (on transient sink failure) or
  redelivering it (after an unclean shutdown) never produces a duplicate
  document/object, only an overwrite of identical content.
- **Bounded everything**: fetch has a timeout, sink persistence is retried a
  bounded number of times with backoff, and DLQ publish has its own timeout —
  no indefinite hangs.
- **No catch-all error swallowing**: sink-persistence failures propagate so
  the retry/DLQ logic can observe and act on them.

Environment
-----------
- `NATS_URL`                        : NATS server URL (default: `nats://nats:4222`)
- `AUDIT_JETSTREAM_STREAM`          : JetStream stream name (default: `ASTRADESK_AUDIT`)
- `AUDIT_JETSTREAM_SUBJECT`         : Primary audit subject (default: `astradesk.audit`)
- `AUDIT_JETSTREAM_DLQ_SUBJECT`     : DLQ subject (default: `astradesk.audit.dlq`)
- `AUDIT_JETSTREAM_DURABLE_CONSUMER`: Durable consumer name (default: `astradesk-auditor`)
- `AUDIT_FETCH_BATCH_SIZE`          : Max messages per fetch (default: `100`)
- `AUDIT_FETCH_TIMEOUT_SEC`         : Bounded wait per fetch call (default: `5`)
- `AUDIT_SINK_RETRIES`              : Bounded sink-persist retries before DLQ (default: `3`)
- `AUDIT_SINK_RETRY_BACKOFF_SEC`    : Delay between sink-persist retries (default: `1`)
- `AUDIT_ACK_WAIT_SEC`              : JetStream redelivery wait for an unacked message (default: `30`)
- `S3_BUCKET`                       : Target S3 bucket (default: `astradesk-audit`)
- `AWS_REGION`                      : AWS region (default: `eu-central-1`)
- `ES_URL`                          : Elasticsearch URL (default: `http://elasticsearch:9200`)
- `ES_INDEX`                        : Elasticsearch index (default: `astradesk-audit`)

Notes
-----
- This is the **entrypoint** of the Auditor service (FastAPI not required here).
- Use `async with Auditor():` to guarantee proper lifecycle.
- The stream is provisioned with both the primary and DLQ subjects, mirroring
  `gateway.main._ensure_audit_stream` on the producer side, so the DLQ is a
  durable JetStream subject as well — not an in-memory or best-effort queue.


Notes (PL):
- Ten moduł jest PUNKTEM WEJŚCIOWYM aplikacji (mikroserwis FastAPI).
- Odpowiedzialność ograniczona do:
  * Konsumowania zdarzeń audytowych z trwałego (JetStream) tematu NATS za
    pomocą trwałego konsumenta typu "pull" z jawnym potwierdzaniem (ack).
  * Niezawodnego zapisywania zdarzeń do Elasticsearch i AWS S3.
  * Potwierdzania (ack) wiadomości NATS dopiero po trwałym zapisie do OBU
    magazynów docelowych.
  * Przekierowywania wiadomości do kolejki DLQ po wyczerpaniu ograniczonej
    liczby prób ponowienia zapisu do magazynu.
- Ustrukturyzowanego logowania w formacie JSON.
- Braku buforowania w pamięci procesu: awaria procesu między pobraniem
  a potwierdzeniem wiadomości nie powoduje utraty danych, ponieważ JetStream
  (broker), a nie proces, przechowuje nieprzetworzone wiadomości.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import signal
from collections.abc import Sequence
from types import FrameType
from typing import Any, Protocol

import aioboto3
import httpx
import nats
import nats.errors
import nats.js.errors
from nats.aio.client import Client as NATSClient
from nats.js.api import AckPolicy, ConsumerConfig
from nats.js.client import JetStreamContext
from pythonjsonlogger import jsonlogger

# --- Konfiguracja ---
NATS_URL = os.getenv('NATS_URL', 'nats://nats:4222')
AUDIT_JETSTREAM_STREAM = os.getenv('AUDIT_JETSTREAM_STREAM', 'ASTRADESK_AUDIT')
AUDIT_SUBJECT = os.getenv('AUDIT_JETSTREAM_SUBJECT', 'astradesk.audit')
AUDIT_DLQ_SUBJECT = os.getenv('AUDIT_JETSTREAM_DLQ_SUBJECT', 'astradesk.audit.dlq')
AUDIT_DURABLE_CONSUMER = os.getenv('AUDIT_JETSTREAM_DURABLE_CONSUMER', 'astradesk-auditor')
FETCH_BATCH_SIZE = int(os.getenv('AUDIT_FETCH_BATCH_SIZE', '100'))
FETCH_TIMEOUT_SEC = float(os.getenv('AUDIT_FETCH_TIMEOUT_SEC', '5'))
SINK_RETRIES = int(os.getenv('AUDIT_SINK_RETRIES', '3'))
SINK_RETRY_BACKOFF_SEC = float(os.getenv('AUDIT_SINK_RETRY_BACKOFF_SEC', '1'))
ACK_WAIT_SEC = float(os.getenv('AUDIT_ACK_WAIT_SEC', '30'))
S3_BUCKET = os.getenv('S3_BUCKET', 'astradesk-audit')
AWS_REGION = os.getenv('AWS_REGION', 'eu-central-1')
ES_URL = os.getenv('ES_URL', 'http://elasticsearch:9200')
ES_INDEX = os.getenv('ES_INDEX', 'astradesk-audit')

# --- Konfiguracja Logowania ---
logger = logging.getLogger(__name__)
logger.setLevel(os.getenv('LOG_LEVEL', 'INFO'))
log_handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s')
log_handler.setFormatter(formatter)
logger.addHandler(log_handler)


def _batch_s3_key(batch: list[dict[str, Any]]) -> str:
    """Derive a deterministic S3 key from the batch's event ids.

    Redelivering the exact same set of events (e.g. after a crash between
    a successful sink write and the JetStream ack) must overwrite the same
    object rather than create a duplicate (`INV-AUD-4`).
    """
    ids = sorted(str(doc.get('event_id', '')) for doc in batch)
    digest = hashlib.sha256('|'.join(ids).encode('utf-8')).hexdigest()
    return f'audit/{digest}.ndjson'


class JetStreamMessage(Protocol):
    """Structural contract for a fetched JetStream message.

    Matches only what `Auditor` actually reads/calls (`data`, `ack()`) so a
    deterministic test fake satisfies it without needing a real
    `nats.aio.msg.Msg` instance.
    """

    data: bytes

    async def ack(self) -> None:
        """Acknowledge durable processing of this message."""
        ...


class Auditor:
    """Durable JetStream audit consumer with concurrent, idempotent sinks.

    Manages a NATS JetStream durable pull subscription and dual persistence
    backends (Elasticsearch & S3). Ensures that:
    - a message is only **acked** after both sinks durably accept its batch,
    - sink failures are **retried** a bounded number of times, then routed
      to the **DLQ subject** (also acked only once the DLQ publish itself
      is confirmed),
    - nothing is buffered only in process memory between fetch and ack.

    Attributes
    ----------
        _lock: Async mutex guarding shutdown/state transitions.
        _shutdown_event: Async event signaling termination.
        _nc: Active NATS client or `None` if not initialized.
        _js: JetStream context bound to `_nc`.
        _sub: Durable pull subscription.
        _http_client: Shared `httpx.AsyncClient` for Elasticsearch.
        _s3_session: Shared `aioboto3.Session` for S3 operations.

    """

    __slots__ = (
        '_lock',
        '_shutdown_event',
        '_nc',
        '_js',
        '_sub',
        '_http_client',
        '_s3_session',
    )

    def __init__(self) -> None:
        """Initialize internal state without performing any I/O.

        The actual network resources (NATS/httpx/aioboto3) are created in
        `__aenter__`, allowing deterministic lifecycle management with `async with`.
        """
        self._lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()
        self._nc: NATSClient | None = None
        self._js: JetStreamContext | None = None
        self._sub: Any = None
        self._http_client: httpx.AsyncClient | None = None
        self._s3_session: aioboto3.Session | None = None

    async def __aenter__(self) -> 'Auditor':  # noqa: UP037
        """Provision network clients (NATS JetStream/HTTP/S3) and return a ready instance.

        Returns
        -------
            Self, with an active durable pull subscription and ready to run.

        """
        logger.info('Initializing Auditor resources...')
        self._nc = await nats.connect(NATS_URL)
        self._js = self._nc.jetstream()
        await self._ensure_stream()
        self._sub = await self._js.pull_subscribe(
            AUDIT_SUBJECT,
            durable=AUDIT_DURABLE_CONSUMER,
            stream=AUDIT_JETSTREAM_STREAM,
            config=ConsumerConfig(
                ack_policy=AckPolicy.EXPLICIT,
                ack_wait=ACK_WAIT_SEC,
            ),
        )
        self._http_client = httpx.AsyncClient(timeout=10.0)
        self._s3_session = aioboto3.Session()
        logger.info('Auditor resources initialized.')
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close network resources.

        No final buffer flush is needed: unacked messages remain durably
        pending in JetStream, not in this process's memory.
        """
        logger.info('Starting Auditor graceful shutdown...')
        if self._nc:
            await self._nc.close()
        if self._http_client:
            await self._http_client.aclose()
        logger.info('Auditor shutdown complete.')

    async def _ensure_stream(self) -> None:
        """Create the audit stream if it does not already exist (idempotent).

        Mirrors `gateway.main._ensure_audit_stream` on the producer side so
        the stream always carries both the primary and DLQ subjects.
        """
        if self._js is None:
            raise RuntimeError('JetStream context not initialized')
        try:
            await self._js.stream_info(AUDIT_JETSTREAM_STREAM)
        except nats.js.errors.NotFoundError:
            await self._js.add_stream(
                name=AUDIT_JETSTREAM_STREAM,
                subjects=[AUDIT_SUBJECT, AUDIT_DLQ_SUBJECT],
            )

    async def _persist_to_es(self, batch: list[dict[str, Any]]) -> None:
        """Persist a batch to Elasticsearch using the `_bulk` NDJSON API.

        Uses each event's `event_id` as the document `_id` so redelivering
        the same event is an idempotent overwrite, not a duplicate. Raises
        on any HTTP or item-level failure so the caller's retry/DLQ logic
        can observe it — this sink never swallows its own errors.

        Args:
        ----
            batch: List of event documents to index.

        """
        if not self._http_client:
            raise RuntimeError('HTTP client not initialized')

        ndjson_lines = []
        for doc in batch:
            action: dict[str, Any] = {'_index': ES_INDEX}
            event_id = doc.get('event_id')
            if event_id:
                action['_id'] = event_id
            ndjson_lines.append(json.dumps({'index': action}))
            ndjson_lines.append(json.dumps(doc, ensure_ascii=False))
        payload = '\n'.join(ndjson_lines) + '\n'

        resp = await self._http_client.post(
            f'{ES_URL}/_bulk',
            content=payload,
            headers={'Content-Type': 'application/x-ndjson'},
        )
        resp.raise_for_status()
        body = resp.json()
        if body.get('errors'):
            raise RuntimeError('Elasticsearch bulk response reported item-level errors')
        logger.info(f'Elasticsearch persisted batch size={len(batch)}.')

    async def _persist_to_s3(self, batch: list[dict[str, Any]]) -> None:
        """Persist a batch as an NDJSON object in S3, keyed deterministically.

        The key is derived from the batch's event ids (`_batch_s3_key`), so
        retrying or redelivering the same batch overwrites the same object
        instead of creating a duplicate. Raises on any failure so the
        caller's retry/DLQ logic can observe it.

        Args:
        ----
            batch: List of event documents to upload.

        """
        if not self._s3_session:
            raise RuntimeError('aioboto3 session not initialized')

        async with self._s3_session.client('s3', region_name=AWS_REGION) as s3_client:  # type: ignore[attr-defined]
            key = _batch_s3_key(batch)
            body = '\n'.join(json.dumps(d, ensure_ascii=False) for d in batch)
            await s3_client.put_object(Bucket=S3_BUCKET, Key=key, Body=body.encode('utf-8'))
            logger.info(f'S3 persisted batch size={len(batch)} to key={key}.')

    async def _persist_with_retry(self, batch: list[dict[str, Any]]) -> bool:
        """Attempt to persist a batch to both sinks with bounded retries.

        Both sinks are re-attempted together on any failure — safe because
        both writes are idempotent — up to `SINK_RETRIES` extra attempts.

        Returns
        -------
            `True` if both sinks durably accepted the batch, `False` once
            retries are exhausted.

        """
        for attempt in range(SINK_RETRIES + 1):
            results = await asyncio.gather(
                self._persist_to_es(batch),
                self._persist_to_s3(batch),
                return_exceptions=True,
            )
            failures = [r for r in results if isinstance(r, BaseException)]
            if not failures:
                return True
            for failure in failures:
                logger.warning(
                    'Sink persist attempt %d/%d failed: %s',
                    attempt + 1,
                    SINK_RETRIES + 1,
                    type(failure).__name__,
                )
            if attempt < SINK_RETRIES:
                await asyncio.sleep(SINK_RETRY_BACKOFF_SEC)
        return False

    async def _publish_to_dlq(self, msg: JetStreamMessage, event_id: str | None) -> bool:
        """Publish a raw message payload to the DLQ subject, bounded by a timeout.

        The dedup id is prefixed (``dlq:<event_id>``) rather than reused
        as-is: JetStream's `Nats-Msg-Id` deduplication window is scoped to
        the whole *stream*, not a single subject, and the primary subject
        and the DLQ subject share one stream. Reusing the bare event id
        here would make the broker treat this publish as a duplicate of the
        already-stored primary message and silently discard it — exactly
        the silent-loss failure mode DLQ routing exists to prevent.

        Returns
        -------
            `True` if the DLQ broker confirmed durable storage, `False` otherwise.

        """
        if self._js is None:
            return False
        headers = {'Nats-Msg-Id': f'dlq:{event_id}'} if event_id else None
        try:
            await asyncio.wait_for(
                self._js.publish(AUDIT_DLQ_SUBJECT, msg.data, headers=headers),
                timeout=FETCH_TIMEOUT_SEC,
            )
            return True
        except Exception as exc:
            logger.error('DLQ publish failed: %s', type(exc).__name__)
            return False

    async def _handle_poison_message(self, msg: JetStreamMessage) -> None:
        """Route a non-JSON message to the DLQ; ack only once DLQ-confirmed.

        Retrying an undecodable payload can never succeed, so it goes
        straight to the DLQ instead of through the sink-retry path.
        """
        dlq_ok = await self._publish_to_dlq(msg, event_id=None)
        if dlq_ok:
            await msg.ack()
            logger.warning('Poison (invalid JSON) message routed to DLQ and acked.')
        else:
            logger.critical('Poison message DLQ publish failed; leaving unacked for redelivery.')

    async def _decode_batch(
        self, msgs: Sequence[JetStreamMessage]
    ) -> list[tuple[JetStreamMessage, dict[str, Any]]]:
        """Split a fetched batch into decodable events, routing poison ones to the DLQ."""
        decodable: list[tuple[JetStreamMessage, dict[str, Any]]] = []
        for msg in msgs:
            try:
                event = json.loads(msg.data)
            except json.JSONDecodeError:
                await self._handle_poison_message(msg)
                continue
            decodable.append((msg, event))
        return decodable

    async def _route_batch_to_dlq(
        self, decodable: list[tuple[JetStreamMessage, dict[str, Any]]]
    ) -> None:
        """Route a batch that exhausted sink retries to the DLQ.

        Acks the batch only if every message was durably confirmed by the
        DLQ publish; otherwise the whole batch is left unacked so JetStream
        redelivers it later (`INV-AUD-3`: never silently drop an accepted
        event).
        """
        dlq_results = []
        for msg, event in decodable:
            dlq_results.append(await self._publish_to_dlq(msg, event_id=event.get('event_id')))

        if all(dlq_results):
            for msg, _ in decodable:
                await msg.ack()
            logger.error(
                f'Sink persist failed after {SINK_RETRIES} retries; '
                f'batch routed to DLQ size={len(decodable)}.'
            )
        else:
            logger.critical(
                'Sink persist and DLQ publish both failed; '
                'leaving batch unacked for JetStream redelivery.'
            )

    async def _process_batch(self, msgs: Sequence[JetStreamMessage]) -> None:
        """Decode, persist, and ack (or DLQ) a fetched batch of messages.

        Decodable messages are persisted as one batch; on success they are
        all acked. On bounded-retry exhaustion the batch is handed to
        `_route_batch_to_dlq`.
        """
        if not msgs:
            return

        decodable = await self._decode_batch(msgs)
        if not decodable:
            return

        batch = [event for _, event in decodable]
        if await self._persist_with_retry(batch):
            for msg, _ in decodable:
                await msg.ack()
            logger.info(f'Acked batch size={len(decodable)} after durable sink write.')
            return

        await self._route_batch_to_dlq(decodable)

    def _handle_shutdown_signal(self, signum: int, frame: FrameType | None) -> None:
        """Signal handler to initiate graceful shutdown.

        Sets the internal `_shutdown_event`, causing the main `run` loop to
        stop fetching after the current bounded fetch call returns.

        Args:
        ----
            signum: OS signal number (e.g., SIGINT, SIGTERM).
            frame: Current stack frame (unused).

        """
        logger.info(f'Received signal {signal.Signals(signum).name}; starting graceful shutdown...')
        self._shutdown_event.set()

    async def run(self) -> None:
        """Run the main service loop.

        Repeatedly fetches a bounded batch from the durable pull
        subscription (timing out after `AUDIT_FETCH_TIMEOUT_SEC` when idle,
        which also caps how long shutdown can take to observe), processes
        it, and loops until `_shutdown_event` is set.
        """
        if not self._sub:
            raise RuntimeError("Auditor not initialized. Use 'async with Auditor()'.")

        logger.info(
            f"Pull-consuming from stream='{AUDIT_JETSTREAM_STREAM}' "
            f"subject='{AUDIT_SUBJECT}' durable='{AUDIT_DURABLE_CONSUMER}'."
        )

        while not self._shutdown_event.is_set():
            try:
                msgs = await self._sub.fetch(batch=FETCH_BATCH_SIZE, timeout=FETCH_TIMEOUT_SEC)
            except TimeoutError:
                # No messages within the bounded wait; loop to re-check shutdown.
                continue
            await self._process_batch(msgs)


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
        logger.critical('Auditor terminated due to an unexpected error.', exc_info=True)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('Application interrupted by user.')
