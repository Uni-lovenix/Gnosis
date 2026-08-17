"""API tests for the search endpoint."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import files as files_api
from app.api import search as search_api
from app.datasources.base import DatasourceConfig
from app.datasources.vector_db_adapter import VectorDBAdapter
from app.embedding.base import EmbedderConfig
from app.embedding.mock_embedder import HashMockEmbedder
from app.main import create_app
from app.observability.task_store import TaskStore
from app.pipeline.indexing import IndexingPipeline
from app.pipeline.retrieval import RetrievalPipeline


@pytest.fixture
def client(tmp_path: Path):
    app = create_app()
    files_api.set_task_store(TaskStore(tmp_path / "tasks.db"))

    # Force a known pipeline independent of env-based fallback.
    dim = 32
    embedder = HashMockEmbedder(EmbedderConfig(name="m", type="mock-hash", options={"dim": dim}))
    ds = VectorDBAdapter(
        DatasourceConfig(name="mem", type="vector", options={"backend": "memory", "dim": dim})
    )
    files_api.set_pipeline(IndexingPipeline(ds, embedder))
    search_api.set_pipeline(RetrievalPipeline(ds, embedder))

    return TestClient(app)


@pytest.mark.asyncio
async def test_search_end_to_end_via_files_import_then_search(client):
    import time

    md = b"# A\n\napple banana cherry\n\n# B\n\nquantum photon"
    r = client.post("/v1/files/import", files={"file": ("x.md", md, "text/markdown")})
    assert r.status_code == 200
    task_id = r.json()["task_id"]

    # Wait for the background pipeline to finish before searching.
    # The TestClient runs BackgroundTasks after the response; we explicitly
    # drain by polling until the task reaches a terminal status.
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        rt = client.get(f"/v1/files/tasks/{task_id}")
        if rt.json()["status"] == "done":
            break
        time.sleep(0.05)
    else:
        raise AssertionError("import task did not reach terminal status in time")

    r = client.post("/v1/search", json={"query": "apple banana", "top_k": 3})
    assert r.status_code == 200
    hits = r.json()["hits"]
    assert len(hits) >= 1
    assert any("apple" in h["text"] for h in hits)


def test_search_empty_query_returns_empty(client):
    r = client.post("/v1/search", json={"query": "", "top_k": 3})
    assert r.status_code == 200
    assert r.json()["hits"] == []


def test_search_pipeline_not_configured(tmp_path: Path):
    from app.api import search as search_api2

    app = create_app()
    files_api.set_task_store(TaskStore(tmp_path / "tasks.db"))
    search_api2.set_pipeline(None)
    search_api2.set_controller(None)
    c = TestClient(app)
    r = c.post("/v1/search", json={"query": "anything"})
    assert r.status_code == 503


def test_search_default_blackboard_path(tmp_path: Path):
    from app.api import search as search_api2

    app = create_app()
    files_api.set_task_store(TaskStore(tmp_path / "tasks.db"))
    assert search_api2.get_controller() is not None
    assert search_api2.get_pipeline() is None
    c = TestClient(app)
    r = c.post("/v1/search", json={"query": "anything"})
    assert r.status_code == 200
    assert r.json()["hits"] == []
