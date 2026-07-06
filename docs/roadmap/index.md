<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: docs/roadmap/index.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# AstraDesk Roadmap — From Audit to Commercial Workhorse

**Status date**: 2026-06-28
**Inputs**: `audit-report.md` Rev 2 (tree `2d59d75`), live tracker (28 issues / 7 milestones)
**Source of truth**: every roadmap item traces to an audit finding or a tracked issue. No aspirational item is included without evidence. Effort is expressed as relative horizons and **evidence-backed gates**, not invented dates.

---

## 0. How to read this roadmap

AstraDesk is being driven to one near-term outcome: **a dependable "workhorse" framework a developer can deploy to serve a commercial client — safely, simply, and from trustworthy docs.** Enterprise-GA polish (SBOM, signing, canary evaluation, multi-tenancy) is real and planned, but it is **the forward direction, not the entry gate.**

The roadmap therefore has two tracks:

- **Track A — Commercial Workhorse v1**: the minimum that makes AstraDesk safe and reproducible enough to run a real client. This is the priority. It ends at a named, testable gate.
- **Track B — Enterprise Direction**: the credible evolution beyond Workhorse v1, sequenced for the partner. Real work, later.

Both tracks are mapped onto the **existing milestone taxonomy** (`v0.3.0`–`v0.6.0`) plus **one additive milestone** (`v0.3.1`). Nothing closed is reopened; history is preserved.

---

## 1. The Workhorse Contract (acceptance principles)

These four principles are the definition of "good." Every Track A item exists to satisfy one of them. They are **acceptance bars, not slogans**.

| Principle | What it means concretely | Done when |
| :--- | :--- | :--- |
| **Security (good-sense)** | It will not harm a client: real auth at ingress, no secrets in the repo, write/execute tools cannot fire without authorization on **any** code path, PII does not leak into logs/traces/models, audit evidence is not lost on crash. | Negative tests prove each control holds, including the keyword-fallback path. |
| **Simplicity / easy implementation** | A developer at a client firm stands the stack up from tracked sources in minutes, on one documented baseline. | `docker compose config` is valid, all images build from `uv.lock`/`pyproject.toml`, every `make` target in the docs exists and runs. |
| **Trustworthy documentation** | Docs describe what the code does, not what was once planned. API routes, ports, commands, and contracts match reality. | Doc snippets and routes are conformance-tested in CI; no claim outranks evidence. |
| **Zero empty / misleading artifacts** | No `.gitkeep` standing in for a feature, no no-op middleware presented as a control, no design YAML indistinguishable from a deployed one. | Every artifact is either implemented-and-tested or explicitly labelled `DESIGN EXAMPLE — NOT IMPLEMENTED`. |

---

## 2. Track A — Commercial Workhorse v1

### Phase 0 — Stabilize (days; blocks everything, partner-visible)

The single worst look for a partner is a red default branch.

| Item | Evidence | Action |
| :--- | :--- | :--- |
| `origin/main` CI is red (Sonar inline-option defect) | audit §5, §11.1; `84a_ci_latest_failed.txt` | Remove the inline shell continuation, pin the scanner image, require one aggregate green status. |
| CI does not gate `develop` | this cycle's `fix/ci-trigger-develop` | Land the trigger PR (base=`develop`); confirm gates fire on the next feature→develop PR. |

**Exit:** `main` green, `develop` gated. Nothing else proceeds until this holds.

### Phase 1 — Safety Core ("won't hurt a client") → milestone `v0.3.1` (new)

This is the heart of the workhorse. All items are audit Criticals/Highs.

