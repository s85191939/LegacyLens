"""Qdrant vector database client for storing and searching code chunks."""

import logging
import uuid
from dataclasses import dataclass, field
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
        # Support Qdrant Cloud with API key authentication
        if settings.qdrant_api_key:
            self.client = AsyncQdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key,
            )
        else:
            self.client = AsyncQdrantClient(url=settings.qdrant_url)
        self.collection_name = settings.qdrant_collection
        self.vector_dim = settings.embedding_dim

    async def initialize(self):
        """Create collection if it doesn't exist, with payload indexes."""
        collections = await self.client.get_collections()
        existing = [c.name for c in collections.collections]

        if self.collection_name not in existing:
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_dim,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created collection: {self.collection_name}")

            # Create payload indexes for filtering
            for field_name, schema_type in [
                ("file_path", PayloadSchemaType.KEYWORD),
                ("language", PayloadSchemaType.KEYWORD),
                ("chunk_type", PayloadSchemaType.KEYWORD),
                ("division", PayloadSchemaType.KEYWORD),
                ("name", PayloadSchemaType.KEYWORD),
                ("section", PayloadSchemaType.KEYWORD),
            ]:
                await self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=schema_type,
                )
            logger.info("Created payload indexes")
        else:
            logger.info(f"Collection {self.collection_name} already exists")

    async def upsert_chunks(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        batch_size: int = 100,
    ) -> int:
        """
        Upsert code chunks with their embeddings into Qdrant.

        Args:
            chunks: List of chunk metadata dicts
            embeddings: Corresponding embedding vectors
            batch_size: Points per upsert batch

        Returns:
            Number of points upserted
        """
        points = []
        for chunk, embedding in zip(chunks, embeddings):
            point = PointStruct(
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
            points.append(point)

        # Batch upsert
        total = 0
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            await self.client.upsert(
                collection_name=self.collection_name,
                points=batch,
            )
            total += len(batch)
            logger.info(f"Upserted {total}/{len(points)} points")

        return total

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        language: Optional[str] = None,
        file_path: Optional[str] = None,
        chunk_type: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Search for similar code chunks.

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            language: Optional filter by language
            file_path: Optional filter by file path
            chunk_type: Optional filter by chunk type

        Returns:
            List of SearchResult objects sorted by relevance
        """
        # Build filter conditions
        conditions = []
        if language:
            conditions.append(
                FieldCondition(field_name="language", match=MatchValue(value=language))
            )
        if file_path:
            conditions.append(
                FieldCondition(field_name="file_path", match=MatchValue(value=file_path))
            )
        if chunk_type:
            conditions.append(
                FieldCondition(field_name="chunk_type", match=MatchValue(value=chunk_type))
            )

        query_filter = Filter(must=conditions) if conditions else None

        results = await self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=query_filter,
            with_payload=True,
        )

        search_results = []
        for hit in results:
            payload = hit.payload
            search_results.append(SearchResult(
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
            ))

        return search_results

    async def get_collection_info(self) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            info = await self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "status": info.status.value if info.status else "unknown",
            }
        except Exception as e:
            return {"name": self.collection_name, "error": str(e)}

    async def delete_collection(self):
        """Delete the entire collection (for re-ingestion)."""
        await self.client.delete_collection(self.collection_name)
        logger.info(f"Deleted collection: {self.collection_name}")

    async def close(self):
        """Close the client connection."""
        await self.client.close()
