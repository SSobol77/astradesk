<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: docs/roadmap/issues/ISSUES_NEW-05_rag_isolation_slo.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# ISSUES_NEW-05 — RAG/embedding isolation & SLO qualification (NEW)

- **Track / Milestone**: B / `v0.5.0`
- **Type**: NEW
- **Workhorse principle**: Security/robustness via fault containment (enterprise direction)
- **GA-gating**: GA-direction (not the Workhorse v1 gate); reserved by interface now
- **Audit anchors**: §6 (High); `services/api-gateway/src/runtime/rag.py:100-145`, `311-355`; `services/api-gateway/src/gateway/main.py:119-184`; `.claude/PIPLINE.md:20`
- **Depends on**: NEW-02 (reproducible images), NEW-03 (stable contracts to extend with an RPC boundary)

## Problem (current evidence)
The API Gateway constructs `SentenceTransformer` in-process during lifespan and performs model placement at startup; retrieval computes the same query embedding twice (before and inside the traced block). A single process owns request admission, DB/Redis clients, BM25, model memory, and embedding compute. SLO targets (p95 ≤ 8s, tool success ≥ 95%) are documented but not enforced by any load/canary test.

## Industry analog & childhood disease
RAG stacks that embed inference in the request process suffer cold-start nondeterminism (model download blocks readiness), OOM under concurrency, GPU/CPU contention, and a single fault domain that takes the whole gateway down. The disease is **co-locating heavy ML with request admission "to ship faster,"** then being unable to scale or isolate failures. We immunize by splitting embedding/RAG into a bounded, separately scaled worker and proving degraded behavior under load.

## Target contract (invariants)
- **INV-RAG-1**: Embedding/RAG execution lives behind a bounded RPC contract in a separately scaled worker; the Gateway holds no model in-process.
- **INV-RAG-2**: Gateway liveness is independent of model/worker readiness; readiness states are explicit.
- **INV-RAG-3**: Each query embedding is computed **once** per request; cache hit/miss paths do not recompute.
- **INV-RAG-4**: The RPC contract defines timeout, queue bound, cancellation, and overload (backpressure/reject) behavior.
- **INV-RAG-5**: p95 latency and tool-success SLOs are asserted by executable load + fault-injection tests, not documentation.

## Interface / design
- Extract embedding/retrieval into a worker service with a typed RPC contract (bounded concurrency, timeouts).
- Pre-bake model artifacts into the worker image; Gateway calls the worker.
- Remove duplicate inference; single compute passed into search.
- k6/Locust workloads + dependency fault injection in CI/perf stage with percentile assertions.

## Failure modes & required behavior
| Failure | Required behavior |
| :--- | :--- |
| Worker overloaded | Backpressure/reject with bounded latency, not unbounded queue |
| Worker unavailable | Gateway stays live; RAG path degrades explicitly |
| Model download slow at start | Worker readiness gated; Gateway readiness independent |
| Request cancelled | Embedding/search cancelled, resources released |
| p95 regression | Perf gate fails |

## Acceptance criteria (Definition of Done)
- [ ] No ML model loaded in the Gateway process; embedding behind RPC.
- [ ] Single embedding compute per request (hit + miss covered).
- [ ] Timeout/queue/cancellation/overload behavior implemented and tested.
- [ ] Load + fault-injection suite asserts p95 ≤ target and tool-success ≥ target.
- [ ] Gateway readiness independent of worker/model readiness.

## Verification evidence (artifact)
Load-test report with percentile assertions; fault-injection results; cold-start readiness log.

## Out of scope
Model selection/quality tuning, multi-model routing, Ragas quality eval (#26).
