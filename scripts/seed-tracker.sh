#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
# File: scripts/seed-tracker.sh
# Purpose: Idempotently seed AstraDesk tracker for the v0.3.1 Safety Core plan.
#   - additive milestone v0.3.1 (touches no historical milestone)
#   - labels (track-a/track-b/supply-chain)
#   - new issues with contract-file references
#   - retarget OPEN #28 to v0.3.1 (rescope)
#   - cross-link follow-ups on CLOSED #9/#16/#19 (never reopened)
#   - track tagging of existing issues
# Safe to re-run: every create is guarded; comments are posted at most once.
#
# Requires: gh (authenticated with repo write), jq.
# This script performs TRACKER writes only. It does NOT touch git history.
set -euo pipefail

REPO="${REPO:-SSobol77/astradesk}"
MILESTONE="v0.3.1 - Commercial Workhorse Hardening"
MILESTONE_DUE="2026-07-25T23:59:59Z"
ISSUES_DIR="docs/roadmap/issues"

command -v gh >/dev/null || { echo "FATAL: gh not found" >&2; exit 1; }
command -v jq >/dev/null || { echo "FATAL: jq not found" >&2; exit 1; }

log() { printf '  %s\n' "$*"; }

# --- helpers -----------------------------------------------------------------

ensure_label() {
  # ensure_label <name> <color> <description>
  local name="$1" color="$2" desc="${3:-}"
  if gh label list --repo "$REPO" --json name --jq '.[].name' | grep -qx "$name"; then
    log "label exists: $name"
  else
    gh label create "$name" --repo "$REPO" --color "$color" --description "$desc"
    log "label created: $name"
  fi
}

ensure_milestone() {
  # ensure_milestone <title> <due_on_iso> <description>
  local title="$1" due="$2" desc="$3"
  local num
  num="$(gh api "repos/$REPO/milestones?state=all&per_page=100" \
        --jq ".[] | select(.title==\"$title\") | .number" | head -n1)"
  if [[ -n "${num:-}" ]]; then
    log "milestone exists: $title (#$num)"
  else
    gh api "repos/$REPO/milestones" -X POST \
      -f title="$title" -f state=open -f due_on="$due" -f description="$desc" >/dev/null
    log "milestone created: $title"
  fi
}

issue_number_by_title() {
  # exact-title match across all states; prints number or empty
  local title="$1"
  gh issue list --repo "$REPO" --state all --search "in:title \"$title\"" \
    --json number,title --jq ".[] | select(.title==\"$title\") | .number" | head -n1
}

ensure_issue() {
  # ensure_issue <title> <milestone-title> <labels-csv> <body>
  local title="$1" ms="$2" labels="$3" body="$4"
  local num; num="$(issue_number_by_title "$title")"
  if [[ -n "${num:-}" ]]; then
    log "issue exists: #$num $title"
  else
    gh issue create --repo "$REPO" --title "$title" \
      --milestone "$ms" --label "$labels" --body "$body" >/dev/null
    log "issue created: $title"
  fi
}

comment_once() {
  # comment_once <issue-number> <marker> <body>  (marker must be embedded in body)
  local num="$1" marker="$2" body="$3"
  if gh issue view "$num" --repo "$REPO" --json comments \
       --jq '.comments[].body' 2>/dev/null | grep -qF "$marker"; then
    log "comment present on #$num (marker: $marker)"
  else
    gh issue comment "$num" --repo "$REPO" --body "$body" >/dev/null
    log "comment posted on #$num"
  fi
}

retarget_open_issue() {
  # retarget_open_issue <number> <milestone-title> <add-label>
  local num="$1" ms="$2" lbl="$3"
  gh issue edit "$num" --repo "$REPO" --milestone "$ms" --add-label "$lbl" >/dev/null
  log "retargeted #$num -> $ms (+$lbl)"
}

add_label() { gh issue edit "$1" --repo "$REPO" --add-label "$2" >/dev/null && log "labeled #$1 +$2"; }

# --- 1. labels ---------------------------------------------------------------
echo "[1/6] labels"
ensure_label track-a        0E8A16 "Commercial workhorse gate"
ensure_label track-b        1D76DB "Enterprise direction"
ensure_label supply-chain   B60205 "Dependency / supply-chain security"
# Guards for every label referenced by ensure_issue below. ensure_label is
# idempotent: pre-existing repo labels are detected and left untouched.
ensure_label security       D73A4A "Security and safety controls"
ensure_label authentication 5319E7 "Authentication, OIDC, JWT, identity"
ensure_label rbac           5319E7 "Role-based access control"
ensure_label devops         0E8A16 "Build, deployment, and infrastructure"
ensure_label testing        F9D0C4 "Tests, gates, and verification evidence"

# --- 2. additive milestone ---------------------------------------------------
echo "[2/6] milestone"
ensure_milestone "$MILESTONE" "$MILESTONE_DUE" \
"Track A gate to first commercial client: OIDC at active ingress, invariant per-tool RBAC on LLM+fallback paths, PII/egress boundary, durable audit, fail-closed OPA, secret removal, reachable-vuln remediation, reproducible build, executable integration gate. Additive; alters no historical milestone."

