# SPDX-License-Identifier: Apache-2.0
# File: modules/s3/outputs.tf
# Description:
#     Output values for the S3 module.
# Author: Siergej Sobolewski
# Since: 2025-10-22

output "bucket_name" {
  description = "Name of the S3 bucket"
  value       = module.s3_bucket.s3_bucket_id
}
