"""Markdown parser: markdown-it-py (tokens) → Document.

We strip front-matter, preserve headings and code fences. The text is the
raw markdown source with front-matter removed; downstream chunker is
format-aware enough to split on heading boundaries when present.
"""
from __future__ import annotations

from pathlib import Path

from app.observability.models import Document
from app.parsers._common import detect_mime


def parse_markdown(path: str | Path) -> Document:
    try:
        from markdown_it import MarkdownIt  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "markdown-it-py not installed. `pip install -e '.[parsers]'`."
        ) from e

    p = Path(path)
    raw = p.read_text(encoding="utf-8", errors="replace")
    raw = _strip_front_matter(raw)
    md = MarkdownIt("commonmark").enable("table")
    env: dict = {}
    tokens = md.parse(raw, env)

    # We could render to HTML here, but for embedding we want raw markdown to
    # retain semantics. Just count headings as metadata and pass text through.
    headings = [t for t in tokens if t.type == "heading_open"]
    h2_count = sum(1 for t in tokens if t.type == "heading_open" and t.tag == "h2")

    return Document(
        source_path=str(p),
        mime=detect_mime(p),
        text=raw,
        metadata={
            "parser": "markdown",
            "headings": len(headings),
            "h2": h2_count,
            "size": p.stat().st_size,
        },
    )


def _strip_front_matter(text: str) -> str:
    """Remove YAML front-matter if present."""
    if not text.startswith("---"):
        return text
    lines = text.splitlines(keepends=True)
    if not lines or not lines[0].startswith("---"):
        return text
    end = None
    for i in range(1, len(lines)):
        if lines[i].startswith("---"):
            end = i
            break
    if end is None:
        return text
    return "".join(lines[end + 1 :]).lstrip("\n")