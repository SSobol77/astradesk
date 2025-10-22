# SPDX-License-Identifier: Apache-2.0
# Certificates Configuration for AstraDesk

## Overview

The `deploy/istio/certs/` directory contains cert-manager configurations for TLS and mTLS certificates used in the AstraDesk project. These certificates secure:
- External traffic via Istio Gateway (e.g., `api.astradesk.example.com`).
- Internal Pod-to-Pod traffic with mTLS in the `astradesk` namespace (STRICT mode).

Certificates are managed by cert-manager and integrated with Istio (`10-peer-authentication.yaml`, `50-cert-manager-certificate.yaml`) and Admin API (`/secrets`).

## Files

- `letsencrypt-prod-clusterissuer.yaml`: ClusterIssuer for Let's Encrypt (external TLS for Gateway).
- `astradesk-ca-clusterissuer.yaml`: ClusterIssuer for internal CA (mTLS for Pod-to-Pod traffic).
- `astradesk-ca-certificate.yaml`: Root CA certificate for mTLS (stored in `astradesk-ca-secret`).
- `README.md`: This file.

## Setup

### Prerequisites
- cert-manager installed in the cluster (`kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.15.3/cert-manager.yaml`).
- Istio installed with mTLS enabled (`deploy/istio/10-peer-authentication.yaml`).
- Admin API running (`http://localhost:8080/api/admin/v1`) with JWT token for `/secrets`.
- Kubectl and Helm installed.

### Steps
1. **Create certs/ Directory**:
   ```bash
   mkdir -p deploy/istio/certs
   ```

2. **Apply Configurations**:
   ```bash
   kubectl apply -f deploy/istio/certs/
   ```

3. **Verify ClusterIssuers**:
   ```bash
   kubectl get clusterissuer letsencrypt-prod astradesk-ca -o yaml
   ```

4. **Verify Certificates**:
   ```bash
   kubectl get certificate -n astradesk astradesk-ca astradesk-tls astradesk-mtls-cert -o yaml
   kubectl get secret -n astradesk astradesk-ca-secret astradesk-tls astradesk-mtls-secret
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
   stage('Apply Cert-Manager Configs') {
     sh 'kubectl apply -f deploy/istio/certs/'
   }
   ```

## Usage
- **Gateway TLS**: Use `astradesk-tls` Secret for Istio Gateway (`deploy/istio/40-gateway.yaml`).
- **mTLS**: Use `astradesk-mtls-secret` for Pod-to-Pod mTLS (referenced in `10-peer-authentication.yaml`).
- **Admin API**: Fetch certificates from `/secrets/astradesk_mtls` in tools (e.g., `packages/domain-support/tools/asana_adapter.py`).

## Troubleshooting
- **Certificate Not Issued**:
  - Check cert-manager logs: `kubectl logs -n cert-manager -l app=cert-manager`.
  - Verify ClusterIssuer status: `kubectl describe clusterissuer letsencrypt-prod`.
- **mTLS Errors**:
  - Check Istio logs: `istioctl analyze -n astradesk`.
  - Ensure Pods have Istio sidecar: `kubectl describe pod -n astradesk`.
- **Secrets API**:
  - Verify JWT: `curl -X GET http://localhost:8080/api/admin/v1/secrets -H "Authorization: Bearer ${JWT}"`.

## License
Apache-2.0 (see SPDX in files).