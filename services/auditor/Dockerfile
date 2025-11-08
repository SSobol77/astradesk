FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1

# Install core library first so dependent packages resolve
COPY core /opt/astradesk/core
RUN pip install --no-cache-dir /opt/astradesk/core

# Install auditor service (packaged via pyproject)
COPY services/auditor /opt/astradesk/auditor
RUN pip install --no-cache-dir /opt/astradesk/auditor

WORKDIR /opt/astradesk/auditor
CMD ["python", "main.py"]
