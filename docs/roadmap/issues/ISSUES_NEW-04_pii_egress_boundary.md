# ISSUES_NEW-04 — Ingress PII/secret redaction & egress boundary (NEW)

- **Track / Milestone**: A / `v0.3.1`
- **Type**: NEW
- **Workhorse principle**: Security (good-sense)
- **GA-gating**: yes — a client's data must not leak through our telemetry or tool/model calls
- **Audit anchors**: §7 (Critical); `mcp/src/gateway/middleware.py:96-110`; `services/api-gateway/src/model_gateway/guardrails.py:70-89`; `services/api-gateway/src/runtime/rag.py:329-333`
- **Depends on**: ISSUE 009 (a request identity to attach classification to)
- **Independent of**: OPA policy authoring (028)

## Problem (current evidence)
The PII middleware is a no-op. Model guardrails record a raw input preview **before** redaction. RAG traces raw query text into span attributes. PII/secrets can therefore enter logs, traces, external model calls, and external tools with no ingress boundary.

## Industry analog & childhood disease
PII-naive RAG/LLM stacks leak user data into trace attributes, prompt logs, and the vector store, then discover it during a compliance review. The disease is **"observe first, redact later"** — telemetry is added for debugging and quietly becomes an exfiltration path. We immunize with redact-before-emit and an explicit egress allow-list.

## Target contract (invariants)
- **INV-PII-1 (INV-NO-RAW-EGRESS)**: No raw user input reaches a log line, span attribute, external model, or external tool before classification + redaction.
- **INV-PII-2**: Data classification is attached at ingress and propagates with the request; downstream emitters consult it.
- **INV-PII-3**: Egress targets (models, tools, sinks) are governed by an allow-list; an unlisted target is denied.
- **INV-PII-4**: Redaction is applied to span attributes and structured logs at the emitter, not optionally at the call site.

## Interface / design
- Replace the no-op middleware with a real ingress classifier (configurable detectors: emails, tokens/secrets, keys, configurable regex packs).
- A redaction utility used by the tracing/logging layer so raw text cannot be set as a span attribute.
- Egress allow-list config consulted by model_gateway and tool adapters.

## Failure modes & required behavior
| Failure | Required behavior |
| :--- | :--- |
| Secret/email/key in user input | Redacted token in logs/traces; original never emitted |
| New emitter added without redaction | Lint/test fails (no raw attribute setter on user text) |
| Egress to unlisted external target | Denied + audited |
| Redactor throws | Fail-closed: drop the field, do not emit raw |

## Acceptance criteria (Definition of Done)
- [ ] Ingress classifier active; no-op middleware removed.
- [ ] Representative PII/secret corpus → asserted absent from logs, span attributes, model payloads, and tool payloads.
- [ ] RAG query and guardrail preview redacted before tracing.
- [ ] Egress allow-list enforced with a negative test (unlisted target denied).
- [ ] Static check forbidding raw user text as a span attribute.

## Verification evidence (artifact)
Leak-corpus test report (zero-leak assertion); egress negative test log.

## Out of scope
Full DLP product integration, tokenization vault (Track B).
