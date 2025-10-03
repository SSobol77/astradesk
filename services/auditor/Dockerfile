FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir nats-py boto3 httpx
COPY main.py .
CMD ["python","main.py"]
