FROM python:3.11-slim AS base

# Zmienne środowiskowe dla Pythona
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Zmienne środowiskowe dla `uv` (będą użyte później)
ENV UV_EXTRA_INDEX_URL="https://download.pytorch.org/whl/cu121" \
    UV_INDEX_STRATEGY="unsafe-best-match"

WORKDIR /app

# Instalujemy `uv` wewnątrz obrazu za pomocą `pip`
# To jest najbardziej niezawodny sposób.
RUN pip install --no-cache-dir uv

# Instalujemy minimalne zależności systemowe (bez zmian)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Kopiujemy pliki konfiguracyjne zależności
COPY pyproject.toml uv.lock ./

# Instalujemy  zależności projektu za pomocą `uv`
# Używamy `uv sync` zamiast `uv pip install`, co jest szybsze i bardziej powtarzalne.
RUN uv sync --all-extras --frozen

# Kopiujemy resztę kodu aplikacji
COPY src ./src

# Ustawimy domyślną komendę
EXPOSE 8080
CMD ["uv", "run", "uvicorn", "src.gateway.main:app", "--host", "0.0.0.0", "--port", "8080"]