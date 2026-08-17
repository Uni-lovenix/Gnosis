"""Tests for /v1/backups list/create endpoints (C11)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_backups_list_and_create(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    backup_root = tmp_path / "backups"
    data_dir.mkdir()
    monkeypatch.setenv("KB_DATA_DIR", str(data_dir))
    monkeypatch.setenv("KB_BACKUP_DIR", str(backup_root))

    client = TestClient(create_app())
    r = client.post("/v1/backups")
    assert r.status_code == 201
    body = r.json()
    assert body["name"].startswith("kb-backup-")
    assert body["path"].startswith(str(backup_root))

    r2 = client.get("/v1/backups")
    assert r2.status_code == 200
    assert [item["name"] for item in r2.json()] == [body["name"]]
