"""Tests for the indexing and retrieval pipelines (using mock embedder + memory datasource)."""
from __future__ import annotations

import pytest

from app.datasources.base import DatasourceConfig
from app.datasources.vector_db_adapter import VectorDBAdapter
from app.embedding.base import EmbedderConfig
from app.embedding.mock_embedder import HashMockEmbedder
from app.observability.models import Document
from app.pipeline.indexing import IndexingPipeline, ProgressEvent
from app.pipeline.retrieval import RetrievalPipeline


@pytest.fixture
def embedder() -> HashMockEmbedder:
    return HashMockEmbedder(EmbedderConfig(name="m", type="mock-hash", options={"dim": 32}))


@pytest.fixture
def ds() -> VectorDBAdapter:
    return VectorDBAdapter(
        DatasourceConfig(name="mem", type="vector", options={"backend": "memory", "dim": 32})
    )


@pytest.mark.asyncio
async def test_indexing_pipeline_runs_end_to_end(embedder, ds):
    pipeline = IndexingPipeline(ds, embedder, embed_batch_size=8)
    events: list[ProgressEvent] = []
    pipeline.on_progress = events.append

    doc = Document(source_path="x", text="apple banana cherry\n\nquantum photon")
    result = await pipeline.run(doc)
    assert result.chunks >= 1
    assert result.embedded == result.chunks
    assert result.written == result.chunks
    assert events  # on_progress was called
    # Stage labels cover the four transitions.
    seen_stages = {e.stage for e in events}
    assert {"parsing", "chunking", "embedding", "writing"} <= seen_stages


@pytest.mark.asyncio
async def test_indexing_pipeline_skips_empty(embedder, ds):
    pipeline = IndexingPipeline(ds, embedder)
    doc = Document(source_path="x", text="")
    result = await pipeline.run(doc)
    assert result.chunks == 0
    assert result.embedded == 0


@pytest.mark.asyncio
async def test_indexing_pipeline_emits_non_decreasing_progress(embedder, ds):
    pipeline = IndexingPipeline(ds, embedder, embed_batch_size=2)
    events: list[ProgressEvent] = []
    pipeline.on_progress = events.append
    text = "lorem ipsum " * 50  # small chunks, multiple batches
    doc = Document(source_path="x", text=text)
    await pipeline.run(doc)
    # Multiple progress updates, monotonically non-decreasing.
    assert len(events) >= 3
    for a, b in zip(events, events[1:]):
        assert b.progress >= a.progress


@pytest.mark.asyncio
async def test_indexing_pipeline_emits_progress_event_with_message(embedder, ds):
    """The ProgressEvent carries a human-readable message for the UI."""
    pipeline = IndexingPipeline(ds, embedder, embed_batch_size=8)
    events: list[ProgressEvent] = []
    pipeline.on_progress = events.append

    doc = Document(source_path="notes.md", text="alpha beta gamma\n\ndelta epsilon")
    await pipeline.run(doc)
    msgs = [e.message for e in events if e.message]
    # At least one message names the file; another names the chunk count.
    assert any("notes.md" in m for m in msgs)
    assert any("/" in m and "chunks" in m for m in msgs)


@pytest.mark.asyncio
async def test_retrieval_returns_top_k(embedder, ds):
    pipeline = IndexingPipeline(ds, embedder)
    docs = [
        Document(source_path="d1", text="apple banana cherry"),
        Document(source_path="d2", text="quantum entanglement photon"),
        Document(source_path="d3", text="apple sauce recipe"),
    ]
    for d in docs:
        await pipeline.run(d)

    retrieval = RetrievalPipeline(ds, embedder)
    hits = await retrieval.search("apple banana", top_k=2)
    assert len(hits) == 2
    # apple-related documents should rank higher than quantum
    assert any("apple" in h.text for h in hits)


@pytest.mark.asyncio
async def test_retrieval_empty_query_returns_empty(embedder, ds):
    retrieval = RetrievalPipeline(ds, embedder)
    assert await retrieval.search("") == []
    assert await retrieval.search("   ") == []