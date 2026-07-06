<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: deploy/istio/deploy_istio_README.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# Istio Configuration for AstraDesk

## Overview

The `deploy/istio/` directory contains Istio configurations for the AstraDesk project, enabling service mesh capabilities in the `astradesk-prod` namespace. It provides:

- Namespace setup with Istio sidecar injection.

- Mutual TLS (mTLS) in STRICT mode for secure Pod-to-Pod communication.

- External HTTPS traffic routing (port 443) via Istio Gateway and VirtualService.

- TLS certificate management with cert-manager.

- Integration with Helm charts (`deploy/chart/`), Admin API (`/secrets`), Terraform (`deploy/infra/`), and configuration management (Ansible/Puppet/Salt).

This directory supports the polyglot stack:

- **Python 3.13+**: `api` (FastAPI), `auditor`.

- **Java 21**: `ticket-adapter`.

- **Node.js 22**: `admin-portal`.

- **Postgres 18**: Database for `api` and `auditor`.

<br>

## Directory Contents

```sh
deploy/istio/
├── peerauthentication.yaml     # Enforces mTLS STRICT for all services
├── gateway.yaml                # Configures HTTPS Gateway on port 443
├── virtualservice.yaml         # Routes external traffic to services
├── certmanager.yaml            # Manages TLS certificates via cert-manager
├── deploy_istio_README.md      # This file
├── readme.md                   # Short apply-order note (this generation)
└── generation-b-reference/     # NOT applied by any tracked pipeline — see below

```

**`astradesk-prod` is not created by any file in this directory.** Both
tracked CI/CD pipelines (`Jenkinsfile`, `.gitlab-ci.yml`) create it via
`helm upgrade --install ... --namespace astradesk-prod --create-namespace`
before applying these Istio manifests; sidecar injection for its pods comes
from the Helm chart's own per-pod `sidecar.istio.io/inject: "true"`
annotation (`deploy/chart/templates/deployment.yaml`), not from a
namespace-level label.

### `generation-b-reference/` — reference only, not applied

