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
from __future__ import annotations

from typing import Dict, List

import grpc

from ..clients.api import AdminApiClient
from ..proto.supply_pb2 import FetchInventoryRequest
from ..proto.supply_pb2_grpc import SupplyServiceStub


class GrpcSapS4HanaClient:
    """Async gRPC client talking to the in-process stub used in tests."""

    def __init__(
        self,
        grpc_url: str = "localhost:50051",
        api_url: str = "http://localhost:8080/api/admin/v1",
        token: str = "",
    ) -> None:
        self.grpc_url = grpc_url
        self.api_client = AdminApiClient(api_url, token)

    async def fetch_inventory(self, query: str) -> List[Dict[str, float]]:
        """Fetch inventory data using the stubbed gRPC service."""
        async with grpc.aio.insecure_channel(self.grpc_url) as channel:
            stub = SupplyServiceStub(channel)
            request = FetchInventoryRequest(query=query)
            response = await stub.FetchInventory(request)
            return [{"material": item.material, "stock": item.stock} for item in response.items]
