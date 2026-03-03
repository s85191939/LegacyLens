"""Ingestion endpoint - triggers codebase ingestion pipeline."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

router = APIRouter(tags=["ingestion"])


class IngestRequest(BaseModel):
    """Request body for ingestion."""
    codebase_path: Optional[str] = None
    reingest: bool = False


class IngestResponse(BaseModel):
    """Response from ingestion."""
    status: str
    message: str
    stats: dict = {}


# Track ingestion state (for /api/ingest/status)
_ingestion_status = {"running": False, "last_stats": None}


def _stats_dict(stats):
    """Build stats dict from pipeline result or error."""
    return {
        "files_scanned": stats.files_scanned,
        "files_processed": stats.files_processed,
        "total_lines": stats.total_lines,
        "total_chunks": stats.total_chunks,
        "total_tokens": stats.total_tokens,
        "total_embeddings": stats.total_embeddings,
        "languages": stats.languages,
        "duration_seconds": round(stats.duration_seconds, 2),
        "errors": (stats.errors or [])[:10],
    }


@router.post("/api/ingest", response_model=IngestResponse)
async def ingest_codebase(request: Request, body: IngestRequest):
    """Trigger ingestion of the codebase. Blocks until indexing is complete so the UI can disable queries for the full duration."""
    if not getattr(request.app.state, "qdrant_connected", False):
        raise HTTPException(
            status_code=503,
            detail="Qdrant vector database is not connected. Please check QDRANT_URL and QDRANT_API_KEY settings.",
        )

    if _ingestion_status["running"]:
        return IngestResponse(
            status="already_running",
            message="Ingestion is already in progress",
        )

    pipeline = request.app.state.pipeline
    _ingestion_status["running"] = True
    try:
        stats = await pipeline.ingest(
            codebase_path=body.codebase_path,
            reingest=body.reingest,
        )
        _ingestion_status["last_stats"] = _stats_dict(stats)
        return IngestResponse(
            status="completed",
            message=f"Ingested {stats.total_chunks} chunks from {stats.files_processed} files.",
            stats=_ingestion_status["last_stats"],
        )
    except Exception as e:
        _ingestion_status["last_stats"] = {"error": str(e)}
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _ingestion_status["running"] = False


@router.get("/api/ingest/status")
async def ingestion_status():
    """Check ingestion status."""
    return {
        "running": _ingestion_status["running"],
        "last_stats": _ingestion_status["last_stats"],
    }
