"""Ingestion endpoint - triggers codebase ingestion pipeline."""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
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


# Track ingestion state
_ingestion_status = {"running": False, "last_stats": None}


async def _run_ingestion(pipeline, codebase_path, reingest):
    """Run ingestion in background."""
    _ingestion_status["running"] = True
    try:
        stats = await pipeline.ingest(
            codebase_path=codebase_path,
            reingest=reingest,
        )
        _ingestion_status["last_stats"] = {
            "files_scanned": stats.files_scanned,
            "files_processed": stats.files_processed,
            "total_chunks": stats.total_chunks,
            "total_tokens": stats.total_tokens,
            "total_embeddings": stats.total_embeddings,
            "languages": stats.languages,
            "duration_seconds": round(stats.duration_seconds, 2),
            "errors": stats.errors[:10],  # Limit error list
        }
    except Exception as e:
        _ingestion_status["last_stats"] = {"error": str(e)}
    finally:
        _ingestion_status["running"] = False


@router.post("/api/ingest", response_model=IngestResponse)
async def ingest_codebase(
    request: Request,
    body: IngestRequest,
    background_tasks: BackgroundTasks,
):
    """Trigger ingestion of the codebase."""
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

    background_tasks.add_task(
        _run_ingestion,
        pipeline,
        body.codebase_path,
        body.reingest,
    )

    return IngestResponse(
        status="started",
        message="Ingestion started in background. Check /api/ingest/status for progress.",
    )


@router.get("/api/ingest/status")
async def ingestion_status():
    """Check ingestion status."""
    return {
        "running": _ingestion_status["running"],
        "last_stats": _ingestion_status["last_stats"],
    }
