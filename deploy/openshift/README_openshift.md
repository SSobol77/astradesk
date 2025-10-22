# SPDX-License-Identifier: Apache-2.0
# OpenShift Configuration for AstraDesk

## Overview

The `deploy/openshift/` directory contains OpenShift templates for deploying the AstraDesk project in a production-ready environment. These templates define `DeploymentConfig`, `Service`, and `Route` resources for core services (`api`, `ticket-adapter`, `admin-portal`, `auditor`) and domain packs (`domain-support`). The configurations:
- Enable Istio sidecar injection for mTLS (`deploy/istio/10-peer-authentication.yaml`).
- Integrate with cert-manager for TLS/mTLS (`deploy/istio/certs/`).
- Support polyglot stack (Python 3.14+, Java 25+, Node.js 22, Postgres 18+).
- Use Admin API (`/secrets`) for certificate and token storage.

## Directory Contents

### astradesk-template.yaml
- **Purpose**: Deploys the main API service (`astradesk-api`) with Istio sidecar, mTLS, and TLS termination.
- **Functionality**:
  - Defines `DeploymentConfig` with 2 replicas, `Service` (port 80 -> 8080), and `Route` (TLS edge).
  - Uses environment variables (`DATABASE_URL`, `REDIS_URL`, `NATS_URL`, `OIDC_*`, `MTLS_CERT_PATH`).
  - Mounts `/secrets` for mTLS/TLS certificates.
- **Usage**: Main entry point for Admin API (`/api/admin/v1`).

### ticket-adapter-template.yaml
- **Purpose**: Deploys the Java-based Ticket Adapter (`astradesk-ticket-adapter`) with MySQL integration.
- **Functionality**:
  - Defines `DeploymentConfig` (2 replicas), `Service` (port 80 -> 8081).
  - Uses `MYSQL_URL_R2DBC` and mTLS certificates.
- **Usage**: Handles ticket storage for `services/ticket-adapter-java`.

### admin-portal-template.yaml
- **Purpose**: Deploys the Node.js-based Admin Portal (`astradesk-admin-portal`).
- **Functionality**:
  - Defines `DeploymentConfig` (2 replicas), `Service` (port 80 -> 3000), and `Route` (TLS edge).
  - Uses `NEXT_PUBLIC_API_URL` for API connectivity.
- **Usage**: Web interface for Admin API (`services/admin-portal`).

### auditor-template.yaml
- **Purpose**: Deploys the Auditor service (`astradesk-auditor`) with NATS and Postgres integration.
- **Functionality**:
  - Defines `DeploymentConfig` (2 replicas), `Service` (port 80 -> 8080).
  - Uses `NATS_URL`, `DATABASE_URL`, and mTLS certificates.
- **Usage**: Event auditing for `services/auditor`.

### domain-packs-template.yaml
- **Purpose**: Deploys domain packs (`domain-support`, etc.) with Istio sidecar.
- **Functionality**:
  - Defines `DeploymentConfig` (1 replica), `Service` (port 80 -> 8080).
  - Uses `API_URL`, `PACK_API_TOKEN`, and mTLS certificates.
- **Usage**: Extends functionality via `packages/domain-*`.

## Setup

### Prerequisites
- **OpenShift**: Cluster with Istio (1.18+) and cert-manager (1.15.3+) installed.
- **Tools**: `oc`, `kubectl`, `istioctl`, `make`.
- **Secrets**: `astradesk-mtls-secret`, `astradesk-tls` in `astradesk-prod` namespace.
- **Dependencies**: Postgres 18, MySQL 8, Redis 8, NATS 2 (defined in `docker-compose.yml`).
- **Registry**: Docker images in `docker.io/astradesk/*`.

### Steps
1. **Create Secrets**:
   ```bash
   oc create secret generic astradesk-mtls-secret --from-file=mtls-cert.pem=secrets/mtls-cert.pem -n astradesk-prod
   oc create secret generic astradesk-tls --from-file=tls-cert.pem=secrets/tls-cert.pem -n astradesk-prod
   ```

2. **Apply Istio Configurations**:
   ```bash
   make apply-istio
   ```

