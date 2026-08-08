"""Milvus 1:1 tests for the vector adapter.

These tests exercise ``VectorDBAdapter`` against a real Milvus server (started
via ``scripts/start_milvus.sh``). They mirror the in-memory tests in
``test_vector_adapter.py`` so that the two backends stay in lockstep.

When Milvus is not reachable, every test in this file is skipped with a clear
hint pointing at the start script — the rest of the suite keeps running.
"""
from __future__ import annotations

import pytest

from app.datasources.base import DatasourceError
from app.datasources.vector_db_adapter import VectorDBAdapter, VectorDBConfig
from app.observability.models import Chunk

from .conftest import require_milvus


DIM = 4


def _adapter(uri: str, collection: str) -> VectorDBAdapter:
    cfg = VectorDBConfig(
        name="milvus",
        type="vector",
        options={"backend": "milvus", "uri": uri, "collection": collection, "dim": DIM},
    )
    return VectorDBAdapter(cfg)


def _chunk(text: str, vec: list[float], document_id: str = "doc1") -> Chunk:
    return Chunk(
        document_id=document_id,
        text=text,
        vector=vec,
        metadata={"src": text, "document_id": document_id},
    )


@pytest.mark.asyncio
async def test_add_search_delete(milvus_uri: str, milvus_collection: str) -> None:
    require_milvus(milvus_uri)  # explicit guard so skip reason is local to this test
    adapter = _adapter(milvus_uri, milvus_collection)
    chunks = [
        _chunk("apple", [1.0, 0.0, 0.0, 0.0]),
        _chunk("banana", [0.0, 1.0, 0.0, 0.0]),
        _chunk("cherry", [0.0, 0.0, 1.0, 0.0]),
    ]
    ids = await adapter.add(chunks)
    assert len(ids) == 3

    hits = await adapter.search([1.0, 0.0, 0.0, 0.0], top_k=2)
    assert len(hits) == 2
    assert hits[0].text == "apple"
    assert hits[0].score > hits[1].score

    removed = await adapter.delete([ids[0]])
    assert removed == 1
    hits = await adapter.search([1.0, 0.0, 0.0, 0.0], top_k=2)
    assert all(h.id != ids[0] for h in hits)


@pytest.mark.asyncio
async def test_add_is_idempotent(milvus_uri: str, milvus_collection: str) -> None:
    require_milvus(milvus_uri)
    adapter = _adapter(milvus_uri, milvus_collection)
    chunks = [_chunk("apple", [1.0, 0.0, 0.0, 0.0])]
    ids1 = await adapter.add(chunks)
    ids2 = await adapter.add(chunks)
    assert ids1 == ids2
    hits = await adapter.search([1.0, 0.0, 0.0, 0.0], top_k=1)
    assert len(hits) == 1
    assert hits[0].id == ids1[0]


@pytest.mark.asyncio
async def test_search_with_filter(milvus_uri: str, milvus_collection: str) -> None:
    require_milvus(milvus_uri)
    adapter = _adapter(milvus_uri, milvus_collection)
    await adapter.add(
        [
            _chunk("apple", [1.0, 0.0, 0.0, 0.0], document_id="docA"),
            _chunk("applesauce", [0.9, 0.1, 0.0, 0.0], document_id="docB"),
        ]
    )
    hits = await adapter.search(
        [1.0, 0.0, 0.0, 0.0],
        top_k=5,
        filter={"document_id": "docB"},
    )
    assert len(hits) == 1
    assert hits[0].metadata["src"] == "applesauce"


@pytest.mark.asyncio
async def test_search_empty_store_returns_empty(
    milvus_uri: str, milvus_collection: str
) -> None:
    require_milvus(milvus_uri)
    adapter = _adapter(milvus_uri, milvus_collection)
    hits = await adapter.search([1.0, 0.0, 0.0, 0.0])
    assert hits == []


@pytest.mark.asyncio
async def test_health_ok(milvus_uri: str, milvus_collection: str) -> None:
    require_milvus(milvus_uri)
    adapter = _adapter(milvus_uri, milvus_collection)
    # seed one row so the collection is not brand-new (Milvus list_collections is
    # the real liveness probe; the adapter uses it).
    await adapter.add([_chunk("seed", [1.0, 0.0, 0.0, 0.0])])
    h = await adapter.health()
    assert h.ok is True


@pytest.mark.asyncio
async def test_chunk_without_vector_rejected(
    milvus_uri: str, milvus_collection: str
) -> None:
    require_milvus(milvus_uri)
    adapter = _adapter(milvus_uri, milvus_collection)
    c = Chunk(document_id="doc1", text="no vec")
    with pytest.raises(DatasourceError):
        await adapter.add([c])


@pytest.mark.asyncio
async def test_dimension_mismatch_rejected(
    milvus_uri: str, milvus_collection: str
) -> None:
    require_milvus(milvus_uri)
    adapter = _adapter(milvus_uri, milvus_collection)
    bad = _chunk("bad", [1.0, 0.0])  # length 2 vs dim 4
    with pytest.raises(Exception):
        await adapter.add([bad])


def test_capabilities_declared(milvus_uri: str, milvus_collection: str) -> None:
    require_milvus(milvus_uri)
    adapter = _adapter(milvus_uri, milvus_collection)
    assert "metadata_filter" in adapter.capabilities()