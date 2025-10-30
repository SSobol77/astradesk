# services/admin_api/Dockerfile 

FROM python:3.14-slim 

# Install system basics 
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates build-essential && rm -rf /var/lib/apt/lists/* 

# Install uv (standalone) 
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && /root/.cargo/bin/uv --version 

ENV PATH="/root/.cargo/bin:${PATH}" 

WORKDIR /app 

# Copy project metadata and sources 
COPY pyproject.toml README.md /app/ 
COPY src /app/src 

# Sync runtime deps (no dev extras) into an isolated env 
RUN uv sync --frozen --no-dev EXPOSE 8001 CMD ["uv", "run", "uvicorn", "astradesk_admin.main:app", "--host", "0.0.0.0", "