# AstraDesk Helm Chart

<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Description: README for the Helm chart in deploy/chart/. Covers chart structure, configuration, and deployment for AstraDesk services (api, ticket-adapter, admin-portal, auditor). -->
<!-- Author: Siergej Sobolewski -->
<!-- Since: 2025-10-22 -->

## Overview

The `deploy/chart/` directory contains the Helm chart for deploying the AstraDesk application to Kubernetes. It manages the deployment of polyglot services (`api`, `ticket-adapter`, `admin-portal`, `auditor`) with autoscaling (HPA, 60% CPU), Istio mTLS (STRICT), and HTTPS via cert-manager. The chart integrates with `deploy/istio/`, `infra/` (Terraform), and Admin API (`/secrets`) for a production-ready setup.

<br>

## Directory Structure

```sh
deploy/chart/
├── Chart.yaml          # Chart metadata (name, version, dependencies)
├── values.yaml         # Configurable values (images, replicas, autoscaling, env)
├── templates/          # Helm templates for Kubernetes resources
│   ├── deployment.yaml # Deployments for all services with Istio sidecar
│   ├── service.yaml    # Services for exposing all services
│   ├── hpa.yaml        # HorizontalPodAutoscaler (60% CPU) for all services
│   ├── tests/          # Helm test templates
│   │   ├── test-hpa.yaml  # Tests HPA configuration (CPU utilization)
│   │   ├── test-mtls.yaml # Tests mTLS STRICT and HTTPS connectivity
```

<br>

## Key Components

### Chart.yaml

Defines the chart metadata:

- **Name**: `astradesk`

- **Version**: `1.2.0`

- **Dependencies**: None (self-contained for AstraDesk services).

### values.yaml

Configures the chart with:

- **Images**: Docker image repositories and tags for `api`, `ticket-adapter`, `admin`, `auditor`.

- **Replicas**: Default replicas (e.g., `2` for each service).

- **Autoscaling**: Enabled with 60% CPU utilization, `minReplicas`, and `maxReplicas`.

- **Resources**: CPU/memory requests and limits.

- **Environment Variables**: `DATABASE_URL`, `NATS_URL`, `MYSQL_URL_R2DBC`, `PACK_API_TOKEN`.

Example snippet:

```yaml
api:
  image:
    repository: docker.io/youruser/astradesk-api
    tag: latest
  replicas: 2
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilizationPercentage: 60
```

### templates/deployment.yaml

Deploys all services (`api`, `ticket-adapter`, `admin`, `auditor`) with:

- Istio sidecar injection (`sidecar.istio.io/inject: "true"`).

- Service-specific ports (e.g., 8080 for `api`, 3000 for `admin`).

- Healthchecks (e.g., `/api/admin/v1/health` for `api`).

- Resource limits and environment variables from `values.yaml`.

### templates/service.yaml

Exposes services with Kubernetes Service resources:

- Maps internal ports (8080 or 3000) to Istio-compatible ports.

- Supports routing via Istio `VirtualService` and `Gateway`.

### templates/hpa.yaml

Configures HorizontalPodAutoscaler for each service:

- Targets 60% CPU utilization.

- Scales between `minReplicas` and `maxReplicas` from `values.yaml`.

### templates/tests/test-hpa.yaml

Validates HPA configuration by checking CPU utilization settings (`kubectl get hpa`).

### templates/tests/test-mtls.yaml

Tests mTLS STRICT and HTTPS connectivity by executing `curl` via Istio proxy to `https://api.astradesk.local/api/admin/v1/health`.

<br>

## Prerequisites

- **Kubernetes**: EKS cluster (configured via `infra/main.tf`).

- **Helm**: Version 3.15.3 or higher.

- **Istio**: Installed with demo profile (`istioctl install --set profile=demo`).

- **cert-manager**: Installed for TLS certificates (`kubectl apply -f cert-manager.yaml`).

- **Docker Registry**: Images pushed to `docker.io/youruser` (configured in `values.yaml`).

- **Terraform Outputs**: RDS endpoints for Postgres and MySQL.

- **Admin API**: Available at `http://localhost:8080/api/admin/v1` for secrets management.

<br>

## Deployment

1. **Install Dependencies**:

   ```bash
   istioctl install --set profile=demo -y
   kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.15.3/cert-manager.yaml
   ```

2. **Apply Istio Configurations**:

   ```bash
   kubectl apply -f deploy/istio/
   ```

3. **Deploy Chart**:

   Use the `Jenkinsfile` or run manually:

   ```bash
   helm upgrade --install astradesk deploy/chart \
       --namespace astradesk-prod \
       --create-namespace \
       --wait --timeout 5m \
       --set api.image.repository=docker.io/youruser/astradesk-api \
       --set api.image.tag=<commit-hash> \
       --set ticketAdapter.image.repository=docker.io/youruser/astradesk-ticket \
       --set ticketAdapter.image.tag=<commit-hash> \
       --set admin.image.repository=docker.io/youruser/astradesk-admin \
       --set admin.image.tag=<commit-hash> \
       --set auditor.image.repository=docker.io/youruser/astradesk-auditor \
       --set auditor.image.tag=<commit-hash> \
       --set database.postgres.host=<rds-postgres-endpoint> \
       --set database.mysql.host=<rds-mysql-endpoint>
   ```

4. **Run Tests**:

   ```bash
   helm test astradesk --namespace astradesk-prod
   ```

## Verification

- **Check Pods**:

  ```bash
  kubectl get pods -n astradesk-prod
  ```

- **Verify mTLS**:

  ```bash
  kubectl get peerauthentication -n astradesk-prod -o jsonpath='{.items[*].spec.mtls.mode}'
  ```

- **Test HTTPS**:

  ```bash
  curl -k https://api.astradesk.local/api/admin/v1/health
  ```

- **Check HPA**:

  ```bash
  kubectl get hpa -n astradesk-prod
  ```

- **Analyze Istio**:

  ```bash
  istioctl analyze -n astradesk-prod
  ```

<br>

## Integration

- **Jenkinsfile**: Automates deployment (`Deploy to Kubernetes` stage) and Istio configuration (`Apply Istio Configs`, `Test Istio mTLS`).

- **Terraform**: Provides RDS endpoints (`rds_postgres_endpoint`, `rds_mysql_endpoint`) in `infra/`.

- **Istio**: Configures mTLS STRICT and HTTPS via `deploy/istio/` (`gateway.yaml`, `virtualservice.yaml`, `peerauthentication.yaml`, `certmanager.yaml`).

- **Admin API**: Stores TLS certificates in `/secrets` (`astradesk_mtls`).

- **Ansible/Puppet/Salt**: Supports configuration management for Docker Compose deployments.

<br>

## Notes

- Replace `docker.io/youruser` with your Docker registry in `values.yaml`.

- Ensure `PACK_API_TOKEN` is set in `.env` for Admin API authentication.

- Autoscaling is configured for 60% CPU utilization (issue #12).

- mTLS is enforced in STRICT mode with cert-manager for HTTPS (issue #15).

<br>

## License

This project is licensed under the Apache License 2.0. See the `LICENSE` file for details.
