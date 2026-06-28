# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: deploy/infra/modules/s3/main.tf
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
