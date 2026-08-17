"""SQLite projection for blackboard entry snapshots."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.blackboard.events import BlackboardChange


class BlackboardProjector:
    """Persists a queryable snapshot of current blackboard entries."""

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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS blackboard_entries (
                    goal_id TEXT NOT NULL,
                    entry_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    error TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_blackboard_entries_goal "
                "ON blackboard_entries(goal_id)"
            )
            conn.commit()

    async def on_change(self, change: BlackboardChange) -> None:
        entry = change.entry
        if entry is None:
            return
        payload = json.dumps(entry.payload, ensure_ascii=False, default=str)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO blackboard_entries(
                    goal_id, entry_id, kind, status, revision, payload, error, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entry_id) DO UPDATE SET
                    goal_id = excluded.goal_id,
                    kind = excluded.kind,
                    status = excluded.status,
                    revision = excluded.revision,
                    payload = excluded.payload,
                    error = excluded.error,
                    updated_at = excluded.updated_at
                """,
                (
                    entry.goal_id,
                    entry.entry_id,
                    entry.kind,
                    entry.status,
                    entry.revision,
                    payload,
                    entry.error,
                    entry.updated_at,
                ),
            )
            conn.commit()

    def list(
        self,
        goal_id: str | None = None,
        kind: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        sql = "SELECT goal_id, entry_id, kind, status, revision, payload, error, updated_at FROM blackboard_entries WHERE 1=1"
        params: list = []
        if goal_id is not None:
            sql += " AND goal_id = ?"
            params.append(goal_id)
        if kind is not None:
            sql += " AND kind = ?"
            params.append(kind)
        if status is not None:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY updated_at"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item["payload"])
            out.append(item)
        return out

