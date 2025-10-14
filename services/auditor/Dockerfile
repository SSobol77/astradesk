FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy the application code
COPY main.py .

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]