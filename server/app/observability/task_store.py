"""SQLite-backed task store for import / search background jobs.

Schema (v1):
  tasks(task_id TEXT PRIMARY KEY,
        kind TEXT NOT NULL,
        status TEXT NOT NULL,            -- queued|running|done|failed
        progress REAL NOT NULL DEFAULT 0,
        error TEXT,
        result TEXT,                     -- JSON-encoded payload
        stage TEXT NOT NULL DEFAULT 'queued',  -- added in v1 migration
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL)
  task_events(id INTEGER PRIMARY KEY AUTOINCREMENT,
              task_id TEXT NOT NULL,
              ts TEXT NOT NULL,
              stage TEXT NOT NULL,
              progress REAL NOT NULL,
              message TEXT NOT NULL,
              FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE)

The on-disk schema is migrated lazily:
  - user_version=0  → v1 (add ``stage`` column + ``task_events`` table).
  - v1 is also the default for fresh installs (the column is in the CREATE
    statement and the migration is a no-op when the column already exists).

The ``task_events`` table is a ring buffer per task_id; ``add_event`` keeps
only the latest ``_EVENTS_KEEP`` rows. Older events are dropped on the next
insert.
"""
from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.observability.models import TaskEvent, TaskStage, TaskStatus


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


_SCHEMA_VERSION = 1
_EVENTS_KEEP = 32


class TaskStore:
    """Thin wrapper around a sqlite3 file with a `tasks` table + per-task
    event ring buffer."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            self._migrate(conn)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS task_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    progress REAL NOT NULL,
                    message TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_task_events_task_id "
                "ON task_events(task_id, id)"
            )
            conn.commit()

    def _migrate(self, conn: sqlite3.Connection) -> None:
        """Bring an existing ``tasks.db`` up to the current schema version."""
        cur = conn.execute("PRAGMA user_version").fetchone()
        version = int(cur[0]) if cur else 0
        if version >= _SCHEMA_VERSION:
            return

        # v0 -> v1: add ``stage`` column to ``tasks`` (idempotent).
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                status TEXT NOT NULL,
                progress REAL NOT NULL DEFAULT 0,
                error TEXT,
                result TEXT,
                stage TEXT NOT NULL DEFAULT 'queued',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
        if "stage" not in cols:
            try:
                conn.execute(
                    "ALTER TABLE tasks ADD COLUMN stage TEXT NOT NULL DEFAULT 'queued'"
                )
            except sqlite3.OperationalError:
                # Race / re-entry: column already exists. Safe to ignore.
                pass

        conn.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")

    # ---- CRUD ---------------------------------------------------------------

    def create(self, task_id: str, kind: str) -> TaskStatus:
        now = _now()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO tasks(task_id, kind, status, progress, stage, "
                "created_at, updated_at) VALUES (?, ?, 'queued', 0, 'queued', ?, ?)",
                (task_id, kind, now, now),
            )
            conn.commit()
        return TaskStatus(task_id=task_id, kind=kind, status="queued")

    def update(
        self,
        task_id: str,
        *,
        status: str | None = None,
        progress: float | None = None,
        stage: str | None = None,
        error: str | None = None,
        result: dict | None = None,
    ) -> None:
        sets: list[str] = []
        vals: list = []
        if status is not None:
            sets.append("status = ?")
            vals.append(status)
        if progress is not None:
            sets.append("progress = ?")
            vals.append(progress)
        if stage is not None:
            sets.append("stage = ?")
            vals.append(stage)
        if error is not None:
            sets.append("error = ?")
            vals.append(error)
        if result is not None:
            sets.append("result = ?")
            vals.append(json.dumps(result, ensure_ascii=False))
        sets.append("updated_at = ?")
        vals.append(_now())
        vals.append(task_id)
        with self._connect() as conn:
            conn.execute(f"UPDATE tasks SET {', '.join(sets)} WHERE task_id = ?", vals)
            conn.commit()

    def purge_stale(self, ttl_days: int = 30) -> int:
        """Delete terminal tasks whose last update is older than ``ttl_days``."""
        if ttl_days <= 0:
            raise ValueError("ttl_days must be greater than zero")
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=ttl_days)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM tasks WHERE status IN ('done', 'failed') AND updated_at < ?",
                (cutoff,),
            )
            conn.commit()
            return cursor.rowcount

    # ---- Events ring buffer -------------------------------------------------

    def add_event(
        self,
        task_id: str,
        stage: str,
        progress: float,
        message: str,
    ) -> TaskEvent:
        """Append an event for ``task_id`` and trim to the last ``_EVENTS_KEEP``
        rows. Returns the inserted event (including its assigned ts)."""
        ts = _now()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO task_events(task_id, ts, stage, progress, message) "
                "VALUES (?, ?, ?, ?, ?)",
                (task_id, ts, stage, progress, message),
            )
            event_id = cur.lastrowid
            # Trim older events so the buffer stays bounded.
            conn.execute(
                "DELETE FROM task_events WHERE task_id = ? AND id NOT IN "
                "(SELECT id FROM task_events WHERE task_id = ? "
                "ORDER BY id DESC LIMIT ?)",
                (task_id, task_id, _EVENTS_KEEP),
            )
            conn.commit()
        return TaskEvent(
            ts=ts,
            stage=TaskStage(stage) if isinstance(stage, str) else stage,
            progress=progress,
            message=message,
        )

    def list_events(self, task_id: str) -> list[TaskEvent]:
        """Return all retained events for ``task_id`` in chronological order."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT ts, stage, progress, message FROM task_events "
                "WHERE task_id = ? ORDER BY id ASC",
                (task_id,),
            ).fetchall()
        return [
            TaskEvent(
                ts=r["ts"],
                stage=TaskStage(r["stage"]),
                progress=r["progress"],
                message=r["message"],
            )
            for r in rows
        ]

    def list_events_since(self, task_id: str, since_id: int) -> list[TaskEvent]:
        """Return events with row id > ``since_id`` (for incremental polling)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT ts, stage, progress, message FROM task_events "
                "WHERE task_id = ? AND id > ? ORDER BY id ASC",
                (task_id, since_id),
            ).fetchall()
        return [
            TaskEvent(
                ts=r["ts"],
                stage=TaskStage(r["stage"]),
                progress=r["progress"],
                message=r["message"],
            )
            for r in rows
        ]

    def last_event_id(self, task_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(id), 0) AS m FROM task_events WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        return int(row["m"]) if row else 0

    # ---- Read ---------------------------------------------------------------

    def get(self, task_id: str) -> TaskStatus | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT task_id, kind, status, progress, stage, error, result "
                "FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        if row is None:
            return None
        result = json.loads(row["result"]) if row["result"] else None
        return TaskStatus(
            task_id=row["task_id"],
            kind=row["kind"],
            status=row["status"],
            progress=row["progress"],
            stage=TaskStage(row["stage"]) if row["stage"] else TaskStage.QUEUED,
            events=self.list_events(task_id),
            error=row["error"],
            result=result,
        )