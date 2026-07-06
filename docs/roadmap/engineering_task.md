<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: docs/roadmap/engineering_task.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# ENGINEERING TASK — v0.3.1 Commercial Workhorse Hardening (Safety Core)

**Track**: A (gate to first commercial client)
**Milestone**: `v0.3.1 — Commercial Workhorse Hardening` (additive; between v0.3.0 and v0.4.0)
**Source of truth**: `audit-report.md` Rev 2, `roadmap.md` §2 Phase 1–2
**Design stance**: contract-first, evidence-driven, fail-closed. Every task states invariants, interfaces, failure modes, and the artifact that proves it done.

> **Status update (2026-07-06, issue #65)**: the 8-issue Safety Core scope
> defined in this file (§5 Issue index: rescoped #9/#16/#19/#28,
> NEW-1/NEW-2/NEW-4/NEW-SEC — closed as #37/#38/#39/#28/#40/#41/#42 and the
> admin-proxy-auth PR) is **fully closed**. The broader `v0.3.1` milestone
> is **not** complete: issue #43 (Helm/Terraform/Istio live deployability,
> consolidated from the roadmap's separate Phase 2 deployability item and
> added to this milestone after this file was written) remains open,
> blocked on live AWS/Kubernetes checks — see
> `audit/evidence/43_deployability_verification.md`. Do not read this
> update as closing `v0.3.1`.

---

## 0. Engineering philosophy — best patterns, immunized against their childhood diseases

We are not inventing a new agent paradigm. We adopt the proven shape of MCP-first, policy-governed agent runtimes and **deliberately inoculate against the failure modes those systems are known to hit in their first years.** The audit findings are, almost one-to-one, the industry's known teething diseases. We treat that as a gift: the cures are known.

