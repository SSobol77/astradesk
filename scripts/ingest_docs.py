# scripts/ingest_docs.py
from __future__ import annotations
import os
import sys
import glob
import textwrap
import asyncpg
from runtime.rag import RAG

DB_URL = os.getenv("DATABASE_URL", "postgresql://astradesk:astrapass@localhost:5432/astradesk")

def simple_chunk(text: str, size: int = 600, overlap: int = 100) -> list[str]:
    text = " ".join(text.split())
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i+size])
        i += size - overlap
    return chunks

async def main(path: str) -> None:
    pool = await asyncpg.create_pool(DB_URL)
    rag = RAG(pool)
    files = glob.glob(os.path.join(path, "**", "*.*"), recursive=True)
    for fp in files:
        if not fp.endswith((".md", ".txt")):
            continue
        with open(fp, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read()
        chunks = simple_chunk(data)
        n = await rag.upsert_chunks(source=os.path.basename(fp), chunks=chunks)
        print(f"Ingested {n} chunks from {fp}")
    await pool.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ingest_docs.py <folder>")
        sys.exit(1)
    import asyncio
    asyncio.run(main(sys.argv[1]))
