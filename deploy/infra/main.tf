# SPDX-License-Identifier: Apache-2.0
# File: main.tf
# Description:
#     Main Terraform configuration for AstraDesk infrastructure on AWS.
#     Defines backend (S3) and modules for VPC, EKS, RDS (Postgres/MySQL), and S3.
#     Integrates with deploy/istio/, /secrets (Admin API), and polyglot stack (Python 3.14+, Java 25+).
# Author: Siergej Sobolewski
# Since: 2025-10-22

terraform {
  required_version = ">= 1.7.0"

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
  source  = "./modules/vpc"
  name    = var.project
  cidr    = "10.0.0.0/16"
  azs     = ["${var.region}a", "${var.region}b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]
  enable_nat_gateway = true
}

module "eks" {
  source        = "./modules/eks"
  cluster_name  = "${var.project}-eks"
  vpc_id        = module.vpc.id
  subnets       = module.vpc.private_subnets
  cluster_version = "1.28"
}

module "rds_postgres" {
  source           = "./modules/rds-postgres"
  db_name          = var.db_name_postgres
  engine_version   = "18"
  instance_class   = "db.t3.micro"
  vpc_id           = module.vpc.id
  subnets          = module.vpc.private_subnets
  db_username      = var.db_username_postgres
  db_password      = var.db_password_postgres
}

module "rds_mysql" {
  source           = "./modules/rds-mysql"
  db_name          = var.db_name_mysql
  engine_version   = "8.0"
  instance_class   = "db.t3.micro"
  vpc_id           = module.vpc.id
  subnets          = module.vpc.private_subnets
  db_username      = var.db_username_mysql
  db_password      = var.db_password_mysql
}

module "s3_artifacts" {
  source      = "./modules/s3"
  name        = "${var.project}-artifacts"
  versioning  = true
  object_lock = true
}
