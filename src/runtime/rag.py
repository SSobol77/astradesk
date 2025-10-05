# src/runtime/rag.py
# -*- coding: utf-8 -*-
# Program jest objęty licencją Apache-2.0.
# Copyright 2025
# Autor: Siergej Sobolewski
"""Implementacja warstwy RAG (Retrieval-Augmented Generation).

Moduł ten dostarcza kompletną, gotową do użytku produkcyjnego warstwę RAG
dla aplikacji AstraDesk. Odpowiada za wektoryzację fragmentów tekstu,
przechowywanie ich w bazie danych PostgreSQL z rozszerzeniem pgvector oraz
zaawansowane mechanizmy wyszukiwania semantycznego.

Główne funkcjonalności:
- Wektoryzacja tekstu przy użyciu modeli z biblioteki SentenceTransformer.
- Przechowywanie wektorów i metadanych w PostgreSQL.
- Wiele strategii wyszukiwania:
  - Proste wyszukiwanie najbliższych sąsiadów (k-NN).
  - Wyszukiwanie z wynikami podobieństwa (cosine similarity).
  - Zaawansowane re-rankowanie za pomocą algorytmu MMR (Maximal Marginal Relevance)
    w celu zapewnienia trafności i różnorodności wyników.
- Operacje administracyjne, takie jak usuwanie dokumentów i zliczanie.

Założenia projektowe:
- Wykorzystanie `asyncpg` do w pełni asynchronicznej komunikacji z bazą danych.
- Operacje na wektorach bazują na odległości kosinusowej w pgvector,
  a metryka podobieństwa jest odpowiednio przeliczana (similarity = 1 - distance).
- Moduł jest niezależny od logiki generowania odpowiedzi przez LLM; jego
  jedynym zadaniem jest dostarczenie relewantnego kontekstu.
"""

from __future__ import annotations

import logging
import math
import unicodedata
from typing import Any, Iterable, List, Optional, Sequence, Tuple

import asyncpg
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# -----------------------------
# Pomocnicze funkcje narzędziowe
# -----------------------------

def _normalize_text(s: str) -> str:
    """Delikatna normalizacja treści.

    Wykonuje następujące operacje:
      - Normalizacja Unicode do formy NFC.
      - Usunięcie skrajnych białych znaków i zwinięcie wielokrotnych
        białych znaków do pojedynczych spacji.

    Args:
        s: Ciąg znaków do normalizacji.

    Returns:
        Znormalizowany ciąg znaków.
    """
    s = unicodedata.normalize("NFC", s)
    s = s.strip()
    return " ".join(s.split())


def _batched(seq: Sequence[Any], size: int) -> Iterable[Sequence[Any]]:
    """Dzieli sekwencję na części o maksymalnym rozmiarze `size`."""
    if size <= 0:
        raise ValueError("Rozmiar paczki musi być większy od 0")
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


# ---------------------------------
# Główna klasa: RAG (embed + search)
# ---------------------------------

