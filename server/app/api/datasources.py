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

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api import chunks as chunks_api
from app.api import health as health_api
from app.datasources.base import DatasourceConfig
from app.datasources.factory import build
from app.datasources.registry import all_types
from app.observability.datasource_store import DatasourceStore
from app.observability.logging import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/v1/datasources", tags=["datasources"])


# Process-wide store; set by main.py at startup.
_store: DatasourceStore | None = None
_controller = None
_embedder_dim = 64
_active_ds = None


def set_store(store: DatasourceStore) -> None:
    global _store
    _store = store


def _store_required() -> DatasourceStore:
    if _store is None:
        raise HTTPException(status_code=503, detail="datasource store not initialized")
    return _store


def set_controller(controller) -> None:
    global _controller
    _controller = controller


def set_embedder_dim(dim: int) -> None:
    global _embedder_dim
    _embedder_dim = int(dim)


def set_active_datasource(ds) -> None:
    global _active_ds
    _active_ds = ds


# ---- Catalog ---------------------------------------------------------------


class DatasourceInfo(BaseModel):
    name: str
    type: str
    capabilities: list[str]


class DatasourceSchemaField(BaseModel):
    """One editable option for a datasource adapter type.

    ``sensitive`` is used by the UI to render password inputs and to keep
    secret values out of visible form summaries; the server never logs
    option values either way.
    """

    key: str
    label: str
    type: Literal["text", "password", "number", "boolean", "select", "list"]
    required: bool = False
    sensitive: bool = False
    default: Any = None
    help: str = ""
    options: list[str] = Field(default_factory=list)


class DatasourceSchema(BaseModel):
    type: str
    label: str
    fields: list[DatasourceSchemaField]


OPTIONS_SCHEMAS: dict[str, DatasourceSchema] = {
    "vector": DatasourceSchema(
        type="vector",
        label="向量数据库",
        fields=[
            DatasourceSchemaField(
                key="backend",
                label="后端",
                type="select",
                required=True,
                default="memory",
                options=["memory", "milvus"],
                help="memory 适合小规模个人库；milvus 适合更大规模向量检索。",
            ),
            DatasourceSchemaField(
                key="collection",
                label="Collection",
                type="text",
                default="kb_chunks",
                help="Milvus 后端使用。",
            ),
            DatasourceSchemaField(
                key="dim",
                label="向量维度",
                type="number",
                default=1024,
                help="必须与 Embedding 模型输出维度一致，bge-m3 为 1024。",
            ),
            DatasourceSchemaField(
                key="uri",
                label="Milvus URI",
                type="text",
                default="http://127.0.0.1:19530",
                help="Milvus 后端使用。",
            ),
        ],
    ),
    "elasticsearch": DatasourceSchema(
        type="elasticsearch",
        label="Elasticsearch 8+",
        fields=[
            DatasourceSchemaField(
                key="hosts",
                label="节点地址",
                type="list",
                required=True,
                default=["http://127.0.0.1:9200"],
                help="JSON 数组，例如 [\"http://127.0.0.1:9200\"]。",
            ),
            DatasourceSchemaField(
                key="index",
                label="索引",
                type="text",
                default="kb_chunks",
            ),
            DatasourceSchemaField(
                key="dim",
                label="向量维度",
                type="number",
                default=1024,
            ),
            DatasourceSchemaField(
                key="username",
                label="用户名",
                type="text",
            ),
            DatasourceSchemaField(
                key="password",
                label="密码",
                type="password",
                sensitive=True,
            ),
            DatasourceSchemaField(
                key="api_key",
                label="API Key",
                type="password",
                sensitive=True,
            ),
            DatasourceSchemaField(
                key="verify_certs",
                label="校验证书",
                type="boolean",
                default=True,
            ),
        ],
    ),
    "postgresql": DatasourceSchema(
        type="postgresql",
        label="PostgreSQL (pgvector)",
        fields=[
            DatasourceSchemaField(
                key="dsn",
                label="DSN",
                type="text",
                required=True,
                sensitive=True,
                default="postgresql://postgres:postgres@127.0.0.1:5432/postgres",
                help="可能包含凭证，请按本地权限妥善保管。",
            ),
            DatasourceSchemaField(
                key="table",
                label="数据表",
                type="text",
                default="kb_chunks",
            ),
            DatasourceSchemaField(
                key="dim",
                label="向量维度",
                type="number",
                default=1024,
            ),
        ],
    ),
    "mysql": DatasourceSchema(
        type="mysql",
        label="MySQL",
        fields=[
            DatasourceSchemaField(
                key="host",
                label="主机",
                type="text",
                default="127.0.0.1",
            ),
            DatasourceSchemaField(
                key="port",
                label="端口",
                type="number",
                default=3306,
            ),
            DatasourceSchemaField(
                key="user",
                label="用户",
                type="text",
                default="root",
            ),
            DatasourceSchemaField(
                key="password",
                label="密码",
                type="password",
                sensitive=True,
                default="",
            ),
            DatasourceSchemaField(
                key="database",
                label="数据库",
                type="text",
                default="kb",
            ),
            DatasourceSchemaField(
                key="table",
                label="数据表",
                type="text",
                default="kb_chunks",
            ),
            DatasourceSchemaField(
                key="dim",
                label="向量维度",
                type="number",
                default=1024,
            ),
            DatasourceSchemaField(
                key="max_scan_rows",
                label="最大扫描行数",
                type="number",
                default=100_000,
                help="MySQL 适配器为 O(N) 扫描，建议仅用于小规模知识库。",
            ),
        ],
    ),
}