3. **Apply OpenShift Templates**:
   ```bash
   oc process -f deploy/openshift/astradesk-template.yaml | oc apply -f -
   oc process -f deploy/openshift/ticket-adapter-template.yaml | oc apply -f -
   oc process -f deploy/openshift/admin-portal-template.yaml | oc apply -f -
   oc process -f deploy/openshift/auditor-template.yaml | oc apply -f -
   oc process -f deploy/openshift/domain-packs-template.yaml | oc apply -f -
   ```

4. **Verify Deployment**:
   ```bash
   oc get pods -n astradesk-prod
   istioctl analyze -n astradesk-prod
   ```

5. **Store Certificates in Admin API**:
   ```bash
   make store-secrets
   ```

6. **Update Jenkinsfile**:
   ```groovy
   stage('Apply OpenShift Templates') {
     agent { docker { image 'bitnami/kubectl:latest' } }
     steps {
       withCredentials([file(credentialsId: 'kubeconfig-astradesk', variable: 'KUBECONFIG')]) {
         sh '''
           oc process -f deploy/openshift/astradesk-template.yaml | oc apply -f -
           oc process -f deploy/openshift/ticket-adapter-template.yaml | oc apply -f -
           oc process -f deploy/openshift/admin-portal-template.yaml | oc apply -f -
           oc process -f deploy/openshift/auditor-template.yaml | oc apply -f -
           oc process -f deploy/openshift/domain-packs-template.yaml | oc apply -f -
         '''
       }
     }
   }
   ```

7. **Update Makefile**:
   ```makefile
   # SPDX-License-Identifier: Apache-2.0
   apply-openshift: ## Apply OpenShift templates
ifndef HAS_OC
	@echo "Error: 'oc' not found." >&2; exit 1
endif
	oc process -f deploy/openshift/astradesk-template.yaml | oc apply -f -
	oc process -f deploy/openshift/ticket-adapter-template.yaml | oc apply -f -
	oc process -f deploy/openshift/admin-portal-template.yaml | oc apply -f -
	oc process -f deploy/openshift/auditor-template.yaml | oc apply -f -
	oc process -f deploy/openshift/domain-packs-template.yaml | oc apply -f -
   ```

## Testing

### Unit and Integration Tests
- **Python Tests**:
  ```bash
  make test-python
  ```
- **Java Tests**:
  ```bash
  make test-java
  ```
- **Node.js Tests**:
  ```bash
  make test-admin
  ```

### End-to-End Tests
- **API Healthcheck**:
  ```bash
  curl https://$(oc get route astradesk-api -n astradesk-prod -o jsonpath='{.spec.host}')/api/admin/v1/health
  ```
- **Istio Verification**:
  ```bash
  istioctl analyze -n astradesk-prod
  ```

## Troubleshooting
- **Pod Issues**:
  - Check logs: `oc logs -n astradesk-prod -l app=astradesk-api`.
  - Verify sidecar: `oc describe pod -n astradesk-prod | grep istio`.
- **mTLS Errors**:
  - Check secrets: `oc get secret -n astradesk-prod astradesk-mtls-secret`.
  - Verify Istio: `istioctl proxy-status -n astradesk-prod`.
- **Route Issues**:
  - Check route: `oc get route astradesk-api -n astradesk-prod -o yaml`.

## Integration with Admin API
- Certificates stored in `/secrets`:
  ```bash
  curl -X GET https://$(oc get route astradesk-api -n astradesk-prod -o jsonpath='{.spec.host}')/api/admin/v1/secrets/astradesk_mtls -H "Authorization: Bearer ${PACK_API_TOKEN}"
  ```

## Deployment
- **Production**:
  ```bash
  make apply-openshift
  ```

## Observability
- Metrics: OpenTelemetry traces via Istio (`pyproject.toml:opentelemetry`).
- Dashboards: Grafana (`grafana/dashboard-astradesk.json`).
- Logs: Published to NATS and stored in Postgres (`services/auditor`).

## Security
- mTLS: Enforced by `deploy/istio/10-peer-authentication.yaml`.
- TLS: Secured by `Route` (edge termination) and `deploy/istio/50-cert-manager-certificate.yaml`.
- RBAC: Controlled via `deploy/istio/30-authorizationpolicy-namespace.yaml`.

## License
Apache-2.0 (see SPDX in files).
