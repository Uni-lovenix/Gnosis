"""Document parsing knowledge source."""
from __future__ import annotations

from pathlib import Path

from app.blackboard.core import Blackboard, BlackboardEntry, Patch
from app.blackboard.registry import KSDescriptor, KnowledgeSource
from app.blackboard.vocabulary import EntryKind
from app.parsers import parse_excel, parse_markdown, parse_pdf, parse_word


_PARSERS = {
    "excel": parse_excel,
    "word": parse_word,
    "pdf": parse_pdf,
    "markdown": parse_markdown,
}


def build_parser(parser_name: str):
    if parser_name not in _PARSERS:
        raise ValueError(f"unknown parser: {parser_name}")
    return _PARSERS[parser_name]


class ParseFileKS(KnowledgeSource):
    descriptor = KSDescriptor(
        ks_id="parse_file",
        description="Parse a staged file into a ParsedDocument.",
        consumes=(EntryKind.IMPORT_JOB.value,),
        produces=(EntryKind.PARSED_DOCUMENT.value,),
        required_resources=("parser",),
        priority=10,
    )

    async def can_handle(self, entry: BlackboardEntry, blackboard: Blackboard) -> bool:
        if entry.kind != EntryKind.IMPORT_JOB.value:
            return False
        if blackboard.find(entry.goal_id, kind=EntryKind.PARSED_DOCUMENT.value):
            return False
        return entry.status == "ready"

    async def execute(self, entry: BlackboardEntry, blackboard: Blackboard) -> Patch:
        parser = build_parser(entry.payload["parser"])
        doc = parser(Path(entry.payload["file_path"]))
        parsed = BlackboardEntry(
            goal_id=entry.goal_id,
            kind=EntryKind.PARSED_DOCUMENT.value,
            status="ready",
            payload={
                "document_id": doc.id,
                "source_path": doc.source_path,
                "mime": doc.mime,
                "text": doc.text,
                "metadata": doc.metadata,
            },
        )
        patch = Patch()
        patch.add(parsed)
        patch.add(
            entry.model_copy(update={"status": "processing"}),
            expected_revision=entry.revision,
        )
        return patch

