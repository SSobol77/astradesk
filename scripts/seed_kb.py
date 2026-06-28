# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: scripts/seed_kb.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for scripts/seed_kb.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

# scripts/seed_kb.py
# Wstawia kilka przykładowych fragmentów do kb_docs.
# - Jeśli HF (SentenceTransformer) jest dostępny, użyje go.
# - Jeśli nie, skorzysta z fallbackowego hash-embeddera (zgodnie z runtime/rag.py).
import asyncio

# Minimalny embedder spójny z fallbackiem z runtime/rag.py (hash-based)
import hashlib
import os

import numpy as np

import asyncpg

EMB_DIM = 384


def hash_embed(texts: list[str]) -> np.ndarray:
    def tokenize(s: str) -> list[str]:
        out, tok = [], []
        for ch in s.lower():
            if ch.isalnum():
                tok.append(ch)
            elif tok:
                out.append(''.join(tok))
                tok = []
        if tok:
            out.append(''.join(tok))
        return out or ['_empty_']

    mat = np.zeros((len(texts), EMB_DIM), dtype=np.float32)
    for i, t in enumerate(texts):
        vec = np.zeros((EMB_DIM,), dtype=np.float32)
        for tok in tokenize(t):
            h = hashlib.blake2b(tok.encode('utf-8'), digest_size=16).digest()
            for j in range(0, 16, 4):
                idx = int.from_bytes(h[j : j + 4], 'little') % EMB_DIM
                vec[idx] += 1.0
        n = float(np.linalg.norm(vec))
        if n > 0:
            vec /= n
        mat[i] = vec
    return mat


def to_vec_literal(row: np.ndarray) -> str:
    return '[' + ','.join(f'{float(x):.6f}' for x in row.tolist()) + ']'


PAYLOAD = [
    ('faq', 'Aby zresetować hasło, użyj portalu SSO i wybierz „Nie pamiętam hasła”.'),
    ('faq', 'VPN: upewnij się, że klient ma aktualną konfigurację i certyfikaty.'),
    ('runbook', 'Webapp: jeśli CPU > 80% przez 15m, zbadaj p95 i autoscaling.'),
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
    dsn = os.environ.get('DATABASE_URL')
    if not dsn:
        raise SystemExit('Set DATABASE_URL in env')

    con = await asyncpg.connect(dsn)
    try:
        await con.execute(CREATE_SQL)
        texts = [p[1] for p in PAYLOAD]
        emb = hash_embed(texts)  # TODO: do produkcji trzeba podmienić na prawdziwy encoder

        for (source, chunk), row in zip(PAYLOAD, emb, strict=False):
            vec_lit = to_vec_literal(row)
            await con.execute(INSERT_SQL, source, chunk, vec_lit)
        print(f'Inserted {len(PAYLOAD)} rows into docs.')
    finally:
        await con.close()


if __name__ == '__main__':
    asyncio.run(main())
