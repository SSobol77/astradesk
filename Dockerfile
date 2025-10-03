FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# uv + deps
COPY pyproject.toml ./
RUN pip install --upgrade pip uv && uv venv && . .venv/bin/activate && uv sync --frozen

COPY src ./src
COPY gateway ./gateway
COPY migrations ./migrations
COPY scripts ./scripts

EXPOSE 8080
CMD [".venv/bin/python","-m","gateway.main"]
