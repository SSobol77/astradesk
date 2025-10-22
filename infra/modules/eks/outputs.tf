# SPDX-License-Identifier: Apache-2.0
# File: modules/eks/outputs.tf
# Description:
#     Output values for the EKS module.
# Author: Siergej Sobolewski
# Since: 2025-10-22

output "cluster_endpoint" {
  description = "Endpoint of the EKS cluster"
  value       = module.eks.cluster_endpoint
}

output "cluster_name" {
  description = "Name of the EKS cluster"
  value       = module.eks.cluster_name
}
