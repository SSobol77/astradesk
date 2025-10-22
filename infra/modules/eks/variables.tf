# SPDX-License-Identifier: Apache-2.0
# File: modules/eks/variables.tf
# Description:
#     Input variables for the EKS module.
# Author: Siergej Sobolewski
# Since: 2025-10-22

variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "cluster_version" {
  description = "Kubernetes version for EKS"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for the EKS cluster"
  type        = string
}

variable "subnets" {
  description = "Subnet IDs for the EKS cluster"
  type        = list(string)
}
