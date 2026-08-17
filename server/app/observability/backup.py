"""Consistent backups for the KB data directory.

The data directory defaults to ``~/.kb-server`` and holds:

* ``datasources.json`` — user-saved datasource configs (may contain credentials).
* ``tasks.db`` — TaskStore + blackboard projection (SQLite).

SQLite files are snapshotted with the sqlite3 backup API so a hot copy is
transactionally consistent; JSON files are copied directly. Backups are
timestamped directories under ``KB_BACKUP_DIR`` with a retention count.

Security note: ``datasources.json`` can contain datasource passwords. Protect
the backup directory with the same permissions as ``~/.kb-server`` and never
commit it to a public repository.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import time
from datetime import datetime
from pathlib import Path

BACKUP_PREFIX = "kb-backup-"
_SQLITE_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
_COPY_SUFFIXES = {".json"}


def _now_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _backup_sqlite(src: Path, dst: Path) -> None:
    """Snapshot a SQLite file via its online backup API."""
    src_conn = sqlite3.connect(str(src))
    dst_conn = sqlite3.connect(str(dst))
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()


def _prune(backup_root: Path, keep: int) -> int:
    """Remove oldest timestamped backups beyond ``keep``; returns count removed."""
    backups = sorted(
        (p for p in backup_root.iterdir() if p.is_dir() and p.name.startswith(BACKUP_PREFIX)),
        key=lambda p: p.name,
    )
    removed = 0
    while len(backups) > max(0, keep):
        stale = backups.pop(0)
        shutil.rmtree(stale)
        removed += 1
    return removed


def backup_data_dir(source: str | Path, backup_root: str | Path, keep: int = 7) -> Path:
    """Copy the data directory into a new timestamped backup snapshot.

    Returns the created backup path. ``backup_root`` may live inside
    ``source``; only top-level data files are copied, never nested backups.
    """
    src = Path(source).expanduser()
    root = Path(backup_root).expanduser()
    root.mkdir(parents=True, exist_ok=True)

    stamp = time.strftime(f"{BACKUP_PREFIX}%Y%m%d-%H%M%S")
    dest = root / stamp
    if dest.exists():
        dest = root / f"{stamp}-{time.time_ns() % 1_000_000}"
    dest.mkdir(parents=True, exist_ok=False)

    copied: list[str] = []
    for item in sorted(src.iterdir()):
        if not item.is_file() or item.name.startswith("."):
            continue
        suffix = item.suffix.lower()
        if suffix in {".tmp", ".lock", ".corrupt"} or suffix.endswith("-journal"):
            continue
        if suffix in _SQLITE_SUFFIXES:
            _backup_sqlite(item, dest / item.name)
        elif suffix in _COPY_SUFFIXES:
            shutil.copy2(item, dest / item.name)
        else:
            continue
        copied.append(item.name)

    manifest = {
        "created_at": _now_utc(),
        "source": str(src),
        "files": copied,
    }
    (dest / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    removed = _prune(root, keep)
    if removed:
        print(f"[kb-backup] pruned {removed} old backup(s)", flush=True)
    return dest


def list_backups(backup_root: str | Path) -> list[dict]:
    """Return backup snapshots newest-first with manifest summaries."""
    root = Path(backup_root).expanduser()
    out: list[dict] = []
    if not root.exists():
        return out
    for item in sorted(root.iterdir(), reverse=True):
        if not item.is_dir() or not item.name.startswith(BACKUP_PREFIX):
            continue
        manifest: dict = {}
        try:
            manifest = json.loads((item / "manifest.json").read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        out.append(
            {
                "name": item.name,
                "path": str(item),
                "created_at": manifest.get("created_at", ""),
                "files": manifest.get("files", []),
                "source": manifest.get("source", ""),
            }
        )
    return out


def latest_backup(backup_root: str | Path) -> dict | None:
    """Return the newest snapshot summary, or ``None`` if none exist."""
    backups = list_backups(backup_root)
    return backups[0] if backups else None


def backup_if_due(
    source: str | Path,
    backup_root: str | Path,
    keep: int = 7,
    interval_hours: float = 24.0,
    now: float | None = None,
) -> tuple[bool, Path | None]:
    """Create a snapshot if none exists or the newest is older than interval.

    Returns ``(created, path_or_none)``. ``path`` is the latest snapshot
    regardless of whether a new one was created.
    """
    latest = latest_backup(backup_root)
    now_s = now if now is not None else time.time()
    if latest is not None and latest.get("created_at"):
        try:
            created_dt = datetime.fromisoformat(latest["created_at"].replace("Z", "+00:00"))
            created_ts = created_dt.timestamp()
        except ValueError:
            created_ts = 0.0
        if now_s - created_ts < interval_hours * 3600:
            return False, Path(latest["path"])
    dest = backup_data_dir(source, backup_root, keep=keep)
    return True, dest


def restore_backup(backup_path: str | Path, target_dir: str | Path) -> dict:
    """Restore a snapshot into ``target_dir`` after preserving the current state.

    Returns ``{"restored_files": [...], "pre_restore": "<path>"}``. The caller
    must stop the server before restoring SQLite files; the desktop main
    process orchestrates that lifecycle.
    """
    backup = Path(backup_path).expanduser()
    if not backup.is_dir() or not backup.name.startswith(BACKUP_PREFIX):
        raise ValueError(f"not a kb backup directory: {backup}")
    manifest_path = backup / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise ValueError(f"backup missing valid manifest.json: {backup}") from e

    target = Path(target_dir).expanduser()
    target.mkdir(parents=True, exist_ok=True)
    pre_restore = backup_data_dir(target, target / ".pre-restore", keep=3)

    restored: list[str] = []
    for name in manifest.get("files", []):
        src = backup / name
        if not src.is_file():
            continue
        shutil.copy2(src, target / name)
        restored.append(name)
    return {"restored_files": restored, "pre_restore": str(pre_restore)}


def main() -> None:
    parser = argparse.ArgumentParser(prog="kb-backup", description="灵知数据目录备份/恢复")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("backup", help="create a snapshot (default)")
    sub.add_parser("list", help="list snapshots")
    restore_parser = sub.add_parser("restore", help="restore a snapshot into KB_DATA_DIR")
    restore_parser.add_argument("backup_path")
    args = parser.parse_args()

    data_dir = Path(os.getenv("KB_DATA_DIR", "~/.kb-server")).expanduser()
    backup_root = Path(
        os.getenv("KB_BACKUP_DIR", str(Path.home() / ".kb-server" / "backups"))
    ).expanduser()
    keep = int(os.getenv("KB_BACKUP_KEEP", "7"))

    if args.command == "restore":
        result = restore_backup(args.backup_path, data_dir)
        print(f"restored {len(result['restored_files'])} file(s) from {args.backup_path}", flush=True)
        print(f"pre-restore snapshot: {result['pre_restore']}", flush=True)
    elif args.command == "list":
        print(json.dumps(list_backups(backup_root), ensure_ascii=False, indent=2), flush=True)
    else:
        dest = backup_data_dir(data_dir, backup_root, keep=keep)
        print(f"backup created: {dest}", flush=True)


if __name__ == "__main__":
    main()
