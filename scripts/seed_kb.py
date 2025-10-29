# scripts/seed_kb.py
# Wstawia kilka przykładowych fragmentów do kb_docs.
# - Jeśli HF (SentenceTransformer) jest dostępny, użyje go.
# - Jeśli nie, skorzysta z fallbackowego hash-embeddera (zgodnie z runtime/rag.py).
import os
import asyncio
import asyncpg
import numpy as np

from typing import List
from pathlib import Path

# Minimalny embedder spójny z fallbackiem z runtime/rag.py (hash-based)
import hashlib

EMB_DIM = 384

def hash_embed(texts: List[str]) -> np.ndarray:
    def tokenize(s: str) -> List[str]:
        out, tok = [], []
        for ch in s.lower():
            if ch.isalnum():
                tok.append(ch)
            elif tok:
                out.append("".join(tok)); tok=[]
        if tok: out.append("".join(tok))
        return out or ["_empty_"]

    mat = np.zeros((len(texts), EMB_DIM), dtype=np.float32)
    for i, t in enumerate(texts):
        vec = np.zeros((EMB_DIM,), dtype=np.float32)
        for tok in tokenize(t):
            h = hashlib.blake2b(tok.encode("utf-8"), digest_size=16).digest()
            for j in range(0, 16, 4):
                idx = int.from_bytes(h[j:j+4], "little") % EMB_DIM
                vec[idx] += 1.0
        n = float(np.linalg.norm(vec))
        if n > 0: vec /= n
        mat[i] = vec
    return mat

def to_vec_literal(row: np.ndarray) -> str:
    return "[" + ",".join(f"{float(x):.6f}" for x in row.tolist()) + "]"

PAYLOAD = [
    ("faq", "Aby zresetować hasło, użyj portalu SSO i wybierz „Nie pamiętam hasła”."),
    ("faq", "VPN: upewnij się, że klient ma aktualną konfigurację i certyfikaty."),
    ("runbook", "Webapp: jeśli CPU > 80% przez 15m, zbadaj p95 i autoscaling."),
]

CREATE_SQL = """
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS docs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source TEXT NOT NULL,
  chunk TEXT NOT NULL,
  embedding vector(384) NOT NULL
);
"""

INSERT_SQL = """
INSERT INTO docs(source, chunk, embedding)
VALUES ($1, $2, $3::vector)
"""

async def main():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("Set DATABASE_URL in env")

    con = await asyncpg.connect(dsn)
    try:
        await con.execute(CREATE_SQL)
        texts = [p[1] for p in PAYLOAD]
        emb = hash_embed(texts)  # TODO: do produkcji trzeba podmienić na prawdziwy encoder

        for (source, chunk), row in zip(PAYLOAD, emb):
            vec_lit = to_vec_literal(row)
            await con.execute(INSERT_SQL, source, chunk, vec_lit)
        print(f"Inserted {len(PAYLOAD)} rows into docs.")
    finally:
        await con.close()

if __name__ == "__main__":
    asyncio.run(main())
