"""Contract tests for the abstract ``DataSource``.

These tests instantiate a fake adapter that records calls, then exercise the
public API and assert behavior. If a new adapter conforms to the contract,
these tests should pass.
"""
from __future__ import annotations

from typing import Any, Iterable

import pytest

from app.datasources.base import DataSource, DatasourceConfig, HealthStatus
from app.observability.models import Chunk, Hit


class FakeAdapter(DataSource):
    type = "fake"

    def __init__(self, config: DatasourceConfig) -> None:
        super().__init__(config)
        self.added: list[Chunk] = []
        self.deleted: list[str] = []
        self.searches: list[tuple[list[float], int]] = []
        self.health_called = 0

    async def add(self, chunks: Iterable[Chunk]) -> list[str]:
        ids: list[str] = []
        for c in chunks:
            if c.vector is None:
                raise ValueError("missing vector")
            self.added.append(c)
            ids.append(c.id)
        return ids

    async def search(self, vector, top_k=5, filter=None):  # type: ignore[override]
        self.searches.append((vector, top_k))
        # Return deterministic ranking by L2 distance to the query.
        scored = []
        for c in self.added:
            s = sum((a - b) ** 2 for a, b in zip(c.vector or [], vector))
            scored.append((c, s))
        scored.sort(key=lambda x: x[1])
        return [
            Hit(id=c.id, score=1.0 / (1.0 + s), text=c.text, metadata=c.metadata)
            for c, s in scored[:top_k]
        ]

    async def delete(self, ids: Iterable[str]) -> int:
        id_list = list(ids)
        self.deleted.extend(id_list)
        return len(id_list)

    async def health(self) -> HealthStatus:
        self.health_called += 1
        return HealthStatus(ok=True)


@pytest.mark.asyncio
async def test_lifecycle_roundtrip():
    cfg = DatasourceConfig(name="t", type="fake")
    ds = FakeAdapter(cfg)
    chunks = [
        Chunk(document_id="d1", text="a", vector=[1.0, 0.0]),
        Chunk(document_id="d1", text="b", vector=[0.0, 1.0]),
    ]
    ids = await ds.add(chunks)
    assert len(ids) == 2

    hits = await ds.search([1.0, 0.0])
    assert len(hits) == 2
    assert hits[0].text == "a"

    removed = await ds.delete([ids[0]])
    assert removed == 1

    h = await ds.health()
    assert h.ok is True


@pytest.mark.asyncio
async def test_search_returns_top_k_in_descending_score():
    ds = FakeAdapter(DatasourceConfig(name="t", type="fake"))
    chunks = [
        Chunk(document_id="d", text="x", vector=[1.0, 0.0]),
        Chunk(document_id="d", text="y", vector=[0.5, 0.5]),
        Chunk(document_id="d", text="z", vector=[0.0, 1.0]),
    ]
    await ds.add(chunks)
    hits = await ds.search([1.0, 0.0], top_k=2)
    assert [h.text for h in hits] == ["x", "y"]
    assert hits[0].score >= hits[1].score


def test_capabilities_default_empty():
    ds = FakeAdapter(DatasourceConfig(name="t", type="fake"))
    assert ds.capabilities() == set()