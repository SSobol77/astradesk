# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: packages/domain-supply/src/domain_supply/policies/supply.rego
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for packages/domain-supply/src/domain_supply/policies/supply.rego.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

package astradesk.supply

violation[msg] {
  input.event.type == "tool.sap_mm.fetch_inventory"
  not contains(input.data.query, "plant='PL01'")
  msg := "Invalid query: restricted to PL01 plant"
}

violation[msg] {
  input.event.cost_per_query > 0.01
  msg := "Cost exceeded threshold"
}

default allow = true
allow if { not violation[_] }
