# SPDX-License-Identifier: Apache-2.0
# File: modules/rds-mysql/main.tf
# Description:
#     Terraform module for creating an AWS RDS MySQL instance for AstraDesk.
#     Provisions a multi-AZ instance with VPC security group.
# Author: Siergej Sobolewski
# Since: 2025-10-22

module "rds_mysql" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 5.0"

  identifier           = "${var.db_name}-mysql"
  engine               = "mysql"
  engine_version       = var.engine_version
  instance_class       = var.instance_class
  allocated_storage    = 20
  db_name              = var.db_name
  username             = var.db_username
  password             = var.db_password
  multi_az             = true
  vpc_security_group_ids = [aws_security_group.rds.id]
  subnet_ids           = var.subnets

  tags = {
    Name    = "${var.db_name}-mysql"
    Project = var.db_name
  }
}

resource "aws_security_group" "rds" {
  name        = "${var.db_name}-rds-sg"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
