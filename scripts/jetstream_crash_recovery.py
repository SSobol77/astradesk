#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: scripts/jetstream_crash_recovery.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for scripts/jetstream_crash_recovery.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Executable crash-recovery evidence for the JetStream durable audit path
(GitHub issue #39).

Starts a real, ephemeral NATS JetStream container (the exact pinned image
digest already used by `docker-compose.yml`/`docker-compose.dev.yml`) and
drives the actual production classes end-to-end — the real
`runtime.audit.JetStreamAuditWriter` producer from the API Gateway and the
real `main.Auditor` consumer from the Auditor service — through a scripted
crash: fetch a batch, deliberately never ack it, disconnect (an unclean
shutdown, not `Auditor.__aexit__`'s graceful path), then reconnect a brand
new `Auditor` instance under the *same* durable consumer name and prove the
unacked batch is redelivered, unmodified, exactly once.

Elasticsearch/S3 are not required: `Auditor._persist_to_es`/`_persist_to_s3`
are replaced with in-memory fakes for this run, because the property under
test is JetStream + durable-consumer redelivery semantics, not the sink
implementations themselves (those are covered by
`services/auditor/tests/test_auditor.py`'s fakes-based unit tests).

Proves, against a real broker:
  * INV-AUD-2 (ISSUES_019): a crash before ack does not lose the event —
    the same event id(s) are redelivered to a fresh consumer instance.
  * No duplicate processing after a clean ack: once acked, the event is not
    redelivered again.
  * INV-AUD-3: a batch that exhausts bounded sink retries is routed to the
    DLQ subject and is independently readable there, never silently dropped.

Usage:
    uv run --package astradesk-api-gateway python scripts/jetstream_crash_recovery.py

Exit code 0 and a PASS report on success; non-zero and a FAIL report
otherwise. Always tears down the ephemeral container, including on failure.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import traceback
import uuid
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

NATS_IMAGE = 'nats@sha256:b3f2bd84176ae7bd0afa9c48a00f06d7d0818ff4aaee898e4172e0b8340e5816'
CONTAINER_NAME = f'astradesk-jetstream-crash-recovery-{uuid.uuid4().hex[:8]}'
NATS_PORT = 24222
NATS_URL = f'nats://127.0.0.1:{NATS_PORT}'

_STREAM = 'ASTRADESK_AUDIT_CRASHTEST'
_SUBJECT = 'astradesk.audit.crashtest'
_DLQ_SUBJECT = 'astradesk.audit.crashtest.dlq'
_DURABLE = 'astradesk-auditor-crashtest'
_ACK_WAIT_SEC = '3'

# Environment must be set *before* importing `runtime.audit` (producer) and
# `main` (consumer): both modules read their configuration from env vars at
# import time via module-level `os.getenv(...)` constants.
os.environ['NATS_URL'] = NATS_URL
os.environ['AUDIT_JETSTREAM_STREAM'] = _STREAM
os.environ['AUDIT_JETSTREAM_SUBJECT'] = _SUBJECT
os.environ['AUDIT_JETSTREAM_DLQ_SUBJECT'] = _DLQ_SUBJECT
os.environ['AUDIT_JETSTREAM_DURABLE_CONSUMER'] = _DURABLE
os.environ['AUDIT_ACK_WAIT_SEC'] = _ACK_WAIT_SEC
os.environ['AUDIT_FETCH_TIMEOUT_SEC'] = '3'
os.environ['AUDIT_SINK_RETRIES'] = '0'
os.environ['AUDIT_SINK_RETRY_BACKOFF_SEC'] = '0'

sys.path.insert(0, str(REPO_ROOT / 'services' / 'api-gateway' / 'src'))
sys.path.insert(0, str(REPO_ROOT / 'services' / 'auditor'))

import nats
import nats.js.errors
from main import Auditor
from runtime.audit import AuditDecision, AuditEvent, JetStreamAuditWriter
from runtime.authz import SideEffect


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def start_nats() -> None:
    _run(['docker', 'rm', '-f', CONTAINER_NAME])
    result = _run(
        [
            'docker',
            'run',
            '-d',
            '--name',
            CONTAINER_NAME,
            '-p',
            f'{NATS_PORT}:4222',
            NATS_IMAGE,
            '--jetstream',
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(f'docker run failed: {result.stderr.strip()}')


def stop_nats() -> None:
    _run(['docker', 'rm', '-f', CONTAINER_NAME])


async def wait_for_nats(attempts: int = 40) -> None:
    last_exc: Exception | None = None
    for _ in range(attempts):
        try:
            nc = await nats.connect(NATS_URL)
            await nc.close()
            return
        except Exception as exc:  # - broad on purpose while polling readiness
            last_exc = exc
            await asyncio.sleep(0.5)
    raise RuntimeError(f'NATS did not become ready in time: {type(last_exc).__name__}')


async def publish_event(event_id: str) -> None:
    """Publish one audit event via the real producer-side writer."""
    nc = await nats.connect(NATS_URL)
    try:
        js = nc.jetstream()
        try:
            await js.stream_info(_STREAM)
        except nats.js.errors.NotFoundError:
            await js.add_stream(name=_STREAM, subjects=[_SUBJECT, _DLQ_SUBJECT])
        writer = JetStreamAuditWriter(
            js, subject=_SUBJECT, dlq_subject=_DLQ_SUBJECT, publish_timeout=2.0, publish_retries=1
        )
        event = AuditEvent(
            event_id=event_id,
            timestamp=datetime.now(UTC),
            tool='restart_service',
            side_effect=SideEffect.EXECUTE,
            decision=AuditDecision.ALLOWED,
            roles=('sre',),
            args_preview={},
        )
        await writer.write(event)
    finally:
        await nc.close()


def _event_ids(msgs: list) -> list[str]:
    return sorted(json.loads(m.data)['event_id'] for m in msgs)


async def run_scenario() -> list[str]:
    lines: list[str] = []

    def log(line: str) -> None:
        print(line)
        lines.append(line)

    log('=== JetStream durable-audit crash-recovery evidence (ISSUE 039) ===')
    log(f'NATS image: {NATS_IMAGE}')
    log(f'Stream={_STREAM} subject={_SUBJECT} dlq={_DLQ_SUBJECT} durable={_DURABLE}')

    await wait_for_nats()
    log('[1] NATS JetStream container is ready.')

    produced_ids = ['crash-evt-0', 'crash-evt-1', 'crash-evt-2']
    for event_id in produced_ids:
        await publish_event(event_id)
    log(f'[2] Published {len(produced_ids)} audit events via JetStreamAuditWriter: {produced_ids}')

    # --- Phase A: fetch, then crash before acking -------------------------- #
    async with Auditor() as auditor1:
        msgs1 = await auditor1._sub.fetch(batch=10, timeout=3)
        crashed_ids = _event_ids(msgs1)
        log(
            f'[3] Consumer #1 fetched {crashed_ids} and deliberately did NOT ack (simulated crash).'
        )
    # __aexit__ only closes the connection; no ack was ever sent to the broker.

    if crashed_ids != produced_ids:
        raise AssertionError(f'expected fetch of {produced_ids}, got {crashed_ids}')

    await asyncio.sleep(float(_ACK_WAIT_SEC) + 1.0)
    log(
        f'[4] Waited past AUDIT_ACK_WAIT_SEC={_ACK_WAIT_SEC}s for JetStream redelivery eligibility.'
    )

    # --- Phase B: fresh consumer instance recovers the unacked batch ------- #
    persisted_batches: list[list[dict]] = []

    async def fake_persist_ok(self: Auditor, batch: list[dict]) -> None:
        persisted_batches.append(list(batch))

    Auditor._persist_to_es = fake_persist_ok  # type: ignore[method-assign]
    Auditor._persist_to_s3 = fake_persist_ok  # type: ignore[method-assign]

    async with Auditor() as auditor2:
        msgs2 = await auditor2._sub.fetch(batch=10, timeout=5)
        redelivered_ids = _event_ids(msgs2)
        log(
            f'[5] Consumer #2 (fresh instance, same durable name) was redelivered: {redelivered_ids}'
        )
        if redelivered_ids != produced_ids:
            raise AssertionError(
                f'crash-recovery redelivery mismatch: expected {produced_ids}, got {redelivered_ids}'
            )
        await auditor2._process_batch(msgs2)
        log('[6] Consumer #2 persisted the batch (fake sinks) and acked after durable write.')

    # One persist call per sink (ES and S3 share the same fake here), each
    # with the full recovered batch.
    if len(persisted_batches) != 2 or any(
        _event_ids_from_dicts(batch) != produced_ids for batch in persisted_batches
    ):
        raise AssertionError('recovered batch was not persisted correctly to both sinks')

    # --- Phase C: no further redelivery after a clean ack ------------------ #
    async with Auditor() as auditor3:
        try:
            msgs3 = await auditor3._sub.fetch(batch=10, timeout=2)
        except TimeoutError:
            msgs3 = []
        log(f'[7] Consumer #3 fetch after ack returned {len(msgs3)} messages (expected 0).')
        if msgs3:
            raise AssertionError('acked events were redelivered again — duplicate processing')

    # --- Phase D: bounded sink-retry exhaustion routes to DLQ -------------- #
    dlq_event_id = 'crash-dlq-0'
    await publish_event(dlq_event_id)
    log(f'[8] Published one more event ({dlq_event_id}) to exercise the DLQ path.')

    async def fake_persist_fail(self: Auditor, batch: list[dict]) -> None:
        raise OSError('simulated persistent sink outage for DLQ evidence')

    Auditor._persist_to_es = fake_persist_fail  # type: ignore[method-assign]
    Auditor._persist_to_s3 = fake_persist_ok  # type: ignore[method-assign]

    async with Auditor() as auditor4:
        msgs4 = await auditor4._sub.fetch(batch=10, timeout=3)
        await auditor4._process_batch(msgs4)
    log('[9] Consumer #4 exhausted sink retries and routed the batch to the DLQ subject.')

    nc_dlq = await nats.connect(NATS_URL)
    try:
        js_dlq = nc_dlq.jetstream()
        dlq_sub = await js_dlq.pull_subscribe(
            _DLQ_SUBJECT, durable='astradesk-auditor-crashtest-dlq-check', stream=_STREAM
        )
        dlq_msgs = await dlq_sub.fetch(batch=10, timeout=3)
        dlq_ids = _event_ids(dlq_msgs)
        for msg in dlq_msgs:
            await msg.ack()
    finally:
        await nc_dlq.close()

    log(f'[10] Independently read back from the DLQ subject: {dlq_ids}')
    if dlq_event_id not in dlq_ids:
        raise AssertionError(f'expected {dlq_event_id} in DLQ, got {dlq_ids}')

    log('=== RESULT: PASS ===')
    log('Crash-before-ack batch was redelivered unmodified to a fresh consumer instance.')
    log('No duplicate redelivery occurred after a clean ack.')
    log('Sink-retry exhaustion durably routed the event to the DLQ subject instead of dropping it.')
    return lines


def _event_ids_from_dicts(batch: list[dict]) -> list[str]:
    return sorted(str(d['event_id']) for d in batch)


def main() -> int:
    start_nats()
    try:
        lines = asyncio.run(run_scenario())
        evidence_path = REPO_ROOT / 'audit' / 'evidence' / '39_jetstream_crash_recovery_run.txt'
        evidence_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        print(f'\nEvidence written to {evidence_path.relative_to(REPO_ROOT)}')
        return 0
    except Exception as exc:  # - top-level script failure report
        traceback.print_exc()
        print(f'=== RESULT: FAIL ({type(exc).__name__}: {exc}) ===', file=sys.stderr)
        return 1
    finally:
        stop_nats()


if __name__ == '__main__':
    raise SystemExit(main())
