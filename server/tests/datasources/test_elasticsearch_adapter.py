"""Tests for the Elasticsearch adapter, using a fake client.

We do not require a running ES server in the unit test suite — instead we
patch ``_client_or_error`` to return a fake client that records calls. This
exercises the adapter's contract end-to-end.
"""
from __future__ import annotations

from typing import Any

import pytest

from app.datasources.elasticsearch_adapter import (
    ElasticsearchAdapter,
    ElasticsearchConfig,
)
from app.observability.models import Chunk


class _FakeIndices:
    def __init__(self) -> None:
        self.exists_result = False
        self.created: list[dict[str, Any]] = []

    def exists(self, index: str) -> bool:
        return self.exists_result

    def create(self, index: str, **body: Any) -> dict[str, Any]:
        self.created.append({"index": index, "body": body})
        self.exists_result = True
        return {"acknowledged": True}


class _FakeBulkResponse:
    def __init__(self, errors: bool = False) -> None:
        self._errors = errors

    def get(self, _key: str, default=None):
        return [] if self._errors else []


class _FakeClient:
    def __init__(self) -> None:
        self.indices = _FakeIndices()
        self.bulk_calls: list[Any] = []
        self.search_calls: list[Any] = []
        self.info_result = {"version": {"number": "8.12.0"}}
        self._bulk_errors = False
        # For G7 browse tests: stubbed list/aggregate responses.
        self._next_search_response: dict[str, Any] | None = None
        self._next_search_error: Exception | None = None

    def bulk(self, operations=None, refresh=None):
        self.bulk_calls.append({"operations": operations, "refresh": refresh})
        return _FakeBulkResponse(self._bulk_errors)

    def search(self, index: str, **kwargs: Any):
        self.search_calls.append({"index": index, **kwargs})
        if self._next_search_error is not None:
            raise self._next_search_error
        if self._next_search_response is not None:
            return self._next_search_response
        # Default: a single KNN-shaped response used by the existing tests.
        return {
            "hits": {
                "hits": [
                    {
                        "_id": "c1",
                        "_score": 0.9,
                        "_source": {
                            "chunk_id": "c1",
                            "document_id": "d1",
                            "text": "hello",
                            "metadata": {"src": "x"},
                        },
                    }
                ]
            }
        }

    def info(self):
        return self.info_result


@pytest.fixture
def patched_es(monkeypatch):
    client = _FakeClient()
    monkeypatch.setattr(
        "app.datasources.elasticsearch_adapter._client_or_error",
        lambda cfg: client,
    )
    return client


@pytest.mark.asyncio
async def test_es_add_creates_index_then_bulk(patched_es):
    cfg = ElasticsearchConfig(
        name="es",
        options={"hosts": ["http://x"], "index": "kb", "dim": 4},
    )
    adapter = ElasticsearchAdapter(cfg)
    chunks = [Chunk(document_id="d1", text="hello", vector=[1.0, 0.0, 0.0, 0.0])]
    ids = await adapter.add(chunks)
    assert ids == [chunks[0].id]
    assert patched_es.indices.created  # ensure_index was called
    assert patched_es.bulk_calls  # bulk was called


@pytest.mark.asyncio
async def test_es_search_uses_knn(patched_es):
    cfg = ElasticsearchConfig(
        name="es",
        options={"hosts": ["http://x"], "index": "kb", "dim": 4},
    )
    adapter = ElasticsearchAdapter(cfg)
    # Pre-populate the fake client so search returns hits.
    hits = await adapter.search([1.0, 0.0, 0.0, 0.0], top_k=3)
    assert len(hits) == 1
    assert hits[0].text == "hello"
    assert hits[0].document_id == "d1"
    assert patched_es.search_calls
    body = patched_es.search_calls[-1]
    assert body["knn"]["field"] == "vector"
    assert body["knn"]["k"] == 3


@pytest.mark.asyncio
async def test_es_health(patched_es):
    cfg = ElasticsearchConfig(name="es", options={"hosts": ["http://x"], "dim": 4})
    adapter = ElasticsearchAdapter(cfg)
    h = await adapter.health()
    assert h.ok is True
    assert h.message == "8.12.0"


def test_es_capabilities_include_metadata_filter():
    cfg = ElasticsearchConfig(name="es", options={"dim": 4})
    adapter = ElasticsearchAdapter.__new__(ElasticsearchAdapter)  # bypass init
    adapter._cfg = cfg
    assert "metadata_filter" in adapter.capabilities()
    assert "bm25_hybrid" in adapter.capabilities()
    assert "chunk_list" in adapter.capabilities()  # G7
    assert "dump" in adapter.capabilities()  # C17


# ---- G7: list_chunks / aggregate_by_document --------------------------------


