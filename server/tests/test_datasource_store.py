"""Unit tests for the persistent datasource config store."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.observability.datasource_store import DatasourceStore


def _mk(tmp_path: Path) -> DatasourceStore:
    return DatasourceStore(tmp_path / "datasources.json")


def test_init_creates_empty_store(tmp_path: Path) -> None:
    store = _mk(tmp_path)
    assert store.list() == []
    assert store.get_active() is None
    assert (tmp_path / "datasources.json").exists()


def test_upsert_adds_new_config(tmp_path: Path) -> None:
    store = _mk(tmp_path)
    saved = store.upsert(name="es-prod", type="elasticsearch", options={"url": "http://x:9200"})
    assert saved["name"] == "es-prod"
    assert saved["type"] == "elasticsearch"
    assert saved["options"] == {"url": "http://x:9200"}
    assert saved["saved_at"]
    assert saved["last_tested_at"] is None
    listed = store.list()
    assert len(listed) == 1 and listed[0]["name"] == "es-prod"


def test_upsert_replaces_existing(tmp_path: Path) -> None:
    store = _mk(tmp_path)
    store.upsert(name="es", type="elasticsearch", options={"url": "http://a"})
    store.upsert(name="es", type="elasticsearch", options={"url": "http://b"})
    listed = store.list()
    assert len(listed) == 1
    assert listed[0]["options"] == {"url": "http://b"}


def test_upsert_strips_none_values(tmp_path: Path) -> None:
    store = _mk(tmp_path)
    saved = store.upsert(
        name="v",
        type="vector",
        options={"backend": "memory", "dim": 64, "extra": None},
    )
    assert "extra" not in saved["options"]
    assert saved["options"]["dim"] == 64


def test_upsert_rejects_empty_name(tmp_path: Path) -> None:
    store = _mk(tmp_path)
    with pytest.raises(ValueError):
        store.upsert(name="", type="vector", options={})


def test_upsert_rejects_empty_type(tmp_path: Path) -> None:
    store = _mk(tmp_path)
    with pytest.raises(ValueError):
        store.upsert(name="v", type="", options={})


def test_delete_removes_config(tmp_path: Path) -> None:
    store = _mk(tmp_path)
    store.upsert(name="a", type="vector", options={})
    store.upsert(name="b", type="vector", options={})
    assert store.delete("a") is True
    assert [c["name"] for c in store.list()] == ["b"]


def test_delete_returns_false_for_missing(tmp_path: Path) -> None:
    store = _mk(tmp_path)
    assert store.delete("ghost") is False


def test_delete_clears_active_if_needed(tmp_path: Path) -> None:
    store = _mk(tmp_path)
    store.upsert(name="a", type="vector", options={})
    store.activate("a")
    assert store.get_active() is not None
    store.delete("a")
    assert store.get_active() is None


def test_activate_then_get_active(tmp_path: Path) -> None:
    store = _mk(tmp_path)
    store.upsert(name="a", type="vector", options={"dim": 32})
    active = store.activate("a")
    assert active["name"] == "a"
    assert store.get_active() and store.get_active()["name"] == "a"


def test_activate_unknown_raises_keyerror(tmp_path: Path) -> None:
    store = _mk(tmp_path)
    with pytest.raises(KeyError):
        store.activate("ghost")


def test_deactivate_clears(tmp_path: Path) -> None:
    store = _mk(tmp_path)
    store.upsert(name="a", type="vector", options={})
    store.activate("a")
    store.deactivate()
    assert store.get_active() is None


def test_mark_tested_stamps_timestamp(tmp_path: Path) -> None:
    store = _mk(tmp_path)
    store.upsert(name="a", type="vector", options={})
    assert store.get("a")["last_tested_at"] is None
    store.mark_tested("a")
    assert store.get("a")["last_tested_at"] is not None


def test_persistence_across_reload(tmp_path: Path) -> None:
    """A second instance reading the same file must see the same data."""
    path = tmp_path / "datasources.json"
    s1 = DatasourceStore(path)
    s1.upsert(name="a", type="vector", options={"dim": 64})
    s1.activate("a")
    s2 = DatasourceStore(path)
    assert s2.list()[0]["name"] == "a"
    assert s2.get_active() is not None


def test_corrupt_file_is_backed_up_and_replaced(tmp_path: Path) -> None:
    path = tmp_path / "datasources.json"
    path.write_text("{ not json", encoding="utf-8")
    store = DatasourceStore(path)
    assert store.list() == []
    backup = path.with_suffix(path.suffix + ".corrupt")
    assert backup.exists()
    # Now the store can accept new writes cleanly.
    store.upsert(name="x", type="vector", options={"dim": 8})
    assert store.list()[0]["name"] == "x"


def test_atomic_write_no_partial_files(tmp_path: Path) -> None:
    """Upsert must not leave sibling .tmp files behind."""
    store = _mk(tmp_path)
    store.upsert(name="a", type="vector", options={})
    leftovers = [p for p in tmp_path.iterdir() if p.suffix == ".tmp"]
    assert leftovers == []
    # Final file is valid JSON.
    raw = json.loads((tmp_path / "datasources.json").read_text("utf-8"))
    assert raw["version"] == 1