1. **Secrets out of the tree.** Remove credential-bearing defaults from Compose/Helm/Terraform, rotate any reused values, add secret-scanning pre-commit + CI gate. *(§7, H9; NEW-1 partial)*
2. **Real ingress auth.** Wire the existing JWKS/OIDC verifier into the active Gateway; disable the HS256 dev-secret fallback outside an explicit local mode; validate issuer/audience/expiry. *(§7, issue #9 → RESCOPE)*
3. **RBAC invariant on side effects.** Declare `side_effect` + `allowed_roles` in registry metadata; deny-by-default; ensure `write`/`execute` tools are gated on **both** the LLM-planned and keyword-fallback paths. *(§7, issue #16 → RESCOPE)*
4. **PII boundary.** Replace the no-op PII middleware; redact before span attributes/logs; egress allow-list; test with representative PII/secrets. *(§7, NEW-4)*
5. **Policy fail-closed (minimum viable OPA).** Guarantee no side-effect tool bypasses policy even before a full OPA workload exists; deploy fail-closed OPA + versioned bundle as the completion of this item. *(§7, issue #28 → RESCOPE)*
6. **Durable audit — done.** The auditor is now a JetStream durable pull consumer with ack-after-durable-write, bounded retry + DLQ, and idempotent sink keys (Elasticsearch `_id`, digest-derived S3 key); the pre-existing JSONL baseline remains the default, non-breaking fallback (`AUDIT_MODE=jsonl`), with JetStream an explicit opt-in (`AUDIT_MODE=jetstream`). Crash-recovery was proven against a real, ephemeral NATS JetStream container, not just mocks (`scripts/jetstream_crash_recovery.py`) — see `audit/evidence/39_jetstream_durable_audit.md`. *(§6 Critical, issue #19 → RESCOPE, resolved by issue #39)*
7. **Dependency triage (reachable only).** Classify the 102 advisory records by runtime-image presence and reachability; remediate reachable Critical/High; archive a zero-unaccepted evidence file. *(§7, NEW-1)*

**Why here, not later:** these are the controls that decide whether the framework can touch a real client's data and systems without causing harm. They are the literal meaning of "secure workhorse."

### Phase 2 — Deployability & Reproducibility ("easy to stand up") → `v0.3.0` + `v0.3.1`

1. **Valid full Compose.** Fix the `mcp → kb-service` profiled-out dependency so `docker compose config` validates. *(§3.1; NEW-2)*
2. **Reproducible images.** Rebuild all Python images from `pyproject.toml`/`uv.lock` on **Python 3.13**, non-root `USER`, drop the missing-`requirements.txt` copies. *(§3.1, §3.3, §7; NEW-2)*
3. **One baseline, pinned.** Align dev/prod DB+cache (pgvector image for dev), pin patches/digests; verify the pgvector migration on an empty volume. *(§6)*
4. **Deployment verified, partially — all offline checks done and the canonical Istio architecture decision applied; only cluster-gated checks remain.** `helm lint`/`helm template`, `istioctl validate`, and `terraform validate` (root + all 5 modules: `vpc`, `eks`, `rds-postgres`, `rds-mysql`, `s3`) now all pass (four real bugs found and fixed: two Helm template/naming bugs, one Istio schema bug, one Istio routing-order bug; plus the `eks` module's incompatibility with the current `hashicorp/aws` provider line resolved via a `required_providers` version constraint — see `audit/evidence/43_deployability_verification.md`). The maintainer chose **Generation A** (`astradesk-prod`, routes all four services, matches both tracked pipelines) as canonical over Generation B (`astradesk`, API-only routing, not referenced by any executable pipeline step); Generation B is relocated to `deploy/istio/generation-b-reference/` (kept for reference, not applied by `kubectl apply -f deploy/istio/`), and stale top-level `infra/` Terraform paths in `Jenkinsfile`/`.gitlab-ci.yml`/referencing docs are fixed to `deploy/infra/`. Porting Generation B's `AuthorizationPolicy`/certificate strategy forward is explicitly deferred to a separate future issue, not part of #43. `helm install`, `terraform plan`/`apply`, `istioctl analyze` against a live mesh, and the negative-connectivity test still require a provisioned cluster/AWS account and were not performed. *(issue #43, consolidating #5/#12/#15/#17 → in progress, not closed)*
5. **Executable integration gate.** Repair `tests/integration_tests.py` collection, mark every test, run Compose-backed `pytest -m integration` as a protected gate. *(§3.2, issue #18 → RESCOPE)*

### Phase 3 — Trustworthy Docs & Honest Artifacts ("developer can rely on it") → `v0.4.0`

1. **Kill doc drift.** Reconcile Gateway route (`/v1/run` vs documented `/v1/agents/run`), README ports (8000/8080), and the Make-target mismatch; generate command refs from `make help`. *(§4, §3.1)*
2. **`make test` == CI.** Make the documented completion command run the same protected checks (not 11 tests / 22%). *(issue #14 → RESCOPE)*
3. **API contract conformance.** Structural OpenAPI diff gate; fix the 2 extra ops + 42 path-template differences in the Admin runtime. *(§10, NEW-3)*
4. **Label or implement every example.** Mark non-existent design YAMLs `DESIGN EXAMPLE — NOT IMPLEMENTED`; link real paths for implemented controls. *(§4)*
5. **Portal E2E for real.** Playwright + mock IdP covering login→agent-query, not mock data. *(issue #23 → implement)*
6. **The Workhorse Implementation Guide.** A new developer doc: "stand up AstraDesk for a client in N documented steps" — the deliverable that makes it a workhorse for integrators. *(direction of §9 doc-quality findings)*

### ✅ GATE — Commercial Workhorse v1 (definition of "can start client work")

AstraDesk is client-deployable when **all** of the following produce reproducible evidence:

- [ ] `main` and `develop` CI green; integration gate executable and passing.
- [ ] No secret in any tracked file; secret-scan gate active.
- [ ] OIDC enforced at active ingress; HS256 fallback disabled outside local mode.
- [ ] Every `write`/`execute` tool denies without role on **both** planning paths (negative tests prove it).
- [ ] PII redacted before logs/traces/egress (tested).
- [ ] Audit durable across an induced crash (recovery test passes). **Done for `AUDIT_MODE=jetstream`**: `scripts/jetstream_crash_recovery.py` proves, against a real NATS JetStream container, that a batch fetched-but-never-acked before a simulated crash is redelivered unmodified to a fresh consumer instance, with no duplicate redelivery after a clean ack and DLQ routing on sink-retry exhaustion (`audit/evidence/39_jetstream_durable_audit.md`, issue #39). Box stays unchecked because the default `AUDIT_MODE=jsonl` baseline (unchanged, non-durable-consumer local file sink) remains the out-of-the-box mode; JetStream durability requires the explicit opt-in.
- [ ] `docker compose config` valid; all images build from lockfiles on Python 3.13; non-root.
- [ ] Helm/Terraform/Istio validated (no UNVERIFIED on deployment). **Offline/static validation fully passes**: `helm lint`/`template`, `terraform validate` (root + all 5 modules, including `eks`), and `istioctl validate` (all 14 tracked `deploy/istio/` files, both manifest generations) all exit 0 (`audit/evidence/43_deployability_verification.md`). **The canonical-Istio-generation decision is resolved and applied**: Generation A (`astradesk-prod`) is canonical, matches both tracked pipelines' namespace, and routes all four services; Generation B (`astradesk`, API-only routing, never referenced by an executable pipeline step) is relocated to `deploy/istio/generation-b-reference/`, kept for reference but no longer applied by `kubectl apply -f deploy/istio/`; porting its `AuthorizationPolicy`/certificate additions forward is deferred to a separate future issue. Stale top-level `infra/` Terraform paths in `Jenkinsfile`/`.gitlab-ci.yml` and referencing docs are fixed to `deploy/infra/`. This box stays unchecked solely for the **cluster/cloud-gated checks** (`helm install`, `terraform plan`/`apply`, live `istioctl analyze`, the negative-connectivity test), none of which can run without a provisioned cluster/AWS account.
- [ ] Reachable Critical/High dependency advisories remediated or formally accepted with expiry.
- [ ] API routes/contracts and `make` targets match docs (conformance-tested).
- [ ] No empty/misleading artifact remains unlabelled.
- [ ] Workhorse Implementation Guide published and followed end-to-end by someone who did not write it.

This gate is **below** enterprise GA and **above** "pilot with side effects disabled." It is the bar at which a developer can responsibly run a commercial client.

---

## 3. Track B — Enterprise Direction (for the partner; real, sequenced)

Shown as direction, not entry requirement. Each maps to existing milestones, re-themed honestly.

### B.1 Release-grade supply chain & pipeline → `v0.4.0`/`v0.5.0`
Complete PIPLINE stages 6–12: multi-arch build, SBOM (`syft`), scan (`grype`/`trivy`), `cosign` sign+verify, GHCR push by immutable digest, environment promotion, canary online-evaluation gates. *(§5; NEW-1 full)*

### B.2 Runtime isolation & SLO qualification → `v0.5.0`
Split RAG/embedding out of the API Gateway into a separately scaled worker with a bounded RPC contract; remove duplicate inference; add k6/Locust load + fault-injection with p95/tool-success assertions. *(§6, NEW-5)*

### B.3 Enterprise features → `v0.5.0`/`v0.6.0`
Multi-tenancy (per-tenant memory/data; schema `tenant_id`) *(issue #27)*; Temporal durable workflows *(issue #25)*; RAG evaluation with Ragas *(issue #26)*; advanced OPA RBAC beyond the Phase-1 fail-closed minimum *(issue #28)*.

### B.4 Operational resilience → `v0.6.0`
Executed Postgres/RAG/audit backup-restore drills with measured RPO/RTO and incident authority; Prometheus alert rules + Alertmanager with proven notification delivery. *(NEW-6; issue #24)*

---

## 4. What we will NOT promise yet (anti-fantasy)

To keep the partner conversation credible:

- **No certification claims.** `docs/en/08_security_governance.md` is a conceptual mapping, not an assessment. SOC2/ISO statements are out of scope until evidenced.
- **No "enterprise-ready" label on Workhorse v1.** It is commercial-client-capable under defined controls, not a multi-tenant SaaS-grade platform.
- **No invented dates beyond tracked milestones.** Horizons are gates with evidence; calendar dates inherit from the tracker (`v0.3.0` 2026-07-18 …) and move only with re-baseline, not optimism.
- **No GA until Track A gate + B.1 supply-chain + B.2 isolation are evidenced.**

---

## 5. Tracker actions (additive only — no history broken)

1. **Add milestone `v0.3.1 — Commercial Workhorse Hardening`** between `v0.3.0` and `v0.4.0`. This is the Track A safety/deployability gate. Purely additive; touches no closed milestone.
2. **Create NEW-1…NEW-6** as issues, assigned: NEW-1/NEW-4 → `v0.3.1`; NEW-2 → `v0.3.1`; NEW-3 → `v0.4.0`; NEW-5 → `v0.5.0`; NEW-6 → `v0.6.0`.
3. **RESCOPE in place** (comment + relabel, do not reopen): #9, #16, #18, #19, #28 carry residual workhorse debt into `v0.3.0`/`v0.3.1`; #14, #5, #12, #15, #17 carry deployability/verification debt.
4. **KEEP**: #21 (OIDC portal) and #23 (E2E) move into the Track A scope they belong to; #24/#25/#26/#27 stay in Track B milestones.
5. All execution (issue/milestone creation, closing, labelling) is performed by a human; this roadmap is the plan, not the mutation.

---

## 6. One-line summary for each audience

- **For the integrator/developer**: AstraDesk reaches a defined, tested "safe to deploy for a client" gate (Track A) before any enterprise-scale feature work.
- **For the partner**: a credible, evidence-anchored evolution from working framework → release-grade supply chain → isolated, multi-tenant, operationally-qualified platform (Track B), with no claim ahead of proof.
