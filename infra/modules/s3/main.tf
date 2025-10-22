# SPDX-License-Identifier: Apache-2.0
# File: modules/s3/main.tf
# Description:
#     Terraform module for creating an AWS S3 bucket for AstraDesk artifacts.
#     Enables versioning and object lock.
# Author: Siergej Sobolewski
# Since: 2025-10-22

module "s3_bucket" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "~> 3.0"

  bucket = var.name
  acl    = "private"

  versioning = {
    enabled = var.versioning
  }

  object_lock_enabled = var.object_lock

  tags = {
    Name    = "${var.name}-artifacts"
    Project = var.name
  }
}
