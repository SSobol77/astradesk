# SPDX-License-Identifier: Apache-2.0
# File: modules/vpc/main.tf
# Description:
#     Terraform module for creating an AWS VPC for AstraDesk.
#     Provisions private/public subnets, NAT Gateway, and security groups.
# Author: Siergej Sobolewski
# Since: 2025-10-22

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = var.name
  cidr = var.cidr

  azs             = var.azs
  private_subnets = var.private_subnets
  public_subnets  = var.public_subnets

  enable_nat_gateway = var.enable_nat_gateway
  single_nat_gateway = true
  enable_vpn_gateway = false

  tags = {
    Name    = "${var.name}-vpc"
    Project = var.name
  }
}
