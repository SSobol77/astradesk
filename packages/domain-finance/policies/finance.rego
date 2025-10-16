# SPDX-License-Identifier: Apache-2.0
# File: packages/domain-finance/policies/finance.rego
# Description: OPA Rego policies for finance domain.
# Upload via API POST /policies, simulate with /policies/{id}:simulate.

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