# SPDX-License-Identifier: Apache-2.0
# File: modules/rds-mysql/outputs.tf
# Description:
#     Output values for the RDS MySQL module.
# Author: Siergej Sobolewski
# Since: 2025-10-22

output "endpoint" {
  description = "RDS MySQL endpoint"
  value       = module.rds_mysql.db_instance_endpoint
}
