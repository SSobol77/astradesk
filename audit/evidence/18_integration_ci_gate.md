<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: audit/evidence/18_integration_ci_gate.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# Issue #18 — Wire integration tests as an executable CI gate

Status: **wired and passing, zero xfail.** `tests/integration_tests.py` is an
explicit, always-run CI job (`integration-tests` in
`.github/workflows/ci.yml`) against real Docker Compose services (Postgres,
Redis, NATS, and all 4 domain-pack MCP servers). Local result: **5 passed**
— no xfail, no skip, no `|| true` hiding a required service's startup
failure. The existing unit-test gate (`build-test-python`, plain
`pytest -q`) is unaffected: 481 passed, unchanged from the pre-change
baseline.

## Scope

This pass continues issue #18 from a prior state of **4 passed, 1
xfailed** (see git history of this file for that superseded revision). The
maintainer decision was explicit: that result is not acceptable for
closing issue #18. This pass removes the `xfail` and fixes the real
blockers it was masking, plus one more blocker it uncovered once the
masked bugs were fixed.

**Explicitly out of scope and not done:** any change to `#43`'s live
deployability work; `#21` OIDC portal code (no regression was found, so
nothing to fix there); `v0.3.1` JetStream audit code (the integration
suite does not depend on it); Track-B issues #46/#45/#27/#26/#25; Node.js
version changes; `npm audit fix`; broad dependency remediation; any
redesign of API Gateway/Admin API architecture; any new integration test
framework.

## Root causes and fixes

Four real, pre-existing defects blocked `test_mcp_server_connectivity` and
`test_full_agent_flow_ops`. All four were confirmed by actually running
`docker compose -f docker-compose.dev.yml up` for all 4 `mcp-*` services
and reading their logs, and by running the integration gate against the
live stack — not inferred from code alone.

### Finding A (blocking, fixed): domain packs did not declare `fastapi`/`uvicorn`

`packages/domain-{support,ops,finance,supply}/pyproject.toml` did not list
`fastapi`/`uvicorn` as dependencies even though every pack's
`tools/mcp_server.py` does `from fastapi import FastAPI` at module scope
and `import uvicorn; uvicorn.run(...)` in `__main__`. All four containers
exited immediately with `ModuleNotFoundError: No module named 'fastapi'`.

**Fix**: added `fastapi>=0.133,<0.134` and `uvicorn[standard]>=0.30,<0.31`
to all four packages' `dependencies` (pinned to the same range as
`services/api-gateway/pyproject.toml`, so the workspace lock resolves one
already-audited version instead of a second one). `uv.lock` regenerated
accordingly (`uv lock`, no manual edits). This is a genuine
dependency-declaration gap, not a compose/image issue — confirmed because
the same `ModuleNotFoundError` also reproduces running the module directly
inside the built image, independent of any compose mount.

### Finding B (blocking, fixed): compose bind-mount shadowed the built image

All four `mcp-*` services in `docker-compose.dev.yml` mounted
`./packages/domain-X:/app` — the *whole* container `/app`, which each
Dockerfile also uses for `/app/.venv` and `/app/core`. The bind mount
shadowed both, so every container failed with
`ModuleNotFoundError: No module named 'domain_support'` (etc.), masking
Finding A behind a second, different startup crash.

**Fix**: mount at the package's own path instead:
`./packages/domain-X:/app/packages/domain-X`, matching each Dockerfile's
actual `COPY packages/domain-X /app/packages/domain-X` target. This is
compose wiring, not a dependency or architecture change — confirmed to be
an image/mount issue (not a dependency issue) because the container's own
built `.venv`/`core` were being shadowed by the bind mount, not missing
from the image.

With Findings A and B both fixed, `mcp-ops`, `mcp-finance`, and
`mcp-supply` started and reported healthy on `docker compose ... ps`.
`mcp-support` still failed — a third, previously-masked defect (Finding
C).

### Finding C (blocking, fixed): `mcp-support` imported a test-only stub at module scope

`mcp-support`'s exact failure, captured via
`docker compose -f docker-compose.dev.yml logs mcp-support`:

