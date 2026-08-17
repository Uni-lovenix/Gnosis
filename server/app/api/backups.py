"""Backup listing and creation endpoints.

Restore is intentionally NOT exposed over HTTP: restoring replaces the
SQLite files the running server owns. The desktop main process stops the
server, runs ``python3 -m app.observability.backup restore``, then restarts
it. This module only lets clients discover and create snapshots.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config.settings import get_settings
from app.observability.backup import backup_data_dir, list_backups

router = APIRouter(prefix="/v1/backups", tags=["backups"])


class BackupInfo(BaseModel):
    name: str
    path: str
    created_at: str
    files: list[str]
    source: str


def _roots() -> tuple[Path, Path, int]:
    s = get_settings()
    data_dir = Path(s.data_dir).expanduser()
    backup_root = Path(s.backup_dir or str(data_dir / "backups")).expanduser()
    return data_dir, backup_root, s.backup_keep


@router.get("", response_model=list[BackupInfo])
async def list_backup_snapshots() -> list[BackupInfo]:
    _, backup_root, _ = _roots()
    return [BackupInfo(**item) for item in list_backups(backup_root)]


@router.post("", response_model=BackupInfo, status_code=201)
async def create_backup_snapshot() -> BackupInfo:
    data_dir, backup_root, keep = _roots()
    try:
        dest = backup_data_dir(data_dir, backup_root, keep=keep)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"backup failed: {e}") from e
    match = next((item for item in list_backups(backup_root) if item["path"] == str(dest)), None)
    if match is None:
        match = {
            "name": dest.name,
            "path": str(dest),
            "created_at": "",
            "files": [],
            "source": str(data_dir),
        }
    return BackupInfo(**match)
