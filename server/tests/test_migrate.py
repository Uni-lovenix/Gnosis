"""Tests for datasource migration dump/load (C17)."""
from __future__ import annotations

import json

from app.datasources.base import DatasourceConfig
from app.datasources.vector_db_adapter import VectorDBAdapter
from app.embedding.base import EmbedderConfig
from app.embedding.mock_embedder import HashMockEmbedder
from app.observability.migrate import dump_chunks, load_chunks
from app.observability.models import Chunk


def _memory(dim: int = 32) -> VectorDBAdapter:
    return VectorDBAdapter(
        DatasourceConfig(name="mem", type="vector", options={"backend": "memory", "dim": dim})
    )


async def test_dump_and_load_roundtrip(tmp_path):
    src = _memory()
    await src.add(
        [
            Chunk(
                id="c1",
                document_id="d1",
                text="apple banana cherry",
                metadata={"parser": "markdown", "document_id": "d1"},
                vector=[0.1] * 32,
            ),
            Chunk(
                id="c2",
                document_id="d1",
                text="quantum photon",
                metadata={"parser": "markdown", "document_id": "d1"},
                vector=[0.2] * 32,
            ),
        ]
    )
    dump_path = tmp_path / "dump.jsonl"

    dumped = await dump_chunks(src, dump_path)
    assert dumped == 2
    lines = [json.loads(line) for line in dump_path.read_text(encoding="utf-8").splitlines()]
    assert {line["document_id"] for line in lines} == {"d1"}
    assert any("apple banana cherry" == line["text"] for line in lines)

    embedder = HashMockEmbedder(EmbedderConfig(name="m", type="mock-hash", options={"dim": 32}))
    target = _memory()
    loaded = await load_chunks(target, embedder, dump_path, batch_size=2)
    assert loaded == 2

    q = await embedder.embed(["apple banana"])
    hits = await target.search(q[0], top_k=3)
    assert any("apple banana cherry" in hit.text for hit in hits)


class _NoDump:
    name = "no-dump"

    def capabilities(self):
        return set()

    async def dump_all(self, *, offset=0, limit=100):
        raise AssertionError("should not be called")


async def test_dump_rejects_source_without_capability(tmp_path):
    import pytest

    with pytest.raises(ValueError, match="does not support dump"):
        await dump_chunks(_NoDump(), tmp_path / "out.jsonl")