| Proven analog | Childhood disease (observed industry-wide) | AstraDesk audit symptom | Our inoculation (this milestone unless noted) |
| :--- | :--- | :--- | :--- |
| LangChain / LangGraph | Leaky abstractions, hidden control flow, untyped tool I/O | Orchestrator + keyword fallback diverge in policy enforcement | Single enforcement point both paths traverse; typed tool contract |
| AutoGPT-era agents | Unbounded autonomy; no approval; cost/loop runaway | Write tools can fire without role on fallback path (§7) | Deny-by-default side-effect metadata + approval record (ISSUE 016) |
| Early MCP adopters | Tool-poisoning via descriptions; declared≠actual schema; auth bolted on late | `schema_ref` never enforced at invoke (§10) | Schema-hash negotiation + reject-on-mismatch (ISSUE 016/028 support) |
| DIY OIDC/JWT | HS256 dev secret reaches prod; no issuer/aud/expiry checks; no rotation | Active ingress uses HS256 fallback while JWKS verifier sits unused (§7) | Wire JWKS, fail-closed on missing prod config (ISSUE 009) |
| In-process RAG stacks | Embedding coupled to request path → latency, OOM, cold-start | `SentenceTransformer` constructed in Gateway lifespan (§6) | Isolate into worker — **Track B**, reserved here by interface only |
| Audit/event pipelines | Event loss on crash (non-durable, ack-before-write) | Core NATS sub, buffer drained before sink persist (§6 Critical) | JetStream durable, ack-after-durable-write, DLQ (ISSUE 019) |
| Helm/K8s first charts | Secrets in values; root containers; wrong probes; floating tags | Creds in compose/values/tfvars; missing `USER`; floating tags (§7,§3) | Secret refs, non-root UID, pinned digests (ISSUE NEW-02 / NEW-01) |
| PII-naive RAG/LLM | User data leaks into logs/traces/vector store/model | PII middleware is a no-op; raw query in spans (§7 Critical) | Redact-before-emit, egress allow-list (ISSUE NEW-04) |
| Multi-tenant retrofits | `tenant_id` added late → data bleed, painful migration | Schema has no tenant column (§ issue #27) | Reserve tenant boundary in schema design now — **Track B** |

**The one invariant that explains half the audit**: in agent runtimes, the *fallback / non-LLM path* is where authority controls quietly fail. Every safety control in this milestone must be proven on **both** the LLM-planned and keyword-fallback execution paths. This is the recurring disease; it gets a dedicated cross-cutting test.

---

## 1. Scope of v0.3.1

In: ingress auth, per-tool authorization invariance, PII/egress boundary, durable audit, fail-closed policy, secret removal, reachable-vuln remediation, reproducible build baseline, executable integration gate.

Out (deferred to Track B with rationale): RAG/embedding worker split, SBOM/sign/canary release pipeline, multi-tenancy, Temporal, Ragas. These are direction, not the client-safety gate.

---

## 2. Cross-cutting invariants (apply to every issue below)

- **INV-DUAL-PATH** — No authority control may depend on the LLM planner being chosen. Identical denial behavior on LLM-planned and keyword-fallback paths. Proven by one shared negative test matrix.
- **INV-FAIL-CLOSED** — Absence or failure of an authority dependency (OIDC config, OPA endpoint, schema hash) results in denial/startup-abort, never silent allow.
- **INV-NO-RAW-EGRESS** — No raw user input reaches a log, span attribute, external model, or external tool before classification/redaction.
- **INV-EVIDENCE** — Each task is "done" only when it emits a reproducible evidence artifact (test run, scan report, render output), not when code merely exists.
- **INV-LOCAL-MODE-EXPLICIT** — Any developer convenience that weakens a control (symmetric token, seeded secret) is reachable only behind an explicit, named, non-default local mode that production startup refuses.

---

## 3. Dependency order (build sequence)

```
Phase 0 (done elsewhere): main green + develop gated
        │
        ▼
ISSUE 009 (OIDC ingress) ──► identity is trustworthy
        │
        ▼
ISSUE 016 (RBAC invariant) ──► authority is trustworthy   ◄── ISSUE 028 (fail-closed OPA) reinforces
        │
        ▼
ISSUE NEW-04 (PII/egress) ──► data handling is trustworthy
        │
        ▼
ISSUE 019 (durable audit) ──► evidence is trustworthy
        │
        ▼
ISSUE NEW-01 (supply chain) + NEW-02 (reproducible build) ──► deployment is trustworthy
        │
        ▼
Integration gate executable (roadmap Phase 2.5) ──► all of the above provable in CI
        │
        ▼
✅ Workhorse v1 Gate (roadmap §2)
```

Rationale for order: you cannot authorize (016) before you can authenticate (009); you cannot prove anything in CI without a reproducible build (NEW-02); audit durability (019) must precede client work because lost audit evidence is unrecoverable.

---

## 4. Verification strategy

| Layer | Method | Gate |
| :--- | :--- | :--- |
| Identity | Negative tests: bad issuer/aud/expiry/sig; missing-prod-config startup abort | Fails closed; HS256 unreachable outside local mode |
| Authority | Dual-path matrix: each `write`/`execute` tool × {LLM, fallback} × {authorized, unauthorized} | Unauthorized denied on every cell |
| Data | Representative PII/secret corpus through ingress → assert absent from logs/spans/egress | Zero leak |
| Evidence | Induced crash + sink outage during audit flush → assert zero event loss after recovery | No loss; DLQ replayable |
| Supply chain | `pip-audit`/image scan; reachability triage | Zero unaccepted reachable Critical/High |
| Build | `docker compose config` valid; image build from lock; non-root assertion | All green in CI |
| Dual-path regression | A single CI test that fails if any side-effect tool is registered without role metadata | Prevents reintroduction |

---

## 5. Issue index (this milestone)

| File | # | Type | Principle | GA-gating |
| :--- | :--- | :--- | :--- | :--- |
| `ISSUES_009_oidc_ingress.md` | rescope #9 | RESCOPE | Security | yes |
| `ISSUES_016_rbac_invariant.md` | rescope #16 | RESCOPE | Security | yes |
| `ISSUES_NEW-04_pii_egress_boundary.md` | NEW-4 | NEW | Security | yes |
| `ISSUES_019_durable_audit.md` | rescope #19 | RESCOPE | Security | yes |
| `ISSUES_028_opa_fail_closed.md` | rescope #28 | RESCOPE | Security | yes |
| `ISSUES_NEW-01_supply_chain.md` | NEW-1 | NEW | Security | yes |
| `ISSUES_NEW-02_reproducible_build.md` | NEW-2 | NEW | Simplicity | yes |
| `ISSUES_NEW-SEC_admin_proxy_auth.md` | NEW-SEC | NEW | Security | yes |

Each issue file is self-contained and follows one contract template (problem → analog disease → invariants → interface → failure modes → acceptance → evidence → out-of-scope).

---

## 6. Tracker actions (additive; human-executed)

1. Create milestone `v0.3.1 — Commercial Workhorse Hardening`.
2. Create issues NEW-01, NEW-02, NEW-04 under `v0.3.1`.
3. Comment+relabel (do not reopen) #9, #16, #19, #28 with the rescoped contract from their issue files; assign to `v0.3.1`.
4. Leave #18, #21 in `v0.3.0`; they feed the same gate.
5. No close/reopen of historical milestones. This milestone is purely additive.
