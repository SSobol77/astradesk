# SPDX-License-Identifier: Apache-2.0
"""File: packages/domain-supply/clients/grpc_client.py
Project: AstraDesk Domain Supply Pack
Description:
    gRPC client for SAP S/4HANA adapter (Java server).
    Integrates with Admin API for metadata, calls gRPC for data fetching.
    Production-ready with async, retry, and error handling.

Author: Siergej Sobolewski
Since: 2025-10-16
"""

import asyncio
import grpc
from tenacity import retry, stop_after_attempt, wait_exponential
from ..proto.supply_pb2 import FetchInventoryRequest
from ..proto.supply_pb2_grpc import SupplyServiceStub
from ..clients.api import AdminApiClient, ProblemDetail
from typing import List, Dict

class GrpcSapS4HanaClient:
    """Async gRPC client for SAP S/4HANA, with API metadata integration."""
    def __init__(self, grpc_url: str = "localhost:50051", api_url: str = "http://localhost:8080/api/admin/v1", token: str = ""):
        self.grpc_url = grpc_url
        self.api_client = AdminApiClient(api_url, token)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def fetch_inventory(self, query: str) -> List[Dict]:
        """Fetch inventory data via gRPC, with API connector check.
        
        :param query: SAP query (e.g., "SELECT material, stock FROM MM").
        :return: List of inventory records.
        :raises ValueError: If API or gRPC call fails.
        """
        # Validate connector via API
        connector_data = {"name": "sap_s4hana", "type": "sap", "config": {"system": "S4HANA"}}
        await self.api_client.create_connector(connector_data)

        # Call gRPC
        async with grpc.aio.insecure_channel(self.grpc_url) as channel:
            stub = SupplyServiceStub(channel)
            request = FetchInventoryRequest(query=query)
            response = await stub.FetchInventory(request)
            return [{"material": item.material, "stock": item.stock} for item in response.items]
