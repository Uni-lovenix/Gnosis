"""Blackboard core: entries, patches, optimistic concurrency and storage."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from app.blackboard.events import BlackboardChange, BlackboardEventBus
from app.blackboard.vocabulary import BlackboardVocabulary
from app.observability.models import new_id


def _now() -> str:
    import time

    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class BlackboardConflictError(RuntimeError):
    """Raised when a Patch targets a stale revision."""


class BlackboardEntry(BaseModel):
    """Canonical blackboard item understood by every knowledge source."""

    entry_id: str = Field(default_factory=new_id)
    goal_id: str
    kind: str
    schema_version: int = 1
    status: str = "queued"
    revision: int = 0
    payload: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    updated_at: str = Field(default_factory=_now)


@dataclass
class Patch:
    """Proposed blackboard mutation produced by a knowledge source."""

    upserts: list[BlackboardEntry] = field(default_factory=list)
    expected_revisions: dict[str, int] = field(default_factory=dict)

    def add(self, entry: BlackboardEntry, expected_revision: int | None = None) -> None:
        self.upserts.append(entry)
        if expected_revision is not None:
            self.expected_revisions[entry.entry_id] = expected_revision


class Blackboard:
    """In-process shared state center with optimistic concurrency control."""

    def __init__(
        self,
        vocabulary: BlackboardVocabulary | None = None,
        event_bus: BlackboardEventBus | None = None,
    ) -> None:
        self.vocabulary = vocabulary or BlackboardVocabulary()
        self.event_bus = event_bus or BlackboardEventBus()
        self._entries: dict[str, BlackboardEntry] = {}
        self._lock = asyncio.Lock()

    def get(self, entry_id: str) -> BlackboardEntry | None:
        return self._entries.get(entry_id)

    def find(
        self,
        goal_id: str,
        kind: str | None = None,
        status: str | None = None,
    ) -> list[BlackboardEntry]:
        out = [
            entry
            for entry in self._entries.values()
            if entry.goal_id == goal_id
            and (kind is None or entry.kind == kind)
            and (status is None or entry.status == status)
        ]
        return sorted(out, key=lambda e: e.updated_at)

    def snapshot(self, goal_id: str) -> list[BlackboardEntry]:
        return self.find(goal_id)

    async def apply_patch(self, patch: Patch) -> list[BlackboardChange]:
        if not patch.upserts:
            return []

        async with self._lock:
            changes: list[BlackboardChange] = []
            for proposed in patch.upserts:
                self.vocabulary.validate_entry(proposed)
                current = self._entries.get(proposed.entry_id)
                expected = patch.expected_revisions.get(proposed.entry_id)
                if expected is not None and (current is None or current.revision != expected):
                    raise BlackboardConflictError(
                        f"stale revision for {proposed.entry_id}: "
                        f"expected {expected}, current {current.revision if current else None}"
                    )

                previous_status = current.status if current else "absent"
                next_revision = (current.revision if current else 0) + 1
                entry = proposed.model_copy(
                    update={"revision": next_revision, "updated_at": _now()}
                )
                self._entries[entry.entry_id] = entry
                changes.append(
                    BlackboardChange(
                        goal_id=entry.goal_id,
                        entry_id=entry.entry_id,
                        kind=entry.kind,
                        status=entry.status,
                        previous_status=previous_status,
                        revision=entry.revision,
                        summary=entry.error or entry.status,
                        entry=entry,
                    )
                )

            if changes:
                await self.event_bus.publish(changes)
            return changes

