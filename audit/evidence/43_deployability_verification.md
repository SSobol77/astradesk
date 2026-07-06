<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: audit/evidence/43_deployability_verification.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# Issue #43 — Helm/Terraform/Istio deployability verification

Status: **offline deployability validation passes for Helm, Terraform (root +
all 5 modules), and Istio; the maintainer has now chosen a canonical Istio
generation and this pass applied that decision; cluster/cloud-dependent
checks (`helm install`, `terraform plan`/`apply`, `istioctl analyze` against
a live mesh, the negative-connectivity test) were not performed and remain
out of reach without a provisioned environment.** Four real bugs were found
and fixed in the first #43 pass (two Helm, one Istio schema, one Istio
routing); a Terraform follow-up fixed the `eks` module/AWS-provider
incompatibility with a version-constraint addition. **This pass (the
canonicalization follow-up)** applied the maintainer's explicit decision —
"Generation A is canonical for #43" — by relocating the non-canonical
generation out of `kubectl apply -f deploy/istio/`'s reach, fixing stale
`infra/` Terraform paths in both tracked pipelines and their referencing
docs (including translated counterparts), and re-verifying the full offline
suite with zero regressions. See "Follow-up: canonicalization applied (this
pass)" below for the complete change list. **Issue #43 is still not closed
by this pass** — see "Decision: why #43 stays open" at the end of this
document; the remaining gap is entirely cluster/cloud-credential-gated
checks, not any further static/offline validation failure or open
architecture decision.

## Scope

Per issue #43's own title and `docs/roadmap/index.md` (Phase 2, item 4:
*"Deployment verified, not UNVERIFIED. Run `helm lint`/template/install,
`terraform validate`/plan, `istioctl analyze` + a negative-connectivity
test... (issues #5/#12/#15/#17 → RESCOPE)"*), this pass covers:

- Helm: `deploy/chart/`
- Terraform: `deploy/infra/` (root + 5 modules: `vpc`, `eks`, `rds-postgres`,
  `rds-mysql`, `s3`)
- Istio: `deploy/istio/` (both manifest generations found there, plus
  `certs/`)
- Compose/build baseline (already covered by issue #40/#41 work; re-run here
  to confirm this pass introduced no regression)

**Explicitly out of scope, found by the same file discovery but not part of
issue #43's Helm/Terraform/Istio title:** `deploy/openshift/` (OpenShift
Templates, issue #5) and `deploy/cm/` (Ansible/Puppet/Salt, config
management). Neither was touched or verified here.

## Tool availability

| Tool | Local result | Resolution |
|---|---|---|
| `helm version` | not installed | Ran via pinned `alpine/helm:3.15.3` image (matches the chart README's own stated prerequisite, "Helm 3.15.3 or higher") |
| `terraform version` | not installed | Ran via pinned `hashicorp/terraform:1.9` image (satisfies `required_version = ">= 1.7.0"` in `deploy/infra/main.tf`) |
| `kubectl version --client` | not installed | Ran via `bitnami/kubectl:latest` image |
| `istioctl version --remote=false` | not installed | Ran via pinned `istio/istioctl:1.22.3` image |
| `docker compose version` | v5.3.0 | already present |

No host system packages were installed; all four missing tools were run via
ephemeral, read-only-mounted (or scratch-copy-mounted, for Terraform — see
below) Docker containers, the same pattern already used for Node/Gradle in
prior passes on this branch's lineage.

## Helm verification

**Command:** `helm lint deploy/chart`; `helm template astradesk deploy/chart`

### Findings, before any fix

`helm lint` failed (`Error: 1 chart(s) linted, 1 chart(s) failed`) and `helm
template` failed outright (`Error: An error occurred while checking for
chart dependencies... found in Chart.yaml, but missing in charts/
directory: istio, cert-manager`) — i.e. the chart could not even render.
Three distinct, real bugs were found:

1. **Orphaned Helm-2-style dependency declaration blocked `helm
   template`/`helm install` entirely.** `deploy/chart/requirements.yaml`
   declared `istio` and `cert-manager` as chart dependencies. Helm 3 still
   honors `requirements.yaml` for backward compatibility (with a deprecation
   notice), but the referenced subcharts were never vendored under
   `charts/`, so `helm template`/`helm install` refused to proceed at all.
   `grep -rn "Subcharts\|\.Chart\.Dependencies\|istio\.\|cert-manager\."
   deploy/chart/` confirmed **zero** templates reference either subchart —
   the only real hits are a Pod annotation
   (`sidecar.istio.io/inject: "true"`) and README prose describing Istio and
   cert-manager as *separately* installed (`istioctl install`, `kubectl
   apply -f cert-manager.yaml`), matching how `deploy/istio/` actually
   works. Confirmed with the user before deleting a tracked file, then
   removed `deploy/chart/requirements.yaml`.
2. **`.Release.Namespace` used without root-context scoping inside a
   `range` block, in `templates/{deployment,service,hpa}.yaml`.** All three
   files iterate `{{- range $service := list "api" "ticketAdapter" "admin"
   "auditor" }}`, which rebinds `.` to each loop element (a plain string).
   `.Release.Namespace` then tries to evaluate `Release` on a string,
   failing with `can't evaluate field Release in type interface {}`. The
   same files already correctly use `$.Values`/`$service` (root- and
   loop-scoped) elsewhere — `.Release.Namespace` was the one place the `$`
   prefix was missing. Helm's renderer only ever surfaces the *first*
   template it fails on (confirmed empirically: `--show-only
   templates/deployment.yaml` and `--show-only templates/hpa.yaml` both
   still reported the error against `service.yaml`, since rendering is one
   combined pass), so fixing one occurrence in isolation would only have
   exposed the next. Fixed all three: `{{ .Release.Namespace }}` →
   `{{ $.Release.Namespace }}`.
3. **`astradesk-ticketAdapter` is not a valid Kubernetes object name.**
   Once (1) and (2) were fixed, `helm lint` surfaced a real (if
   warning-level) issue: `metadata.name: Invalid value:
   "astradesk-ticketAdapter"` — Kubernetes object names must be lowercase
   RFC 1123/DNS-1035; `ticketAdapter`'s uppercase `A` is rejected by the
   API server (this would not be caught by client-side dry-run tooling, and
   would only surface as a real, guaranteed apply-time failure). Kubernetes
   **label values** (unlike names) do permit mixed case, so `app:
   astradesk-{{ $service }}` labels/selectors were left untouched (both
   sides of every Service→Pod selector still match each other
   byte-for-byte). Fixed only the four `metadata.name`/`scaleTargetRef.name`
   occurrences using Sprig's `kebabcase` filter (`astradesk-{{ $service |
   kebabcase }}`), rather than renaming the `values.yaml` key itself —
   `ticketAdapter` is a documented, actively-used `--set` key in both
   `deploy/chart/deploy_chart_README.md` and the real `Jenkinsfile`
   (`--set ticketAdapter.image.repository=...`), so renaming the values
   schema would have broken that public interface for no benefit.
   Confirmed the project already uses `astradesk-ticket-adapter` as its
   real convention elsewhere (`deploy/openshift/ticket-adapter-template.yaml`
   already names it that way).
   **Consequence fixed in the same pass:** `deploy/istio/virtualservice.yaml`
   (see Istio section) referenced the old, now-corrected name
   (`host: astradesk-ticketAdapter`) as a routing destination; updated to
   `astradesk-ticket-adapter` to match.

### Result after fixes

```text
$ helm lint --strict deploy/chart
==> Linting deploy/chart
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed
```

```text
$ helm template astradesk deploy/chart
(renders cleanly, exit 0 — 4 Deployments, 4 Services, 4 HPAs, 1 Helm test Pod,
 all with valid lowercase names: astradesk-{api,ticket-adapter,admin,auditor})
