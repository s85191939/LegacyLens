"""Health check and stats endpoints."""

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health_check(request: Request):
    """Health check endpoint."""
    store = request.app.state.store
    try:
        info = await store.get_collection_info()
        qdrant_status = "connected"
    except Exception as e:
        info = {}
        qdrant_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "qdrant": qdrant_status,
        "collection": info,
    }


@router.get("/api/stats")
async def get_stats(request: Request):
    """Get collection statistics."""
    store = request.app.state.store
    info = await store.get_collection_info()
    return {
        "collection": info,
    }
