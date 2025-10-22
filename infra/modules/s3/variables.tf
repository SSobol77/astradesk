# SPDX-License-Identifier: Apache-2.0
# File: modules/s3/variables.tf
# Description:
#     Input variables for the S3 module.
# Author: Siergej Sobolewski
# Since: 2025-10-22

variable "name" {
  description = "Name of the S3 bucket"
  type        = string
}

variable "versioning" {
  description = "Enable versioning for the S3 bucket"
  type        = bool
}

variable "object_lock" {
  description = "Enable object lock for the S3 bucket"
  type        = bool
}
