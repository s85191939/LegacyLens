"""Ingestion pipeline - orchestrates scan → preprocess → chunk → embed → store."""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

from backend.config import get_settings
from backend.embeddings.embedder import Embedder
from backend.ingestion.chunker import CodeChunk, chunk_file
from backend.ingestion.preprocessor import preprocess_file
from backend.ingestion.scanner import ScanResult, scan_codebase
from backend.vectordb.qdrant_store import QdrantStore

logger = logging.getLogger(__name__)


@dataclass
class IngestionStats:
    """Statistics from an ingestion run."""
    files_scanned: int = 0
    files_processed: int = 0
    total_lines: int = 0
    total_chunks: int = 0
    total_tokens: int = 0
    total_embeddings: int = 0
    languages: Dict[str, int] = field(default_factory=dict)
    duration_seconds: float = 0
    errors: List[str] = field(default_factory=list)


class IngestionPipeline:
    """Orchestrates the full ingestion pipeline."""

    def __init__(self, embedder: Embedder, store: QdrantStore):
        self.embedder = embedder
        self.store = store

    async def ingest(
        self,
        codebase_path: str = None,
        reingest: bool = False,
    ) -> IngestionStats:
        """
        Run the full ingestion pipeline.

        Args:
            codebase_path: Path to codebase (default from settings)
            reingest: If True, delete existing collection first

        Returns:
            IngestionStats with pipeline results
        """
        settings = get_settings()
        if codebase_path is None:
            codebase_path = settings.codebase_path

        start_time = time.time()
        stats = IngestionStats()

        # Step 0: Reingest if requested
        if reingest:
            try:
                await self.store.delete_collection()
                logger.info("Deleted existing collection for re-ingestion")
            except Exception:
                pass  # Collection might not exist
            await self.store.initialize()

        # Step 1: Scan codebase
        logger.info(f"Scanning codebase: {codebase_path}")
        scan_result = scan_codebase(codebase_path)
        stats.files_scanned = scan_result.total_files
        stats.total_lines = scan_result.total_lines
        logger.info(
            f"Found {scan_result.total_files} files, "
            f"{scan_result.total_lines} lines across "
            f"{len(scan_result.languages)} languages"
        )

        # Step 2: Process each file → preprocess → chunk
        all_chunks: List[CodeChunk] = []

        for file_info in scan_result.files:
            try:
                content, metadata = preprocess_file(file_info.absolute_path)
                chunks = chunk_file(content, file_info.relative_path, file_info.language)
                all_chunks.extend(chunks)
                stats.files_processed += 1

                lang = file_info.language
                stats.languages[lang] = stats.languages.get(lang, 0) + len(chunks)

            except Exception as e:
                error_msg = f"Error processing {file_info.relative_path}: {e}"
                logger.error(error_msg)
                stats.errors.append(error_msg)

        stats.total_chunks = len(all_chunks)
        stats.total_tokens = sum(c.tokens for c in all_chunks)
        logger.info(
            f"Created {stats.total_chunks} chunks "
            f"({stats.total_tokens} tokens) "
            f"from {stats.files_processed} files"
        )

        if not all_chunks:
            logger.warning("No chunks created - nothing to embed")
            stats.duration_seconds = time.time() - start_time
            return stats

        # Step 3: Generate embeddings
        logger.info("Generating embeddings...")
        texts = [chunk.content for chunk in all_chunks]
        embeddings = await self.embedder.embed_texts(texts)
        stats.total_embeddings = len(embeddings)
        logger.info(f"Generated {len(embeddings)} embeddings")

        # Step 4: Upsert into Qdrant
        logger.info("Upserting into Qdrant...")
        chunk_dicts = [
            {
                "content": c.content,
                "file_path": c.file_path,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "chunk_type": c.chunk_type,
                "name": c.name,
                "division": c.division,
                "section": c.section,
                "language": c.language,
                "dependencies": c.dependencies,
                "tokens": c.tokens,
                "content_hash": c.content_hash,
            }
            for c in all_chunks
        ]

        await self.store.upsert_chunks(chunk_dicts, embeddings)
        logger.info("Ingestion complete!")

        stats.duration_seconds = time.time() - start_time
        return stats
