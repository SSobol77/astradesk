<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: audit/evidence/40_dependency_triage.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# Issue #40 (NEW-01) — dependency & supply-chain triage

Status: **gate green for all three images — do not close #40 until the PR
merges and CI confirms it.** `astradesk:ci-python`, `astradesk:ci-java`, and
`astradesk:ci-js` each individually pass the fail-closed Trivy gate, and the
combined three-image invocation
(`scripts/ci/supply_chain_scan.sh astradesk:ci-python astradesk:ci-java
astradesk:ci-js`) now **exits 0** (`final_scan_rc=0`). The Java image was the
last remaining blocker: it carried a previously-unscanned set of Spring
Boot/Netty/Jackson/Spring Security JAR findings plus a base-image-bundled Go
binary (`pebble`) finding set (see "Follow-up: Java image recheck — new
findings discovered, out of scope for this pass" below for how they were
found) — both are now fully remediated, with full detail and evidence in
"Follow-up: Java image remediation (Spring Boot/Netty/Jackson BOM bump +
`pebble` removal)" below. This document tracks a series of bounded passes:
the fail-closed scan gate and evidence capture, followed by narrow
Python-package remediation, a Starlette/FastAPI remediation, a
Transformers/RAG-ML remediation, a time-boxed accepted-risk disposition for
the remaining Debian OS base-image findings that have no upstream fix, an
Admin Portal/JS `next` remediation plus runtime-image npm/corepack/yarn
hardening, a Java image recheck that surfaced new findings, and finally (this
pass) the Java remediation itself. Issue #40 itself should only be closed by
the PR that merges this branch after CI passes, per the issue's own closure
contract — this document being green is necessary but not sufficient on its
own. A separate, genuinely pre-existing application defect (a duplicate
`TicketController` bean-name conflict, unrelated to any dependency version
and proven so — see that same Java remediation section) remains and is
**explicitly out of scope** for this pass; it does not affect the Trivy gate
and must not block merging this branch.

As of the "narrow package remediation" pass, the fail-closed scan gate
against `astradesk:ci-python-scoped` still **failed** — 11 Debian OS findings
(9 HIGH / 2 CRITICAL, no upstream fix available yet) and 7 Python-package
findings (7 HIGH / 0 CRITICAL, `starlette` (3) and `transformers` (4), both
blocked by resolver-affecting constraints), down from the pass before that's
11 + 20.

As of the follow-up "Starlette/FastAPI remediation" pass, the gate still
**failed** — 11 Debian OS findings (unchanged, no upstream fix available
yet) and 4 Python-package findings (4 HIGH / 0 CRITICAL, all `transformers`)
remained. `starlette` was fully remediated in that pass.

