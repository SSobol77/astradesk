<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: docs/roadmap/issues/ISSUES_NEW-SEC_admin_proxy_auth.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# ISSUES_NEW-SEC — Admin API proxy defense-in-depth authentication/authorization (NEW)

- **Track / Milestone**: A / `v0.3.1`
- **Type**: NEW (deferred out of ISSUE 009 / ISSUE 028 as a dedicated security issue)
- **Workhorse principle**: Security (good-sense)
- **GA-gating**: yes — an unauthenticated path to `/secrets`, `/users`, `/policies`, etc. is a critical gap
- **Audit anchors**: ISSUE 009 OIDC/JWKS audit; `services/api-gateway/src/gateway/main.py` (`/api/admin/v1/{path:path}`); `services/admin_api/src/astradesk_admin/main.py`
- **Depends on**: ISSUE 009 (OIDC verifier/`Principal` contract reused, not redesigned)
- **Independent of**: RBAC choke point (016), durable audit (019), policy enforcement (028), NEW-04 redaction/egress — none of these were redesigned

## Origin

During the ISSUE 009 OIDC/JWKS ingress audit, the agent found that
`/api/admin/v1/{path}` in the API Gateway proxied to `services/admin_api`
**without a gateway auth check**, while the Admin API itself did not
independently guard its sensitive endpoints either. This was explicitly
deferred out of #009/#028 and tracked as this dedicated issue.

## Problem (current evidence, pre-fix)

`services/api-gateway/src/gateway/main.py::proxy_to_admin_service` forwarded
every request under `/api/admin/v1/{path}` to the Admin API with no
`Depends(...)` auth gate at all. `services/admin_api/src/astradesk_admin/main.py`
had no auth dependency of its own — every route (`/secrets`, `/users`,
`/roles`, `/policies`, `/audit`, …) was reachable by any caller who could
reach the Admin API's port, relying entirely on network placement/Compose
isolation for protection.

## Industry analog & childhood disease

A common failure mode in agent/admin-panel architectures: the "internal"
admin backend is left unauthenticated because it's assumed to be reachable
only through a trusted proxy or private network. The disease is **trusting
network topology as an authentication mechanism** — once that topology
assumption breaks (a misconfigured route, a compromised pod, a debug port left
open), there is no second gate. We immunize with defense-in-depth: two
independent authentication/authorization checks, neither of which trusts the
other's decision or the network path between them.

## Architecture decision

Option C — defense-in-depth. Both layers independently authenticate and
authorize; neither relies solely on network placement, Compose isolation,
ingress, internal headers, or the other layer's decision.

## Target contract (invariants)

- **INV-ADMIN-AUTH-1/5/6**: `/api/admin/v1/{path}` at the API Gateway requires
  an authenticated principal with role `admin`; missing/invalid
  `Authorization` → `401`, authenticated non-admin → `403`, both before any
  upstream connection.
- **INV-ADMIN-AUTH-2**: The Gateway's authorization check is the `admin` role,
  reusing the existing ISSUE 016 `normalize_roles` case-fold convention.
- **INV-ADMIN-AUTH-3/4/7/8**: The Admin API independently requires the same —
  a verified Bearer JWT and the `admin` role — regardless of the Gateway's
  decision.
- **INV-ADMIN-AUTH-9/11**: The Gateway strips caller-supplied `X-AstraDesk-*`
  identity headers before proxying; they are never a valid authentication
  mechanism at either layer.
- **INV-ADMIN-AUTH-10**: The Gateway forwards `Authorization` unchanged to the
  Admin API only because the Admin API independently re-verifies the same
  Bearer JWT.
- **INV-ADMIN-AUTH-12**: No raw JWT, `Authorization` header, secret, or full
  raw claim set is logged or echoed in an error response at either layer.
- **INV-ADMIN-AUTH-13**: `GET /health` (Admin API) and `GET /healthz` (Gateway)
  remain public — liveness/dashboard status only, no sensitive state.
