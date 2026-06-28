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
- [ ] Durable JetStream consumer; ack-after-durable-write.
- [ ] Crash-recovery test: kill during flush → zero event loss after restart.
- [ ] Sink-outage test: induced outage → events land in DLQ, replay restores them.
- [ ] Idempotency test: forced redelivery → no duplicates.
- [ ] Removed exception suppression; failures observable in metrics.

## Verification evidence (artifact)
Crash-recovery and sink-outage test logs; DLQ replay output.

## Out of scope
WORM/object-lock retention tier and long-term archival policy (Track B / ops).
