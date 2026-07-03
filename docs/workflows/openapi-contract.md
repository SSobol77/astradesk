<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: docs/workflows/openapi-contract.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# OpenAPI Contract Update Workflow

> Canonical checklist for keeping the AstraDesk Admin API specification, generated client code, and CI guardrails in sync.

## When to use this workflow

Run this procedure **every time** you:

- add, rename, or remove endpoints in `openapi/astradesk-admin.v1.yaml`
- adjust schemas or parameters that affect the admin portal client
- change security requirements on Admin API operations (e.g. add/remove a `security:`
  block or edit `components.securitySchemes`, as NEW-SEC did when adding the
  `BearerAuth` requirement to previously-unprotected operations)
- regenerate OpenAPI-driven TypeScript helpers

This is the single source of truth for contract updates—link to it in pull requests whenever an API change ships.

---

## Prerequisites

- Node.js ≥ 22 with `npm` available locally (or Docker access to run the Node toolchain).
- Admin portal dependencies installed (`npm ci` inside `services/admin-portal`).
- CI configured with the **API contract sync** job (already enforced via `.github/workflows/ci.yml`).

Optional but recommended:

- Python + `uv` for backend tests.
- Docker if you need to rebuild containers before merging.

---

## Step-by-step procedure

1. **Edit the OpenAPI spec**
   ```bash
   $EDITOR openapi/astradesk-admin.v1.yaml
   ```
   Keep descriptions and tags updated; they drive generated metadata.

2. **Regenerate client artifacts**
   ```bash
   cd services/admin-portal
   npm run openapi:gen
   ```
   This rewrites:
   - `src/api/types.gen.ts`
   - `src/api/spec-operations.gen.ts`
   - any additional files emitted by the generator script

3. **Verify drift guard passes**
   ```bash
   npm run openapi:check
   ```
   The command fails if artifacts are stale or missing.

4. **Verify the contract version/shape guard**
   ```bash
   bash scripts/check-openapi-version.sh
   ```
   Confirms `openapi.version` (`3.1.0`) and `info.version` (`1.2.0`) are unchanged, and
   that `services/admin-portal/openapi/OpenAPI.yaml` (if present as a real file rather
   than a symlink) matches the canonical spec. Run this whenever the spec changes,
   including security-only changes that don't touch schemas.

5. **Run quality gates locally**
   ```bash
   npm run lint
   npm run typecheck
   npm run test
   ```
   _Tip:_ Without a local Node install you can use Docker:
   ```bash
   docker run --rm -v "$PWD":/app -w /app node:22 npm run typecheck
   ```

6. **Stage and commit related changes together**
   ```bash
   git add openapi/astradesk-admin.v1.yaml \
           services/admin-portal/src/api/types.gen.ts \
           services/admin-portal/src/api/spec-operations.gen.ts \
           services/admin-portal/scripts/*openapi*.ts
   git commit -m "docs: update admin API contract"
   ```
   Include any other touched files (e.g., UI updates) in the same changeset to keep history cohesive.

7. **Push and open a pull request**
   - Reference this workflow in the PR description.
   - Ensure branch protection requires the **API contract sync** job to pass on CI.

---

## Environment & tooling notes

- **Node provisioning:** use `nvm`, `asdf`, or the project-provided Docker image to match `NODE_VERSION=22` defined in CI. Do **not** rely on older runtimes.
- **Admin portal scripts:** both `scripts/openapi-generate.ts` and `scripts/check-openapi-sync.ts` locate the repo root automatically—run them only from within `services/admin-portal`.
- **CI enforcement:** `.github/workflows/ci.yml` contains an explicit “API contract sync” step. Merges into `main` are blocked if generated files differ from the specification.

---

## Troubleshooting

| Symptom | Resolution |
| --- | --- |
| `npm run openapi:gen` fails with “spec not found” | Ensure `ASTRA_OPENAPI_SPEC` is unset or points to `openapi/astradesk-admin.v1.yaml`. |
| `npm run openapi:check` reports stale files after regeneration | Re-run `openapi:gen`, then confirm git staged the regenerated files. |
| CI contract job fails on PR | Pull the latest main branch, re-run steps 2–4 locally, and recommit the regenerated artifacts. |

---

Following this checklist keeps the admin portal, API specification, and CI guardrails aligned, preventing contract drift from reaching production. Save this document as the authoritative reference for contract updates. 💼
