"""Health check and stats endpoints."""

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health_check(request: Request):
    """Health check endpoint - also attempts to reconnect if Qdrant was down."""
    store = request.app.state.store

    try:
        info = await store.get_collection_info()

        if info.get("error"):
            request.app.state.qdrant_connected = False
            return {
                "status": "degraded",
                "qdrant": f"disconnected: {info['error']}",
                "collection": info,
            }

        # We have valid collection info, mark healthy.
        request.app.state.qdrant_connected = True
        return {
            "status": "healthy",
            "qdrant": "connected",
            "collection": info,
        }

    except Exception as exc:
        request.app.state.qdrant_connected = False
        return {
            "status": "degraded",
            "qdrant": f"disconnected: {str(exc)}",
            "collection": {"error": str(exc)},
        }


@router.get("/api/stats")
async def get_stats(request: Request):
    """Get collection statistics."""
    store = request.app.state.store
    try:
        info = await store.get_collection_info()
    except Exception as exc:
        info = {"error": str(exc)}

    return {
        "collection": info,
    }
