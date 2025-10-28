"""Minimal asyncio-friendly gRPC stub used for tests."""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any, Awaitable, Callable, Dict, Tuple

_SERVER_REGISTRY: Dict[str, "InProcessServer"] = {}


class InsecureChannel:
    def __init__(self, target: str):
        self._target = target

    async def __aenter__(self) -> "InsecureChannel":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def invoke(self, service: str, method: str, request: Any) -> Any:
        server = _SERVER_REGISTRY.get(self._target)
        if server is None and self._target.startswith("localhost:"):
            port = self._target.split(":", 1)[1]
            server = _SERVER_REGISTRY.get(f"[::]:{port}") or _SERVER_REGISTRY.get(f"0.0.0.0:{port}")
        if server is None or not server.started:
            raise RuntimeError(f"No gRPC server listening on {self._target!r}")
        return await server.invoke(service, method, request)


class InProcessServer:
    def __init__(self):
        self._handlers: Dict[Tuple[str, str], Callable[[Any, Any], Awaitable[Any]]] = {}
        self._target: str | None = None
        self.started = False

    def add_insecure_port(self, target: str) -> None:
        self._target = target

    def add_handler(self, service: str, method: str, handler: Callable[[Any, Any], Awaitable[Any]]) -> None:
        self._handlers[(service, method)] = handler

    async def start(self) -> None:
        if self._target is None:
            raise RuntimeError("No target configured via add_insecure_port.")
        _SERVER_REGISTRY[self._target] = self
        self.started = True

    async def stop(self, _grace: Any) -> None:
        if self._target and _SERVER_REGISTRY.get(self._target) is self:
            _SERVER_REGISTRY.pop(self._target)
        self.started = False

    async def invoke(self, service: str, method: str, request: Any) -> Any:
        handler = self._handlers.get((service, method))
        if handler is None:
            raise RuntimeError(f"Handler {service}/{method} not registered.")
        return await handler(request, None)


def insecure_channel(target: str) -> InsecureChannel:
    return InsecureChannel(target)


def server() -> InProcessServer:
    return InProcessServer()


_aio_module = ModuleType("grpc.aio")
_aio_module.InsecureChannel = InsecureChannel
_aio_module.insecure_channel = insecure_channel
_aio_module.InProcessServer = InProcessServer
_aio_module.server = server

sys.modules.setdefault("grpc.aio", _aio_module)

aio = _aio_module

__all__ = [
    "aio",
    "InsecureChannel",
    "InProcessServer",
    "insecure_channel",
    "server",
]
