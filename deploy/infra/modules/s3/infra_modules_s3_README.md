<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: deploy/infra/modules/s3/infra_modules_s3_README.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# S3 Module for AstraDesk

## Overview

This module provisions an AWS S3 bucket for AstraDesk artifacts (e.g., domain-support uploads). It uses `terraform-aws-modules/s3-bucket/aws` with versioning and object lock.

## Inputs

- `name`: Bucket name (e.g., `astradesk-artifacts`).
- `versioning`: Enable versioning (true/false).
- `object_lock`: Enable object lock (true/false).

## Outputs

- `bucket_name`: S3 bucket name.

## Usage

```hcl
module "s3_artifacts" {
  source      = "./modules/s3"
  name        = "astradesk-artifacts"
  versioning  = true
  object_lock = true
}
