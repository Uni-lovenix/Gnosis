"""DataSource abstraction and registry.

The minimum capability set is: add / search / delete / health. Adapters may
declare additional capabilities via `capabilities()`.

Adapters must be safe to import even if their optional dependency is missing;
they should raise a clear `DatasourceError` at construction time instead.
"""
from __future__ import annotations

import abc
from typing import Any, Iterable

from pydantic import BaseModel, Field

from app.observability.models import Chunk, ChunkSummary, DocumentSummary, Hit


class DatasourceError(RuntimeError):
    """Raised when an adapter cannot operate (missing dep, bad config, IO error)."""


class NotSupportedError(DatasourceError):
    """Raised when an adapter is asked to perform an operation it does not
    implement. Adapters declare what they support via ``capabilities()``;
    the API layer checks the capability and converts this error to HTTP 501.
    """


class DatasourceConfig(BaseModel):
    """Common config for any datasource.

    Adapters define their own subclass with extra fields; the base `name` is
    used as the registry key.
    """

    name: str
    type: str
    options: dict[str, Any] = Field(default_factory=dict)


class HealthStatus(BaseModel):
    ok: bool
    latency_ms: float | None = None
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class DataSource(abc.ABC):
    """Abstract vector + metadata store.

    Implementations should be idempotent on `add` (re-adding the same id
    replaces the row), and `search` must return hits ordered by descending
    score.
    """

    name: str
    type: str

    def __init__(self, config: DatasourceConfig) -> None:
        self.config = config
        self.name = config.name or self.type

    # ---- Capability reporting -------------------------------------------------

    def capabilities(self) -> set[str]:
        """Adapter-declared capabilities beyond the minimum set."""
        return set()

    # ---- Required operations --------------------------------------------------

    @abc.abstractmethod
    async def add(self, chunks: Iterable[Chunk]) -> list[str]:
        """Upsert chunks; return assigned ids (in the same order)."""

    @abc.abstractmethod
    async def search(
        self,
        vector: list[float],
        top_k: int = 5,
        filter: dict[str, Any] | None = None,
    ) -> list[Hit]:
        """Return top-k hits sorted by descending score."""

    @abc.abstractmethod
    async def delete(self, ids: Iterable[str]) -> int:
        """Delete by id; return the number actually removed."""

    @abc.abstractmethod
    async def health(self) -> HealthStatus:
        """Lightweight liveness/readiness check."""

    # ---- Optional browse helpers (G7) -----------------------------------------

    async def list_chunks(
        self,
        *,
        document_id: str | None = None,
        parser: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ChunkSummary], int]:
        """Return ``(chunks, total)`` for the browse endpoint.

        Default raises ``NotSupportedError``; only adapters that advertise
        the ``chunk_list`` capability implement this. ``total`` is the
        unpaginated match count (what the UI shows in the pagination bar).
        """
        raise NotSupportedError(f"{self.type}.list_chunks not implemented")

    async def aggregate_by_document(self) -> dict[str, DocumentSummary]:
        """Return a per-document rollup: chunk count, parsers, sample text.

        Default raises ``NotSupportedError``; only ``chunk_list``-capable
        adapters implement this. Used by the browse UI's aggregation panel.
        """
        raise NotSupportedError(
            f"{self.type}.aggregate_by_document not implemented"
        )

    # ---- Optional migration helper (C17) -------------------------------------

    async def dump_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[Chunk], int]:
        """Return full-text chunks for migration, without vector data.

        Adapters advertise the ``dump`` capability when implemented. This is
        intentionally separate from ``list_chunks`` (browse preview truncates
        text; migration needs the full text).
        """
        raise NotSupportedError(f"{self.type}.dump_all not implemented")

    # ---- Optional helpers -----------------------------------------------------

    async def close(self) -> None:  # noqa: B027
        """Release connections. Default no-op for stateless adapters."""
        return None


# ---- Registry ---------------------------------------------------------------

_REGISTRY: dict[str, type[DataSource]] = {}


def register_datasource(type_name: str, cls: type[DataSource]) -> None:
    """Register an adapter class under a type key (e.g. ``elasticsearch``)."""
    if type_name in _REGISTRY:
        raise ValueError(f"datasource type {type_name!r} already registered")
    _REGISTRY[type_name] = cls


def get_datasource_cls(type_name: str) -> type[DataSource]:
    if type_name not in _REGISTRY:
        raise DatasourceError(f"unknown datasource type: {type_name}")
    return _REGISTRY[type_name]


def list_datasource_types() -> list[str]:
    return sorted(_REGISTRY)
