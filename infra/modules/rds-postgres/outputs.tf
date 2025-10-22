# SPDX-License-Identifier: Apache-2.0
# File: modules/rds-postgres/outputs.tf
# Description:
#     Output values for the RDS Postgres module.
# Author: Siergej Sobolewski
# Since: 2025-10-22

output "endpoint" {
  description = "RDS Postgres endpoint"
  value       = module.rds_postgres.db_instance_endpoint
}
