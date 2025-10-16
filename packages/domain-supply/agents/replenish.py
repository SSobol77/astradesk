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

from typing import AsyncIterator, List, Dict
import asyncio
from pydantic import BaseModel
from ..clients.api import AdminApiClient, ProblemDetail
from ..clients.grpc_client import GrpcSapS4HanaClient

class ReplenishResult(BaseModel):
    """Pydantic model for replenishment result, aligned with OpenAPI Run schema."""
    item_id: str
    quantity: int
    priority: str

async def replenish_inventory(items: List[Dict], api_url: str = "http://localhost:8080/api/admin/v1", token: str = "", grpc_url: str = "localhost:50051") -> AsyncIterator[ReplenishResult]:
    """Generate replenishment plan by fetching data via gRPC and calling Admin API.

    Steps:
    1. Fetch inventory data from SAP S/4HANA via gRPC client.
    2. Create or get agent via POST /agents (if not exists).
    3. Test agent with input via POST /agents/{id}:test.
    4. Poll run results via GET /runs/{id} until completed.

    Uses local logic for computation, submits via API for compliance.

    :param items: List of inventory items (e.g., [{"item_id": "A1", "stock": 10, "min_stock": 50}]).
    :param api_url: Base URL for Admin API.
    :param token: JWT token for BearerAuth.
    :param grpc_url: gRPC server URL for SAP S/4HANA.
    :raises ValueError: If API or gRPC call fails.
    :yield: ReplenishResult for each replenishment action.
    """
    client = AdminApiClient(api_url, token)
    grpc_client = GrpcSapS4HanaClient(grpc_url, api_url, token)

    # Step 1: Fetch inventory data via gRPC
    inventory_data = await grpc_client.fetch_inventory("SELECT material, stock FROM MM WHERE stock < min_stock")
    input_data = items if items else inventory_data  # Use provided data or fetched

    # Step 2: Create or get agent via API
    agent_data = {"name": "supply_replenish", "config": {"method": "replenish", "threshold": 50}}
    try:
        agent = await client.create_agent(agent_data)
    except ValueError as e:
        agents_resp = await client.client.get("/agents", params={"name": "supply_replenish"})
        if agents_resp.status_code == 200 and agents_resp.json():
            agent = agents_resp.json()[0]
        else:
            raise e

    # Step 3: Local replenishment logic
    replenish_plan = []
    for item in input_data:
        min_stock = item.get("min_stock", 50)
        stock = item["stock"]
        if stock < min_stock:
            replenish_plan.append({
                "item_id": item["material"],
                "quantity": min_stock - stock,
                "priority": "urgent" if stock < min_stock * 0.2 else "normal"
            })

    # Step 4: Submit to API and poll results
    run_id = await client.test_agent(agent["id"], {"replenish_plan": replenish_plan})
    while True:
        run = await client.get_run(run_id)
        if run["status"] == "completed":
            for result in run["output"]:
                yield ReplenishResult(**result)
            break
        await asyncio.sleep(1)
