###### SPDX-License-Identifier: Apache-2.0

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
