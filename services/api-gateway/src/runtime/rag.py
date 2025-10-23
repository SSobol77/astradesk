# SPDX-License-Identifier: Apache-2.0
"""
runtime.rag — RAG z pgvector:
- lazy load SentenceTransformer (bez blokowania startu serwera),
- twardy timeout pobierania modelu z HF + retry,
- tryb offline/lokalny cache,
- deterministyczny fallback embedder, gdy HF niedostępny,
- poprawne bindowanie do pgvector (string literal -> ::vector).
"""

from __future__ import annotations

import logging
import os
import time
import math
import hashlib
from typing import List, Sequence, Optional

import asyncpg
import numpy as np

logger = logging.getLogger(__name__)

CREATE_SQL = """
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS kb_docs (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source    TEXT NOT NULL,
    chunk     TEXT NOT NULL,
    embedding vector(384) NOT NULL  -- wymiary zgodne z all-MiniLM-L6-v2
);
"""

# Konfiguracja HF przez env:
HF_MODEL_NAME = os.getenv("HF_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
HF_HOME = os.getenv("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
HF_HUB_OFFLINE = os.getenv("HF_HUB_OFFLINE", "0").lower() in ("1", "true", "yes")
HF_TIMEOUT_SECS = int(os.getenv("HF_HUB_TIMEOUT", "25"))  # twardy timeout pojedynczej próby pobrania modelu
HF_RETRIES = int(os.getenv("HF_HUB_RETRIES", "2"))        # dodatkowe próby

EMB_DIM = 384  # MiniLM-L6-v2 = 384


class _Embedder:
    """Interfejs dla embeddera (prawdziwy albo fallback)."""
    dim: int

    def embed(self, texts: List[str]) -> np.ndarray:
        raise NotImplementedError


class _HashEmbedder(_Embedder):
    """
    Bardzo szybki, deterministyczny fallback:
    - mapuje tokeny (b. prosto) do 384-wymiarowego wektora przez haszowanie,
    - normalizuje L2 (jak SentenceTransformers z normalize_embeddings=True).
    To NIE ma jakości S-BERT, ale pozwala 100% utrzymać usługę, gdy HF leży.
    """

    def __init__(self, dim: int = EMB_DIM) -> None:
        self.dim = dim

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        # Mega-prosta tokenizacja po białych znakach i znakach nie-alfanumerycznych.
        out: List[str] = []
        token = []
        for ch in text.lower():
            if ch.isalnum():
                token.append(ch)
            elif token:
                out.append("".join(token))
                token = []
        if token:
            out.append("".join(token))
        return out or ["_empty_"]

    def embed(self, texts: List[str]) -> np.ndarray:
        mat = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            vec = np.zeros((self.dim,), dtype=np.float32)
            for tok in self._tokenize(t):
                h = hashlib.blake2b(tok.encode("utf-8"), digest_size=16).digest()
                # Użyj 4 bajtowych „slotów”
                for j in range(0, 16, 4):
                    idx = int.from_bytes(h[j:j+4], "little") % self.dim
                    vec[idx] += 1.0
            # normalizacja L2
            norm = float(np.linalg.norm(vec))
            if norm > 0:
                vec /= norm
            mat[i] = vec
        return mat


class _SentenceTREmbedder(_Embedder):
    """Thin-wrapper na SentenceTransformer, z offline support i timeoutami."""
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model = None
        self.dim = EMB_DIM  # ustawimy po załadowaniu

    def _download_with_timebox(self) -> None:
        # Pobieramy model z HF z twardym timeoutem i retry.
        import threading
        from sentence_transformers import SentenceTransformer

        last_err: Optional[BaseException] = None
        for attempt in range(1, HF_RETRIES + 2):
            done = False
            model_holder = {}

            def _load():
                try:
                    model_holder["m"] = SentenceTransformer(
                        self._model_name,
                        cache_folder=HF_HOME,
                        local_files_only=HF_HUB_OFFLINE,
                        trust_remote_code=True,
                    )
                except BaseException as e:  # noqa: BLE001
                    nonlocal last_err
                    last_err = e
                finally:
                    nonlocal done
                    done = True

            th = threading.Thread(target=_load, daemon=True)
            th.start()
            start = time.time()
            while not done and (time.time() - start) < HF_TIMEOUT_SECS:
                time.sleep(0.05)
            if not done:
                logger.warning("HF: przekroczono timeout %ss podczas ładowania modelu (próba %s/%s)",
                               HF_TIMEOUT_SECS, attempt, HF_RETRIES + 1)
                # spróbuj ubić i kolejna próba
                continue

            if "m" in model_holder and model_holder["m"] is not None:
                self._model = model_holder["m"]
                try:
                    dim = self._model.get_sentence_embedding_dimension()
                    if dim:
                        self.dim = int(dim)
                except Exception:
                    pass
                return
            else:
                logger.warning("HF: nie udało się załadować modelu (próba %s/%s): %s",
                               attempt, HF_RETRIES + 1, last_err)

        raise RuntimeError(f"Nie udało się pobrać/załadować modelu '{self._model_name}' w limicie czasu.")

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        self._download_with_timebox()

    def embed(self, texts: List[str]) -> np.ndarray:
        self._ensure_loaded()
        vec = self._model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return np.asarray(vec, dtype=np.float32)


class RAG:
    """
    RAG z pgvector i dwoma trybami embeddera:
      - SentenceTransformer (HF) — jeśli dostępny,
      - HashEmbedder (fallback) — gdy HF niedostępny.
    """
    __slots__ = ("pool", "_embedder", "_fallback")

    def __init__(self, pool: asyncpg.Pool, prefer_offline: bool | None = None) -> None:
        if pool is None:
            raise ValueError("pool is required")
        self.pool = pool

        # logika wyboru embeddera na starcie TYLKO jako deklaracja; init modelu leniwie
        use_offline = HF_HUB_OFFLINE if prefer_offline is None else prefer_offline
        self._fallback = _HashEmbedder(dim=EMB_DIM)
        try:
            if use_offline:
                logger.info("RAG: działam w trybie OFFLINE — preferuję lokalny cache HF.")
            self._embedder = _SentenceTREmbedder(HF_MODEL_NAME)
        except Exception as e:
            logger.warning("RAG: nie udało się przygotować SentenceTransformer (%s) — używam fallbacku.", e)
            self._embedder = self._fallback

    async def init_schema(self) -> None:
        async with self.pool.acquire() as con:
            await con.execute(CREATE_SQL)

    @staticmethod
    def _to_vector_literal(emb: Sequence[float]) -> str:
        # pgvector akceptuje zapis: [e1,e2,...]
        return "[" + ",".join(f"{x:.6f}" for x in emb) + "]"

    def _safe_embed(self, text: str) -> np.ndarray:
        """
        Zwraca 1xD embedding. W razie problemów z HF — przełącza się na fallback.
        """
        try:
            vec = self._embedder.embed([text])
            if not isinstance(vec, np.ndarray) or vec.ndim != 2 or vec.shape[0] != 1:
                raise RuntimeError("embedder zwrócił nieprawidłowy kształt wektora")
            return vec
        except Exception as e:
            logger.error("RAG: błąd embeddera (%s). Przełączam na fallback.", e)
            self._embedder = self._fallback
            return self._embedder.embed([text])

    async def retrieve(self, query: str, k: int = 4) -> List[str]:
        """
        Zwróć top-k chunków najbardziej podobnych semantycznie do zapytania.
        """
        # 1) Embedding zapytania
        vec = self._safe_embed(query)  # (1, D)
        emb: np.ndarray = np.asarray(vec, dtype=np.float32)[0]
        vec_lit = self._to_vector_literal(emb.tolist())  # "[0.123,-0.234,...]"

        # 2) Zapytanie top-k
        sql = """
        SELECT chunk
        FROM kb_docs
        ORDER BY embedding <-> $1::vector
        LIMIT $2;
        """
        async with self.pool.acquire() as con:
            await self.init_schema()
            rows = await con.fetch(sql, vec_lit, k)
            return [r["chunk"] for r in rows]
