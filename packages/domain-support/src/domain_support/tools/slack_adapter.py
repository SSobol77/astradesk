# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: packages/domain-support/src/domain_support/tools/slack_adapter.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for packages/domain-support/src/domain_support/tools/slack_adapter.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Minimal Slack adapter stub used by tests."""

from __future__ import annotations


class SlackAdapter:
    async def post_message(self, message_data: dict) -> dict[str, str]:
        ticket = message_data.get('ticket_id', 'unknown')
        return {'message_id': f'slack-{ticket}'}
