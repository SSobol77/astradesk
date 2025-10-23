###### SPDX-License-Identifier: Apache-2.0

# RDS Postgres Module for AstraDesk

## Overview

This module provisions an AWS RDS Postgres instance for AstraDesk (used by Python core). It uses `terraform-aws-modules/rds/aws` with multi-AZ and VPC security.

## Inputs

- `db_name`: Database name (e.g., `astradesk`).
- `engine_version`: Postgres version (e.g., `18`).
- `instance_class`: RDS instance class (e.g., `db.t3.micro`).
- `vpc_id`: VPC ID.
- `subnets`: Subnet IDs.
- `db_username`: Database username.
- `db_password`: Database password (sensitive).

## Outputs

- `endpoint`: RDS Postgres endpoint.

## Usage

```hcl
module "rds_postgres" {
  source           = "./modules/rds-postgres"
  db_name          = "astradesk"
  engine_version   = "18"
  instance_class   = "db.t3.micro"
  vpc_id           = "vpc-12345678"
  subnets          = ["subnet-123", "subnet-456"]
  db_username      = "astradesk"
  db_password      = "astrapass"
}
