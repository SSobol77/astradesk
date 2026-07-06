<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: docs/roadmap/issues/ISSUES_019_durable_audit.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# ISSUES_019 — Durable, recoverable audit (RESCOPE of #19)

- **Track / Milestone**: A / `v0.3.1`
- **Type**: RESCOPE of closed #19 (corrects the prior stale "stub" claim — subscriber is real)
- **Workhorse principle**: Security (good-sense) — non-repudiation
- **GA-gating**: yes — lost audit evidence is unrecoverable; a client-facing workhorse cannot lose it
- **Audit anchors**: §6 (Critical); `services/auditor/main.py:261-283`, `338-377`
- **Depends on**: none (parallelizable), but precedes client work

## Problem (current evidence)
The auditor is a genuine NATS subscriber (386 LOC), not a stub. However it uses a **non-durable core NATS subscription**, drains its in-memory buffer **before** sink persistence, and suppresses sink exceptions. A process or sink failure can lose audit events despite the module's "reliable persistence" claim.

## Industry analog & childhood disease
Event/audit pipelines commonly ack-before-write and buffer in memory for throughput, then lose data on the first crash or sink outage — discovered only during an incident when the audit trail has a hole. The disease is **throughput optimization that sacrifices the durability the component exists to provide.** We immunize with durable consumers and ack-after-durable-write.

## Target contract (invariants)
- **INV-AUD-1**: An event is acknowledged to the broker only **after** it is durably persisted to a sink (ack-after-write).
- **INV-AUD-2**: The subscription is a JetStream **durable** consumer; restart resumes from the last unacked message.
- **INV-AUD-3**: Sink failure triggers bounded retry, then routes to a DLQ; events are never silently dropped.
- **INV-AUD-4**: Writes are idempotent (idempotency key) so redelivery does not duplicate audit records.
- **INV-AUD-5**: Audit availability is independent of the request path — Gateway does not block on audit, but audit cannot lose what it accepted.

## Interface / design
- Migrate subscription to JetStream durable consumer with explicit ack.
- Persist → ack ordering; remove pre-write buffer drain.
- DLQ subject + replay tool; idempotency key derived from event id.

## Failure modes & required behavior
| Failure | Required behavior |
| :--- | :--- |
| Process crash mid-flush | On restart, unacked events redelivered; zero loss |
| Elasticsearch/S3 sink outage | Retry with backoff, then DLQ; no ack until durable |
| Duplicate redelivery | Idempotent write; single audit record |
| Sink throws | Surfaced + retried, not suppressed |

## Acceptance criteria (Definition of Done)
- [x] Durable JetStream consumer; ack-after-durable-write.
- [x] Crash-recovery test: kill during flush → zero event loss after restart.
- [x] Sink-outage test: induced outage → events land in DLQ, replay restores them.
- [x] Idempotency test: forced redelivery → no duplicates.
- [x] Removed exception suppression; failures observable (structured logs; no dedicated Prometheus counter yet — see Limitations).

## Verification evidence (artifact)
Crash-recovery and sink-outage test logs; DLQ replay output.

**Resolved by GitHub issue #39** (tracked separately from this RESCOPE
document because #19/#19-RESCOPE predates the numbered-issue workflow used
from #39 onward). Full implementation record, exact commands, and results:
`audit/evidence/39_jetstream_durable_audit.md`. Raw crash-recovery run
output: `audit/evidence/39_jetstream_crash_recovery_run.txt`.

Summary of how each invariant is satisfied:

- **INV-AUD-1/INV-AUD-5** (ack-after-durable-write; Gateway doesn't block on
  audit but can't lose what it accepted): the producer-side
  `runtime.audit.JetStreamAuditWriter` (`services/api-gateway/src/runtime/audit.py`)
  only returns from `write()` once JetStream acknowledges durable storage on
  the primary subject; the pre-existing `ToolRegistry.execute` choke point
  (`services/api-gateway/src/runtime/registry.py`, unmodified) already
  awaits `AuditWriter.write()` before invoking a side-effecting tool, so a
  tool never runs without a durably-stored audit record. Selected via the
  explicit, non-default `AUDIT_MODE=jetstream` (`INV-LOCAL-MODE-EXPLICIT`
  applies in reverse here: the *stronger* mode must be opted into, and the
  weaker JSONL baseline stays the default so existing deployments are
  unaffected).
- **INV-AUD-2** (durable JetStream consumer, restart resumes from the last
  unacked message): `services/auditor/main.py`'s `Auditor` is now a
  JetStream durable pull consumer (`AckPolicy.EXPLICIT`, durable name
  `AUDIT_JETSTREAM_DURABLE_CONSUMER`). Proven against a real, ephemeral NATS
  JetStream container by `scripts/jetstream_crash_recovery.py`: a batch
  fetched-but-never-acked by one `Auditor` instance is redelivered
  unmodified to a brand-new instance under the same durable name.
- **INV-AUD-3** (bounded retry then DLQ, never silently dropped): both the
  producer and the consumer retry a bounded number of times
  (`AUDIT_PUBLISH_RETRIES`/`AUDIT_SINK_RETRIES`) before routing to a DLQ
  subject; a message is acked off the primary subject only once the DLQ
  publish itself is broker-confirmed, otherwise it is left unacked for
  JetStream to redeliver. "Replay" is the DLQ subject itself: it is an
  ordinary durable JetStream subject on the same stream, so an operator (or
  a future tooling script) can independently pull-consume it — exactly what
  the crash-recovery script's DLQ-readback step does.
- **INV-AUD-4** (idempotent writes): the producer uses the audit event id as
  the JetStream `Nats-Msg-Id` (broker-side publish dedup); the consumer uses
  the event id as the Elasticsearch document `_id` and a digest of the
  batch's event ids as the S3 object key, so redelivery overwrites rather
  than duplicates. The DLQ publish on both sides deliberately uses a
  *different* dedup id (`dlq:<event_id>`) — see Limitations for why reusing
  the primary id there is actually a bug, not a feature.

## Limitations (carried into the #39 evidence record)

- No dedicated Prometheus counter for audit sink failures/DLQ routing yet;
  failures are structured JSON logs (`services/auditor/main.py`) at
  WARNING/ERROR/CRITICAL. Wiring these into the existing
  `services/api-gateway/src/tools/metrics.py`-style exporter is reasonable
  follow-up work, not required by this issue's contract.
- No automated DLQ replay tool (a script that re-publishes DLQ events back
  onto the primary subject after an operator fixes the underlying sink
  outage) exists yet; the DLQ subject is independently readable today, but
  replay is a manual `nats` CLI / script operation.

## Out of scope
WORM/object-lock retention tier and long-term archival policy (Track B / ops).
