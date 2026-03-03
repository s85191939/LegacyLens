"""Retrieval pipeline - query embedding, search, and context assembly."""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.config import get_settings
from backend.embeddings.embedder import Embedder
from backend.vectordb.qdrant_store import QdrantStore, SearchResult

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Result from the retrieval pipeline."""
    query: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    context: str = ""
    retrieval_time_ms: float = 0
    total_tokens: int = 0


class Retriever:
    """Handles query → embedding → search → context assembly."""

    def __init__(self, embedder: Embedder, store: QdrantStore):
        self.embedder = embedder
        self.store = store
        settings = get_settings()
        self.top_k = settings.top_k
        self.top_k_expanded = settings.top_k_expanded
        self.max_context_tokens = 8000

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        language: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> RetrievalResult:
        """
        Full retrieval pipeline: embed query → search → assemble context.

        Args:
            query: Natural language query
            top_k: Override default top-k
            language: Optional language filter
            file_path: Optional file path filter

        Returns:
            RetrievalResult with context and sources
        """
        start_time = time.time()
        k = top_k or self.top_k

        # 1. Embed the query
        query_embedding = await self.embedder.embed_query(query)

        # 2. Search Qdrant
        results = await self.store.search(
            query_embedding=query_embedding,
            top_k=k,
            language=language,
            file_path=file_path,
        )

        # 2b. If no results and no filters, retry with larger k so we rarely return 0 when index has data
        if not results and not language and not file_path:
            results = await self.store.search(
                query_embedding=query_embedding,
                top_k=min(20, max(self.top_k_expanded, 10)),
                language=None,
                file_path=None,
            )
            if results:
                results = results[: self.top_k]
                logger.info("Initial search returned 0; used fallback broader search")

        # 2c. Last resort: if index has data but we still have 0 (e.g. edge case), get any chunks so we always return something
        if not results and not language and not file_path:
            try:
                info = await self.store.get_collection_info()
                points = info.get("points_count") or info.get("vectors_count")
                if isinstance(points, (int, float)) and points > 0:
                    results = await self.store.get_any_chunks(limit=self.top_k)
                    if results:
                        logger.info("Using get_any_chunks fallback so user always gets an answer")
            except Exception as exc:
                logger.warning("get_any_chunks fallback failed: %s", exc)

        # 3. Check if results are ambiguous (low scores) → expand search
        if results and results[0].score < 0.5 and k == self.top_k:
            logger.info(
                f"Low confidence ({results[0].score:.3f}), expanding to k={self.top_k_expanded}"
            )
            results = await self.store.search(
                query_embedding=query_embedding,
                top_k=self.top_k_expanded,
                language=language,
                file_path=file_path,
            )

        # 4. Assemble context
        context, sources = self._assemble_context(results)

        elapsed_ms = (time.time() - start_time) * 1000

        return RetrievalResult(
            query=query,
            sources=sources,
            context=context,
            retrieval_time_ms=elapsed_ms,
            total_tokens=sum(s.get("tokens", 0) for s in sources),
        )

    def _assemble_context(
        self, results: List[SearchResult]
    ) -> tuple:
        """
        Assemble context from search results.
        Merges adjacent chunks from the same file and respects token budget.
        """
        sources = []
        context_parts = []
        total_tokens = 0

        # Group results by file for potential merging
        seen_hashes = set()

        for result in results:
            # Skip duplicates
            content_key = f"{result.file_path}:{result.start_line}"
            if content_key in seen_hashes:
                continue
            seen_hashes.add(content_key)

            if total_tokens + result.tokens > self.max_context_tokens:
                break

            # Format source for context
            header = f"File: {result.file_path} | Lines: {result.start_line}-{result.end_line}"
            if result.name:
                header += f" | {result.chunk_type.title()}: {result.name}"

            context_parts.append(f"--- {header} ---\n{result.content}")
            total_tokens += result.tokens

            sources.append({
                "file_path": result.file_path,
                "start_line": result.start_line,
                "end_line": result.end_line,
                "chunk_type": result.chunk_type,
                "name": result.name,
                "division": result.division,
                "section": result.section,
                "language": result.language,
                "dependencies": result.dependencies,
                "score": round(result.score, 4),
                "tokens": result.tokens,
                "content": result.content,
            })

        context = "\n\n".join(context_parts)
        return context, sources