As of the follow-up "Transformers/RAG-ML remediation" pass (see "Follow-up:
Transformers/RAG-ML remediation" below), the gate still **fails** — 11
Debian OS findings (unchanged, out of scope for that pass; no upstream fix
available yet) remain, and **zero** Python-package findings remain.
`transformers` is fully remediated. The Debian OS findings are the *only*
remaining blocker to a fully green gate, and they are blocked on an upstream
fix that does not exist yet on any current Debian suite. Every remaining
finding is a precisely documented blocker, not an oversight.

As of this follow-up "Debian OS accepted-risk disposition" pass (see that
section below), those same 11 Debian OS findings — still with no upstream
fixed version — are now dispositioned as time-boxed accepted risk in
`.trivyignore` (`exp:2026-08-31`), per INV-SC-1(b)/INV-SC-4. **The gate now
passes: `scripts/ci/supply_chain_scan.sh astradesk:ci-python-scoped` exits 0.**
Zero Python-package HIGH/CRITICAL findings remain, and zero unaccepted
Debian OS findings remain — the only entries suppressed are the 11 findings
(8 unique advisory IDs) already documented above as having no available
fix, each individually justified and expiring 2026-08-31 to force
re-review at the next hardening window.

## What this pass captures

- `audit/evidence/19_pip_audit.txt` — raw `uv run pip-audit --format columns`
  output against the root workspace environment, captured on the date in that
  file's header. 97 known advisories across 19 packages at capture time.
- `audit/evidence/40_trivy_api_gateway_scoped.json` — raw
  `trivy image --format json` output against `astradesk:ci-python-scoped`
  (post-remediation state), giving exact per-finding `PkgPath`/`FixedVersion`
  data used throughout this file.
- This file — the reachability disposition for each flagged package.
- `scripts/ci/supply_chain_scan.sh` + `.trivyignore` — the fail-closed Trivy
  image-scan gate wired into `.github/workflows/ci.yml` for the three images
  CI already builds (`astradesk:ci-python`, `astradesk:ci-java`,
  `astradesk:ci-js`).
- A investigated-but-**not-applied** root-Dockerfile scoping change (see
  "Docker scoping: investigated, not applied" below) and a newly-discovered,
  pre-existing, out-of-scope startup defect it surfaced.

## Disposition table

Legend: **remediated** / **not-present-in-runtime-image** /
**accepted-with-expiry** (requires a `.trivyignore` entry with `exp:` date —
none recorded yet; see that file's header) / **pending** (reachable, real,
deferred to a follow-up bounded pass — not yet a contract-compliant
disposition under INV-SC-1).

| Package | Version | Advisories | Disposition | Why |
|---|---|---|---|---|
| pytest, black, pygments, pip (via pip-audit's own `pip-api`), plus `ecdsa`/`msgpack`/`python-jose` (confirmed via Trivy) | various | 1 each | **remediated** | Were only present because the root `Dockerfile` ran `uv sync --all-extras --frozen`, pulling in the entire workspace (dev/docs/test tooling and unrelated services' dependencies). Two blockers stood between this scoping change and being applied: (1) a pre-existing runtime startup defect (`ModuleNotFoundError: No module named 'agents'`, fixed via `ENV PYTHONPATH=/app/src`); (2) a missing direct dependency — `astradesk-api-gateway` imports `aioboto3` (Bedrock provider) without declaring it, fixed by adding `aioboto3>=15.4.0` to `services/api-gateway/pyproject.toml` and regenerating `uv.lock`. With both fixed, the root `Dockerfile` now runs `uv sync --frozen --no-dev --package astradesk-api-gateway`. Trivy-confirmed: Python-package HIGH/CRITICAL findings dropped from 24 (23H+1C) to 20 (20H+0C) — `black`, `ecdsa`, `msgpack`, and `python-jose` (CVE-2024-33663, the sole CRITICAL) are gone; `aioboto3`/`aiobotocore`/`boto3` introduced zero new findings. See "Follow-up: missing `aioboto3` dependency fixed; scoping change applied" below. |
| mkdocs, mkdocs-material, pymdown-extensions, mkdocstrings, pypdf, beautifulsoup4, markdown-it-py | various | (docs/ingestion extras) | **remediated** (confirmed via Trivy: absent from the scoped image) | Confirmed zero references in any Dockerfile `COPY`/entrypoint and zero use in any containerized script; `make db-seed` runs `scripts/seed_kb.py`/`scripts/ingest_docs.py` on the developer's local `uv` environment, never inside a built image. Eliminated from the shipped image now that the Dockerfile scoping change is applied (see the `aioboto3` follow-up section below). |
| `datamodel-code-generator` (pulls `black`) | — | 1 (via black) | **remediated** | Declared as a *base* (non-optional) root `pyproject.toml` dependency but has zero references anywhere in the tree (`git grep` for `datamodel_code_generator`/`datamodel-codegen` returns nothing). Not moved to `[dev]` extras — not needed: the now-applied Dockerfile scoping change (`uv sync --frozen --no-dev --package astradesk-api-gateway`) already excludes it from the shipped image, since the package-scoped sync never pulls the root meta-package's own dependencies regardless of where they're declared. |
| starlette (via `fastapi`) | 1.3.1 (was 0.46.2) | 3→0 (CVE-2025-62727 fixed 0.49.1; CVE-2026-48818 fixed 1.1.0; CVE-2026-54283 fixed 1.3.1) | **remediated** | Reachable — every FastAPI service in the root workspace. Root cause (identified in the prior pass): `services/api-gateway/pyproject.toml` pinned `fastapi>=0.115,<0.116`, and FastAPI 0.115.14 itself pins `starlette<0.47.0,>=0.40.0` (confirmed via PyPI metadata) — a hard resolver ceiling below even the first fix. Fixed this pass by raising the `fastapi` upper bound to `>=0.133,<0.134` — confirmed via PyPI metadata across every FastAPI 0.115–0.139 minor release (`0.116.0`→`<0.47.0`, `0.117.0`→`<0.49.0`, `0.121.0`→`<0.50.0`, `0.129.0`→`<1.0.0`, `0.133.0`→ no upper bound at all) that `0.133.0` is the *lowest* release whose own starlette constraint drops the upper bound entirely, satisfying "bump FastAPI only to the lowest version line that resolves Starlette to a patched version." `uv lock` alone kept starlette at 0.46.2 (it still satisfied the relaxed bound); `uv lock --upgrade-package starlette` was then run explicitly, resolving to `1.3.1` — the latest available, clearing all three CVEs. See "Follow-up: Starlette/FastAPI remediation" below for full verification evidence. |
| transformers | 5.3.0 (was 4.45.2) | 4→0 (CVE-2024-11392/11393/11394 fixed 4.48.0; CVE-2026-4372 fixed 5.3.0) | **remediated** | Reachable — direct RAG-embedding runtime dependency of `services/api-gateway`. `services/api-gateway/pyproject.toml` exact-pinned `"transformers==4.45.2"`, so `uv lock --upgrade-package transformers` was a confirmed no-op. Fixed in the dedicated "Transformers/RAG-ML remediation" pass (see that section below) by changing the pin to `"transformers>=5.3.0,<5.4.0"` — the exact minimum needed to clear the 4th advisory (the other three clear at 4.48.0, well below this). Required also bumping `sentence-transformers` (below) to satisfy the resulting resolver conflict. Full RAG test coverage (32 RAG/embedding/model_gateway-tagged tests, 448 total) passed unchanged; the actual `SentenceTransformer.encode(...)` call signature used in `services/api-gateway/src/runtime/rag.py` (`convert_to_tensor`, `device`, `batch_size`, `show_progress_bar` kwargs) is unchanged across the 3.x→5.x line. |
| torch | 2.9.0 (unchanged) | 0 (current Trivy DB) | **not-reachable-as-finding** | The earlier "4 advisories" count in this table predated this pass's Trivy JSON evidence and did not reproduce against a real scan; confirmed again in the "Transformers/RAG-ML remediation" pass: `torch` still has zero Trivy findings. Not bumped — confirmed unnecessary: `transformers==5.3.0`'s own optional `torch` extra requires only `torch>=2.4` (checked via PyPI metadata), well below the current exact pin `"torch==2.9.0"`, so the resolver never needed to touch it and it wasn't touched. |
| sentence-transformers | 5.2.3 (was 3.4.1) | 0 direct | **remediated** (as a required carrier for the `transformers` fix) | No CVE advisories of its own at any version checked; changed only because `services/api-gateway/pyproject.toml`'s prior `"sentence-transformers>=3.0,<4.0"` pin transitively capped `transformers` at `<5.0.0` (every sentence-transformers 3.x/4.x/early-5.x release up to 5.1.x declares `transformers<5.0.0,>=4.41.0`; PyPI metadata across the full 3.0.0–5.6.0 release history showed `5.2.0` is the *lowest* release that raises this to `transformers<6.0.0,>=4.41.0`). Changed the pin to `"sentence-transformers>=5.2.0,<5.3.0"` — the narrowest possible bump to the exact cutover minor line, resolving to the latest patch within it (`5.2.3`). This is a 2-major-line jump (3→4→5) in `sentence-transformers` itself, which is more than "narrow" in isolation, but it is a forced transitive consequence of the `transformers` CVE fix, not an independent choice — no smaller `sentence-transformers` bump satisfies the `transformers>=5.3.0` requirement. |
| pillow | 12.3.0 (was 12.0.0) | 3→0 (CVE-2026-25990 fixed 12.1.1; CVE-2026-40192/42311 fixed 12.2.0) | **remediated** | Transitive via `sentence-transformers`, unpinned by any workspace `pyproject.toml`. `uv lock --upgrade-package pillow` resolved cleanly to 12.3.0 (clears all three fix targets) with zero other package changes. Trivy-confirmed absent from the rebuilt `astradesk:ci-python-scoped` image. |
| urllib3 | 2.7.0 (was 1.26.20) | 4→0 (CVE-2025-66418/66471 fixed 2.6.0; CVE-2026-21441 fixed 2.6.3; CVE-2026-44431 fixed 2.7.0) | **remediated** | Reachable via `aiobotocore`/`botocore` (auditor S3 sink, Bedrock), `kubernetes-asyncio` (api-gateway K8s calls), `opa-python-client` (live OPA policy calls). The previously-flagged 1.x→2.x resolver-conflict risk did not materialize: `uv lock --upgrade-package urllib3` resolved cleanly straight to 2.7.0 with zero other package changes, confirming the current `botocore`/`kubernetes-asyncio` pins already tolerate urllib3 2.x. `uv run pytest` (448 tests, including the K8s/S3/OPA-touching suites) passed unchanged after the bump. |
| cryptography | 48.0.1 (was 46.0.3) | 2→0 (CVE-2026-26007 fixed 46.0.5; GHSA-537c-gmf6-5ccf vulnerable-bundled-OpenSSL fixed 48.0.1) | **remediated** | Reachable via `python-jose[cryptography]` / `pyjwt[crypto]` (OIDC path). `uv lock --upgrade-package cryptography` (unpinned) resolved to the latest available (49.0.0) — too large a jump for a security-critical crypto backend on the OIDC path, so the upgrade was re-run pinned to the minimal version clearing both advisories: `uv lock --upgrade-package "cryptography==48.0.1"`. Zero other package changes; `uv run pytest` passed unchanged. This is a dependency-version bump only — no auth/OIDC/RBAC code was touched, satisfying the "do not refactor auth/OIDC/RBAC" exclusion. |
| python-jose | 3.3.0 | 3 (incl. CVE-2024-33663 algorithm confusion) | **remediated** (from the shipped image); **pending** (dev/CI environment, low urgency) | Declared only in the **root** `pyproject.toml` (capped `<3.4.0`, which actively blocks the fix), purely so `uv run pytest` can execute `mcp/tests` from the root environment. The standalone `mcp/` service has its **own** separate `uv.lock`, already resolved to `python-jose 3.5.0` (patched) — confirmed via `mcp/uv.lock`. With the Dockerfile scoping change now applied, this root-level copy is no longer installed into any shipped image (it is a dependency of the root meta-package, not of `astradesk-api-gateway`) — confirmed absent from the `astradesk:ci-python-scoped` Trivy scan. The residual risk is dev/CI-environment-only. Lifting the `<3.4.0` cap is still good hygiene but is not required for the image-scan gate to be accurate and was left for a follow-up pass to keep this one surgical. |
| protobuf | 6.33.6 (was 6.33.0) | 1→0 (CVE-2026-0994 fixed 6.33.5/5.29.6) | **remediated** | Reachable via `opentelemetry-exporter-otlp-proto-grpc`/`grpcio-tools` in `services/api-gateway`, and independently in `packages/domain-finance`/`packages/domain-supply`'s own gRPC dependency. `uv lock --upgrade-package protobuf` resolved cleanly to 6.33.6 with zero other package changes. Trivy-confirmed absent from the rebuilt image. |
| setuptools (vendors `wheel`, `jaraco.context`) | 82.0.1 (was 80.9.0) | 2→0 (`wheel` CVE-2026-24049 fixed 0.46.2; `jaraco.context` CVE-2026-23949 fixed 6.1.0) | **remediated** | Trivy's JSON evidence (`PkgPath`) resolved a mystery from the prior pass: `wheel` and `jaraco.context` are **not** independent `uv.lock` dependencies at all (`git grep`/`uv.lock` search found zero direct or transitive entries for either name) — they are copies **vendored inside `setuptools`** itself, at `app/.venv/lib/python3.13/site-packages/setuptools/_vendor/{wheel,jaraco.context}-*.dist-info/`. `setuptools` is pulled transitively by `grpcio-tools`, `kubernetes-asyncio`, and `torch`. Verified by downloading the `setuptools-82.0.1` wheel from PyPI and inspecting its `_vendor/` directory directly before touching the lockfile: it vendors `wheel 0.46.3` (clears the 0.46.2 fix target) and `jaraco.context 6.1.0` (exact fix-target match). `uv lock --upgrade-package setuptools` then resolved cleanly to 82.0.1 with zero other package changes. Trivy-confirmed both vendored findings are gone from the rebuilt image. |
| idna, requests, filelock, msgpack, fonttools | various | 1 each | **pending** | Narrow, low-count transitives (httpx/anyio, huggingface-hub/opa-python-client, torch/transformers/cachecontrol, cachecontrol, matplotlib respectively). Not present in the current `astradesk:ci-python-scoped` Trivy HIGH/CRITICAL scan (0 findings) — retained here as a historical note from the pre-scoping pip-audit baseline; candidates for a future narrow patch-level pass only if they reappear in a Trivy image scan. |
| gzip, libacl1, libncursesw6, libtinfo6, ncurses-base, ncurses-bin, perl-base | Debian trixie (13) package versions, e.g. `gzip 1.13-1`, `perl-base 5.40.1-6` | 11 (9 HIGH, 2 CRITICAL) | **accepted-with-expiry** (`.trivyignore`, `exp:2026-08-31`) | Base-image (`python@sha256:...`, `python:3.13-slim`, built on `debian:trixie-slim`) OS packages, present regardless of any Python dependency scoping. Investigated across two passes per the suggested remediation order ("prefer updating the pinned Python base image digest"): `docker buildx imagetools inspect python:3.13-slim` confirms (both times, most recently in this pass) the currently pinned digest (`sha256:eb43ff12...`) **is already** the latest published multi-arch manifest for that tag — there is no newer digest to refresh to. Cross-checked `python:3.13-slim-bookworm` (Debian 12) as an alternative Debian track; not pursued because Trivy's own DB reports these specific CVEs as `Status: affected` with no `Fixed Version`, or `Status: fix_deferred` for several `perl-base` CVEs (Debian Security Tracker status meaning no patched package has shipped for *any* current suite) — switching Debian tracks would not clear findings Debian itself has not fixed anywhere. This is a genuine upstream blocker, not a project-side gap. Per rule 2 of the accepted-risk pass ("if any Debian OS finding has a non-empty FixedVersion, do not ignore it"), all 11 were re-confirmed via the final Trivy JSON to have `FixedVersion: null`, satisfying rule 3 ("all remaining findings are Debian OS findings with no FixedVersion... add them to `.trivyignore`"). Dispositioned as accepted risk with a hard `exp:2026-08-31` expiry — see "Follow-up: Debian OS accepted-risk disposition" below for the full advisory-by-advisory table and evidence. Re-check at or before that date; if Debian still has not shipped fixes, renew the acceptance with a fresh review rather than silently extending it. |

## Docker scoping: investigated, not applied

The root `Dockerfile`'s builder stage runs `uv sync --all-extras --frozen`,
unlike every sibling service Dockerfile (`services/admin_api/Dockerfile`,
`services/auditor/Dockerfile`, `mcp/Dockerfile`,
`packages/domain-*/Dockerfile`), which all use
`uv sync --frozen --no-dev --package <name>`. This was investigated as a
candidate fix:

1. Built `astradesk:ci-python-before` (unmodified) and
   `astradesk:ci-python-after` (`uv sync --frozen --no-dev --package
   astradesk-api-gateway`) with `docker build --no-cache`. Both built
   successfully.
2. Enumerated installed packages in both images
   (`python -c "import importlib.metadata..."`) and separately ran
   `scripts/ci/supply_chain_scan.sh` (real Trivy, not a simulation) against
   both. Python-package HIGH/CRITICAL findings: 24 (23H+1C) before → 20
   (20H+0C) after. `black`, `ecdsa`, `msgpack`, and **`python-jose`
   (CVE-2024-33663, the one CRITICAL finding)** are present before and absent
   after; every other flagged package (`aiohttp`, `cryptography`,
   `jaraco.context`, `pillow`, `protobuf`, `starlette`, `transformers`,
   `urllib3`, `wheel`) is unchanged, confirming the scoping change removes
   exactly the dev/docs/test/root-only tooling and nothing that
   `astradesk-api-gateway` actually needs.
3. Ran both images with their real `ENTRYPOINT`/`CMD`
   (`uvicorn src.gateway.main:app ...`), not just an import check. **Both**
   fail identically:
   ```
   File "/app/src/gateway/main.py", line 41, in <module>
       from agents.base import BaseAgent
   ModuleNotFoundError: No module named 'agents'
   ```
   Root cause (confirmed via `find`/`cat` inside the container): `uv sync`
   installs `astradesk-api-gateway` in **editable** mode, and its
   `__editable__.astradesk_api_gateway-0.3.0.pth` shim in `.venv` points to
   `/app/services/api-gateway/src` — the builder stage's layout. The runtime
   stage, however, only copies that source to `/app/src`
   (`COPY services/api-gateway/src ./src`) and never to
   `/app/services/api-gateway/src` (unlike `services/auditor` and
   `services/admin_api`, which *are* copied to their matching
   `/app/services/<name>` paths in the runtime stage). `/app/src` alone is
   never added to `sys.path`, so `agents`, `runtime`, `model_gateway`, and
   `tools` (all direct children of `services/api-gateway/src/`) are
   unimportable at container start, regardless of the `uv sync` flags.
4. This defect is **pre-existing** and **unrelated to this pass**: it
   reproduces identically on the untouched `Dockerfile` at `develop`. It has
   gone unnoticed because CI (`build-test-python` in
   `.github/workflows/ci.yml`) only runs `docker build`, never `docker run`,
   for this image. It has not reached a real deployment: `deploy/chart/values.yaml`
   still points at the placeholder `docker.io/youruser/astradesk-api`
   repository, and no Helm/OpenShift template sets a compensating
   `PYTHONPATH`.

**Decision:** the `uv sync` scoping change is not applied in this pass. It is
proven safe relative to the current baseline (identical startup failure with
or without it) and proven to remove real, verified vulnerable
packages — including the sole CRITICAL Python-package finding — but the
task's evidentiary bar for this optional change explicitly requires proof
that "API Gateway starts/imports," and that bar cannot be met while the
unrelated defect above stands, by either version of the image. Fixing that
defect (e.g. also copying `services/api-gateway` to
`/app/services/api-gateway` in the runtime stage, or setting
`ENV PYTHONPATH=/app/src`) is a Dockerfile/packaging bug fix outside
issue #40's dependency/supply-chain scope and is not attempted here — it
should be filed and fixed as its own change, at which point the `uv sync`
scoping edit above (with the Trivy before/after evidence already gathered)
can be reconsidered.

## Follow-up: runtime startup bug fixed; scoping change re-tested, still blocked

A separate bounded pass fixed the pre-existing runtime startup defect
identified above, then re-tested the withheld `uv sync` scoping change now
that its blocking precondition was resolved.

1. **Startup fix applied.** Added `ENV PYTHONPATH=/app/src` to the root
   `Dockerfile` runtime stage, immediately before `USER 10001:10001` — the
   same pattern already shipped in `services/admin_api/Dockerfile` (which
   copies its source to `/app/src` and sets the identical `PYTHONPATH`). No
   other Dockerfile stage, `COPY`, or `CMD` line was changed; `CMD` still
   invokes `src.gateway.main:app` (uvicorn's own `--app-dir` default already
   puts `/app` on `sys.path`, which is why `src.gateway.main` resolves —
   `/app/src` was the entry missing for `main.py`'s own top-level imports
   such as `from agents.base import BaseAgent`).
2. **Proof — import smoke test** (`astradesk:ci-python`, rebuilt with the fix):
   ```
   $ docker run --rm -i --entrypoint python astradesk:ci-python - <<'PY'
   from agents.base import BaseAgent
   from gateway.main import app
   print("api gateway runtime import ok", app is not None, BaseAgent.__name__)
   PY
   api gateway runtime import ok True BaseAgent
   ```
3. **Proof — real entrypoint.** `docker run --rm -p 18080:8000 astradesk:ci-python`
   no longer raises `ModuleNotFoundError`. It now runs past import and
   application startup logic and fails only on missing runtime configuration
   that a bare `docker run` (no compose network, no secrets) cannot supply —
   first `AuthConfigError: Missing required OIDC configuration` (expected
   fail-closed behavior, `INV-FAIL-CLOSED`), and with `AUTH_MODE=local-dev`
   explicitly set, `ConnectionRefusedError` connecting to Postgres (no
   database present in the standalone container). Both are well past the
   original import failure point and are the correct, by-design outcomes for
   a container run outside its real deployment topology.
4. **Scoping change re-tested — new, different blocker found.** With the
   startup fix in place, the root `Dockerfile` builder stage was changed to
   `uv sync --frozen --no-dev --package astradesk-api-gateway` and rebuilt
   with `--no-cache` as `astradesk:ci-python-scoped`. The import smoke test
   now fails differently:
   ```
   File "/app/src/model_gateway/providers/bedrock_provider.py", line 58, in <module>
       import aioboto3
   ModuleNotFoundError: No module named 'aioboto3'
   ```
   Root cause: `services/api-gateway/src/model_gateway/providers/bedrock_provider.py`
   imports `aioboto3` directly (the Bedrock model provider), but
   `services/api-gateway/pyproject.toml` never declares `aioboto3` as a
   dependency of `astradesk-api-gateway` — it is declared only under
   `astradesk-auditor` (`uv.lock` confirms this). The unscoped
   `uv sync --all-extras --frozen` masked this by installing the entire
   workspace, including `astradesk-auditor`'s dependencies, into the same
   shared `.venv`. This is a genuine, pre-existing missing-dependency
   declaration in `astradesk-api-gateway`, distinct from the startup bug
   fixed in this pass, and fixing it requires adding a dependency and
   regenerating `uv.lock` — both explicitly out of scope for this pass
   ("no dependency bumps," "no lockfile changes").
5. **Decision applied per the standing rule:** scoped `uv sync` breaks
   runtime even after the startup fix, so the scoping change is **reverted**;
   the root `Dockerfile` keeps `uv sync --all-extras --frozen`. Only the
   `ENV PYTHONPATH=/app/src` startup fix is kept.
6. **Scan gate re-run against the corrected (unscoped) image**
   (`astradesk:ci-python`) to confirm no regression:
   `scripts/ci/supply_chain_scan.sh astradesk:ci-python` still reports
   `Total: 24 (HIGH: 23, CRITICAL: 1)` Python-package findings — identical to
   the pre-fix baseline recorded above, confirming the `PYTHONPATH` change
   has zero effect on installed packages or the scan gate outcome, as
   expected. The gate still exits non-zero (`FAILED`) on the same `pending`
   packages listed in the disposition table; that is unchanged by this pass.
   (The scoped-image scan hit an unrelated local disk-space exhaustion error
   mid-run in this environment before the scoping change was reverted; since
   the scoping change is not being applied, that scan was not re-run — the
   import-level failure above is sufficient to make the revert decision.)
7. **Follow-up recorded, not actioned here:** declare `aioboto3` as a direct
   dependency of `services/api-gateway/pyproject.toml` in a dedicated pass,
   then re-attempt the `uv sync --frozen --no-dev --package
   astradesk-api-gateway` scoping change (the Trivy before/after evidence
   already gathered above — 24→20 findings, removing the sole CRITICAL,
   `python-jose`/CVE-2024-33663 — remains valid once that precondition is
   also met).

## Follow-up: missing `aioboto3` dependency fixed; scoping change applied

The follow-up item from the previous pass (item 7 above) was actioned in this
bounded pass.

1. **Root cause confirmed.**
   `services/api-gateway/src/model_gateway/providers/bedrock_provider.py`
   imports `aioboto3` directly (`import aioboto3`, `aioboto3.Session()`), but
   `services/api-gateway/pyproject.toml` only declared `botocore` (a
   transitive dependency shared by several AWS SDK packages, not `aioboto3`
   itself). `git grep` confirmed `aioboto3` is otherwise declared only in
   `services/auditor/pyproject.toml` (`aioboto3>=15.4.0`), which is an
   unrelated service.
2. **Dependency declared.** Added `"aioboto3>=15.4.0"` to
   `services/api-gateway/pyproject.toml`'s `dependencies` list, next to the
   existing `botocore` line. The version bound matches
   `astradesk-auditor`'s existing declaration and the version already
   resolved in `uv.lock` (`aioboto3==15.4.0`) — not copied blindly, but the
   same narrow lower bound consistent with the current, already-verified
   lock resolution, so no other package's resolved version changes.
3. **Lockfile regenerated:** `uv lock` (no other flags). Diff is exactly two
   lines: `{ name = "aioboto3" }` added to `astradesk-api-gateway`'s
   `dependencies` and `{ name = "aioboto3", specifier = ">=15.4.0" }` added
   to its `requires-dist` in `uv.lock`. No other package version in the lock
   changed — `aioboto3`, `aiobotocore`, and `boto3` were already resolved at
   their current versions via `astradesk-auditor`.
4. **Root `Dockerfile` scoping change re-applied:**
   `uv sync --all-extras --frozen` → `uv sync --frozen --no-dev --package
   astradesk-api-gateway` in the builder stage. The `ENV PYTHONPATH=/app/src`
   runtime-stage fix from the previous pass is unchanged and still required
   (it addresses a separate problem — the editable-install `.pth`/source-copy
   layout — independent of which packages are installed).
5. **Proof — image rebuilt** with `docker build --no-cache -t
   astradesk:ci-python-scoped .`; build succeeded.
6. **Proof — import smoke test:**
   ```
   $ docker run --rm -i --entrypoint python astradesk:ci-python-scoped - <<'PY'
   from agents.base import BaseAgent
   from gateway.main import app
   print("api gateway scoped runtime import ok", app is not None, BaseAgent.__name__)
   PY
   api gateway scoped runtime import ok True BaseAgent
   ```
   No `ModuleNotFoundError`.
7. **Proof — real entrypoint:**
   `docker run --rm -p 18080:8000 astradesk:ci-python-scoped` runs past
   import and application startup logic, failing only on the same expected,
   by-design `AuthConfigError: Missing required OIDC configuration: OIDC_ISSUER,
   OIDC_AUDIENCE, OIDC_JWKS_URL` (`INV-FAIL-CLOSED`) seen on the unscoped
   image in the previous pass — not an import error.
8. **Supply-chain scan re-run against the scoped image**
   (`scripts/ci/supply_chain_scan.sh astradesk:ci-python-scoped`, real Trivy).
   Results:
   - Debian OS packages: `Total: 11 (HIGH: 9, CRITICAL: 2)` — base-image
     findings (`gzip`, `libacl1`, `ncurses*`, `perl-base`), unaffected by
     Python dependency scoping; unchanged from the unscoped image.
   - Python packages: `Total: 20 (HIGH: 20, CRITICAL: 0)` — down from the
     unscoped baseline of `24 (HIGH: 23, CRITICAL: 1)`, exactly matching the
     prediction recorded in the "Docker scoping: investigated, not applied"
     section above. `black`, `ecdsa`, `msgpack`, and `python-jose`
     (CVE-2024-33663, the sole CRITICAL Python-package finding) are gone.
     The remaining 20 findings are the same 9 packages already documented as
     `pending` in the disposition table: `aiohttp`, `cryptography`,
     `jaraco.context`, `pillow`, `protobuf`, `starlette`, `transformers`,
     `urllib3`, `wheel`. Adding `aioboto3` introduced **zero** new
     HIGH/CRITICAL findings — `aioboto3`, `aiobotocore`, and `boto3` all
     scan clean.
   - The gate still exits non-zero (`FAILED`) — expected, since the 9
     `pending` packages above are real, reachable, and deliberately deferred
     per this pass's scope (no FastAPI/Starlette/Torch/Transformers/
     urllib3/cryptography remediation; batch dependency updates excluded).
     Nothing was added to `.trivyignore`: none of these findings are false
     positives or proven non-reachable, so hiding them would violate
     INV-SC-4.
