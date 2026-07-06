# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: deploy/infra/terraform.tfvars
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

region               = "eu-central-1"
project              = "astradesk"
db_name_postgres     = "astradesk"
db_username_postgres = "astradesk"
db_password_postgres = "astrapass"
db_name_mysql        = "tickets"
db_username_mysql    = "tickets"
db_password_mysql    = "tickets"
