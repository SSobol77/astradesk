"""
Minimal gRPC helpers for the supply service tests.
"""

from __future__ import annotations

import json
from typing import Any

import grpc

from domain_supply.proto.supply_pb2 import (
    FetchInventoryRequest,
    FetchInventoryResponse,
    InventoryItem,
)


def _serialize_fetch_inventory_request(request: FetchInventoryRequest) -> bytes:
    return json.dumps({'query': request.query}, separators=(',', ':')).encode('utf-8')


def _deserialize_fetch_inventory_request(payload: bytes) -> FetchInventoryRequest:
    return FetchInventoryRequest(**json.loads(payload.decode('utf-8')))


def _serialize_fetch_inventory_response(response: FetchInventoryResponse) -> bytes:
    return json.dumps(
        {'items': [{'material': item.material, 'stock': item.stock} for item in response.items]},
        separators=(',', ':'),
    ).encode('utf-8')


def _deserialize_fetch_inventory_response(payload: bytes) -> FetchInventoryResponse:
    data = json.loads(payload.decode('utf-8'))
    return FetchInventoryResponse(items=[InventoryItem(**item) for item in data['items']])


class SupplyServiceStub:
    SERVICE_NAME = 'SupplyService'

    def __init__(self, channel: grpc.aio.Channel | None = None):
        self._channel = channel

    async def FetchInventory(self, request, context=None):
        if self._channel is None:
            raise NotImplementedError('Stub without channel is for server subclassing.')
        fetch_inventory = self._channel.unary_unary(
            f'/{self.SERVICE_NAME}/FetchInventory',
            request_serializer=_serialize_fetch_inventory_request,
            response_deserializer=_deserialize_fetch_inventory_response,
        )
        return await fetch_inventory(request)


def add_SupplyServiceServicer_to_server(servicer: Any, server: grpc.aio.Server) -> None:
    """Register an async supply servicer using the public gRPC server API."""
    rpc_method_handlers = {
        'FetchInventory': grpc.unary_unary_rpc_method_handler(
            servicer.FetchInventory,
            request_deserializer=_deserialize_fetch_inventory_request,
            response_serializer=_serialize_fetch_inventory_response,
        )
    }
    generic_handler = grpc.method_handlers_generic_handler(
        SupplyServiceStub.SERVICE_NAME,
        rpc_method_handlers,
    )
    server.add_generic_rpc_handlers((generic_handler,))


__all__ = ['SupplyServiceStub', 'add_SupplyServiceServicer_to_server']
