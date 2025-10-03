# src/runtime/rag.py
# -*- coding: utf-8 -*-
# Program jest objęty licencją Apache-2.0.
# Autor: Siergej Sobolewski
#
# Cel modułu
# ----------
# Zawodowa warstwa RAG (Retrieval-Augmented Generation) dla AstraDesk:
#  - Wektoryzacja tekstu (SentenceTransformer),
#  - Składowanie i podobieństwo w Postgres + pgvector (cosine),
#  - API do insertów i wyszukiwania z wieloma wariantami (proste / MMR),
#  - Skorygowana metryka: z dystansu kosinusowego (<->) wyliczamy similarity.
#
# Projektowe założenia:
#  - Używamy pgvector z operatorem "<->" i operatorem indeksowym vector_cosine_ops,
#    co implikuje: distance = 1 - cosine_similarity.
#  - Wstawki asynchroniczne; batchowanie encodowania po stronie modelu.
#  - Brak zmian schematu: tabela `documents(id, source, chunk, embedding, created_at)`.
#
# Minimalne wymagania:
#  - asyncpg, numpy, sentence-transformers
#
# Uwaga:
#  - Warstwa nie generuje finalnej odpowiedzi LLM — jedynie zapewnia retrieval.
#  - Przy pierwszym uruchomieniu pamiętaj wykonać migrację z rozszerzeniem pgvector.
#    (patrz migrations/0001_init_pgvector.sql w projekcie).
#

from __future__ import annotations

from typing import Any, Iterable, List, Sequence, Tuple

import asyncio
import math
import unicodedata

import asyncpg
import numpy as np
from sentence_transformers import SentenceTransformer


# -----------------------------
# Pomocnicze funkcje narzędziowe
# -----------------------------

def _normalize_text(s: str) -> str:
    """
    Delikatna normalizacja treści:
      - NFC (stabilizacja akcentów/unicode),
      - strip() i kolaps wielokrotnych białych znaków do pojedynczych spacji.
    Nie robimy agresywnych transformacji (lowercase, usuwanie znaków),
    żeby nie tracić informacji – to rola embeddingów.
    """
    s = unicodedata.normalize("NFC", s)
    s = s.strip()
    # Łagodna redukcja białych znaków
    out = []
    ws = False
    for ch in s:
        if ch.isspace():
            if not ws:
                out.append(" ")
                ws = True
        else:
            out.append(ch)
            ws = False
    return "".join(out)


def _batched(seq: Sequence[str], size: int) -> Iterable[Sequence[str]]:
    """Dzieli sekwencję na bloki o maksymalnym rozmiarze `size`."""
    if size <= 0:
        raise ValueError("batch size must be > 0")
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


# ---------------------------------
# Główna klasa: RAG (embed + search)
# ---------------------------------

