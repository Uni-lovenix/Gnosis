"""Tests for the PostgreSQL adapter using a fake psycopg connection."""
from __future__ import annotations

from typing import Any

import pytest

from app.datasources.postgres_adapter import PostgresAdapter, PostgresConfig
from app.observability.models import Chunk


class _FakeCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[Any, ...] | None]] = []
        self._fetchall: list[tuple[Any, ...]] = []
        self.rowcount = 0

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        self.executed.append((sql, params))

    def executemany(self, sql: str, seq: list[tuple[Any, ...]]) -> None:
        self.executed.append((sql, ("many", tuple(seq))))
        self.rowcount = len(seq)

    def fetchone(self):
        return (1,)

    def fetchall(self):
        return self._fetchall

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeConn:
    def __init__(self) -> None:
        self.cursor_obj = _FakeCursor()
        self.committed = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def patched_pg(monkeypatch):
    conn = _FakeConn()
    calls: list[_FakeConn] = []

    def _fake_connect(_dsn: str):
        calls.append(conn)
        return conn

    monkeypatch.setattr(
        "app.datasources.postgres_adapter._import_psycopg",
        lambda: (object, lambda c: None),  # type: ignore[arg-type]
    )
    monkeypatch.setattr(
        "app.datasources.postgres_adapter.PostgresAdapter._connect",
        lambda self: _fake_connect(self._dsn),
    )
    return conn, calls


@pytest.mark.asyncio
async def test_pg_ensure_schema_creates_extension_and_table(patched_pg):
    conn, _ = patched_pg
    cfg = PostgresConfig(name="pg", options={"dsn": "x", "table": "kb", "dim": 4})
    PostgresAdapter(cfg)  # construction triggers _ensure_schema
    executed_sqls = " | ".join(s for s, _ in conn.cursor_obj.executed)
    assert "CREATE EXTENSION" in executed_sqls
    assert "CREATE TABLE" in executed_sqls
    assert "ivfflat" in executed_sqls


@pytest.mark.asyncio
async def test_pg_add_inserts_rows(patched_pg):
    conn, _ = patched_pg
    cfg = PostgresConfig(name="pg", options={"dsn": "x", "table": "kb", "dim": 4})
    adapter = PostgresAdapter(cfg)
    chunks = [
        Chunk(document_id="d1", text="hi", vector=[1.0, 0.0, 0.0, 0.0]),
        Chunk(document_id="d1", text="bye", vector=[0.0, 1.0, 0.0, 0.0]),
    ]
    ids = await adapter.add(chunks)
    assert ids == [c.id for c in chunks]
    # last executemany was the insert
    last_sql, last_params = conn.cursor_obj.executed[-1]
    assert "INSERT INTO" in last_sql
    assert last_params[0] == "many"


@pytest.mark.asyncio
async def test_pg_search_executes_cosine_query(patched_pg):
    conn, _ = patched_pg
    conn.cursor_obj._fetchall = [
        ("c1", "d1", "hello", '{"src": "x"}', 0.95),
    ]
    cfg = PostgresConfig(name="pg", options={"dsn": "x", "dim": 4})
    adapter = PostgresAdapter(cfg)
    hits = await adapter.search([1.0, 0.0, 0.0, 0.0], top_k=3)
    assert len(hits) == 1
    assert hits[0].text == "hello"
    assert hits[0].document_id == "d1"
    last_sql = conn.cursor_obj.executed[-1][0]
    assert "<=>" in last_sql
    assert "ORDER BY" in last_sql


@pytest.mark.asyncio
async def test_pg_delete_uses_any(patched_pg):
    conn, _ = patched_pg
    conn.cursor_obj.rowcount = 2
    cfg = PostgresConfig(name="pg", options={"dsn": "x", "dim": 4})
    adapter = PostgresAdapter(cfg)
    removed = await adapter.delete(["a", "b"])
    assert removed == 2
    last_sql = conn.cursor_obj.executed[-1][0]
    assert "= ANY(%s)" in last_sql


@pytest.mark.asyncio
async def test_pg_health(patched_pg):
    conn, _ = patched_pg
    cfg = PostgresConfig(name="pg", options={"dsn": "x", "dim": 4})
    adapter = PostgresAdapter(cfg)
    h = await adapter.health()
    assert h.ok is True
