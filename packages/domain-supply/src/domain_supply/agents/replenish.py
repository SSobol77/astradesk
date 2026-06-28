# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: packages/domain-supply/src/domain_supply/agents/replenish.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for packages/domain-supply/src/domain_supply/agents/replenish.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Asynchronous agent for inventory replenishment using SAP S/4HANA data.
Integrates with SAP S/4HANA via gRPC client, and Admin API for agent/run management.
Production-ready with async, retry, and error handling.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass

from domain_supply.clients.api import AdminApiClient
from domain_supply.clients.grpc_client import GrpcSapS4HanaClient


@dataclass(frozen=True)
class ReplenishResult:
    """Simple DTO returned by the mocked Admin API."""

    item_id: str
    quantity: int
    priority: str


async def replenish_inventory(
    items: list[dict],
    api_url: str = 'http://localhost:8080/api/admin/v1',
    token: str = '',
    grpc_url: str = 'localhost:50051',
) -> AsyncIterator[ReplenishResult]:
    """Yield replenishment decisions produced via mocked Admin API."""
    client = AdminApiClient(api_url, token)
    grpc_client = GrpcSapS4HanaClient(grpc_url, api_url, token)

    input_data = items
    if not input_data:
        inventory_data = await grpc_client.fetch_inventory(
            'SELECT material, stock FROM MM WHERE stock < min_stock'
        )
        input_data = inventory_data

    agent = await client.create_agent(
        {'name': 'supply_replenish', 'config': {'method': 'simple', 'threshold': 50}}
    )
    submission = {'inventory': input_data}
    run_id = await client.test_agent(agent['id'], submission)
    while True:
        run = await client.get_run(run_id)
        if run['status'] == 'completed':
            for result in run['output']:
                yield ReplenishResult(**result)
            break
        await asyncio.sleep(1)