- **INV-ADMIN-AUTH-14**: Tests require no real external IdP, network,
  Kubernetes, or cloud dependency.
- **INV-FAIL-CLOSED**: Missing/invalid OIDC configuration aborts Admin API
  startup (`AuthConfigError`), mirroring the Gateway's ISSUE 009 contract.

## Interface / design

- **Gateway**: `services/api-gateway/src/gateway/auth_dependency.py` gains
  `require_admin_role` (`Depends(require_authenticated)` + `admin` role
  check). `gateway/main.py`'s `proxy_to_admin_service` depends on it, strips
  `X-AstraDesk-*` headers via `_strip_spoofable_headers`, and forwards
  `Authorization` unchanged. Incidentally fixed a pre-existing bug where the
  proxy returned a base `Response` around an async-generator body
  (`aiter_bytes()`), which Starlette cannot render — every successful proxy
  call would 500 regardless of auth; changed to `StreamingResponse`.
- **Admin API**: new `services/admin_api/src/astradesk_admin/auth.py`
  independently verifies the Bearer JWT via the shared
  `astradesk_core.utils.oidc.build_verifier_from_env()`/`Principal` contract,
  with a locally-duplicated (not imported) role-normalization helper to
  respect the API Gateway/Admin API service boundary. A new `lifespan`
  installs the verifier at startup (fail-closed). All routes except
  `GET /health` and FastAPI's auto `/docs`/`/redoc`/`/openapi.json` are
  registered on `admin_router = APIRouter(dependencies=[Depends(require_admin)])`.
- **OpenAPI**: `openapi/astradesk-admin.v1.yaml` already declared a
  `BearerAuth` (`http`/`bearer`/`JWT`) security scheme and applied it to some
  operations; this change added `security: [BearerAuth]` to the 19 operations
  that lacked it (`/jobs*`, `/dlq`, `/users*`, `/roles`, `/policies*`,
  `/audit`, `/settings/{group}*`), so every protected operation now declares
  the requirement in the contract, not only in code. Contract version
  unchanged at `1.2.0`.
- **Dependency wiring**: `services/admin_api/pyproject.toml` now depends on
  `astradesk-core` (previously only used indirectly); root `pyproject.toml`
  now lists `astradesk-admin-api` as a dependency (it was a workspace member
  but not consumed by anything, so `uv sync` never installed it) and adds
  `services/admin_api/tests` to `[tool.pytest.ini_options] testpaths`.

## Failure modes & required behavior

| Failure | Required behavior |
| :--- | :--- |
| Missing `Authorization` at Gateway | `401`, upstream never called |
| Malformed/invalid token at Gateway | `401`, upstream never called |
| Authenticated non-admin at Gateway | `403`, upstream never called |
| Authenticated `admin` at Gateway | Proxied; `X-AstraDesk-*` stripped, `Authorization` forwarded |
| Missing/invalid token at Admin API | `401` |
| Authenticated non-admin at Admin API | `403` |
| Missing OIDC config on a deployed tier (Admin API startup) | `AuthConfigError`, process does not start |
| `X-AstraDesk-*` headers present, no Bearer JWT | `401` — headers are not trusted as identity |

## Acceptance criteria (Definition of Done)

- [x] Gateway: `/api/admin/v1/{path}` requires authenticated `admin`; 401/403
  enforced before any upstream call
  (`services/api-gateway/tests/runtime/test_admin_proxy_auth.py`).
- [x] Gateway: caller-supplied `X-AstraDesk-*` headers stripped before
  proxying (`test_admin_proxy_auth.py::test_strips_caller_supplied_internal_identity_headers`).
- [x] Gateway: `Authorization` forwarded unchanged only on allowed admin
  requests, never on denied ones
  (`test_admin_proxy_auth.py::test_forwards_authorization_unchanged_on_allowed_admin_request`,
  `test_denied_requests_never_forward_authorization_to_upstream`).
