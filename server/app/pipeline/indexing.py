"""Indexing pipeline: parse → chunk → embed → write to datasource.

This module orchestrates the work; it does not own parsers/embedders/data-
sources directly but receives them via constructor injection. The pipeline
runs synchronously in this iteration; the files API invokes it inside the
request handler and writes progress to the task store.

The ``on_progress`` callback receives a ``ProgressEvent`` (stage, progress,
message) so the renderer can show *what* is happening, not just *how far*.
A legacy float-only callback can still be plugged in by wrapping it in a
``ProgressEvent``-compatible function; the files API in this iteration does
exactly that when wiring the callback into the task store.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Union

from app.chunking import ChunkParams, TextChunker
from app.datasources.base import DataSource
from app.embedding.base import Embedder
from app.observability.models import Document


@dataclass
class ProgressEvent:
    """One stage transition emitted by ``IndexingPipeline``.

    ``stage`` is one of the values from ``TaskStage`` (``parsing``,
    ``chunking``, ``embedding``, ``writing``); ``progress`` is the fraction
    of the whole pipeline; ``message`` is a short human-readable hint
    suitable for surfacing in the UI ("parsing README.md", "32/240 chunks
    embedded", etc.).
    """

    stage: str
    progress: float
    message: str = ""


# A callback can either accept a single ``ProgressEvent`` (preferred) or a
# bare ``float`` for backward compatibility with old callers / tests.
ProgressCallback = Callable[[Union[ProgressEvent, float]], None]


@dataclass
class IndexResult:
    document_id: str
    chunks: int
    embedded: int
    written: int


class IndexingPipeline:
    def __init__(
        self,
        datasource: DataSource,
        embedder: Embedder,
        chunker: TextChunker | None = None,
        embed_batch_size: int = 32,
        on_progress: ProgressCallback | None = None,
    ) -> None:
        self.datasource = datasource
        self.embedder = embedder
        self.chunker = chunker or TextChunker(ChunkParams())
        self.embed_batch_size = embed_batch_size
        # ``on_progress`` receives a ``ProgressEvent``. The single production
        # caller is ``app/api/files.py::_run_import``; tests typically pass a
        # list-collector (e.g. ``events.append``) or a no-op. Float-only
        # callbacks from before this iteration should be replaced with a
        # ``ProgressEvent``-aware callback (see ``ProgressEvent.progress``).
        self.on_progress: ProgressCallback = on_progress or (lambda _e: None)

    def _emit(self, stage: str, progress: float, message: str = "") -> None:
        self.on_progress(ProgressEvent(stage=stage, progress=progress, message=message))

    async def run(self, doc: Document) -> IndexResult:
        self._emit("parsing", 0.05, f"parsing {doc.source_path}")
        chunks = self.chunker.split(doc)
        self._emit("chunking", 0.30, f"{len(chunks)} chunks")

        if not chunks:
            return IndexResult(document_id=doc.id, chunks=0, embedded=0, written=0)

        # Embed in batches.
        total = len(chunks)
        for i in range(0, total, self.embed_batch_size):
            batch = chunks[i : i + self.embed_batch_size]
            vecs = await self.embedder.embed([c.text for c in batch])
            for c, v in zip(batch, vecs):
                c.vector = v
            done = i + len(batch)
            frac = min(1.0, done / total)
            self._emit(
                "embedding",
                0.30 + 0.50 * frac,
                f"{done}/{total} chunks embedded",
            )

        ids = await self.datasource.add(chunks)
        self._emit("writing", 1.0, f"wrote {len(ids)} chunks")
        return IndexResult(
            document_id=doc.id,
            chunks=total,
            embedded=total,
            written=len(ids),
        )