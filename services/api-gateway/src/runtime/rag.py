# SPDX-License-Identifier: Apache-2.0
# services/api-gateway/src/runtime/rag.py
"""Produkcyjny moduł RAG z leniwym ładowaniem i mechanizmem fallback.

Ten moduł dostarcza zaawansowaną, odporną na błędy implementację RAG,
zaprojektowaną do działania w asynchronicznym środowisku produkcyjnym.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from typing import Any, List, Protocol, Sequence

import asyncpg
import numpy as np

logger = logging.getLogger(__name__)

# --- Konfiguracja ---
HF_MODEL_NAME = os.getenv("HF_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
HF_HOME = os.getenv("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
HF_HUB_OFFLINE = os.getenv("HF_HUB_OFFLINE", "0").lower() in ("1", "true", "yes")
HF_TIMEOUT_SECS = int(os.getenv("HF_HUB_TIMEOUT", "25"))
HF_RETRIES = int(os.getenv("HF_HUB_RETRIES", "2"))
EMB_DIM = 384  # Wymiar dla all-MiniLM-L6-v2

# --- Kontrakt i Implementacje Embedderów ---

class Embedder(Protocol):
    """Kontrakt dla wszystkich klas embedderów."""
    dim: int
    async def embed(self, texts: list[str]) -> np.ndarray: ...

class HashEmbedder(Embedder):
    """Deterministyczny embedder fallback, oparty na haszowaniu."""
    __slots__ = ("dim",)
    
    def __init__(self, dim: int = EMB_DIM) -> None:
        self.dim = dim

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Prosta tokenizacja po białych znakach i znakach nie-alfanumerycznych."""
        out: list[str] = []
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

    async def embed(self, texts: list[str]) -> np.ndarray:
        """Generuje wektory embeddingów na podstawie haszy tokenów."""
        mat = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            vec = np.zeros((self.dim,), dtype=np.float32)
            for tok in self._tokenize(t):
                h = hashlib.blake2b(tok.encode("utf-8"), digest_size=16).digest()
                for j in range(0, 16, 4):
                    idx = int.from_bytes(h[j:j+4], "little") % self.dim
                    vec[idx] += 1.0
            
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec /= norm
            mat[i] = vec
        return mat

class SentenceTransformerEmbedder(Embedder):
    """Wrapper na SentenceTransformer z asynchronicznym, leniwym ładowaniem."""
    __slots__ = ("_model_name", "_model", "dim", "_load_lock")

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model: Any | None = None
        self.dim = EMB_DIM
        self._load_lock = asyncio.Lock()

    async def _ensure_loaded(self) -> None:
        """Asynchronicznie ładuje model z Hugging Face z timeoutem i ponowieniami."""
        if self._model is not None:
            return

        async with self._load_lock:
            if self._model is not None:
                return
            
            from sentence_transformers import SentenceTransformer
            
            logger.info(f"Rozpoczynanie ładowania modelu SentenceTransformer: '{self._model_name}'...")
            
            def _blocking_load():
                """Blokująca funkcja do uruchomienia w osobnym wątku."""
                return SentenceTransformer(
                    self._model_name,
                    cache_folder=HF_HOME,
                    local_files_only=HF_HUB_OFFLINE,
                )

            for attempt in range(HF_RETRIES + 1):
                try:
                    model = await asyncio.wait_for(
                        asyncio.to_thread(_blocking_load),
                        timeout=HF_TIMEOUT_SECS
                    )
                    self._model = model
                    
                    if (dim := getattr(self._model, 'get_sentence_embedding_dimension', lambda: None)()) is not None:
                        self.dim = dim
                    
                    logger.info(f"Model '{self._model_name}' załadowany pomyślnie.")
                    return
                except asyncio.TimeoutError:
                    logger.warning(f"Przekroczono timeout ({HF_TIMEOUT_SECS}s) podczas ładowania modelu (próba {attempt + 1}/{HF_RETRIES + 1}).")
                except Exception as e:
                    logger.warning(f"Błąd podczas ładowania modelu (próba {attempt + 1}/{HF_RETRIES + 1}): {e}")
            
            raise RuntimeError(f"Nie udało się załadować modelu '{self._model_name}' po {HF_RETRIES + 1} próbach.")

    async def embed(self, texts: list[str]) -> np.ndarray:
        """Asynchronicznie wektoryzuje teksty, uruchamiając `encode` w osobnym wątku."""
        await self._ensure_loaded()
        if not self._model:
            raise RuntimeError("Model SentenceTransformer nie został załadowany.")
            
        loop = asyncio.get_running_loop()
        vecs = await loop.run_in_executor(
            None,
            lambda: self._model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        )
        return np.asarray(vecs, dtype=np.float32)

# --- Główna Klasa RAG ---

class RAG:
    """Zarządza cyklem życia dokumentów w systemie RAG."""
    __slots__ = ("pool", "_embedder", "_fallback_embedder")

    def __init__(self, pool: asyncpg.Pool) -> None:
        if pool is None: raise ValueError("Pula połączeń `pool` jest wymagana.")
        self.pool = pool
        self._fallback_embedder = HashEmbedder(dim=EMB_DIM)
        self._embedder: Embedder = self._fallback_embedder
        
        try:
            self._embedder = SentenceTransformerEmbedder(HF_MODEL_NAME)
            logger.info("RAG skonfigurowany do użycia SentenceTransformer.")
        except ImportError:
            logger.warning("Biblioteka `sentence-transformers` nie jest zainstalowana. RAG będzie działał w trybie fallback (HashEmbedder).")
        except Exception as e:
            logger.warning(f"Nie udało się zainicjalizować SentenceTransformer ({e}). RAG będzie działał w trybie fallback.")

    async def _safe_embed(self, texts: list[str]) -> np.ndarray:
        """Wektoryzuje teksty, używając głównego embeddera z automatycznym fallbackiem."""
        try:
            if isinstance(self._embedder, SentenceTransformerEmbedder):
                return await self._embedder.embed(texts)
        except Exception as e:
            logger.error(f"Błąd głównego embeddera SentenceTransformer: {e}. Trwałe przełączenie na HashEmbedder dla tego żądania.")
            self._embedder = self._fallback_embedder
        
        return await self._fallback_embedder.embed(texts)

    @staticmethod
    def _to_vector_literal(embedding: Sequence[float]) -> str:
        """Konwertuje listę float na string akceptowalny przez pgvector: '[1.0,2.0,...]'."""
        return "[" + ",".join(map(str, embedding)) + "]"

    async def retrieve(self, query: str, agent_name: str, k: int = 4) -> list[str]:
        """Zwraca top-k chunków najbardziej podobnych semantycznie do zapytania."""
        embedding_matrix = await self._safe_embed([query])
        query_embedding = embedding_matrix[0]

        sql = """
            SELECT chunk
            FROM documents
            WHERE source LIKE $3
            ORDER BY embedding <-> $1
            LIMIT $2
        """
        try:
            async with self.pool.acquire() as con:
                rows = await con.fetch(
                    sql,
                    self._to_vector_literal(query_embedding.tolist()),
                    k,
                    f"{agent_name}/%"
                )
                return [r["chunk"] for r in rows]
        except asyncpg.PostgresError as e:
            logger.error(f"Błąd podczas wyszukiwania w RAG dla agenta '{agent_name}': {e}", exc_info=True)
            return []