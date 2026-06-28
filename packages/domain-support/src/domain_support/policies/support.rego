# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: packages/domain-support/src/domain_support/policies/support.rego
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for packages/domain-support/src/domain_support/policies/support.rego.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

package astradesk.support

violation[msg] {
  input.event.type == "tool.jira.list"
  not startswith(input.data.jql, "project=OPS")
  msg := "Invalid JQL: restricted to OPS project"
}

violation[msg] {
  input.event.type == "tool.asana.create_task"
  not input.data.project_gid in ["allowed_gid1", "allowed_gid2"]
  msg := "Unauthorized Asana project"
}

violation[msg] {
  input.event.type == "tool.slack.post"
  not input.data.channel in ["#support-oncall", "#escalations"]
  msg := "Unauthorized Slack channel"
}

default allow = true
allow if { not violation[_] }
