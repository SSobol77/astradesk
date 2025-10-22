# SPDX-License-Identifier: Apache-2.0
# File: Dockerfile
# Description:
#     Dockerfile for the AstraDesk API service.
#     Builds a Python 3.11-based image for running the API with Uvicorn.
# Author: Siergej Sobolewski
# Since: 2025-10-11
# Główny Dockerfile (dla serwisu `api`)
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ENV UV_EXTRA_INDEX_URL="https://download.pytorch.org/whl/cu121"
ENV UV_INDEX_STRATEGY="unsafe-best-match"

WORKDIR /app

RUN pip install --no-cache-dir uv

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
# Kopiujemy też paczki, bo workspace ich potrzebuje
COPY packages/ ./packages/

RUN uv sync --all-extras --frozen

COPY src ./src

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "src.gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]