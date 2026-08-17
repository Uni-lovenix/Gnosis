"""Read-only view of the effective high-availability settings."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.config.settings import get_settings

router = APIRouter(prefix="/v1/settings/ha", tags=["ha"])


class HaSettingsResponse(BaseModel):
    backup_auto: bool
    backup_interval_hours: float
    backup_keep: int
    health_monitor: bool
    health_monitor_interval_seconds: int
    failover_enabled: bool
    failover_consecutive_failures: int
    failover_auto_recover: bool
    failover_recover_consecutive_checks: int


@router.get("", response_model=HaSettingsResponse)
async def ha_settings() -> HaSettingsResponse:
    s = get_settings()
    return HaSettingsResponse(
        backup_auto=s.backup_auto,
        backup_interval_hours=s.backup_interval_hours,
        backup_keep=s.backup_keep,
        health_monitor=s.health_monitor,
        health_monitor_interval_seconds=s.health_monitor_interval_seconds,
        failover_enabled=s.failover_enabled,
        failover_consecutive_failures=s.failover_consecutive_failures,
        failover_auto_recover=s.failover_auto_recover,
        failover_recover_consecutive_checks=s.failover_recover_consecutive_checks,
    )