def _browse_response(
    *,
    hits: list[dict[str, Any]],
    total_value: int = 0,
    aggs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an ES-shaped search response for the browse stub."""
    return {
        "hits": {
            "total": {"value": total_value or len(hits)},
            "hits": hits,
        },
        "aggregations": aggs or {},
    }


@pytest.mark.asyncio
async def test_es_list_chunks_paginates_and_sorts(patched_es):
    long_text = "x" * 500
    patched_es._next_search_response = _browse_response(
        hits=[
            {
                "_id": "c1",
                "_source": {
                    "chunk_id": "c1",
                    "document_id": "d1",
                    "text": "hello",
                    "metadata": {"parser": "markdown"},
                },
            },
            {
                "_id": "c2",
                "_source": {
                    "chunk_id": "c2",
                    "document_id": "d1",
                    "text": long_text,
                    "metadata": {"parser": "markdown"},
                },
            },
        ],
        total_value=2,
    )
    adapter = ElasticsearchAdapter(
        ElasticsearchConfig(name="es", options={"hosts": ["http://x"], "dim": 4})
    )
    chunks, total = await adapter.list_chunks(offset=0, limit=20)
    assert total == 2
    assert len(chunks) == 2
    # Long text is truncated server-side.
    assert chunks[0].text == "hello"
    assert chunks[0].text_length == 5
    assert chunks[1].text.endswith("…")
    assert chunks[1].text_length == 500

    body = patched_es.search_calls[-1]
    assert body["from"] == 0
    assert body["size"] == 20
    assert body["sort"] == [{"document_id": "asc"}, {"chunk_id": "asc"}]
    assert body["_source"] == ["chunk_id", "document_id", "text", "metadata"]


@pytest.mark.asyncio
async def test_es_list_chunks_filters_by_document_id_and_parser(patched_es):
    patched_es._next_search_response = _browse_response(hits=[], total_value=0)
    adapter = ElasticsearchAdapter(
        ElasticsearchConfig(name="es", options={"hosts": ["http://x"], "dim": 4})
    )
    await adapter.list_chunks(document_id="d-42", parser="pdf")
    body = patched_es.search_calls[-1]
    filters = body["query"]["bool"]["filter"]
    assert {"term": {"document_id": "d-42"}} in filters
    assert {"term": {"metadata.parser": "pdf"}} in filters


@pytest.mark.asyncio
async def test_es_dump_all_returns_full_text(patched_es):
    long_text = "x" * 500
    patched_es._next_search_response = _browse_response(
        hits=[
            {
                "_id": "c1",
                "_source": {
                    "chunk_id": "c1",
                    "document_id": "d1",
                    "text": long_text,
                    "metadata": {"parser": "markdown"},
                },
            }
        ],
        total_value=1,
    )
    adapter = ElasticsearchAdapter(
        ElasticsearchConfig(name="es", options={"hosts": ["http://x"], "dim": 4})
    )
    chunks, total = await adapter.dump_all(offset=0, limit=10)
    assert total == 1
    assert len(chunks) == 1
    assert chunks[0].text == long_text
    assert chunks[0].document_id == "d1"
    body = patched_es.search_calls[-1]
    assert body["query"] == {"match_all": {}}


@pytest.mark.asyncio
async def test_es_aggregate_by_document_groups(patched_es):
    patched_es._next_search_response = _browse_response(
        hits=[],
        total_value=0,
        aggs={
            "by_doc": {
                "buckets": [
                    {
                        "key": "d1",
                        "doc_count": 5,
                        "parsers": {"buckets": [{"key": "markdown"}, {"key": "pdf"}]},
                        "sample": {
                            "hits": {
                                "hits": [
                                    {
                                        "_source": {
                                            "chunk_id": "c1",
                                            "text": "first chunk text",
                                        }
                                    }
                                ]
                            }
                        },
                    },
                    {
                        "key": "d2",
                        "doc_count": 3,
                        "parsers": {"buckets": [{"key": "pdf"}]},
                        "sample": {
                            "hits": {
                                "hits": [
                                    {
                                        "_source": {
                                            "chunk_id": "c9",
                                            "text": "second doc opener",
                                        }
                                    }
                                ]
                            }
                        },
                    },
                ]
            }
        },
    )
    adapter = ElasticsearchAdapter(
        ElasticsearchConfig(name="es", options={"hosts": ["http://x"], "dim": 4})
    )
    out = await adapter.aggregate_by_document()
    assert set(out.keys()) == {"d1", "d2"}
    assert out["d1"].chunk_count == 5
    assert out["d1"].parsers == ["markdown", "pdf"]
    assert out["d1"].first_chunk_id == "c1"
    assert out["d1"].sample_text == "first chunk text"
    assert out["d2"].chunk_count == 3
    assert out["d2"].parsers == ["pdf"]
    assert out["d2"].first_chunk_id == "c9"

    body = patched_es.search_calls[-1]
    assert body["size"] == 0
    assert "by_doc" in body["aggs"]


@pytest.mark.asyncio
async def test_es_aggregate_by_document_handles_es_failure(patched_es):
    """If the agg query raises, the endpoint returns {} rather than 500."""
    patched_es._next_search_error = RuntimeError("boom")
    adapter = ElasticsearchAdapter(
        ElasticsearchConfig(name="es", options={"hosts": ["http://x"], "dim": 4})
    )
    out = await adapter.aggregate_by_document()
    assert out == {}
