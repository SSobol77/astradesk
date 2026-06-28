# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: deploy/infra/variables.tf
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
