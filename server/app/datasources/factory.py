"""Factory: turn a DatasourceConfig into a live adapter instance."""
from __future__ import annotations

from app.datasources.base import DataSource, DatasourceConfig, get_datasource_cls


def build(config: DatasourceConfig) -> DataSource:
    cls = get_datasource_cls(config.type)
    return cls(config)