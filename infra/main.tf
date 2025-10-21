terraform { required_version = ">= 1.7.0" }
provider "aws" { region = var.region }

module "vpc" { source = "./modules/vpc" name = var.project }
module "eks" {
  source       = "./modules/eks"
  cluster_name = "${var.project}-eks"
  vpc_id       = module.vpc.id
  subnets      = module.vpc.private_subnets
}
module "rds_postgres" {
  source     = "./modules/rds-postgres"
  db_name    = "astradesk"
  engine_ver = "17"
}
module "rds_mysql" {
  source     = "./modules/rds-mysql"
  db_name    = "tickets"
  engine_ver = "8.0"
}
module "s3_artifacts" {
  source      = "./modules/s3"
  name        = "${var.project}-artifacts"
  versioning  = true
  object_lock = true
}
