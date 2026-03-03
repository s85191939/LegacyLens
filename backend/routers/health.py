"""Health check and stats endpoints."""

import asyncio

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])

# Short timeout so Railway health check never hangs when Qdrant is unreachable
HEALTH_CHECK_TIMEOUT = 3.0


@router.get("/api/health")
@router.get("/health")  # alias for Railway / load balancers that check /health
async def health_check(request: Request):
    """Health check endpoint. Always returns 200 quickly; Qdrant check is time-limited."""
    store = getattr(request.app.state, "store", None)
    if store is None:
        return {"status": "starting", "qdrant": "pending", "collection": {}}

    try:
        info = await asyncio.wait_for(
            store.get_collection_info(),
            timeout=HEALTH_CHECK_TIMEOUT,
        )

        if info.get("error"):
            request.app.state.qdrant_connected = False
            return {
                "status": "degraded",
                "qdrant": f"disconnected: {info['error']}",
                "collection": info,
            }

        request.app.state.qdrant_connected = True
        return {
            "status": "healthy",
            "qdrant": "connected",
            "collection": info,
        }

    except asyncio.TimeoutError:
        request.app.state.qdrant_connected = False
        return {
            "status": "degraded",
            "qdrant": "disconnected: timeout",
            "collection": {"error": "timeout"},
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
