"""Semantic retrieval knowledge source."""
from __future__ import annotations

from app.blackboard.core import Blackboard, BlackboardEntry, Patch
from app.blackboard.registry import KSDescriptor, KnowledgeSource
from app.blackboard.resources import DatasourceResource
from app.blackboard.vocabulary import EntryKind


class SemanticRetrievalKS(KnowledgeSource):
    descriptor = KSDescriptor(
        ks_id="semantic_retrieval",
        description="Search the active datasource with an embedded query.",
        consumes=(EntryKind.SEARCH_JOB.value,),
        produces=(EntryKind.SEARCH_RESULT.value,),
        required_resources=("search",),
        priority=20,
    )

    def __init__(self, datasource_resource: DatasourceResource) -> None:
        self.datasource_resource = datasource_resource

    async def can_handle(self, entry: BlackboardEntry, blackboard: Blackboard) -> bool:
        if entry.kind != EntryKind.SEARCH_JOB.value:
            return False
        if blackboard.find(entry.goal_id, kind=EntryKind.SEARCH_RESULT.value):
            return False
        return "query_vector" in entry.payload

    async def execute(self, entry: BlackboardEntry, blackboard: Blackboard) -> Patch:
        datasource = self.datasource_resource.get()
        hits = await datasource.search(
            entry.payload["query_vector"],
            top_k=entry.payload.get("top_k", 5),
            filter=entry.payload.get("filter"),
        )
        result = BlackboardEntry(
            goal_id=entry.goal_id,
            kind=EntryKind.SEARCH_RESULT.value,
            status="done",
            payload={"hits": [hit.model_dump() for hit in hits]},
        )
        patch = Patch()
        patch.add(result)
        patch.add(
            entry.model_copy(update={"status": "done"}),
            expected_revision=entry.revision,
        )
        return patch

