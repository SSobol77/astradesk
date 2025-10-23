# SPDX-License-Identifier: Apache-2.0
# File: outputs.tf
# Description:
#     Output values for AstraDesk AWS infrastructure.
#     Exports VPC ID, EKS cluster endpoint, RDS endpoints, and S3 bucket name.
#     Used by Jenkinsfile and Makefile for CI/CD integration.
# Author: Siergej Sobolewski
# Since: 2025-10-22

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
