"""Tests for the SQLite task store."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.observability.models import TaskStage
from app.observability.task_store import TaskStore, _EVENTS_KEEP


def test_create_get_update(tmp_path: Path):
    store = TaskStore(tmp_path / "tasks.db")
    t = store.create("t1", "import")
    assert t.status == "queued"
    assert t.kind == "import"

    store.update("t1", status="running", progress=0.5)
    t = store.get("t1")
    assert t.status == "running"
    assert t.progress == 0.5

    store.update("t1", status="done", result={"chunks": 3})
    t = store.get("t1")
    assert t.status == "done"
    assert t.result == {"chunks": 3}


def test_get_missing_returns_none(tmp_path: Path):
    store = TaskStore(tmp_path / "tasks.db")
    assert store.get("nope") is None


def test_error_recorded(tmp_path: Path):
    store = TaskStore(tmp_path / "tasks.db")
    store.create("t2", "import")
    store.update("t2", status="failed", error="boom")
    t = store.get("t2")
    assert t.error == "boom"
    assert t.status == "failed"


def test_idempotent_schema_creation(tmp_path: Path):
    store = TaskStore(tmp_path / "tasks.db")
    store2 = TaskStore(tmp_path / "tasks.db")
    store.create("a", "import")
    assert store2.get("a") is not None  # same file → same record


def test_purge_stale_removes_old_terminal_tasks_and_preserves_active(tmp_path: Path):
    db_path = tmp_path / "tasks.db"
    store = TaskStore(db_path)
    for task_id, status in (("done-old", "done"), ("failed-old", "failed"),
                            ("queued-old", "queued"), ("running-old", "running"),
                            ("done-new", "done")):
        store.create(task_id, "import")
        store.update(task_id, status=status)

    old = (datetime.now(timezone.utc) - timedelta(days=31)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE tasks SET updated_at = ? WHERE task_id LIKE '%-old'", (old,))
        conn.commit()

    assert store.purge_stale(ttl_days=30) == 2
    assert store.get("done-old") is None
    assert store.get("failed-old") is None
    assert store.get("queued-old") is not None
    assert store.get("running-old") is not None
    assert store.get("done-new") is not None


def test_purge_stale_rejects_non_positive_ttl(tmp_path: Path):
    store = TaskStore(tmp_path / "tasks.db")
    with pytest.raises(ValueError, match="ttl_days"):
        store.purge_stale(0)
    with pytest.raises(ValueError, match="ttl_days"):
        store.purge_stale(-1)


def test_purge_stale_returns_zero_when_nothing_matches(tmp_path: Path):
    store = TaskStore(tmp_path / "tasks.db")
    assert store.purge_stale() == 0


def test_purge_stale_uses_updated_at_not_created_at(tmp_path: Path):
    db_path = tmp_path / "tasks.db"
    store = TaskStore(db_path)
    store.create("recently-updated", "import")
    store.update("recently-updated", status="done")
    old = (datetime.now(timezone.utc) - timedelta(days=31)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE tasks SET created_at = ? WHERE task_id = ?", (old, "recently-updated"))
        conn.commit()
    assert store.purge_stale() == 0
    assert store.get("recently-updated") is not None


# ---- Stage + event ring buffer (G6) -----------------------------------------


def test_stage_round_trip(tmp_path: Path):
    store = TaskStore(tmp_path / "tasks.db")
    store.create("t-stage", "import")
    store.update("t-stage", stage="embedding")
    t = store.get("t-stage")
    assert t is not None
    assert t.stage == TaskStage.EMBEDDING


def test_default_stage_is_queued(tmp_path: Path):
    store = TaskStore(tmp_path / "tasks.db")
    store.create("t-default", "import")
    t = store.get("t-default")
    assert t is not None
    assert t.stage == TaskStage.QUEUED


def test_add_event_appears_in_list(tmp_path: Path):
    store = TaskStore(tmp_path / "tasks.db")
    store.create("t-evt", "import")
    store.add_event("t-evt", "parsing", 0.05, "starting")
    store.add_event("t-evt", "embedding", 0.50, "32/64 chunks")
    events = store.list_events("t-evt")
    assert len(events) == 2
    assert events[0].stage == TaskStage.PARSING
    assert events[1].stage == TaskStage.EMBEDDING
    assert events[1].progress == 0.50
    # get() also returns events so the API endpoint has them ready.
    t = store.get("t-evt")
    assert t is not None
    assert len(t.events) == 2


def test_event_ring_buffer_trims_to_32(tmp_path: Path):
    store = TaskStore(tmp_path / "tasks.db")
    store.create("t-ring", "import")
    # Push _EVENTS_KEEP + 3 events; only the last _EVENTS_KEEP should remain.
    for i in range(_EVENTS_KEEP + 3):
        store.add_event("t-ring", "embedding", i / 100, f"event {i}")
    events = store.list_events("t-ring")
    assert len(events) == _EVENTS_KEEP
    # The kept events are the most recent ones.
    assert events[0].message == "event 3"
    assert events[-1].message == f"event {_EVENTS_KEEP + 2}"


def test_list_events_since_paginates(tmp_path: Path):
    store = TaskStore(tmp_path / "tasks.db")
    store.create("t-page", "import")
    for i in range(5):
        store.add_event("t-page", "embedding", i / 10, f"event {i}")
    # Get the last 2 (events with id > 3).
    events = store.list_events_since("t-page", 3)
    assert len(events) == 2
    assert events[0].message == "event 3"
    assert events[1].message == "event 4"


def test_last_event_id_returns_zero_for_unknown_task(tmp_path: Path):
    store = TaskStore(tmp_path / "tasks.db")
    assert store.last_event_id("never-existed") == 0


def test_schema_migration_adds_stage_to_existing_db(tmp_path: Path):
    """Simulate a pre-v1 ``tasks.db`` by creating the old schema directly,
    then assert the migration brings it up to date without losing existing
    rows."""
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE tasks (
                task_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                status TEXT NOT NULL,
                progress REAL NOT NULL DEFAULT 0,
                error TEXT,
                result TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO tasks(task_id, kind, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("legacy-1", "import", "done", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
        )
        conn.commit()

    # Constructing TaskStore should run the migration transparently.
    store = TaskStore(db_path)

    # Existing row is still there and now carries the default stage.
    t = store.get("legacy-1")
    assert t is not None
    assert t.task_id == "legacy-1"
    assert t.stage == TaskStage.QUEUED

    # The schema is now at user_version=1.
    with sqlite3.connect(db_path) as conn:
        ver = conn.execute("PRAGMA user_version").fetchone()[0]
        assert int(ver) == 1
        cols = {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
        assert "stage" in cols
