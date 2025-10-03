"""
Auditor microservice:
- Subskrybuje NATS subject: "astradesk.audit"
- Buforuje i zapisuje zdarzenia do S3 (parquet/ndjson) oraz Elasticsearch.

Zmienne środowiskowe:
- NATS_URL=nats://nats:4222
- S3_BUCKET=astradesk-audit
- AWS_REGION=eu-central-1
- ES_URL=http://elasticsearch:9200
- ES_INDEX=astradesk-audit
- FLUSH_SIZE=200
- FLUSH_INTERVAL_SEC=10
"""

from __future__ import annotations
import asyncio
import json
import os
import time
from typing import Any, List

import nats
import boto3
import botocore
import httpx

NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")
S3_BUCKET = os.getenv("S3_BUCKET", "astradesk-audit")
AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
ES_URL = os.getenv("ES_URL", "http://elasticsearch:9200")
ES_INDEX = os.getenv("ES_INDEX", "astradesk-audit")
FLUSH_SIZE = int(os.getenv("FLUSH_SIZE", "200"))
FLUSH_INTERVAL_SEC = int(os.getenv("FLUSH_INTERVAL_SEC", "10"))


class Auditor:
    """Prosty buforujący subscriber; bezpieczny w użyciu w środowisku produkcyjnym."""

    def __init__(self) -> None:
        self._nc: nats.NATS | None = None
        self._buf: list[dict[str, Any]] = []
        self._last_flush = time.time()

        # Klienci S3 i Elasticsearch
        self._s3 = boto3.client("s3", region_name=AWS_REGION)
        self._http = httpx.AsyncClient(timeout=10.0)

    async def connect(self) -> None:
        self._nc = await nats.connect(NATS_URL)

    async def _flush_if_needed(self, force: bool = False) -> None:
        if not self._buf:
            return
        cond_size = len(self._buf) >= FLUSH_SIZE
        cond_time = (time.time() - self._last_flush) >= FLUSH_INTERVAL_SEC
        if force or cond_size or cond_time:
            batch = self._buf
            self._buf = []
            self._last_flush = time.time()
            await self._persist_batch(batch)

    async def _persist_batch(self, batch: List[dict[str, Any]]) -> None:
        # 1) Elasticsearch (bulk NDJSON)
        try:
            ndjson_lines = []
            for doc in batch:
                ndjson_lines.append(json.dumps({"index": {"_index": ES_INDEX}}))
                ndjson_lines.append(json.dumps(doc, ensure_ascii=False))
            payload = "\n".join(ndjson_lines) + "\n"
            es_bulk_url = f"{ES_URL}/_bulk"
            r = await self._http.post(es_bulk_url, content=payload, headers={"Content-Type": "application/x-ndjson"})
            r.raise_for_status()
        except Exception as e:
            # log do stderr; w realnym systemie: logger + retry z kolejką DLQ
            print(f"[WARN] ES bulk error: {e}")

        # 2) S3 (append-like: zapisujemy partię z timestampem)
        try:
            key = f"audit/{int(time.time())}-{len(batch)}.ndjson"
            body = "\n".join(json.dumps(d, ensure_ascii=False) for d in batch).encode("utf-8")
            self._s3.put_object(Bucket=S3_BUCKET, Key=key, Body=body)
        except botocore.exceptions.BotoCoreError as e:
            print(f"[WARN] S3 put_object error: {e}")

    async def run(self) -> None:
        if not self._nc:
            await self.connect()

        async def handler(msg: nats.aio.msg.Msg):
            try:
                data = json.loads(msg.data.decode("utf-8"))
                self._buf.append(data)
                await self._flush_if_needed()
            except Exception as e:
                print(f"[WARN] auditor parse error: {e}")

        await self._nc.subscribe("astradesk.audit", cb=handler)
        print("[INFO] Auditor subscribed to 'astradesk.audit'")

        # pętla flushująca co FLUSH_INTERVAL_SEC
        while True:
            await asyncio.sleep(FLUSH_INTERVAL_SEC)
            await self._flush_if_needed(force=False)


if __name__ == "__main__":
    auditor = Auditor()
    asyncio.run(auditor.run())
