"""Health endpoints: liveness snapshot + dependency-aware readiness probe."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config.settings import get_settings
from app.datasources.base import DataSource
from app.datasources.registry import all_types
from app.embedding.base import Embedder
from app.observability.logging import get_logger

log = get_logger("health")

router = APIRouter(prefix="/v1/health", tags=["health"])


@dataclass
class RuntimeState:
    """Facts captured at component assembly time; read by /v1/health."""

    embedder: Embedder | None = None
    embedder_backend: str | None = None
    embedder_fallback: bool = False
    datasource: DataSource | None = None
    datasource_source: str = "none"
    data_dir: str = ""
    started_at: float = time.time()
    datasource_ok: bool | None = None
    datasource_message: str | None = None
    datasource_latency_ms: float | None = None
    embedder_ok: bool | None = None
    embedder_message: str | None = None
    last_probe_at: str | None = None


_runtime = RuntimeState()
_PROBE_TTL_SECONDS = 15.0
_PROBE_TIMEOUT_SECONDS = 2.5
_probe_cache: tuple[float, list["HealthCheck"]] | None = None


def set_runtime_state(
    *,
    embedder: Embedder | None = None,
    embedder_backend: str | None = None,
    embedder_fallback: bool = False,
    datasource: DataSource | None = None,
    datasource_source: str = "none",
    data_dir: str = "",
) -> None:
    """Store the running component set so health can report reality."""
    global _runtime, _probe_cache
    _runtime = RuntimeState(
        embedder=embedder,
        embedder_backend=embedder_backend,
        embedder_fallback=embedder_fallback,
        datasource=datasource,
        datasource_source=datasource_source,
        data_dir=data_dir,
        started_at=time.time(),
    )
    _probe_cache = None


def update_active_datasource(
    datasource: DataSource | None,
    source: str = "active",
) -> None:
    """Swap the runtime datasource without resetting the process start time."""
    global _probe_cache
    _runtime.datasource = datasource
    _runtime.datasource_source = source
    _runtime.datasource_ok = None
    _runtime.datasource_message = None
    _runtime.datasource_latency_ms = None
    _probe_cache = None


def update_dependency_health(
    *,
    datasource_ok: bool | None = None,
    datasource_message: str | None = None,
    datasource_latency_ms: float | None = None,
    embedder_ok: bool | None = None,
    embedder_message: str | None = None,
) -> None:
    """Store the latest dependency probe results for /v1/health."""
    _runtime.datasource_ok = datasource_ok
    _runtime.datasource_message = datasource_message
    _runtime.datasource_latency_ms = datasource_latency_ms
    _runtime.embedder_ok = embedder_ok
    _runtime.embedder_message = embedder_message
    _runtime.last_probe_at = datetime.now(timezone.utc).isoformat()


class ActiveDatasourceHealth(BaseModel):
    name: str
    type: str
    source: str
    ok: bool | None = None
    latency_ms: float | None = None
    message: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"
    embed_backend: str
    embed_dim: int
    datasources: list[str]
    degraded: bool
    started_at: str
    uptime_seconds: float
    embedder_backend: str | None
    embedder_fallback: bool
    embedder_ok: bool | None
    active_datasource: ActiveDatasourceHealth | None
    data_dir: str
    last_probe_at: str | None


class HealthCheck(BaseModel):
    name: str
    ok: bool
    latency_ms: float | None = None
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ReadyResponse(BaseModel):
    status: str
    degraded: bool
    checks: list[HealthCheck]


@router.get("", response_model=HealthResponse)
async def health() -> HealthResponse:
    s = get_settings()
    degraded = (
        _runtime.embedder_fallback
        or _runtime.datasource is None
        or _runtime.datasource_ok is False
        or _runtime.embedder_ok is False
    )
    started_at = datetime.fromtimestamp(_runtime.started_at, tz=timezone.utc).isoformat()
    active: ActiveDatasourceHealth | None = None
    if _runtime.datasource is not None:
        active = ActiveDatasourceHealth(
            name=_runtime.datasource.name,
            type=_runtime.datasource.type,
            source=_runtime.datasource_source,
            ok=_runtime.datasource_ok,
            latency_ms=_runtime.datasource_latency_ms,
            message=_runtime.datasource_message,
        )
    return HealthResponse(
        status="degraded" if degraded else "ok",
        embed_backend=s.embed_backend,
        embed_dim=s.embed_dim,
        datasources=all_types(),
        degraded=degraded,
        started_at=started_at,
        uptime_seconds=round(time.time() - _runtime.started_at, 3),
        embedder_backend=_runtime.embedder_backend,
        embedder_fallback=_runtime.embedder_fallback,
        embedder_ok=_runtime.embedder_ok,
        active_datasource=active,
        data_dir=_runtime.data_dir,
        last_probe_at=_runtime.last_probe_at,
    )


async def _probe_checks() -> list[HealthCheck]:
    """Run dependency probes with a short TTL cache."""
    global _probe_cache
    now = time.monotonic()
    if _probe_cache is not None and now - _probe_cache[0] < _PROBE_TTL_SECONDS:
        return _probe_cache[1]

    checks: list[HealthCheck] = [HealthCheck(name="server", ok=True)]

    if _runtime.datasource is None:
        checks.append(HealthCheck(name="datasource", ok=False, message="no active datasource"))
    else:
        start = time.perf_counter()
        try:
            h = await asyncio.wait_for(_runtime.datasource.health(), timeout=_PROBE_TIMEOUT_SECONDS)
            checks.append(
                HealthCheck(
                    name="datasource",
                    ok=h.ok,
                    latency_ms=h.latency_ms,
                    message=h.message,
                    details=h.details,
                )
            )
        except Exception as e:  # noqa: BLE001
            checks.append(
                HealthCheck(
                    name="datasource",
                    ok=False,
                    latency_ms=round((time.perf_counter() - start) * 1000, 2),
                    message=str(e),
                )
            )

    if _runtime.embedder is None:
        checks.append(HealthCheck(name="embedder", ok=False, message="no embedder"))
    else:
        start = time.perf_counter()
        try:
            ok = await asyncio.wait_for(_runtime.embedder.health(), timeout=_PROBE_TIMEOUT_SECONDS)
            checks.append(
                HealthCheck(
                    name="embedder",
                    ok=bool(ok),
                    latency_ms=round((time.perf_counter() - start) * 1000, 2),
                    message="probe ok" if ok else "embed probe failed",
                )
            )
        except Exception as e:  # noqa: BLE001
            checks.append(
                HealthCheck(
                    name="embedder",
                    ok=False,
                    latency_ms=round((time.perf_counter() - start) * 1000, 2),
                    message=str(e),
                )
            )

    _probe_cache = (now, checks)
    ds_check = next((c for c in checks if c.name == "datasource"), None)
    embed_check = next((c for c in checks if c.name == "embedder"), None)
    update_dependency_health(
        datasource_ok=ds_check.ok if ds_check is not None else None,
        datasource_message=ds_check.message if ds_check is not None else None,
        datasource_latency_ms=ds_check.latency_ms if ds_check is not None else None,
        embedder_ok=embed_check.ok if embed_check is not None else None,
        embedder_message=embed_check.message if embed_check is not None else None,
    )
    if not all(c.ok for c in checks):
        log.warning(
            "health.readiness_degraded",
            checks=[{"name": c.name, "ok": c.ok, "message": c.message} for c in checks],
        )
    return checks


async def refresh_runtime_health() -> list[HealthCheck]:
    """Force a dependency probe and refresh the /v1/health snapshot."""
    return await _probe_checks()


@router.get("/ready", response_model=ReadyResponse)
async def ready() -> ReadyResponse:
    checks = await _probe_checks()
    degraded = not all(c.ok for c in checks)
    return ReadyResponse(
        status="degraded" if degraded else "ready",
        degraded=degraded,
        checks=checks,
    )
