"""Persistent store for user-saved datasource connection configs.

A single JSON file under ``settings.data_dir / 'datasources.json'`` holds a
list of named configs plus an ``active`` pointer. Operations are atomic via
``os.replace`` after writing to a sibling temp file.

Schema (v1):

    {
      "version": 1,
      "active": "<name>",          # or null
      "configs": [
        {
          "name": "my-elasticsearch",
          "type": "elasticsearch",
          "options": {...},        # adapter-specific
          "saved_at": "2026-08-04T12:00:00Z",
          "last_tested_at": "..."  # optional
        }
      ]
    }

Why JSON, not SQLite:
* The store is small (handful of entries) and human-editable — users can
  drop the file into a repo or share a known-good config with a teammate.
* Goal.md line 16 explicitly accepts "配置文件" as an alternative to UI.
* SQLite would add an opaque binary file next to ``tasks.db`` for no real win.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class DatasourceStore:
    """Persistent list of named datasource configs + an ``active`` pointer."""

    SCHEMA_VERSION = 1

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_locked({"version": self.SCHEMA_VERSION, "active": None, "configs": []})

    # ---- internal ----------------------------------------------------------

    def _read_locked(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": self.SCHEMA_VERSION, "active": None, "configs": []}
        try:
            data = json.loads(self.path.read_text("utf-8"))
        except json.JSONDecodeError:
            # Corrupt file: back it up and start clean so the server still boots.
            backup = self.path.with_suffix(self.path.suffix + ".corrupt")
            os.replace(self.path, backup)
            return {"version": self.SCHEMA_VERSION, "active": None, "configs": []}
        # Defensive migration: missing keys fill in defaults.
        data.setdefault("version", self.SCHEMA_VERSION)
        data.setdefault("active", None)
        data.setdefault("configs", [])
        data.setdefault("failover", [])
        return data

    def _write_locked(self, data: dict[str, Any]) -> None:
        # Write to sibling temp file, then atomic-rename.
        tmp_fd, tmp_path = tempfile.mkstemp(
            prefix=self.path.name + ".", suffix=".tmp", dir=str(self.path.parent)
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2, sort_keys=False)
                fh.write("\n")
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_path, self.path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass
            raise

    # ---- CRUD --------------------------------------------------------------

    def list(self) -> list[dict[str, Any]]:
        """Return all saved configs (a shallow copy, ordered by saved_at asc)."""
        data = self._read_locked()
        return [dict(cfg) for cfg in data.get("configs", [])]

    def get_active(self) -> dict[str, Any] | None:
        """Return the active config dict, or ``None`` if no active set."""
        data = self._read_locked()
        name = data.get("active")
        if not name:
            return None
        for cfg in data.get("configs", []):
            if cfg.get("name") == name:
                return dict(cfg)
        return None

    def get_failover(self) -> list[str]:
        """Return the configured failover order (valid names only)."""
        data = self._read_locked()
        known = {cfg.get("name") for cfg in data.get("configs", [])}
        return [name for name in data.get("failover", []) if name in known]

    def set_failover(self, names: list[str]) -> list[str]:
        """Persist a failover order; only known config names are kept."""
        data = self._read_locked()
        known = {cfg.get("name") for cfg in data.get("configs", [])}
        clean: list[str] = []
        for name in names:
            if name in known and name not in clean:
                clean.append(name)
        data["failover"] = clean
        self._write_locked(data)
        return clean

    def get(self, name: str) -> dict[str, Any] | None:
        for cfg in self._read_locked().get("configs", []):
            if cfg.get("name") == name:
                return dict(cfg)
        return None

    def upsert(
        self,
        *,
        name: str,
        type: str,
        options: dict[str, Any],
    ) -> dict[str, Any]:
        """Add or replace a config by name; returns the saved dict.

        Validation is intentionally light: callers (``/v1/datasources/configs``
        POST handler) must already have run ``/v1/datasources/test`` for the
        same payload, which surfaces adapter-level errors early.
        """
        if not name.strip():
            raise ValueError("name is required")
        if not type.strip():
            raise ValueError("type is required")
        # Strip none values; do not mutate caller's options.
        opts = {k: v for k, v in (options or {}).items() if v is not None}

        data = self._read_locked()
        now = _now()
        saved: dict[str, Any] | None = None
        for cfg in data.get("configs", []):
            if cfg.get("name") == name:
                cfg["type"] = type
                cfg["options"] = opts
                # Preserve saved_at; do not bump it on every edit.
                cfg.setdefault("saved_at", now)
                cfg["last_tested_at"] = None  # schema change invalidates test.
                saved = dict(cfg)
                break
        if saved is None:
            saved = {
                "name": name,
                "type": type,
                "options": opts,
                "saved_at": now,
                "last_tested_at": None,
            }
            data.setdefault("configs", []).append(saved)
        # If this was the active config and schema changed, deactivate is NOT
        # done automatically — caller explicitly decides via /activate.
        self._write_locked(data)
        return saved

    def delete(self, name: str) -> bool:
        """Remove a config by name; if it was active, clear ``active``."""
        data = self._read_locked()
        before = len(data.get("configs", []))
        data["configs"] = [c for c in data.get("configs", []) if c.get("name") != name]
        changed = len(data["configs"]) != before
        if data.get("active") == name:
            data["active"] = None
        if changed:
            self._write_locked(data)
        return changed

    def activate(self, name: str) -> dict[str, Any]:
        """Mark a config as the active datasource; returns the config dict."""
        data = self._read_locked()
        match = next((c for c in data.get("configs", []) if c.get("name") == name), None)
        if match is None:
            raise KeyError(f"unknown datasource config: {name}")
        data["active"] = name
        self._write_locked(data)
        return dict(match)

    def deactivate(self) -> None:
        data = self._read_locked()
        data["active"] = None
        self._write_locked(data)

    def mark_tested(self, name: str) -> None:
        """Stamp ``last_tested_at`` after a successful health probe."""
        data = self._read_locked()
        for cfg in data.get("configs", []):
            if cfg.get("name") == name:
                cfg["last_tested_at"] = _now()
                self._write_locked(data)
                return