@router.get("/schemas", response_model=dict[str, DatasourceSchema])
async def list_schemas() -> dict[str, DatasourceSchema]:
    """Return per-adapter option schemas for the Settings form.

    This is a read-only catalog: the server does not persist the schema, and
    existing JSON-only configs keep working unchanged.
    """
    return {type_name: OPTIONS_SCHEMAS[type_name] for type_name in all_types() if type_name in OPTIONS_SCHEMAS}


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


class FailoverResponse(BaseModel):
    names: list[str]


class FailoverUpsert(BaseModel):
    names: list[str]


async def failover_datasource() -> dict | None:
    """Try configured failover candidates and hot-switch to the first healthy one.

    Returns ``{"from": name, "to": name}`` on success or ``None`` when no
    candidate is available/healthy. Used by the health monitor.
    """
    store = _store_required()
    if _controller is None:
        return None
    active_cfg = store.get_active()
    active_name = active_cfg["name"] if active_cfg is not None else None
    candidates = [name for name in store.get_failover() if name != active_name]
    for name in candidates:
        cfg = store.get(name)
        if cfg is None:
            continue
        ds = None
        try:
            ds = build(
                DatasourceConfig(
                    name=cfg["name"],
                    type=cfg["type"],
                    options={**cfg.get("options", {}), "dim": _embedder_dim},
                )
            )
            h = await ds.health()
            if not h.ok:
                await ds.close()
                continue
        except Exception:  # noqa: BLE001
            if ds is not None:
                try:
                    await ds.close()
                except Exception:  # noqa: BLE001
                    pass
            continue

        await _controller.replace_datasource(ds)
        store.activate(name)
        chunks_api.set_active_datasource(ds)
        health_api.update_active_datasource(ds, source="active")
        log.warning(
            "datasource.failover",
            from_name=active_name,
            to_name=name,
            type=cfg["type"],
        )
        return {"from": active_name, "to": name}
    log.warning("datasource.failover_exhausted", candidates=candidates)
    return None


