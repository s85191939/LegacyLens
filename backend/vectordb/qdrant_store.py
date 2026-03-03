"""Qdrant vector database client for storing and searching code chunks."""

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from backend.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A search result from Qdrant."""

    content: str
    file_path: str
    start_line: int
    end_line: int
    chunk_type: str
    name: str
    division: str
    section: str
    language: str
    dependencies: List[str]
    score: float
    tokens: int


class QdrantStore:
    """Manages Qdrant collection for code chunk storage and retrieval."""

    def __init__(self):
        settings = get_settings()
        self.collection_name = settings.qdrant_collection
        self.vector_dim = settings.embedding_dim
        self.qdrant_url = settings.qdrant_url
        self.qdrant_api_key = settings.qdrant_api_key
        self.client: Optional[AsyncQdrantClient] = None

    def _build_client(self) -> AsyncQdrantClient:
        """
        Build Qdrant client lazily so malformed env vars do not crash app startup.
        """
        if self.client is not None:
            return self.client

        try:
            if self.qdrant_api_key:
                self.client = AsyncQdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key)
            else:
                self.client = AsyncQdrantClient(url=self.qdrant_url)
            return self.client
        except Exception as exc:
            # Keep backend alive in degraded mode even with bad Qdrant config.
            raise RuntimeError(f"Failed to create Qdrant client for URL '{self.qdrant_url}': {exc}") from exc

    async def initialize(self):
        """Create collection if it doesn't exist, with payload indexes."""
        client = self._build_client()
        collections = await client.get_collections()
        existing = [c.name for c in collections.collections]

        if self.collection_name not in existing:
            await client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_dim, distance=Distance.COSINE),
            )
            logger.info("Created collection: %s", self.collection_name)

            for field_name, schema_type in [
                ("file_path", PayloadSchemaType.KEYWORD),
                ("language", PayloadSchemaType.KEYWORD),
                ("chunk_type", PayloadSchemaType.KEYWORD),
                ("division", PayloadSchemaType.KEYWORD),
                ("name", PayloadSchemaType.KEYWORD),
                ("section", PayloadSchemaType.KEYWORD),
            ]:
                await client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=schema_type,
                )
            logger.info("Created payload indexes")
        else:
            logger.info("Collection %s already exists", self.collection_name)

    async def upsert_chunks(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        batch_size: int = 100,
    ) -> int:
        """Upsert code chunks with their embeddings into Qdrant."""
        client = self._build_client()

        points = []
        for chunk, embedding in zip(chunks, embeddings):
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        "content": chunk["content"],
                        "file_path": chunk["file_path"],
                        "start_line": chunk["start_line"],
                        "end_line": chunk["end_line"],
                        "chunk_type": chunk["chunk_type"],
                        "name": chunk.get("name", ""),
                        "division": chunk.get("division", ""),
                        "section": chunk.get("section", ""),
                        "language": chunk.get("language", ""),
                        "dependencies": chunk.get("dependencies", []),
                        "tokens": chunk.get("tokens", 0),
                        "content_hash": chunk.get("content_hash", ""),
                    },
                )
            )

        total = 0
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            await client.upsert(collection_name=self.collection_name, points=batch)
            total += len(batch)
            logger.info("Upserted %s/%s points", total, len(points))

        return total

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        language: Optional[str] = None,
        file_path: Optional[str] = None,
        chunk_type: Optional[str] = None,
    ) -> List[SearchResult]:
        """Search for similar code chunks."""
        client = self._build_client()

        conditions = []
        if language:
            conditions.append(FieldCondition(field_name="language", match=MatchValue(value=language)))
        if file_path:
            conditions.append(FieldCondition(field_name="file_path", match=MatchValue(value=file_path)))
        if chunk_type:
            conditions.append(FieldCondition(field_name="chunk_type", match=MatchValue(value=chunk_type)))

        query_filter = Filter(must=conditions) if conditions else None

        results = await client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=query_filter,
            with_payload=True,
        )

        search_results: List[SearchResult] = []
        for hit in results:
            payload = hit.payload
            search_results.append(
                SearchResult(
                    content=payload.get("content", ""),
                    file_path=payload.get("file_path", ""),
                    start_line=payload.get("start_line", 0),
                    end_line=payload.get("end_line", 0),
                    chunk_type=payload.get("chunk_type", ""),
                    name=payload.get("name", ""),
                    division=payload.get("division", ""),
                    section=payload.get("section", ""),
                    language=payload.get("language", ""),
                    dependencies=payload.get("dependencies", []),
                    score=hit.score,
                    tokens=payload.get("tokens", 0),
                )
            )

        return search_results

    async def get_collection_info(self) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            client = self._build_client()
            info = await client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "status": info.status.value if info.status else "unknown",
            }
        except Exception as exc:
            return {"name": self.collection_name, "error": str(exc)}

    async def delete_collection(self):
        """Delete the entire collection (for re-ingestion)."""
        client = self._build_client()
        await client.delete_collection(self.collection_name)
        logger.info("Deleted collection: %s", self.collection_name)

    async def close(self):
        """Close the client connection."""
        if self.client is not None:
            await self.client.close()
