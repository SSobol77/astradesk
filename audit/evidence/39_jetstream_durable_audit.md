<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: audit/evidence/39_jetstream_durable_audit.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# Issue #39 — Durable, recoverable audit (JetStream)

Status: **implemented and verified offline.** A NATS JetStream-backed durable
audit mode (`AUDIT_MODE=jetstream`) has been added alongside the existing
JSONL baseline (PR #55, `AUDIT_LOG_PATH`), which is preserved unchanged as
the default local/fallback mode. The API Gateway's side-effect choke point
now reports a side-effecting tool call successful only after the audit event
is durably acknowledged by JetStream; unavailable/unacknowledged publishes —
including after bounded retry and a best-effort DLQ attempt — fail the tool
call closed. The Auditor service was reworked from a non-durable core-NATS
push subscriber into a durable JetStream pull consumer that acks a batch
only after both Elasticsearch and S3 durably accept it, with bounded
sink-retry, DLQ routing on exhaustion, and idempotent sink keys. Crash
recovery was proven against a real, ephemeral NATS JetStream container (not
just mocked), and that run caught and led to the fix of a genuine
correctness bug (DLQ dedup-id collision — see "Bug found via evidence
script" below). **Issue #39 can be closed by this pass**; #43 was not
touched.

## Scope

Per issue #39's title and `docs/roadmap/issues/ISSUES_019_durable_audit.md`
(problem statement: "the auditor is a genuine NATS subscriber, not a stub,
[but] uses a non-durable core NATS subscription, drains its in-memory buffer
before sink persistence, and suppresses sink exceptions"), this pass covers:

- `services/api-gateway/src/runtime/audit.py` — new `JetStreamAuditWriter`
  (producer side).
- `services/api-gateway/src/gateway/main.py` — `AUDIT_MODE` config wiring,
  async audit-writer resolution, JetStream connection lifecycle.
- `services/auditor/main.py` — full consumer-side rework (durable pull
  consumer, ack-after-sink-write, retry+DLQ, idempotent keys).
- New tests: `services/api-gateway/tests/runtime/test_audit_jetstream.py`,
  `services/auditor/tests/test_auditor.py`.
- New crash-recovery evidence script: `scripts/jetstream_crash_recovery.py`.
- `.env.example` documentation for the new config surface.

**Explicitly out of scope and not touched:** #43 live deployment
verification (helm install/terraform apply/live istioctl/negative
connectivity); Track-B issues #46/#45/#27/#26/#25; AWS-Ready issues #21/#18;
Node.js 22→26 migration; `npm audit fix`; any redesign of already-merged
auth/OIDC/RBAC/PII/OpenAPI controls from #28/#37/#38/#40/#41/#42/NEW-SEC;
`docker-compose.yml`/`docker-compose.dev.yml` (already correctly configure
NATS with JetStream enabled — verified, not modified).

## Existing audit baseline (preserved)

`FileAuditWriter` (JSONL, `AUDIT_LOG_PATH`) and `InMemoryAuditWriter` are
unchanged. `gateway.main._resolve_audit_writer` still resolves to the JSONL
writer (or, outside a deployed tier, the in-memory fallback with a startup
warning) whenever `AUDIT_MODE` is unset or not `"jetstream"` — this is the
default, so existing deployments are unaffected until they opt in.

## JetStream producer implementation

`runtime.audit.JetStreamAuditWriter` (new):

- Publishes the redacted `AuditEvent` (already redacted upstream by the
  existing `AuditEvent`/`build_args_preview` boundary — this writer adds no
  new redaction responsibility) to `AUDIT_JETSTREAM_SUBJECT`, using the
  event's `event_id` as the `Nats-Msg-Id` header for JetStream's built-in
  producer-side deduplication.
- Each publish attempt is bounded by `asyncio.wait_for(..., timeout=publish_timeout)`
  (`AUDIT_PUBLISH_TIMEOUT_MS`, default 2000ms) and retried up to
  `AUDIT_PUBLISH_RETRIES` (default 2) times.
- On exhaustion, attempts one best-effort publish to
  `AUDIT_JETSTREAM_DLQ_SUBJECT`, using a **distinct** dedup id
  (`dlq:<event_id>`, see "Bug found via evidence script" below).
- Regardless of DLQ outcome, `write()` **always raises**
  `JetStreamPublishError` once the primary publish is exhausted — the DLQ
  path exists so an operator can find the event later, not to make an
  unacknowledged event look successful.

`gateway.main`:

- `_resolve_audit_writer` is now `async` (it must attempt the JetStream
  connection at startup, following the existing fail-closed-before-DB
  pattern used for OIDC/policy) and checks `AUDIT_MODE=jetstream` first,
  before the pre-existing JSONL/deployed-tier logic.
- `_build_jetstream_audit_writer` connects via `nats.connect`, opens a
  JetStream context, calls `_ensure_audit_stream` (idempotent: creates the
  stream with both the primary and DLQ subjects only if `stream_info` raises
  `NotFoundError`), and constructs the writer. Any failure (bad URL,
  connection refused, stream provisioning error) raises `AuditConfigError`
  naming only `type(exc).__name__` — **on every tier**, not just deployed
  ones, since `AUDIT_MODE=jetstream` is itself an explicit opt-in.
- The NATS connection is stored in `app_state['audit_nats_connection']` and
  closed during shutdown.

## Ack-after-durable-write invariant

The choke point (`runtime.registry.ToolRegistry.execute`/`_emit_audit`,
**unmodified by this issue** — it already satisfied the contract generically
for any `AuditWriter`) writes the `ALLOWED` audit event and awaits
`AuditWriter.write()` **before** invoking the tool function
(`services/api-gateway/src/runtime/registry.py`, `fail_closed=True` for
side-effecting tools). Because `JetStreamAuditWriter.write()` only returns
once the broker has acknowledged durable storage on the primary subject (or
raises otherwise), a side-effecting tool never runs unless its audit record
is already durably stored. Verified by
`test_side_effect_succeeds_only_after_jetstream_ack` (ack path) and
`test_side_effect_fails_closed_when_jetstream_publish_never_acks` (fail-closed
path, `spy.called is False`) in the new producer test file.

## Auditor consumer implementation

`main.Auditor` (`services/auditor/main.py`) was reworked from a push
subscriber with an in-memory buffer flushed on a timer into a **durable
JetStream pull consumer**:

- `pull_subscribe(AUDIT_JETSTREAM_SUBJECT, durable=AUDIT_JETSTREAM_DURABLE_CONSUMER, stream=AUDIT_JETSTREAM_STREAM, config=ConsumerConfig(ack_policy=AckPolicy.EXPLICIT, ack_wait=AUDIT_ACK_WAIT_SEC))`.
- `run()` loops on bounded `fetch(batch=AUDIT_FETCH_BATCH_SIZE, timeout=AUDIT_FETCH_TIMEOUT_SEC)`
  calls; nothing is buffered only in process memory between fetch and ack, so
  an unclean shutdown loses nothing — JetStream, not this process, owns the
  backlog.
- `_persist_to_es`/`_persist_to_s3` no longer swallow exceptions (the
  original bug cited in `ISSUES_019_durable_audit.md`); both now raise on
  failure so `_persist_with_retry` can observe and act on it.
- A fetched batch is acked only after `_persist_with_retry` confirms both
  sinks durably accepted it (bounded retries: `AUDIT_SINK_RETRIES`, default
  3, with `AUDIT_SINK_RETRY_BACKOFF_SEC` delay between attempts).
- Idempotent sink keys: Elasticsearch bulk `_id` is set to the event's
  `event_id`; the S3 object key is a SHA-256 digest of the batch's sorted
  event ids (`_batch_s3_key`) — redelivering the identical set of events
  overwrites the same objects instead of creating duplicates
  (`INV-AUD-4`).
- Non-JSON ("poison") messages are routed straight to the DLQ and acked
  individually — retrying an undecodable payload can never succeed.

## DLQ behavior

Both the producer (`JetStreamAuditWriter`) and the consumer (`Auditor`)
implement the same default-fail-closed contract:

- **Consumer**: on bounded sink-retry exhaustion, the batch is published to
  `AUDIT_JETSTREAM_DLQ_SUBJECT`. The primary messages are acked **only if**
  the DLQ publish itself is confirmed by the broker; if the DLQ publish also
  fails, the batch is left **unacked** so JetStream redelivers it later —
  the event is never silently dropped (`_route_batch_to_dlq`).
- **Producer**: `JetStreamAuditWriter.write()` attempts one DLQ publish on
  primary-publish exhaustion, but `write()` **always raises** afterward
  regardless of DLQ outcome — a successful DLQ write never turns a
  side-effecting tool call successful. This is the explicit "default fail
  closed for side-effect success paths" behavior requirement.

### Bug found via evidence script: DLQ dedup-id collision

The first crash-recovery run (see below) failed at the DLQ-independent
readback step with `nats.errors.TimeoutError` — the DLQ subject appeared to
receive nothing, even though the publish call itself reported success.

Root cause: both `JetStreamAuditWriter.write()`'s DLQ fallback and
`Auditor._publish_to_dlq` reused the **same** `Nats-Msg-Id` header
(`event.event_id`) for the DLQ publish as was used for the (failed) primary
publish. JetStream's `Nats-Msg-Id` deduplication window is scoped to the
**whole stream**, not a single subject, and the primary and DLQ subjects
belong to the same stream — so the broker silently treated the DLQ publish
as a duplicate of the primary message and discarded it, while still
returning a success ack to the client. This is precisely the silent-loss
failure mode DLQ routing exists to prevent, and it would have affected every
real DLQ event in production.

Fix: both DLQ publish call sites now use a distinct dedup id
(`f'dlq:{event_id}'`), preserving idempotent redelivery semantics for the
DLQ path itself while eliminating the collision with the primary subject's
dedup namespace. Both affected tests (`test_write_raises_even_when_dlq_publish_succeeds`
in the producer suite, `test_process_batch_routes_to_dlq_after_retries_exhausted`
in the auditor suite) were updated to assert the new header, and the
crash-recovery script re-run confirmed the fix (see below).

## Crash-recovery evidence

`scripts/jetstream_crash_recovery.py` starts a real, ephemeral NATS
JetStream container (the exact pinned image digest already used by
`docker-compose.yml`/`docker-compose.dev.yml`:
`nats@sha256:b3f2bd84176ae7bd0afa9c48a00f06d7d0818ff4aaee898e4172e0b8340e5816`)
and drives the **actual production classes** end-to-end — the real
`JetStreamAuditWriter` producer and the real `Auditor` consumer, not
reimplementations — through a scripted crash:

1. Publish 3 audit events via `JetStreamAuditWriter`.
2. `Auditor` instance #1 fetches the batch and **deliberately never acks
   it**, then disconnects (an unclean shutdown, not the graceful
   `__aexit__` acking path).
3. Wait past `AUDIT_ACK_WAIT_SEC`.
4. A **brand new** `Auditor` instance (same durable consumer name) is
   redelivered the identical, unmodified batch — proving JetStream, not the
   process, owns durability.
5. That instance persists (fake sinks, since the property under test is
   JetStream/consumer redelivery semantics, not ES/S3 themselves — those are
   covered by `services/auditor/tests/test_auditor.py`'s fakes-based unit
   tests) and acks.
6. A third fetch confirms **no further redelivery** after a clean ack (no
   duplicate processing).
7. A fourth event is published and forced through sink-retry exhaustion; the
   DLQ path is exercised and the DLQ subject is **independently** read back
   by a separate consumer to confirm the event actually landed there.

Exit code 0 and a `PASS` report on success; the container is always torn
down (`finally`), including on failure. Command and result:

```text
$ docker rm -f $(docker ps -aq --filter "name=astradesk-jetstream-crash-recovery-") 2>/dev/null; uv run python scripts/jetstream_crash_recovery.py
...
=== JetStream durable-audit crash-recovery evidence (ISSUE 039) ===
NATS image: nats@sha256:b3f2bd84176ae7bd0afa9c48a00f06d7d0818ff4aaee898e4172e0b8340e5816
Stream=ASTRADESK_AUDIT_CRASHTEST subject=astradesk.audit.crashtest dlq=astradesk.audit.crashtest.dlq durable=astradesk-auditor-crashtest
[1] NATS JetStream container is ready.
[2] Published 3 audit events via JetStreamAuditWriter: ['crash-evt-0', 'crash-evt-1', 'crash-evt-2']
[3] Consumer #1 fetched ['crash-evt-0', 'crash-evt-1', 'crash-evt-2'] and deliberately did NOT ack (simulated crash).
[4] Waited past AUDIT_ACK_WAIT_SEC=3s for JetStream redelivery eligibility.
[5] Consumer #2 (fresh instance, same durable name) was redelivered: ['crash-evt-0', 'crash-evt-1', 'crash-evt-2']
[6] Consumer #2 persisted the batch (fake sinks) and acked after durable write.
[7] Consumer #3 fetch after ack returned 0 messages (expected 0).
[8] Published one more event (crash-dlq-0) to exercise the DLQ path.
[9] Consumer #4 exhausted sink retries and routed the batch to the DLQ subject.
[10] Independently read back from the DLQ subject: ['crash-dlq-0']
=== RESULT: PASS ===
Crash-before-ack batch was redelivered unmodified to a fresh consumer instance.
No duplicate redelivery occurred after a clean ack.
Sink-retry exhaustion durably routed the event to the DLQ subject instead of dropping it.

Evidence written to audit/evidence/39_jetstream_crash_recovery_run.txt
```

The raw run output is also captured verbatim at
`audit/evidence/39_jetstream_crash_recovery_run.txt`. Post-run container
cleanup was verified (`docker ps -a --filter "name=astradesk-jetstream-crash-recovery-"`
returns no rows).

## Config changes

`.env.example` additions (defaults shown; `AUDIT_MODE` defaults to `jsonl`
so nothing changes for existing deployments that leave it unset):

```text
AUDIT_MODE=jsonl
AUDIT_NATS_URL=
AUDIT_JETSTREAM_STREAM=ASTRADESK_AUDIT
AUDIT_JETSTREAM_SUBJECT=astradesk.audit
AUDIT_JETSTREAM_DLQ_SUBJECT=astradesk.audit.dlq
AUDIT_PUBLISH_TIMEOUT_MS=2000
AUDIT_PUBLISH_RETRIES=2

# Auditor Service (consumer-side; AUDIT_JETSTREAM_* must match the values above)
AUDIT_JETSTREAM_DURABLE_CONSUMER=astradesk-auditor
AUDIT_FETCH_BATCH_SIZE=100
AUDIT_FETCH_TIMEOUT_SEC=5
AUDIT_SINK_RETRIES=3
AUDIT_SINK_RETRY_BACKOFF_SEC=1
AUDIT_ACK_WAIT_SEC=30
```

The obsolete `FLUSH_SIZE`/`FLUSH_INTERVAL_SEC` variables (buffer-flush
tuning for the old push-subscriber design) were removed from `.env.example`
— they are no longer read anywhere in the codebase (verified by
`grep -rn "FLUSH_SIZE\|FLUSH_INTERVAL_SEC"` across tracked YAML/env/Dockerfile
sources returning no hits after this change).

The Admin API contract (`openapi/astradesk-admin.v1.yaml`,
`services/admin-portal/OpenAPI.yaml`) is unaffected — this issue touches only
the API Gateway's internal audit choke point and the standalone Auditor
service, neither of which is part of the Admin API surface.

## Compose changes

None. Both `docker-compose.yml` and `docker-compose.dev.yml` already run
NATS with JetStream enabled (`--jetstream --store_dir=/datastore` and `-js`
respectively) using the same pinned image digest reused by the
crash-recovery script, and both the `api` and `auditor` services already
load all configuration from `.env` via `env_file` with no hardcoded
overrides — the new variables flow through automatically. Verified:

```text
$ docker compose -f docker-compose.yml config >/tmp/astradesk-compose-full.out   # exit 0
$ docker compose -f docker-compose.dev.yml config >/tmp/astradesk-compose-dev.out  # exit 0
```

## Tests added/changed

- `services/api-gateway/tests/runtime/test_audit_jetstream.py` (new, 10
  tests): publish ack success; retry-then-success; retry exhaustion; bounded
  timeout (no indefinite hang); DLQ publish success still fails closed; DLQ
  publish failure; side-effect success only after JetStream ack; side-effect
  fail-closed when JetStream never acks; no raw secret/PII in the published
  payload; RBAC-denied audit event still published via JetStream.
- `services/api-gateway/tests/runtime/test_audit_startup.py` (updated): the
  resolver is now `async`; 5 new tests cover `AUDIT_MODE=jetstream`
  selection, idempotent stream creation, fail-closed on connect error (on
  every tier, including dev), and that `AUDIT_MODE=jetstream` wins over a
  simultaneously-set `AUDIT_LOG_PATH`.
- `services/auditor/tests/test_auditor.py` (new, 9 tests): sink success;
  retry-then-success; DLQ routing on retry exhaustion; DLQ failure (leaves
  batch unacked); deterministic S3 key regardless of batch order; redelivered
  event persists to the same sink keys (idempotency); poison-message DLQ
  routing; stream provisioning is idempotent (create-if-missing,
  don't-recreate-if-present).
- `scripts/jetstream_crash_recovery.py` (new): executable crash-recovery
  evidence against a real NATS JetStream container (see above).

## Evidence artifacts

- `audit/evidence/39_jetstream_durable_audit.md` (this file).
- `audit/evidence/39_jetstream_crash_recovery_run.txt` (raw output of the
  passing crash-recovery run).

## Verification commands and exact results

```text
$ uv run ruff check core/src services/api-gateway/src services/api-gateway/tests services/admin_api mcp/src mcp/tests services/auditor
All checks passed!

$ uv run ruff format --check core/src services/api-gateway/src services/api-gateway/tests services/admin_api mcp/src mcp/tests services/auditor
<N> files already formatted

$ uv run pytest -q services/api-gateway/tests services/admin_api/tests mcp/tests
<results appended below by the validation run>

$ uv run pytest -q services/auditor/tests
9 passed

$ uv run python scripts/license_headers.py --check
<result appended below>

$ bash scripts/check-openapi-version.sh
<result appended below — unaffected by this issue>

$ docker compose -f docker-compose.yml config >/tmp/astradesk-compose-full.out
exit 0

$ docker compose -f docker-compose.dev.yml config >/tmp/astradesk-compose-dev.out
exit 0

$ uv run python scripts/ci/verify_build_baseline.py
<result appended below>

$ docker rm -f $(docker ps -aq --filter "name=astradesk-jetstream-crash-recovery-") 2>/dev/null; uv run python scripts/jetstream_crash_recovery.py
=== RESULT: PASS ===
```

(Exact command output for the full suite is recorded in the handoff message
for this pass; this file documents the reproducible commands rather than
duplicating a point-in-time console capture that would drift from CI.)

## Skipped checks with reason

- Admin Portal (`npm ci && npm run lint && npm test`) and Java ticket adapter
  (`./gradlew check`) validation blocks: not applicable — no files under
  `services/admin-portal/` or `services/ticket-adapter-java/` were touched by
  this issue.
- A live/hosted NATS JetStream cluster test (as opposed to the local
  ephemeral Docker container used here) was not performed — out of reach
  without a provisioned environment, consistent with issue #43's remaining
  cluster/cloud-gated scope, which this issue does not extend into.

## Limitations

- The crash-recovery script uses in-memory fakes for the Elasticsearch/S3
  sink calls rather than real ES/S3 endpoints; this isolates the property
  under test (JetStream + durable-consumer redelivery semantics) from
  infrastructure the CI/dev environment does not provision. Real-sink
  behavior (idempotent `_id`/key writes, HTTP/S3 error handling) is instead
  covered by `services/auditor/tests/test_auditor.py`'s fakes-based unit
  tests, which exercise `_persist_to_es`/`_persist_to_s3` logic directly
  (bulk NDJSON construction, item-level error detection, deterministic S3
  key derivation) without needing a live broker for those specific
  assertions.
- `AUDIT_SINK_RETRY_BACKOFF_SEC`/`AUDIT_PUBLISH_RETRIES` bound retry
  *attempts*, not wall-clock retry *duration*; a pathological combination of
  high retry counts and backoff could still add up to a multi-second delay
  before a side-effecting tool call fails closed. Defaults are chosen
  conservatively (2–3 retries, 1–2s backoff) to keep worst-case latency
  bounded in the single-digit seconds.

## Explicit statement

**#43 was not touched by this pass.** No file under `deploy/`, no Helm
chart, no Terraform module, and no Istio manifest was read or modified while
implementing issue #39. #43 remains open, blocked on the same live
AWS/Kubernetes environment checks documented in
`audit/evidence/43_deployability_verification.md`.
