FROM python:3.11-slim

WORKDIR /app

# Iainstalujemy zależności w sposób powtarzalny
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Kopiujemy kod aplikacji
COPY main.py .

# Ustawienie zmiennej, aby logi były od razu widoczne
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]