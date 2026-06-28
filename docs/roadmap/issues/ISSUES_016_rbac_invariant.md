# ISSUES_016 — RBAC invariant on every side-effect path (RESCOPE of #16)

- **Track / Milestone**: A / `v0.3.1`
- **Type**: RESCOPE of closed #16
- **Workhorse principle**: Security (good-sense)
- **GA-gating**: yes — the single highest-impact control for client safety
- **Audit anchors**: §7 (Critical); `services/api-gateway/src/gateway/main.py:143-154`; `services/api-gateway/src/tools/ops_actions.py:77-119`; `services/api-gateway/src/tools/tickets_proxy.py:157-181`; `services/api-gateway/src/agents/base.py:279`
- **Depends on**: ISSUE 009 (identity)
- **Reinforced by**: ISSUE 028 (fail-closed OPA)

## Problem (current evidence)
RBAC is not invariant. The registry supports `allowed_roles`, but built-in tools are registered without roles. `restart_service` does a direct role check; `create_ticket` depends on an optional OPA client that the **keyword-fallback** registry execution never passes. A `write` tool can therefore execute without the documented per-tool role policy when the planner is bypassed.

## Industry analog & childhood disease
AutoGPT-era agents executed side effects with no authorization gate; later frameworks added RBAC on the "happy" LLM path but left tool-execution shortcuts (retries, keyword routing, direct registry calls) ungated. The disease is **authority that depends on which code path was taken.** We immunize by making authorization a property of the tool invocation itself, not of the planner.

## Target contract (invariants)
- **INV-RBAC-1 (INV-DUAL-PATH)**: Authorization is enforced at one choke point that **both** the LLM-planned and keyword-fallback paths must traverse. No tool executes outside it.
- **INV-RBAC-2**: Every tool declares `side_effect ∈ {read, write, execute}` and `allowed_roles` in registry metadata at registration; registration of a side-effect tool without roles fails fast.
- **INV-RBAC-3 (INV-FAIL-CLOSED)**: Unknown tool, missing metadata, or unavailable policy → deny.
- **INV-RBAC-4**: `write`/`execute` require an approval/change record id; absence → deny + audit.

## Interface / design
- Move authorization into the registry/orchestrator boundary so fallback execution cannot skip it; `agents/base.py` fallback calls the same gated invoke.
- Tool metadata schema extended: `{name, side_effect, allowed_roles, requires_approval}`.
- A startup invariant check enumerates registered tools and aborts if any `side_effect != read` lacks `allowed_roles`.

## Failure modes & required behavior
| Failure | Required behavior |
| :--- | :--- |
| Side-effect tool registered without roles | Startup aborts (catch at boot, not at call) |
| Unauthorized role invokes `write`/`execute` (LLM path) | Deny + audit |
| Same invocation via keyword-fallback | Identical deny + audit |
| `write` without approval record | Deny + audit |
| Policy backend unavailable | Deny (fail-closed), not allow |

## Acceptance criteria (Definition of Done)
- [ ] All built-in tools carry `side_effect` + `allowed_roles`.
- [ ] **Dual-path negative matrix**: for each `write`/`execute` tool × {LLM, fallback} × {authorized, unauthorized}, unauthorized is denied in every cell.
- [ ] Boot-time invariant test: registering a roleless side-effect tool aborts startup.
- [ ] Approval-record enforcement test for `write`/`execute`.
- [ ] CI regression test that fails if any side-effect tool lacks role metadata.

## Verification evidence (artifact)
Dual-path RBAC matrix test output; boot-invariant test log.

## Out of scope
Policy authoring/bundle distribution (ISSUE 028); fine-grained ABAC (Track B).