```

**Helm render/lint passed.** `helm install`/`helm test` against a live
cluster were **not performed** — no cluster was provisioned or assumed.

**Findings documented but not fixed** (do not block rendering, so left as
observations rather than "structural errors" needing a fix):

- `deploy/chart/tests/test-api.yaml` and `deploy/chart/tests/test-hpa.yaml`
  live at the chart root (sibling to `templates/`), not under
  `templates/tests/`. Helm only treats files under `templates/` (recursively)
  as chart content — these two are silently **never rendered or run** by
  `helm test`, despite `deploy_chart_README.md`'s directory listing
  presenting them as if they lived under `templates/tests/` alongside the
  one file that actually does (`test-mtls.yaml`). Moving them was not
  attempted in this pass (a file relocation, i.e. delete-plus-create, raises
  the same "modifying tracked file layout" question already raised and
  resolved once this pass for `requirements.yaml`; better to let the
  maintainer decide in one pass rather than piecemeal).
- `deploy_chart_README.md` states chart "Version: 1.2.0" and "Dependencies:
  None"; the actual `Chart.yaml` says `version: 0.2.0`, and (before the fix
  above) a real `requirements.yaml` dependency block existed. The README is
  stale relative to the tracked chart. Not corrected here — general doc
  accuracy beyond deployability evidence is a larger edit than this pass's
  narrow verification mandate.

## Terraform verification

**Commands:** `terraform fmt -check -recursive`; `terraform init
-backend=false`; `terraform validate` — run against root (`deploy/infra/`)
and each of the 5 modules individually, per the task's "run validation per
module/root discovered" instruction. Terraform was run against a **scratch
copy** of `deploy/infra/` (not the tracked tree directly) so the
`.terraform/`/`.terraform.lock.hcl` caches `terraform init` creates never
touch the real working tree — the repository's `.gitignore` only excludes a
top-level `infra/.terraform/` pattern, which does not match the actual
`deploy/infra/` path (a separate pre-existing drift, not modified here since
it wasn't required to complete verification).

### `terraform fmt` — real, fixed

`terraform fmt -check -recursive -diff` failed (exit 3) on 5 files:
`main.tf`, `modules/eks/main.tf`, `modules/rds-mysql/main.tf`,
`modules/rds-postgres/main.tf`, `terraform.tfvars` — all pure `=`-alignment
whitespace, no semantic changes. Applied `terraform fmt -recursive` directly
(a deterministic auto-formatter, the Terraform equivalent of `ruff format`,
carrying no behavioral risk) to the real tracked files; `fmt -check` now
passes clean (exit 0).

### `terraform init -backend=false` — passed

Succeeded for the root config: downloaded all 5
`terraform-aws-modules/*` registry modules and resolved/installed 6 provider
plugins (`aws`, `random`, `tls`, `kubernetes`, `time`, `cloudinit`) with zero
AWS credentials or network calls to AWS itself (only Terraform's own public
registry, `registry.terraform.io`).

### `terraform validate` — 4/5 modules pass; `eks` has a real, pre-existing
### incompatibility, not fixed (original pass — resolved in the follow-up below)

| Target | Result |
|---|---|
| root (all 5 modules combined) | **fails** — transitively, via the `eks` module (see below) |
| `modules/vpc` (standalone) | passes (1 pre-existing deprecation warning inside vendored module code) |
| `modules/eks` (standalone) | **fails** — confirmed independent of root-level resolution |
| `modules/rds-postgres` (standalone) | passes, clean |
| `modules/rds-mysql` (standalone) | passes, clean |
| `modules/s3` (standalone) | passes (1 pre-existing deprecation warning inside vendored module code) |

**The `eks` module failure, verbatim (errors are inside the *downloaded*
`terraform-aws-modules/eks/aws` v19.21.0 source, not this repository's own
`modules/eks/main.tf`):**

```text
Error: Unsupported argument
  on .terraform/modules/eks.eks/main.tf line 428, in resource "aws_eks_addon" "before_compute":
  428:   resolve_conflicts        = try(each.value.resolve_conflicts, "OVERWRITE")
An argument named "resolve_conflicts" is not expected here.

Error: Unsupported block type
  on .terraform/modules/eks.eks/modules/eks-managed-node-group/main.tf line 104:
  dynamic "elastic_gpu_specifications" { ...
Blocks of type "elastic_gpu_specifications" are not expected here.
(+ 2 more, same pattern: "elastic_inference_accelerator")
```

**Root cause, confirmed, not assumed:** `deploy/infra/modules/eks/main.tf`
pins `terraform-aws-modules/eks/aws version = "~> 19.0"` (resolved
`19.21.0`), and that module's own vendored `versions.tf` only declares
`aws >= 4.57` — no upper bound. With no upper bound anywhere in this
repository's own Terraform either, `terraform init` resolves the *newest*
available `hashicorp/aws` provider (`6.53.0`). `aws_eks_addon.resolve_conflicts`
and the `elastic_gpu_specifications`/`elastic_inference_accelerator` dynamic
blocks on `aws_launch_template` were removed from the AWS provider's schema
in a major version well after `19.21.0` of the EKS module was released
against. This is confirmed independent of the root's combined resolution:
`modules/eks` validated **standalone** hits the identical four errors.

**Why this was not fixed in the first pass:** the correct remediation is
either pinning `hashicorp/aws` to an older major line compatible with EKS
module `19.x`, or bumping the EKS module to a newer major line compatible
with AWS provider `6.x` — both looked, at the time, like real
infrastructure/dependency-version decisions. A dedicated follow-up pass (see
immediately below) was recommended rather than deciding unilaterally in the
same pass that discovered the problem.

## Follow-up: `eks` module provider-constraint fix (this pass)

This is the dedicated follow-up pass recommended above, requested via issue
#43 continuation. Scoped strictly to a Terraform provider version
constraint; no AWS resource topology, no EKS module major-version bump, no
`terraform plan`/`apply`, no real AWS credentials.

### Decision: pin the provider, not the module

Per this pass's own decision rule ("prefer the smallest provider constraint
that keeps the existing EKS module major line; do not bump the EKS module
major unless provider pinning cannot validate"), the fix tested first was
capping `hashicorp/aws` below the major version that removed the
attributes/blocks EKS module `19.x` still emits, while leaving
`terraform-aws-modules/eks/aws version = "~> 19.0"` untouched. This is a
**deployability validation fix, not an AWS architecture change**: it
changes which already-published, already-compatible version of a provider
plugin `terraform validate`/`init` resolves to when computing the
Terraform-side type/schema graph — it does not add, remove, or reconfigure
any AWS resource, node group, VPC topology, or IAM policy. Nothing in
`deploy/infra/modules/eks/main.tf`'s own resource arguments changed.

Checked every vendored module's own provider floor first (via each
module's downloaded `versions.tf`, not guessed) to confirm a workable
window exists below the major-6 boundary:

| Module | Its own `aws` provider floor |
|---|---|
| `eks` (`terraform-aws-modules/eks/aws ~> 19.0`) | `>= 4.57` |
| `eks`'s own `kms` sub-module | `>= 4.33` |
| `vpc` (`terraform-aws-modules/vpc/aws ~> 5.0`) | `>= 5.79` (the highest floor of any module) |
| `rds-postgres`/`rds-mysql` (`terraform-aws-modules/rds/aws ~> 5.0`) | `>= 4.65` |
| `s3` (`terraform-aws-modules/s3-bucket/aws ~> 3.0`) | `>= 4.9` |

The union of every floor plus a new `< 6.0` ceiling leaves a valid,
non-empty window (effectively `>= 5.79, < 6.0`, driven by `vpc`'s floor
being the highest) — confirmed by actually running `init`, not just
reasoning about semver ranges.

### Fix applied

**`deploy/infra/main.tf`** — added a `required_providers` block inside the
existing root `terraform { ... }` block (this repo has no separate
`versions.tf`; the root `terraform{}` block, which already holds
`required_version` and the `backend "s3"` block, is the layout-matching
location):

```hcl
required_providers {
  aws = {
    source  = "hashicorp/aws"
    version = ">= 4.57, < 6.0"
  }
}
```

**`deploy/infra/modules/eks/main.tf`** — the same constraint was **also**
needed directly inside the module's own file. Reproduced via the task's own
required command, `terraform -chdir=deploy/infra/modules/eks validate`
treats that directory as its own standalone root and does **not** inherit
a constraint declared only in the caller's (root's) `terraform{}` block —
confirmed empirically: after fixing only `main.tf`, the root passed but
`modules/eks` validated standalone still failed with the identical four
errors. Added an equivalent `terraform { required_providers { aws = {
version = ">= 4.57, < 6.0" } } }` block directly above the `module "eks"`
block in that file. Only `eks` received this per-module block — `vpc`,
`rds-postgres`, `rds-mysql`, and `s3` all validate standalone without one
today (confirmed: none of their vendored module versions use any
provider-6.x-incompatible attribute), so adding speculative constraints to
modules with no confirmed failure was avoided, per "smallest fix" and "do
not redesign the infrastructure."

### Provider version resolved after `init -upgrade`

```text
$ terraform -chdir=deploy/infra init -backend=false -upgrade
...
- Installing hashicorp/aws v5.100.0...
- Installed hashicorp/aws v5.100.0 (signed by HashiCorp)
...
Terraform has been successfully initialized!
```

`hashicorp/aws v5.100.0` — the newest published 5.x release, satisfying
every module's own floor and the new `< 6.0` ceiling simultaneously.

### `terraform validate` — all 6 targets now pass

| Target | Result after fix |
|---|---|
| root (all 5 modules combined) | **passes** (1 pre-existing cosmetic deprecation warning: `kubernetes_config_map` → `kubernetes_config_map_v1`, inside vendored EKS module code) |
| `modules/vpc` (standalone) | passes (same pre-existing deprecation warning as before, unrelated to this fix) |
| `modules/eks` (standalone) | **passes** — was the confirmed blocker; now clean except the same cosmetic `kubernetes_config_map` warning |
| `modules/rds-postgres` (standalone) | passes, clean, zero warnings |
| `modules/rds-mysql` (standalone) | passes, clean, zero warnings |
| `modules/s3` (standalone) | passes (same pre-existing deprecation warning as before, unrelated to this fix) |

```text
$ terraform -chdir=deploy/infra/modules/eks validate
Warning: Deprecated Resource
  with module.eks.kubernetes_config_map.aws_auth,
  on .terraform/modules/eks/main.tf line 545: resource "kubernetes_config_map" "aws_auth" {
Deprecated; use kubernetes_config_map_v1.

Success! The configuration is valid, but there were some
validation warnings as shown above.
```

`terraform fmt -check -recursive` was re-run against the real tracked tree
after both edits and remains clean (exit 0) — the two new
`required_providers` blocks were written in canonical `terraform fmt` style
from the start.

**Terraform syntax/module validation now passes for all 5 modules and the
root** (`vpc`, `eks`, `rds-postgres`, `rds-mysql`, `s3`). `terraform
plan`/`apply` were **not run** — neither this pass nor the prior one — both
require AWS credentials and the real S3 backend (`deploy/infra/main.tf`
declares `backend "s3" { bucket = "astradesk-tfstate" ... }`), neither of
which was assumed, provided, or required by this fix. No real AWS resource
topology was changed.

### `.terraform.lock.hcl` — not tracked, none generated in the real tree

Per this pass's decision rule: `git ls-files deploy/infra/.terraform.lock.hcl
'deploy/infra/**/.terraform.lock.hcl'` returns nothing — this repository
does not track Terraform dependency lock files anywhere under
`deploy/infra/`. Every `terraform init`/`validate` in both the original and
this follow-up pass ran against a **scratch copy** of `deploy/infra/`
outside the repository (never the tracked tree directly), so no
`.terraform.lock.hcl` or `.terraform/` directory was ever generated in the
real working tree — confirmed with `find deploy/infra -name ".terraform*"`
returning empty both before and after this pass. No lockfile cleanup was
needed.

