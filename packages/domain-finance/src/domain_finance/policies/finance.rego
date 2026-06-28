# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: packages/domain-finance/src/domain_finance/policies/finance.rego
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for packages/domain-finance/src/domain_finance/policies/finance.rego.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

package astradesk.finance

violation[msg] {
  input.event.type == "tool.erp.oracle.fetch_sales"
  not contains(input.data.query, "CURRENT_MONTH")
  msg := "Invalid query: must be current month for compliance"
}

violation[msg] {
  input.event.cost_per_query > 0.01
  msg := "Cost exceeded threshold"
}

default allow = true
allow if { not violation[_] }
