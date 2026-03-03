"""OpenAI embedding module with batching and retry logic."""

import asyncio
import logging
from typing import List

from openai import AsyncOpenAI

from backend.config import get_settings

logger = logging.getLogger(__name__)


class Embedder:
    """Generates embeddings using OpenAI text-embedding-3-small."""

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.embedding_model
        self.dim = settings.embedding_dim
        self.batch_size = 100  # Max chunks per API call
        self.max_retries = 3

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts with batching.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (1536-dim each)
        """
        all_embeddings = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = await self._embed_batch_with_retry(batch)
            all_embeddings.extend(batch_embeddings)

            if i + self.batch_size < len(texts):
                logger.info(
                    f"Embedded {i + len(batch)}/{len(texts)} chunks"
                )

        return all_embeddings

    async def embed_query(self, query: str) -> List[float]:
        """Embed a single query string."""
        embeddings = await self._embed_batch_with_retry([query])
        return embeddings[0]

    async def _embed_batch_with_retry(
        self, texts: List[str]
    ) -> List[List[float]]:
        """Embed a batch with exponential backoff retry."""
        for attempt in range(self.max_retries):
            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=texts,
                )
                return [item.embedding for item in response.data]
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Embedding failed after {self.max_retries} attempts: {e}")
                    raise
                wait_time = 2 ** attempt
                logger.warning(
                    f"Embedding attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)

        raise RuntimeError("Unreachable")