class RAG:
    """Zarządza cyklem życia dokumentów w systemie RAG.

    Klasa enkapsuluje logikę wektoryzacji tekstu, przechowywania
    w bazie danych pgvector oraz wyszukiwania semantycznego.
    """

    __slots__ = (
        "pg_pool",
        "model_name",
        "model",
        "dim",
        "batch_size",
        "deduplicate",
        "min_chars",
        "normalize",
    )

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
        """Inicjalizuje instancję RAG.

        Konstruktor konfiguruje połączenie z bazą danych, ładuje model
        do tworzenia embeddingów oraz ustawia parametry potoku przetwarzania
        tekstu.

        Args:
            pg_pool: Współdzielona, asynchroniczna pula połączeń do bazy
                danych PostgreSQL z rozszerzeniem pgvector.
            model: Nazwa modelu z biblioteki SentenceTransformer, który
                zostanie użyty do wektoryzacji tekstu.
            batch_size: Rozmiar paczki (batch) używany podczas kodowania
                dokumentów. Pomaga kontrolować zużycie pamięci/VRAM.
            deduplicate: Jeśli True, identyczne fragmenty tekstu w ramach
                jednego wywołania `upsert` zostaną usunięte.
            min_chars: Minimalna liczba znaków, aby fragment tekstu został
                uznany za wartościowy i przetworzony. Pomaga filtrować szum.
            normalize: Jeśli True, tekst zostanie poddany normalizacji
                (NFC, zwinięcie białych znaków) przed wektoryzacją.

        Raises:
            ValueError: Jeśli `pg_pool` nie zostanie dostarczony (jest None).
        """
        if pg_pool is None:
            raise ValueError("pg_pool must not be None")

        self.pg_pool = pg_pool
        self.model_name = model
        self.model = SentenceTransformer(model)
        self.dim = self.model.get_sentence_embedding_dimension()

        self.batch_size = batch_size
        self.deduplicate = deduplicate
        self.min_chars = min_chars
        self.normalize = normalize

    def _embed(self, texts: Sequence[str]) -> np.ndarray:
        """Wektoryzuje listę tekstów.

        Zwraca macierz float32 (N, dim) ze znormalizowanymi embeddingami
        (o normie L2 równej 1), co jest kluczowe dla metryki kosinusowej.

        Args:
            texts: Sekwencja tekstów do wektoryzacji.

        Returns:
            Macierz NumPy z embeddingami.
        """
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)

        vecs = self.model.encode(
            list(texts),
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return np.asarray(vecs, dtype=np.float32)

    async def upsert(self, source: str, chunks: List[str]) -> int:
        """Przetwarza i wstawia fragmenty tekstu (chunks) do bazy danych.

        Proces obejmuje opcjonalną normalizację, deduplikację, filtrowanie,
        a następnie wektoryzację i zapis do bazy w ramach jednej transakcji.
        Operacja jest krytyczna - jej niepowodzenie rzuci wyjątek.

        Args:
            source: Identyfikator źródła dokumentów (np. nazwa pliku).
            chunks: Lista fragmentów tekstu do przetworzenia.

        Returns:
            Liczba fragmentów, które zostały pomyślnie wstawione do bazy.
            
        Raises:
            asyncpg.PostgresError: W przypadku błędu komunikacji z bazą danych.
        """
        if not source or not source.strip():
            raise ValueError("source must not be empty")
        if not chunks:
            return 0

        prepped: List[str] = []
        seen: set[str] = set()
        for c in chunks:
            if c is None:
                continue
            t = _normalize_text(c) if self.normalize else c.strip()
            if len(t) < self.min_chars:
                continue
            if self.deduplicate and t in seen:
                continue
            seen.add(t)
            prepped.append(t)

        if not prepped:
            return 0

        vecs = self._embed(prepped)

        try:
            async with self.pg_pool.acquire() as con:
                async with con.transaction():
                    for chunk, vec in zip(prepped, vecs, strict=True):
                        await con.execute(
                            "INSERT INTO documents(source, chunk, embedding) VALUES ($1, $2, $3)",
                            source,
                            chunk,
                            vec.tolist(),
                        )
            return len(prepped)
        except (asyncpg.PostgresError, OSError) as e:
            logger.error(
                f"Nie udało się wstawić dokumentów dla źródła '{source}'. Błąd: {e}",
                exc_info=True,
            )
            raise

    async def retrieve(self, query: str, k: int = 5) -> List[str]:
        """Wyszukuje k najbliższych fragmentów tekstu dla danego zapytania.

        Args:
            query: Zapytanie użytkownika.
            k: Liczba fragmentów do zwrócenia.

        Returns:
            Lista k najbardziej pasujących fragmentów tekstu.
        """
        rows = await self._retrieve_rows(query, k)
        return [r["chunk"] for r in rows]

    async def retrieve_with_scores(
        self, query: str, k: int = 5
    ) -> List[Tuple[str, float]]:
        """Wyszukuje k najbliższych fragmentów wraz z wynikiem podobieństwa.

        Wynik podobieństwa (cosine similarity) jest w zakresie [0, 1],
        gdzie 1 oznacza identyczność.

        Args:
            query: Zapytanie użytkownika.
            k: Liczba fragmentów do zwrócenia.

        Returns:
            Lista par (fragment_tekstu, wynik_podobieństwa).
        """
        rows = await self._retrieve_rows(query, k, return_distance=True)
        out: List[Tuple[str, float]] = []
        for r in rows:
            dist = float(r.get("distance", 1.0) or 1.0)
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
        """Wyszukuje fragmenty z re-rankingiem MMR (Maximal Marginal Relevance).

        Algorytm ten balansuje między trafnością wyników (relevance) a ich
        różnorodnością (diversity), aby uniknąć zwracania wielu bardzo
        podobnych do siebie fragmentów.

        Args:
            query: Zapytanie użytkownika.
            k: Liczba wyników do zwrócenia po re-rankingu.
            fetch_k: Liczba kandydatów do pobrania z bazy przed re-rankingiem.
            lambda_mult: Współczynnik balansu (1.0 = tylko trafność, 0.0 = tylko różnorodność).

        Returns:
            Lista par (fragment_tekstu, wynik_trafności) posortowana malejąco.
        """
        if k <= 0:
            return []
        fetch_k = max(fetch_k, k)
        lambda_mult = max(0.0, min(1.0, lambda_mult))

        rows = await self._retrieve_rows(query, fetch_k)
        if not rows:
            return []

        docs = [r["chunk"] for r in rows]
        query_embedding = self._embed([query])[0]
        doc_embeddings = self._embed(docs)

        relevance_scores = (doc_embeddings @ query_embedding).astype(np.float32)
        doc_similarity_matrix = (doc_embeddings @ doc_embeddings.T).astype(np.float32)

        selected_indices: list[int] = []
        candidate_indices = set(range(len(docs)))

        first_idx = int(np.argmax(relevance_scores))
        selected_indices.append(first_idx)
        candidate_indices.remove(first_idx)

        while len(selected_indices) < k and candidate_indices:
            best_i: Optional[int] = None
            best_score = -math.inf

            for i in candidate_indices:
                relevance = relevance_scores[i]
                diversity = max(doc_similarity_matrix[i, j] for j in selected_indices)
                mmr_score = lambda_mult * relevance - (1.0 - lambda_mult) * diversity
                if mmr_score > best_score:
                    best_score, best_i = mmr_score, i

            assert best_i is not None, "Logika pętli MMR musi znaleźć kandydata"
            selected_indices.append(best_i)
            candidate_indices.remove(best_i)

        items = [(docs[i], float(relevance_scores[i])) for i in selected_indices]
        return sorted(items, key=lambda item: item[1], reverse=True)

    async def delete_source(self, source: str) -> int:
        """Usuwa wszystkie dokumenty powiązane z danym źródłem.

        Args:
            source: Identyfikator źródła do usunięcia.

        Returns:
            Liczba usuniętych dokumentów.
            
        Raises:
            asyncpg.PostgresError: W przypadku błędu komunikacji z bazą danych.
        """
        if not source or not source.strip():
            raise ValueError("source must not be empty")

        try:
            async with self.pg_pool.acquire() as con:
                status = await con.execute(
                    "DELETE FROM documents WHERE source = $1", source
                )
                return int(status.split()[1])
        except (IndexError, ValueError):
            return 0  # Fallback, jeśli format statusu jest nieoczekiwany
        except (asyncpg.PostgresError, OSError) as e:
            logger.error(
                f"Nie udało się usunąć dokumentów dla źródła '{source}'. Błąd: {e}",
                exc_info=True,
            )
            raise

    async def count_documents(self) -> int:
        """Zwraca całkowitą liczbę dokumentów w bazie."""
        try:
            async with self.pg_pool.acquire() as con:
                row = await con.fetchrow("SELECT COUNT(*) AS c FROM documents")
                return int(row["c"]) if row else 0
        except (asyncpg.PostgresError, OSError) as e:
            logger.error(f"Nie udało się policzyć dokumentów. Błąd: {e}", exc_info=True)
            return 0

    async def _retrieve_rows(
        self, query: str, k: int, *, return_distance: bool = False
    ) -> List[asyncpg.Record]:
        """Wewnętrzna metoda do pobierania surowych wierszy z bazy danych.

        Args:
            query: Zapytanie użytkownika.
            k: Liczba wierszy do pobrania.
            return_distance: Czy dołączyć kolumnę `distance` w wyniku.

        Returns:
            Lista rekordów `asyncpg.Record`, lub pusta lista w razie błędu.
        """
        if not query or not query.strip() or k <= 0:
            return []

        try:
            query_embedding = self._embed([query])[0].tolist()

            distance_sql = (
                ", (embedding <-> $1::vector) AS distance" if return_distance else ""
            )
            sql = f"""
                SELECT chunk{distance_sql}
                FROM documents
                ORDER BY embedding <-> $1::vector
                LIMIT $2
            """

            async with self.pg_pool.acquire() as con:
                rows = await con.fetch(sql, query_embedding, k)

            return list(rows)
        except (asyncpg.PostgresError, OSError) as e:
            logger.error(
                f"Nie udało się wyszukać dokumentów dla zapytania. Błąd: {e}",
                exc_info=True,
            )
            return []
        