<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: deploy/infra/modules/vpc/infra_modules_vpc_README.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# VPC Module for AstraDesk

## Overview

This module provisions an AWS VPC with private and public subnets, NAT Gateway, and security groups for AstraDesk. It uses `terraform-aws-modules/vpc/aws` for best practices.

## Inputs

- `name`: Name of the VPC (e.g., `astradesk`).
- `cidr`: CIDR block (e.g., `10.0.0.0/16`).
- `azs`: List of Availability Zones.
- `private_subnets`: CIDR blocks for private subnets.
- `public_subnets`: CIDR blocks for public subnets.
- `enable_nat_gateway`: Enable NAT Gateway (default: false).

## Outputs

- `id`: VPC ID.
- `private_subnets`: Private subnet IDs.
- `public_subnets`: Public subnet IDs.

## Usage

```hcl
module "vpc" {
  source  = "./modules/vpc"
  name    = "astradesk"
  cidr    = "10.0.0.0/16"
  azs     = ["eu-central-1a", "eu-central-1b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]
  enable_nat_gateway = true
}
