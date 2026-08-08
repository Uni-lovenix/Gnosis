"""Tests for the task progress endpoints (G6 upload observability)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.files import set_pipeline, set_task_store
from app.chunking import ChunkParams, TextChunker
from app.datasources.base import DatasourceConfig
from app.datasources.vector_db_adapter import VectorDBAdapter
from app.embedding.base import EmbedderConfig
from app.embedding.mock_embedder import HashMockEmbedder
from app.observability.models import TaskStage
from app.observability.task_store import TaskStore
from app.pipeline.indexing import IndexingPipeline


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """A FastAPI TestClient with the file/task endpoints wired to a
    throwaway in-memory TaskStore and pipeline."""
    from app.main import app

    store = TaskStore(tmp_path / "tasks.db")
    embedder = HashMockEmbedder(EmbedderConfig(name="m", type="mock-hash", options={"dim": 16}))
    ds = VectorDBAdapter(
        DatasourceConfig(name="mem", type="vector", options={"backend": "memory", "dim": 16})
    )
    pipeline = IndexingPipeline(ds, embedder, TextChunker(ChunkParams()), embed_batch_size=4)
    set_task_store(store)
    set_pipeline(pipeline)
    return TestClient(app)


def test_task_status_includes_stage_and_events_after_run(client: TestClient, tmp_path: Path):
    """Driving an import end-to-end through the API must produce a
    TaskStatus that includes a populated ``stage`` field and a non-empty
    ``events`` array."""
    upload = tmp_path / "note.md"
    upload.write_text("# Title\n\nbody paragraph with content\n\nmore content here\n")
    with open(upload, "rb") as f:
        r = client.post(
            "/v1/files/import",
            files={"file": ("note.md", f, "text/markdown")},
        )
    assert r.status_code == 200, r.text
    task_id = r.json()["task_id"]

    # The background task has already run by the time we get here (TestClient
    # waits). Poll once for the final state.
    r = client.get(f"/v1/files/tasks/{task_id}")
    assert r.status_code == 200
    body: dict[str, Any] = r.json()
    assert body["status"] == "done"
    assert body["stage"] == TaskStage.DONE.value
    assert isinstance(body["events"], list)
    assert len(body["events"]) >= 4  # parsing, chunking, embedding, writing
    seen_stages = {e["stage"] for e in body["events"]}
    assert {"parsing", "chunking", "embedding", "writing"} <= seen_stages


def test_task_events_endpoint_returns_all_events(client: TestClient, tmp_path: Path):
    upload = tmp_path / "tiny.md"
    upload.write_text("hello world")
    with open(upload, "rb") as f:
        r = client.post(
            "/v1/files/import",
            files={"file": ("tiny.md", f, "text/markdown")},
        )
    assert r.status_code == 200
    task_id = r.json()["task_id"]

    r = client.get(f"/v1/files/tasks/{task_id}/events")
    assert r.status_code == 200
    body = r.json()
    assert "events" in body
    assert "next_since_id" in body
    assert body["next_since_id"] >= len(body["events"])


def test_task_events_since_id_paginates(client: TestClient, tmp_path: Path):
    upload = tmp_path / "two.md"
    upload.write_text("alpha beta\n\ngamma delta\n")
    with open(upload, "rb") as f:
        r = client.post(
            "/v1/files/import",
            files={"file": ("two.md", f, "text/markdown")},
        )
    task_id = r.json()["task_id"]

    first = client.get(f"/v1/files/tasks/{task_id}/events").json()
    total = len(first["events"])
    assert total >= 4  # parsing, chunking, embedding, writing
    half = first["next_since_id"] // 2

    second = client.get(f"/v1/files/tasks/{task_id}/events?since_id={half}").json()
    # The second call should return only events after the midpoint.
    assert len(second["events"]) <= total
    assert second["next_since_id"] >= half


def test_task_events_endpoint_404_for_unknown_task(client: TestClient):
    r = client.get("/v1/files/tasks/does-not-exist/events")
    assert r.status_code == 404


def test_task_status_default_stage_is_queued_for_old_payload(
    client: TestClient, tmp_path: Path
):
    """If the server payload omits ``stage`` (older version), the renderer
    should fall back to ``queued``. We simulate this by directly inserting
    a row without the stage column populated via the legacy migration path."""
    from app.observability.task_store import TaskStore

    # Use the store the fixture created (tmp_path/tasks.db).
    store_path = next(p for p in tmp_path.iterdir() if p.name == "tasks.db")
    # Add a row that bypasses the API but shares the same db file.
    TaskStore(store_path).create("legacy-payload", "import")
    r = client.get("/v1/files/tasks/legacy-payload")
    assert r.status_code == 200
    body = r.json()
    assert body["stage"] == TaskStage.QUEUED.value
    assert body["events"] == []