# --- 3. new v0.3.1 issues (reference contract files) -------------------------
echo "[3/6] v0.3.1 issues"
ensure_issue "Wire JWKS/OIDC at active ingress" "$MILESTONE" "security,authentication,track-a" \
"Hardening follow-up to #9. Contract: $ISSUES_DIR/ISSUES_009_oidc_ingress.md
Fail-closed JWKS; HS256 only behind explicit local mode. Enforces INV-DUAL-PATH identity."
ensure_issue "RBAC invariant on every side-effect path" "$MILESTONE" "security,rbac,track-a" \
"Follow-up to #16. Contract: $ISSUES_DIR/ISSUES_016_rbac_invariant.md
Deny-by-default; dual-path (LLM+fallback) negative matrix. Central INV-DUAL-PATH control."
ensure_issue "Durable, recoverable audit (JetStream)" "$MILESTONE" "security,track-a" \
"Follow-up to #19. Contract: $ISSUES_DIR/ISSUES_019_durable_audit.md
Ack-after-durable-write, DLQ, crash-recovery test."
ensure_issue "Dependency & supply-chain remediation" "$MILESTONE" "security,supply-chain,track-a" \
"NEW-01. Contract: $ISSUES_DIR/ISSUES_NEW-01_supply_chain.md
Reachability triage; CI scan gate fail-closed."
ensure_issue "Reproducible containers, valid Compose, one baseline" "$MILESTONE" "devops,track-a" \
"NEW-02. Contract: $ISSUES_DIR/ISSUES_NEW-02_reproducible_build.md
uv.lock builds, Python 3.13, non-root, pinned digests."
ensure_issue "Ingress PII/secret redaction & egress boundary" "$MILESTONE" "security,track-a" \
"NEW-04. Contract: $ISSUES_DIR/ISSUES_NEW-04_pii_egress_boundary.md
Redact-before-emit; egress allow-list."
ensure_issue "Verify Helm/Terraform/Istio deployability (remove UNVERIFIED)" "$MILESTONE" "devops,testing,track-a" \
"Consolidates residual validation from #5/#12/#15/#17: helm lint/template/install, terraform validate/plan, istioctl analyze + negative-connectivity."

# --- 4. retarget OPEN #28 (rescope) ------------------------------------------
echo "[4/6] retarget #28 (OPA)"
retarget_open_issue 28 "$MILESTONE" track-a
comment_once 28 "[seed-tracker:rescope-028]" \
"[seed-tracker:rescope-028] RESCOPE -> deployable fail-closed OPA + schema-hash pinning (v0.3.1). Contract: $ISSUES_DIR/ISSUES_028_opa_fail_closed.md. Advanced policy-authoring UX deferred to Track B."

# --- 5. follow-up cross-links on CLOSED issues (never reopened) ---------------
echo "[5/6] follow-up comments on closed #9/#16/#19"
comment_once 9  "[seed-tracker:followup-9]" \
"[seed-tracker:followup-9] Residual hardening tracked as new v0.3.1 issue 'Wire JWKS/OIDC at active ingress'. #9 stays closed (original deliverable shipped)."
comment_once 16 "[seed-tracker:followup-16]" \
"[seed-tracker:followup-16] Residual hardening tracked as new v0.3.1 issue 'RBAC invariant on every side-effect path'. #16 stays closed."
comment_once 19 "[seed-tracker:followup-19]" \
"[seed-tracker:followup-19] Residual hardening tracked as new v0.3.1 issue 'Durable, recoverable audit'. #19 stays closed (subscriber exists; durability is new scope)."

# --- 6. track tagging + Track B new issues -----------------------------------
echo "[6/6] track tagging + Track B issues"
for i in 18 21 23 24; do add_label "$i" track-a; done
for i in 25 26 27;    do add_label "$i" track-b; done

ensure_issue "API implementation-contract conformance" "v0.4.0 - AI-Powered Enhancements" "track-a" \
"NEW-03. Contract: $ISSUES_DIR/ISSUES_NEW-03_contract_conformance.md
Gateway route /v1/run vs docs; Admin API structural diff (42 path-templates, 2 extra ops)."
ensure_issue "RAG/embedding isolation & SLO qualification" "v0.5.0 - Enterprise-Grade Features" "track-b" \
"NEW-05. Contract: $ISSUES_DIR/ISSUES_NEW-05_rag_isolation_slo.md
Split embedding from Gateway; bounded RPC; load/fault-injection SLO gate."
ensure_issue "Backup/restore & DR evidence (RPO/RTO)" "v0.6.0 - Advanced Features and Polish" "track-b" \
"NEW-06. Contract: $ISSUES_DIR/ISSUES_NEW-06_backup_restore_dr.md
Executed restore drills; measured RPO/RTO; runbook with decision authority."

echo "Done. Re-running this script is safe (idempotent)."
