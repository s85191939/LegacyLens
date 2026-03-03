from backend.vectordb.qdrant_store import QdrantStore


def test_store_can_initialize_without_api_key(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("backend.vectordb.qdrant_store.AsyncQdrantClient", FakeClient)

    store = QdrantStore()
    store.qdrant_url = "http://localhost:6333"
    store.qdrant_api_key = ""
    store._build_client()

    assert captured["url"] == "http://localhost:6333"
    assert "api_key" not in captured
