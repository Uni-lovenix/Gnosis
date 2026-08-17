"""Blackboard controller and knowledge source integration tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.blackboard.control import (
    BlackboardController,
    KnowledgeSourceConflictError,
    ResourceManager,
)
from app.blackboard.core import Blackboard
from app.blackboard.events import BlackboardEventBus
from app.blackboard.registry import KSDescriptor, KnowledgeSourceRegistry
from app.blackboard.resources import DatasourceResource
from app.blackboard.sources import (
    BrowseKS,
    ChunkEmbeddingKS,
    ChunkTextKS,
    ParseFileKS,
    QueryEmbeddingKS,
    SemanticRetrievalKS,
    WriteDatasourceKS,
)
from app.blackboard.vocabulary import BlackboardVocabulary, EntryKind
from app.datasources.base import DataSource, DatasourceConfig, HealthStatus
from app.datasources.vector_db_adapter import VectorDBAdapter
from app.embedding.base import EmbedderConfig
from app.embedding.mock_embedder import HashMockEmbedder
from app.observability.models import ChunkSummary, DocumentSummary


@pytest.fixture
def embedder():
    return HashMockEmbedder(
        EmbedderConfig(name="m", type="mock-hash", options={"dim": 32})
    )


@pytest.fixture
def ds():
    return VectorDBAdapter(
        DatasourceConfig(
            name="mem",
            type="vector",
            options={"backend": "memory", "dim": 32},
        )
    )


def _build_controller(embedder, ds, *, extra_sources=None):
    vocabulary = BlackboardVocabulary()
    event_bus = BlackboardEventBus()
    blackboard = Blackboard(vocabulary=vocabulary, event_bus=event_bus)
    resources = ResourceManager(
        {
            "parser": 1,
            "chunker": 1,
            "embedder": 1,
            "datasource_write": 1,
            "search": 1,
            "llm": 1,
        }
    )
    registry = KnowledgeSourceRegistry(vocabulary, known_resources=set(resources.capacities))
    datasource_resource = DatasourceResource(ds)
    controller = BlackboardController(
        blackboard=blackboard,
        event_bus=event_bus,
        registry=registry,
        resource_manager=resources,
        datasource_resource=datasource_resource,
    )
    controller.register_knowledge_source(ParseFileKS())
    controller.register_knowledge_source(ChunkTextKS())
    controller.register_knowledge_source(ChunkEmbeddingKS(embedder))
    controller.register_knowledge_source(WriteDatasourceKS(datasource_resource))
    controller.register_knowledge_source(QueryEmbeddingKS(embedder))
    controller.register_knowledge_source(SemanticRetrievalKS(datasource_resource))
    controller.register_knowledge_source(BrowseKS(datasource_resource))
    for source in extra_sources or []:
        controller.register_knowledge_source(source)
    return controller


@pytest.mark.asyncio
async def test_import_chain_runs_through_blackboard(embedder, ds, tmp_path: Path):
    controller = _build_controller(embedder, ds)
    path = tmp_path / "notes.md"
    path.write_text("# Notes\n\napple banana cherry\n\nquantum photon", encoding="utf-8")

    snapshot = await controller.submit_import(
        "import-1",
        file_path=str(path),
        parser="markdown",
        mime="text/markdown",
    )

    kinds = {entry.kind for entry in snapshot}
    assert {
        EntryKind.PARSED_DOCUMENT.value,
        EntryKind.CHUNK_SET.value,
        EntryKind.EMBEDDED_CHUNK_SET.value,
        EntryKind.INDEX_RESULT.value,
    } <= kinds
    result = next(entry for entry in snapshot if entry.kind == EntryKind.INDEX_RESULT.value)
    assert result.status == "done"
    assert result.payload["written"] >= 1


@pytest.mark.asyncio
async def test_search_chain_embeds_query_and_retrieves(embedder, ds, tmp_path: Path):
    controller = _build_controller(embedder, ds)
    path = tmp_path / "notes.md"
    path.write_text("# Notes\n\napple banana cherry\n\nquantum photon", encoding="utf-8")
    await controller.submit_import("import-1", file_path=str(path), parser="markdown")

    snapshot = await controller.submit_search(
        "search-1",
        query="apple banana",
        top_k=3,
    )

    result = next(
        (entry for entry in snapshot if entry.kind == EntryKind.SEARCH_RESULT.value),
        None,
    )
    assert result is not None
    assert result.payload["hits"]
    assert any("apple" in hit["text"] for hit in result.payload["hits"])


@pytest.mark.asyncio
async def test_replace_datasource_then_import_uses_new(embedder, ds, tmp_path: Path):
    controller = _build_controller(embedder, ds)
    new_ds = VectorDBAdapter(
        DatasourceConfig(
            name="mem-new",
            type="vector",
            options={"backend": "memory", "dim": 32},
        )
    )

    await controller.replace_datasource(new_ds)
    assert controller.datasource_resource.datasource is new_ds

    path = tmp_path / "notes.md"
    path.write_text("# Notes\n\napple banana cherry\n\nquantum photon", encoding="utf-8")
    await controller.submit_import("import-new", file_path=str(path), parser="markdown")

    snapshot = await controller.submit_search("search-new", query="apple banana", top_k=3)
    result = next(
        (entry for entry in snapshot if entry.kind == EntryKind.SEARCH_RESULT.value),
        None,
    )
    assert result is not None
    assert result.payload["hits"]
    assert any("apple" in hit["text"] for hit in result.payload["hits"])


class _StubBrowseDataSource(DataSource):
    type = "stub-browse"

    def __init__(self) -> None:
        super().__init__(DatasourceConfig(name="stub", type=self.type, options={}))
        self.name = "stub"
        self.chunks = [
            ChunkSummary(
                chunk_id="c1",
                document_id="d1",
                text="hello",
                text_length=5,
                metadata={"parser": "markdown"},
            )
        ]
        self.aggregations = {
            "d1": DocumentSummary(
                document_id="d1",
                chunk_count=1,
                parsers=["markdown"],
                first_chunk_id="c1",
                sample_text="hello",
            )
        }

    def capabilities(self) -> set[str]:
        return {"chunk_list"}

    async def add(self, chunks):
        return []

    async def search(self, vector, top_k=5, filter=None):
        return []

    async def delete(self, ids):
        return 0

    async def health(self):
        return HealthStatus(ok=True)

    async def list_chunks(self, *, document_id=None, parser=None, offset=0, limit=20):
        return self.chunks, len(self.chunks)

    async def aggregate_by_document(self):
        return self.aggregations


@pytest.mark.asyncio
async def test_browse_chain_reads_active_datasource(embedder, ds):
    controller = _build_controller(embedder, ds)
    controller.set_datasource(_StubBrowseDataSource())

    snapshot = await controller.submit_browse(
        "browse-1",
        document_id="d1",
        limit=10,
    )

    result = next(
        (entry for entry in snapshot if entry.kind == EntryKind.BROWSE_RESULT.value),
        None,
    )
    assert result is not None
    assert result.payload["total"] == 1
    assert result.payload["chunks"][0]["text"] == "hello"


@pytest.mark.asyncio
async def test_scheduler_raises_on_equal_priority_conflict(embedder, ds):
    class AlwaysA:
        descriptor = KSDescriptor(
            ks_id="always-a",
            consumes=(EntryKind.SEARCH_JOB.value,),
            produces=(EntryKind.SEARCH_RESULT.value,),
            priority=10,
        )

        async def can_handle(self, entry, blackboard):
            return True

        async def execute(self, entry, blackboard):
            return None

    class AlwaysB(AlwaysA):
        descriptor = KSDescriptor(
            ks_id="always-b",
            consumes=(EntryKind.SEARCH_JOB.value,),
            produces=(EntryKind.SEARCH_RESULT.value,),
            priority=10,
        )

    controller = _build_controller(embedder, ds, extra_sources=[AlwaysA(), AlwaysB()])

    with pytest.raises(KnowledgeSourceConflictError):
        await controller.submit_search("conflict-1", query="hello")


@pytest.mark.asyncio
async def test_resource_manager_blocks_while_locked():
    resources = ResourceManager({"embedder": 1})
    assert resources.can_acquire(["embedder"])

    async with resources.acquire(["embedder"]):
        assert not resources.can_acquire(["embedder"])

    assert resources.can_acquire(["embedder"])
