import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers import health


class OkStore:
    async def get_collection_info(self):
        return {"name": "legacylens", "points_count": 10}


class ErrStore:
    async def get_collection_info(self):
        return {"name": "legacylens", "error": "unauthorized"}


class SlowStore:
    async def get_collection_info(self):
        await asyncio.sleep(4)
        return {"name": "legacylens", "points_count": 10}


def build_client(store):
    app = FastAPI()
    app.include_router(health.router)
    app.state.store = store
    app.state.qdrant_connected = False
    return TestClient(app)


def test_health_healthy_when_qdrant_ok():
    client = build_client(OkStore())
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "healthy"


def test_health_degraded_when_store_reports_error():
    client = build_client(ErrStore())
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "degraded"
    assert "unauthorized" in body["qdrant"]


def test_health_degraded_on_timeout():
    client = build_client(SlowStore())
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "degraded"
    assert "timeout" in body["qdrant"]