9. **Decision:** all three changes are kept — `ENV PYTHONPATH=/app/src`, the
   `uv sync --frozen --no-dev --package astradesk-api-gateway` scoping
   change, and the `aioboto3>=15.4.0` dependency declaration (with its
   `uv.lock` update). The root API Gateway image now builds, imports, and
   starts correctly with a minimal, package-scoped dependency surface, and
   ships fewer vulnerable Python packages (20 vs. 24) with zero net-new
   findings from the fix itself.
10. **Remaining `pending` work is unchanged and out of scope for this pass:**
    the 9 Python packages above and the Debian OS-level findings still
    require their own dedicated remediation passes (version bumps, resolver
    verification, and — for the OS packages — a base-image update), per the
    disposition table and this pass's explicit exclusions.

## Follow-up: narrow Python-package remediation (Group A–D triage)

This pass's goal was to make the fail-closed Trivy gate green for
`astradesk:ci-python-scoped`, or produce a precise remaining-blocker list.
Starting point: Debian OS `11 (9H/2C)`, Python packages `20 (20H/0C)`
(identical to the previous pass's final numbers — re-confirmed by a fresh
`docker build --no-cache` and rescan before any change was made).

**Group A — Debian OS base image.** Investigated, blocked, documented above
in the disposition table's `gzip`/`libacl1`/`ncurses*`/`perl-base` row. In
summary: `docker buildx imagetools inspect python:3.13-slim` proved the
Dockerfile's pinned digest is already the latest published one; a
`python:3.13-slim-bookworm` cross-check was not pursued further once Trivy's
own DB confirmed these specific CVEs have `Status: affected`/`fix_deferred`
with no `Fixed Version` in Debian's tracker at all — no currently-published
Debian package fixes them, on any track. Not fixable by a digest bump this
pass or arguably any pass until Debian ships a fix.

**Group B — narrow Python packages (`setuptools`/`wheel`/`jaraco.context`,
`aiohttp`, `protobuf`, `cryptography`, `urllib3`) plus `pillow` (Group D
candidate, resolver-safe).** All seven remediated:

1. Trivy JSON evidence (`audit/evidence/40_trivy_api_gateway_scoped.json`,
   captured with `--format json` against the pre-remediation image) gave
   exact `PkgPath` per finding, resolving what the prior pass could not
   explain: `wheel` and `jaraco.context` have **no entry anywhere in
   `uv.lock`** — confirmed by both `uv.lock` text search and a script walking
   every package block's `dependencies` list for reverse-references. They are
   vendored *inside* `setuptools` at
   `app/.venv/lib/python3.13/site-packages/setuptools/_vendor/`. Verified the
   fix by downloading the `setuptools-82.0.1` wheel directly from PyPI (no
   Docker rebuild needed for this check) and inspecting its `_vendor/`
   contents: it bundles `wheel 0.46.3` and `jaraco.context 6.1.0`, clearing
   both CVEs (fix targets 0.46.2 and 6.1.0 respectively).
2. Applied via `uv`, one package at a time, checking `git diff uv.lock` after
   each for scope (no unrelated package version changes, no added/removed
   package blocks, no duplicate resolutions):
   - `uv lock --upgrade-package setuptools` → 80.9.0 → 82.0.1 (fixes vendored
     `wheel`/`jaraco.context`).
   - `uv lock --upgrade-package aiohttp` → 3.13.1 → 3.14.1 (fix target was
     3.13.3; resolver picked the latest compatible release, still narrowly
     scoped to this one package).
   - `uv lock --upgrade-package protobuf` → 6.33.0 → 6.33.6 (fix target
     6.33.5).
   - `uv lock --upgrade-package urllib3` → 1.26.20 → 2.7.0. The prior pass
     flagged this as a resolver-conflict candidate requiring confirmation
     that `botocore`/`kubernetes-asyncio` tolerate urllib3 2.x — the resolver
     accepted the bump cleanly with zero other package changes, and the full
     test suite (448 tests, including K8s/S3/OPA-touching suites) passed
     unchanged, confirming compatibility.
   - `cryptography`: `uv lock --upgrade-package cryptography` (unpinned) first
     resolved to `49.0.0` — the *latest* release, three major versions ahead
     of 46.0.3, judged too large a jump for a security-critical crypto
     backend on the OIDC verification path without dedicated regression
     coverage. Reverted and re-run pinned to the minimal version that clears
     *both* advisories: `uv lock --upgrade-package "cryptography==48.0.1"`
     (`uv` accepts `name==version` syntax for `--upgrade-package`). This is a
     dependency-version bump only; no line of auth/OIDC/RBAC code was
     touched, keeping this within the "do not refactor auth/OIDC/RBAC/PII"
     exclusion.
   - `uv lock --upgrade-package pillow` → 12.0.0 → 12.3.0 (fix target
     12.2.0). Pillow is grouped with Torch/Transformers in the task's
     suggested order due to shared RAG blast radius, but unlike them it is
     *not* pinned by any workspace `pyproject.toml` (purely transitive via
     `sentence-transformers`), so the resolver moved it independently with
     zero cascade — treated as a Group B-style narrow, resolver-safe fix.
