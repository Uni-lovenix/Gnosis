"""Knowledge source descriptors, protocol and dynamic registry."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.blackboard.core import Blackboard, BlackboardEntry, Patch
from app.blackboard.vocabulary import VocabularyError


@dataclass(frozen=True)
class KSDescriptor:
    """Declarative metadata used for discovery and scheduling."""

    ks_id: str
    description: str = ""
    consumes: tuple[str, ...] = ()
    produces: tuple[str, ...] = ()
    required_resources: tuple[str, ...] = ()
    priority: int = 10


class KnowledgeSource(Protocol):
    """A knowledge source only reads the blackboard and returns a Patch."""

    descriptor: KSDescriptor

    async def can_handle(
        self,
        entry: BlackboardEntry,
        blackboard: Blackboard,
    ) -> bool: ...

    async def execute(
        self,
        entry: BlackboardEntry,
        blackboard: Blackboard,
    ) -> Patch | None: ...


class KnowledgeSourceRegistry:
    """Runtime registry with registration/discovery and vocabulary checks."""

    def __init__(
        self,
        vocabulary,
        known_resources: set[str] | None = None,
    ) -> None:
        self._vocabulary = vocabulary
        self._known_resources = known_resources or {
            "parser",
            "chunker",
            "embedder",
            "datasource_write",
            "search",
            "llm",
        }
        self._sources: dict[str, KnowledgeSource] = {}

    def register(self, source: KnowledgeSource) -> None:
        descriptor = source.descriptor
        if descriptor.ks_id in self._sources:
            raise ValueError(f"knowledge source already registered: {descriptor.ks_id}")
        for kind in descriptor.consumes + descriptor.produces:
            if not self._vocabulary.has_kind(kind):
                raise VocabularyError(
                    f"knowledge source {descriptor.ks_id} uses unknown kind {kind}"
                )
        unknown_resources = set(descriptor.required_resources) - self._known_resources
        if unknown_resources:
            raise ValueError(
                f"knowledge source {descriptor.ks_id} uses unknown resources: "
                f"{sorted(unknown_resources)}"
            )
        self._sources[descriptor.ks_id] = source

    def unregister(self, ks_id: str) -> None:
        self._sources.pop(ks_id, None)

    def get(self, ks_id: str) -> KnowledgeSource:
        if ks_id not in self._sources:
            raise KeyError(f"knowledge source not registered: {ks_id}")
        return self._sources[ks_id]

    def list(self) -> list[KnowledgeSource]:
        return sorted(self._sources.values(), key=lambda ks: ks.descriptor.ks_id)

    async def enabled(
        self,
        entry: BlackboardEntry,
        blackboard: Blackboard,
    ) -> list[KnowledgeSource]:
        out: list[KnowledgeSource] = []
        for source in self._sources.values():
            if await source.can_handle(entry, blackboard):
                out.append(source)
        return out
