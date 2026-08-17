"""Tests for GET /v1/settings/ha (G18)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_ha_settings_returns_effective_values():
    client = TestClient(create_app())
    r = client.get("/v1/settings/ha")
    assert r.status_code == 200
    body = r.json()
    assert body["backup_auto"] is False  # conftest pins this off in tests
    assert body["backup_interval_hours"] == 24.0
    assert body["backup_keep"] == 7
    assert body["health_monitor"] is False  # conftest pins this off in tests
    assert body["health_monitor_interval_seconds"] == 30
    assert body["failover_enabled"] is False  # conftest pins this off in tests
    assert body["failover_consecutive_failures"] == 2
    assert body["failover_auto_recover"] is False  # conftest pins this off in tests
    assert body["failover_recover_consecutive_checks"] == 3


def test_ha_settings_reflects_env_overrides(monkeypatch):
    monkeypatch.setenv("KB_BACKUP_INTERVAL_HOURS", "12")
    monkeypatch.setenv("KB_FAILOVER_CONSECUTIVE_FAILURES", "4")
    monkeypatch.setenv("KB_HEALTH_MONITOR_INTERVAL_SECONDS", "45")
    client = TestClient(create_app())
    body = client.get("/v1/settings/ha").json()
    assert body["backup_interval_hours"] == 12.0
    assert body["failover_consecutive_failures"] == 4
    assert body["health_monitor_interval_seconds"] == 45