3. **Total lockfile diff for this pass: exactly 6 package version lines
   changed** (`setuptools`, `aiohttp`, `protobuf`, `urllib3`, `cryptography`,
   `pillow`) — confirmed via a script diffing every `[[package]] name`/
   `version` pair before and after; zero packages added, zero removed, zero
   duplicate resolutions.
4. **Proof — `uv run pytest -q services/api-gateway/tests
   services/admin_api/tests mcp/tests`: 448 passed**, run after `uv sync
   --frozen --all-extras` picked up all six changes into the local dev
   environment.
5. **Proof — image rebuild:** `docker build -t astradesk:ci-python-scoped .`
   succeeded (two earlier attempts failed on host disk exhaustion during the
   final `exporting layers` step — an environment-local resource limit, not a
   build or dependency defect; resolved by `docker builder prune -af`
   between attempts to maximize free space before the final successful
   build).
6. **Proof — runtime import and entrypoint, unchanged from prior passes:**
   `from agents.base import BaseAgent; from gateway.main import app` →
   `api gateway scoped runtime import ok True BaseAgent`; the real
   `uvicorn` entrypoint still fails closed on the same expected
   `AuthConfigError: Missing required OIDC configuration` (`INV-FAIL-CLOSED`),
   confirming the dependency bumps did not change startup behavior.
7. **Proof — Trivy rescan of the rebuilt image:** Debian OS unchanged at
   `11 (9H/2C)` (expected — Group A is blocked, see above). Python packages:
   `Total: 7 (HIGH: 7, CRITICAL: 0)`, down from `20 (20H/0C)` — 13 findings
   eliminated, zero new findings introduced. The 7 remaining findings are
   exactly `starlette` (3) and `transformers` (4) — see Groups C/D below.

**Group C — `starlette`/`fastapi`, blocked.** Attempted
`uv lock --upgrade-package starlette`: confirmed a no-op (`git diff uv.lock`
showed zero change). Root cause, confirmed via PyPI metadata
(`pypi.org/pypi/fastapi/0.115.14/json`): FastAPI 0.115.14 declares
`starlette<0.47.0,>=0.40.0`. All three starlette fix targets (0.49.1, 1.1.0,
1.3.1) are above that ceiling. `services/api-gateway/pyproject.toml` itself
pins `"fastapi>=0.115,<0.116"`. Clearing this requires bumping FastAPI past
0.115.x — a resolver-wide change affecting route handling, dependency
injection, and OpenAPI schema generation across every FastAPI-based service
in the workspace, explicitly excluded from this pass by both the "do not
batch-update FastAPI/Starlette" instruction and the "do not break Admin API
contract 1.2.0" / "do not refactor... OpenAPI" constraints. This is a
documented blocker for a dedicated future pass with full route and
OpenAPI-contract regression coverage, not an oversight.

**Group D — `transformers`/`torch`/`pillow`, mostly blocked.** `pillow` was
resolver-safe and is remediated (Group B above). `transformers` and `torch`
are both pinned to **exact** versions in
`services/api-gateway/pyproject.toml` (`"transformers==4.45.2"`,
`"torch==2.9.0"`) — confirmed `uv lock --upgrade-package transformers` and
`uv lock --upgrade-package torch` are both no-ops without editing those
pins. For `torch`: the current Trivy scan reports **zero** HIGH/CRITICAL
findings (the prior pass's disposition-table count of 4 predates this pass's
Trivy JSON evidence and could not be reproduced against the current image;
left as a corrected `not-reachable-as-finding` row, nothing to fix). For
`transformers`: even lifting the exact pin only clears 3 of its 4 advisories
(`CVE-2024-11392/11393/11394`, fixed at 4.48.0) — the 4th
(`CVE-2026-4372`) requires the 5.x major line, which is a real
`sentence-transformers`/RAG-pipeline compatibility risk (`sentence-
transformers` is pinned to 3.x). Per this pass's explicit "treat
Transformers/Torch/Pillow separately because of RAG/ML blast radius"
instruction, this is deferred to a dedicated pass with full RAG test
coverage, not attempted here.

**Tooling fix required to keep this evidence file itself passing CI:**
`scripts/license_headers.py --check` flagged
`audit/evidence/40_trivy_api_gateway_scoped.json` for "obsolete Apache
license reference remains." Root cause: the checker's `APACHE_PATTERN` scans
every tracked file's raw text for old Apache-license header remnants (a
leftover-cleanup check from AstraDesk's relicense to GPL-2.0-only) — but a
raw Trivy JSON scan report legitimately embeds many third-party packages'
own SPDX license identifiers (e.g. `protobuf`, `cryptography` are
Apache-licensed) as *scanned data*, not as our own file header. This is a
structural, permanent conflict: any future Trivy JSON evidence artifact
under `audit/evidence/` will always trip this check as long as any scanned
package in the image is Apache-licensed (i.e. always). Fixed narrowly in
`scripts/license_headers.py`'s `is_excluded()`: files matching
`audit/evidence/*.json` are now excluded from the header/Apache-pattern scan
(plain `.json` files already had no header-format requirement — this only
suppresses the false-positive pattern match). The exclusion is scoped
specifically to `audit/evidence/*.json`; it does not weaken enforcement for
`audit/evidence/*.md` files (which retain their required canonical header)
or any `.json` file elsewhere in the repository. Verified:
`uv run python scripts/license_headers.py --check` → `License headers
verified; would normalize 0 file(s).`

**Decision:** all six dependency bumps are kept (`setuptools`, `aiohttp`,
`protobuf`, `urllib3`, `cryptography`, `pillow`), plus the
`scripts/license_headers.py` exclusion fix. The Trivy gate is **not** green
— Debian OS (11, blocked on an upstream fix) and `starlette`/`transformers`
(7, blocked on resolver-affecting, explicitly out-of-scope framework/ML
version bumps) remain. Every remaining finding has a specific, evidenced
blocker recorded above; none are hidden in `.trivyignore` — none qualify as
false positives or proven non-reachable under INV-SC-1, so suppressing them
would violate INV-SC-4.

## Follow-up: Starlette/FastAPI remediation

Follow-up bounded pass, scoped to *only* the `starlette` findings identified
as blocked above. `transformers`/`torch`/RAG dependencies were explicitly
untouched, per the pass's own scope contract.

1. **Constraint audit.** `git grep -nE "fastapi|starlette"` across every
   workspace member's `pyproject.toml` plus `uv.lock` found three declarations
   of `fastapi`: `services/api-gateway/pyproject.toml` (`>=0.115,<0.116` —
   the blocker), `services/admin_api/pyproject.toml` (`>=0.115.0`, no upper
   bound — not a blocker), and `mcp/pyproject.toml` (`>=0.110.0`, no upper
   bound). The `mcp/` service is **not** a `[tool.uv.workspace]` member (root
   `pyproject.toml` comment confirms it is deliberately excluded — it has its
   own independent `mcp/uv.lock`), so it does not participate in or constrain
   the root workspace's resolution at all. No other workspace file pins
   `starlette` directly. Confirmed `services/api-gateway/pyproject.toml`'s
   `fastapi<0.116` ceiling is the sole blocker in the root workspace
   resolution.
2. **Confirmed the suggested resolver flow alone is insufficient.**
   `uv lock --upgrade-package fastapi` (run before any `pyproject.toml` edit)
   was a confirmed no-op — `git diff uv.lock` showed zero change beyond the
   prior pass's six package bumps, since the `pyproject.toml` ceiling still
   capped the resolver at `0.115.14`.
3. **Found the minimal FastAPI version line.** Per the instruction to "prefer
   bumping FastAPI only to the lowest version line that resolves Starlette to
   a patched version," queried PyPI metadata (`pypi.org/pypi/fastapi/<version>/json`,
   `requires_dist`) across every FastAPI minor release from `0.115.0` to the
   latest (`0.139.0`, 91 stable releases) to find exactly where the
   `starlette` upper bound relaxes:

   | FastAPI version | `starlette` constraint |
   |---|---|
   | 0.116.0 | `<0.47.0,>=0.40.0` |
   | 0.117.0–0.120.x | `<0.49.0,>=0.40.0` |
   | 0.121.0 | `<0.50.0,>=0.40.0` (crosses the first fix, 0.49.1) |
   | 0.122.0–0.128.x | `<0.51.0,>=0.40.0` |
   | 0.129.0–0.132.x | `<1.0.0,>=0.40.0` (still short of the 1.1.0/1.3.1 fixes) |
   | **0.133.0** | **`>=0.40.0` — upper bound removed entirely** |

   `0.133.0` is therefore the lowest FastAPI release that permits resolving
   `starlette` to any patched 1.x version. Confirmed `0.132.1` (the
   immediately preceding stable release) still carries the `<1.0.0` cap, so
   `0.133.0` is the exact cutover, not an approximation.
4. **Applied the minimal edit.** Changed
   `services/api-gateway/pyproject.toml`'s dependency line from
   `"fastapi>=0.115,<0.116"` to `"fastapi>=0.133,<0.134"` — raising the floor
   only as far as the identified cutover and keeping the same one-minor-line
   pinning discipline the file already used (not floating to `latest`).
5. **Regenerated the lockfile with `uv` only (no pip).** `uv lock` alone
   resolved `fastapi` to `0.133.1` but left `starlette` at the old `0.46.2` —
   `uv`'s default resolution keeps an already-locked package version when it
   still satisfies the (now relaxed) constraint, it does not opportunistically
   upgrade transitives. `uv lock --upgrade-package starlette` was then run
   explicitly, resolving `starlette` to `1.3.1` (the latest available,
   clearing all three CVE fix targets: 0.49.1, 1.1.0, 1.3.1).
