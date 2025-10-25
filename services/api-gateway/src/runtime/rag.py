# SPDX-License-Identifier: Apache-2.0
# services/api-gateway/src/runtime/rag.py
"""Retrieval-Augmented Generation (RAG) system for AstraDesk.

Provides hybrid search (keyword BM25 via Redis + semantic embeddings via PGVector)
with PyTorch 2.9 acceleration, governance via OPA, and optional self-reflection
for snippet quality. Supports vector DB (PGVector on PostgreSQL 18+) and keyword
index (Redis 8+).

Author: Siergej Sobolewski
Since: 2025-10-25
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional, Protocol

import asyncpg  # Async PostgreSQL client for PGVector
import redis.asyncio as redis  # Async Redis for BM25 corpus storage
import torch  # PyTorch 2.9 for embeddings and torch.compile
from opa_python_client import OPAClient  # OPA for governance
from opentelemetry import trace  # AstraOps/OTel tracing
from pydantic import BaseModel  # Pydantic v2.9+ for models
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

    model_name: str = "all-MiniLM-L6-v2"  # Default embedding model
    k: int = 5  # Top-k results
    semantic_weight: float = 0.7  # Weight for semantic score in hybrid
    keyword_weight: float = 0.3  # Weight for keyword score
    reflection_threshold: float = 0.7  # Min score for snippet acceptance
    use_fp16: bool = True  # Mixed precision for PyTorch perf
    pg_dsn: str = os.getenv(
        "PG_DSN", "postgresql://user:pass@localhost:5432/db"
    )  # PGVector DSN
    redis_url: str = os.getenv(
        "REDIS_URL", "redis://localhost:6379/0"
    )  # Redis URL
    redis_key: str = "rag_corpus"  # Key for stored tokenized corpus


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
    - Async-native: Suitable for FastAPI integration.
    """

    def __init__(
        self,
        config: Optional[RAGConfig] = None,
        opa_client: Optional[OPAClient] = None,
        llm_planner: Optional[LLMPlannerProtocol] = None,
        corpus: Optional[List[str]] = None,
    ) -> None:
        """Initialize the RAG system.

        Args:
            config: Optional configuration (defaults to RAGConfig()).
            opa_client: OPA client for policy enforcement.
            llm_planner: Optional LLM planner for self-reflection scoring.
            corpus: Optional initial list of documents for BM25 index (stored in Redis).
        """
        self.config = config or RAGConfig()
        self.opa_client = opa_client
        self.llm_planner = llm_planner
        self.tracer = trace.get_tracer(__name__)  # OTel tracer

        # PyTorch model setup
        self.model = SentenceTransformer(self.config.model_name)
        if self.config.use_fp16:
            self.model.half()  # fp16 mixed precision
        self.model = torch.compile(
            self.model, mode="reduce-overhead", fullgraph=True
        )  # PyTorch 2.9 compile
        self.model.eval()  # Inference mode

        # Connections
        self.pg_pool: Optional[asyncpg.Pool] = None
        self.redis_client: Optional[redis.Redis] = None
        self.bm25: Optional[BM25Okapi] = None

        # BM25 corpus storage (in-memory + Redis)
        self.keyword_index: List[str] = corpus or []  # Full documents in order
        self._init_connections()
        if corpus:
            self._build_bm25_index(corpus)

    # ----------------------------------------------------------------------- #
    # Connection & Index Management
    # ----------------------------------------------------------------------- #
    def _init_connections(self) -> None:
        """Initialize async connections to PGVector and Redis."""
        self.pg_pool = asyncpg.create_pool(
            self.config.pg_dsn, min_size=1, max_size=10
        )
        self.redis_client = redis.from_url(self.config.redis_url)

    def _build_bm25_index(self, corpus: List[str]) -> None:
        """Build BM25 index from corpus and store tokenized docs in Redis."""
        tokenized_corpus = [doc.split() for doc in corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)
        self.keyword_index = corpus  # Keep full docs in memory (same order)
        # Store tokenized corpus in Redis (JSON serialized)
        self.redis_client.set(
            self.config.redis_key, json.dumps(tokenized_corpus)
        )

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
        4. Rank and select top-k.
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
        k = k or self.config.k

        with self.tracer.start_as_current_span("rag.retrieve") as span:
            span.set_attribute("query", query)
            span.set_attribute("agent_name", agent_name)
            span.set_attribute("k", k)
            span.set_attribute("use_reflection", use_reflection)

            # Step 1: OPA governance check
            if self.opa_client:
                with self.tracer.start_as_current_span("opa.check"):
                    decision = await self.opa_client.check_policy(
                        input={"query": query, "agent": agent_name},
                        policy_path="astradesk/rag_access",
                    )
                    if not decision.get("result", False):
                        span.record_exception(
                            PermissionError("OPA denied RAG access")
                        )
                        raise PermissionError("Access denied by policy")

            # Step 2: PyTorch embedding computation
            with self.tracer.start_as_current_span("embed_query"):
                with torch.no_grad():
                    query_embedding = (
                        self.model.encode(
                            query, convert_to_tensor=True
                        )
                        .cpu()
                        .tolist()
                    )  # To list for DB query

            # Step 3: Hybrid search
            candidates: List[RAGSnippet] = []
            with self.tracer.start_as_current_span("hybrid_search"):
                # --- Keyword: BM25 from Redis ---
                if self.redis_client and self.bm25 is not None:
                    tokenized_corpus_json = await self.redis_client.get(
                        self.config.redis_key
                    )
                    if tokenized_corpus_json:
                        tokenized_corpus = json.loads(tokenized_corpus_json)
                        self.bm25 = BM25Okapi(tokenized_corpus)
                        tokenized_query = query.split()
                        bm25_scores = self.bm25.get_scores(tokenized_query)
                        top_keyword_idxs = sorted(
                            range(len(bm25_scores)),
                            key=lambda i: bm25_scores[i],
                            reverse=True,
                        )[: k * 2]
                        for idx in top_keyword_idxs:
                            if idx < len(self.keyword_index):
                                candidates.append(
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
                        candidates.append(
                            RAGSnippet(
                                content=row["content"],
                                score=1 - row["dist"],  # Normalize distance to score
                                source=row["source"],
                                agent_name=agent_name,
                            )
                        )

                # --- Hybrid rank: Weighted sum (dedup by content) ---
                unique_candidates: Dict[str, RAGSnippet] = {}
                for cand in candidates:
                    key = cand.content
                    if key not in unique_candidates:
                        unique_candidates[key] = cand
                    else:
                        # Merge scores (take max per source, then weight)
                        existing = unique_candidates[key]
                        existing.score = max(existing.score, cand.score)

                # Apply hybrid weights
                weighted: List[RAGSnippet] = []
                for cand in unique_candidates.values():
                    bm25_score = cand.score if cand.source == "bm25" else 0.0
                    sem_score = cand.score if cand.source != "bm25" else 0.0
                    cand.score = (
                        bm25_score * self.config.keyword_weight
                        + sem_score * self.config.semantic_weight
                    )
                    weighted.append(cand)

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
                top_candidates = filtered

            span.set_attribute("final_count", len(top_candidates))
            return top_candidates

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
            data = json.loads(raw.strip())
            return max(0.0, min(1.0, float(data.get("score", 0.5))))
        except Exception as e:  # pragma: no cover
            logger.warning(f"Reflection failed: {e}")
            return 0.5  # Default medium confidence
