# SPDX-License-Identifier: Apache-2.0
# services/api-gateway/src/tests/runtime/test_rag.py
"""Testy jednostkowe dla modułu src.runtime.rag (klasa RAG).

Zakres:
- Inicjalizacja RAG (model, parametry).
- Przetwarzanie fragmentów: normalizacja, filtrowanie, deduplikacja.
- Wektoryzacja tekstów (_embed).
- Operacje CRUD: upsert, retrieve, retrieve_with_scores, retrieve_mmr, delete_source, count_documents.
- Obsługa błędów i brzegowe przypadki (puste dane, błędy DB).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from src.runtime.rag import RAG, _batched, _normalize_text


# --- Pomocnicze funkcje ---

def test_normalize_text():
    """Testuje funkcję _normalize_text."""
    assert _normalize_text("  Hello\n  world  ") == "Hello world"
    assert _normalize_text("café") == "café"
    assert _normalize_text("") == ""
    assert _normalize_text(" \t\n ") == ""


def test_batched():
    """Testuje funkcję _batched."""
    assert list(_batched([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]
    assert list(_batched([], 2)) == []
    with pytest.raises(ValueError):
        list(_batched([1, 2], 0))


# --- Testy klasy RAG ---

@pytest.fixture
def mock_pg_pool():
    """Zwraca jeden, spójny mock dla asyncpg.Pool."""
    pool = AsyncMock()
    conn = AsyncMock()

    pool.acquire = AsyncMock(return_value=conn)
    pool.release = AsyncMock()

    trans_manager = AsyncMock()
    trans_manager.__aenter__ = AsyncMock(return_value=None)
    trans_manager.__aexit__ = AsyncMock(return_value=None)
    conn.transaction = MagicMock(return_value=trans_manager)

    pool._conn = conn
    return pool


@pytest.fixture
def mock_sentence_transformer():
    """Mockuje SentenceTransformer."""
    with patch("src.runtime.rag.SentenceTransformer") as mock:
        instance = mock.return_value
        instance.get_sentence_embedding_dimension.return_value = 384
        instance.encode.return_value = np.random.rand(2, 384).astype(np.float32)
        yield instance


@pytest.fixture
def rag_instance(mock_pg_pool, mock_sentence_transformer):
    """Zwraca instancję RAG z mockami."""
    return RAG(pg_pool=mock_pg_pool, model="fake-model", batch_size=16)


# --- Testy inicjalizacji ---

def test_rag_initialization_success(mock_pg_pool, mock_sentence_transformer):
    rag = RAG(pg_pool=mock_pg_pool, model="all-MiniLM-L6-v2", batch_size=32)
    assert rag.model_name == "all-MiniLM-L6-v2"
    assert rag.batch_size == 32
    assert rag.dim == 384


def test_rag_initialization_fails_without_pool():
    with pytest.raises(ValueError, match="pg_pool must not be None"):
        RAG(pg_pool=None)


def test_rag_initialization_fails_without_dimension(mock_pg_pool):
    with patch("src.runtime.rag.SentenceTransformer") as mock:
        instance = mock.return_value
        instance.get_sentence_embedding_dimension.return_value = None
        with pytest.raises(ValueError, match="Nie udało się określić wymiaru"):
            RAG(pg_pool=mock_pg_pool, model="fake-model")


# --- Testy _prepare_chunks ---

def test_prepare_chunks_full_logic(rag_instance):
    chunks = ["  Hello world  ", "Hello world", None, "  ", "Short", "Another valid chunk here."]
    rag_instance.min_chars = 6
    result = rag_instance._prepare_chunks(chunks)
    assert set(result) == {"Hello world", "Another valid chunk here."}


def test_prepare_chunks_no_deduplication(rag_instance):
    rag_instance.deduplicate = False
    rag_instance.min_chars = 1
    chunks = ["Test", "Test"]
    result = rag_instance._prepare_chunks(chunks)
    assert result == ["Test", "Test"]


def test_prepare_chunks_no_normalization(rag_instance):
    rag_instance.normalize = False
    rag_instance.min_chars = 1
    chunks = ["  Test chunk\r\n"]
    result = rag_instance._prepare_chunks(chunks)
    assert result == ["  Test chunk"]


# --- Testy _embed ---

def test_embed_empty_list(rag_instance):
    result = rag_instance._embed([])
    np.testing.assert_array_equal(result, np.zeros((0, 384), dtype=np.float32))


# --- Testy retrieve_rows ---

async def test_retrieve_rows_success(rag_instance, mock_pg_pool):
    rag_instance.model.encode.return_value = np.array([[0.1] * 384], dtype=np.float32)
    mock_record1 = {"chunk": "Found chunk"}
    mock_pg_pool._conn.fetch.return_value = [mock_record1]
    rows = await rag_instance._retrieve_rows("query", k=1)
    assert len(rows) == 1
    assert rows[0]["chunk"] == "Found chunk"


async def test_retrieve_rows_empty_query(rag_instance):
    rows = await rag_instance._retrieve_rows("   ", k=1)
    assert rows == []


# --- Testy retrieve ---

async def test_retrieve_success(rag_instance, mock_pg_pool):
    mock_record1 = {"chunk": "Retrieved chunk"}
    mock_pg_pool._conn.fetch.return_value = [mock_record1]
    result = await rag_instance.retrieve("query", k=1)
    assert result == ["Retrieved chunk"]


# --- Testy retrieve_with_scores ---

async def test_retrieve_with_scores_success(rag_instance, mock_pg_pool):
    mock_record1 = MagicMock()
    mock_record1.__getitem__.side_effect = {"chunk": "Chunk", "distance": 0.3}.__getitem__
    mock_record1.get.side_effect = {"chunk": "Chunk", "distance": 0.3}.get
    mock_pg_pool._conn.fetch.return_value = [mock_record1]
    result = await rag_instance.retrieve_with_scores("query", k=1)
    assert result == [("Chunk", 0.7)]


# --- Testy retrieve_mmr ---

async def test_retrieve_mmr_success(rag_instance, mock_pg_pool):
    def mock_encode(texts, **kwargs):
        if len(texts) == 1: return np.array([[0.5] * 384], dtype=np.float32)
        arr = np.random.rand(len(texts), 384).astype(np.float32)
        arr[0] = [0.5] * 384
        return arr
    rag_instance.model.encode.side_effect = mock_encode
    mock_pg_pool._conn.fetch.return_value = [{"chunk": "Chunk1"}, {"chunk": "Chunk2"}]
    result = await rag_instance.retrieve_mmr("query", k=2, fetch_k=5, lambda_mult=0.7)
    assert len(result) <= 2
    assert isinstance(result[0][0], str)


async def test_retrieve_mmr_empty_results(rag_instance, mock_pg_pool):
    mock_pg_pool._conn.fetch.return_value = []
    result = await rag_instance.retrieve_mmr("query", k=2)
    assert result == []


async def test_retrieve_mmr_k_is_zero(rag_instance):
    result = await rag_instance.retrieve_mmr("query", k=0)
    assert result == []


# --- Testy upsert ---

async def test_upsert_success(rag_instance, mock_pg_pool):
    source = "test_source"
    chunks = ["This is chunk number one", "This is chunk number two"]
    rag_instance.model.encode.return_value = np.random.rand(2, 384).astype(np.float32)
    result = await rag_instance.upsert(source, chunks)
    assert mock_pg_pool._conn.execute.call_count == 2
    assert result == 2


async def test_upsert_db_error(rag_instance, mock_pg_pool, caplog):
    from asyncpg import PostgresError
    source = "test_source"
    chunks = ["This is a test chunk for error"]
    rag_instance.model.encode.return_value = np.random.rand(1, 384).astype(np.float32)
    mock_pg_pool._conn.execute.side_effect = PostgresError("DB error")
    with pytest.raises(PostgresError):
        await rag_instance.upsert(source, chunks)
    assert "Nie udało się wstawić dokumentów" in caplog.text


async def test_upsert_empty_and_filtered_chunks(rag_instance):
    assert await rag_instance.upsert("source", []) == 0
    rag_instance.min_chars = 100
    assert await rag_instance.upsert("source", ["short"]) == 0


async def test_upsert_invalid_source(rag_instance):
    with pytest.raises(ValueError, match="source must not be empty"):
        await rag_instance.upsert("  ", ["chunk"])


# --- Testy delete_source ---

async def test_delete_source_success(rag_instance, mock_pg_pool):
    mock_pg_pool._conn.execute.return_value = "DELETE 3"
    result = await rag_instance.delete_source("source1")
    assert result == 3


async def test_delete_source_db_error(rag_instance, mock_pg_pool, caplog):
    from asyncpg import PostgresError
    mock_pg_pool._conn.execute.side_effect = PostgresError("DB error")
    with pytest.raises(PostgresError):
        await rag_instance.delete_source("source1")
    assert "Nie udało się usunąć dokumentów" in caplog.text


async def test_delete_source_invalid_source(rag_instance):
    with pytest.raises(ValueError, match="source must not be empty"):
        await rag_instance.delete_source("")


async def test_delete_source_unparsable_status(rag_instance, mock_pg_pool):
    mock_pg_pool._conn.execute.return_value = "OK" # Nie da się sparsować
    result = await rag_instance.delete_source("source1")
    assert result == 0


# --- Testy count_documents ---

async def test_count_documents_success(rag_instance, mock_pg_pool):
    mock_pg_pool._conn.fetchrow.return_value = {"c": 42}
    result = await rag_instance.count_documents()
    assert result == 42


async def test_count_documents_db_error(rag_instance, mock_pg_pool, caplog):
    from asyncpg import PostgresError
    mock_pg_pool._conn.fetchrow.side_effect = PostgresError("DB error")
    result = await rag_instance.count_documents()
    assert result == 0
    assert "Nie udało się policzyć dokumentów" in caplog.text