`deploy/istio/generation-b-reference/` holds a second, independent
generation of Istio manifests (namespace `astradesk`, adds an
`AuthorizationPolicy` and a `DestinationRule` this directory's generation
does not have) that used to sit at this same flat directory level. It is
**not** referenced by either tracked pipeline and currently routes only the
API service (no route for `ticket-adapter`, `admin`, or `auditor`). See
`generation-b-reference/README.md` and
`audit/evidence/43_deployability_verification.md` ("Istio dual-generation
inventory") for the full comparison and why this directory's generation was
chosen as canonical.

### peerauthentication.yaml

- **Purpose**: Enforces mTLS in STRICT mode for all traffic in `astradesk-prod`.

- **Functionality**:
  - Sets `mtls.mode: STRICT` for Pod-to-Pod communication.
  - Applies to all workloads in the namespace.

- **Usage**: Secures internal communication between services (e.g., `api` to `auditor`, `ticket-adapter` to `admin`).

- **Dependencies**: Requires certificates from `certmanager.yaml` or `certs/`.

### gateway.yaml

- **Purpose**: Configures an Istio Gateway for external HTTPS traffic.

- **Functionality**:
  - Exposes port 443 with TLS (`SIMPLE` mode) using `astradesk-tls` Secret.
  - Supports hosts `*.astradesk.local` (configurable for production FQDN).

- **Usage**: Routes external traffic to services via `virtualservice.yaml`.

- **Dependencies**: Requires `astradesk-tls` from `certmanager.yaml`.

### virtualservice.yaml

- **Purpose**: Routes external HTTPS traffic to AstraDesk services.

- **Functionality**:
  - Maps hosts (`api.astradesk.local`, `ticket.astradesk.local`, `admin.astradesk.local`, `auditor.astradesk.local`) to services.
  - Routes paths (`/api`, `/ticket`, `/`, `/auditor`) to respective services (`api:8080`, `ticket-adapter:8080`, `admin:3000`, `auditor:8080`).

- **Usage**: Enables external access to Admin API (`/api/admin/v1`) and other services.

- **Dependencies**: Requires `gateway.yaml`.

### certmanager.yaml

- **Purpose**: Manages TLS certificates for Gateway and mTLS.

- **Functionality**:
  - Defines self-signed `Issuer` and `Certificate` for `astradesk-tls`.
  - Covers `*.astradesk.local` and subdomains (`api.astradesk.local`, etc.).

- **Usage**: Provides certificates for HTTPS (port 443) and internal mTLS.

- **Dependencies**: Requires `certs/astradesk-ca-clusterissuer.yaml` or `letsencrypt-prod-clusterissuer.yaml`.

### certs/

- **Purpose**: Stores cert-manager configurations for ClusterIssuers and CA certificates.

- **Files**:
  - `letsencrypt-prod-clusterissuer.yaml`: ClusterIssuer for Let's Encrypt (external TLS).
  - `astradesk-ca-clusterissuer.yaml`: ClusterIssuer for internal CA (mTLS).
  - `astradesk-ca-certificate.yaml`: Root CA certificate for mTLS.
  - `README.md`: Instructions for certificate setup.

- **Usage**: Manages certificates for `certmanager.yaml` and `gateway.yaml`.

- **Dependencies**: Requires cert-manager installed.

### README.markdown

- **Purpose**: This file, documenting the `deploy/istio/` directory.

<br>

## Setup

### Prerequisites

- **Kubernetes**: EKS cluster (configured via `deploy/infra/main.tf`).

- **Istio**: Version 1.18+ (`istioctl install --set profile=demo -y`).

- **cert-manager**: Version 1.15.3 (`kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.15.3/cert-manager.yaml`).

- **Tools**: `kubectl`, `istioctl`, `helm`, `curl`.

- **Admin API**: Running at `http://localhost:8080/api/admin/v1` with `PACK_API_TOKEN`.

- **Dependencies**: Postgres 18, MySQL, Redis, NATS (via `docker-compose.yml` or `deploy/chart/`).

### Steps

1. **Install cert-manager and Istio**:

   ```bash
   kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.15.3/cert-manager.yaml
   istioctl install --set profile=demo -y

   ```

2. **Apply Istio Configurations**:

   ```bash
   kubectl apply -f deploy/istio/

   ```

3. **Verify Namespace**:

   ```bash
   kubectl get namespace astradesk-prod -o yaml
   # Ensure istio-injection: enabled

   ```

4. **Verify Certificates**:

   ```bash
   kubectl get certificate -n astradesk-prod astradesk-tls -o yaml
   kubectl get secret -n astradesk-prod astradesk-tls -o yaml

   ```

5. **Store Certificates in Admin API**:

   ```bash
   kubectl get secret -n astradesk-prod astradesk-tls -o jsonpath='{.data.tls\.crt}' | base64 -d > mtls-cert.pem
   curl -X POST http://localhost:8080/api/admin/v1/secrets -H "Authorization: Bearer ${PACK_API_TOKEN}" -d '{
     "name": "astradesk_mtls",
     "type": "certificate",
     "value": "'"$(cat mtls-cert.pem)"'"
   }'
   rm -f mtls-cert.pem

   ```

6. **Update CI/CD (Jenkinsfile)**:

   ```groovy
   stage('Apply Istio Configs') {
       agent { docker { image 'bitnami/kubectl:latest' } }
       steps {
           unstash 'source'
           withCredentials([file(credentialsId: 'kubeconfig-astradesk', variable: 'KUBECONFIG')]) {
               retry(3) {
                   sh 'kubectl apply -f deploy/istio/ --kubeconfig=$KUBECONFIG'
                   sh 'istioctl analyze -n astradesk-prod --kubeconfig=$KUBECONFIG'
               }
           }
       }
   }
   stage('Test Istio mTLS') {
       agent { docker { image 'bitnami/kubectl:latest' } }
       steps {
           unstash 'source'
           withCredentials([file(credentialsId: 'kubeconfig-astradesk', variable: 'KUBECONFIG')]) {
               sh '''
                   kubectl get peerauthentication -n astradesk-prod -o jsonpath='{.items[*].spec.mtls.mode}' | grep -q STRICT || exit 1
                   kubectl exec -n astradesk-prod -c istio-proxy $(kubectl get pod -l app=astradesk-api -n astradesk-prod -o jsonpath='{.items[0].metadata.name}') --kubeconfig=$KUBECONFIG -- curl -k https://api.astradesk.local/api/admin/v1/health > mtls-test.log 2>&1
               '''
               stash name: 'mtls-test-log', includes: 'mtls-test.log'
           }
       }
   }

   ```

7. **Update Makefile**:

   ```makefile
   # SPDX-License-Identifier: GPL-2.0-only
   apply-istio: ## Apply Istio configurations
       kubectl apply -f deploy/istio/
   verify-istio: ## Verify Istio configurations
       istioctl analyze -n astradesk-prod
   verify-mtls: ## Verify mTLS configuration
       kubectl get peerauthentication -n astradesk-prod -o jsonpath='{.items[*].spec.mtls.mode}' | grep -q STRICT && echo "mTLS is STRICT" || exit 1
       helm test astradesk --namespace astradesk-prod

   ```

<br>

## Testing

### Unit and Integration Tests

- **Verify mTLS**:

  - Add tests in `packages/domain-support/tests/test_triage.py` for mTLS validation.

  - Example:

    ```python
    # SPDX-License-Identifier: GPL-2.0-only
    import pytest
    from ..tools.asana_adapter import AsanaAdapter

    @pytest.mark.asyncio
    async def test_asana_mtls_failure():
        adapter = AsanaAdapter(api_url="https://api.astradesk.local/api/admin/v1", token="invalid")
        with pytest.raises(ValueError, match="401"):
            await adapter.create_task({"name": "Test Task"})
    ```

  - Run:

    ```bash
    cd packages/domain-support
    uv run pytest tests
    ```

- **Run All Pack Tests**:

  ```bash
  make test-packs
  ```

### End-to-End Tests

- **Test HTTPS**:

  ```bash
  curl -k https://api.astradesk.local/api/admin/v1/health
  ```

- **Test Istio Configuration**:

  ```bash
  istioctl analyze -n astradesk-prod
  ```

- **Test mTLS**:

  ```bash
  make verify-mtls
  ```

- **Playwright UI Tests** (for `admin-portal`):

  ```bash
  cd services/admin-portal
  npx playwright test
  ```

## Troubleshooting

- **Namespace Issues**:

  - Verify sidecar injection:

    ```bash
    kubectl describe pod -n astradesk-prod | grep istio
    ```

  - Fix: Ensure `istio-injection: enabled` in `00-namespace.yaml`.

- **mTLS Errors**:
  - Check proxy status:

    ```bash
    istioctl proxy-status -n astradesk-prod
    ```

  - Verify certificates:

    ```bash
    kubectl describe certificate -n astradesk-prod astradesk-tls
    ```

- **Gateway/Routing Issues**:

  - Check VirtualService:

    ```bash
    kubectl get virtualservice -n astradesk-prod astradesk-vs -o yaml
    ```

  - Check IngressGateway logs:

    ```bash
    kubectl logs -n istio-system -l istio=ingressgateway
    ```

- **Certificate Issues**:

  - Check cert-manager logs:

    ```bash
    kubectl logs -n cert-manager -l app=cert-manager
    ```

  - Verify ClusterIssuers:

    ```bash
    kubectl describe clusterissuer letsencrypt-prod astradesk-ca
    ```

- **API Errors**:

  - Monitor Grafana (`grafana/dashboard-astradesk.json`) for 5xx errors.

  - Check API logs:

    ```bash
    kubectl logs -n astradesk-prod -l app=astradesk-api
    ```

<br>

## Integration

- **Helm Charts** (`deploy/chart/`):

  - Deploys services with Istio sidecar injection (`sidecar.istio.io/inject: "true"`).

  - Configures autoscaling (HPA, 60% CPU) via `hpa.yaml`.

  - Tests mTLS and HTTPS via `test-mtls.yaml` and `test-hpa.yaml`.

- **Admin API** (`/secrets`):

  - Stores `astradesk-tls` certificate for use in `asana_adapter.py`, `slack_adapter.py`, etc.

  - Example:

    ```bash
    curl -X GET http://localhost:8080/api/admin/v1/secrets/astradesk_mtls -H "Authorization: Bearer ${PACK_API_TOKEN}"
    ```

- **Configuration Management**:

  - **Ansible**: `ansible/playbook.yml` applies Istio configs and secrets.

  - **Puppet**: `puppet/manifests/astradesk.pp` manages certificates.

  - **Salt**: `salt/astradesk/init.sls` configures mTLS.

- **CI/CD** (`Jenkinsfile`):

  - Stages: `Apply Istio Configs`, `Test Istio mTLS`, `Store Certificates in Admin API`, `Deploy to Kubernetes`.

  - Archives `mtls-test.log` for test verification.

- **Observability**:

  - Metrics: OpenTelemetry traces (`pyproject.toml:opentelemetry`).

  - Dashboards: Grafana (`grafana/dashboard-astradesk.json`).

  - Logs: NATS and Postgres via `services/auditor`.

<br>

## Security

- **mTLS**: STRICT mode enforced by `peerauthentication.yaml`.

- **TLS**: HTTPS on port 443 via `gateway.yaml` and `certmanager.yaml`.

- **RBAC**: Controlled via `src/runtime/auth.py` and Kubernetes RBAC.

- **Secrets**: Managed via `/secrets` and Kubernetes Secrets (`astradesk-tls`).

<br>

## Contributing

- Fork the repository and create a branch:

  ```bash
  git checkout -b istio-config-update
  ```

- Update configurations and test:

  ```bash
  istioctl analyze -n astradesk-prod
  kubectl apply -f deploy/istio/
  ```

- Submit a PR with updated `README.markdown`.

- Ensure `make test-packs` and `make verify-mtls` pass.

<br>

## License

Licensed under the GNU General Public License version 2 only. See the `LICENSE` file for details.
