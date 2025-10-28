"""
Minimal tool registry with async execution support.
"""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Set


class ToolRegistryError(Exception):
    """Base error for registry issues."""


class ToolNotFoundError(ToolRegistryError):
    pass


class ToolRegistrationError(ToolRegistryError):
    pass


class AuthorizationError(ToolRegistryError):
    pass


ToolCallable = Callable[..., Any]


@dataclass(frozen=True)
class ToolInfo:
    name: str
    callable: ToolCallable
    description: str = ""
    version: str = "1.0.0"
    schema: Optional[Dict[str, Any]] = None
    allowed_roles: Set[str] = field(default_factory=set)
    is_coroutine: bool = False


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolInfo] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _validate_name(name: str) -> None:
        if not name or any(c.isspace() for c in name) or name.strip() != name:
            raise ToolRegistrationError("Tool name must be non-empty and without whitespace.")

    async def register(
        self,
        name: str,
        func: ToolCallable,
        *,
        description: str = "",
        version: str = "1.0.0",
        schema: Optional[Dict[str, Any]] = None,
        allowed_roles: Optional[Iterable[str]] = None,
    ) -> None:
        if not callable(func):
            raise ToolRegistrationError("Provided object is not callable.")

        self._validate_name(name)
        roles = set(allowed_roles or [])
        is_coro = inspect.iscoroutinefunction(func)

        info = ToolInfo(
            name=name,
            callable=func,
            description=description,
            version=version,
            schema=schema,
            allowed_roles=roles,
            is_coroutine=is_coro,
        )

        async with self._lock:
            if name in self._tools:
                raise ToolRegistrationError(f"Tool '{name}' already registered.")
            self._tools[name] = info

    async def unregister(self, name: str) -> None:
        async with self._lock:
            if name not in self._tools:
                raise ToolNotFoundError(name)
            self._tools.pop(name)

    def get(self, name: str) -> ToolCallable:
        if name not in self._tools:
            raise ToolNotFoundError(name)
        return self._tools[name].callable

    def get_info(self, name: str) -> ToolInfo:
        if name not in self._tools:
            raise ToolNotFoundError(name)
        return self._tools[name]

    def names(self) -> List[str]:
        return sorted(self._tools.keys())

    def exists(self, name: str) -> bool:
        return name in self._tools

    async def execute(self, name: str, **kwargs: Any) -> Any:
        if name not in self._tools:
            raise ToolNotFoundError(name)
        info = self._tools[name]

        claims = kwargs.pop("claims", None)
        if info.allowed_roles:
            roles = []
            if isinstance(claims, dict):
                value = claims.get("roles")
                if isinstance(value, list):
                    roles = [str(r).lower() for r in value]
                elif isinstance(value, str):
                    roles = [value.lower()]
            if not any(role in roles for role in (r.lower() for r in info.allowed_roles)):
                raise AuthorizationError("Caller lacks required roles.")

        func = info.callable
        signature = inspect.signature(func)
        if "claims" in signature.parameters:
            kwargs["claims"] = claims

        if info.is_coroutine:
            return await func(**kwargs)
        return await asyncio.to_thread(func, **kwargs)


__all__ = [
    "AuthorizationError",
    "ToolRegistry",
    "ToolRegistrationError",
    "ToolNotFoundError",
    "ToolInfo",
]
