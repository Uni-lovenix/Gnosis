"""SQLite blackboard projection tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.blackboard.core import BlackboardEntry
from app.blackboard.events import BlackboardChange
from app.blackboard.projection import BlackboardProjector
from app.blackboard.vocabulary import EntryKind


@pytest.mark.asyncio
async def test_projection_upserts_current_entry_snapshot(tmp_path: Path):
    projector = BlackboardProjector(tmp_path / "bb.db")
    entry = BlackboardEntry(
        goal_id="goal-1",
        kind=EntryKind.INDEX_RESULT.value,
        status="done",
        payload={"written": 3},
    )

    await projector.on_change(
        BlackboardChange(
            goal_id=entry.goal_id,
            entry_id=entry.entry_id,
            kind=entry.kind,
            status=entry.status,
            previous_status="absent",
            revision=1,
            entry=entry,
        )
    )

    rows = projector.list(goal_id="goal-1")
    assert len(rows) == 1
    assert rows[0]["kind"] == EntryKind.INDEX_RESULT.value
    assert rows[0]["payload"]["written"] == 3


@pytest.mark.asyncio
async def test_projection_replaces_same_entry(tmp_path: Path):
    projector = BlackboardProjector(tmp_path / "bb.db")
    first = BlackboardEntry(
        goal_id="goal-1",
        kind=EntryKind.SEARCH_JOB.value,
        status="ready",
        payload={"query": "a"},
    )
    second = first.model_copy(update={"status": "done", "payload": {"query": "b"}})

    for entry in (first, second):
        await projector.on_change(
            BlackboardChange(
                goal_id=entry.goal_id,
                entry_id=entry.entry_id,
                kind=entry.kind,
                status=entry.status,
                previous_status="ready",
                revision=entry.revision + 1,
                entry=entry,
            )
        )

    rows = projector.list(kind=EntryKind.SEARCH_JOB.value)
    assert len(rows) == 1
    assert rows[0]["status"] == "done"
    assert rows[0]["payload"] == {"query": "b"}

