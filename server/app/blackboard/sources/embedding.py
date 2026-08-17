"""Embedding knowledge sources for chunks and queries."""
from __future__ import annotations

from app.blackboard.core import Blackboard, BlackboardEntry, Patch
from app.blackboard.registry import KSDescriptor, KnowledgeSource
from app.blackboard.vocabulary import EntryKind
from app.embedding.base import Embedder


class ChunkEmbeddingKS(KnowledgeSource):
    descriptor = KSDescriptor(
        ks_id="chunk_embedding",
        description="Embed every chunk in a ChunkSet.",
        consumes=(EntryKind.CHUNK_SET.value,),
        produces=(EntryKind.EMBEDDED_CHUNK_SET.value,),
        required_resources=("embedder",),
        priority=50,
    )

    def __init__(self, embedder: Embedder) -> None:
        self.embedder = embedder

    async def can_handle(self, entry: BlackboardEntry, blackboard: Blackboard) -> bool:
        if entry.kind != EntryKind.CHUNK_SET.value:
            return False
        if blackboard.find(entry.goal_id, kind=EntryKind.EMBEDDED_CHUNK_SET.value):
            return False
        return entry.status == "ready" and entry.payload.get("count", 0) > 0

    async def execute(self, entry: BlackboardEntry, blackboard: Blackboard) -> Patch:
        chunks = [dict(chunk) for chunk in entry.payload["chunks"]]
        texts = [chunk["text"] for chunk in chunks]
        vectors = await self.embedder.embed(texts)
        for chunk, vector in zip(chunks, vectors):
            chunk["vector"] = vector
        embedded = BlackboardEntry(
            goal_id=entry.goal_id,
            kind=EntryKind.EMBEDDED_CHUNK_SET.value,
            status="ready",
            payload={
                "document_id": entry.payload.get("document_id"),
                "chunks": chunks,
                "count": len(chunks),
                "embedded": len(chunks),
            },
        )
        patch = Patch()
        patch.add(embedded)
        patch.add(
            entry.model_copy(update={"status": "done"}),
            expected_revision=entry.revision,
        )
        return patch


class QueryEmbeddingKS(KnowledgeSource):
    descriptor = KSDescriptor(
        ks_id="query_embedding",
        description="Embed a search query into a query vector.",
        consumes=(EntryKind.SEARCH_JOB.value,),
        produces=(EntryKind.SEARCH_JOB.value,),
        required_resources=("embedder",),
        priority=10,
    )

    def __init__(self, embedder: Embedder) -> None:
        self.embedder = embedder

    async def can_handle(self, entry: BlackboardEntry, blackboard: Blackboard) -> bool:
        return entry.kind == EntryKind.SEARCH_JOB.value and "query_vector" not in entry.payload

    async def execute(self, entry: BlackboardEntry, blackboard: Blackboard) -> Patch:
        vectors = await self.embedder.embed([entry.payload["query"]])
        updated = entry.model_copy(
            update={
                "status": "ready",
                "payload": {**entry.payload, "query_vector": vectors[0]},
            }
        )
        patch = Patch()
        patch.add(updated, expected_revision=entry.revision)
        return patch

