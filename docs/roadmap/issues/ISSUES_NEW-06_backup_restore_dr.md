<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: docs/roadmap/issues/ISSUES_NEW-06_backup_restore_dr.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# ISSUES_NEW-06 — Backup/restore & disaster-recovery evidence (NEW)

- **Track / Milestone**: B / `v0.6.0`
- **Type**: NEW
- **Workhorse principle**: Operational resilience (enterprise direction)
- **GA-gating**: GA-direction (not the Workhorse v1 gate)
- **Audit anchors**: §8; `docs/operations.md:360-390`; relates to ISSUE 019 (durable audit) and issue #24 (alerts)
- **Depends on**: ISSUE 019 (audit durability), NEW-02 (reproducible infra)

## Problem (current evidence)
Disaster-recovery content is prose without executable restore procedures or drill results. There is no documented, tested backup/restore for Postgres (agent memory + RAG/pgvector state) or audit storage, and no measured RPO/RTO or named decision authority.

## Industry analog & childhood disease
Teams document a DR plan, schedule backups, and never test a restore — then discover during a real incident that the backup is unrestorable, the extension/state is incomplete, or nobody is authorized to trigger failover. The disease is **"DR on paper"**: backups that were never proven to restore, with unknown recovery time. We immunize by requiring an **executed, timed restore drill** as the acceptance evidence, not a written procedure.

## Target contract (invariants)
- **INV-DR-1**: Every stateful store (Postgres memory, pgvector RAG state, audit sink) has a backup whose **restore is executed and verified**, not merely scheduled.
- **INV-DR-2**: Restore is idempotent and produces a verifiable post-restore integrity check (row/vector/audit counts and a functional probe).
- **INV-DR-3**: Measured **RPO** (max data-loss window) and **RTO** (restore duration) are recorded from a real drill.
- **INV-DR-4**: pgvector extension/state restores correctly on the pinned image (ties to NEW-02 baseline).
- **INV-DR-5**: A named decision authority and runbook trigger exist for invoking recovery.

## Interface / design
- Backup jobs for Postgres (incl. pgvector) and audit storage with retention policy.
- A repeatable restore script run against an empty target; post-restore integrity probe.
- Drill procedure capturing timestamps to compute RPO/RTO; recorded in ops docs.

## Failure modes & required behavior
| Failure | Required behavior |
| :--- | :--- |
| Backup exists but restore fails | Drill fails; not "done" until restore verified |
| pgvector state missing post-restore | Integrity probe fails |
| Restore exceeds RTO target | Recorded as a gap with remediation |
| Audit gap exceeds RPO | Recorded; tie to ISSUE 019 durability |
| No authorized operator | Runbook defines authority before GA |

## Acceptance criteria (Definition of Done)
- [ ] Executed restore drill for Postgres + pgvector + audit storage on an empty target.
- [ ] Post-restore integrity probe passes (counts + functional check).
- [ ] Measured RPO/RTO recorded from the drill.
- [ ] Runbook with decision authority and trigger steps published.
- [ ] Restore verified on the pinned baseline image.

## Verification evidence (artifact)
Drill log with RPO/RTO timestamps; integrity-probe output; restore runbook.

## Out of scope
Multi-region active-active, automated failover orchestration, chaos-engineering program (future).
