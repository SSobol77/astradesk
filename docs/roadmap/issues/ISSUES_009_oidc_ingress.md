<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: docs/roadmap/issues/ISSUES_009_oidc_ingress.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# ISSUES_009 — Wire JWKS/OIDC at active ingress (RESCOPE of #9)

- **Track / Milestone**: A / `v0.3.1`
- **Type**: RESCOPE of closed #9 (retain historical closure; residual control moved here)
- **Workhorse principle**: Security (good-sense)
- **GA-gating**: yes — identity must be trustworthy before authority (016)
- **Audit anchors**: §7 (Critical); `services/api-gateway/src/gateway/main.py:69-105`; `core/src/astradesk_core/utils/auth.py:125-240`
- **Depends on**: Phase 0 (main green)
- **Blocks**: ISSUE 016, NEW-04, 019

## Problem (current evidence)
The active Gateway authenticates with an HS256 development-secret fallback. A tested JWKS/OIDC verifier already exists in `astradesk_core.utils.auth` but is **not** wired into the live ingress. Documentation claims OIDC; the running code does not use it.

## Industry analog & childhood disease
DIY OIDC/JWT integrations routinely ship a symmetric dev secret that survives into production, skip issuer/audience/expiry validation, and have no key-rotation story. The result is forgeable tokens and silent trust of the wrong issuer. We immunize by making asymmetric JWKS the only production path and refusing to start without it.

## Target contract (invariants)
- **INV-OIDC-1**: Production startup MUST abort if OIDC issuer/JWKS/audience config is absent or unreachable (INV-FAIL-CLOSED).
- **INV-OIDC-2**: Every request token is validated for signature (JWKS), `iss`, `aud`, `exp`, `nbf`, and required scope/claim set before any handler runs.
- **INV-OIDC-3**: The HS256 symmetric path is reachable only behind `ASTRADESK_AUTH_MODE=local-dev` (named, non-default); production refuses that value (INV-LOCAL-MODE-EXPLICIT).
- **INV-OIDC-4**: JWKS keys are cached with TTL and re-fetched on `kid` miss; rotation does not require a restart.

## Interface / design
- Single auth dependency injected at the Gateway ingress boundary; remove inline secret handling from `gateway/main.py`.
- Config surface: `OIDC_ISSUER`, `OIDC_AUDIENCE`, `OIDC_JWKS_URL` (or discovery), `AUTH_MODE`.
- Verifier reused from `astradesk_core.utils.auth` (no second implementation).

## Failure modes & required behavior
| Failure | Required behavior |
| :--- | :--- |
| Missing prod OIDC config | Startup aborts with explicit error; no fallback to HS256 |
| JWKS endpoint unreachable at request time | 503 with cached keys if valid; deny if no usable key |
| Expired / wrong `aud` / wrong `iss` token | 401, audited, no handler execution |
| Unknown `kid` | One JWKS refresh, then deny if still unknown |
| `AUTH_MODE=local-dev` set in production image | Startup refuses |

## Acceptance criteria (Definition of Done)
- [ ] Live ingress validates via JWKS; HS256 removed from default path.
- [ ] Negative tests: bad signature, wrong `iss`, wrong `aud`, expired, `nbf` in future, unknown `kid` → all denied and audited.
- [ ] Startup-abort test for missing prod config.
- [ ] Rotation test: new signing key honored without restart.
- [ ] `local-dev` refused by a production-profiled startup.

## Verification evidence (artifact)
`audit/evidence/` (next run): auth negative-matrix test output + startup-abort test log.

## Out of scope
Portal front-channel OIDC (#21), token exchange for downstream services (Track B).
