###### SPDX-License-Identifier: Apache-2.0

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
