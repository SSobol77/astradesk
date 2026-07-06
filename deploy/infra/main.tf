# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: deploy/infra/main.tf
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

terraform {
  required_version = ">= 1.7.0"

  # Issue #43: terraform-aws-modules/eks/aws ~> 19.0 (pinned in
  # modules/eks/main.tf) only declares aws >= 4.57 with no upper bound, so an
  # unconstrained root resolves the newest aws provider (6.x), which dropped
  # aws_eks_addon.resolve_conflicts and the aws_launch_template
  # elastic_gpu_specifications/elastic_inference_accelerator blocks that
  # module version 19.x still emits — breaking `terraform validate`. Capping
  # below 6.0 here keeps every module's own floor intact (vpc's >= 5.79 is
  # the highest) and resolves to the newest compatible 5.x release instead
  # of bumping the EKS module's major line. See
  # audit/evidence/43_deployability_verification.md.
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.57, < 6.0"
    }
  }

  backend "s3" {
    bucket         = "astradesk-tfstate"
    key            = "prod/terraform.tfstate"
    region         = "eu-central-1"
    dynamodb_table = "astradesk-tfstate-lock"
  }
}

provider "aws" {
  region = var.region
}

module "vpc" {
  source             = "./modules/vpc"
  name               = var.project
  cidr               = "10.0.0.0/16"
  azs                = ["${var.region}a", "${var.region}b"]
  private_subnets    = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets     = ["10.0.101.0/24", "10.0.102.0/24"]
  enable_nat_gateway = true
}

module "eks" {
  source          = "./modules/eks"
  cluster_name    = "${var.project}-eks"
  vpc_id          = module.vpc.id
  subnets         = module.vpc.private_subnets
  cluster_version = "1.28"
}

module "rds_postgres" {
  source         = "./modules/rds-postgres"
  db_name        = var.db_name_postgres
  engine_version = "18"
  instance_class = "db.t3.micro"
  vpc_id         = module.vpc.id
  subnets        = module.vpc.private_subnets
  db_username    = var.db_username_postgres
  db_password    = var.db_password_postgres
}

module "rds_mysql" {
  source         = "./modules/rds-mysql"
  db_name        = var.db_name_mysql
  engine_version = "8.0"
  instance_class = "db.t3.micro"
  vpc_id         = module.vpc.id
  subnets        = module.vpc.private_subnets
  db_username    = var.db_username_mysql
  db_password    = var.db_password_mysql
}

module "s3_artifacts" {
  source      = "./modules/s3"
  name        = "${var.project}-artifacts"
  versioning  = true
  object_lock = true
}
