###### SPDX-License-Identifier: Apache-2.0

# AWS Infrastructure for AstraDesk

## Overview

The `infra/` directory contains Terraform configurations for deploying the AstraDesk infrastructure on AWS. It provisions a VPC, EKS cluster, RDS instances (Postgres and MySQL), and an S3 bucket for artifacts. The setup is production-ready, integrating with:
- **Istio**: mTLS and Gateway (`deploy/istio/`).
- **cert-manager**: TLS certificates (`deploy/istio/certs/`).
- **Admin API**: `/secrets` for AWS credentials (OpenAPI 3.1.0).
- **Polyglot Stack**: Python 3.14+ (API), Java 25+ (ticket-adapter), Node.js 22 (admin-portal), Postgres 18+.
- **CI/CD**: Jenkinsfile (`terraform plan/apply`), Makefile (`terraform-init`, `terraform-apply`).

## Directory Structure

```sh
infra/
├── main.tf              # Main Terraform file with backend and module calls
├── variables.tf         # Project variables
├── outputs.tf           # Project outputs
├── README.md            # This file
└── modules/
    ├── vpc/             # VPC module (terraform-aws-modules/vpc/aws)
    ├── eks/             # EKS module (terraform-aws-modules/eks/aws)
    ├── rds-postgres/    # RDS Postgres module
    ├── rds-mysql/       # RDS MySQL module
    └── s3/              # S3 module (terraform-aws-modules/s3-bucket/aws)
```

## Prerequisites

- **Terraform**: v1.7.0+.
- **AWS CLI**: Configured with credentials (`aws configure`).
- **Tools**: `kubectl`, `istioctl`, `helm`.
- **Dependencies**: AWS account with permissions for VPC, EKS, RDS, S3.
- **Admin API**: Running at `http://localhost:8080/api/admin/v1` with JWT for `/secrets`.

## Setup

1. **Initialize Terraform**:
   ```bash
   cd infra
   terraform init
   ```

2. **Configure Variables**:
   Create `terraform.tfvars`:
   ```hcl
   region = "eu-central-1"
   project = "astradesk"
   db_name_postgres = "astradesk"
   db_username_postgres = "astradesk"
   db_password_postgres = "astrapass"
   db_name_mysql = "tickets"
   db_username_mysql = "tickets"
   db_password_mysql = "tickets"
   ```

3. **Plan and Apply**:
   ```bash
   terraform plan -var-file="terraform.tfvars"
   terraform apply -var-file="terraform.tfvars" -auto-approve
   ```

4. **Store AWS Credentials in Admin API**:
   ```bash
   curl -X POST http://localhost:8080/api/admin/v1/secrets -H "Authorization: Bearer ${PACK_API_TOKEN}" -d '{
     "name": "aws_creds",
     "type": "aws",
     "access_key": "${AWS_ACCESS_KEY_ID}",
     "secret_key": "${AWS_SECRET_ACCESS_KEY}"
   }'
   ```

5. **Update Jenkinsfile**:
   ```groovy
   stage('Terraform Plan') {
     agent { docker { image 'hashicorp/terraform:1.7.0' } }
     steps {
       dir('infra') {
         sh 'terraform init'
         sh 'terraform plan -var-file="terraform.tfvars"'
       }
     }
   }
   stage('Terraform Apply') {
     when { branch 'main' }
     agent { docker { image 'hashicorp/terraform:1.7.0' } }
     steps {
       dir('infra') {
         sh 'terraform apply -var-file="terraform.tfvars" -auto-approve'
       }
     }
   }
   ```

6. **Update Makefile**:
   ```makefile
   # SPDX-License-Identifier: Apache-2.0
   terraform-init: ## Initialize Terraform
	terraform -chdir=infra init

   terraform-plan: ## Plan Terraform changes
	terraform -chdir=infra plan -var-file="terraform.tfvars"

   terraform-apply: ## Apply Terraform changes
	terraform -chdir=infra apply -var-file="terraform.tfvars" -auto-approve
   ```

## Testing

### Unit Tests
```bash
terraform validate -chdir=infra
```

### Integration Tests
```bash
make terraform-plan
```

### End-to-End Tests
```bash
terraform apply -var-file="terraform.tfvars" -auto-approve
kubectl get pods -n astradesk-prod
istioctl analyze -n astradesk-prod
```

### Database Tests
- Postgres:
  ```bash
  psql -h $(terraform output -raw rds_postgres_endpoint) -U astradesk -d astradesk
  ```
- MySQL:
  ```bash
  mysql -h $(terraform output -raw rds_mysql_endpoint) -u tickets -p tickets
  ```

## Integration

- **Admin API**: AWS credentials stored in `/secrets` (e.g., `domain-support/tools/asana_adapter.py` for S3 uploads).
- **Istio**: EKS integrates with `deploy/istio/` (mTLS, Gateway).
- **cert-manager**: RDS/S3 use security groups for mTLS (`deploy/istio/certs/`).
- **Polyglot**:
  - RDS Postgres: Python core (`src/gateway/main.py`).
  - RDS MySQL: Java ticket-adapter (`services/ticket-adapter-java`).
  - S3: Artifacts for domain packs (`packages/domain-support`).

## Observability

- **Metrics**: EKS with Prometheus node exporter (`grafana/dashboard-astradesk.json`).
- **Dashboards**: Grafana for EKS, RDS, S3 metrics.
- **Logs**: AWS CloudWatch for EKS/RDS, stored in Postgres (`services/auditor`).

## Security

- **mTLS**: Enforced by `deploy/istio/10-peer-authentication.yaml`.
- **TLS**: RDS/S3 with security groups from VPC module.
- **Secrets**: AWS credentials in `/secrets` via Admin API.
- **RBAC**: EKS IAM roles for pods.

## Troubleshooting

- **Terraform Errors**:
  - Check logs: `terraform plan -debug`.
  - Verify AWS credentials: `aws sts get-caller-identity`.
- **Module Issues**:
  - Validate: `terraform validate -chdir=infra/modules/vpc`.
  - Fix: Update module versions (e.g., `version = "~> 5.0"` for vpc).

## Contributing

- Fork and create a branch (`git checkout -b infra-update`).
- Add features/tests, submit PR with >90% coverage.
- Ensure `make terraform-plan` passes.

## License

Apache-2.0 (see SPDX in files).
