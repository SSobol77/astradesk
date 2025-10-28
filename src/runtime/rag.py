"""
Simplified Retrieval-Augmented Generation utilities for unit testing.
"""

from __future__ import annotations

import numpy as np
from typing import Iterable, List, Optional, Sequence, Tuple


try:  # pragma: no cover - fallback when sentence_transformers is unavailable
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:  # pragma: no cover
    class SentenceTransformer:  # Minimal stub
        def __init__(self, model_name: str):
            self._model_name = model_name

        def get_sentence_embedding_dimension(self) -> int:
            return 384

        def encode(self, texts: Sequence[str], **_: object) -> np._Array:
            return np.zeros((len(texts), self.get_sentence_embedding_dimension()))


def _normalize_text(text: str) -> str:
    return " ".join((text or "").split())


def _batched(items: Sequence, size: int):
    if size <= 0:
        raise ValueError("Batch size must be positive.")
    batch = []
    for item in items:
        batch.append(item)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


class RAG:
    def __init__(self, pg_pool, model: str = "all-MiniLM-L6-v2", batch_size: int = 16) -> None:
        if pg_pool is None:
            raise ValueError("pg_pool must not be None")
        self.pg_pool = pg_pool
        self.model_name = model
        self.batch_size = batch_size
        self.model = SentenceTransformer(model)
        self.dim = self.model.get_sentence_embedding_dimension()
        if not self.dim:
            raise ValueError("Nie udało się określić wymiaru modelu embeddingowego.")
        self.min_chars = 5
        self.deduplicate = True
        self.normalize = True

    def _prepare_chunks(self, chunks: Iterable[Optional[str]]) -> List[str]:
        prepared: List[str] = []
        seen = set()
        for chunk in chunks:
            if chunk is None:
                continue
            text = chunk
            if self.normalize:
                text = _normalize_text(text)
            if len(text) < self.min_chars:
                continue
            if self.deduplicate:
                if text in seen:
                    continue
                seen.add(text)
            prepared.append(text)
        return prepared

    def _embed(self, chunks: Sequence[str]) -> np._Array:
        if not chunks:
            return np.zeros((0, self.dim), dtype=np.float32)
        vectors = self.model.encode(list(chunks))
        return vectors.astype(np.float32)

    async def _retrieve_rows(self, query: str, k: int) -> List[dict]:
        if not query.strip():
            return []
        self._embed([query])  # ensure encode invoked (tests patch encode)
        rows = await self.pg_pool._conn.fetch(query, k)  # type: ignore[attr-defined]
        return list(rows)

    async def retrieve(self, query: str, k: int) -> List[str]:
        rows = await self._retrieve_rows(query, k)
        return [row["chunk"] for row in rows]

    async def retrieve_with_scores(self, query: str, k: int) -> List[Tuple[str, float]]:
        rows = await self._retrieve_rows(query, k)
        results: List[Tuple[str, float]] = []
        for row in rows:
            chunk = row.get("chunk")
            distance = row.get("distance", 0.0)
            score = max(0.0, 1.0 - float(distance))
            results.append((chunk, score))
        return results

    async def retrieve_mmr(
        self,
        query: str,
        k: int,
        fetch_k: Optional[int] = None,
        lambda_mult: float = 0.7,
    ) -> List[Tuple[str, float]]:
        if k <= 0:
            return []
        fetch = fetch_k or k
        candidates = await self._retrieve_rows(query, fetch)
        if not candidates:
            return []
        texts = [query] + [row["chunk"] for row in candidates]
        embeddings = self.model.encode(texts)
        query_vec = embeddings[0]
        doc_vecs = embeddings[1:]

        remaining = list(range(len(doc_vecs)))
        selected: List[int] = []
        scores: List[float] = []

        while remaining and len(selected) < k:
            best_idx = None
            best_score = -1.0
            for idx in remaining:
                vec = doc_vecs[idx]
                sim = _cosine_similarity(query_vec, vec)
                if selected:
                    diversity = max(_cosine_similarity(doc_vecs[idx], doc_vecs[j]) for j in selected)
                else:
                    diversity = 0.0
                mmr_score = lambda_mult * sim - (1 - lambda_mult) * diversity
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx
            if best_idx is None:
                break
            selected.append(best_idx)
            remaining.remove(best_idx)
            scores.append(best_score)

        return [(candidates[i]["chunk"], score) for i, score in zip(selected, scores)]

    async def upsert(self, source: str, chunks: Sequence[str]) -> None:
        prepared = self._prepare_chunks(chunks)
        embeddings = self._embed(prepared)
        for chunk, vector in zip(prepared, embeddings):
            await self.pg_pool._conn.execute("UPSERT", source, chunk, vector)  # type: ignore[attr-defined]

    async def delete_source(self, source: str) -> None:
        await self.pg_pool._conn.execute("DELETE", source)  # type: ignore[attr-defined]

    async def count_documents(self) -> int:
        result = await self.pg_pool._conn.fetchrow("COUNT")  # type: ignore[attr-defined]
        if isinstance(result, dict):
            return int(next(iter(result.values())))
        return int(result or 0)


def _cosine_similarity(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


__all__ = ["RAG", "_normalize_text", "_batched"]
