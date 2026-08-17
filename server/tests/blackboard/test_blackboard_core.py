"""Core blackboard tests: vocabulary, patches, events and conflict control."""
from __future__ import annotations

import pathlib

import pytest

from app.blackboard.core import Blackboard, BlackboardConflictError, BlackboardEntry, Patch
from app.blackboard.events import BlackboardEventBus
from app.blackboard.registry import KSDescriptor, KnowledgeSourceRegistry
from app.blackboard.vocabulary import BlackboardVocabulary, EntryKind, VocabularyError


@pytest.mark.asyncio
async def test_apply_patch_increments_revision_and_publishes_event():
    bus = BlackboardEventBus()
    seen = []
    bus.subscribe(seen.append)
    blackboard = Blackboard(event_bus=bus)
    entry = BlackboardEntry(goal_id="g", kind=EntryKind.SEARCH_JOB.value, status="ready")

    changes = await blackboard.apply_patch(Patch(upserts=[entry]))

    assert len(changes) == 1
    assert blackboard.get(entry.entry_id) is not None
    assert blackboard.get(entry.entry_id).revision == 1
    assert seen[0].entry_id == entry.entry_id
    assert seen[0].status == "ready"


@pytest.mark.asyncio
async def test_stale_patch_is_rejected():
    blackboard = Blackboard()
    entry = BlackboardEntry(goal_id="g", kind=EntryKind.IMPORT_JOB.value, status="ready")
    await blackboard.apply_patch(Patch(upserts=[entry]))

    updated = entry.model_copy(update={"status": "processing"})
    await blackboard.apply_patch(
        Patch(upserts=[updated], expected_revisions={entry.entry_id: 1})
    )

    with pytest.raises(BlackboardConflictError):
        await blackboard.apply_patch(
            Patch(upserts=[updated], expected_revisions={entry.entry_id: 1})
        )


@pytest.mark.asyncio
async def test_vocabulary_rejects_unknown_kind():
    blackboard = Blackboard()
    entry = BlackboardEntry(goal_id="g", kind="unknown_kind", status="ready")
    with pytest.raises(VocabularyError):
        await blackboard.apply_patch(Patch(upserts=[entry]))


def test_registry_validates_descriptor_vocabulary():
    registry = KnowledgeSourceRegistry(
        BlackboardVocabulary(),
        known_resources={"parser"},
    )

    class BadSource:
        descriptor = KSDescriptor(
            ks_id="bad",
            consumes=("not_a_kind",),
            produces=(EntryKind.PARSED_DOCUMENT.value,),
        )

        async def can_handle(self, entry, blackboard):
            return False

        async def execute(self, entry, blackboard):
            return None

    with pytest.raises(VocabularyError):
        registry.register(BadSource())


def test_registry_validates_resources():
    registry = KnowledgeSourceRegistry(
        BlackboardVocabulary(),
        known_resources={"parser"},
    )

    class BadSource:
        descriptor = KSDescriptor(
            ks_id="bad-resource",
            consumes=(EntryKind.IMPORT_JOB.value,),
            produces=(EntryKind.PARSED_DOCUMENT.value,),
            required_resources=("missing_resource",),
        )

        async def can_handle(self, entry, blackboard):
            return False

        async def execute(self, entry, blackboard):
            return None

    with pytest.raises(ValueError):
        registry.register(BadSource())


def test_knowledge_sources_do_not_import_each_other():
    source_dir = (
        pathlib.Path(__file__).resolve().parents[2] / "app" / "blackboard" / "sources"
    )
    for path in sorted(source_dir.glob("*.py")):
        if path.name == "__init__.py":
            continue
        text = path.read_text(encoding="utf-8")
        assert "from app.blackboard.sources" not in text
        assert "import app.blackboard.sources" not in text
