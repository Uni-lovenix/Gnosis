"""Datasource write knowledge source."""
from __future__ import annotations

from app.blackboard.core import Blackboard, BlackboardEntry, Patch
from app.blackboard.registry import KSDescriptor, KnowledgeSource
from app.blackboard.resources import DatasourceResource
from app.blackboard.vocabulary import EntryKind
from app.observability.models import Chunk


class WriteDatasourceKS(KnowledgeSource):
    descriptor = KSDescriptor(
        ks_id="write_datasource",
        description="Write embedded chunks into the active datasource.",
        consumes=(EntryKind.EMBEDDED_CHUNK_SET.value,),
        produces=(EntryKind.INDEX_RESULT.value,),
        required_resources=("datasource_write",),
        priority=60,
    )

    def __init__(self, datasource_resource: DatasourceResource) -> None:
        self.datasource_resource = datasource_resource

    async def can_handle(self, entry: BlackboardEntry, blackboard: Blackboard) -> bool:
        if entry.kind != EntryKind.EMBEDDED_CHUNK_SET.value:
            return False
        if blackboard.find(entry.goal_id, kind=EntryKind.INDEX_RESULT.value):
            return False
        return entry.status == "ready"

    async def execute(self, entry: BlackboardEntry, blackboard: Blackboard) -> Patch:
        chunks = [Chunk(**chunk) for chunk in entry.payload["chunks"]]
        datasource = self.datasource_resource.get()
        ids = await datasource.add(chunks)
        result = BlackboardEntry(
            goal_id=entry.goal_id,
            kind=EntryKind.INDEX_RESULT.value,
            status="done",
            payload={
                "document_id": entry.payload.get("document_id"),
                "chunks": len(chunks),
                "embedded": entry.payload.get("embedded", len(chunks)),
                "written": len(ids),
            },
        )
        patch = Patch()
        patch.add(result)
        patch.add(
            entry.model_copy(update={"status": "done"}),
            expected_revision=entry.revision,
        )
        return patch

