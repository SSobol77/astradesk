# AstraDesk — Jenkins Pipeline Guide

This document explains how to run the production Jenkins pipeline defined in
`Jenkinsfile`.

## 1. Controller prerequisites
- Jenkins 2.414+ with Pipeline plugin.
- Agents (static or ephemeral) capable of running:
  - Docker (used in most stages via `agent { docker { image ... } }`)
  - Python 3.14, Java 25, Node 22 if you opt for bare-metal agents instead.
- SonarQube server accessible from the agents.
- Terraform CLI, Helm, kubectl, istioctl available on agents (or inside images).

## 2. Credentials & secrets
Create the following entries in **Manage Jenkins → Credentials** (IDs must match
the Jenkinsfile):

| ID                     | Type                               | Usage                               |
|------------------------|------------------------------------|-------------------------------------|
| `kubeconfig-astradesk` | Secret file                        | Kubeconfig for Helm/Kubectl stages  |
| `aws-credentials`      | AWS credentials                    | Terraform & AWS secret injection    |
| `admin-api-jwt`        | Secret text                        | JWT for Admin API `/secrets` calls  |
| `sonar-token`          | Secret text                        | SonarQube scanner authentication    |
| Docker registry creds  | Username/Password (`dockerhub`)    | Optional if pushing images          |

Configure global environment variables (Manage Jenkins → Configure System):
- `SONAR_HOST_URL` (e.g. `https://sonar.yourdomain`).
- `REGISTRY_URL` override if not using Docker Hub.

## 3. Pipeline setup
1. Create a **Multibranch Pipeline** or **Pipeline** job pointing at the repo.
2. Ensure “Lightweight checkout” is enabled (default) so the Jenkinsfile is read
   without full clone initially.
3. For multibranch: set branch sources to your Git provider; Jenkins will detect
   `Jenkinsfile` automatically.

## 4. Stage overview
1. **OpenAPI Sync** — keeps admin portal spec aligned.
2. **Checkout** — stashes source for reuse across parallel stages.
3. **Code Analysis & Tests** (parallel):
   - Python (ruff, mypy, pytest, coverage)
   - Java (Gradle `check`, Jacoco)
   - Node (lint + Jest)
4. **SonarQube Analysis** — aggregates coverage & runs scanner.
5. **Store AWS Secrets** — posts AWS creds into Admin API `/secrets`.
6. **Docker Build & Push** — multi-arch images + cosign signing (requires registry creds).
7. **Terraform Init/Plan/Apply** — uses `${TERRAFORM_DIR}` with AWS backend.
8. **Config Management Dry Runs** — Ansible, Puppet, Salt `--check`.
9. **Config Management Deploy** — full apply if dry runs succeeded.
10. **Istio Verification** — `istioctl analyze` plus mTLS strictness checks.
11. **Helm Deploy** — upgrades charts with image tags / DB endpoints from TF output.
12. **Post Actions** — archive artifacts, publish JUnit, notify Slack.

Refer to the Jenkinsfile comments for additional environment variables that may
need overriding per environment (e.g. `HELM_NAMESPACE`, `ADMIN_API_URL`).

## 5. Running the pipeline
- Trigger manually via “Build Now” or let SCM webhooks (GitHub/GitLab) kick off builds.
- Monitor stage logs in the Blue Ocean or classic UI.
- For debugging, re-run failed stages with “Replay” after adjusting parameters.

## 6. Troubleshooting tips
- Missing tools inside docker agent → extend the base image or switch to a node label.
- Terraform state lock issues → verify remote backend configuration.
- Helm failures due to image tags → ensure `IMAGE_TAG` computed by the script has been pushed to registry.
- Cosign signing errors → configure `COSIGN_PASSWORD` or use keyless mode if preferred.