- [x] Gateway: no raw token leak in response body/headers
  (`test_admin_proxy_auth.py::test_401_and_403_responses_never_echo_raw_token`).
- [x] Admin API: every sensitive operation independently requires Bearer JWT +
  `admin`; `/health` stays public
  (`services/admin_api/tests/test_admin_auth.py`, including a blanket sweep
  over every `admin_router` route).
- [x] Admin API: `X-AstraDesk-*` headers never trusted as identity
  (`test_admin_auth.py::test_does_not_trust_spoofed_identity_headers`).
- [x] Admin API: fail-closed startup without OIDC config
  (`test_admin_auth.py::test_install_verifier_is_fail_closed_without_oidc_config`).
- [x] OpenAPI: `BearerAuth` security scheme applied to all protected
  operations (verified by a script sweep of `paths:`; 74 operations, 0
  missing after the change).
- [x] Existing ISSUE 009 (OIDC), 016 (RBAC), 019 (audit), 028 (policy) suites
  re-run and pass unchanged (152 tests) — none were redesigned.
- [ ] Admin Portal OpenAPI generation/sync (`npm run openapi:gen`,
  `npm run openapi:check`, `npm run lint`, `npm run test`). *(Not run — Node.js
  was unavailable in the implementing environment. The spec change is
  additive-only (`security:` blocks only); neither generator currently emits
  per-operation security metadata into `types.gen.ts`/`spec-operations.gen.ts`,
  so content drift is unlikely, but `npm run openapi:check`'s mtime-based
  staleness check **will** fail until a maintainer with Node.js regenerates.
  This remains an open, maintainer-side action item.)*
- [ ] Service-to-service mTLS / Istio `AuthorizationPolicy` between Gateway and
  Admin API. *(Not implemented here — tracked as future network-layer
  hardening; see `docs/en/08_security_governance.md` §8.13. This issue
  delivers the application-layer guard, not a replacement for it.)*
- [ ] Signed internal service-identity tokens as an alternative to the
  (now-stripped) `X-AstraDesk-*` headers. *(Not implemented; not required for
  the current invariant set.)*

## Verification evidence (artifact)

```bash
uv run ruff check core/src services/api-gateway/src services/api-gateway/tests services/admin_api mcp/src mcp/tests
uv run ruff format --check core/src services/api-gateway/src services/api-gateway/tests services/admin_api mcp/src mcp/tests
uv run pytest -q services/api-gateway/tests services/admin_api/tests mcp/tests   # 448 passed
uv run pytest -q                                                                  # 467 passed (repo-wide)
uv run python scripts/license_headers.py --check
bash scripts/check-openapi-version.sh
```

All passed. `mypy` on the four changed/new auth files (`gateway/auth_dependency.py`,
`gateway/main.py`, `astradesk_admin/auth.py`, `astradesk_admin/main.py`)
reported zero new errors — only the pre-existing, documented
`opentelemetry.trace` baseline noise in unrelated transitively-imported
modules.

## Admin Portal / Node.js toolchain caveat

Node.js was not available in the implementing environment, so
`npm ci`, `npm run openapi:gen`, `npm run openapi:check`, `npm run lint`, and
`npm run test` under `services/admin-portal` were **not run**. No generated
TypeScript client files were hand-edited or regenerated. This is recorded as
an explicit open item, not claimed as done — see `docs/workflows/openapi-contract.md`
for the exact commands a maintainer must run before merge.

## Out of scope

NEW-02 (reproducible containers), NEW-01 (vulnerability triage), Admin Portal
rewrite, OIDC/JWKS redesign (009), RBAC redesign (016), NEW-04
redaction/egress redesign, durable audit redesign (019), policy enforcement
redesign (028), service-to-service mTLS/Istio `AuthorizationPolicy`, signed
internal service-identity tokens, OPA-based policy evaluation for Admin API
operations (beyond the existing Gateway-side OPA tool-policy gate).
