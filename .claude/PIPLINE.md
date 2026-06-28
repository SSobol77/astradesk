---
description: AstraDesk CI/CD pipeline standards, quality gates, artifact rules, and release promotion policy.
alwaysApply: true
---

Author: Siergej Sobolewski

# PIPLINE.md — AstraDesk CI/CD Pipeline Standards

## Gate Taxonomy

AstraDesk uses two gate levels.

### Track A — Commercial Workhorse / v0.3.1 Safety Core

This is the first client-facing gate. It focuses on controls that prevent harm:

- reproducible build baseline
- valid Compose graph
- real OIDC/JWKS ingress
- RBAC invariant on every side-effect path
- fail-closed policy
- schema-hash enforcement
- PII/secret egress boundary
- durable audit
- reachable Critical/High dependency remediation
- executable integration gate

### Track B — Enterprise Direction

These are required for later enterprise-grade promotion, but they are not allowed to block the v0.3.1 Safety Core unless the issue explicitly says so:

- full SBOM release publishing
- cosign signing
- canary online evaluation
- advanced RAG/embedding worker split
- multi-tenancy
- disaster-recovery automation
- Temporal/Ragas evaluation layers

When in doubt, do not pull Track B into the v0.3.1 Safety Core. Reserve interfaces only.

## Pipeline Stages (Required Order)

All services and domain packs must pass through these stages before promotion to production.

| Stage               | Tooling                                                        | Gate                                                                                                                       |
| :------------------ | :------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------- |
| 1. Lint             | `ruff` (Python), `eslint` (TS), `checkstyle` (Java)            | Zero errors                                                                                                                |
| 2. Typecheck        | `mypy` (Python), `tsc --noEmit` (TS), Gradle compile (Java)    | Zero errors                                                                                                                |
| 3. Unit Test        | `pytest` (Python), `vitest` (TS), `junit` (Java)               | Pass + coverage evidence generated; no unexplained 0.0% new-code coverage; 90% is the target gate for production hardening |
| 4. Integration Test | `pytest -m integration` with Docker Compose                    | Pass                                                                                                                       |
| 5. Red Team         | `tests/red_team_tests.py`                                      | Prompt injection blocked                                                                                                   |
| 6. Build            | Docker multi-arch (`linux/amd64`, `linux/arm64`)               | Success                                                                                                                    |
| 7. SBOM             | `syft` → `sbom.spdx.json`                                      | Generated                                                                                                                  |
| 8. Scan             | `grype` or `trivy` on SBOM/image                               | No critical/high CVEs                                                                                                      |
| 9. Sign             | `cosign sign` (optional but recommended)                       | Signature verified                                                                                                         |
| 10. Push            | `docker push` to `ghcr.io/<org>/astradesk-<svc>:<git-sha>`     | Success                                                                                                                    |
| 11. Deploy          | `helm upgrade --install astradesk deploy/chart -f values.yaml` | Health checks pass                                                                                                         |
| 12. Online Eval     | Canary probes with in-loop judge gates                         | Latency p95 ≤ 8s, success ≥ 95%                                                                                            |

Coverage policy:

- Coverage evidence is mandatory for CI and SonarCloud.
- A missing or misplaced coverage report is a pipeline failure.
- `0.0% Coverage on New Code` is acceptable only when the pull request truly contains no coverable code.
- The long-term production hardening target is ≥ 90%, but current baseline gaps must be closed through explicit ratchet issues rather than hidden or false gates.

## Branching Model

AstraDesk uses a strict two-tier integration model.

- `main` — release / production-stable branch. It advances only from `develop` at a milestone or release boundary after required gates pass.
- `develop` — integration branch for the active milestone.
- `issue/<number>-<slug>` — work branch for tracked roadmap or GitHub issue work, for example `issue/016-rbac-invariant`.
- `fix/<slug>` — work branch for CI, build, documentation, or defect fixes that are not tied to a numbered issue, for example `fix/ci-coverage-path`.
- `fix/<number>-<slug>` — work branch for fixes tied to a numbered issue, for example `fix/051-coverage-path`.

### Flow

1. Start from `develop`.

   ```bash
   git switch develop
   git pull --ff-only origin develop
   git switch -c issue/<number>-<slug>
   ```

   or, for non-numbered fixes:

   ```bash
   git switch develop
   git pull --ff-only origin develop
   git switch -c fix/<slug>
   ```

2. Open a pull request with **base = `develop`**.

3. Required CI gates must pass before merge.

4. Merge to `develop` after review and green CI, then delete the work branch.

5. At a milestone or release boundary, promote `develop` to `main` after required gates pass, then tag the release.

### Rules — non-negotiable

