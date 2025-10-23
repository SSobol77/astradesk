###### SPDX-License-Identifier: Apache-2.0

# RDS MySQL Module for AstraDesk

## Overview

This module provisions an AWS RDS MySQL instance for AstraDesk (used by Java ticket-adapter). It uses `terraform-aws-modules/rds/aws` with multi-AZ and VPC security.

## Inputs

- `db_name`: Database name (e.g., `tickets`).
- `engine_version`: MySQL version (e.g., `8.0`).
- `instance_class`: RDS instance class (e.g., `db.t3.micro`).
- `vpc_id`: VPC ID.
- `subnets`: Subnet IDs.
- `db_username`: Database username.
- `db_password`: Database password (sensitive).

## Outputs

- `endpoint`: RDS MySQL endpoint.

## Usage

```hcl
module "rds_mysql" {
  source           = "./modules/rds-mysql"
  db_name          = "tickets"
  engine_version   = "8.0"
  instance_class   = "db.t3.micro"
  vpc_id           = "vpc-12345678"
  subnets          = ["subnet-123", "subnet-456"]
  db_username      = "tickets"
  db_password      = "tickets"
}
