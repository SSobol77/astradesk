# SPDX-License-Identifier: Apache-2.0
# File: modules/eks/main.tf
# Description:
#     Terraform module for creating an AWS EKS cluster for AstraDesk.
#     Provisions a managed node group and IAM roles.
# Author: Siergej Sobolewski
# Since: 2025-10-22

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version
  vpc_id          = var.vpc_id
  subnet_ids      = var.subnets

  eks_managed_node_groups = {
    default = {
      min_size     = 2
      max_size     = 4
      desired_size = 2
      instance_types = ["t3.medium"]
    }
  }

  tags = {
    Name    = "${var.cluster_name}-eks"
    Project = var.cluster_name
  }
}
