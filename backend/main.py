"""FastAPI application entry point for LegacyLens."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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

    # Try to connect to Qdrant with a short timeout (Railway health check must pass quickly)
    app.state.qdrant_connected = False
    try:
        await asyncio.wait_for(store.initialize(), timeout=5.0)
        app.state.qdrant_connected = True
        logger.info("Qdrant connected successfully")
    except asyncio.TimeoutError:
        logger.warning("Qdrant connection timed out on startup — degraded mode")
    except Exception as e:
        logger.warning("Qdrant not available on startup: %s — degraded mode", e)

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
    try:
        await store.close()
    except Exception:
        pass
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


# Serve static frontend in production (built React app)
STATIC_DIR = Path(__file__).parent.parent / "static"

if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    logger.info(f"Serving frontend from {STATIC_DIR}")

    # Mount /assets for JS/CSS bundles
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    async def serve_index():
        """Serve the React SPA index."""
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve static files or fall back to index.html for SPA routing."""
        # Serve exact file if it exists (e.g. favicon.ico, manifest.json)
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        # Fall back to index.html for SPA client-side routing
        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/")
    async def root():
        """Root endpoint (no frontend build found — dev mode)."""
        return {
            "name": "LegacyLens",
            "description": "RAG system for legacy enterprise codebases",
            "version": "1.0.0",
            "docs": "/docs",
        }
