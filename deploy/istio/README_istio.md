# SPDX-License-Identifier: Apache-2.0
# Istio Configuration for AstraDesk

## Overview

The `deploy/istio/` directory contains Istio configurations for the AstraDesk project, enabling service mesh capabilities for the `astradesk` namespace. These configurations manage:
- Namespace setup with Istio sidecar injection.
- Mutual TLS (mTLS) for secure Pod-to-Pod communication.
- External traffic routing via Istio Gateway and VirtualService.
- Authorization policies for traffic control.
- TLS certificate management with cert-manager integration.

This directory integrates with:
- `deploy/istio/certs/` for certificate configurations (e.g., Let's Encrypt, internal CA).
- `services/ticket-adapter-java/` and `packages/domain-support/` for service connectivity.
- Admin API (`/secrets`) for storing certificates and secrets.
- Helm charts (`deploy/chart/`) for deployment.
- Grafana dashboards (`grafana/dashboard-astradesk.json`) for monitoring.

## Directory Contents

### 00-namespace.yaml
- **Purpose**: Defines the `astradesk` namespace with Istio sidecar injection enabled.
- **Functionality**:
  - Creates the `astradesk` namespace.
  - Enables automatic Envoy sidecar injection for all Pods (`istio-injection: enabled`).
  - Adds label `app: astradesk` for workload grouping and monitoring.
- **Usage**: Ensures all services (e.g., `astradesk-api`, `domain-support`, `ticket-adapter-java`) run with Istio sidecars for mTLS and traffic management.
- **Dependencies**: Required for all other Istio configurations in this directory.

### 10-peer-authentication.yaml
- **Purpose**: Enforces mandatory mutual TLS (mTLS) for all traffic in the `astradesk` namespace.
- **Functionality**:
  - Sets `mtls.mode: STRICT` to require mTLS for all Pod-to-Pod communication.
  - Optionally restricts to workloads with label `app: astradesk`.
- **Usage**: Secures internal communication (e.g., between `domain-support` and `astradesk-api`) using Istio certificates.
- **Dependencies**: Requires certificates from `50-cert-manager-certificate.yaml` or `deploy/istio/certs/`.

### 20-destinationrule-astradesk-api.yaml
- **Purpose**: Configures traffic policy for the `astradesk-api` service.
- **Functionality**:
  - Enforces `ISTIO_MUTUAL` mTLS for connections to `astradesk-api.astradesk.svc.cluster.local:8080`.
  - Specifies port-level mTLS settings for consistency with `41-virtualservice-astradesk-api.yaml`.
- **Usage**: Ensures secure communication to the API service, used by `domain-support` tools (e.g., `asana_adapter.py`, `slack_adapter.py`).
- **Dependencies**: Works with `10-peer-authentication.yaml` and `41-virtualservice-astradesk-api.yaml`.

### 30-authorizationpolicy-namespace.yaml
- **Purpose**: Restricts traffic in the `astradesk` namespace to authorized sources.
- **Functionality**:
  - Allows traffic only from within the `astradesk` namespace or from Istio IngressGateway (`istio-system/istio-ingressgateway-service-account`).
  - Applies to workloads with label `app: astradesk`.
- **Usage**: Enhances security by limiting access to services like `astradesk-api` and `ticket-adapter-java`.
- **Dependencies**: Requires `00-namespace.yaml` and `40-gateway.yaml`.

### 40-gateway.yaml
- **Purpose**: Defines an Istio Gateway for external HTTPS traffic.
- **Functionality**:
  - Configures port 443 with TLS (`SIMPLE` mode) using the `astradesk-tls` Secret.
  - Supports host `api.astradesk.example.com` (requires update to production FQDN).
  - Enforces minimum TLS version (`TLSV1_2`).
- **Usage**: Serves as the public entry point for the AstraDesk API, routing external traffic to `astradesk-api`.
- **Dependencies**: Requires `astradesk-tls` from `50-cert-manager-certificate.yaml`.

### 41-virtualservice-astradesk-api.yaml
- **Purpose**: Maps external host to the `astradesk-api` service.
- **Functionality**:
  - Routes all HTTP(S) traffic for `api.astradesk.example.com` to `astradesk-api:8080` via the `astradesk-gw` Gateway.
  - Supports weighted routing (default 100%) for potential canary deployments.
- **Usage**: Enables external access to the Admin API (e.g., `/api/admin/v1`) for `domain-support` tools.
- **Dependencies**: Requires `40-gateway.yaml` and `20-destinationrule-astradesk-api.yaml`.

### 50-cert-manager-certificate.yaml
- **Purpose**: Defines TLS and mTLS certificates managed by cert-manager.
- **Functionality**:
  - Creates `astradesk-tls` for Gateway TLS (`api.astradesk.example.com`).
  - Creates `astradesk-mtls-cert` for internal mTLS (`*.astradesk.local`).
  - Uses `letsencrypt-prod` (external TLS) and `astradesk-ca` (mTLS) ClusterIssuers.
- **Usage**: Provides certificates for secure external and internal communication.
- **Dependencies**: Requires `deploy/istio/certs/` (ClusterIssuers and CA cert).

### certs/
- **Purpose**: Contains cert-manager configurations for ClusterIssuers and CA certificates.
- **Files**:
  - `letsencrypt-prod-clusterissuer.yaml`: ClusterIssuer for Let's Encrypt (external TLS).
  - `astradesk-ca-clusterissuer.yaml`: ClusterIssuer for internal CA (mTLS).
  - `astradesk-ca-certificate.yaml`: Root CA certificate for mTLS.
  - `README.md`: Documentation for certificate setup.
- **Usage**: Manages certificates referenced in `50-cert-manager-certificate.yaml`.
- **Dependencies**: Requires cert-manager installed in the cluster.

### readme.md
- **Purpose**: This file, documenting the `deploy/istio/` directory and its configurations.

## Setup

### Prerequisites
- **Kubernetes**: Cluster with Istio installed (version 1.18+ recommended).
- **cert-manager**: Installed for certificate management (`kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.15.3/cert-manager.yaml`).
- **Tools**: `kubectl`, `istioctl`, Helm.
- **Admin API**: Running at `http://localhost:8080/api/admin/v1` with JWT token for `/secrets`.
- **Dependencies**: Postgres 18, Redis, NATS (defined in `docker-compose.yml`).

### Steps
1. **Create certs/ Directory** (if not exists):
   ```bash
   mkdir -p deploy/istio/certs
   ```

2. **Apply Configurations**:
   ```bash
   kubectl apply -f deploy/istio/
   ```

3. **Verify Namespace and Sidecar Injection**:
   ```bash
   kubectl get namespace astradesk -o yaml  # Check istio-injection: enabled
   ```

4. **Verify Certificates**:
   ```bash
   kubectl get certificate -n astradesk astradesk-tls astradesk-mtls-cert astradesk-ca -o yaml
   kubectl get secret -n astradesk astradesk-tls astradesk-mtls-secret astradesk-ca-secret
   ```

5. **Store Certificates in Admin API**:
   ```bash
   kubectl get secret -n astradesk astradesk-mtls-secret -o jsonpath='{.data.tls\.crt}' | base64 -d > mtls-cert.pem
   curl -X POST http://localhost:8080/api/admin/v1/secrets -H "Authorization: Bearer ${JWT}" -d '{
     "name": "astradesk_mtls",
     "type": "certificate",
     "value": "'"$(cat mtls-cert.pem)"'"
   }'
   ```

6. **Update CI/CD (Jenkinsfile)**:
   ```groovy
   stage('Apply Istio Configs') {
     sh 'kubectl apply -f deploy/istio/'
   }
   ```

7. **Update Makefile**:
   ```makefile
   # SPDX-License-Identifier: Apache-2.0
   apply-istio: ## Apply Istio configurations
       kubectl apply -f deploy/istio/
   ```

## Testing

### Unit and Integration Tests
- **Verify mTLS and TLS**:
  - Add tests in `packages/domain-support/tests/test_triage.py` to mock mTLS failures (e.g., 401/403 from `/secrets`).
  - Example:
    ```python
    # SPDX-License-Identifier: Apache-2.0
    import pytest
    from ..tools.asana_adapter import AsanaAdapter

    @pytest.mark.asyncio
    async def test_asana_mtls_failure():
        adapter = AsanaAdapter(api_url="http://localhost:8080/api/admin/v1", token="invalid")
        with pytest.raises(ValueError, match="401"):
            await adapter.create_task({"name": "Test Task"})
    ```
  - Run tests:
    ```bash
    cd packages/domain-support
    uv run pytest tests
    ```

- **Run All Pack Tests**:
  ```bash
  make test-packs
  ```

### End-to-End Tests
- **Test Gateway**:
  ```bash
  curl -k https://api.astradesk.example.com/api/admin/v1/health  # Replace with prod FQDN
  ```

- **Test Istio Configuration**:
  ```bash
  istioctl analyze -n astradesk
  ```

- **Playwright UI Tests** (for `services/admin-portal`):
  ```bash
  cd services/admin-portal
  npx playwright test
  ```

## Troubleshooting

- **Namespace Issues**:
  - Verify sidecar injection: `kubectl describe pod -n astradesk | grep istio`.
  - Fix: Ensure `istio-injection: enabled` in `00-namespace.yaml`.

- **mTLS Errors**:
  - Check Istio logs: `istioctl proxy-status -n astradesk`.
  - Verify certificates: `kubectl describe certificate -n astradesk astradesk-mtls-cert`.

- **Gateway/Routing Issues**:
  - Check VirtualService: `kubectl get virtualservice -n astradesk astradesk-api -o yaml`.
  - Verify IngressGateway logs: `kubectl logs -n istio-system -l istio=ingressgateway`.

- **Certificate Issues**:
  - Check cert-manager logs: `kubectl logs -n cert-manager -l app=cert-manager`.
  - Verify ClusterIssuers: `kubectl describe clusterissuer letsencrypt-prod astradesk-ca`.

- **API Errors**:
  - Monitor Grafana (`grafana/dashboard-astradesk.json`) for 5xx errors.
  - Check Admin API logs: `kubectl logs -n astradesk -l app=astradesk-api`.

## Integration with Admin API
- **Store Certificates**:
  - Certificates (`astradesk-tls`, `astradesk-mtls-secret`) are stored in `/secrets` for use in tools (e.g., `asana_adapter.py`, `slack_adapter.py`).
  - Example:
    ```bash
    curl -X GET http://localhost:8080/api/admin/v1/secrets/astradesk_mtls -H "Authorization: Bearer ${JWT}"
    ```

- **RBAC**:
  - Ensure `admin` or `operator` role for `/secrets` access (via `src/runtime/auth.py`).

## Deployment
- **Local**:
  ```bash
  make up  # Starts dependencies (docker-compose.yml)
  kubectl apply -f deploy/istio/
  ```

- **Production**:
  ```bash
  make helm-deploy  # Deploys via Helm (deploy/chart/)
  ```

## Observability
- **Metrics**: OpenTelemetry traces for Istio traffic (`pyproject.toml:opentelemetry`).
- **Dashboards**: Grafana (`grafana/dashboard-astradesk.json`) with mTLS and API metrics.
- **Logs**: Published to NATS and stored in Postgres (`services/auditor`).

## Security
- **mTLS**: Enforced by `10-peer-authentication.yaml` and `20-destinationrule-astradesk-api.yaml`.
- **TLS**: Secured by `40-gateway.yaml` and `50-cert-manager-certificate.yaml`.
- **RBAC**: Controlled via `30-authorizationpolicy-namespace.yaml` and `src/runtime/auth.py`.
- **Secrets**: Managed via `/secrets` and Kubernetes Secrets (`deploy/chart/`).

## Contributing
- Fork the repository and create a branch (`git checkout -b istio-config-update`).
- Update configurations and test with `istioctl analyze` and `kubectl apply`.
- Submit a PR with changes and updated `deploy/istio/README.md`.
- Ensure `make test-packs` passes.

## License
Apache-2.0 (see SPDX in files).
