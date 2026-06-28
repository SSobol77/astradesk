<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: docs/roadmap/issues/ISSUES_028_opa_fail_closed.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# ISSUES_028 — Deployable fail-closed OPA + schema-hash pinning (RESCOPE of #28)

- **Track / Milestone**: A / `v0.3.1`
- **Type**: RESCOPE of open #28 (narrow to deployable, uniform enforcement)
- **Workhorse principle**: Security (good-sense)
- **GA-gating**: yes — policy must be a real, uniform boundary, not optional code
- **Audit anchors**: §7; §10; `services/api-gateway/src/gateway/orchestrator.py:173-179`; `mcp/src/gateway/config.py:41-47`; `mcp/src/gateway/gateway.py:87-180`
- **Depends on**: ISSUE 016 (RBAC choke point exists to attach policy to)

## Problem (current evidence)
The orchestrator calls OPA before LLM-planned tools, but: no OPA server/sidecar/bundle is tracked, fallback calls are not centrally policy-checked, and `schema_ref` is configuration metadata never compared against a caller schema hash at invoke. Policy exists as code, not as a deployable, uniform, fail-closed boundary.

## Industry analog & childhood disease
Early MCP/tool ecosystems suffered tool-poisoning (a tool's declared schema/description drifts from what it actually accepts) and "optional policy" that is present in code but absent in deployment. The disease is **policy and schema integrity that are advisory rather than enforced.** We immunize with a deployed fail-closed OPA and schema-hash negotiation that rejects mismatches.

## Target contract (invariants)
- **INV-OPA-1 (INV-FAIL-CLOSED)**: If the OPA endpoint is unavailable or returns no decision, the action is denied.
- **INV-OPA-2 (INV-DUAL-PATH)**: Both LLM-planned and fallback tool calls pass the same policy check.
- **INV-OPA-3**: Policy bundles are versioned and their version is recorded in the audit decision.
- **INV-SCHEMA-1**: Tool invocation carries a `schema_hash`; the gateway canonicalizes and hashes the declared schema and **rejects on mismatch**; both expected and received hashes are audited.

## Interface / design
- Tracked OPA workload (sidecar/deployment) + bundle directory; health-gated.
- Policy check moved to the shared invoke choke point from ISSUE 016 (so fallback is covered).
- `schema_hash` added to the MCP call contract; canonical JSON schema hashing; mismatch → reject.

## Failure modes & required behavior
| Failure | Required behavior |
| :--- | :--- |
| OPA endpoint down | Deny (fail-closed) + audit |
| Decision absent/ambiguous | Deny |
| Tool schema hash mismatch | Reject invocation + audit expected/received |
| Fallback path tool call | Same policy decision as LLM path |
| Bundle version unknown | Deny until a valid versioned bundle loads |

## Acceptance criteria (Definition of Done)
- [ ] OPA deployed and health-gated; bundle versioned.
- [ ] Bypass test: OPA down → side effects denied, not allowed.
- [ ] Dual-path test: fallback tool call is policy-checked identically.
- [ ] Schema-hash negotiation enforced; mismatch rejected with audit of both hashes.
- [ ] Decision + bundle version present in audit records.

## Verification evidence (artifact)
OPA-down bypass test log; schema-mismatch rejection test; dual-path policy test.

## Out of scope
Rich policy authoring UX, policy simulation/CI policy tests as a separate suite (Track B).
