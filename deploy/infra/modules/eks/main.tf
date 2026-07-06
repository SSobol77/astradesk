# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: deploy/infra/modules/eks/main.tf
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Configures the associated AstraDesk component or deployment.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

# Issue #43: this module's own aws provider floor (>= 4.57, no upper bound)
# lets a standalone `terraform validate` of this directory resolve aws 6.x,
# which dropped attributes/blocks that terraform-aws-modules/eks/aws ~> 19.0
# still emits. The root `deploy/infra/main.tf` also caps this, but a module
# validated on its own (as its own root) does not inherit the caller's
# constraint, so it is repeated here. See
# audit/evidence/43_deployability_verification.md.
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.57, < 6.0"
    }
  }
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version
  vpc_id          = var.vpc_id
  subnet_ids      = var.subnets

  eks_managed_node_groups = {
    default = {
      min_size       = 2
      max_size       = 4
      desired_size   = 2
      instance_types = ["t3.medium"]
    }
  }

  tags = {
    Name    = "${var.cluster_name}-eks"
    Project = var.cluster_name
  }
}
