FROM ghcr.io/astral-sh/uv:0.4.22-py3.11.8 AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ENV UV_EXTRA_INDEX_URL="https://download.pytorch.org/whl/cu121" UV_INDEX_STRATEGY="unsafe-best-match"

WORKDIR /app

# Install system dependencies (only what's needed for torch and pgvector)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and lockfile
COPY pyproject.toml uv.lock ./

# Sync dependencies (including dev for consistency with CI)
RUN uv sync --all-extras --frozen

# Copy application code
COPY src ./src
COPY gateway ./gateway
COPY migrations ./migrations
COPY scripts ./scripts

EXPOSE 8080
CMD [".venv/bin/uv", "run", "python", "-m", "gateway.main"]
