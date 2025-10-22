# SPDX-License-Identifier: Apache-2.0
# File: variables.tf
# Description:
#     Input variables for AstraDesk AWS infrastructure.
#     Defines region, project name, and DB credentials for RDS (Postgres/MySQL).
#     Compatible with .env.example (DATABASE_URL, MYSQL_URL_R2DBC).
# Author: Siergej Sobolewski
# Since: 2025-10-22

variable "region" {
  description = "AWS region for deployment"
  type        = string
  default     = "eu-central-1"
}

variable "project" {
  description = "Project name for resource tagging"
  type        = string
  default     = "astradesk"
}

variable "db_name_postgres" {
  description = "Database name for RDS Postgres"
  type        = string
  default     = "astradesk"
}

variable "db_username_postgres" {
  description = "Username for RDS Postgres"
  type        = string
  default     = "astradesk"
}

variable "db_password_postgres" {
  description = "Password for RDS Postgres (store in /secrets for production)"
  type        = string
  sensitive   = true
  default     = "astrapass"
}

variable "db_name_mysql" {
  description = "Database name for RDS MySQL"
  type        = string
  default     = "tickets"
}

variable "db_username_mysql" {
  description = "Username for RDS MySQL"
  type        = string
  default     = "tickets"
}

variable "db_password_mysql" {
  description = "Password for RDS MySQL (store in /secrets for production)"
  type        = string
  sensitive   = true
  default     = "tickets"
}