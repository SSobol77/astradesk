# SPDX-License-Identifier: Apache-2.0
# File: modules/vpc/outputs.tf
# Description:
#     Output values for the VPC module.
# Author: Siergej Sobolewski
# Since: 2025-10-22

output "id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "private_subnets" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnets
}

output "public_subnets" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnets
}
