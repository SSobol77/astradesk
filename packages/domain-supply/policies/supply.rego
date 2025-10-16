# SPDX-License-Identifier: Apache-2.0
# File: packages/domain-supply/policies/supply.rego
# Description: OPA Rego policies for supply chain domain.
# Upload via API POST /policies, simulate with /policies/{id}:simulate.

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
