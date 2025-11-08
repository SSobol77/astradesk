# services/admin_api/Dockerfile 

FROM python:3.14-slim

WORKDIR /app

# можно что-то поставить для сборки, если надо
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# метаданные проекта
COPY services/admin_api/pyproject.toml /app/pyproject.toml
COPY services/admin_api/README.md /app/README.md

# исходники admin api
COPY services/admin_api/src /app/src

# ⬇⬇⬇ главное: кладём твои доменные пакеты в тот же /app
COPY packages /app/packages

# самые базовые зависимости
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir fastapi uvicorn

# чтобы astradesk_admin импортировался
ENV PYTHONPATH=/app/src

EXPOSE 8001

CMD ["uvicorn", "astradesk_admin.main:app", "--host", "0.0.0.0", "--port", "8001"]