async def recover_primary() -> dict | None:
    """Switch back to the first failover candidate when it is healthy again.

    Returns ``{"from": name, "to": name}`` on success or ``None`` when the
    primary is already active, unavailable, or unhealthy.
    """
    store = _store_required()
    if _controller is None:
        return None
    order = store.get_failover()
    if not order:
        return None
    primary_name = order[0]
    active_cfg = store.get_active()
    active_name = active_cfg["name"] if active_cfg is not None else None
    if active_name == primary_name:
        return None
    cfg = store.get(primary_name)
    if cfg is None:
        return None

    ds = None
    try:
        ds = build(
            DatasourceConfig(
                name=cfg["name"],
                type=cfg["type"],
                options={**cfg.get("options", {}), "dim": _embedder_dim},
            )
        )
        h = await ds.health()
        if not h.ok:
            await ds.close()
            return None
    except Exception:  # noqa: BLE001
        if ds is not None:
            try:
                await ds.close()
            except Exception:  # noqa: BLE001
                pass
        return None

    await _controller.replace_datasource(ds)
    store.activate(primary_name)
    chunks_api.set_active_datasource(ds)
    health_api.update_active_datasource(ds, source="active")
    log.info(
        "datasource.failover_recovered",
        from_name=active_name,
        to_name=primary_name,
        type=cfg["type"],
    )
    return {"from": active_name, "to": primary_name}


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


@router.post("/configs/{name}/tested", response_model=DatasourceConfigResponse)
async def mark_config_tested(name: str) -> DatasourceConfigResponse:
    """Stamp ``last_tested_at`` after the user verifies a saved config."""
    store = _store_required()
    cfg = store.get(name)
    if cfg is None:
        raise HTTPException(status_code=404, detail=f"no such datasource config: {name}")
    store.mark_tested(name)
    cfg = store.get(name)
    return DatasourceConfigResponse(
        name=cfg["name"],
        type=cfg["type"],
        options=cfg.get("options", {}),
        saved_at=cfg.get("saved_at", ""),
        last_tested_at=cfg.get("last_tested_at"),
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


@router.post("/active/{name}/switch", response_model=DatasourceConfigResponse)
async def switch_active_now(name: str) -> DatasourceConfigResponse:
    """Hot-swap the running active datasource without restarting the server.

    Unlike ``PUT /active/{name}`` (which only persists the pointer for the
    next start), this endpoint builds and probes the adapter, waits for any
    in-flight write/search on the blackboard, swaps the shared resource, and
    then persists the pointer so the next start stays consistent.
    """
    store = _store_required()
    cfg = store.get(name)
    if cfg is None:
        raise HTTPException(status_code=404, detail=f"no such datasource config: {name}")
    if _controller is None:
        raise HTTPException(
            status_code=503,
            detail="blackboard controller not initialized; cannot hot-switch",
        )

    ds = None
    try:
        ds = build(
            DatasourceConfig(
                name=cfg["name"],
                type=cfg["type"],
                options={**cfg.get("options", {}), "dim": _embedder_dim},
            )
        )
        h = await ds.health()
        if not h.ok:
            raise HTTPException(
                status_code=400,
                detail=f"datasource health check failed: {h.message}",
            )
    except HTTPException:
        if ds is not None:
            await ds.close()
        raise
    except Exception as e:  # noqa: BLE001
        if ds is not None:
            await ds.close()
        raise HTTPException(status_code=400, detail=f"invalid config: {e}") from e

    await _controller.replace_datasource(ds)
    saved = store.activate(name)
    chunks_api.set_active_datasource(ds)
    health_api.update_active_datasource(ds, source="active")
    log.info("datasource.switched", name=cfg["name"], type=cfg["type"])
    return DatasourceConfigResponse(
        name=saved["name"],
        type=saved["type"],
        options=saved.get("options", {}),
        saved_at=saved.get("saved_at", ""),
        last_tested_at=saved.get("last_tested_at"),
    )


@router.get("/failover", response_model=FailoverResponse)
async def get_failover() -> FailoverResponse:
    store = _store_required()
    return FailoverResponse(names=store.get_failover())


@router.put("/failover", response_model=FailoverResponse)
async def set_failover(req: FailoverUpsert) -> FailoverResponse:
    store = _store_required()
    names = store.set_failover(req.names)
    return FailoverResponse(names=names)


@router.delete("/failover", response_model=FailoverResponse)
async def clear_failover() -> FailoverResponse:
    store = _store_required()
    store.set_failover([])
    return FailoverResponse(names=[])


@router.delete("/active")
async def clear_active() -> dict:
    _store_required().deactivate()
    return {"name": None, "deleted": True}
