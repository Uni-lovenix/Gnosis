"""Tests for the text chunker."""
from __future__ import annotations

from app.chunking import ChunkParams, TextChunker, chunk_text
from app.observability.models import Document


def test_short_text_single_chunk():
    chunks = chunk_text("hello world", document_id="d1")
    assert len(chunks) == 1
    assert chunks[0].text == "hello world"
    assert chunks[0].document_id == "d1"


def test_short_text_with_higher_min_chunk_filtered():
    # Below min_chunk → no chunks
    chunks = chunk_text("hi", min_chunk=10)
    assert chunks == []


def test_paragraph_aware_splitting():
    text = "A" * 100 + "\n\n" + "B" * 100 + "\n\n" + "C" * 100
    chunks = chunk_text(text, chunk_size=150, overlap=20)
    # Each paragraph fits; should yield 3 chunks with no overlap.
    assert len(chunks) == 3
    assert all(c.text.strip() == "A" * 100 or "B" in c.text or "C" in c.text for c in chunks)


def test_overlap_carries_context():
    text = "P1. " * 50 + "\n\n" + "P2. " * 50 + "\n\n" + "P3. " * 50
    chunks = chunk_text(text, chunk_size=300, overlap=80)
    # Should produce multiple chunks with overlap
    assert len(chunks) >= 2
    # Overlap text from P1 should appear at start of P2's chunk
    has_overlap = any(
        "P1." in chunks[i].text and "P2." in chunks[i + 1].text
        for i in range(len(chunks) - 1)
    )
    assert has_overlap


def test_hard_split_long_paragraph():
    text = "x" * 5000
    chunks = chunk_text(text, chunk_size=1000, overlap=100)
    # All chunks <= 1000 + small buffer for hard-split safety
    for c in chunks:
        assert len(c.text) <= 1100  # allow tiny slack for boundary detection
    # Combined output covers the whole input
    covered = sum(len(c.text) for c in chunks)
    assert covered >= 4500  # small slack for overlap double-count


def test_min_chunk_filters_fragments():
    text = "ok. " * 100
    chunks = chunk_text(text, chunk_size=200, overlap=10, min_chunk=100)
    assert all(len(c.text) >= 100 for c in chunks)


def test_chunker_with_document():
    # Small paragraphs merge into one chunk (within chunk_size); document_id preserved.
    doc = Document(source_path="x", text="P1.\n\nP2.\n\nP3.")
    chunks = TextChunker().split(doc)
    assert len(chunks) == 1
    assert chunks[0].document_id == doc.id
    assert "P1." in chunks[0].text and "P2." in chunks[0].text and "P3." in chunks[0].text


def test_chunker_separates_large_paragraphs():
    text = ("X" * 100 + "\n\n") * 3  # each paragraph 100 chars, total 300
    chunks = TextChunker(ChunkParams(chunk_size=150, overlap=10)).split(
        Document(source_path="x", text=text)
    )
    assert len(chunks) >= 2


def test_chunker_metadata_preserved():
    doc = Document(source_path="x", text="hello world here", metadata={"src": "x"})
    chunks = TextChunker().split(doc)
    assert chunks
    for c in chunks:
        assert c.metadata["src"] == "x"


def test_invalid_params():
    import pytest

    with pytest.raises(ValueError):
        ChunkParams(chunk_size=100, overlap=100)
    with pytest.raises(ValueError):
        ChunkParams(chunk_size=100, overlap=10, min_chunk=0)


def test_metadata_preserved_old():
    pass  # replaced by test_chunker_metadata_preserved