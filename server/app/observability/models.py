"""Domain models shared across the server.

We define `Document`, `Chunk`, `Hit` as plain pydantic models so they can be
serialized to JSON for IPC and HTTP. Keep them dependency-free.
"""
from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def new_id() -> str:
    """Generate a short id used for documents, chunks, and tasks."""
    return uuid4().hex[:16]


class Document(BaseModel):
    """A parsed file before chunking."""

    id: str = Field(default_factory=new_id)
    source_path: str
    mime: str = ""
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    """A chunk of text ready for embedding and indexing."""

    id: str = Field(default_factory=new_id)
    document_id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    # Filled in after embedding.
    vector: list[float] | None = None


class Hit(BaseModel):
    """A search result."""

    id: str
    score: float
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    document_id: str | None = None


class ChunkSummary(BaseModel):
    """Lightweight view of a stored chunk for browse / inspection UIs.

    ``text`` is server-side truncated to 240 chars (with an ellipsis) to
    keep the browse payload bounded; ``text_length`` carries the full size
    so the UI can show "240 / 1.4k chars" hints.
    """

    chunk_id: str
    document_id: str
    text: str
    text_length: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentSummary(BaseModel):
    """One entry in the per-document rollup returned by the browse endpoint.

    ``chunk_count`` is the total number of chunks stored under this
    ``document_id`` (across the whole index, not just the current page);
    ``parsers`` lists distinct parser values seen; ``first_chunk_id`` is
    convenient for "jump to source"; ``sample_text`` is the first chunk's
    text, also truncated.
    """

    document_id: str
    chunk_count: int
    parsers: list[str] = Field(default_factory=list)
    first_chunk_id: str | None = None
    sample_text: str = ""


class TaskStage(str, Enum):
    """Pipeline stage labels emitted by the import pipeline.

    The renderer maps these to human-readable text and a colored tag.
    New stages should be appended (never reorder) so existing persisted
    events keep their meaning across releases.
    """

    QUEUED = "queued"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    WRITING = "writing"
    DONE = "done"
    FAILED = "failed"


class TaskEvent(BaseModel):
    """One row in the per-task rolling event log."""

    ts: str          # ISO-8601 UTC, same format as TaskStore._now()
    stage: TaskStage
    progress: float
    message: str


class TaskStatus(BaseModel):
    """Background task state.

    ``stage`` is the latest pipeline stage; ``events`` is a short ring buffer
    of the most recent stage transitions so the renderer can show "what's
    happening" alongside the progress bar.
    """

    task_id: str
    kind: str  # "import" | "search" | ...
    status: str  # "queued" | "running" | "done" | "failed"
    progress: float = 0.0
    stage: TaskStage = TaskStage.QUEUED
    events: list[TaskEvent] = Field(default_factory=list)
    error: str | None = None
    result: dict[str, Any] | None = None
