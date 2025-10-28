"""
Lightweight FastAPI stub providing just enough surface for the tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: Any = None):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class FastAPI:
    def __init__(self, title: str = "", version: str = "0"):
        self.title = title
        self.version = version
        self._routes: Dict[Tuple[str, str], Callable[..., Any]] = {}

    def _register(self, method: str, path: str, handler: Callable[..., Any]) -> Callable[..., Any]:
        self._routes[(method.upper(), path)] = handler
        return handler

    def get(self, path: str, **_: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return self._register("GET", path, func)

        return decorator

    def post(self, path: str, **_: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return self._register("POST", path, func)

        return decorator

    def route(self, method: str, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return self._register(method, path, func)

        return decorator

    def _call_handler(self, method: str, path: str, **kwargs: Any) -> Tuple[int, Any]:
        handler = self._routes.get((method.upper(), path))
        if handler is None:
            raise HTTPException(status_code=404, detail="Not Found")
        result = handler(**kwargs)
        if isinstance(result, tuple) and len(result) == 2:
            body, status = result
            return status, body
        return 200, result


@dataclass
class Request:
    """Placeholder request object used by handlers that expect it."""

    path: str


def Depends(func: Callable[..., Any]) -> Callable[..., Any]:  # pragma: no cover - simple passthrough
    return func


def Header(*_: Any, **__: Any) -> Any:  # pragma: no cover
    return None


__all__ = ["FastAPI", "HTTPException", "Depends", "Header", "Request"]
