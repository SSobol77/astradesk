# scripts/ingest_docs.py
from __future__ import annotations

import argparse
import os
import sys
import glob
import textwrap
import asyncpg
from runtime.rag import RAG

DB_URL = os.getenv("DATABASE_URL", "postgresql://astradesk:astrapass@localhost:5432/astradesk")


async def main():
    parser = argparse.ArgumentParser(description="Ingest documents into RAG for a specific agent.")
    parser.add_argument(
        "agent_name",
        type=str,
        choices=["support", "ops"], # Ograniczamy do znanych agentów
        help="The name of the agent whose dataset should be ingested."
    )
    args = parser.parse_args()

    # Budujemy ścieżkę do odpowiedniego katalogu
    dataset_path = os.path.join("datasets", args.agent_name)
    
    if not os.path.isdir(dataset_path):
        print(f"Error: Directory not found for agent '{args.agent_name}' at '{dataset_path}'")
        return


def simple_chunk(text: str, size: int = 600, overlap: int = 100) -> list[str]:
    text = " ".join(text.split())
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i+size])
        i += size - overlap
    return chunks


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ingest_docs.py <folder>")
        sys.exit(1)
    import asyncio
    asyncio.run(main(sys.argv[1]))
