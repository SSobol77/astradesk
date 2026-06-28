# ISSUES_NEW-02 — Reproducible containers, valid Compose, one baseline (NEW)

- **Track / Milestone**: A / `v0.3.1`
- **Type**: NEW
- **Workhorse principle**: Simplicity / easy implementation
- **GA-gating**: yes — an integrator must stand the stack up from tracked sources
- **Audit anchors**: §3.1, §3.3, §6, §7; `audit/evidence/40_compose.txt`; `95_hypothesis_checks.txt`; `73_source_path_checks.txt`
- **Depends on**: none; **blocks** NEW-01 (need a reproducible image to scan) and the integration gate

## Problem (current evidence)
Full Compose validation fails (`mcp` depends on profiled-out `kb-service`). Dev API/domain Dockerfiles use Python 3.11, use `pip`, and copy non-existent `requirements.txt`. Package metadata is uniformly 3.13 but five images are 3.11. Several runtime Dockerfiles have no final `USER`. Dev/prod DB+cache baselines diverge with floating tags.

## Industry analog & childhood disease
First-generation Helm/Compose/K8s setups ship root containers, floating `:latest`/`:8-alpine` tags, secrets in values, and Dockerfiles that drift from the real dependency manifest. The disease is **"works on my machine" packaging** — non-reproducible images that an integrator cannot rebuild. We immunize by building only from `pyproject.toml`/`uv.lock`, pinning by digest, and running non-root.

## Target contract (invariants)
- **INV-BUILD-1**: Every Python image builds solely from `pyproject.toml` + `uv.lock` (no `pip`, no `requirements.txt`).
- **INV-BUILD-2**: One Python baseline — **3.13 latest patch** — across all images and CI.
- **INV-BUILD-3**: Every runtime image declares a fixed numeric **non-root** `USER`; read-only root FS where feasible.
- **INV-BUILD-4**: `docker compose -f docker-compose.yml config` and the dev variant both validate.
- **INV-BUILD-5**: Base images, DB, and cache are pinned by digest; dev and prod share the same engine baseline (pgvector image for dev).

## Interface / design
- Multi-stage uv-based Dockerfile pattern (builder installs from lock; runtime is slim, non-root).
- Fix the Compose profile dependency (`mcp`/`kb-service`) so the graph is valid.
- Pin `postgres`/`pgvector`/`redis` by digest; verify the pgvector migration on an empty volume.

## Failure modes & required behavior
| Failure | Required behavior |
| :--- | :--- |
| `compose config` invalid | CI fails; fix profile/dependency semantics |
| Image built with `pip`/missing requirements | Build fails; only lock-based path allowed |
| Root container | Image lint fails (non-root assertion) |
| Floating tag | CI rejects unpinned base/DB/cache references |
| pgvector migration on selected dev image fails | Use pinned pgvector image; verified on empty volume |

## Acceptance criteria (Definition of Done)
- [ ] Both Compose files validate in CI.
- [ ] All Python images build from `uv.lock` on Python 3.13, non-root.
- [ ] Base/DB/cache pinned by digest; dev/prod baselines aligned.
- [ ] pgvector migration verified on a clean volume in CI.
- [ ] Non-root assertion test across tracked Dockerfiles.

## Verification evidence (artifact)
`docker compose config` pass logs; image build + non-root assertion; clean-volume migration run.

## Out of scope
Multi-arch build/push, SBOM/sign (Track B B.1); secret-reference wiring is shared with NEW-01/§7 secret removal.
