# SPDX-License-Identifier: Apache-2.0
"""File: packages/domain-supply/tests/test_replenish.py
Project: AstraDesk Domain Supply Pack
Description:
    Production-level tests for replenishment agent with gRPC integration.
    Uses respx for API mocking and grpc.aio.testing for gRPC.

Author: Siergej Sobolewski
Since: 2025-10-16
"""

import pytest
import httpx
from respx import MockRouter
from ..agents.replenish import replenish_inventory
from ..clients.grpc_client import GrpcSapS4HanaClient
from ..clients.api import ProblemDetail
from ..proto.supply_pb2 import FetchInventoryResponse, InventoryItem
from ..proto.supply_pb2_grpc import SupplyServiceStub

@pytest.mark.asyncio
async def test_replenish_success(respx_mock: MockRouter):
    """Test successful replenishment with mocked API and gRPC."""
    respx_mock.post("/agents").respond(201, json={"id": "sup1"})
    respx_mock.post("/agents/sup1:test").respond(200, json={"run_id": "run_sup1"})
    respx_mock.get("/runs/run_sup1").respond(200, json={"status": "completed", "output": [{"item_id": "A1", "quantity": 40, "priority": "urgent"}]})

    results = [res async for res in replenish_inventory([{"item_id": "A1", "stock": 10, "min_stock": 50}], api_url="http://mock", token="fake")]
    assert len(results) == 1
    assert results[0].quantity == 40
    assert results[0].priority == "urgent"

@pytest.mark.asyncio
async def test_replenish_grpc_integration():
    """Test gRPC client with mocked server."""
    from grpc.aio import server as aio_server
    from ..proto.supply_pb2_grpc import add_SupplyServiceServicer_to_server

    class MockSupplyService(SupplyServiceStub):
        async def FetchInventory(self, request, context):
            return FetchInventoryResponse(items=[InventoryItem(material="M1", stock=100)])

    server = aio_server()
    add_SupplyServiceServicer_to_server(MockSupplyService(), server)
    server.add_insecure_port('[::]:50051')
    await server.start()

    client = GrpcSapS4HanaClient("localhost:50051", "http://mock", "fake")
    inventory = await client.fetch_inventory("SELECT material, stock FROM MM")
    assert len(inventory) == 1
    assert inventory[0]["material"] == "M1"
    assert inventory[0]["stock"] == 100

    await server.stop(None)
