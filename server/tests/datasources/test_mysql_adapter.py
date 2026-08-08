"""Tests for the MySQL adapter using a fake PyMySQL connection."""
from __future__ import annotations

import json
from typing import Any

import pytest
import structlog.testing

from app.datasources.mysql_adapter import MysqlAdapter, MysqlConfig
from app.observability.models import Chunk


class _FakeCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[Any, ...] | None]] = []
        self._rows: list[tuple[Any, ...]] = []
        self.rowcount = 0

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        self.executed.append((sql, params))
        if params and params and isinstance(params[0], (list, tuple)):
            self.rowcount = len(params[0])
        elif sql.lstrip().upper().startswith("DELETE"):
            # crude: count placeholders
            self.rowcount = sql.count("%s")

    def executemany(self, sql: str, seq: list[tuple[Any, ...]]) -> None:
        self.executed.append((sql, ("many", tuple(seq))))
        self.rowcount = len(seq)

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return (1,)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeConn:
    def __init__(self) -> None:
        self.cursor_obj = _FakeCursor()

    def cursor(self):
        return self.cursor_obj

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def patched_mysql(monkeypatch):
    conn = _FakeConn()

    monkeypatch.setattr(
        "app.datasources.mysql_adapter._import_pymysql",
        lambda: object,
    )
    monkeypatch.setattr(
        "app.datasources.mysql_adapter.MysqlAdapter._connect",
        lambda self: conn,
    )
    return conn


@pytest.mark.asyncio
async def test_mysql_ensure_schema(patched_mysql):
    conn = patched_mysql
    cfg = MysqlConfig(name="m", options={"host": "x", "dim": 4})
    MysqlAdapter(cfg)
    executed = " | ".join(s for s, _ in conn.cursor_obj.executed)
    assert "CREATE TABLE" in executed
    assert "JSON" in executed


@pytest.mark.asyncio
async def test_mysql_add_inserts_and_idempotent(patched_mysql):
    conn = patched_mysql
    cfg = MysqlConfig(name="m", options={"host": "x", "dim": 4})
    adapter = MysqlAdapter(cfg)
    chunks = [
        Chunk(document_id="d1", text="hi", vector=[1.0, 0.0, 0.0, 0.0]),
    ]
    ids = await adapter.add(chunks)
    assert ids == [chunks[0].id]
    last_sql = conn.cursor_obj.executed[-1][0]
    assert "ON DUPLICATE KEY UPDATE" in last_sql


@pytest.mark.asyncio
async def test_mysql_search_ranks_by_cosine(patched_mysql):
    conn = patched_mysql
    conn.cursor_obj._rows = [
        ("c1", "hello", json.dumps({"src": "x"}), json.dumps([1.0, 0.0, 0.0, 0.0])),
        ("c2", "bye", json.dumps({"src": "y"}), json.dumps([0.0, 1.0, 0.0, 0.0])),
    ]
    cfg = MysqlConfig(name="m", options={"host": "x", "dim": 4})
    adapter = MysqlAdapter(cfg)
    hits = await adapter.search([1.0, 0.0, 0.0, 0.0], top_k=2)
    assert len(hits) == 2
    assert hits[0].text == "hello"
    assert hits[0].score > hits[1].score


@pytest.mark.asyncio
async def test_mysql_search_filter(patched_mysql):
    conn = patched_mysql
    conn.cursor_obj._rows = []
    cfg = MysqlConfig(name="m", options={"host": "x", "dim": 4})
    adapter = MysqlAdapter(cfg)
    await adapter.search([1.0, 0.0, 0.0, 0.0], filter={"document_id": "d1"})
    last_sql, last_params = conn.cursor_obj.executed[-1]
    assert "JSON_EXTRACT" in last_sql


@pytest.mark.asyncio
async def test_mysql_delete(patched_mysql):
    conn = patched_mysql
    cfg = MysqlConfig(name="m", options={"host": "x", "dim": 4})
    adapter = MysqlAdapter(cfg)
    removed = await adapter.delete(["a", "b", "c"])
    assert removed == 3


@pytest.mark.asyncio
async def test_mysql_health(patched_mysql):
    cfg = MysqlConfig(name="m", options={"host": "x", "dim": 4})
    adapter = MysqlAdapter(cfg)
    h = await adapter.health()
    assert h.ok is True


@pytest.mark.asyncio
async def test_mysql_dim_mismatch_rejected(patched_mysql):
    cfg = MysqlConfig(name="m", options={"host": "x", "dim": 4})
    adapter = MysqlAdapter(cfg)
    bad = Chunk(document_id="d", text="x", vector=[1.0, 0.0])
    with pytest.raises(Exception):
        await adapter.add([bad])


# ---------------------------------------------------------------------------
# KI-02 (C8): scan_limit_risk capability + scan_limit_hit warning
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mysql_capabilities_include_scan_limit_risk(patched_mysql):
    cfg = MysqlConfig(name="m", options={"host": "x", "dim": 4})
    adapter = MysqlAdapter(cfg)
    caps = adapter.capabilities()
    assert "metadata_filter" in caps
    assert "small_dataset_only" in caps
    assert "scan_limit_risk" in caps


@pytest.mark.asyncio
async def test_mysql_init_warns_small_dataset_only(patched_mysql):
    cfg = MysqlConfig(name="m", options={"host": "x", "dim": 4})
    with structlog.testing.capture_logs() as cap:
        MysqlAdapter(cfg)
    events = [e["event"] for e in cap]
    assert "mysql.adapter.small_dataset_only" in events
    # init info event also present for downstream consumers
    assert "mysql.adapter.initialized" in events


@pytest.mark.asyncio
async def test_mysql_search_warns_when_scan_limit_hit(patched_mysql):
    conn = patched_mysql
    # Build exactly max_scan_rows fake rows so the warning fires.
    max_scan = 100_000
    cfg = MysqlConfig(
        name="m", options={"host": "x", "dim": 4, "max_scan_rows": max_scan}
    )
    adapter = MysqlAdapter(cfg)
    conn.cursor_obj._rows = [
        (f"c{i}", "hi", json.dumps({}), json.dumps([1.0, 0.0, 0.0, 0.0]))
        for i in range(max_scan)
    ]
    with structlog.testing.capture_logs() as cap:
        hits = await adapter.search([1.0, 0.0, 0.0, 0.0], top_k=3)
    assert len(hits) == 3  # result is still top_k-truncated
    scan_events = [e for e in cap if e["event"] == "mysql.adapter.scan_limit_hit"]
    assert scan_events, "expected mysql.adapter.scan_limit_hit warning"
    assert scan_events[0]["scanned_rows"] == max_scan
    assert scan_events[0]["max_scan_rows"] == max_scan
    assert scan_events[0]["log_level"] == "warning"


@pytest.mark.asyncio
async def test_mysql_search_no_warn_below_limit(patched_mysql):
    conn = patched_mysql
    max_scan = 100_000
    cfg = MysqlConfig(
        name="m", options={"host": "x", "dim": 4, "max_scan_rows": max_scan}
    )
    adapter = MysqlAdapter(cfg)
    conn.cursor_obj._rows = [
        (f"c{i}", "hi", json.dumps({}), json.dumps([1.0, 0.0, 0.0, 0.0]))
        for i in range(max_scan - 1)
    ]
    with structlog.testing.capture_logs() as cap:
        await adapter.search([1.0, 0.0, 0.0, 0.0], top_k=3)
    scan_events = [e for e in cap if e["event"] == "mysql.adapter.scan_limit_hit"]
    assert not scan_events, "did not expect scan_limit_hit below max_scan_rows"