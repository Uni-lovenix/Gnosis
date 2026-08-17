"""Blackboard vocabulary: the canonical set of entry kinds and statuses.

Every knowledge source declares ``consumes`` and ``produces`` kinds that
must exist here before registration. Keeping the vocabulary centralized makes
the blackboard's interaction language explicit instead of relying on ad-hoc
payload keys spread across modules.
"""
from __future__ import annotations

from enum import Enum


class EntryKind(str, Enum):
    IMPORT_JOB = "import_job"
    PARSED_DOCUMENT = "parsed_document"
    CHUNK_SET = "chunk_set"
    ENTITY_SET = "entity_set"
    RELATION_SET = "relation_set"
    EMBEDDED_CHUNK_SET = "embedded_chunk_set"
    INDEX_RESULT = "index_result"
    SEARCH_JOB = "search_job"
    SEARCH_RESULT = "search_result"
    ANSWER = "answer"
    BROWSE_REQUEST = "browse_request"
    BROWSE_RESULT = "browse_result"
    DATASOURCE_CONFIG_STATE = "datasource_config_state"
    DATASOURCE_HEALTH_RESULT = "datasource_health_result"


ALLOWED_STATUSES = {
    "queued",
    "ready",
    "processing",
    "done",
    "failed",
    "cancelled",
}


class VocabularyError(ValueError):
    """Raised when an entry or knowledge source violates the vocabulary."""


class BlackboardVocabulary:
    """Registry of kinds understood by this blackboard instance."""

    def __init__(self) -> None:
        self._kinds = {kind.value for kind in EntryKind}

    def register_kind(self, kind: str) -> None:
        self._kinds.add(kind)

    def has_kind(self, kind: str) -> bool:
        return kind in self._kinds

    def validate_status(self, status: str) -> None:
        if status not in ALLOWED_STATUSES:
            raise VocabularyError(f"unknown blackboard status: {status}")

    def validate_entry(self, entry) -> None:
        if not self.has_kind(entry.kind):
            raise VocabularyError(f"unknown blackboard kind: {entry.kind}")
        if not isinstance(entry.payload, dict):
            raise VocabularyError(f"blackboard payload must be a dict for {entry.kind}")
        self.validate_status(entry.status)

