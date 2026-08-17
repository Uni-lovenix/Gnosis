"""Mutable shared resources consumed by knowledge sources."""
from __future__ import annotations

from dataclasses import dataclass

from app.datasources.base import DataSource


class ResourceUnavailableError(RuntimeError):
    pass


@dataclass
class DatasourceResource:
    """Mutable active datasource holder used by write/retrieval/browse KS."""

    datasource: DataSource | None = None

    def get(self) -> DataSource:
        if self.datasource is None:
            raise ResourceUnavailableError("no active datasource configured")
        return self.datasource

    def set(self, datasource: DataSource | None) -> None:
        self.datasource = datasource