## Istio/Kubernetes verification

**Commands:** `istioctl validate -f deploy/istio`; `kubectl apply
--dry-run=client -f ...` (attempted, see limitation below).

### Two independent, non-identical manifest generations coexist

`deploy/istio/` contains an old, unprefixed generation and a newer, numbered
generation — summarized briefly here; see the dedicated **"Istio
dual-generation inventory"** section below (added this pass) for the full
file-by-file inventory, every tracked reference, a field-by-field behavioral
comparison, decision options, and a recommendation. **Neither generation was
deleted, merged, or canonicalized in this pass** — both remain exactly as
found, and both continue to validate independently below.

### Findings, before any fix

`istioctl validate -f deploy/istio` failed (exit 1) with one warning and one
blocking error, both real:

1. **Warning — unreachable route in the old `virtualservice.yaml`:**
   `virtualService rule #3 match #0 of prefix /auditor is not used
   (duplicate/overlapping match in rule #0 of prefix / on #2)`. The file
   listed a catch-all `prefix: /` match *before* the more specific `prefix:
   /auditor` match; Istio evaluates HTTP match rules in list order and takes
   the first match, so `/auditor` traffic was silently being routed to the
   `admin` service instead of `auditor`. Fixed by reordering: `/auditor`
   now precedes the catch-all `/`.
2. **Error — invalid `AuthorizationPolicy` schema in the new
   `30-authorizationpolicy-namespace.yaml`:**
   `` `to.operation` must not be empty, found at rule 0 `` (and rule 1).
   Both rules used `to: [{operation: {}}]`, intending "allow all
   operations" per their own comments — but Istio's schema rejects an empty
   `operation` object outright. The correct way to express "no operation
   restriction" is to omit `to` entirely. Fixed by removing both `to`
   blocks, leaving only `from`.

