"""
Simple synchronous test client for the FastAPI stub.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from . import FastAPI, HTTPException, Request


@dataclass
class Response:
    status_code: int
    _json: Any

    def json(self) -> Any:
        return self._json


class TestClient:
    def __init__(self, app: FastAPI):
        self.app = app

    def __enter__(self) -> "TestClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - nothing to clean up
        return None

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Response:
        params = params or {}
        try:
            status, payload = self.app._call_handler("GET", path, request=Request(path=path), **params)
        except HTTPException as exc:
            return Response(status_code=exc.status_code, _json={"detail": exc.detail})
        return Response(status_code=status, _json=payload)

    def post(self, path: str, json: Optional[Dict[str, Any]] = None) -> Response:
        json = json or {}
        try:
            status, payload = self.app._call_handler("POST", path, request=Request(path=path), body=json)
        except HTTPException as exc:
            return Response(status_code=exc.status_code, _json={"detail": exc.detail})
        return Response(status_code=status, _json=payload)


__all__ = ["TestClient", "Response"]