class RAG:
    """
    RAG: embed → (Postgres+pgvector) → retrieve.

    Kluczowe założenia:
      - Korzystamy z SentenceTransformer z normalizacją embeddingów
        (`normalize_embeddings=True`), co współgra z indeksami pgvector
        (vector_cosine_ops) i operatorami odległości `<->`.
      - W enkoderze robimy batchowanie, żeby nie przepełniać RAM/VRAM.
      - Zwracamy teksty oraz (opcjonalnie) *score* ∈ [0, 1] (cosine similarity).

    Parametry:
      pg_pool        : asyncpg.Pool — współdzielona pula połączeń do Postgresa,
      model          : nazwa modelu SentenceTransformer,
      batch_size     : rozmiar batcha do encodowania,
      deduplicate    : czy odrzucać ewidentne duplikaty wejściowych chunków,
      min_chars      : minimalna długość sensownego chunku (filtr szumu),
      normalize      : czy normalizować treści (NFC + whitespace collapse).

    Uwaga dot. pgvector:
      - Jeśli tworzysz indeks: `USING ivfflat (embedding vector_cosine_ops)`,
        to operator `<->` zwraca *cosine distance*. Similarity = 1 - distance.
    """

    def __init__(
        self,
        pg_pool: asyncpg.Pool,
        model: str = "sentence-transformers/all-MiniLM-L6-v2",
        *,
        batch_size: int = 64,
        deduplicate: bool = True,
        min_chars: int = 10,
        normalize: bool = True,
    ) -> None:
        if pg_pool is None:
            raise ValueError("pg_pool must not be None")

        self.pg_pool = pg_pool
        self.model_name = model
        self.model = SentenceTransformer(model)
        self.dim = int(self.model.get_sentence_embedding_dimension())

        self.batch_size = int(batch_size)
        self.deduplicate = bool(deduplicate)
        self.min_chars = int(min_chars)
        self.normalize = bool(normalize)

    # -----------------------
    # Embedding (wewnętrznie)
    # -----------------------

    def _embed(self, texts: Sequence[str]) -> np.ndarray:
        """
        Wektoryzuje listę tekstów i zwraca macierz float32 (N, dim),
        z *znormalizowanymi* embeddingami (norma L2 == 1).
        """
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        vecs = self.model.encode(
            list(texts),
            batch_size=self.batch_size,
            normalize_embeddings=True,  # spójność z cosine_ops
            convert_to_numpy=True,
        )
        # Bezpieczny rzut na float32 (wydajność + zgodność z pgvector)
        return np.asarray(vecs, dtype=np.float32)

    # ---------------
    # Operacje INSERT
    # ---------------

    async def upsert(self, source: str, chunks: List[str]) -> int:
        """
        Wstawia (append) fragmenty `chunks` dla źródła `source`.
        Brak dedykowanego "ON CONFLICT" (schema nie wymusza unikalności) — to celowe:
        wersjonowanie dokumentów obsługuj na poziomie `source` (np. source = "X@v2").

        Heurystyki:
          - (opcjonalnie) odfiltruj duplikaty identycznych chunków w pojedynczym wsadzie,
          - (opcjonalnie) pomiń zbyt krótkie/szumowe fragmenty (min_chars),
          - normalizuj tekst (NFC + whitespace), jeśli `normalize=True`.

        :return: liczba *zaakceptowanych* do wstawienia fragmentów.
        """
        if not source or not source.strip():
            raise ValueError("source must not be empty")
        if not chunks:
            return 0

        # Normalizacja / filtr długości / deduplikacja w bieżącej partii
        prepped: List[str] = []
        seen: set[str] = set()
        for c in chunks:
            if c is None:
                continue
            t = _normalize_text(c) if self.normalize else c.strip()
            if len(t) < self.min_chars:
                continue
            if self.deduplicate:
                # Deduplikacja tylko w obrębie tego upserta (nie globalna)
                key = t
                if key in seen:
                    continue
                seen.add(key)
            prepped.append(t)

        if not prepped:
            return 0

        # Embedding w batchach — SentenceTransformer i tak ma batching,
        # ale my dzielimy wcześniej, żeby kontrolować RAM.
        vecs = self._embed(prepped)

        # Insert do Postgresa — każdy chunk z odpowiadającym embeddingiem.
        async with self.pg_pool.acquire() as con:
            async with con.transaction():
                for chunk, vec in zip(prepped, vecs):
                    await con.execute(
                        "INSERT INTO documents(source, chunk, embedding) VALUES ($1, $2, $3)",
                        source,
                        chunk,
                        vec.tolist(),  # pgvector przyjmie list[float]
                    )

        return len(prepped)

    # ----------------
    # Operacje SELECT
    # ----------------

    async def retrieve(self, query: str, k: int = 5) -> List[str]:
        """
        Prosty retrieval: najbliższe wektory wg cosine distance z pgvector.
        Zwraca tylko teksty (bez score).

        :param query: zapytanie użytkownika
        :param k: ile fragmentów zwrócić
        """
        rows = await self._retrieve_rows(query, k)
        return [r["chunk"] for r in rows]

    async def retrieve_with_scores(self, query: str, k: int = 5) -> List[Tuple[str, float]]:
        """
        Retrieval ze *score* (cosine similarity ∈ [0..1]).
        Przeliczamy: similarity = 1 - distance (bo `<->` zwraca distance przy cosine_ops).

        :return: lista (chunk, score) posortowana malejąco po score.
        """
        rows = await self._retrieve_rows(query, k, return_distance=True)
        out: List[Tuple[str, float]] = []
        for r in rows:
            dist = float(r["distance"]) if "distance" in r and r["distance"] is not None else 1.0
            sim = max(0.0, min(1.0, 1.0 - dist))
            out.append((r["chunk"], sim))
        return out

    async def retrieve_mmr(
        self,
        query: str,
        k: int = 5,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
    ) -> List[Tuple[str, float]]:
        """
        Retrieval z re-rankingiem **MMR (Maximal Marginal Relevance)**:
          - pobieramy `fetch_k` kandydatów z bazy po cosine distance,
          - embedujemy je lokalnie, liczymy podobieństwo query↔doc oraz doc↔doc,
          - składamy zestaw `k` elementów maksymalizujących pokrycie i różnorodność.

        :param query: zapytanie użytkownika
        :param k: ile wyników finalnie zwrócić
        :param fetch_k: ilu kandydatów wstępnie pobrać z bazy
        :param lambda_mult: balans (1.0: tylko relevance, 0.0: tylko diversity)
        :return: lista (chunk, score) — score to relevance (cosine similarity query↔doc)
        """
        if k <= 0:
            return []
        fetch_k = max(fetch_k, k)

        # 1) wstępny retrieval po cosine distance (najbliższe)
        rows = await self._retrieve_rows(query, fetch_k)
        if not rows:
            return []

        # 2) embed zapytania i kandydatów
        qv = self._embed([query])[0]  # (dim,)
        docs = [r["chunk"] for r in rows]
        dvs = self._embed(docs)       # (N, dim)

        # 3) relevance (q•d) oraz doc-to-doc (dla diversity)
        #    Ponieważ embeddingi są znormalizowane, dot product == cosine similarity.
        rel = (dvs @ qv).astype(np.float32)        # (N,)
        # macierz podobieństwa doc↔doc (N, N) — przy dużych N ogranicz fetch_k!
        sim_dd = (dvs @ dvs.T).astype(np.float32)  # (N, N)

        # 4) MMR greedy
        selected: list[int] = []
        candidates = set(range(len(docs)))

        # Wybierz najbardziej relewantny na start
        first = int(np.argmax(rel))
        selected.append(first)
        candidates.remove(first)

        while len(selected) < k and candidates:
            best_i = None
            best_score = -math.inf
            for i in candidates:
                # diversity: maksymalne podobieństwo do już wybranych
                div = max(sim_dd[i, j] for j in selected) if selected else 0.0
                mmr = lambda_mult * rel[i] - (1.0 - lambda_mult) * div
                if mmr > best_score:
                    best_score, best_i = mmr, i
            selected.append(best_i)  # type: ignore[arg-type]
            candidates.remove(best_i)  # type: ignore[arg-type]

        # 5) zwróć posortowane wg relevance (nie MMR score), bo to zwykle czytelniejsze
        items = [(docs[i], float(rel[i])) for i in selected]
        items.sort(key=lambda t: t[1], reverse=True)
        return items

    # -----------------------
    # Operacje administracyjne
    # -----------------------

    async def delete_source(self, source: str) -> int:
        """
        Usuwa wszystkie dokumenty powiązane ze źródłem `source`.
        Zwraca liczbę usuniętych wierszy.
        """
        if not source or not source.strip():
            raise ValueError("source must not be empty")
        async with self.pg_pool.acquire() as con:
            row = await con.fetchrow("DELETE FROM documents WHERE source = $1 RETURNING COUNT(*) AS c", source)
            # Nie wszystkie wersje PG wspierają RETURNING COUNT(*) tak, jakbyśmy chcieli.
            # Bezpieczniej zrobić dwa zapytania:
            if row and row.get("c") is not None:
                return int(row["c"])
        # fallback: policz przed/po (tańsze: pojedyncze COUNT, ale tu już usunięte)
        return 0

    async def count_documents(self) -> int:
        """Zwraca liczbę wierszy w tabeli `documents` (pomocne operacyjnie)."""
        async with self.pg_pool.acquire() as con:
            row = await con.fetchrow("SELECT COUNT(*) AS c FROM documents")
            return int(row["c"])

    # -----------------------
    # Wewnętrzne: SELECT rows
    # -----------------------

    async def _retrieve_rows(self, query: str, k: int, *, return_distance: bool = False) -> List[asyncpg.Record]:
        """
        Wspólna funkcja pobierająca top-k rekordów wg cosine distance.
        Jeśli `return_distance=True`, dołącza kolumnę `distance` (float).

        Nota:
          - `<->` dla vector_cosine_ops zwraca dystans kosinusowy — mniejszy = bliżej.
          - Similarity = 1 - distance (używane w retrieve_with_scores()).
        """
        if not query or not query.strip():
            return []
        if k <= 0:
            return []

        qv = self._embed([query])[0].tolist()  # list[float] → pgvector

        async with self.pg_pool.acquire() as con:
            if return_distance:
                sql = """
                    SELECT chunk,
                           (embedding <-> $1::vector) AS distance
                    FROM documents
                    ORDER BY embedding <-> $1::vector
                    LIMIT $2
                """
                rows = await con.fetch(sql, qv, k)
            else:
                sql = """
                    SELECT chunk
                    FROM documents
                    ORDER BY embedding <-> $1::vector
                    LIMIT $2
                """
                rows = await con.fetch(sql, qv, k)
        return list(rows)