- No `issue/*` or `fix/*` branch may open a pull request directly against `main`.
- `main` advances only via `develop`.
- `develop` may be ahead of `main` during active milestone work. This is expected.
- Do not re-sync `develop` into `main` after every PR.
- Promote `develop` to `main` only at milestone or release boundary.
- Emergency hotfixes still flow `fix/* → develop → main`, unless a documented release-manager exception is explicitly recorded on the pull request.
- Agents must not commit, push, merge, delete branches, or retarget pull requests unless the maintainer explicitly instructs them to do so.

## GitHub Repository Policy (required configuration)

1. **Default branch = `develop`** — new PRs target `develop` by default.
2. **Protect `main`** — no direct pushes; changes arrive only via PR.
3. **Restrict PRs into `main`** to source branch `develop`.
4. **Required status checks (CI)** must pass before merging into **both** `develop` and `main`.
5. **Emergency hotfixes** flow `fix/* → develop → main`; any deviation requires a
   documented release-manager exception recorded on the PR.

## Agent Execution Rules

AI agents working on AstraDesk must follow these rules.

### Required starting report

Before editing files, the agent must report:

- current branch
- expected base branch
- intended work branch
- intended changed files
- whether the task touches production, security, CI, API contract, migrations, policy, or observability surfaces

### Branch discipline

- Agents must assume `develop` is the base branch for all implementation work.
- Agents must not create pull requests from `issue/*` or `fix/*` branches to `main`.
- Agents must not retarget pull requests from `develop` to `main`.
- Agents must not merge `develop` into `main`.
- Agents must not delete local or remote branches unless explicitly instructed by the maintainer.

### Scope discipline

Agents must not expand task scope without explicit maintainer approval.

Examples:

- A CI coverage fix must not change OIDC, RBAC, runtime policy, or API behavior.
- An RBAC issue must not change OIDC token verification unless the issue explicitly says so.
- A documentation/process branch must not change production code.
- A security control branch must include negative tests for denial paths.

### Required handoff

At the end of each task, the agent must report:

- current branch
- files changed
- exact commands executed
- exact test/lint/typecheck results
- whether any required gate was skipped
- known unrelated baseline failures
- whether commit, push, or merge was performed

If commit, push, or merge was not explicitly requested, the agent must leave changes unstaged or staged only as instructed by the maintainer.

## Artifact Standards

- Images: `astradesk-<component>:<first-8-chars-of-sha>`
- Helm chart: `deploy/chart/` with environment-specific `values-<env>.yaml`
- SBOM: `sbom.spdx.json` attached to GitHub/GitLab release artifacts
- Audit logs: published to NATS `astradesk.audit`, sunk to S3 + Elasticsearch

## Quality Gates — Non-Negotiable

1. **Security**
   - No hardcoded secrets.
   - No reachable unaccepted Critical/High vulnerability in runtime images.
   - OIDC/JWKS enforced at active ingress outside explicit local mode.
   - OPA unavailable or ambiguous decision means deny.

2. **Contract**
   - Admin API OpenAPI contract version `1.2.0` must remain synchronized.
   - Runtime schema and canonical OpenAPI must pass structural diff.
   - Generated clients must be regenerated when the contract changes.

3. **RBAC**
   - Every tool declares `side_effect`.
   - Every `write` or `execute` tool declares `allowed_roles`.
   - Every `write` or `execute` tool has role-rejection coverage.
   - Unauthorized calls are denied on both LLM-planned and keyword-fallback paths.

4. **PII / Egress**
   - Raw PII, secrets, tokens, credentials, and sensitive payloads must not appear in logs, traces, model payloads, tool payloads, audit previews, or RAG traces.
   - Representative leak corpus must pass.

5. **Audit**
   - Side-effect execution requires audit emission.
   - Accepted audit events must be durably recoverable.
   - Crash and sink-outage recovery tests are required for audit changes.

6. **Observability**
   - New services expose `/metrics` and a health/readiness endpoint.
   - Logs include `trace_id` and `request_id`.
   - Spans must not contain raw PII/secrets.

7. **Docs**
   - `README.md` and `docs/en/` must be updated when public behavior changes.
   - Design-only artifacts must be marked `DESIGN EXAMPLE — NOT IMPLEMENTED`.

## Rollback Criteria

- p95 latency > 8s for 5 minutes
- Tool success rate < 95% for 10 minutes
- Error rate > 1% for 5 minutes
- Any critical security finding in deployed image

## Environment Matrix

| Env   | Namespace     | Replicas | Notes                        |
| :---- | :------------ | :------- | :--------------------------- |
| dev   | `astra-dev`   | 1-2      | Full stack, mockable         |
| stage | `astra-stage` | 2        | Production-like data         |
| prod  | `astra-prod`  | 2+       | mTLS STRICT, HPA, audit WORM |

## Related Files

- `Makefile` — local shortcuts for `test`, `build`, `migrate`, `ingest`
- `.github/workflows/ci.yml` — GitHub Actions runner
- `.gitlab-ci.yml` — GitLab CI runner
- `instructions.jenkins.md` — Jenkins pipeline notes
