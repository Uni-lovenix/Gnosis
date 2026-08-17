"""Text chunking knowledge source."""
from __future__ import annotations

from app.blackboard.core import Blackboard, BlackboardEntry, Patch
from app.blackboard.registry import KSDescriptor, KnowledgeSource
from app.blackboard.vocabulary import EntryKind
from app.chunking import TextChunker
from app.observability.models import Document


class ChunkTextKS(KnowledgeSource):
    descriptor = KSDescriptor(
        ks_id="chunk_text",
        description="Split a ParsedDocument into a ChunkSet.",
        consumes=(EntryKind.PARSED_DOCUMENT.value,),
        produces=(EntryKind.CHUNK_SET.value,),
        required_resources=("chunker",),
        priority=20,
    )

    async def can_handle(self, entry: BlackboardEntry, blackboard: Blackboard) -> bool:
        if entry.kind != EntryKind.PARSED_DOCUMENT.value:
            return False
        if blackboard.find(entry.goal_id, kind=EntryKind.CHUNK_SET.value):
            return False
        return entry.status == "ready"

    async def execute(self, entry: BlackboardEntry, blackboard: Blackboard) -> Patch:
        payload = entry.payload
        doc = Document(
            id=payload["document_id"],
            source_path=payload["source_path"],
            mime=payload.get("mime", ""),
            text=payload["text"],
            metadata=payload.get("metadata", {}),
        )
        chunks = TextChunker().split(doc)
        chunk_set = BlackboardEntry(
            goal_id=entry.goal_id,
            kind=EntryKind.CHUNK_SET.value,
            status="ready",
            payload={
                "document_id": doc.id,
                "chunks": [chunk.model_dump() for chunk in chunks],
                "count": len(chunks),
            },
        )
        patch = Patch()
        patch.add(chunk_set)
        patch.add(
            entry.model_copy(update={"status": "done"}),
            expected_revision=entry.revision,
        )
        return patch
