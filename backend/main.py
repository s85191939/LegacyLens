"""FastAPI application entry point for LegacyLens."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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
    logger.info("Starting LegacyLens...")

    embedder = Embedder()
    store = QdrantStore()

    app.state.qdrant_connected = False
    try:
      # Prevent Railway startup hangs if Qdrant is slow/unreachable.
      await asyncio.wait_for(store.initialize(), timeout=8)
      app.state.qdrant_connected = True
      logger.info("Qdrant connected successfully")
    except Exception as exc:
      logger.warning("Qdrant unavailable on startup: %s", exc)
      logger.warning("App will start in degraded mode; query/ingest disabled until Qdrant is reachable")

    retriever = Retriever(embedder=embedder, store=store)
    generator = Generator()
    pipeline = IngestionPipeline(embedder=embedder, store=store)

    app.state.embedder = embedder
    app.state.store = store
    app.state.retriever = retriever
    app.state.generator = generator
    app.state.pipeline = pipeline

    logger.info("LegacyLens ready")
    yield

    try:
        await store.close()
    except Exception:
        pass
    logger.info("LegacyLens shutdown complete")


app = FastAPI(
    title="LegacyLens",
    description="RAG system for navigating legacy enterprise codebases",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(ingest.router)
app.include_router(query.router)

STATIC_DIR = Path(__file__).parent.parent / "static"

if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    logger.info("Serving frontend from %s", STATIC_DIR)

    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    async def serve_index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
else:

    @app.get("/")
    async def root():
        return {
            "name": "LegacyLens",
            "description": "RAG system for legacy enterprise codebases",
            "version": "1.0.0",
            "docs": "/docs",
        }
