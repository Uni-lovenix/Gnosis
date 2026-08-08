"""Smoke tests for the registry and factory."""
from __future__ import annotations

import pytest

from app.datasources.base import DatasourceConfig, DatasourceError, get_datasource_cls, list_datasource_types
from app.datasources.factory import build
from app.datasources.registry import all_types


def test_registry_includes_four_types():
    types = set(all_types())
    assert {"elasticsearch", "postgresql", "mysql", "vector"} <= types


def test_unknown_type_raises():
    with pytest.raises(DatasourceError):
        get_datasource_cls("nonexistent")


def test_factory_returns_instance():
    from app.datasources.vector_db_adapter import VectorDBAdapter

    cfg = DatasourceConfig(name="v", type="vector", options={"backend": "memory", "dim": 4})
    ds = build(cfg)
    assert isinstance(ds, VectorDBAdapter)