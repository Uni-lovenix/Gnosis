"""Text chunker.

Strategy: paragraph-aware, character-based window with overlap. We split on
paragraph boundaries when possible so chunks respect semantic structure. If a
paragraph is longer than ``chunk_size``, we hard-split on sentence/word
boundaries.

Defaults target BGE-M3 practical limits:
  - chunk_size: 1200 chars (~ 256-512 tokens depending on language)
  - overlap:    200  chars (~ 16% overlap)
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.observability.models import Chunk, Document


@dataclass
class ChunkParams:
    chunk_size: int = 1200
    overlap: int = 200
    min_chunk: int = 10  # discard fragments shorter than this

    def __post_init__(self) -> None:
        if self.overlap >= self.chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")
        if self.min_chunk < 1:
            raise ValueError("min_chunk must be ≥ 1")


class TextChunker:
    def __init__(self, params: ChunkParams | None = None) -> None:
        self.params = params or ChunkParams()

    def split(self, doc: Document) -> list[Chunk]:
        paragraphs = _split_paragraphs(doc.text)
        chunks: list[Chunk] = []
        buf = ""
        for p in paragraphs:
            # If adding the next paragraph fits, append; otherwise flush.
            if buf and len(buf) + 1 + len(p) > self.params.chunk_size:
                chunks.extend(self._flush(buf, doc.id, doc.metadata))
                buf = _carry_overlap(buf, self.params.overlap)
            buf = (buf + "\n" + p).strip() if buf else p
        if buf:
            chunks.extend(self._flush(buf, doc.id, doc.metadata))
        return [c for c in chunks if len(c.text) >= self.params.min_chunk]

    # ---- internals ----------------------------------------------------------

    def _flush(self, text: str, document_id: str, doc_meta: dict) -> list[Chunk]:
        """Slice a buffer into chunks of <= chunk_size (hard split on long text)."""
        if len(text) <= self.params.chunk_size:
            return [Chunk(document_id=document_id, text=text, metadata=dict(doc_meta))]
        out: list[Chunk] = []
        i = 0
        n = len(text)
        while i < n:
            end = min(i + self.params.chunk_size, n)
            if end < n:
                # try to back off to a sentence/word boundary
                end = _find_break(text, end, hard_min=i + self.params.chunk_size // 2)
            piece = text[i:end].strip()
            if piece:
                out.append(Chunk(document_id=document_id, text=piece, metadata=dict(doc_meta)))
            if end == i:
                break
            i = max(end - self.params.overlap, i + 1)
        return out


# ---- helpers ---------------------------------------------------------------

_PARA_SPLIT = re.compile(r"\n\s*\n")


def _split_paragraphs(text: str) -> list[str]:
    text = text.replace("\r\n", "\n")
    paras = [p.strip() for p in _PARA_SPLIT.split(text) if p.strip()]
    return paras


def _carry_overlap(buf: str, overlap: int) -> str:
    if overlap <= 0 or len(buf) <= overlap:
        return ""
    return buf[-overlap:]


_BREAK_CHARS = "。！？!?；;\n"


def _find_break(text: str, end: int, hard_min: int) -> int:
    """Find a soft break at or before ``end``; never returns < hard_min."""
    if end >= len(text):
        return end
    for ch in _BREAK_CHARS:
        idx = text.rfind(ch, hard_min, end)
        if idx > hard_min:
            return idx + 1
    # fallback: last whitespace
    idx = text.rfind(" ", hard_min, end)
    if idx > hard_min:
        return idx + 1
    return end


# Convenience function for ad-hoc use.
def chunk_text(text: str, document_id: str = "", **kwargs) -> list[Chunk]:
    params = ChunkParams(**kwargs)
    doc = Document(id=document_id or "inline", source_path="<inline>", text=text)
    return TextChunker(params).split(doc)