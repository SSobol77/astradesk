# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: deploy/infra/modules/rds-mysql/variables.tf
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
