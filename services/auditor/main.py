# services/auditor/main.py
"""Mikroserwis Auditora dla AstraDesk.

Serwis ten subskrybuje zdarzenia audytowe z NATS, buforuje je, a następnie
w sposób niezawodny zapisuje do długoterminowych systemów przechowywania
danych, takich jak Elasticsearch i AWS S3.

Główne cechy:
- **Niezawodność**: Implementuje logikę "graceful shutdown" do obsługi
  sygnałów SIGINT/SIGTERM, zapewniając zapisanie danych z bufora przed
  zamknięciem.
- **Wydajność**: Używa w pełni asynchronicznych bibliotek (`nats-py`,
  `aioboto3`, `httpx`) do nieblokującej obsługi I/O.
- **Obserwowalność**: Wykorzystuje ustrukturyzowane logowanie w formacie JSON,
  co ułatwia analizę logów w systemach takich jak ELK czy Grafana Loki.
- **Odporność na błędy**: Każda operacja zapisu jest opakowana w solidną
  obsługę błędów z logowaniem. W przyszłości można tu dodać mechanizm
  Dead-Letter Queue (DLQ).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import time
from typing import Any, Dict, List

import aioboto3
import httpx
import nats
from botocore.exceptions import BotoCoreError
from python_json_logger import jsonlogger

# --- Konfiguracja ---
NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")
AUDIT_SUBJECT = "astradesk.audit"
S3_BUCKET = os.getenv("S3_BUCKET", "astradesk-audit")
AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
ES_URL = os.getenv("ES_URL", "http://elasticsearch:9200")
ES_INDEX = os.getenv("ES_INDEX", "astradesk-audit")
FLUSH_SIZE = int(os.getenv("FLUSH_SIZE", "100"))
FLUSH_INTERVAL_SEC = int(os.getenv("FLUSH_INTERVAL_SEC", "10"))

# --- Konfiguracja Ustrukturyzowanego Logowania ---
logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    '%(asctime)s %(name)s %(levelname)s %(message)s'
)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)


class Auditor:
    """Zarządza subskrypcją, buforowaniem i zapisem zdarzeń audytowych."""

    def __init__(self) -> None:
        self._buf: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._last_flush_time = time.monotonic()
        self._shutdown_event = asyncio.Event()

    async def _persist_to_es(self, batch: List[Dict[str, Any]], client: httpx.AsyncClient) -> None:
        """Zapisuje partię danych do Elasticsearch przy użyciu API _bulk."""
        try:
            ndjson_lines = []
            for doc in batch:
                ndjson_lines.append(json.dumps({"index": {"_index": ES_INDEX}}))
                ndjson_lines.append(json.dumps(doc, ensure_ascii=False))
            payload = "\n".join(ndjson_lines) + "\n"
            
            resp = await client.post(
                f"{ES_URL}/_bulk",
                content=payload,
                headers={"Content-Type": "application/x-ndjson"},
            )
            resp.raise_for_status()
            logger.info(f"Pomyślnie zapisano {len(batch)} zdarzeń w Elasticsearch.")
        except httpx.HTTPStatusError as e:
            logger.error(
                "Błąd HTTP podczas zapisu do Elasticsearch.",
                extra={"status_code": e.response.status_code, "response": e.response.text},
            )
        except Exception as e:
            logger.error("Nieoczekiwany błąd podczas zapisu do Elasticsearch.", exc_info=True)

    async def _persist_to_s3(self, batch: List[Dict[str, Any]], s3_client) -> None:
        """Zapisuje partię danych jako obiekt NDJSON w S3."""
        try:
            key = f"audit/{int(time.time())}-{len(batch)}.ndjson"
            body = "\n".join(json.dumps(d, ensure_ascii=False) for d in batch)
            
            await s3_client.put_object(Bucket=S3_BUCKET, Key=key, Body=body.encode("utf-8"))
            logger.info(f"Pomyślnie zapisano {len(batch)} zdarzeń w S3 pod kluczem: {key}")
        except BotoCoreError:
            logger.error("Błąd BotoCore podczas zapisu do S3.", exc_info=True)

    async def _flush(self) -> None:
        """Pobiera dane z bufora i zleca ich zapis."""
        async with self._lock:
            if not self._buf:
                return
            batch_to_flush = self._buf
            self._buf = []
            self._last_flush_time = time.monotonic()
        
        logger.info(f"Rozpoczynanie zapisu partii {len(batch_to_flush)} zdarzeń.")
        
        # Tworzymy klientów wewnątrz, aby zapewnić świeże połączenia
        async with httpx.AsyncClient(timeout=10.0) as http_client, \
                   aioboto3.Session().client("s3", region_name=AWS_REGION) as s3_client:
            await asyncio.gather(
                self._persist_to_es(batch_to_flush, http_client),
                self._persist_to_s3(batch_to_flush, s3_client),
            )

    async def _message_handler(self, msg: nats.aio.msg.Msg) -> None:
        """Przetwarza pojedynczą wiadomość z NATS."""
        try:
            data = json.loads(msg.data)
            async with self._lock:
                self._buf.append(data)
        except json.JSONDecodeError:
            logger.warning("Otrzymano nieprawidłowy format JSON w wiadomości NATS.", extra={"raw_data": msg.data.decode('utf-8', 'ignore')})

    async def _periodic_flush(self) -> None:
        """Okresowo sprawdza, czy bufor powinien zostać zapisany."""
        while not self._shutdown_event.is_set():
            await asyncio.sleep(1)
            async with self._lock:
                buffer_size = len(self._buf)
                time_since_flush = time.monotonic() - self._last_flush_time
            
            if buffer_size >= FLUSH_SIZE or (buffer_size > 0 and time_since_flush >= FLUSH_INTERVAL_SEC):
                await self._flush()

    async def run(self) -> None:
        """Główna pętla działania serwisu."""
        nc = await nats.connect(NATS_URL)
        logger.info(f"Pomyślnie połączono z NATS pod adresem: {NATS_URL}")
        
        await nc.subscribe(AUDIT_SUBJECT, cb=self._message_handler)
        logger.info(f"Zasubskrybowano temat NATS: '{AUDIT_SUBJECT}'")
        
        flush_task = asyncio.create_task(self._periodic_flush())
        
        await self._shutdown_event.wait()
        
        # Graceful shutdown
        logger.info("Otrzymano sygnał zamknięcia. Zapisywanie pozostałych danych z bufora...")
        flush_task.cancel()
        await self._flush()
        await nc.close()
        logger.info("Auditor został pomyślnie zamknięty.")

    def _handle_shutdown_signal(self) -> None:
        """Obsługuje sygnały SIGINT/SIGTERM."""
        logger.info("Inicjowanie procedury graceful shutdown...")
        self._shutdown_event.set()

def main():
    loop = asyncio.get_event_loop()
    auditor = Auditor()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, auditor._handle_shutdown_signal)
        
    try:
        loop.run_until_complete(auditor.run())
    finally:
        loop.close()

if __name__ == "__main__":
    main()
