<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: deploy/infra/modules/eks/infra_modules_eks_README.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# EKS Module for AstraDesk

## Overview

This module provisions an AWS EKS cluster with managed node groups for AstraDesk. It uses `terraform-aws-modules/eks/aws` for best practices.

## Inputs

- `cluster_name`: Name of the EKS cluster (e.g., `astradesk-eks`).
- `cluster_version`: Kubernetes version (e.g., `1.28`).
- `vpc_id`: VPC ID.
- `subnets`: Subnet IDs.

## Outputs

- `cluster_endpoint`: EKS cluster endpoint.
- `cluster_name`: EKS cluster name.

## Usage

```hcl
module "eks" {
  source        = "./modules/eks"
  cluster_name  = "astradesk-eks"
  cluster_version = "1.28"
  vpc_id        = "vpc-12345678"
  subnets       = ["subnet-123", "subnet-456"]
}
