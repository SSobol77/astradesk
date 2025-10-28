"""
Tiny stub replicating just enough of the `respx` API for the tests.
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


_active_router: contextvars.ContextVar["MockRouter | None"] = contextvars.ContextVar(
    "respx_active_router", default=None
)


@dataclass
class _MockResponse:
    status_code: int
    json_payload: Any

    def json(self) -> Any:
        return self.json_payload


class _MockRoute:
    def __init__(self, router: "MockRouter", method: str, path: str):
        self.router = router
        self.method = method.upper()
        self.path = path
        self._response: Optional[_MockResponse] = None

    def respond(self, status_code: int, json: Any = None) -> "_MockRoute":
        self._response = _MockResponse(status_code=status_code, json_payload=json)
        self.router._routes[(self.method, self.path)] = self._response
        return self


class MockRouter:
    def __init__(self):
        self._routes: Dict[Tuple[str, str], _MockResponse] = {}
        self._token: Optional[contextvars.Token] = None

    def __enter__(self) -> "MockRouter":
        self._token = _active_router.set(self)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._token is not None:
            _active_router.reset(self._token)
            self._token = None

    def route(self, method: str, path: str) -> _MockRoute:
        return _MockRoute(self, method, path)

    def post(self, path: str) -> _MockRoute:
        return self.route("POST", path)

    def get(self, path: str) -> _MockRoute:
        return self.route("GET", path)

    def put(self, path: str) -> _MockRoute:
        return self.route("PUT", path)

    def delete(self, path: str) -> _MockRoute:
        return self.route("DELETE", path)


def dispatch(method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> _MockResponse:
    router = _active_router.get()
    if router is None:
        raise RuntimeError("No active respx MockRouter. Use the respx_mock fixture.")
    response = router._routes.get((method.upper(), path))
    if response is None:
        raise RuntimeError(f"No mocked response for {method} {path}")
    return response


__all__ = ["MockRouter", "dispatch"]
