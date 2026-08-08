"""PDF parser: pdfplumber (text layer only).

We deliberately do not perform OCR in this iteration. Scanned PDFs return
empty text; the API surfaces this as a partial failure with an explicit
``ocr_required: True`` flag in metadata.
"""
from __future__ import annotations

from pathlib import Path

from app.observability.models import Document
from app.parsers._common import detect_mime


def parse_pdf(path: str | Path) -> Document:
    try:
        import pdfplumber  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "pdfplumber not installed. `pip install -e '.[parsers]'`."
        ) from e

    p = Path(path)
    parts: list[str] = []
    page_count = 0
    with pdfplumber.open(str(p)) as pdf:
        for i, page in enumerate(pdf.pages):
            page_count += 1
            text = page.extract_text() or ""
            if text.strip():
                parts.append(f"## Page {i + 1}\n{text.strip()}\n")

    text = "\n".join(parts).strip()
    return Document(
        source_path=str(p),
        mime=detect_mime(p),
        text=text,
        metadata={
            "parser": "pdf",
            "pages": page_count,
            "ocr_required": text == "",
            "size": p.stat().st_size,
        },
    )