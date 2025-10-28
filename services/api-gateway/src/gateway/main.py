# SPDX-License-Identifier: Apache-2.0
# services/api-gateway/src/gateway/main.py
"""Minimal FastAPI application exposing a health endpoint for tests."""

from __future__ import annotations

from fastapi import FastAPI, Request

app = FastAPI(title="AstraDesk API Gateway (stub)", version="0.1.0")


@app.get("/healthz")
def healthz(request: Request | None = None) -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health")
def health(request: Request | None = None) -> dict[str, str]:
    return {"status": "ok"}
