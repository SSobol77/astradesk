"""
Minimal gRPC helpers for the supply service tests.
"""

from __future__ import annotations

from typing import Any

from grpc import aio


class SupplyServiceStub:
    SERVICE_NAME = "SupplyService"

    def __init__(self, channel: aio.InsecureChannel | None = None):
        self._channel = channel

    async def FetchInventory(self, request, context=None):
        if self._channel is None:
            raise NotImplementedError("Stub without channel is for server subclassing.")
        return await self._channel.invoke(self.SERVICE_NAME, "FetchInventory", request)


def add_SupplyServiceServicer_to_server(servicer: Any, server: aio.InProcessServer) -> None:
    async def handler(request, context):
        return await servicer.FetchInventory(request, context)

    server.add_handler(SupplyServiceStub.SERVICE_NAME, "FetchInventory", handler)


__all__ = ["SupplyServiceStub", "add_SupplyServiceServicer_to_server"]
