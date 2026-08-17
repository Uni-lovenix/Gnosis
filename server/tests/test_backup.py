"""Tests for the data-directory backup helper (C10)."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import pytest

from app.observability.backup import (
    backup_data_dir,
    backup_if_due,
    latest_backup,
    list_backups,
    restore_backup,
)


def _make_data(src) -> None:
    src.mkdir(parents=True, exist_ok=True)
    (src / "datasources.json").write_text(
        json.dumps({"version": 1, "active": None, "configs": []}),
        encoding="utf-8",
    )
    conn = sqlite3.connect(src / "tasks.db")
    conn.execute("CREATE TABLE tasks (task_id TEXT PRIMARY KEY, status TEXT)")
    conn.execute("INSERT INTO tasks VALUES ('t1', 'done')")
    conn.commit()
    conn.close()


def test_backup_copies_json_and_sqlite_snapshot(tmp_path):
    src = tmp_path / "data"
    root = tmp_path / "backups"
    _make_data(src)

    dest = backup_data_dir(src, root, keep=2)

    assert dest.name.startswith("kb-backup-")
    assert (dest / "datasources.json").exists()
    assert (dest / "manifest.json").exists()
    manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["files"]) == {"datasources.json", "tasks.db"}

    conn = sqlite3.connect(dest / "tasks.db")
    try:
        assert conn.execute("SELECT status FROM tasks WHERE task_id='t1'").fetchone() == ("done",)
    finally:
        conn.close()


def test_backup_skips_temp_and_journal_files(tmp_path):
    src = tmp_path / "data"
    root = tmp_path / "backups"
    _make_data(src)
    (src / "tasks.db-journal").write_text("partial", encoding="utf-8")
    (src / "datasources.json.tmp").write_text("partial", encoding="utf-8")

    dest = backup_data_dir(src, root, keep=2)

    assert not (dest / "tasks.db-journal").exists()
    assert not (dest / "datasources.json.tmp").exists()


def test_backup_prunes_old_snapshots(tmp_path):
    src = tmp_path / "data"
    root = tmp_path / "backups"
    _make_data(src)

    first = backup_data_dir(src, root, keep=2)
    backup_data_dir(src, root, keep=2)
    third = backup_data_dir(src, root, keep=2)

    backups = sorted(p for p in root.iterdir() if p.is_dir())
    assert len(backups) == 2
    assert third in backups
    assert first not in backups


def test_list_backups_returns_manifest_summary(tmp_path):
    src = tmp_path / "data"
    root = tmp_path / "backups"
    _make_data(src)

    dest = backup_data_dir(src, root, keep=2)
    snapshots = list_backups(root)

    assert len(snapshots) == 1
    assert snapshots[0]["name"] == dest.name
    assert snapshots[0]["path"] == str(dest)
    assert set(snapshots[0]["files"]) == {"datasources.json", "tasks.db"}
    assert snapshots[0]["source"] == str(src)


def test_restore_backup_restores_and_keeps_pre_restore(tmp_path):
    src = tmp_path / "data"
    root = tmp_path / "backups"
    _make_data(src)
    dest = backup_data_dir(src, root, keep=2)

    conn = sqlite3.connect(src / "tasks.db")
    conn.execute("INSERT INTO tasks VALUES ('t2', 'failed')")
    conn.commit()
    conn.close()
    (src / "datasources.json").write_text(
        json.dumps({"version": 1, "active": "later", "configs": []}),
        encoding="utf-8",
    )

    result = restore_backup(dest, src)

    assert set(result["restored_files"]) == {"datasources.json", "tasks.db"}
    pre = Path(result["pre_restore"])
    assert pre.is_dir()

    conn = sqlite3.connect(src / "tasks.db")
    try:
        rows = conn.execute("SELECT task_id, status FROM tasks ORDER BY task_id").fetchall()
    finally:
        conn.close()
    assert rows == [("t1", "done")]
    data = json.loads((src / "datasources.json").read_text(encoding="utf-8"))
    assert data["active"] is None

    pre_conn = sqlite3.connect(pre / "tasks.db")
    try:
        pre_rows = pre_conn.execute("SELECT task_id, status FROM tasks ORDER BY task_id").fetchall()
    finally:
        pre_conn.close()
    assert pre_rows == [("t1", "done"), ("t2", "failed")]


def test_restore_rejects_non_backup_directory(tmp_path):
    src = tmp_path / "data"
    _make_data(src)
    with pytest.raises(ValueError, match="not a kb backup directory"):
        restore_backup(src, tmp_path / "target")


def test_latest_backup_returns_newest_snapshot(tmp_path):
    src = tmp_path / "data"
    root = tmp_path / "backups"
    _make_data(src)
    assert latest_backup(root) is None

    first = backup_data_dir(src, root, keep=2)
    second = backup_data_dir(src, root, keep=2)

    latest = latest_backup(root)
    assert latest is not None
    assert latest["path"] == str(second)
    assert latest["path"] != str(first)


def test_backup_if_due_creates_when_no_backup(tmp_path):
    src = tmp_path / "data"
    root = tmp_path / "backups"
    _make_data(src)

    created, path = backup_if_due(src, root, keep=2, interval_hours=24)
    assert created is True
    assert path is not None
    assert path.is_dir()


def test_backup_if_due_skips_fresh_snapshot(tmp_path):
    src = tmp_path / "data"
    root = tmp_path / "backups"
    _make_data(src)
    dest = backup_data_dir(src, root, keep=2)

    created, path = backup_if_due(src, root, keep=2, interval_hours=24, now=time.time())
    assert created is False
    assert path == dest


def test_backup_if_due_creates_after_interval(tmp_path):
    src = tmp_path / "data"
    root = tmp_path / "backups"
    _make_data(src)
    first = backup_data_dir(src, root, keep=2)

    created, path = backup_if_due(
        src,
        root,
        keep=2,
        interval_hours=24,
        now=time.time() + 25 * 3600,
    )
    assert created is True
    assert path is not None
    assert path != first