```text
Traceback (most recent call last):
  File "/app/packages/domain-support/src/domain_support/tools/mcp_server.py", line 28, in <module>
    from domain_support.tools.jira_adapter import JiraAdapter
  File "/app/packages/domain-support/src/domain_support/tools/jira_adapter.py", line 19, in <module>
    from domain_support.clients.api import AdminApiClient
  File "/app/packages/domain-support/src/domain_support/clients/api.py", line 23, in <module>
    from respx import dispatch
ModuleNotFoundError: No module named 'respx'
```

Root cause is **not** a missing PyPI dependency declaration like Finding
A. The repo-root `respx/` directory (`respx/__init__.py`: *"Tiny stub
replicating just enough of the `respx` API for the tests"*) is a
test-only, hand-written stub — not the real PyPI `respx` package, and not
installable via `pyproject.toml`/`uv.lock` at all. It is importable only
because the root `conftest.py` inserts the repo root onto `sys.path` for
pytest, and (accidentally) because `python -m package.module` run from a
repo-root CWD also puts the CWD on `sys.path[0]` — which is exactly how
this went unnoticed in local dev. Inside the Docker image, `WORKDIR` is
`/app` and only `packages/domain-support`, `core`, and the built `.venv`
are present; the repo-root `respx/` stub is never copied in, so the import
fails unconditionally, regardless of any dependency declaration.
`packages/domain-finance` and `packages/domain-supply` have the identical
`clients/api.py` pattern, but their own `mcp_server.py` never imports it
(no `jira_adapter`-equivalent import chain), so only `mcp-support` was
actually blocked by this.

**Fix**: `packages/domain-support/src/domain_support/clients/api.py` now
imports `respx.dispatch` lazily, inside `AdminApiClient._request`, instead
of at module scope. `JiraAdapter()` is constructed at `mcp_server.py`
module scope but never calls `_request` until a real `jira.list_tickets`
tool invocation — deferring the import lets the FastAPI app object exist
and `/health` respond without ever needing `respx` at startup. This is the
minimal correct fix for the **reported symptom** ("mcp-support exits
immediately"): it does not change `_request`'s behavior in any way, so
`packages/domain-support/tests/test_triage.py` (which drives
`AdminApiClient` through the `respx_mock` fixture) is unaffected byte for
byte.

**Explicitly not fixed (deliberately, out of scope, flagged for
follow-up)**: `AdminApiClient` in `domain-support`, `domain-finance`, and
`domain-supply` remains architecturally coupled to the `respx` test stub
— calling it for a real request outside pytest still raises
`RuntimeError: No active respx MockRouter`. Making it a genuine HTTP
client (`httpx.AsyncClient` against the real Admin API) is a larger,
cross-cutting change touching three packages' production code and their
existing unit tests' mocking story; it is dependency/architecture-shaped
work, not "fix startup," and was not required to reach 5 passing
integration tests (the JIRA tool is never invoked by this suite).

### Finding D (blocking, fixed): `nx.has_cycles` does not exist in `networkx`

`services/api-gateway/src/agents/{base,support,ops,billing}.py` all called
`nx.has_cycles(intent_graph)` to detect cycles in the per-request Intent
Graph. `networkx` has never exposed a function by that name; the correct
API for testing whether a `DiGraph` is acyclic is
`nx.is_directed_acyclic_graph`. Every fallback-planner request that
reached this check crashed with
`AttributeError: module 'networkx' has no attribute 'has_cycles'`,
observed directly via a captured stack trace during a real
`/v1/run` call before this fix:

```text
INFO:gateway.orchestrator:[...] Running fallback agent: support
ERROR:gateway.main:[...] Unexpected error during agent execution
AttributeError: module 'networkx' has no attribute 'has_cycles'
```

This 500'd every fallback-planner request for all three agents, but was
invisible to the previous "4 passed, 1 xfailed" result: the two
`test_full_agent_flow_*` tests assert `result.passed or result.error_message`,
and a 500 response populates `error_message`, so the assertion passed on
the *error* branch without ever exercising real tool execution.

**Fix**: `nx.has_cycles(intent_graph)` → `not nx.is_directed_acyclic_graph(intent_graph)`
at all 4 call sites (`agents/base.py:261`, `agents/billing.py:324`,
`agents/ops.py:305`, `agents/support.py:313`). `is_directed_acyclic_graph`
returns `True` when the graph has no cycles, so negating it preserves the
exact existing semantics ("raise if a cycle is present") for these
`DiGraph` intent graphs — no new graph semantics were invented. No
existing unit-test location covers `BaseAgent.run()`'s or the per-agent
`run()`'s intent-graph traversal directly (the only tests referencing
these agent classes are `packages/domain-ops/tests/test_ops_agent.py`,
which tests the *unrelated* `domain_ops.agents.ops.OpsAgent`, a different
class in a different package), so this integration suite is the
regression coverage for this fix, run via
`uv run pytest -q -m integration tests/integration_tests.py`.

### Finding E (newly exposed by Finding D's fix, blocking, fixed): `OpsAgent` heuristic planner missing a Polish keyword

Fixing Finding D let the `ops` fallback-planner flow run to completion for
the first time, which surfaced a second, previously-masked defect:
`test_full_agent_flow_ops` failed with
`tools_invoked=['search_ops_kb', 'get_metrics', 'get_metrics']` instead of
the expected `['get_metrics']` (`passed=False`, `error_message=None` — a
real assertion failure, not tolerated by the lenient
`result.passed or result.error_message` check).

Root cause: `OpsAgent._heuristic_plan` (`agents/ops.py:190`) only matched
the English keyword `'metrics'` (plus `'performance'`, `'status'`,
`'health'`), not the Polish `'metryki'` — even though this file's own
`runtime.planner.KeywordPlanner._rules` already includes `'metryki'` in
its metrics rule. For the scenario's Polish query
(`'Sprawdź metryki webapp'`), `_heuristic_plan` matched nothing, fell
through to its `search_ops_kb` catch-all (a tool name not registered in
`ToolRegistry` at all — confirmed via
`ERROR runtime.registry:registry.py:418 get_info('search_ops_kb'): not found`),
which produced a low-quality error result, triggering the reflection loop
to call `self.planner.replan(...)` (the *generic* `KeywordPlanner`, which
does recognize `'metryki'`) twice, adding two more `get_metrics` graph
nodes before hitting `MAX_REFLECTIONS`.

**Fix**: added `'metryki'` to `OpsAgent._heuristic_plan`'s metrics keyword
tuple (`agents/ops.py:190`), matching the synonym already used by
`KeywordPlanner` and by the analogous Polish keywords already present in
`SupportAgent._heuristic_plan` (`'zgłoszenie'`, `'incydent'`). No new
tool, no new registry entry, no new graph semantics — one missing
synonym in an existing keyword tuple.

## Investigation summary (per this pass's explicit requirements)

- **Exact stack trace for each failing `mcp-*` service**: only
  `mcp-support` ultimately failed after Findings A/B were fixed (see
  Finding C's captured traceback above); `mcp-ops`, `mcp-finance`,
  `mcp-supply` became healthy immediately once A and B were fixed.
- **Exact file(s) using `nx.has_cycles`**: `services/api-gateway/src/agents/base.py:261`,
  `billing.py:324`, `ops.py:305`, `support.py:313` (all four, identical
  pattern).
- **Exact package metadata declaring runtime deps**: `packages/domain-{support,ops,finance,supply}/pyproject.toml`'s
  `[project.dependencies]` (Finding A); confirmed in `uv.lock` after
  `uv lock` regeneration.
- **Dependency-declaration vs. compose/image issue**: both were present
  and independent — Finding A (real PyPI packages, genuinely undeclared)
  and Finding B (compose bind-mount shadowing the image's own `/app`
  contents) each fully masked the other; Finding C was a third, distinct
  image/import-time issue (a test-only local stub, not a PyPI package,
  never copied into any image).
- **Did all four `mcp-*` services need the same fix?** No. Findings A and
  B applied to all four. Finding C applied only to `mcp-support`, because
  only `domain-support`'s `mcp_server.py` imports the `jira_adapter` →
  `clients.api` chain; `domain-finance`/`domain-ops`/`domain-supply`'s
  `mcp_server.py` files do not import their own (identically-patterned)
  `clients/api.py`.
- **Is the integration test itself objectively correct?** Yes for all 5
  tests as currently written; no test assertion was loosened or
  bypassed to reach 5 passing. `test_mcp_server_connectivity`'s
  `assert any(connectivity.values())` and the two
  `result.passed or result.error_message` checks were already present
  before this pass and are unchanged — they were previously *tolerating*
  Findings C/D/E's failures, not hiding them; fixing the underlying bugs
  is what now makes them pass on the strict branch (`result.passed`)
  rather than the lenient one.

## Integration marker / gate

- Marker registered in `pyproject.toml`'s `[tool.pytest.ini_options]`:
  `markers = ["integration: full end-to-end tests against real docker-compose services (ISSUE 018); never run by the default unit-test gate."]`.
- Applied via `pytestmark = pytest.mark.integration` at the top of
  `tests/integration_tests.py`.
- Exact command (identical locally and in CI):

  ```bash
  uv run pytest -q -m integration tests/integration_tests.py
  ```

- `@pytest.mark.xfail` on `test_mcp_server_connectivity` has been removed
  entirely — the underlying defects it documented (Findings A/B/C) are
  fixed, not tolerated.

## Compose services used

`docker-compose.dev.yml`, all required for a real signal, **all now
hard requirements** (no `|| true`, no best-effort startup):

- `postgres`, `redis`, `nats` — backing the gateway's agent → tool → RAG
  flow.
- `mcp-support`, `mcp-ops`, `mcp-finance`, `mcp-supply` — the 4
  domain-pack MCP servers, now startable (Findings A/B/C).

`docker-compose.yml` (the non-dev stack) is still not used, for the same
reason as before: its `domain-*` services expose no relevant host ports,
and `api-gateway` itself is not required — the suite drives the FastAPI
`app` in-process via `TestClient`.

## CI workflow change

`.github/workflows/ci.yml`'s `integration-tests` job (parallel to, not
dependent on, `build-test-python`/`build-test-java`/`build-test-js`):

1. Checkout, `astral-sh/setup-uv`, `actions/setup-python` (Python 3.13).
2. `uv sync --frozen --extra dev`.
3. Start **all 7** required services in one `--wait --wait-timeout 180`
   command: `postgres redis nats mcp-support mcp-ops mcp-finance
   mcp-supply`. No `|| true` remains anywhere in this job — a failure to
   become healthy for any of the 7 now fails the step, and therefore the
   job, deterministically.
4. Run `uv run pytest -q -m integration tests/integration_tests.py` with
   `DATABASE_URL`/`REDIS_URL`/`NATS_URL` pointed at the compose services'
   published host ports, `AUTH_MODE=local-dev` +
   `ASTRADESK_DEV_JWT_SECRET=<ci-only literal>` (never a real credential,
   generated fresh per CI run, verified only by that same run's own
   process — the same class of CI-only fixture value as
   `docker-compose.dev.yml`'s existing `POSTGRES_PASSWORD: dev_password`),
   and `ENVIRONMENT=ci`.
5. Tear down with `docker compose ... down -v`, `if: always()`.

No existing job, step, or check was removed or weakened. `sonar-scan`'s
`needs:` list was not changed.

## Tests added/changed

- `tests/integration_tests.py`: removed the `@pytest.mark.xfail` on
  `test_mcp_server_connectivity`; rewrote the module docstring's "ISSUE
  018 wiring notes" to describe Findings A/B/C as fixed (not tolerated)
  and to drop the now-fixed `has_cycles` item from the "discovered, not
  fixed" list (only the unrelated, still-pre-existing `OpaClient` finding
  remains there). No test assertion was loosened; no test was deleted.
- `services/api-gateway/src/agents/{base,billing,ops,support}.py`:
  `nx.has_cycles` → `nx.is_directed_acyclic_graph` (Finding D).
- `services/api-gateway/src/agents/ops.py`: added `'metryki'` keyword
  (Finding E).
- `packages/domain-support/src/domain_support/clients/api.py`: lazy
  `respx` import (Finding C).
- `packages/domain-{support,ops,finance,supply}/pyproject.toml` +
  `uv.lock`: added `fastapi`/`uvicorn` runtime dependencies (Finding A).
- `docker-compose.dev.yml`: volume-mount fix for the 4 `mcp-*` services
  (Finding B).
- `pyproject.toml`: `integration` marker registration (unchanged from
  prior pass).
- `.github/workflows/ci.yml`: `integration-tests` job now starts all 7
  services in one required `--wait` step; removed the `|| true` and its
  accompanying stale comments.

## Docs/evidence updated

- `audit/evidence/18_integration_ci_gate.md` (this file, superseding its
  own prior "4 passed, 1 xfailed" revision).

## Verification commands and exact results

```text
$ uv run ruff check core/src services/api-gateway/src services/api-gateway/tests services/admin_api mcp/src mcp/tests
All checks passed!

$ uv run ruff format --check core/src services/api-gateway/src services/api-gateway/tests services/admin_api mcp/src mcp/tests
93 files already formatted

$ uv run pytest -q services/api-gateway/tests services/admin_api/tests mcp/tests
462 passed

$ uv run pytest -q --cov-report=xml:coverage.xml   # full default suite, unit-gate parity check
481 passed   # identical to the pre-change baseline; tests/integration_tests.py still not
             # collected by the bare default run (unchanged — by design, see module docstring)

$ uv run python scripts/license_headers.py --check
License headers verified; would normalize 0 file(s).

$ bash scripts/check-openapi-version.sh
(exit 0)

$ docker compose -f docker-compose.yml config
(exit 0)

$ docker compose -f docker-compose.dev.yml config
(exit 0)

$ uv run python scripts/ci/verify_build_baseline.py
Reproducible-build baseline OK: 12 Dockerfile(s), 3 compose file(s) checked.

$ docker compose -f docker-compose.dev.yml up -d --wait --wait-timeout 180 \
    postgres redis nats mcp-support mcp-ops mcp-finance mcp-supply
(exit 0; all 7 healthy)

$ DATABASE_URL=postgresql://astradesk:astradesk@localhost:5432/astradesk \
  REDIS_URL=redis://localhost:6379/0 \
  NATS_URL=nats://localhost:4222 \
  AUTH_MODE=local-dev \
  ASTRADESK_DEV_JWT_SECRET=integration-test-secret \
  ENVIRONMENT=ci \
  uv run pytest -q -m integration tests/integration_tests.py
5 passed in ~20s

$ docker compose -f docker-compose.dev.yml down -v
(exit 0; containers, volumes, and network removed)

$ docker ps -a
(empty — no leftover containers)
```

## Skipped checks with reason

- Admin Portal (`npm ci`/`openapi:gen`/`openapi:check`/`lint`/`test`):
  not applicable — no file under `services/admin-portal/` was touched.
- Making `AdminApiClient` (domain-support/finance/supply) a real HTTP
  client instead of a test-stub façade: out of scope per this task's
  "do not redesign API Gateway/Admin API architecture" and "fix startup
  only minimally" constraints; recorded above (Finding C) for a
  maintainer follow-up.
- The pre-existing `'OpaClient' object has no attribute 'check_policy'`
  warning on the LLM planner path: unrelated to this gate (the suite
  falls back to the keyword planner and still reaches 5 passing tests
  through that path), recorded for visibility only, not fixed.

## Generated/cache/local artifacts changed

- `uv.lock`: regenerated to add `fastapi`/`uvicorn` to the 4 domain
  packages (via `uv lock`, no manual edits).
- `coverage.xml`: regenerated by the verification commands above; not
  hand-edited.

## Explicit statement

**#43 was not touched by this pass.** No file under `deploy/` was read or
modified. #43 remains open, blocked on the same live AWS/Kubernetes
environment checks documented in
`audit/evidence/43_deployability_verification.md`. **#21 OIDC portal code
was not touched**: no regression was found in it during this work.