Both fixes also directly caused, and required, the Helm-side
`astradesk-ticketAdapter` → `astradesk-ticket-adapter` correction described
above, since the old `virtualservice.yaml` referenced that Service by name
as a routing destination.

### Result after fixes

```text
$ istioctl validate -f deploy/istio
"/istio/50-cert-manager-certificate.yaml" is valid
"/istio/certs/astradesk-ca-certificate.yaml" is valid
"/istio/certs/astradesk-ca-clusterissuer.yaml" is valid
"/istio/gateway.yaml" is valid
"/istio/10-peer-authentication.yaml" is valid
"/istio/41-virtualservice-astradesk-api.yaml" is valid
"/istio/certs/letsencrypt-prod-clusterissuer.yaml" is valid
"/istio/peerauthentication.yaml" is valid
"/istio/00-namespace.yaml" is valid
"/istio/30-authorizationpolicy-namespace.yaml" is valid
"/istio/40-gateway.yaml" is valid
"/istio/virtualservice.yaml" is valid
"/istio/20-destinationrule-astradesk-api.yaml" is valid
"/istio/certmanager.yaml" is valid
(exit 0)
```

**Istio manifest validation passed via istioctl** for all 14 tracked YAML
files under `deploy/istio/` (both generations, plus `certs/`).

