# SPDX-License-Identifier: Apache-2.0
# File: modules/rds-mysql/variables.tf
# Description:
#     Input variables for the RDS MySQL module.
# Author: Siergej Sobolewski
# Since: 2025-10-22

variable "db_name" {
  description = "Database name for RDS MySQL"
  type        = string
}

variable "engine_version" {
  description = "MySQL engine version"
  type        = string
}

variable "instance_class" {
  description = "RDS instance class"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for RDS"
  type        = string
}

variable "subnets" {
  description = "Subnet IDs for RDS"
  type        = list(string)
}

variable "db_username" {
  description = "Username for RDS MySQL"
  type        = string
}

variable "db_password" {
  description = "Password for RDS MySQL"
  type        = string
  sensitive   = true
}