6. **Diff scope, verified via a script diffing every `[[package]]`
   name/version pair before and after:** exactly `fastapi` (0.115.14→0.133.1)
   and `starlette` (0.46.2→1.3.1) changed among previously-resolved packages,
   plus **one new package**, `annotated-doc==0.0.4` — a ~7&nbsp;KB first-party
   FastAPI utility package (`Annotated[..., Doc(...)]` metadata support,
   maintained by FastAPI's own author) pulled in directly by the newer
   `fastapi` release; confirmed via `uv.lock` reverse-dependency search that
   `fastapi` is its only consumer. Zero packages removed, zero duplicate
   resolutions, and the six package bumps from the prior pass
   (`setuptools`/`aiohttp`/`protobuf`/`urllib3`/`cryptography`/`pillow`)
   are untouched by this change.
7. **Proof — `uv run pytest -q services/api-gateway/tests
   services/admin_api/tests mcp/tests`: 448 passed, 1 warning.** The warning
   is `StarletteDeprecationWarning: Using httpx with starlette.testclient is
   deprecated; install httpx2 instead` — a test-tooling-only notice from
   `starlette.testclient.TestClient` (used exclusively by FastAPI's own test
   client wrapper in the test suite), not a runtime/production code path.
   Not acted on: installing a new, unreleased-sounding `httpx2` dependency
   speculatively is out of scope for a Starlette-CVE-only pass and would
   itself be a dependency addition requiring its own review.
8. **Proof — `uv run ruff check` / `uv run ruff format --check`** (same
   paths as the baseline suite): both pass with zero findings.
9. **Proof — `bash scripts/check-openapi-version.sh`: exit 0, no output.**
   No OpenAPI contract drift from the FastAPI bump — confirmed the Admin API
   contract (`openapi/astradesk-admin.v1.yaml` /
   `services/admin-portal/OpenAPI.yaml`) was not touched and the version
   checker raised nothing. No manual OpenAPI edits were made or needed.
10. **Proof — image rebuild:** `docker build -t astradesk:ci-python-scoped .`
    succeeded on the first attempt (no disk-space retries needed this time).
11. **Proof — runtime import and entrypoint, unchanged:**
    `from agents.base import BaseAgent; from gateway.main import app` →
    `api gateway scoped runtime import ok True BaseAgent`; the real
    `uvicorn` entrypoint still fails closed on the same
    `AuthConfigError: Missing required OIDC configuration`
    (`INV-FAIL-CLOSED`), confirming the FastAPI/Starlette bump did not change
    startup or auth-wiring behavior.
12. **Proof — Trivy rescan of the rebuilt image:** Debian OS unchanged at
    `11 (9H/2C)` (Group A remains blocked on the upstream Debian fix, not
    touched this pass). Python packages: `Total: 4 (HIGH: 4, CRITICAL: 0)`,
    down from `7 (7H/0C)` — all 3 `starlette` findings eliminated, zero new
    findings introduced. The 4 remaining findings are exactly `transformers`
    (`CVE-2024-11392/11393/11394/CVE-2026-4372`), untouched as required by
    this pass's explicit scope exclusion.

**Decision:** the `fastapi` constraint bump (`>=0.115,<0.116` →
`>=0.133,<0.134`) and the resulting `starlette` 0.46.2→1.3.1 /
`annotated-doc` 0.0.4 lockfile changes are kept. The Trivy gate is still
**not** green — Debian OS (11, blocked on an upstream Debian fix) and
`transformers` (4, blocked on a 5.x major-line RAG-compatibility risk,
explicitly out of scope for this pass) remain, both with specific, evidenced
blockers recorded in the disposition table above. Nothing was added to
`.trivyignore`.

## Follow-up: Transformers/RAG-ML remediation

Dedicated follow-up pass, scoped to *only* the `transformers` findings left
blocked above. Debian OS and Torch were explicitly out of scope; Torch was
touched only to the extent of *verifying* it did not need to change.

1. **Confirmed the RAG/embedding code surface and blast radius.**
   `git grep` for `transformers|sentence-transformers|SentenceTransformer|
   torch|embedding|rag|vllm|huggingface` across `services/api-gateway`,
   `core`, and `packages` found exactly one direct
   `sentence_transformers.SentenceTransformer` import/usage site:
   `services/api-gateway/src/runtime/rag.py`. No other workspace member
   imports `transformers` or `sentence_transformers` directly. All existing
   RAG tests (`services/api-gateway/tests/runtime/test_rag.py`,
   `test_pii_emitters.py`) patch `SentenceTransformer` with a `MagicMock`,
   so no test exercises a real embedding computation — the regression risk
   from a library bump is entirely about import-time/constructor/call-
   signature compatibility, not numerical output drift.
2. **Confirmed exact Trivy fix targets from JSON evidence:** 3 advisories
   (`CVE-2024-11392`, `CVE-2024-11393`, `CVE-2024-11394`) fixed at `4.48.0`
   (within the existing 4.x line); the 4th (`CVE-2026-4372`) fixed only at
   `5.3.0` — a major-line jump.
3. **Confirmed the suggested resolver flow alone is insufficient.**
   `uv lock --upgrade-package transformers` against the existing exact pin
   `"transformers==4.45.2"` was a confirmed no-op (`git diff uv.lock`
   unchanged; version still `4.45.2`).
4. **Checked whether Torch needed to change before touching anything.**
   Queried PyPI metadata for `transformers==5.3.0`'s optional `torch` extra:
   `torch>=2.4` — well below the current exact pin `"torch==2.9.0"`.
   `transformers`' base install (no extras) declares **no** hard `torch`
   dependency at all (torch is intentionally optional in transformers'
   own packaging; the consuming application pins its own torch version,
   exactly as this repo already does). Conclusion: Torch does not need to
   change for this fix, and per the pass's own rule ("do not update Torch
   unless resolver or runtime compatibility requires it") it was left
   untouched.
5. **Edited the `transformers` pin** in
   `services/api-gateway/pyproject.toml` from `"transformers==4.45.2"` to
   `"transformers>=5.3.0,<5.4.0"` — the minimum version that clears the 4th
   CVE, pinned to a single narrow minor line (matching the file's existing
   `fastapi>=0.133,<0.134`-style convention) rather than left unbounded.
6. **`uv lock` reported a resolver conflict**, exactly as anticipated by the
   pass's own contingency rule: `sentence-transformers>=3.0,<4.0`
   transitively requires `transformers<5.0.0` (every sentence-transformers
   release from `3.0.0` through `5.1.x` declares this same upper bound —
   confirmed by querying PyPI metadata for representative versions across
   that entire range), which is incompatible with the new
   `transformers>=5.3.0` floor.
7. **Found the minimal `sentence-transformers` version line that resolves
   the conflict.** Queried PyPI metadata for `requires_dist` across every
   `sentence-transformers` release from `4.0.0` through `5.3.0`:

   | sentence-transformers version | `transformers` constraint |
   |---|---|
   | 3.0.0–3.1.1 | `<5.0.0,>=4.34.0`/`>=4.38.0` |
   | 3.2.0–5.1.0 | `<5.0.0,>=4.41.0` |
   | **5.2.0** | **`<6.0.0,>=4.41.0` — upper bound raised past 5.x** |
   | 5.3.0 | `<6.0.0,>=4.41.0` (unchanged from 5.2.0) |

   `5.2.0` is the exact cutover. Edited the `sentence-transformers` pin to
   `"sentence-transformers>=5.2.0,<5.3.0"` — narrowed to that one minor
   line, per the pass's own rule 8 ("update sentence-transformers only as
   narrowly as needed"). This is unavoidably a 2-major-line jump
   (3→4→5) in absolute terms; there is no `sentence-transformers` version
   below `5.2.0` that permits `transformers>=5.3.0`, so no narrower path
   exists.
8. **Re-ran `uv lock` — resolved cleanly with no further conflicts:**
   `transformers` 4.45.2→5.3.0, `sentence-transformers` 3.4.1→5.2.3 (the
   latest patch within the pinned `5.2.x` line), plus transitive cascade
   required by transformers 5.3.0's own updated dependency floor:
   `huggingface-hub` 0.36.0→1.22.0 (transformers 5.3.0 requires
   `huggingface-hub>=1.3.0,<2.0`), `tokenizers` 0.20.4rc0→0.23.0rc0
   (transformers 5.3.0 requires `tokenizers>=0.22.0,<=0.23.0`), `hf-xet`
   1.2.0→1.5.1, `click` 8.3.0→8.4.2, and two new small packages pulled in
   as `typer`'s own dependencies (`typer` itself is a new transitive of
   `huggingface-hub`≥1.x's CLI): `typer==0.26.8`, `shellingham==1.5.4`.
   Verified via a script diffing every `[[package]]` name/version pair:
   these are the *only* changes — zero unrelated packages touched, zero
   duplicate resolutions, `torch`/`fastapi`/`starlette` and the prior
   passes' six other bumps (`setuptools`/`aiohttp`/`protobuf`/`urllib3`/
   `cryptography`/`pillow`) all unchanged.
9. **Proof — RAG/embedding-tagged test subset:**
   `uv run pytest -q services/api-gateway/tests -k "rag or embedding or
   model_gateway or vllm or provider"` → **32 passed, 378 deselected.**
10. **Proof — full selected test gate:** `uv run pytest -q
    services/api-gateway/tests services/admin_api/tests mcp/tests` → **448
    passed, 1 warning** (the same pre-existing
    `StarletteDeprecationWarning` about `httpx`/`starlette.testclient` from
    the prior FastAPI/Starlette pass — unrelated to this change, not new).
11. **Proof — `uv run ruff check` / `uv run ruff format --check`** (same
    paths as the baseline suite): both pass with zero findings.
    `bash scripts/check-openapi-version.sh`: exit 0, no output — no
    OpenAPI contract drift; no OpenAPI files touched.
12. **Proof — image rebuild:** `docker build -t astradesk:ci-python-scoped .`
    succeeded on the first attempt.
13. **Proof — runtime import and entrypoint, unchanged:**
    `from agents.base import BaseAgent; from gateway.main import app` →
    `api gateway scoped runtime import ok True BaseAgent`; the real
    `uvicorn` entrypoint still fails closed on the same
    `AuthConfigError: Missing required OIDC configuration`
    (`INV-FAIL-CLOSED`), confirming the ML-stack bump did not change
    startup or auth-wiring behavior.
14. **Proof — Trivy rescan of the rebuilt image:** Debian OS unchanged at
    `11 (9H/2C)` (out of scope for this pass, blocked on the upstream
    Debian fix documented earlier). Python packages: **zero HIGH/CRITICAL
    findings** — down from `4 (4H/0C)`. Confirmed directly in the raw scan
    output: `transformers-5.3.0.dist-info/METADATA` lists `0` matched
    vulnerabilities, and no `Total:` line is emitted for the Python/lang-pkgs
    category at all (Trivy only prints a category total when it has
    findings to report). Zero new findings introduced by the
    `huggingface-hub`/`tokenizers`/`hf-xet`/`click`/`typer`/`shellingham`
    transitive cascade.

**Decision:** the `transformers` (→5.3.0) and `sentence-transformers`
(→5.2.3) constraint changes, and their full resolver-forced transitive
cascade, are kept. `torch` was verified unnecessary to change and was left
at `2.9.0`. The Trivy gate is still **not** green — only the Debian OS
findings (11, blocked on an upstream Debian fix, explicitly out of scope for
this pass) remain. This is now the *sole* remaining blocker to a fully green
`astradesk:ci-python-scoped` gate. Nothing was added to `.trivyignore`.

## Follow-up: Debian OS accepted-risk disposition

Final follow-up pass. No Python dependency, Docker, or application code
changes were made — this pass only dispositions the last remaining findings
(all Debian OS, all with no upstream fixed version) and hardens the scan
gate script itself. `transformers`/`torch`/RAG and all other Python packages
were explicitly out of scope and untouched.

### Confirmed only Debian OS findings remain (decision rule 1)

