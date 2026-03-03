"""Health check and stats endpoints."""

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health_check(request: Request):
    """Health check endpoint - also attempts to reconnect if Qdrant was down."""
    store = request.app.state.store
    qdrant_connected = getattr(request.app.state, "qdrant_connected", False)

    try:
        info = await store.get_collection_info()
        qdrant_status = "connected"

        # If we weren't connected before, try to initialize the collection
        if not qdrant_connected:
            try:
                await store.initialize()
            except Exception:
                pass
            request.app.state.qdrant_connected = True

    except Exception as e:
        info = {}
        qdrant_status = f"disconnected: {str(e)}"
        request.app.state.qdrant_connected = False

    return {
        "status": "healthy" if request.app.state.qdrant_connected else "degraded",
        "qdrant": qdrant_status,
        "collection": info,
    }


@router.get("/api/stats")
async def get_stats(request: Request):
    """Get collection statistics."""
    store = request.app.state.store
    try:
        info = await store.get_collection_info()
    except Exception as e:
        info = {"error": str(e)}
    return {
        "collection": info,
    }
