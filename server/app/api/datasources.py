"""/v1/datasources endpoints.

GET    /v1/datasources                    — list registered adapter types
POST   /v1/datasources/test               — build a temporary adapter and call health()
GET    /v1/datasources/configs            — list user-saved connection configs
POST   /v1/datasources/configs            — save / upsert a connection config
DELETE /v1/datasources/configs/{name}     — drop a saved config
GET    /v1/datasources/active             — show the active datasource (or null)
PUT    /v1/datasources/active/{name}      — mark a saved config as active
DELETE /v1/datasources/active             — clear the active pointer
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.datasources.base import DatasourceConfig
from app.datasources.factory import build
from app.datasources.registry import all_types
from app.observability.datasource_store import DatasourceStore

router = APIRouter(prefix="/v1/datasources", tags=["datasources"])


# Process-wide store; set by main.py at startup.
_store: DatasourceStore | None = None


def set_store(store: DatasourceStore) -> None:
    global _store
    _store = store


def _store_required() -> DatasourceStore:
    if _store is None:
        raise HTTPException(status_code=503, detail="datasource store not initialized")
    return _store


# ---- Catalog ---------------------------------------------------------------


class DatasourceInfo(BaseModel):
    name: str
    type: str
    capabilities: list[str]


@router.get("", response_model=list[DatasourceInfo])
async def list_types() -> list[DatasourceInfo]:
    """List available datasource adapter types.

    This is a static catalog; it does not reflect running instances. Live
    instances are managed by the desktop host process.
    """
    out: list[DatasourceInfo] = []
    for type_name in all_types():
        cfg = DatasourceConfig(name=f"sample-{type_name}", type=type_name)
        try:
            # Instantiate just to read declared capabilities; tear down immediately.
            ds = build(cfg)
            caps = sorted(ds.capabilities())
            await ds.close()
            out.append(DatasourceInfo(name=type_name, type=type_name, capabilities=caps))
        except Exception:  # noqa: BLE001
            # Adapter may require external dep; skip silently here.
            out.append(DatasourceInfo(name=type_name, type=type_name, capabilities=[]))
    return out


# ---- Test ------------------------------------------------------------------


class DatasourceTestRequest(BaseModel):
    name: str = "test"
    type: str
    options: dict = Field(default_factory=dict)


class DatasourceTestResponse(BaseModel):
    ok: bool
    latency_ms: float | None = None
    message: str | None = None


@router.post("/test", response_model=DatasourceTestResponse)
async def test_connection(req: DatasourceTestRequest) -> DatasourceTestResponse:
    """Build a fresh adapter and run a health check."""
    try:
        cfg = DatasourceConfig(name=req.name, type=req.type, options=req.options)
        ds = build(cfg)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"invalid config: {e}") from e
    try:
        h = await ds.health()
    finally:
        await ds.close()
    return DatasourceTestResponse(ok=h.ok, latency_ms=h.latency_ms, message=h.message)


# ---- Saved configs (CRUD) --------------------------------------------------


class DatasourceConfigResponse(BaseModel):
    name: str
    type: str
    options: dict
    saved_at: str
    last_tested_at: str | None = None


class DatasourceConfigUpsert(BaseModel):
    name: str
    type: str
    options: dict = Field(default_factory=dict)


class ActiveResponse(BaseModel):
    name: str | None = None
    config: DatasourceConfigResponse | None = None


@router.get("/configs", response_model=list[DatasourceConfigResponse])
async def list_configs() -> list[DatasourceConfigResponse]:
    """Return user-saved datasource configs (does not echo back type/options
    that the server considers unsafe to log — all are returned verbatim so
    the UI can edit them)."""
    store = _store_required()
    out: list[DatasourceConfigResponse] = []
    for cfg in store.list():
        out.append(
            DatasourceConfigResponse(
                name=cfg["name"],
                type=cfg["type"],
                options=cfg.get("options", {}),
                saved_at=cfg.get("saved_at", ""),
                last_tested_at=cfg.get("last_tested_at"),
            )
        )
    return out


@router.post("/configs", response_model=DatasourceConfigResponse)
async def upsert_config(req: DatasourceConfigUpsert) -> DatasourceConfigResponse:
    """Add or replace a named config. Callers SHOULD invoke ``/v1/datasources/
    test`` first with the same payload to surface adapter-level errors early;
    server only enforces non-empty ``name``/``type`` here."""
    store = _store_required()
    # Reject unknown types early — adapter registry is the source of truth.
    valid_types = set(all_types())
    if req.type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"unknown datasource type: {req.type}; valid: {sorted(valid_types)}",
        )
    # Probe build to fail-fast on bad options (e.g. missing dsn), but do not
    # require health to be ok — some adapters surface ok=False without raising.
    try:
        cfg = DatasourceConfig(name=req.name, type=req.type, options=req.options)
        ds = build(cfg)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"invalid config: {e}") from e
    finally:
        try:
            await ds.close()  # type: ignore[name-defined]
        except Exception:  # noqa: BLE001
            pass
    try:
        saved = store.upsert(name=req.name, type=req.type, options=req.options)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return DatasourceConfigResponse(
        name=saved["name"],
        type=saved["type"],
        options=saved.get("options", {}),
        saved_at=saved.get("saved_at", ""),
        last_tested_at=saved.get("last_tested_at"),
    )


@router.delete("/configs/{name}")
async def delete_config(name: str) -> dict:
    store = _store_required()
    removed = store.delete(name)
    if not removed:
        raise HTTPException(status_code=404, detail=f"no such datasource config: {name}")
    return {"name": name, "deleted": True}


# ---- Active selection ------------------------------------------------------


@router.get("/active", response_model=ActiveResponse)
async def get_active() -> ActiveResponse:
    store = _store_required()
    cfg = store.get_active()
    if cfg is None:
        return ActiveResponse(name=None, config=None)
    return ActiveResponse(
        name=cfg["name"],
        config=DatasourceConfigResponse(
            name=cfg["name"],
            type=cfg["type"],
            options=cfg.get("options", {}),
            saved_at=cfg.get("saved_at", ""),
            last_tested_at=cfg.get("last_tested_at"),
        ),
    )


@router.put("/active/{name}", response_model=DatasourceConfigResponse)
async def set_active(name: str) -> DatasourceConfigResponse:
    """Mark a saved config as the active datasource (used by next startup).

    The active datasource only takes effect on the next server start; the
    currently running import/search pipeline is intentionally not swapped
    to avoid mid-flight mismatches. See docs/RUNBOOK.md §5.
    """
    store = _store_required()
    try:
        cfg = store.activate(name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return DatasourceConfigResponse(
        name=cfg["name"],
        type=cfg["type"],
        options=cfg.get("options", {}),
        saved_at=cfg.get("saved_at", ""),
        last_tested_at=cfg.get("last_tested_at"),
    )


@router.delete("/active")
async def clear_active() -> dict:
    _store_required().deactivate()
    return {"name": None, "deleted": True}
