"""FastAPI application entry point for LegacyLens."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.embeddings.embedder import Embedder
from backend.ingestion.pipeline import IngestionPipeline
from backend.rag.generator import Generator
from backend.rag.retriever import Retriever
from backend.routers import health, ingest, query
from backend.vectordb.qdrant_store import QdrantStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    settings = get_settings()
    logger.info("Starting LegacyLens...")

    # Initialize components
    embedder = Embedder()
    store = QdrantStore()
    await store.initialize()

    retriever = Retriever(embedder=embedder, store=store)
    generator = Generator()
    pipeline = IngestionPipeline(embedder=embedder, store=store)

    # Attach to app state
    app.state.embedder = embedder
    app.state.store = store
    app.state.retriever = retriever
    app.state.generator = generator
    app.state.pipeline = pipeline

    logger.info("LegacyLens ready!")
    yield

    # Cleanup
    await store.close()
    logger.info("LegacyLens shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="LegacyLens",
    description="RAG system for navigating legacy enterprise codebases",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(ingest.router)
app.include_router(query.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "LegacyLens",
        "description": "RAG system for legacy enterprise codebases",
        "version": "1.0.0",
        "docs": "/docs",
    }
