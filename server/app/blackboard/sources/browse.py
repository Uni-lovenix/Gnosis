"""Browse knowledge source for read-only chunk inspection."""
from __future__ import annotations

from app.blackboard.core import Blackboard, BlackboardEntry, Patch
from app.blackboard.registry import KSDescriptor, KnowledgeSource
from app.blackboard.resources import DatasourceResource
from app.blackboard.vocabulary import EntryKind


class BrowseKS(KnowledgeSource):
    descriptor = KSDescriptor(
        ks_id="browse",
        description="Read chunks and document aggregations from the active datasource.",
        consumes=(EntryKind.BROWSE_REQUEST.value,),
        produces=(EntryKind.BROWSE_RESULT.value,),
        required_resources=("search",),
        priority=10,
    )

    def __init__(self, datasource_resource: DatasourceResource) -> None:
        self.datasource_resource = datasource_resource

    async def can_handle(self, entry: BlackboardEntry, blackboard: Blackboard) -> bool:
        if entry.kind != EntryKind.BROWSE_REQUEST.value:
            return False
        if blackboard.find(entry.goal_id, kind=EntryKind.BROWSE_RESULT.value):
            return False
        return entry.status == "ready"

    async def execute(self, entry: BlackboardEntry, blackboard: Blackboard) -> Patch:
        datasource = self.datasource_resource.get()
        chunks, total = await datasource.list_chunks(
            document_id=entry.payload.get("document_id"),
            parser=entry.payload.get("parser"),
            offset=entry.payload.get("offset", 0),
            limit=entry.payload.get("limit", 20),
        )
        aggregations = await datasource.aggregate_by_document()
        result = BlackboardEntry(
            goal_id=entry.goal_id,
            kind=EntryKind.BROWSE_RESULT.value,
            status="done",
            payload={
                "chunks": [chunk.model_dump() for chunk in chunks],
                "total": total,
                "aggregations": {
                    document_id: agg.model_dump()
                    for document_id, agg in aggregations.items()
                },
            },
        )
        patch = Patch()
        patch.add(result)
        patch.add(
            entry.model_copy(update={"status": "done"}),
            expected_revision=entry.revision,
        )
        return patch

