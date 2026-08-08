"""End-to-end tests for /v1/datasources/configs* endpoints.

We bypass ``create_app()``'s module-level singleton by setting up a TestClient
on a fresh FastAPI app instance, then inject a per-test DatasourceStore so
tests remain isolated even if ``main.app`` is reused by another test.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import datasources as datasources_api
from app.api import search as search_api
from app.main import _build_default_components
from app.observability.datasource_store import DatasourceStore


@pytest.fixture
def client_with_store(tmp_path: Path) -> TestClient:
    """Fresh app per test; DatasourceStore pointed at a tmp datasources.json."""
    store = DatasourceStore(tmp_path / "datasources.json")

    app = FastAPI(title="test")
    # Wire only the router under test (no embedder / pipeline needed).
    datasources_api.set_store(store)
    app.include_router(datasources_api.router)

    with TestClient(app) as c:
        yield c


def test_upsert_then_list(client_with_store: TestClient) -> None:
    r = client_with_store.post(
        "/v1/datasources/configs",
        json={"name": "vec-local", "type": "vector", "options": {"backend": "memory", "dim": 64}},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "vec-local"
    assert body["type"] == "vector"
    assert body["saved_at"]

    r = client_with_store.get("/v1/datasources/configs")
    assert r.status_code == 200
    names = [c["name"] for c in r.json()]
    assert names == ["vec-local"]


def test_upsert_rejects_unknown_type(client_with_store: TestClient) -> None:
    r = client_with_store.post(
        "/v1/datasources/configs",
        json={"name": "x", "type": "madeup", "options": {}},
    )
    assert r.status_code == 400
    assert "unknown datasource type" in r.json()["detail"]


def test_upsert_rejects_invalid_options(client_with_store: TestClient) -> None:
    """Postgres without dsn should fail-fast at build()."""
    r = client_with_store.post(
        "/v1/datasources/configs",
        json={"name": "bad-pg", "type": "postgresql", "options": {}},
    )
    assert r.status_code == 400


def test_upsert_replaces_existing(client_with_store: TestClient) -> None:
    client_with_store.post(
        "/v1/datasources/configs",
        json={"name": "v", "type": "vector", "options": {"backend": "memory", "dim": 32}},
    )
    r = client_with_store.post(
        "/v1/datasources/configs",
        json={"name": "v", "type": "vector", "options": {"backend": "memory", "dim": 128}},
    )
    assert r.status_code == 200
    listed = client_with_store.get("/v1/datasources/configs").json()
    assert len(listed) == 1
    assert listed[0]["options"]["dim"] == 128


def test_delete_clears_active(client_with_store: TestClient) -> None:
    client_with_store.post(
        "/v1/datasources/configs",
        json={"name": "v", "type": "vector", "options": {"backend": "memory", "dim": 32}},
    )
    client_with_store.put("/v1/datasources/active/v")
    assert client_with_store.get("/v1/datasources/active").json()["name"] == "v"
    r = client_with_store.delete("/v1/datasources/configs/v")
    assert r.status_code == 200
    assert client_with_store.get("/v1/datasources/active").json()["name"] is None


def test_activate_unknown_returns_404(client_with_store: TestClient) -> None:
    r = client_with_store.put("/v1/datasources/active/missing")
    assert r.status_code == 404


def test_active_round_trip(client_with_store: TestClient) -> None:
    assert client_with_store.get("/v1/datasources/active").json()["name"] is None
    client_with_store.post(
        "/v1/datasources/configs",
        json={"name": "v1", "type": "vector", "options": {"backend": "memory", "dim": 32}},
    )
    r = client_with_store.put("/v1/datasources/active/v1")
    assert r.status_code == 200
    assert r.json()["name"] == "v1"
    assert client_with_store.get("/v1/datasources/active").json()["name"] == "v1"
    r = client_with_store.delete("/v1/datasources/active")
    assert r.status_code == 200
    assert client_with_store.get("/v1/datasources/active").json()["name"] is None


def test_startup_loads_active_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When the active config points at an in-memory vector, the next server
    start should pick it up as the default datasource.

    We stub ``app.main.settings`` directly because it has been resolved at
    module import time; rebuilding ``app.config.settings`` would not replace
    the binding in the already-imported ``app.main`` module.
    """
    store = DatasourceStore(tmp_path / "datasources.json")
    store.upsert(name="mem", type="vector", options={"backend": "memory", "dim": 32})
    store.activate("mem")
    datasources_api.set_store(store)

    # Replace the module-level settings object so ``_build_default_components``
    # reads ``data_dir`` from our tmp dir.
    from app import main as main_mod
    from app.config.settings import Settings

    fake = main_mod.settings.model_copy(update={"data_dir": str(tmp_path)})
    monkeypatch.setattr(main_mod, "settings", fake)

    embedder, ds = main_mod._build_default_components()
    assert ds is not None
    assert ds.name == "mem"
    if hasattr(ds, "close"):
        ds.close()
