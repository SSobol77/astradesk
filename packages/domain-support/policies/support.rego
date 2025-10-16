# SPDX-License-Identifier: Apache-2.0
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
