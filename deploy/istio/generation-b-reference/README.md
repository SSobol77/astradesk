<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: deploy/istio/generation-b-reference/README.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# Istio "Generation B" — reference only, not the active deployment path

The files in this directory are **not** applied by either tracked CI/CD
pipeline (`Jenkinsfile`, `.gitlab-ci.yml`) and are **not** part of the
canonical Istio configuration for AstraDesk. They are kept here for
reference only.

## Why this directory exists

`deploy/istio/` previously contained two independent, non-identical sets of
Istio manifests side by side at the same flat directory level: an older set
(namespace `astradesk-prod`) and this newer, numbered set (namespace
`astradesk`). Both validated successfully with `istioctl validate`, and
`kubectl apply -f deploy/istio/` would have applied both simultaneously into
two different namespaces in a real cluster — see
`audit/evidence/43_deployability_verification.md`'s "Istio dual-generation
inventory" section for the full comparison that led to this decision.

**Maintainer decision (issue #43):** the `astradesk-prod` generation
(the files directly under `deploy/istio/`) is canonical, because:

- Both executable deployment pipelines (`Jenkinsfile`, `.gitlab-ci.yml`)
  already reference namespace `astradesk-prod`.
- The canonical generation already routes all four services (`api`,
  `ticket-adapter`, `admin`, `auditor`); this directory's `VirtualService`
  (`41-virtualservice-astradesk-api.yaml`) only ever routed the API service.
- This directory's manifests were not referenced by any executable pipeline
  step — only by documentation.

These files were moved here, out of `deploy/istio/`'s flat top level,
specifically so `kubectl apply -f deploy/istio/` (non-recursive, exactly as
both tracked pipelines invoke it) no longer applies them.

## What is preserved here for future work

This generation includes two real, additive security improvements the
canonical generation does not have:

- `30-authorizationpolicy-namespace.yaml` — a Layer-7 `AuthorizationPolicy`
  restricting inbound traffic to same-namespace sources and the Istio
  ingress gateway's service account. The canonical generation has no
  `AuthorizationPolicy` at all today and relies on mTLS identity alone.
- `50-cert-manager-certificate.yaml` + `certs/` — a two-tier certificate
  strategy (public Let's Encrypt ACME for the external hostname, a separate
  internal CA for mesh-internal mTLS) rather than one self-signed
  certificate covering everything.

Porting these into the canonical generation is explicitly **out of scope**
for issue #43 and was not done as part of this canonicalization pass. It is
recommended as its own, separate, explicitly-scoped design issue — see
`audit/evidence/43_deployability_verification.md` for the full rationale.

## Do not

- Do not add these files back to `kubectl apply -f deploy/istio/`'s
  top-level scope without also completing the routing gap (no route exists
  here for `ticket-adapter`, `admin`, or `auditor`) and updating both
  tracked pipelines' namespace references.
- Do not delete this directory without deciding what, if anything, gets
  ported into the canonical generation first.
