# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: deploy/infra/outputs.tf
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

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.id
}

output "eks_cluster_endpoint" {
  description = "Endpoint of the EKS cluster"
  value       = module.eks.cluster_endpoint
}

output "rds_postgres_endpoint" {
  description = "Endpoint of the RDS Postgres instance"
  value       = module.rds_postgres.endpoint
}

output "rds_mysql_endpoint" {
  description = "Endpoint of the RDS MySQL instance"
  value       = module.rds_mysql.endpoint
}

output "s3_bucket_name" {
  description = "Name of the S3 artifacts bucket"
  value       = module.s3_artifacts.bucket_name
}
