"""Helpers shared by all parsers."""
from __future__ import annotations

from pathlib import Path
from typing import IO


def open_binary(path: str | Path) -> IO[bytes]:
    """Open a file for binary read; used by parsers."""
    return Path(path).open("rb")


def detect_mime(path: str | Path) -> str:
    """Lightweight MIME detection by extension."""
    ext = Path(path).suffix.lower()
    return {
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".pdf": "application/pdf",
        ".md": "text/markdown",
        ".markdown": "text/markdown",
        ".txt": "text/plain",
    }.get(ext, "application/octet-stream")