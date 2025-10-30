# SPDX-License-Identifier: Apache-2.0
"""File: services/api-gateway/src/runtime/rag.py

Retrieval-Augmented Generation (RAG) system for AstraDesk.

Provides hybrid search (keyword BM25 via Redis + semantic embeddings via PGVector)
with PyTorch 2.9 acceleration, governance via OPA, and optional self-reflection
for snippet quality. Supports vector DB (PGVector on PostgreSQL 18+) and keyword
index (Redis 8+).

Attributes:
  Author: Siergej Sobolewski
  Since: 2025-10-25

Environment Variables:
  pg_dsn: PG_DSN "PGVector DSN"
  redis_url: REDIS_URL
  redis_key: "rag_corpus"  Key for stored tokenized corpus
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional, Protocol

import asyncpg  # Async PostgreSQL client for PGVector
import redis.asyncio as redis  # Async Redis for BM25 corpus storage
import torch  # PyTorch 2.9 for embeddings and torch.compile
from opa_client.opa import OpaClient  # OPA for governance
from opentelemetry import trace  # AstraOps/OTel tracing
from pydantic import BaseModel, ValidationError  # Pydantic v2.9+ for models
from rank_bm25 import BM25Okapi  # For keyword search
from sentence_transformers import SentenceTransformer  # Semantic embeddings


logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# LLM Planner Protocol (for reflection) – avoids tight coupling to concrete impl
# --------------------------------------------------------------------------- #
class LLMPlannerProtocol(Protocol):
    """Protocol defining the minimal interface required for reflection."""

    async def chat(
        self,
        messages: List[Dict[str, str]],
        params: Optional[Dict[str, Any]] = None,
    ) -> str:  # pragma: no cover
        """Send a chat completion request and return raw response string."""
        ...


# --------------------------------------------------------------------------- #
# Configuration & Data Models
# --------------------------------------------------------------------------- #
class RAGConfig(BaseModel):
    """Configuration model for the RAG system."""

    model_name: str = "all-MiniLM-L6-v2"
    k: int = 5
    semantic_weight: float = 0.7
    keyword_weight: float = 0.3
    reflection_threshold: float = 0.7
    use_fp16: bool = True
    pg_dsn: str = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_key: str = "rag_corpus"

    def model_post_init(self, __context: Any) -> None:
        """Validate config post-init."""
        if abs(self.semantic_weight + self.keyword_weight - 1.0) > 1e-6:
            raise ValidationError("Semantic and keyword weights must sum to 1.0")


class RAGSnippet(BaseModel):
    """Model for a single retrieved snippet with metadata."""

    content: str
    score: float
    source: str
    agent_name: Optional[str] = None


# --------------------------------------------------------------------------- #
# RAG Core
# --------------------------------------------------------------------------- #
class RAG:
    """Retrieval-Augmented Generation system with PyTorch enhancements and governance.

    Features:
    - Hybrid search: BM25 (keyword via Redis) + cosine similarity (semantic via PGVector).
    - PyTorch 2.9: torch.compile for model acceleration, fp16 mixed precision.
    - Governance: OPA policy check before retrieval (e.g., RBAC on query/agent).
    - Self-reflection: Optional LLM-based scoring for snippet relevance.
    - OTel tracing: Spans for retrieve, embed, reflect.
    - Async-native: Suitable for FastAPI integration. Use `await rag.ainit()` after instantiation.
    - Ingestion: Methods to add documents to both indexes.
    """

    def __init__(
        self,
        config: Optional[RAGConfig] = None,
        opa_client: Optional[OpaClient] = None,
        llm_planner: Optional[LLMPlannerProtocol] = None,
    ) -> None:
        """Initialize the RAG system (sync). Call `await self.ainit()` for async setup.

        Args:
            config: Optional configuration (defaults to RAGConfig()).
            opa_client: OPA client for policy enforcement.
            llm_planner: Optional LLM planner for self-reflection scoring.
        """
        self.config = config or RAGConfig()
        self.opa_client = opa_client
        self.llm_planner = llm_planner
        self.tracer = trace.get_tracer(__name__)  # OTel tracer
        self.embedding_cache = {}

        # PyTorch model setup
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = SentenceTransformer(self.config.model_name)
        if self.config.use_fp16 and self.device.type == "cuda":
            self.model.half()  # fp16 mixed precision on GPU

        # This is Compiling PyTorch 2.9 - DISABLED for Python 3.14+ compatibility, 
        # uncomment `https://github.com/pytorch/pytorch/issues/1568566` will be closed:
        # self.model = torch.compile(
        #     self.model, mode="reduce-overhead", fullgraph=True
        # )  

        self.model.to(self.device)
        self.model.eval()  # Inference mode

        # Connections (initialized in ainit)
        self.pg_pool: Optional[asyncpg.Pool] = None
        self.redis_client: Optional[redis.Redis] = None
        self.bm25: Optional[BM25Okapi] = None
        self.keyword_index: List[str] = []  # Full documents in order

    async def ainit(self) -> None:
        """Async initialization for connections and loading BM25 index."""
        await self._init_connections()
        await self._load_bm25_from_redis()

    # ----------------------------------------------------------------------- #
    # Connection & Index Management
    # ----------------------------------------------------------------------- #
    async def _init_connections(self) -> None:
        """Initialize async connections to PGVector and Redis Cloud."""
        try:
            logger.info("🔄 Initializing database connections...")
            
            # ✅ Uproszczona konfiguracja - tak jak w teście
            self.pg_pool = await asyncpg.create_pool(self.config.pg_dsn)
            logger.info("✅ PostgreSQL pool created")
            
            # Test connection
            async with self.pg_pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                logger.info(f"✅ PostgreSQL test query: {result}")
            
            # Redis
            self.redis_client = redis.from_url(
                self.config.redis_url,
                decode_responses=True,
                socket_connect_timeout=5
            )
            await self.redis_client.ping()
            logger.info("✅ Redis connection successful")
            
        except Exception as e:
            logger.error(f"❌ Connection initialization failed: {e}")
            # ✅ Dodaj więcej informacji diagnostycznych
            logger.error(f"PostgreSQL DSN: {self.config.pg_dsn[:50]}...")
            logger.error(f"Redis URL: {self.config.redis_url[:50]}...")
            raise RuntimeError(f"Failed to initialize connections: {e}") from e


    async def _load_bm25_from_redis(self) -> None:
        """Load BM25 index from Redis if available."""
        if not self.redis_client:
            return
        try:
            tokenized_corpus_json = await self.redis_client.get(self.config.redis_key)
            if tokenized_corpus_json:
                tokenized_corpus = json.loads(tokenized_corpus_json)
                self.bm25 = BM25Okapi(tokenized_corpus)
                # Note: We need full contents; assume separate key for full docs or ingest properly
                # For now, load full docs from another key if exists
                full_docs_json = await self.redis_client.get(self.config.redis_key + "_full")
                if full_docs_json:
                    self.keyword_index = json.loads(full_docs_json)
        except Exception as e:
            logger.warning(f"Failed to load BM25 from Redis: {e}")

    async def _build_bm25_index(self, corpus: List[str]) -> None:
        """Build BM25 index from corpus and store tokenized/full docs in Redis."""
        if not self.redis_client:
            raise RuntimeError("Redis client not initialized")
        tokenized_corpus = [doc.split() for doc in corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)
        self.keyword_index = corpus  # Keep full docs in memory
        # Store in Redis
        await self.redis_client.set(
            self.config.redis_key, json.dumps(tokenized_corpus)
        )
        await self.redis_client.set(
            self.config.redis_key + "_full", json.dumps(corpus)
        )

    # ----------------------------------------------------------------------- #
    # Ingestion Methods
    # ----------------------------------------------------------------------- #
    async def ingest_documents(
        self, documents: List[str], sources: Optional[List[str]] = None
    ) -> None:
        """Ingest documents into both BM25 (Redis) and PGVector.

        Args:
            documents: List of document contents.
            sources: Optional list of sources (same length as documents).
        
        """
        
        if not sources:
            sources = ["unknown"] * len(documents)
        if len(documents) != len(sources):
            raise ValueError("Documents and sources must have same length")

        with self.tracer.start_as_current_span("rag.ingest") as span:
            span.set_attribute("num_docs", len(documents))

            # BM25: Append to existing or build new
            await self._build_bm25_index(self.keyword_index + documents)

            # PGVector: Embed and insert with batch optimization
            if self.pg_pool:
                try:
                    with torch.no_grad():
                        # Batch processing dla lepszej wydajności
                        embeddings = self.model.encode(
                            documents, 
                            convert_to_tensor=True, 
                            device=self.device,
                            batch_size=32,  # Optymalny batch size
                            show_progress_bar=False
                        ).cpu().tolist()
                        
                    async with self.pg_pool.acquire() as conn:
                        async with conn.transaction():
                            for doc, src, emb in zip(documents, sources, embeddings):
                                await conn.execute(
                                    """
                                    INSERT INTO docs (content, source, embedding)
                                    VALUES ($1, $2, $3::vector)
                                    ON CONFLICT (content) DO NOTHING
                                    """,
                                    doc,
                                    src,
                                    emb,
                                )
                    logger.info(f"Ingested {len(documents)} documents to PGVector")
                    
                except Exception as e:
                    logger.error(f"PGVector ingest failed: {e}")
                    raise RuntimeError("Ingestion failed") from e

    # ----------------------------------------------------------------------- #
    # Public Retrieval API
    # ----------------------------------------------------------------------- #
    async def retrieve(
        self,
        query: str,
        agent_name: str,
        k: Optional[int] = None,
        use_reflection: bool = True,
    ) -> List[RAGSnippet]:
        """Perform hybrid RAG retrieval with PyTorch embeddings, OPA governance, and optional self-reflection.

        Workflow:
        1. OPA policy check (e.g., allow query for agent).
        2. Compute query embedding with PyTorch.
        3. Hybrid search: BM25 (keyword from Redis) + cosine sim (semantic from PGVector).
        4. Rank and select top-k with normalized hybrid scores.
        5. Optional: Self-reflect on each snippet via LLM.

        Args:
            query: User query.
            agent_name: Agent requesting the retrieval (for OPA).
            k: Number of results (overrides config).
            use_reflection: Whether to apply self-reflection filtering.

        Returns:
            List of ranked RAGSnippet objects.

        Raises:
            PermissionError: If OPA denies the query.
            RuntimeError: On embedding or DB/Redis errors.
        """

        # Cache dla embeddingów zapytania
        cache_key = f"embedding:{hash(query)}"
        if cache_key in self.embedding_cache:
            query_embedding = self.embedding_cache[cache_key]
        else:
            with torch.no_grad():
                query_embedding = self.model.encode(
                    query, convert_to_tensor=True, device=self.device
                ).cpu().tolist()
            self.embedding_cache[cache_key] = query_embedding
            # Limit cache size
            if len(self.embedding_cache) > 1000:
                self.embedding_cache.pop(next(iter(self.embedding_cache)))

        k = k or self.config.k

        with self.tracer.start_as_current_span("rag.retrieve") as span:
            span.set_attribute("query", query)
            span.set_attribute("agent_name", agent_name)
            span.set_attribute("k", k)
            span.set_attribute("use_reflection", use_reflection)

            try:
                # Step 1: OPA governance check
                if self.opa_client:
                    with self.tracer.start_as_current_span("opa.check"):
                        decision = await self.opa_client.check_policy(
                            input={"query": query, "agent": agent_name},
                            policy_path="astradesk/rag_access",
                        )
                        if not decision.get("result", False):
                            raise PermissionError("Access denied by policy")

                # Step 2: PyTorch embedding computation
                with self.tracer.start_as_current_span("embed_query"):
                    with torch.no_grad():
                        query_embedding = (
                            self.model.encode(
                                query, convert_to_tensor=True, device=self.device
                            )
                            .cpu()
                            .tolist()
                        )

                # Step 3: Hybrid search
                bm25_candidates: List[RAGSnippet] = []
                sem_candidates: List[RAGSnippet] = []
                with self.tracer.start_as_current_span("hybrid_search"):
                    # --- Keyword: BM25 ---
                    if self.bm25 and self.keyword_index:
                        tokenized_query = query.split()
                        bm25_scores = self.bm25.get_scores(tokenized_query)
                        # Normalize BM25 scores (min-max)
                        if bm25_scores:
                            min_score = min(bm25_scores)
                            max_score = max(bm25_scores)
                            if max_score > min_score:
                                bm25_scores = [
                                    (s - min_score) / (max_score - min_score)
                                    for s in bm25_scores
                                ]
                        top_keyword_idxs = sorted(
                            range(len(bm25_scores)),
                            key=lambda i: bm25_scores[i],
                            reverse=True,
                        )[: k * 2]
                        for idx in top_keyword_idxs:
                            if idx < len(self.keyword_index):
                                bm25_candidates.append(
                                    RAGSnippet(
                                        content=self.keyword_index[idx],
                                        score=bm25_scores[idx],
                                        source="bm25",
                                        agent_name=agent_name,
                                    )
                                )

                    # --- Semantic: Cosine sim from PGVector ---
                    if self.pg_pool:
                        async with self.pg_pool.acquire() as conn:
                            db_results = await conn.fetch(
                                """
                                SELECT content, source, embedding <=> $1::vector AS dist
                                FROM docs
                                ORDER BY dist ASC
                                LIMIT $2
                                """,
                                query_embedding,
                                k * 2,
                            )
                        for row in db_results:
                            sem_candidates.append(
                                RAGSnippet(
                                    content=row["content"],
                                    score=1 - row["dist"],  # Already normalized [0,1]
                                    source=row["source"],
                                    agent_name=agent_name,
                                )
                            )

                    # --- Hybrid rank: Merge by content, weighted sum ---
                    from collections import defaultdict

                    scores_by_content: Dict[str, Dict[str, float]] = defaultdict(dict)
                    for cand in bm25_candidates:
                        scores_by_content[cand.content]["bm25"] = cand.score
                    for cand in sem_candidates:
                        scores_by_content[cand.content]["semantic"] = cand.score
                        scores_by_content[cand.content]["source"] = cand.source  # Keep semantic source if available

                    weighted: List[RAGSnippet] = []
                    for content, scores in scores_by_content.items():
                        bm25_score = scores.get("bm25", 0.0)
                        sem_score = scores.get("semantic", 0.0)
                        hybrid_score = (
                            bm25_score * self.config.keyword_weight
                            + sem_score * self.config.semantic_weight
                        )
                        weighted.append(
                            RAGSnippet(
                                content=content,
                                score=hybrid_score,
                                source=scores.get("source", "hybrid"),
                                agent_name=agent_name,
                            )
                        )

                    # Sort and top-k
                    weighted.sort(key=lambda x: x.score, reverse=True)
                    top_candidates = weighted[:k]

                # Step 4-5: Self-reflection if enabled
                if use_reflection and self.llm_planner:
                    filtered: List[RAGSnippet] = []
                    for cand in top_candidates:
                        with self.tracer.start_as_current_span("reflect_snippet"):
                            score = await self._reflect_snippet(query, cand.content)
                            if score >= self.config.reflection_threshold:
                                cand.score = score  # Update with reflection score
                                filtered.append(cand)
                    top_candidates = filtered or top_candidates  # Fallback if all filtered

                span.set_attribute("final_count", len(top_candidates))
                return top_candidates

            except PermissionError:
                raise
            except Exception as e:
                logger.error(f"Retrieval failed: {e}")
                raise RuntimeError("Retrieval error") from e

    # ----------------------------------------------------------------------- #
    # Self-Reflection (LLM-based)
    # ----------------------------------------------------------------------- #
    async def _reflect_snippet(self, query: str, content: str) -> float:
        """LLM-based reflection to score snippet relevance.

        Args:
            query: User query.
            content: Snippet content.

        Returns:
            Relevance score (0.0-1.0).
        """
        system = (
            "Evaluate relevance: Return JSON {'score': float(0.0-1.0)}. "
            "No explanations."
        )
        user = f"Query: {query}\nContent: {content}"

        try:
            raw = await self.llm_planner.chat(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                params={"max_tokens": 50, "temperature": 0.0},
            )
            # More robust parsing
            raw = raw.strip()
            if raw.startswith("{") and raw.endswith("}"):
                data = json.loads(raw)
                return max(0.0, min(1.0, float(data.get("score", 0.5))))
            else:
                raise ValueError("Invalid JSON response")
        except Exception as e:  # pragma: no cover
            logger.warning(f"Reflection failed: {e}")
            return 0.5  # Default medium confidence
        