**Limitation, confirmed not assumed:** `kubectl apply --dry-run=client`
could not be meaningfully exercised in this environment. Even in "client"
mode, `kubectl` requires a reachable API server to perform REST-mapping
discovery (confirmed: it fails with `dial tcp [::1]:8080: connect:
connection refused` even with `--validate=false`, before ever reading the
YAML's contents) — it is not a purely offline command the way `istioctl
validate` is. Per this issue's explicit instruction ("do not fake
server-side validation"), no cluster (real, `kind`, or otherwise) was
spun up to work around this. `istioctl validate` was used instead, since it
bundles Istio's own schemas and needs no server at all — it is the
tool this issue's own text names as the fallback for exactly this
situation.

**`istioctl analyze` against a live mesh and the negative-connectivity test
were not performed; cluster apply not performed; requires environment.**

## Istio dual-generation inventory

This section is the maintainer decision point requested as a continuation of
issue #43. It is a precise inventory only — **no `deploy/istio/` manifest
was altered, deleted, merged, or canonicalized in this pass.** Both
generations remain exactly as found and both still pass `istioctl validate`
independently (re-confirmed fresh for this pass — see "`istioctl validate`
status" below).

### Generation A — files (old, unprefixed)

| File | Kind | `metadata.name` | `metadata.namespace` | `apiVersion` |
|---|---|---|---|---|
| `deploy/istio/gateway.yaml` | `Gateway` | `astradesk-gateway` | `astradesk-prod` | `networking.istio.io/v1alpha3` |
| `deploy/istio/virtualservice.yaml` | `VirtualService` | `astradesk-vs` | `astradesk-prod` | `networking.istio.io/v1alpha3` |
| `deploy/istio/peerauthentication.yaml` | `PeerAuthentication` | `default` | `astradesk-prod` | `security.istio.io/v1beta1` |
| `deploy/istio/certmanager.yaml` | `Issuer` + `Certificate` | `astradesk-selfsigned-issuer`, `astradesk-tls` | `astradesk-prod` | `cert-manager.io/v1` |

No `Namespace`, `DestinationRule`, or `AuthorizationPolicy` resource exists
in Generation A — it assumes `astradesk-prod` is created elsewhere (both
tracked pipelines create it via `helm --create-namespace`, which does not by
itself add an `istio-injection: enabled` label; sidecar injection for
Generation A's pods depends entirely on the Helm chart's own per-pod
`sidecar.istio.io/inject: "true"` annotation in
`deploy/chart/templates/deployment.yaml`, not on any namespace-level label).

### Generation B — files (new, numbered)

| File | Kind | `metadata.name` | `metadata.namespace` | `apiVersion` |
|---|---|---|---|---|
| `deploy/istio/00-namespace.yaml` | `Namespace` | `astradesk` | *(cluster-scoped)* | `v1` |
| `deploy/istio/10-peer-authentication.yaml` | `PeerAuthentication` | `astradesk-peer-auth` | `astradesk` | `security.istio.io/v1beta1` |
| `deploy/istio/20-destinationrule-astradesk-api.yaml` | `DestinationRule` | `astradesk-api` | `astradesk` | `networking.istio.io/v1beta1` |
| `deploy/istio/30-authorizationpolicy-namespace.yaml` | `AuthorizationPolicy` | `astradesk-allow-from-namespace-and-ingress` | `astradesk` | `security.istio.io/v1beta1` |
| `deploy/istio/40-gateway.yaml` | `Gateway` | `astradesk-gw` | `astradesk` | `networking.istio.io/v1beta1` |
| `deploy/istio/41-virtualservice-astradesk-api.yaml` | `VirtualService` | `astradesk-api` | `astradesk` | `networking.istio.io/v1beta1` |
| `deploy/istio/50-cert-manager-certificate.yaml` | `Certificate` ×2 | `astradesk-tls`, `astradesk-mtls-cert` | `astradesk` | `cert-manager.io/v1` |
| `deploy/istio/certs/astradesk-ca-certificate.yaml` | `Certificate` | `astradesk-ca` | `astradesk` | `cert-manager.io/v1` |
| `deploy/istio/certs/astradesk-ca-clusterissuer.yaml` | `ClusterIssuer` | `astradesk-ca` | *(cluster-scoped)* | `cert-manager.io/v1` |
| `deploy/istio/certs/letsencrypt-prod-clusterissuer.yaml` | `ClusterIssuer` | `letsencrypt-prod` | *(cluster-scoped)* | `cert-manager.io/v1` |

Generation B is self-contained for namespace setup (declares its own
`Namespace` with `istio-injection: enabled` baked in) and adds two resource
*kinds* Generation A has no equivalent of at all: `DestinationRule` and
`AuthorizationPolicy`.

### Where each is referenced (pipelines and docs)

Confirmed via `git grep` against every tracked `Jenkinsfile*`, `deploy/`,
`docs/`, `README.md`, `.github/`, and `.gitlab-ci.yml` path — not assumed:

| Reference | Generation implied | Exact evidence |
|---|---|---|
| `Jenkinsfile` (`HELM_NAMESPACE`, `Istio Config` stage) | **A** | `HELM_NAMESPACE = 'astradesk-prod'` (line 29); `kubectl apply -f deploy/istio/ --kubeconfig=$KUBECONFIG` then `istioctl analyze -n ${HELM_NAMESPACE} --kubeconfig=$KUBECONFIG` (lines 405–406) |
| `.gitlab-ci.yml` (`istio:apply`, `istio:sync-certs`, `deploy:helm` jobs) | **A** | `kubectl apply -f deploy/istio/ -n astradesk-prod` and `istioctl analyze -n astradesk-prod` (lines 325–326, gated `if: $CI_COMMIT_BRANCH == "main"`); cert sync reads `kubectl get secret -n astradesk-prod astradesk-tls` (line 342); the real `helm upgrade --install astradesk deploy/chart ... --namespace astradesk-prod --create-namespace` (lines 377–395, `only: main`, `when: manual`) |
| `README.md` (root, mTLS quick-start, lines 504–506) | **B** | `kubectl apply -f deploy/istio/00-namespace.yaml`, then `deploy/istio/10-peer-authentication.yaml` "(and the rest in deploy/istio/)" |
| `deploy/chart/deploy_chart_README.md` | **A** | Documents `gateway.yaml`/`virtualservice.yaml`/`peerauthentication.yaml`/`certmanager.yaml` by name (line 221) and uses `astradesk-prod` throughout its Deployment/Verification sections |
| `deploy/istio/readme.md` (Polish, short) | **B** only | Documents exactly the `00`→`50` sequence and nothing else |
| `deploy/istio/deploy_istio_README.md` (English, long) | **Hybrid, internally inconsistent** | States namespace `astradesk-prod` throughout (line 21) and its own directory listing shows `00-namespace.yaml` (B) alongside `gateway.yaml`/`peerauthentication.yaml`/`virtualservice.yaml`/`certmanager.yaml` (A) as if all six coexist normally under `templates`-style headings; never mentions `10-`/`20-`/`30-`/`41-`/`50-` at all. Also states "Java 25" for the ticket adapter, contradicting the actual JDK 21 toolchain — an independent sign this doc is stale. |
| `deploy/istio/certs/README_certs.md` | **B**, one exception | References `deploy/istio/10-peer-authentication.yaml` (line 38); its one troubleshooting line uses `istioctl analyze -n astradesk` (line 91, matching B's namespace) — the **only** place in the whole grep where an actual command targets the `astradesk` namespace instead of `astradesk-prod` |
| `deploy/infra/README_infra.md` | **Mixed** | Cites `deploy/istio/10-peer-authentication.yaml` (B, line 171) but its example commands use `kubectl get pods -n astradesk-prod` / `istioctl analyze -n astradesk-prod` (A, lines 139–140) |
| `deploy/openshift/README_openshift.md` | **Mixed** | Cites B's files by path (`10-peer-authentication.yaml`, `30-authorizationpolicy-namespace.yaml`, `50-cert-manager-certificate.yaml`) but every actual `oc`/`kubectl`/`istioctl` command targets `-n astradesk-prod` (A's namespace) |
| `deploy/openshift/*-template.yaml` (5 files) | **A** | Each has a template parameter defaulting to `value: astradesk-prod` |

**Both tracked, executable CI/CD pipeline definitions (`Jenkinsfile` and
`.gitlab-ci.yml`) deploy Generation A's namespace exclusively** — including
the real `helm upgrade --install`/`helm upgrade --dry-run` commands, which
also target `--namespace astradesk-prod`. Every reference to Generation B
lives in documentation, never in a tracked pipeline's executable `script`/
`sh` step. That said, neither pipeline file is fully trustworthy as "proven
live automation": both `Jenkinsfile` (`TERRAFORM_DIR = 'infra'`) and
`.gitlab-ci.yml` (`terraform -chdir=infra output ...`) reference a top-level
`infra/` directory that does not exist anywhere in this repository (Terraform
actually lives at `deploy/infra/`, confirmed via `git ls-files` and `find`)
— an independently-confirmed staleness in both pipelines, unrelated to
Istio, that should temper how much weight "the pipeline says so" carries on
its own.

### Behavioral comparison

| Dimension | Generation A | Generation B |
|---|---|---|
| Namespace | `astradesk-prod` (must pre-exist; not self-provisioning) | `astradesk` (self-provisioning via its own `00-namespace.yaml`, includes `istio-injection: enabled`) |
| Networking `apiVersion` | `networking.istio.io/v1alpha3` (older) | `networking.istio.io/v1beta1` (current) |
| Security `apiVersion` | `security.istio.io/v1beta1` | `security.istio.io/v1beta1` *(identical — not a difference)* |
| Gateway host(s) | `*.astradesk.local` (wildcard, `.local` TLD) | `api.astradesk.example.com` (single, real-looking FQDN); adds `minProtocolVersion: TLSV1_2` (A sets no minimum) |
| **Routing coverage** | **All 4 services**: `/api`→`astradesk-api:8080`, `/ticket`→`astradesk-ticket-adapter:8080`, `/auditor`→`astradesk-auditor:8080`, `/`→`astradesk-admin:3000` (one `VirtualService`, 4 hosts) | **API only**: `/`→`astradesk-api...svc.cluster.local:8080` (one `VirtualService`, 1 host). **No route exists for ticket-adapter, admin, or auditor in Generation B at all.** |
| mTLS (`PeerAuthentication`) scope | `STRICT`, **no selector** — applies to every workload in `astradesk-prod` unconditionally | `STRICT`, **selector `matchLabels: app: astradesk`** — only covers workloads carrying that exact label; anything in the `astradesk` namespace without it is not covered by this policy |
| `DestinationRule` | none | `astradesk-api` only, forces `ISTIO_MUTUAL` (largely redundant with `PeerAuthentication` STRICT's automatic mTLS in modern Istio, but not harmful); no equivalent for the other 3 services in either generation |
| `AuthorizationPolicy` (Layer-7 authorization) | **none at all** — any mTLS-authenticated mesh peer may reach any workload in `astradesk-prod`; security rests entirely on mTLS identity | **`astradesk-allow-from-namespace-and-ingress`** — restricts workloads labeled `app: astradesk` to traffic from same-namespace sources or the `istio-ingressgateway` service account only |
| Certificate strategy | Single self-signed `Issuer`→`Certificate` (`astradesk-selfsigned-issuer`), covers wildcard + 4 named `.local` hosts — a local/dev-style posture | Two-tier: public ACME (`letsencrypt-prod` `ClusterIssuer`, real Let's Encrypt production endpoint) for the external FQDN, plus a separate internal CA (`astradesk-ca` `ClusterIssuer`) for internal mTLS — a materially more production-realistic split |
| Cert lifetime | Not specified (cert-manager default, typically 90d/renew at 2/3 life) | Explicit `duration: 2160h` (90d) / `renewBefore: 360h` (15d) on both certificates |

### `istioctl validate` status

Re-confirmed fresh for this pass:

```text
$ istioctl validate -f deploy/istio
"/istio/00-namespace.yaml" is valid
"/istio/41-virtualservice-astradesk-api.yaml" is valid
"/istio/certs/letsencrypt-prod-clusterissuer.yaml" is valid
"/istio/virtualservice.yaml" is valid
"/istio/30-authorizationpolicy-namespace.yaml" is valid
"/istio/50-cert-manager-certificate.yaml" is valid
"/istio/certmanager.yaml" is valid
"/istio/peerauthentication.yaml" is valid
"/istio/certs/astradesk-ca-clusterissuer.yaml" is valid
"/istio/gateway.yaml" is valid
"/istio/10-peer-authentication.yaml" is valid
"/istio/20-destinationrule-astradesk-api.yaml" is valid
"/istio/40-gateway.yaml" is valid
"/istio/certs/astradesk-ca-certificate.yaml" is valid
(exit 0)
```

**Both generations pass `istioctl validate` independently and simultaneously
— validity is not a discriminator between them.** The only prior blockers
(the `/auditor` routing-order warning in Generation A's `virtualservice.yaml`
and the invalid `to.operation` schema error in Generation B's
`30-authorizationpolicy-namespace.yaml`) were both already fixed in the
first #43 pass, before this inventory.

### A technical note on what `kubectl apply -f deploy/istio/` actually does

Both tracked pipelines run `kubectl apply -f deploy/istio/` (non-recursive)
followed by `istioctl analyze -n astradesk-prod` (or `-n ${HELM_NAMESPACE}`,
same value). Two consequences worth flagging precisely:

1. `kubectl apply -f <dir>` without `-R`/`--recursive` only applies files
   directly inside that directory — **`certs/*.yaml` is never applied by
   either tracked pipeline.** The only tracked place that applies `certs/`
   is `deploy/istio/certs/README_certs.md`'s own manually-documented
   `kubectl apply -f deploy/istio/certs/` step.
2. Every manifest in both generations declares its own `metadata.namespace`
   (or is cluster-scoped), so the `-n astradesk-prod` flag on the `apply`
   command is inert for placement — it would only matter for a resource
   that omits its own namespace, and none does. It is **not** inert on the
   following `istioctl analyze -n astradesk-prod`, though: that command
   scopes analysis to the `astradesk-prod` namespace only, so if this
   pipeline step ever actually ran against a real cluster with both
   generations applied, it would silently never analyze Generation B's
   resources (all in `astradesk`) at all.

### Is either generation unused?

**No — by the literal, tracked-pipeline `kubectl apply -f deploy/istio/`
command, both generations would be applied to a real cluster in the same
run** (that command does not distinguish between them; it applies every
top-level file in the directory). Neither is dead YAML. What differs is
*documentation and downstream tooling intent*: Generation A is what the two
executable pipeline definitions actually verify/reference by namespace;
Generation B is what the root `README.md`'s quick-start and the directory's
own short `readme.md` present as the way to do it; `deploy_istio_README.md`
tries to describe both together and gets neither fully right.

### Decision options

| Option | What it means | Risk |
|---|---|---|
| **(1) Canonicalize Generation A** | Keep `astradesk-prod`/old files as the real config; delete or archive Generation B's files; update `README.md`'s quick-start and `deploy/istio/readme.md` to match; fix `deploy_istio_README.md`. | Loses Generation B's `AuthorizationPolicy` (Layer-7 authorization) and its more realistic two-tier cert strategy unless ported forward. Matches what the two live pipelines already reference, so lowest *pipeline-consistency* risk. |
| **(2) Canonicalize Generation B** | Keep `astradesk`/new files; delete or archive Generation A's files; update `Jenkinsfile`/`.gitlab-ci.yml`/`deploy_chart_README.md`/`README_infra.md`/`README_openshift.md` (all reference `astradesk-prod`) to the `astradesk` namespace. | **Currently loses routing for ticket-adapter, admin, and auditor entirely** — Generation B's `VirtualService` only routes the API. This gap would need a new `VirtualService`/route added for the other three services before this option is safe to adopt. Also requires updating the `PeerAuthentication` selector-scoping tradeoff (see comparison table) to confirm it is intentional. Highest one-time doc/pipeline churn, but architecturally the more modern, more secure base to build on. |
| **(3) Merge: take Generation B's security additions, Generation A's routing completeness** | Keep one namespace (whichever is chosen), port `DestinationRule`+`AuthorizationPolicy` from B and the full 4-service `VirtualService` from A into a single generation; delete the other. | Requires the most hands-on authoring (new/merged YAML), so the most work, but produces the only outcome that has neither gap. This is architecture design, not a validation fix — explicitly out of this pass's scope to perform. |
| **(4) Leave both, document explicitly** | Keep both generations, but stop presenting either as accidental: pick one namespace as "production" and explicitly label the other's files (in-file comment + README) as superseded/reference-only, without deleting them. | Lowest immediate risk (fully reversible, no deletion, no pipeline change required today), but leaves the underlying ambiguity — and the `istioctl analyze -n astradesk-prod` blind spot toward Generation B — unresolved. Defers the real decision. |

### Decision: ratified and applied (see follow-up section below)

The maintainer chose **Option (1), canonicalize Generation A** — matching
this document's own recommendation from the inventory pass — with one
clarification: Generation B's `AuthorizationPolicy` and two-tier certificate
strategy are **not** being backported in this pass at all, not even as a
same-effort follow-up. They remain recorded here as a candidate for a
future, separate, explicitly-scoped design issue. Rationale, as given:

- Both executable deployment pipelines use namespace `astradesk-prod`
  (Generation A).
- Generation A already routes all four services; Generation B currently
  routes only the API.
- Generation B is not referenced by any executable pipeline step.

**This decision has been applied** — see "Follow-up: canonicalization
applied (this pass)" immediately after this section for the full change
list, verification evidence, and exactly what was and was not touched.

### Statement: no generation deleted or canonicalized in the inventory pass

The paragraphs above and the file tables earlier in this section describe
the state **as found during the inventory pass** — confirmed via
`git diff --name-status` at the end of that pass (see
handoff): zero files under `deploy/istio/` were added, deleted, or modified
by this inventory pass. The two `deploy/istio/*.yaml` fixes present in this
document's earlier "Findings, before any fix" section were made in the
**prior** #43 pass, before this inventory work began.

## Follow-up: canonicalization applied (this pass)

This section documents the maintainer-directed follow-up that acted on the
inventory above. Scope: relocate the non-canonical Istio generation out of
`kubectl apply -f deploy/istio/`'s reach, fix stale Terraform `infra/` paths
in both tracked pipelines and every doc that echoes them, and re-verify the
full offline suite. **No AWS credentials were used or required; `terraform
plan`/`apply` were not run; `kubectl apply` was not run against any real
cluster; Generation B's `AuthorizationPolicy`/`DestinationRule`/certificate
strategy were not ported into Generation A.**

### Istio: Generation B relocated, not deleted

Moved (via `git mv`, preserving history) every Generation B file out of
`deploy/istio/`'s flat top level into a new `deploy/istio/generation-b-reference/`
subdirectory:

```text
deploy/istio/00-namespace.yaml                       → deploy/istio/generation-b-reference/00-namespace.yaml
deploy/istio/10-peer-authentication.yaml             → deploy/istio/generation-b-reference/10-peer-authentication.yaml
deploy/istio/20-destinationrule-astradesk-api.yaml   → deploy/istio/generation-b-reference/20-destinationrule-astradesk-api.yaml
deploy/istio/30-authorizationpolicy-namespace.yaml   → deploy/istio/generation-b-reference/30-authorizationpolicy-namespace.yaml
deploy/istio/40-gateway.yaml                         → deploy/istio/generation-b-reference/40-gateway.yaml
deploy/istio/41-virtualservice-astradesk-api.yaml    → deploy/istio/generation-b-reference/41-virtualservice-astradesk-api.yaml
deploy/istio/50-cert-manager-certificate.yaml        → deploy/istio/generation-b-reference/50-cert-manager-certificate.yaml
deploy/istio/readme.md                               → deploy/istio/generation-b-reference/readme.md
deploy/istio/certs/README_certs.md                   → deploy/istio/generation-b-reference/certs/README_certs.md
deploy/istio/certs/astradesk-ca-certificate.yaml     → deploy/istio/generation-b-reference/certs/astradesk-ca-certificate.yaml
deploy/istio/certs/astradesk-ca-clusterissuer.yaml   → deploy/istio/generation-b-reference/certs/astradesk-ca-clusterissuer.yaml
deploy/istio/certs/letsencrypt-prod-clusterissuer.yaml → deploy/istio/generation-b-reference/certs/letsencrypt-prod-clusterissuer.yaml
```

Verified content-identical at the new location (`diff` against each file's
prior `HEAD` blob) for all 11 files above except
`30-authorizationpolicy-namespace.yaml`, whose only difference is the
already-known, already-documented schema fix from the original #43 pass
(the removed invalid `to: [{operation: {}}]` blocks) — not a new change.
Each moved file's own `File:` SPDX header comment was updated to its new
path (required to keep `scripts/license_headers.py --check` passing; see
below). Added `deploy/istio/generation-b-reference/README.md` (new)
explaining why the directory exists, the maintainer's decision and
rationale, what is preserved there for future work, and what not to do with
it. The now-empty `deploy/istio/certs/` directory (git does not track empty
directories; this was leftover from the `git mv` operations) was removed.

**Result: `deploy/istio/`'s flat top level now contains only Generation A**
(`certmanager.yaml`, `gateway.yaml`, `peerauthentication.yaml`,
`virtualservice.yaml`, plus `deploy_istio_README.md` and `readme.md`).
Confirmed structurally, not just asserted:

```text
$ find deploy/istio -maxdepth 1 -type f
deploy/istio/certmanager.yaml
deploy/istio/deploy_istio_README.md
deploy/istio/gateway.yaml
deploy/istio/peerauthentication.yaml
deploy/istio/virtualservice.yaml

$ find deploy/istio -maxdepth 1 -type d
deploy/istio
deploy/istio/generation-b-reference
```

`kubectl apply -f deploy/istio/` (non-recursive — confirmed in the
inventory pass above, and unchanged kubectl behavior) now applies exactly
these 4 manifests and nothing from `generation-b-reference/`, in either
tracked pipeline. (`istioctl validate -f deploy/istio` does recurse into
subdirectories by design, so it still validates all 14 files, both
generations, in one invocation — that tool's recursion has no bearing on
what `kubectl apply` actually does, which was the property that mattered.)

### Terraform: stale `infra/` paths fixed in both tracked pipelines

Both `Jenkinsfile` and `.gitlab-ci.yml` referenced a top-level `infra/`
directory that does not exist in this repository (confirmed via `find` and
`git ls-files` in the prior inventory pass); the real Terraform root is
`deploy/infra/`. Fixed every occurrence:

| File | Before | After |
|---|---|---|
| `Jenkinsfile` | `TERRAFORM_DIR = 'infra'` | `TERRAFORM_DIR = 'deploy/infra'` |
| `Jenkinsfile` | `infra/plan.out,` (in `archiveArtifacts`) | `deploy/infra/plan.out,` |
| `.gitlab-ci.yml` | global cache path `.terraform/` | `deploy/infra/.terraform/` |
| `.gitlab-ci.yml` | `terraform:init`/`plan`/`apply` jobs: `cd infra` (×3) | `cd deploy/infra` |
| `.gitlab-ci.yml` | `terraform:init` artifact path `infra/.terraform/` | `deploy/infra/.terraform/` |
| `.gitlab-ci.yml` | `terraform:plan` artifact path `infra/plan.out` | `deploy/infra/plan.out` |
| `.gitlab-ci.yml` | `terraform -chdir=infra output ...` (×2, in `deploy:helm`) | `terraform -chdir=deploy/infra output ...` |

All other `${TERRAFORM_DIR}`/`env.TERRAFORM_DIR` uses in `Jenkinsfile` are
variable references and needed no direct edit — they now resolve correctly
from the single constant fix above. Confirmed with a follow-up grep that no
bare (non-`deploy/infra`) `infra` path remains in either file.

### Docs: Generation B no longer presented as the active deploy path

Fixed every tracked doc that referenced a now-moved Generation B file path,
a stale `infra/` Terraform path, or the stale "Java 25" ticket-adapter claim
(the actual toolchain is JDK 21 — see the issue #40 Java remediation
evidence):

| File | What changed |
|---|---|
| `deploy/istio/deploy_istio_README.md` | Directory-contents tree no longer lists `00-namespace.yaml`/`certs/` as if they live here; added a `generation-b-reference/` subsection explaining the split; fixed `infra/` → `deploy/infra/` (×2); fixed "Java 25" → "Java 21" |
| `README.md` (root) | mTLS quick-start rewritten: namespace is Helm-created, not a separate manifest; `kubectl apply -f deploy/istio/` now correctly described as applying the 4 canonical files; fixed `cd infra` → `cd deploy/infra` in the AWS/Terraform quick-start |
| `docs/pl/README.pl.main.md`, `docs/zh-CN/README.zh-CN.main.md` | Same two fixes, translated |
| `deploy/chart/deploy_chart_README.md` | Fixed 3× stale `infra/` → `deploy/infra/` |
| `deploy/infra/README_infra.md` | Fixed directory-tree header, 4× `infra/`-family path/command references, "Java 25+" → "Java 21", and a pre-existing `terraform validate -chdir=...` flag-order typo encountered while fixing the same line's path; two `deploy/istio/certs/...` references pointed to `certmanager.yaml` instead (Generation A's self-contained cert-manager file) |
| `deploy/openshift/README_openshift.md` | Fixed 2× moved-file references to Generation A's files; fixed "Java 25+" → "Java 21"; the RBAC/`AuthorizationPolicy` claim was **not** redirected to a Generation A equivalent (none exists) — rewritten to state plainly that the canonical generation has no `AuthorizationPolicy` today, point at `generation-b-reference/` and this evidence document for the deferred follow-up, and note that application-level RBAC is separately enforced in `src/runtime/auth.py` |
| `packages/README.md` | Fixed a stale reference to the now-moved `41-virtualservice-astradesk-api.yaml`; redirected to canonical `virtualservice.yaml`; fixed `infra/main.tf` → `deploy/infra/main.tf` |

No doc was rewritten wholesale; every change is a targeted fix to a
specific stale path, moved-file reference, or factual claim — none of them
change what the canonical Istio generation technically *does*.

### License headers: moved files needed their own path corrected

`uv run python scripts/license_headers.py --check` failed immediately after
the `git mv` operations: all 12 moved files still declared their *old*
path in their own `File:` SPDX header comment line, which
`scripts/license_headers.py` validates against each file's actual current
path. Fixed all 12 (plus the new `generation-b-reference/README.md`, which
was written with the correct path from the start). This is a direct,
mechanical consequence of the file relocation, not a new dependency or
deployment-artifact change.

### Verification after canonicalization — zero regressions

Re-ran the complete offline suite against the changed tree:

```text
$ helm lint --strict deploy/chart                              → 0 chart(s) failed
$ helm template astradesk deploy/chart                          → exit 0
$ terraform fmt -check -recursive (deploy/infra)                 → exit 0
$ terraform init -backend=false && terraform validate (root)     → Success (1 cosmetic warning, unchanged)
$ terraform init/validate × 5 modules (vpc/eks/rds-pg/rds-my/s3) → all Success (unchanged from prior pass)
$ istioctl validate -f deploy/istio                              → all 14 files valid, exit 0 (both generations, one now nested)
$ docker compose -f docker-compose.yml config                    → exit 0
$ docker compose -f docker-compose.dev.yml config                → exit 0
$ uv run python scripts/ci/verify_build_baseline.py               → OK, 12 Dockerfiles, 3 compose files
$ uv run ruff check ...                                           → All checks passed!
$ uv run ruff format --check ...                                  → 81 files already formatted
$ uv run pytest -q ...                                            → 448 passed, 1 warning (pre-existing, unrelated)
$ uv run python scripts/license_headers.py --check                → would normalize 0 file(s)
$ bash scripts/check-openapi-version.sh                           → exit 0
```

No Terraform `.tf` file, no Helm chart template, and no application/service
source file was touched in this pass — only `Jenkinsfile`, `.gitlab-ci.yml`,
the Istio directory layout, documentation, and this evidence document.

## Compose/build baseline

```text
$ docker compose -f docker-compose.yml config          → exit 0
$ docker compose -f docker-compose.dev.yml config      → exit 0
$ uv run python scripts/ci/verify_build_baseline.py    → (see below)
```

**One real bug found and fixed, in the verifier script itself, not a
deployment artifact:** `scripts/ci/verify_build_baseline.py`'s
`check_node_baseline()` called `full_path.read_text()` on every git-tracked
`.yml`/`.yaml`/Dockerfile-suffixed path without checking the file still
exists on disk — a check its sibling function `check_no_floating_latest()`
already has (`if not full_path.is_file(): continue`). This crashed
(`FileNotFoundError`) once `deploy/chart/requirements.yaml` was deleted from
the working tree but not yet staged (still present in git's index, so still
returned by `tracked_files()`). Added the same one-line existence guard to
`check_node_baseline()`. This is the "tiny tool-script fix" this issue's
instructions explicitly allow when a verifier requires it — not a
dependency or deployment-artifact change.

```text
Reproducible-build baseline OK: 12 Dockerfile(s), 3 compose file(s) checked.
```

## General baseline validation (regression check only — no deployment-artifact scope)

| Command | Result |
|---|---|
| `uv run ruff check core/src services/api-gateway/src services/api-gateway/tests services/admin_api mcp/src mcp/tests` | All checks passed! |
| `uv run ruff format --check` (same paths) | 81 files already formatted |
| `uv run pytest -q services/api-gateway/tests services/admin_api/tests mcp/tests` | 448 passed, 1 warning (pre-existing, unrelated) |
| `uv run python scripts/license_headers.py --check` | License headers verified; would normalize 0 file(s) |
| `bash scripts/check-openapi-version.sh` | exit 0 |

Admin Portal (`npm ci`/lint/test) and Java ticket-adapter (`./gradlew test`)
verification suites were **not run** — no files under `services/admin-portal/`
or `services/ticket-adapter-java/` were touched by this pass, and the
task's own instructions make those suites conditional on those files being
touched.

## Remaining UNVERIFIED markers

Both markers found by `git grep -nE 'UNVERIFIED|unverified'` at the start of
this pass live in `docs/roadmap/index.md`:

- Line 83 (Phase 2, item 4) — narrowed further to record that the
  maintainer has chosen and this pass applied a canonical Istio generation
  (pointing at this document's "Follow-up: canonicalization applied"
  section), and that only cluster/cloud-gated checks remain. See the diff
  to that file for exact wording.
- Line 106 (Gate checklist) — **left unchecked, wording refreshed**. The
  checklist item reads "Helm/Terraform/Istio validated (no UNVERIFIED on
  deployment)" as an all-or-nothing bar. All offline/static validation now
  passes across Helm, Terraform (including the `eks` module), and Istio,
  and the Istio dual-generation architecture decision that previously kept
  this box open is now resolved and applied. The box still stays unchecked
  solely because `helm install`/`terraform plan`/`apply`/live `istioctl
  analyze`/the negative-connectivity test remain un-run (cluster/cloud
  gated) — not a static-validation failure and not an open architecture
  question, but still a real gap against the checklist's literal bar.

No other `UNVERIFIED`/`unverified` markers exist in tracked files relevant
to deployment (the two other grep hits — `scripts/seed-tracker.sh`'s issue
title text, and a legitimate `jwt.get_unverified_header()` API call in
`test_oidc_ingress.py` — are unrelated).

## Skipped checks with reason

| Check | Reason skipped |
|---|---|
| `helm install`/`helm test` | requires a live Kubernetes cluster |
| `terraform plan`/`apply` | requires AWS credentials + real S3 backend |
| `kubectl apply --dry-run=client` (schema-validated) | requires a reachable API server even in client mode (confirmed, not assumed) |
| `istioctl analyze` | requires a live Istio-installed mesh |
| Negative-connectivity test | requires a live cluster + live mTLS/AuthorizationPolicy enforcement |
| OpenShift template validation | out of scope for issue #43 (Helm/Terraform/Istio only) |
| Ansible/Puppet/Salt (`deploy/cm/`) validation | out of scope for issue #43 |
| Admin Portal / Java ticket-adapter suites | no files under those trees were touched this pass |

## External credential/cluster assumptions

None were made. No AWS account, kubeconfig, or live Istio mesh was assumed
to exist; every check above that would have needed one is listed as skipped
rather than simulated.

## Decision: why #43 stays open

Issue #43's own acceptance text (`docs/roadmap/index.md`, Phase 2 item 4)
and the linked issues #5/#12/#15/#17 collectively expect the *full* verified
chain — install, plan, live `istioctl analyze`, and a negative-connectivity
test — not only static/offline validation. Across all passes to date, every
offline/static check now passes (Helm, Terraform root + all 5 modules,
Istio); five real bugs have been found and fixed (two Helm, one Istio
schema, one Istio routing, one Terraform provider-constraint); and the
Istio dual-generation architecture question has been resolved by explicit
maintainer decision and applied (Generation A canonicalized, Generation B
relocated to a clearly-labeled, non-applied reference location, stale
`infra/` Terraform paths fixed in both tracked pipelines and their
referencing docs). What remains, and is **not** closed by this pass, is
entirely cluster/cloud-credential-gated:

1. Every check in the "Skipped checks" table above — `helm install`/
   `helm test`, `terraform plan`/`apply`, live `istioctl analyze`, and the
   negative-connectivity test — all require a provisioned cluster and/or
   AWS account that was not assumed, provided, or required by any pass.
2. Porting Generation B's `AuthorizationPolicy` and two-tier certificate
   strategy into the now-canonical generation remains explicitly deferred
   to a separate, future design issue — by the maintainer's own stated
   rationale, not something #43 is expected to resolve.

The `eks` Terraform module incompatibility that blocked the previous pass
is **resolved** (see the Terraform follow-up section above) and is no
longer a reason #43 stays open.

Per this task's own instruction ("Closes #43 only if the issue acceptance
contract is fully satisfied"), and per the Workhorse Contract's "no claim
outranks evidence" principle, issue #43 is **not closed** by this pass.
