# ISSUES_NEW-03 — API implementation-contract conformance (NEW)

- **Track / Milestone**: A / `v0.4.0`
- **Type**: NEW
- **Workhorse principle**: Trustworthy documentation
- **GA-gating**: yes — an integrator's generated client must match the running service
- **Audit anchors**: §4; §10; `docs/api.md:102-205`; `services/api-gateway/src/gateway/main.py:275-286`; `audit/evidence/72_admin_contract_diff.txt`; `services/admin-portal/scripts/check-openapi-sync.ts:53-70`
- **Depends on**: ISSUE 009 (auth shape affects documented operations), NEW-02 (reproducible env to regenerate in)

## Problem (current evidence)
Two contract truths diverge from implementation. (1) The public Gateway doc specifies `/v1/agents/run`; the active code exposes `/v1/run`. (2) The runtime Admin API exposes 76 operations vs 74 canonical; after parameter-name normalization it has two undocumented operations, and exact path templates differ for 42 canonical operations. The portal's generated-client check compares **file mtimes**, not regenerated content, so a touched file passes without matching the spec.

## Industry analog & childhood disease
OpenAPI-first projects routinely let the spec become aspirational: the document and the generated SDK drift from the handlers, and "sync" checks verify timestamps instead of content. Integrators then build against a contract the server does not honor. The disease is **a contract that is asserted, not enforced.** We immunize by generating the runtime schema in CI and structurally diffing it against the source of truth, and by regenerating clients to a temp dir and requiring a zero diff.

## Target contract (invariants)
- **INV-API-1**: One public Gateway route is canonical; docs, spec, tests, and code agree on it.
- **INV-API-2**: The runtime Admin schema is **structurally identical** to canonical `1.2.0`: same operation set, parameter names, path templates, request/response schemas, and status codes.
- **INV-API-3 (INV-FAIL-CLOSED)**: A structural diff between runtime schema and canonical spec fails CI (treated as a breaking-contract event).
- **INV-API-4**: Generated portal client is verified by regenerate-to-temp + zero-diff, never by mtime.

## Interface / design
- CI step emits the runtime OpenAPI from the live app and diffs it (operations/params/schemas/status) against `openapi/astradesk-admin.v1.yaml`.
- Route-conformance test asserts the implemented Gateway path equals the documented one.
- Replace `check-openapi-sync.ts` mtime logic with deterministic regeneration into a scratch dir + `diff`.

## Failure modes & required behavior
| Failure | Required behavior |
| :--- | :--- |
| Runtime schema adds/removes an operation vs canonical | CI fails (breaking contract) |
| Path-template / param-name drift | CI fails with the specific diff |
| Gateway route ≠ documented route | Route-conformance test fails |
| Generated client touched but content-stale | Regenerate-diff fails |

## Acceptance criteria (Definition of Done)
- [ ] Canonical Gateway route chosen; docs/spec/tests/code aligned; route-conformance test passes.
- [ ] Runtime-vs-canonical structural diff is clean (2 extra ops + 42 path-template diffs resolved).
- [ ] CI structural-diff gate active and failing-closed on drift.
- [ ] Portal client check is regenerate-to-temp + zero-diff.

## Verification evidence (artifact)
Clean structural-diff report; route-conformance test log; regenerate-diff CI output.

## Out of scope
Spec redesign / new endpoints; API versioning beyond the existing `1.2.0` contract axis.
