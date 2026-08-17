"""Blackboard control component: agenda, scheduler, resources and controller."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from app.blackboard.core import Blackboard, BlackboardConflictError, BlackboardEntry, Patch
from app.blackboard.events import BlackboardEventBus
from app.blackboard.registry import KnowledgeSource, KnowledgeSourceRegistry
from app.blackboard.resources import DatasourceResource
from app.blackboard.vocabulary import EntryKind
from app.observability.models import new_id
from app.observability.logging import get_logger

log = get_logger(__name__)


def _now() -> str:
    import time

    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class AgendaItem(BaseModel):
    """One triggered knowledge-source task waiting for scheduling."""

    agenda_id: str = Field(default_factory=new_id)
    goal_id: str
    entry_id: str
    ks_id: str
    priority: int
    required_resources: list[str] = Field(default_factory=list)
    status: str = "ready"
    created_at: str = Field(default_factory=_now)


class Agenda:
    """Storage for triggered knowledge-source tasks."""

    def __init__(self) -> None:
        self.items: list[AgendaItem] = []

    def add(self, item: AgendaItem) -> bool:
        for existing in self.items:
            if (
                existing.goal_id == item.goal_id
                and existing.entry_id == item.entry_id
                and existing.ks_id == item.ks_id
            ):
                return False
        self.items.append(item)
        return True

    def mark(self, agenda_id: str, status: str) -> None:
        for item in self.items:
            if item.agenda_id == agenda_id:
                item.status = status
                return

    def ready(self, goal_id: str) -> list[AgendaItem]:
        return [
            item
            for item in self.items
            if item.goal_id == goal_id and item.status == "ready"
        ]


class KnowledgeSourceConflictError(RuntimeError):
    """Raised when two knowledge sources claim the same blackboard state."""


@dataclass
class ResourceManager:
    """Capacity-1 resource locks used by the scheduler."""

    capacities: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {
            name: asyncio.Lock() for name in self.capacities
        }

    def can_acquire(self, resources: list[str]) -> bool:
        return all(not self._locks[name].locked() for name in set(resources))

    @asynccontextmanager
    async def acquire(self, resources: list[str]):
        acquired: list[str] = []
        try:
            for name in sorted(set(resources)):
                lock = self._locks[name]
                await lock.acquire()
                acquired.append(name)
            yield
        finally:
            for name in reversed(acquired):
                self._locks[name].release()


class Scheduler:
    """Selects the next runnable agenda item."""

    def choose(self, agenda: Agenda, goal_id: str, resources: ResourceManager) -> AgendaItem | None:
        candidates = [
            item
            for item in agenda.ready(goal_id)
            if resources.can_acquire(item.required_resources)
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda item: (item.priority, item.created_at, item.agenda_id))


class BlackboardController:
    """Scheduler of knowledge sources for one or more goals."""

    def __init__(
        self,
        blackboard: Blackboard | None = None,
        event_bus: BlackboardEventBus | None = None,
        registry: KnowledgeSourceRegistry | None = None,
        resource_manager: ResourceManager | None = None,
        scheduler: Scheduler | None = None,
        datasource_resource: DatasourceResource | None = None,
    ) -> None:
        self.event_bus = event_bus or BlackboardEventBus()
        self.blackboard = blackboard or Blackboard(event_bus=self.event_bus)
        self.registry = registry or KnowledgeSourceRegistry(self.blackboard.vocabulary)
        self.resources = resource_manager or ResourceManager(
            {
                "parser": 1,
                "chunker": 1,
                "embedder": 1,
                "datasource_write": 1,
                "search": 1,
                "llm": 1,
            }
        )
        self.scheduler = scheduler or Scheduler()
        self.agenda = Agenda()
        self.datasource_resource = datasource_resource or DatasourceResource()
        self._goal_locks: dict[str, asyncio.Lock] = {}

    def register_knowledge_source(self, source: KnowledgeSource) -> None:
        self.registry.register(source)

    def subscribe(self, callback):
        return self.event_bus.subscribe(callback)

    def set_datasource(self, datasource) -> None:
        self.datasource_resource.set(datasource)

    async def replace_datasource(self, datasource) -> None:
        """Swap the active datasource without interrupting in-flight work.

        Waits for write/search resource locks, then swaps the shared resource.
        The previous datasource is closed best-effort after the swap.
        """
        previous = self.datasource_resource.datasource
        async with self.resources.acquire(["datasource_write", "search"]):
            self.datasource_resource.set(datasource)
        if previous is not None and previous is not datasource:
            close = getattr(previous, "close", None)
            if close is not None:
                try:
                    await close()
                except Exception as exc:  # noqa: BLE001
                    log.warning("datasource.close_failed", name=previous.name, reason=str(exc))

    async def submit_import(
        self,
        goal_id: str,
        *,
        file_path: str,
        parser: str,
        mime: str | None = None,
        size: int | None = None,
    ) -> list[BlackboardEntry]:
        entry = BlackboardEntry(
            goal_id=goal_id,
            kind=EntryKind.IMPORT_JOB.value,
            status="ready",
            payload={
                "file_path": file_path,
                "parser": parser,
                "mime": mime,
                "size": size,
            },
        )
        await self.blackboard.apply_patch(Patch(upserts=[entry]))
        await self.run_goal(goal_id)
        return self.blackboard.snapshot(goal_id)

    async def submit_search(
        self,
        goal_id: str,
        *,
        query: str,
        top_k: int = 5,
        filter: dict[str, Any] | None = None,
    ) -> list[BlackboardEntry]:
        entry = BlackboardEntry(
            goal_id=goal_id,
            kind=EntryKind.SEARCH_JOB.value,
            status="ready",
            payload={"query": query, "top_k": top_k, "filter": filter},
        )
        await self.blackboard.apply_patch(Patch(upserts=[entry]))
        await self.run_goal(goal_id)
        return self.blackboard.snapshot(goal_id)

    async def submit_browse(
        self,
        goal_id: str,
        *,
        document_id: str | None = None,
        parser: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[BlackboardEntry]:
        entry = BlackboardEntry(
            goal_id=goal_id,
            kind=EntryKind.BROWSE_REQUEST.value,
            status="ready",
            payload={
                "document_id": document_id,
                "parser": parser,
                "offset": offset,
                "limit": limit,
            },
        )
        await self.blackboard.apply_patch(Patch(upserts=[entry]))
        await self.run_goal(goal_id)
        return self.blackboard.snapshot(goal_id)

    async def run_goal(self, goal_id: str, max_steps: int = 100) -> None:
        lock = self._goal_locks.setdefault(goal_id, asyncio.Lock())
        async with lock:
            for _ in range(max_steps):
                await self._cancel_stale(goal_id)
                candidates = await self._candidates(goal_id)
                if not candidates:
                    return
                self._raise_on_conflict(candidates)
                for item in candidates:
                    self.agenda.add(item)

                item = self.scheduler.choose(self.agenda, goal_id, self.resources)
                if item is None:
                    return
                self.agenda.mark(item.agenda_id, "running")
                source = self.registry.get(item.ks_id)
                entry = self.blackboard.get(item.entry_id)
                if entry is None:
                    self.agenda.mark(item.agenda_id, "failed")
                    continue

                try:
                    async with self.resources.acquire(item.required_resources):
                        patch = await source.execute(entry, self.blackboard)
                    if patch is not None:
                        await self.blackboard.apply_patch(patch)
                    self.agenda.mark(item.agenda_id, "done")
                except Exception as exc:  # noqa: BLE001
                    self.agenda.mark(item.agenda_id, "failed")
                    await self._mark_entry_failed(entry, exc)
                    raise
            raise RuntimeError(f"blackboard goal {goal_id} exceeded max_steps")

    async def _candidates(self, goal_id: str) -> list[AgendaItem]:
        out: list[AgendaItem] = []
        for entry in self.blackboard.find(goal_id):
            if entry.status in {"done", "failed", "cancelled"}:
                continue
            for source in await self.registry.enabled(entry, self.blackboard):
                descriptor = source.descriptor
                out.append(
                    AgendaItem(
                        goal_id=goal_id,
                        entry_id=entry.entry_id,
                        ks_id=descriptor.ks_id,
                        priority=descriptor.priority,
                        required_resources=list(descriptor.required_resources),
                    )
                )
        return out

    def _raise_on_conflict(self, candidates: list[AgendaItem]) -> None:
        by_slot: dict[tuple[str, str], AgendaItem] = {}
        for item in candidates:
            key = (item.goal_id, item.entry_id)
            previous = by_slot.get(key)
            if previous is not None and previous.priority == item.priority:
                for candidate in candidates:
                    if (candidate.goal_id, candidate.entry_id) == key:
                        self.agenda.mark(candidate.agenda_id, "conflict")
                raise KnowledgeSourceConflictError(
                    f"knowledge source conflict for {key}: "
                    f"{previous.ks_id} and {item.ks_id} both claim priority {item.priority}"
                )
            by_slot[key] = item

    async def _mark_entry_failed(self, entry: BlackboardEntry, exc: Exception) -> None:
        failed = entry.model_copy(update={"status": "failed", "error": str(exc)})
        try:
            await self.blackboard.apply_patch(
                Patch(upserts=[failed], expected_revisions={entry.entry_id: entry.revision})
            )
        except BlackboardConflictError:
            # A newer state already won; keep it and let the scheduler re-evaluate.
            return

    async def _cancel_stale(self, goal_id: str) -> None:
        for item in self.agenda.ready(goal_id):
            entry = self.blackboard.get(item.entry_id)
            if entry is None:
                item.status = "cancelled"
                continue
            source = self.registry.get(item.ks_id)
            enabled = False
            for candidate in await self.registry.enabled(entry, self.blackboard):
                if candidate is source:
                    enabled = True
                    break
            if not enabled:
                item.status = "cancelled"