Re-extracted every HIGH/CRITICAL finding from
`audit/evidence/40_trivy_api_gateway_scoped.json` (the final JSON from the
prior "Transformers/RAG-ML remediation" pass). All 11 entries have
`Target: astradesk:ci-python-scoped (debian 13.5)` / `Type: debian` — zero
are Python-package findings. Decision rule 1 ("if any remaining finding is
a Python package finding, stop and report it") does not trigger.

### Confirmed no FixedVersion exists for any of them (decision rule 2)

| Advisory ID | Package(s) | Severity | Installed | FixedVersion | Trivy `Status` |
|---|---|---|---|---|---|
| `CVE-2026-41992` | `gzip` | HIGH | `1.13-1` | *(none)* | `affected` |
| `CVE-2026-54369` | `libacl1` | HIGH | `2.3.2-2+b1` | *(none)* | `affected` |
| `CVE-2025-69720` | `libncursesw6`, `libtinfo6`, `ncurses-base`, `ncurses-bin` | HIGH | `6.5+20250216-2` | *(none)* | `affected` |
| `CVE-2026-42496` | `perl-base` | CRITICAL | `5.40.1-6` | *(none)* | `fix_deferred` |
| `CVE-2026-8376` | `perl-base` | CRITICAL | `5.40.1-6` | *(none)* | `affected` |
| `CVE-2026-42497` | `perl-base` | HIGH | `5.40.1-6` | *(none)* | `fix_deferred` |
| `CVE-2026-48962` | `perl-base` | HIGH | `5.40.1-6` | *(none)* | `affected` |
| `CVE-2026-9538` | `perl-base` | HIGH | `5.40.1-6` | *(none)* | `fix_deferred` |

11 total findings (9 HIGH / 2 CRITICAL) across 8 unique advisory IDs — every
one has an empty `FixedVersion`. As an additional, independent check beyond
the JSON evidence alone, re-ran
`docker buildx imagetools inspect python:3.13-slim` (same command used in
two prior passes): the digest returned
(`sha256:eb43ff125d8d58d7449dcba7d336c23bcac412f526d861db493b9994d8010280`)
is byte-for-byte identical to the digest already pinned in `Dockerfile` —
confirming, a third time, that no newer base image exists to refresh to.
Decision rule 2 ("if any Debian OS finding has a non-empty FixedVersion, do
not ignore it — remediate instead") does not trigger for any of the 11.

### Verified Trivy's actual `exp:` enforcement before relying on it

Rather than assume, empirically tested Trivy 0.72.0's behavior with two
throwaway ignorefiles against the real image, each containing only
`CVE-2026-41992 exp:<date>`:

- `exp:2020-01-01` (already expired): the CVE **still appeared** in scan
  output — Trivy did not suppress an expired entry.
- `exp:2099-01-01` (far future): the CVE **did not appear** — Trivy
  correctly suppressed a non-expired entry.

This proves Trivy 0.72.0 *does* correctly enforce the expiry date once an
`exp:` annotation is present. However, Trivy's ignorefile format treats
`exp:` as optional — a bare `CVE-2024-12345` line with no `exp:` at all
would be suppressed **forever**, which conflicts with this repository's own
documented policy (this file's header, INV-SC-4: "Entries without an `exp:`
date are not permitted"). That specific gap — mandatory presence of `exp:`,
not the date comparison itself — was not enforced anywhere before this pass.

### Hardened `scripts/ci/supply_chain_scan.sh` to close that gap

Added a `validate_ignorefile_expiry()` function, run before Trivy is
invoked, that parses `.trivyignore` (skipping comments and blank lines) and
fails closed (exit 1, before any scan runs) if any active entry either lacks
an `exp:YYYY-MM-DD` suffix or has one that has already passed (UTC date
comparison, lexicographic on the zero-padded ISO-8601 format — no
`date -d` parsing needed, keeping it a small, portable, easily-read check
per the "keep this simple" instruction). Manually exercised three cases
directly (not part of the pytest suite — this is a small bash script with
no existing shell-test framework in the repo):

1. An entry missing `exp:` → `EXIT=1`, error names the file, line number,
   and the offending entry.
2. An entry with an already-past `exp:2020-01-01` → `EXIT=1`, error states
   the expiry date and today's UTC date.
3. A file with a comment line, a blank line, and two entries with valid
   future `exp:` dates → `EXIT=0`.

The existing (pre-this-pass) `.trivyignore`, which had zero active entries,
was also re-validated and passed (`EXIT=0`) before any new entries were
added, confirming the function does not false-positive on a header-only
file.

### Added the `.trivyignore` entries (decision rule 3)

Added exactly the 8 unique advisory IDs from the table above to
`.trivyignore`, one per line, each under a justification comment
identifying the affected package(s), installed version, and Trivy `Status`,
with a pointer to this evidence file, and each stamped `exp:2026-08-31` —
the exact date specified for this pass. No wildcard suppressions, no
Python-package IDs, no packages beyond the 8 confirmed above.

### Proof — image rebuild and final scans

1. `docker build -t astradesk:ci-python-scoped .` — succeeded (mostly a
   cache hit: no Dockerfile, dependency, or application source changed this
   pass, only `.trivyignore` and `scripts/ci/supply_chain_scan.sh`, neither
   of which is copied into the image).
2. Runtime import proof, unchanged:
   `api gateway scoped runtime import ok True BaseAgent`; real `uvicorn`
   entrypoint still fails closed on
   `AuthConfigError: Missing required OIDC configuration`
   (`INV-FAIL-CLOSED`).
3. Regenerated `audit/evidence/40_trivy_api_gateway_scoped.json` against the
   rebuilt image with `--ignorefile .trivyignore`: **zero** vulnerabilities
   in both the `debian` (os-pkgs) and `Python` (lang-pkgs) result sets.
4. **Final gate proof:**
   `scripts/ci/supply_chain_scan.sh astradesk:ci-python-scoped` →
   `supply_chain_scan.sh: astradesk:ci-python-scoped PASSED.` — **exit 0.**
   The Trivy table output confirms
   `astradesk:ci-python-scoped (debian 13.5) | debian | 0` and every scanned
   Python package at `0`, with the log line
   `Some vulnerabilities have been ignored/suppressed. Use the
   "--show-suppressed" flag to display them.` confirming the 11 findings
   were suppressed via the new `.trivyignore` entries, not silently absent
   for an unrelated reason.
5. Full baseline validation suite re-ran clean: `uv run ruff check`,
   `uv run ruff format --check`, `uv run pytest -q
   services/api-gateway/tests services/admin_api/tests mcp/tests` (448
   passed, 1 warning — the same pre-existing unrelated
   `StarletteDeprecationWarning`), `uv run python
   scripts/license_headers.py --check`, `bash
   scripts/check-openapi-version.sh`, both `docker compose ... config`
   invocations, and `uv run python scripts/ci/verify_build_baseline.py` —
   all pass with zero findings, confirming this pass introduced no
   regression anywhere else.

### Statements required by this pass's contract

- **Zero Python-package HIGH/CRITICAL findings remain** in
  `astradesk:ci-python-scoped`, confirmed by the final JSON evidence and by
  the gate script's own PASSED table output.
- **Issue #39 (durable, recoverable audit — JetStream, ack-after-durable-
  write, DLQ, crash-recovery testing) was not touched** by this pass or any
  prior pass on this branch. No JetStream, audit-durability, or DLQ code was
  read, modified, or referenced.

**Decision:** the 8 advisory-ID entries in `.trivyignore` (all
`exp:2026-08-31`) and the `scripts/ci/supply_chain_scan.sh` expiry-validation
hardening are kept. The fail-closed Trivy gate now **passes** (exit 0) for
`astradesk:ci-python-scoped`. This does not itself close issue #40 — per the
issue's contract, #40 closes only via the PR that merges this branch after
CI passes.

## Reachability method

For each flagged package, reachability was determined by walking `uv.lock`
reverse-dependencies against the direct dependency lists in each workspace
member's own `pyproject.toml`, then cross-checking which Dockerfile actually
installs that member (`uv sync --package <name>` scoping) versus which image
still performs a full/`--all-extras` install. Packages that only appear
because of the latter are the ones remediated in this pass; every other
package is a genuine direct-or-transitive runtime dependency of a shipped
service and is documented `pending` rather than glossed over.

## What is explicitly deferred (not "accepted")

Nothing above is recorded as **accepted-with-expiry**. That disposition
requires a `.trivyignore` entry with a justification and an `exp:` date
(INV-SC-4), and this pass's instructions restrict `.trivyignore` to proven
non-reachable findings or documented false positives — not reachable findings
that are merely deferred for resolver-safety reasons. The `pending` rows
above are the honest, current state: real, reachable, and awaiting a
dedicated remediation pass with full test evidence per package. The CI gate
added in this pass will correctly report these as failures on
`astradesk:ci-python` until they are individually remediated or a future,
explicitly-reviewed acceptance is recorded.

## Follow-up: Admin Portal / JS image remediation

Bounded pass scoped to `astradesk:ci-js` only. No Python or Java changes were
made. Node.js was kept at 22; `npm audit fix` was never run.

### Findings before this pass

`docker build -f services/admin-portal/Dockerfile -t astradesk:ci-js .` (a
cache hit — no source had changed) followed by `trivy image --severity
HIGH,CRITICAL --format json --ignorefile .trivyignore` against
`astradesk:ci-js` (raw output: `audit/evidence/40_trivy_admin_portal_js.json`,
this pass's post-fix version — the pre-fix JSON was not separately retained,
per the instruction to overwrite that evidence file) reproduced exactly the
13 findings named in this pass's brief:

| Package | Installed | Findings | Path |
|---|---|---|---|
| `next` | 15.5.5 | 11 (1 CRITICAL: CVE-2025-55182; 10 HIGH: CVE-2026-44573/44574/44575/44578/44579/45109, GHSA-8h8q-6873-q5fj, GHSA-h25m-26qc-wcjf, GHSA-mwv6-3258-q52c, GHSA-q4gf-8mx6-v5v3) | `app/standalone/node_modules/next/package.json` |
| `picomatch` | 4.0.3 | 1 HIGH: CVE-2026-33671 | `usr/local/lib/node_modules/npm/node_modules/picomatch/package.json` |
| `sigstore` | 3.1.0 | 1 HIGH: CVE-2026-48815 | `usr/local/lib/node_modules/npm/node_modules/sigstore/package.json` |

The `picomatch`/`sigstore` `PkgPath` values confirmed, before any change was
made, that both are vendored **inside the base image's own global npm CLI
install** (`/usr/local/lib/node_modules/npm/node_modules/...`), not Admin
Portal application dependencies — the project's own `package-lock.json` also
resolves a `picomatch@4.0.3` copy transitively (via `tailwindcss`/glob
tooling), but that copy is a *build-time-only* dependency never traced into
`.next/standalone` and never appeared as a separate Trivy finding.

### `next` remediation — targeted lockfile update

Every one of the 11 `next` findings' `FixedVersion` lists was cross-checked
to find the lowest 15.x patch that clears all of them simultaneously; the
binding constraint is CVE-2026-45109 (`15.5.18, 16.2.6`) — every other
finding's floor (15.5.7 through 15.5.16) is at or below 15.5.18. **15.5.18**
was therefore the target, confirmed reachable via `npm view next@15.5.18
version` against the real registry before touching any file.

Ran, inside the exact pinned base image the Dockerfile already uses
(`node@sha256:16e22a550f3863206a3f701448c45f7912c6896a62de43add43bb9c86130c3e2`,
Node 22.23.1 / npm 10.9.8 — Node.js was not installed in the host shell used
for this pass, so all `npm`/`node` commands in this pass ran inside this
pinned image, mounted as `--user 1000:1000` to keep host file ownership
correct):

```bash
npm install next@15.5.18 --package-lock-only
```

`git diff` on the result confirms a surgically-scoped change: `package.json`
changes only the `"next"` line (`^15.0.0` → `^15.5.18`); `package-lock.json`
changes only `next`, its `@next/env`, and its eight `@next/swc-*` optional
platform packages (15.5.5 → 15.5.18 throughout, 41 insertions / 40
deletions, zero other `node_modules/*` package entries touched). `react`/
`react-dom` were not touched — the resolver did not require it. (`npm`'s own
file-rewrite also alphabetically re-sorted two adjacent `devDependencies`
keys — `@vitest/coverage-v8` and `vitest` — as an unavoidable side effect of
letting `npm install` manage the file; no semantic change.)

`npm ci` was then re-run to materialize the updated lockfile (one run hit a
transient `ETXTBSY` from `esbuild`'s postinstall binary-version check — a
known bind-mount/exec race, not a code issue; the retry succeeded cleanly
with no code changes in between).

### Global npm/corepack/yarn remediation — runtime-stage hardening

Per the suggested remediation order, first checked whether a newer
`node:22-alpine` digest would clear `picomatch`/`sigstore`:
`docker buildx imagetools inspect node:22-alpine` returned manifest-list
digest `sha256:16e22a550f3863206a3f701448c45f7912c6896a62de43add43bb9c86130c3e2`
— byte-identical to the digest already pinned in
`services/admin-portal/Dockerfile`. As with the Python base image in the
Debian OS follow-up above, there is no newer digest to refresh to; a digest
bump cannot clear these findings.

Confirmed the fallback condition (the standalone runtime never needs
npm/corepack/yarn) by inspecting the base image directly: `CMD ["node",
"server.js"]` is the only thing the `runner` stage ever executes, and the
base image's npm/corepack/yarn footprint is entirely separate, root-owned
payload — `/usr/local/lib/node_modules/npm` (17.2 MB, containing the exact
vendored `picomatch`/`sigstore` copies Trivy flagged),
`/usr/local/lib/node_modules/corepack` (1.2 MB), and `/opt/yarn-v1.22.22`
(referenced by the `/usr/local/bin/{yarn,yarnpkg}` symlinks). None of it is
reachable from `node server.js`.

Added one `RUN rm -rf ...` in the final `runner` stage of
`services/admin-portal/Dockerfile` (merged into the pre-existing `chown`
step's own `RUN`, after the `COPY --from=build`/`COPY services/admin-portal/
package.json` lines, before `USER 1000:1000`), removing
`/usr/local/lib/node_modules/{npm,corepack}`,
`/usr/local/bin/{npm,npx,corepack,yarn,yarnpkg}`, and `/opt/yarn-v*`. The
`deps` and `build` stages are untouched and still run `npm ci`/`npm run
build` against the full, unmodified base image — only the shipped `runner`
stage loses the package-manager payload.

### Admin Portal verification (all green)

Run inside the same pinned Node 22 image, from the repository root bind-
mounted so the OpenAPI scripts' `findRepoRoot()` (`.git`-based) resolution
works:

1. `npm ci` — 520 packages installed, zero errors (after the one transient
   `ETXTBSY` retry noted above).
2. `npm run openapi:gen` — regenerated `src/api/types.gen.ts`; `git diff`
   confirmed **zero content change** (the spec had not moved since the last
   generation).
3. `npm run openapi:check` — `OpenAPI artifacts up-to-date.`
4. `npm run lint` — `eslint . --max-warnings=0`, zero warnings/errors.
5. `npm test` — `vitest run`: 3 test files, 4 tests, all passed.
6. `npm run build` — `next build` with `NEXT_PUBLIC_API_BASE_URL=http://
   localhost:8080` (matching the exact env var the root
   `.github/workflows/ci.yml` sets for this same step — plain `npm run
   build` with no env var fails fast on the pre-existing, unrelated
   `lib/env.ts` build-time validation, which is expected and matches the
   nested `services/admin-portal/.github/workflows/ci.yml`'s own behavior,
   not a regression from this pass). Compiled successfully; all 24 routes
   generated, unchanged from the pre-fix route list.

### Proof — image rebuild and final scan

1. `docker build --no-cache -f services/admin-portal/Dockerfile -t
   astradesk:ci-js .` — succeeded, including the new `rm -rf` runtime-
   hardening layer (1.7s).
2. `scripts/ci/supply_chain_scan.sh astradesk:ci-js` →
   `supply_chain_scan.sh: astradesk:ci-js PASSED.` — **exit 0.** Every
   scanned target (`alpine 3.24.1` OS packages plus every `node-pkg` target
   under `app/standalone/node_modules/...`) reports `0` vulnerabilities; the
   `usr/local/lib/node_modules/npm/...` targets no longer appear in the
   report at all, confirming physical removal rather than suppression.
3. Regenerated `audit/evidence/40_trivy_admin_portal_js.json` against the
   fixed image with the same `--ignorefile .trivyignore` invocation used by
   the gate script.
4. Runtime proof: `docker run --rm --entrypoint node astradesk:ci-js -v` →
   `v22.23.1` (node still present and functional post-hardening).
5. Startup smoke test: `timeout 20s docker run --rm -p 13000:3000 -e
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8080 astradesk:ci-js` → server
   logged `✓ Ready in 77ms`, then was stopped by the timeout (exit 124) —
   the explicitly-acceptable outcome. No missing-`node`, missing-
   `server.js`, or module-resolution failure.

### Statements required by this pass's contract

- **Zero JS-package HIGH/CRITICAL findings remain** in `astradesk:ci-js`,
  confirmed by the final JSON evidence and the gate script's PASSED output.
- Node.js stayed at 22 throughout (pinned by digest, unchanged); `npm audit
  fix` was never invoked; no Python dependency was touched; no Admin API
  contract, OpenAPI spec, or auth/OIDC/RBAC code was touched.
- Issue #39 (durable, recoverable audit) and Track-B issues #46/#45/#27/#26/
  #25 were not touched by this pass.

**Decision:** the `next@15.5.18` lockfile bump and the runtime-stage
npm/corepack/yarn removal in `services/admin-portal/Dockerfile` are kept.
`scripts/ci/supply_chain_scan.sh astradesk:ci-js` now **passes** (exit 0).

## Follow-up: Java image recheck — new findings discovered, out of scope for this pass

The prior pass's Java scan had been interrupted (Ctrl+C) before producing a
result, leaving `astradesk:ci-java`'s actual gate status unknown. This pass
re-ran it to completion, as instructed, strictly as a **status recheck** —
this pass's brief provided detailed, prescriptive remediation rules for the
JS/Node ecosystem only (target version selection, lockfile-only update
command, runtime-stage hardening approach) and gave no equivalent
remediation instructions for the Java/Gradle ecosystem, framing the Java
step only as "rechecked" / "final Java status still needs to be rechecked."

### Result: FAILED — 28 new HIGH/CRITICAL findings

`docker build -f services/ticket-adapter-java/Dockerfile -t astradesk:ci-java
.` (cache hit, no Java/Gradle source changed) followed by
`scripts/ci/supply_chain_scan.sh astradesk:ci-java` →
`supply_chain_scan.sh: astradesk:ci-java FAILED — unaccepted reachable
HIGH,CRITICAL finding(s).` (`java_scan_rc=1`). Full JSON evidence captured at
`audit/evidence/40_trivy_ticket_adapter_java.json`.

**`app/app.jar` (Spring Boot fat jar) — 21 findings, 20 HIGH / 1 CRITICAL:**

| Library | Installed | Fix floor | Advisories |
|---|---|---|---|
| `com.fasterxml.jackson.core:jackson-databind` | 2.17.3 | 2.18.8 | CVE-2026-54512, CVE-2026-54513 |
| `io.netty:netty-codec` | 4.1.116.Final | 4.1.133.Final | CVE-2026-42583 |
| `io.netty:netty-codec-dns` | 4.1.116.Final | 4.1.133.Final | CVE-2026-42579 |
| `io.netty:netty-codec-http` | 4.1.116.Final | 4.1.132.Final | CVE-2026-33870, CVE-2026-42584, CVE-2026-42587 |
| `io.netty:netty-codec-http2` | 4.1.116.Final | 4.1.124.Final | CVE-2025-55163, CVE-2026-33871, CVE-2026-42587 |
| `io.netty:netty-handler` | 4.1.116.Final | 4.1.118.Final | CVE-2025-24970, CVE-2026-44249, CVE-2026-45416, CVE-2026-50010 |
| `io.netty:netty-resolver-dns` | 4.1.116.Final | (see advisory) | CVE-2026-45674, CVE-2026-47691 |
| `org.springframework.boot:spring-boot` | 3.3.7 | 3.3.11 | CVE-2025-22235, CVE-2026-40973 |
| `org.springframework.security:spring-security-crypto` | 6.3.6 | 6.3.8 | CVE-2025-22228 |
| `org.springframework.security:spring-security-web` | (Boot-managed) | 6.5.9 | **CVE-2026-22732 (CRITICAL)** |
| `org.springframework:spring-core` | 6.1.16 | 6.2.11 | CVE-2025-41249 |

All of the above are versions the Spring Boot Gradle plugin's dependency-
management BOM resolves transitively from `org.springframework.boot:spring-
boot` (declared in `services/ticket-adapter-java`'s Gradle build) — none are
directly pinned in `build.gradle.kts` today, so remediation is most likely a
Spring Boot BOM version bump, possibly combined with explicit per-library
overrides if the target Boot line doesn't itself raise Netty/Jackson/
Spring Security far enough (the same kind of resolver-chain investigation
`fastapi`/`starlette` needed in the Python remediation above).

**`usr/bin/pebble` (Go binary bundled inside the `eclipse-temurin` base
image, not installed by this project's own Dockerfile) — 7 findings, all
HIGH:**

| Library | Installed | Fix floor | Advisories |
|---|---|---|---|
| `golang.org/x/net` | v0.40.0 | 0.53.0–0.55.0 | CVE-2026-25681, CVE-2026-27136, CVE-2026-33814, CVE-2026-39821, CVE-2026-42502 |
| `stdlib` (Go) | v1.26.3 | 1.25.11 / 1.26.4 | CVE-2026-27145, CVE-2026-42504 |

`pebble` is a Let's-Encrypt-style ACME test-CA binary bundled by the
`eclipse-temurin@sha256:d2b9f8f...` image maintainers; `services/ticket-
adapter-java/Dockerfile`'s `ENTRYPOINT ["java","-jar","app.jar"]` never
invokes it. This is architecturally the same category as the Debian OS
base-image findings already dispositioned above for the Python image
(unreachable-from-the-shipped-application, base-image-bundled payload) —
but confirming that disposition (or, alternatively, removing `pebble` from
the runtime image the way this pass removed npm/corepack/yarn from
`astradesk:ci-js`) requires its own investigation and was not attempted
here.

### Why this was not remediated in this pass

1. This pass's brief supplied nine detailed, prescriptive implementation
   rules for the Node/JS remediation and none for Java — the Java step was
   scoped explicitly as a recheck of a previously-interrupted scan, not a
   remediation mandate.
2. `spring-security-web`/`spring-security-crypto` sit directly in the
   security-dependency surface this branch's instructions fence off
   ("do not refactor auth/OIDC/RBAC"). A pure dependency-version bump (no
   code change) would likely satisfy that boundary — the earlier
   `cryptography`/`python-jose` bumps in this same document's Python
   follow-up did exactly that on the OIDC path — but the exact target
   versions, the Spring Boot BOM cascade, and full regression coverage
   deserve the same single-variable, fully-tested treatment every other
   remediation in this document received, not a same-pass addition bolted
   onto a JS-scoped brief with no equivalent instructions.
3. Expanding scope here unilaterally would break the bounded-pass discipline
   this entire document follows (one ecosystem/library group per pass, full
   verification evidence per pass).

**Decision:** left `astradesk:ci-java` unmodified. `scripts/ci/
supply_chain_scan.sh astradesk:ci-java` **fails** (`java_scan_rc=1`), and
therefore the combined-image gate (`astradesk:ci-python astradesk:ci-java
astradesk:ci-js`) also **fails** (`final_scan_rc=1`) — Java, not JS, is now
the sole blocker. This is a newly-discovered, real, reachable finding set
(for `app.jar`) plus a base-image-bundled finding set (for `pebble`), not an
oversight, and is recommended as its own dedicated, bounded follow-up pass:
investigate the Spring Boot BOM-managed version chain, bump
`org.springframework.boot` (and any library it doesn't itself raise far
enough) in `build.gradle.kts`, run `./gradlew check` plus the full
`ticket-adapter-java` test suite, and separately evaluate `pebble`'s
reachability/removability the same way the Debian OS packages and the JS
image's npm/corepack/yarn payload were each evaluated above.

## Follow-up: Java image remediation (Spring Boot/Netty/Jackson BOM bump + `pebble` removal)

This is the dedicated follow-up pass recommended immediately above. Scoped
strictly to `astradesk:ci-java`: Gradle dependency/BOM declarations and one
runtime-stage `Dockerfile` line only. No Python or JS changes were made, no
Gradle wrapper change was needed (stayed on Gradle 9.2.0), Java stayed at 21,
and no application code was touched (see the pre-existing-defect finding
below for why one tempting code change was deliberately **not** made).

### Investigation: confirming the BOM-managed version chain

`services/ticket-adapter-java/build.gradle.kts` declares no direct version
for any of the flagged libraries — `spring-boot-starter-webflux/actuator/
validation/security/oauth2-resource-server/data-r2dbc` all resolve through
the Spring Boot Gradle plugin's own dependency-management BOM, version
pinned once, at the root, in `build.gradle.kts`
(`id("org.springframework.boot") version "3.3.7"`). Since Java wasn't
runnable locally with a real JDK (the host has a JRE 21 — confirmed via
`./gradlew javaToolchains`, `Is JDK: false` — and only a JDK 25, not JDK 21),
every Gradle command in this pass ran inside the exact pinned
`gradle@sha256:f73b9e12248ea459a1118f40da095c5305e90e2ebb22b790bcf0bfb9fcb1e39b`
image the project's own Dockerfile already uses (`--user 1000:1000`, a
persisted `GRADLE_USER_HOME` to avoid re-downloading the distribution per
invocation), matching the exact same pattern used for Node in the prior JS
pass.

`./gradlew :services:ticket-adapter-java:dependencies --configuration
runtimeClasspath` (pre-change) confirmed every flagged package's exact
managed version and confirmed the resolution path runs entirely through the
Spring Boot BOM (`spring-boot:3.3.7`, `spring-security-*:6.3.6`,
`spring-core:6.1.16`, `netty-*:4.1.116.Final`, `jackson-databind:2.17.3` —
all exactly matching the Trivy-reported `InstalledVersion`s).

### Determining the target Spring Boot version — verified, not assumed

Cross-referencing every fix-floor in `audit/evidence/40_trivy_ticket_adapter_java.json`
(re-parsed with the task's own inspection snippet) against real Maven
Central metadata (`curl` against `maven-metadata.xml` and the published
`spring-boot-dependencies` POM — not memorized version numbers) established:

- `CVE-2026-40973` (spring-boot) has **no fix in the 3.3.x or 3.4.x line** —
  its `FixedVersion` list is only `4.0.6, 3.5.14`. This makes **3.5.14** the
  lowest Spring Boot version, on the 3.x major line, that clears both
  `spring-boot` CVEs (the smallest change that doesn't jump to Boot 4.0, a
  major-version line with its own breaking changes).
- `CVE-2026-22732` (`spring-security-web`, the CRITICAL finding) similarly
  has **no fix before 6.5.9** — 6.3.x/6.4.x are not listed as fixed.

Fetched `spring-boot-dependencies-3.5.14.pom` directly from Maven Central to
check what that specific patch manages, rather than assuming a newer Boot
line clears everything:

| Managed by Boot 3.5.14 | Version | Clears the reported floor? |
|---|---|---|
| `spring-framework.version` | 6.2.18 | Yes (floor 6.2.11) |
| `spring-security.version` | 6.5.10 | Yes (floor 6.5.9 CRITICAL, and 6.3.8 for the crypto CVE) |
| `jackson-bom.version` | 2.21.2 | **No** — the 2.21.x line's own fix floor is 2.21.4 |
| `netty.version` | 4.1.132.Final | **No** — reported floors range 4.1.133.Final–4.1.135.Final |

This is the precise situation the task's suggested remediation approach
anticipated: Spring Boot's own BOM bump clears Spring Security and Spring
Core, but **not** Jackson or Netty, because Boot 3.5.14 selects a patch
level within each line that itself predates that specific CVE's fix.

### Changes made

1. **`build.gradle.kts` (root)** — bumped the Spring Boot plugin version:
   `id("org.springframework.boot") version "3.3.7"` → `"3.5.14"`.
   `io.spring.dependency-management` stayed at `1.1.7` (version-independent
   of the Boot line; resolution proved it still works correctly).
2. **`services/ticket-adapter-java/build.gradle.kts`** — added exactly two
   narrow BOM property overrides (the mechanism the `io.spring.dependency-
   management` plugin documents for exactly this situation), placed just
   before the `dependencies {}` block:

   ```kotlin
   extra["jackson-bom.version"] = "2.21.4"
   extra["netty.version"] = "4.1.135.Final"
   ```

   Both target versions were confirmed to exist on Maven Central
   (`jackson-databind`, `jackson-bom`, and `netty-handler` `maven-metadata.xml`)
   before use. `4.1.135.Final` is the binding floor across all nine
   Netty-family findings (`netty-handler`/`netty-resolver-dns` have no fix
   before `4.1.135.Final`; every other Netty module's floor is at or below
   that). No other dependency declaration was touched; React/Python/JS were
   not touched; the Gradle wrapper was not touched (stayed on 9.2.0, already
   comfortably newer than Spring Boot 3.5.x requires).

### Verification: every managed version re-checked via `dependencyInsight`, not assumed

Re-ran `dependencyInsight` for every flagged package after the change and
confirmed a single, final, "selected by rule" resolution for each — not just
a hopeful reading of the requested-vs-resolved arrows in the raw tree output:

| Package | Resolved version | Floor required |
|---|---|---|
| `spring-boot` | 3.5.14 | 3.5.14 |
| `spring-security-web` | 6.5.10 | 6.5.9 (CRITICAL) |
| `spring-security-crypto` | 6.5.10 | 6.3.8 |
| `spring-core` | 6.2.18 | 6.2.11 |
| `jackson-databind` | 2.21.4 | 2.21.4 |
| `netty-codec` | 4.1.135.Final | 4.1.133.Final |
| `netty-codec-dns` | 4.1.135.Final | 4.1.133.Final |
| `netty-codec-http` | 4.1.135.Final | 4.1.133.Final |
| `netty-codec-http2` | 4.1.135.Final | 4.1.133.Final |
| `netty-handler` | 4.1.135.Final | 4.1.135.Final |
| `netty-resolver-dns` | 4.1.135.Final | 4.1.135.Final |

Every flagged package clears its required floor. `dependencyInsight` for
`netty-handler`, `netty-resolver-dns`, `netty-codec`, and `netty-codec-dns`
each explicitly showed `(selected by rule)` at `4.1.135.Final`, confirming
the `netty.version` override — not an incidental transitive bump — is what
resolved them.

### `/usr/bin/pebble` remediation

Per the task's ordered remediation rules:

1. **Digest refresh check first:** `docker buildx imagetools inspect
   eclipse-temurin:21-jre` resolves to
   `sha256:d2b9f8f12212cadcfdf889461531784e8fd097feade954d65b31ee7a71c473ec`
   — byte-identical to the digest already pinned in
   `services/ticket-adapter-java/Dockerfile`. Same "already latest, no
   newer digest exists" outcome as the Python and Node base images in
   earlier passes; a digest bump cannot clear this finding.
2. **Reachability check:** `docker run --rm --entrypoint sh astradesk:ci-java
   -c "ls -la /usr/bin/pebble; grep -rl pebble /usr/local/bin ..."` confirmed
   the binary exists (9.9 MB, root-owned) but is referenced by **no** script
   anywhere in the image, and the image's own `Config.Entrypoint` is exactly
   `["java","-jar","app.jar"]` — `pebble` (a Go ACME test-CA binary the
   `eclipse-temurin` maintainers bundle for their own testing) is never
   invoked by this service.
3. **Removal applied:** added `rm -f /usr/bin/pebble` to the existing `RUN
   groupadd && useradd && chown` step in the Dockerfile's single runtime
   stage (merged into that RUN rather than added as a separate layer, same
   pattern as the JS Dockerfile's npm/corepack/yarn removal). No
   `.trivyignore` entry was needed — the task's fallback-to-suppression rule
   only applies "if removal is not possible," which was not the case here.

### Java tests

`./gradlew :services:ticket-adapter-java:test --no-daemon` (run inside the
same pinned Gradle/JDK-21 image) — **BUILD SUCCESSFUL**, 6 tests across
`TicketControllerTest` and its two `@Nested` classes (`CreateTicketTests`,
`GetTicketTests`), 0 failures, 0 errors (confirmed via the JUnit XML
`test-results`, not just the Gradle summary line). The only compiler output
was four pre-existing `@MockBean`-deprecation warnings (Spring Boot 3.4+
deprecated `@MockBean` in favor of `@MockitoBean`; this is an upstream
deprecation notice unrelated to this pass's changes, not a new warning it
introduced, and does not fail the build).

### Proof — image rebuild and Trivy gate

1. `docker build --no-cache -f services/ticket-adapter-java/Dockerfile -t
   astradesk:ci-java .` — succeeded; the `rm -f /usr/bin/pebble` layer added
   0.2s.
2. `scripts/ci/supply_chain_scan.sh astradesk:ci-java` →
   `supply_chain_scan.sh: astradesk:ci-java PASSED.` — **exit 0.** Trivy's
   table output shows `astradesk:ci-java (ubuntu 26.04) | ubuntu | 0` and
   `app/app.jar | jar | 0`; `usr/bin/pebble` no longer appears as a scanned
   target at all, confirming physical removal.
3. Regenerated `audit/evidence/40_trivy_ticket_adapter_java.json` against
   the fixed image.
4. Runtime proof: `docker image inspect astradesk:ci-java --format
   '{{.Config.User}}'` → `10001:10001` (non-root preserved); `docker run
   --rm --entrypoint java astradesk:ci-java -version` →
   `openjdk version "21.0.11"` (Java 21 preserved, Temurin build); a direct
   `ls`/ `ENTRYPOINT` check inside the image confirmed `/usr/bin/pebble` is
   gone and `node`/`java` (respectively, per image) still resolve correctly.
5. **Final three-image gate:** `scripts/ci/supply_chain_scan.sh
   astradesk:ci-python astradesk:ci-java astradesk:ci-js` → all three
   `PASSED`, **`final_scan_rc=0`.**

### Pre-existing defect discovered by the container-startup smoke test — NOT remediated, out of scope

The task's required `timeout 20s docker run --rm astradesk:ci-java` smoke
test does not reach "starts, then fails/times out on external config" — it
fails almost immediately with:

```text
org.springframework.beans.factory.BeanDefinitionStoreException: Failed to
parse configuration class [com.astradesk.ticket.TicketApp]
Caused by: org.springframework.context.annotation.ConflictingBeanDefinitionException:
Annotation-specified bean name 'ticketController' for bean class
[com.astradesk.ticket.web.TicketController] conflicts with existing,
non-compatible bean definition of same name and class
[com.astradesk.ticket.http.TicketController]
```

**Proven pre-existing and unrelated to this pass's dependency changes** —
not asserted, empirically verified: `git stash`-ed both `build.gradle.kts`
changes, rebuilt `astradesk:ci-java` against the original, untouched Spring
Boot 3.3.7, and re-ran the identical smoke test. It produced the **exact
same** `ConflictingBeanDefinitionException`, with the Spring Boot banner
correctly showing `v3.3.7`. The stash was then popped and the fixed image
rebuilt again before continuing. This defect exists independently of any
Spring Boot/Netty/Jackson/Spring Security version and would have failed
identically the first time anyone ever booted the full, un-sliced
application context, at any point since `web/TicketController.java` was
added (`git log`: 2025-11-06, over a month after the original
`http/TicketController.java` from the 2025-10-03 initial project structure).

Root cause: two **complete, independently-routed, parallel implementations**
of the same `/api/tickets` REST surface coexist in the tree —
`com.astradesk.ticket.http.TicketController` (+ `http.TicketReq`,
`model.Ticket`, `repo.TicketRepo`) and `com.astradesk.ticket.web.TicketController`
(+ `web.dto.*`, `service.TicketService`, `web.TicketMapper`,
`repository.TicketRepository`). `TicketApp`'s default, unscoped
`@SpringBootApplication` component-scan picks up both; both are
`@RestController`-annotated with the identical default bean name
(`ticketController`, derived from the shared simple class name), which
Spring's `ClassPathBeanDefinitionScanner` correctly refuses to register
twice. The only existing test, `TicketControllerTest`, never caught this
because it uses `@WebFluxTest(controllers = TicketController.class)` — a
*sliced* test context that loads only the explicitly-imported
`http.TicketController`, never performing a full component scan that would
exercise both.

**Why this was not fixed here, even though it blocks the literal smoke-test
step:** resolving it requires deciding which controller is authoritative,
and that decision is security-relevant, not cosmetic. `SecurityConfig`
(`@EnableWebFluxSecurity`) enforces only `.anyExchange().authenticated()`
globally — no centralized role-based rule. The **only** role-based
restriction on the ticket-listing endpoint
(`hasRole('SUPPORT_AGENT') or hasRole('ADMIN')`) exists as a
`@PreAuthorize` annotation on `http.TicketController` alone;
`web.TicketController` carries no method-level `@PreAuthorize` at all. Removing
the `http` package (the naive fix, and the one the newer, better-layered
`web`/`service`/`repository` stack would suggest) would silently drop that
RBAC restriction unless `SecurityConfig` were also extended — squarely
inside this task's own "do not refactor auth/OIDC/RBAC" exclusion. Removing
the `web` package instead would delete the newer service-layer architecture
and its only `PUT` (update) endpoint, and contradicts `TicketApp`'s own
`databaseProbe` bean, which is already wired to the newer
`repository.TicketRepository`. Neither direction is a "minimal compatibility
fix" — both require an application-owner decision this pass does not have
the authority or context to make safely. Left both files untouched.

**Why this does not block the Trivy gate or this pass's goal:** Trivy scans
image filesystem contents (installed JAR versions) for known-vulnerable
*packages*, not application wiring — `java_scan_rc=0` and `final_scan_rc=0`
are unaffected by this defect. The task's own unacceptable-outcomes list for
the smoke test (`Missing Java runtime`, `Missing jar`,
`ClassNotFoundException`/`NoClassDefFoundError` *caused by the dependency
update*) does not name this failure mode, and it is now proven not to be
caused by the dependency update. Recommended as a separate, dedicated
follow-up issue — scoped to a deliberate decision about which
`TicketController` implementation is authoritative, with `SecurityConfig`
updated to preserve the `SUPPORT_AGENT`/`ADMIN` role restriction regardless
of which implementation wins, before any code is deleted.
