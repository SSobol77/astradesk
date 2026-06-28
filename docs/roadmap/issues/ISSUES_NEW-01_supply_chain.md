<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: docs/roadmap/issues/ISSUES_NEW-01_supply_chain.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# ISSUES_NEW-01 — Dependency & supply-chain remediation (NEW)

- **Track / Milestone**: A / `v0.3.1`
- **Type**: NEW
- **Workhorse principle**: Security (good-sense)
- **GA-gating**: yes for reachable Critical/High; full SBOM/sign pipeline is Track B
- **Audit anchors**: §3.3, §7; `audit/evidence/19_pip_audit.txt`; `98_ci_stage_map.txt`
- **Depends on**: NEW-02 (a reproducible image to scan)

## Problem (current evidence)
`pip-audit` reports 102 known vulnerability records across 23 installed packages; GitHub CI has no dependency/image scan or SBOM gate. The locked environment does not meet the declared "no critical/high vulnerability" criterion.

## Industry analog & childhood disease
Python/ML stacks accumulate large transitive advisory counts; teams either ignore them or attempt a blind "update everything" that breaks the resolver. The disease is **treating a raw advisory count as either irrelevant or as a blocking wall, instead of triaging by reachability.** We immunize with reachability triage + a scanning gate that tracks accepted risk with expiry.

## Target contract (invariants)
- **INV-SC-1**: Every advisory is dispositioned: remediated, not-present-in-runtime-image, or accepted-with-expiry + justification.
- **INV-SC-2**: No **reachable** Critical/High advisory remains unaccepted before the Workhorse v1 gate.
- **INV-SC-3 (INV-FAIL-CLOSED)**: CI dependency/image scan fails the build on a new unaccepted reachable Critical/High.
- **INV-SC-4**: Acceptances are time-boxed; an expired acceptance fails CI.

## Interface / design
- Triage matrix: advisory × present-in-runtime-image? × reachable? → disposition.
- CI gate: `pip-audit` + image scan (`grype`/`trivy`) with an allow-list file carrying expiry dates and justifications.
- (Track B handoff: SBOM via `syft`, signing, digest verification.)

## Failure modes & required behavior
| Failure | Required behavior |
| :--- | :--- |
| New reachable Critical/High introduced | CI fails |
| Advisory only in build stage, not runtime | Documented, not blocking |
| Acceptance past expiry | CI fails |
| Resolver conflict on remediation | Pin via tested constraint set, not blind upgrade |

## Acceptance criteria (Definition of Done)
- [ ] All 102 records dispositioned in a tracked triage file.
- [ ] Zero unaccepted reachable Critical/High.
- [ ] CI scan gate active and failing-closed on regression.
- [ ] Time-boxed acceptances with justification + expiry.

## Verification evidence (artifact)
Triage file; green scan-gate run; expiry-enforcement test.

## Out of scope
SBOM generation, cosign signing, digest-verified promotion (Track B B.1).
