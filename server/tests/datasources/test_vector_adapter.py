"""Tests for the in-memory vector adapter (the default vector backend)."""
from __future__ import annotations

import numpy as np
import pytest

from app.datasources.registry import all_types
from app.datasources.vector_db_adapter import VectorDBAdapter, VectorDBConfig
from app.observability.models import Chunk


@pytest.fixture
def adapter() -> VectorDBAdapter:
    cfg = VectorDBConfig(name="mem", type="vector", options={"backend": "memory", "dim": 4})
    return VectorDBAdapter(cfg)


def _chunk(text: str, vec: list[float], document_id: str = "doc1") -> Chunk:
    return Chunk(
        document_id=document_id,
        text=text,
        vector=vec,
        metadata={"src": text, "document_id": document_id},
    )


@pytest.mark.asyncio
async def test_registry_includes_all_adapters():
    types = set(all_types())
    assert {"elasticsearch", "postgresql", "mysql", "vector"} <= types


@pytest.mark.asyncio
async def test_add_search_delete(adapter: VectorDBAdapter):
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
async def test_add_is_idempotent(adapter: VectorDBAdapter):
    chunks = [_chunk("apple", [1.0, 0.0, 0.0, 0.0])]
    ids1 = await adapter.add(chunks)
    ids2 = await adapter.add(chunks)
    assert ids1 == ids2
    hits = await adapter.search([1.0, 0.0, 0.0, 0.0], top_k=1)
    assert len(hits) == 1
    assert hits[0].id == ids1[0]


@pytest.mark.asyncio
async def test_search_with_filter(adapter: VectorDBAdapter):
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
async def test_health_ok(adapter: VectorDBAdapter):
    h = await adapter.health()
    assert h.ok is True


@pytest.mark.asyncio
async def test_search_empty_store_returns_empty(adapter: VectorDBAdapter):
    hits = await adapter.search([1.0, 0.0, 0.0, 0.0])
    assert hits == []


@pytest.mark.asyncio
async def test_chunk_without_vector_rejected(adapter: VectorDBAdapter):
    c = Chunk(document_id="doc1", text="no vec")
    with pytest.raises(Exception):
        await adapter.add([c])


@pytest.mark.asyncio
async def test_dimension_mismatch_rejected():
    cfg = VectorDBConfig(name="mem", type="vector", options={"backend": "memory", "dim": 4})
    adapter = VectorDBAdapter(cfg)
    bad = _chunk("bad", [1.0, 0.0])  # length 2 vs dim 4
    with pytest.raises(Exception):
        await adapter.add([bad])


def test_capabilities_declared(adapter: VectorDBAdapter):
    assert "metadata_filter" in adapter.capabilities()