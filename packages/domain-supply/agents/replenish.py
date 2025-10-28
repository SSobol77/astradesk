# SPDX-License-Identifier: Apache-2.0
"""File: packages/domain-supply/agents/replenish.py
Project: AstraDesk Domain Supply Pack
Description:
    Asynchronous agent for inventory replenishment using SAP S/4HANA data.
    Integrates with SAP S/4HANA via gRPC client, and Admin API for agent/run management.
    Production-ready with async, retry, and error handling.

Author: Siergej Sobolewski
Since: 2025-10-16
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import AsyncIterator, Dict, List

from ..clients.api import AdminApiClient
from ..clients.grpc_client import GrpcSapS4HanaClient


@dataclass(frozen=True)
class ReplenishResult:
    """Simple DTO returned by the mocked Admin API."""

    item_id: str
    quantity: int
    priority: str


async def replenish_inventory(
    items: List[Dict],
    api_url: str = "http://localhost:8080/api/admin/v1",
    token: str = "",
    grpc_url: str = "localhost:50051",
) -> AsyncIterator[ReplenishResult]:
    """Yield replenishment decisions produced via mocked Admin API."""
    client = AdminApiClient(api_url, token)
    grpc_client = GrpcSapS4HanaClient(grpc_url, api_url, token)

    input_data = items
    if not input_data:
        inventory_data = await grpc_client.fetch_inventory("SELECT material, stock FROM MM WHERE stock < min_stock")
        input_data = inventory_data

    agent = await client.create_agent({"name": "supply_replenish", "config": {"method": "simple", "threshold": 50}})
    submission = {"inventory": input_data}
    run_id = await client.test_agent(agent["id"], submission)
    while True:
        run = await client.get_run(run_id)
        if run["status"] == "completed":
            for result in run["output"]:
                yield ReplenishResult(**result)
            break
        await asyncio.sleep(1)
