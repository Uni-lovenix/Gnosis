"""Tests for /v1/health and /v1/health/ready (C10)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import health as health_api
from app.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_health_reports_ok_startup_facts(client):
    r = client.get("/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["degraded"] is False
    assert body["embedder_backend"] == "mock-hash"
    assert body["embedder_fallback"] is False
    assert body["active_datasource"]["name"] == "default"
    assert body["active_datasource"]["type"] == "vector"
    assert body["uptime_seconds"] >= 0
    assert body["started_at"].endswith("+00:00")


def test_health_reports_degraded_when_components_missing(client, monkeypatch):
    monkeypatch.setattr(
        health_api,
        "_runtime",
        health_api.RuntimeState(
            embedder_backend="mock-hash",
            embedder_fallback=True,
            datasource=None,
            datasource_source="none",
        ),
    )
    r = client.get("/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "degraded"
    assert body["degraded"] is True
    assert body["active_datasource"] is None


def test_ready_reports_all_dependency_checks(client):
    r = client.get("/v1/health/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert body["degraded"] is False
    names = {c["name"] for c in body["checks"]}
    assert names == {"server", "datasource", "embedder"}
    assert all(c["ok"] for c in body["checks"])


def test_ready_marks_datasource_failure(client, monkeypatch):
    from app.datasources.base import HealthStatus

    class _BadDatasource:
        name = "bad"
        type = "vector"

        async def health(self):
            return HealthStatus(ok=False, message="backend unreachable")

    monkeypatch.setattr(health_api._runtime, "datasource", _BadDatasource())
    monkeypatch.setattr(health_api, "_probe_cache", None)
    r = client.get("/v1/health/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "degraded"
    ds_check = next(c for c in body["checks"] if c["name"] == "datasource")
    assert ds_check["ok"] is False
    assert "backend unreachable" in ds_check["message"]


def test_ready_refreshes_health_snapshot(client):
    ready = client.get("/v1/health/ready")
    assert ready.status_code == 200

    r = client.get("/v1/health")
    body = r.json()
    assert body["degraded"] is False
    assert body["embedder_ok"] is True
    assert body["active_datasource"]["ok"] is True
    assert body["last_probe_at"] is not None


def test_health_reports_live_datasource_failure(client, monkeypatch):
    monkeypatch.setattr(
        health_api._runtime,
        "datasource_ok",
        False,
    )
    monkeypatch.setattr(
        health_api._runtime,
        "datasource_message",
        "backend unreachable",
    )
    r = client.get("/v1/health")
    body = r.json()
    assert body["status"] == "degraded"
    assert body["degraded"] is True
    assert body["active_datasource"]["ok"] is False
    assert body["active_datasource"]["message"] == "backend unreachable"
