# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: deploy/infra/modules/rds-postgres/main.tf
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

module "rds_postgres" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 5.0"

  identifier             = "${var.db_name}-postgres"
  engine                 = "postgres"
  engine_version         = var.engine_version
  instance_class         = var.instance_class
  allocated_storage      = 20
  db_name                = var.db_name
  username               = var.db_username
  password               = var.db_password
  multi_az               = true
  vpc_security_group_ids = [aws_security_group.rds.id]
  subnet_ids             = var.subnets

  tags = {
    Name    = "${var.db_name}-postgres"
    Project = var.db_name
  }
}

resource "aws_security_group" "rds" {
  name   = "${var.db_name}-rds-sg"
  vpc_id = var.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
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
