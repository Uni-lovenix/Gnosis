"""Tests for the /v1/chunks browse endpoint (G7)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api import chunks as chunks_api
from app.datasources.base import (
    ChunkSummary,
    DataSource,
    DatasourceConfig,
    DocumentSummary,
    NotSupportedError,
)


class _StubDataSource(DataSource):
    """Minimal DataSource for browse tests; only list_chunks and
    aggregate_by_document are exercised."""

    def __init__(
        self,
        *,
        name: str = "stub",
        type: str = "stub",
        chunks: list[ChunkSummary] | None = None,
        aggs: dict[str, DocumentSummary] | None = None,
        capabilities: set[str] | None = None,
    ) -> None:
        cfg = DatasourceConfig(name=name, type=type, options={})
        super().__init__(cfg)
        # DataSource declares ``name``/``type`` as class annotations; set them
        # so endpoints that read ``ds.type`` don't crash with AttributeError.
        self.name = name
        self.type = type
        self._chunks = chunks or []
        self._aggs = aggs or {}
        # NOTE: use ``is not None`` (not ``or``) so an explicit empty set means
        # "no capabilities"; an empty set is falsy in Python and would fall
        # back to the default.
        self._caps = capabilities if capabilities is not None else {"chunk_list"}

    def capabilities(self) -> set[str]:
        return self._caps

    async def add(self, chunks):  # noqa: ARG002
        return [c.id for c in chunks]

    async def search(self, vector, top_k=5, filter=None):  # noqa: ARG002
        return []

    async def delete(self, ids):  # noqa: ARG002
        return 0

    async def health(self):
        from app.datasources.base import HealthStatus
        return HealthStatus(ok=True, message="stub")

    async def list_chunks(self, *, document_id=None, parser=None, offset=0, limit=20):
        return self._chunks, len(self._chunks)

    async def aggregate_by_document(self) -> dict[str, DocumentSummary]:
        return self._aggs


@pytest.fixture
def client_with_active(monkeypatch):
    """A TestClient with a stubbed active datasource bound to the chunks API."""
    from app.main import app

    chunks = [
        ChunkSummary(
            chunk_id="c1",
            document_id="d1",
            text="hello",
            text_length=5,
            metadata={"parser": "markdown"},
        ),
        ChunkSummary(
            chunk_id="c2",
            document_id="d1",
            text="world",
            text_length=5,
            metadata={"parser": "markdown"},
        ),
    ]
    aggs = {
        "d1": DocumentSummary(
            document_id="d1",
            chunk_count=2,
            parsers=["markdown"],
            first_chunk_id="c1",
            sample_text="hello",
        ),
    }
    ds = _StubDataSource(chunks=chunks, aggs=aggs)
    chunks_api.set_active_datasource(ds)
    return TestClient(app)


def test_browse_returns_chunks_and_aggregations(client_with_active):
    r = client_with_active.get("/v1/chunks")
    assert r.status_code == 200
    body: dict[str, Any] = r.json()
    assert len(body["chunks"]) == 2
    assert body["total"] == 2
    assert body["aggregations"]["d1"]["chunk_count"] == 2


def test_browse_passes_filters_through(client_with_active):
    r = client_with_active.get(
        "/v1/chunks",
        params={"document_id": "d1", "parser": "markdown", "offset": 0, "limit": 10},
    )
    assert r.status_code == 200


def test_browse_rejects_invalid_limit(client_with_active):
    """FastAPI's Query(ge=1, le=100) returns 422 for out-of-range values; the
    handler's manual check is a backstop for callers that bypass validation
    (e.g. test clients)."""
    r = client_with_active.get("/v1/chunks", params={"limit": 0})
    assert r.status_code in (400, 422)
    r = client_with_active.get("/v1/chunks", params={"limit": 9999})
    assert r.status_code in (400, 422)


def test_browse_rejects_negative_offset(client_with_active):
    r = client_with_active.get("/v1/chunks", params={"offset": -1})
    assert r.status_code in (400, 422)


def test_browse_returns_501_when_capability_missing():
    from app.main import app

    chunks_api.set_active_datasource(
        _StubDataSource(name="vec", type="vector", capabilities=set())
    )
    client = TestClient(app)
    r = client.get("/v1/chunks")
    assert r.status_code == 501
    assert "chunk_list" in r.json()["detail"]


def test_browse_returns_503_when_no_active_datasource():
    from app.main import app

    chunks_api.set_active_datasource(None)
    client = TestClient(app)
    r = client.get("/v1/chunks")
    assert r.status_code == 503


def test_browse_returns_501_when_aggregate_raises_not_supported():
    """Even when capability says yes, a runtime NotSupportedError during the
    aggregate call surfaces as 501 (not 500)."""

    class _PartialStub(_StubDataSource):
        async def aggregate_by_document(self):  # type: ignore[override]
            raise NotSupportedError("agg not supported in this build")

    from app.main import app

    chunks_api.set_active_datasource(_PartialStub())
    client = TestClient(app)
    r = client.get("/v1/chunks")
    assert r.status_code == 501