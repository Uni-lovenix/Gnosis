"""FastAPI application entrypoint."""
from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI

from app.api import chunks as chunks_api
from app.api import backups as backups_api
from app.api import datasources as datasources_api
from app.api import files as files_api
from app.api import ha as ha_api
from app.api import health as health_api
from app.api.middleware import install_request_context
from app.api import search as search_api
from app.config.settings import get_settings
from app.datasources.base import DatasourceConfig
from app.datasources.factory import build as build_datasource
from app.datasources.registry import all_types  # noqa: F401  (populate registry)
from app.embedding import (  # noqa: F401  (populate registry)
    BGEM3Embedder,
    HashMockEmbedder,
    OpenAICompatEmbedder,
)
from app.embedding.base import EmbedderConfig
from app.embedding.factory import build_embedder
from app.observability.datasource_store import DatasourceStore
from app.observability.backup import backup_if_due
from app.observability.logging import configure_logging, get_logger
from app.observability.task_store import TaskStore
from app.blackboard.control import BlackboardController, ResourceManager
from app.blackboard.core import Blackboard
from app.blackboard.events import BlackboardEventBus
from app.blackboard.projection import BlackboardProjector
from app.blackboard.registry import KnowledgeSourceRegistry
from app.blackboard.resources import DatasourceResource
from app.blackboard.sources import (
    BrowseKS,
    ChunkEmbeddingKS,
    ChunkTextKS,
    ParseFileKS,
    QueryEmbeddingKS,
    SemanticRetrievalKS,
    WriteDatasourceKS,
)
from app.blackboard.vocabulary import BlackboardVocabulary

settings = get_settings()
configure_logging(level=settings.log_level, json_output=settings.log_json)
log = get_logger("kb-server")


def _build_datasource_from_config(
    cfg: dict, embedder_dim: int, fallback_log: bool = True
):
    """Build a live datasource from a stored config dict.

    Returns ``None`` on build failure so callers can fall back gracefully.
    """
    try:
        ds = build_datasource(
            DatasourceConfig(
                name=cfg["name"],
                type=cfg["type"],
                options=cfg.get("options", {}),
            )
        )
        return ds
    except Exception as e:  # noqa: BLE001
        if fallback_log:
            log.warning("datasource.config_load_failed", reason=str(e), cfg=cfg.get("name"))
        return None


def _resolve_default_datasource(data_dir: Path, embedder_dim: int):
    """Pick the active datasource in priority order.

    1. ``datasources.json`` -> ``active`` config (user-saved via UI).
    2. In-memory vector (always works).

    Returns ``(datasource, source_label)`` where ``source_label`` is one of
    ``"active"``, ``"default"``, ``"none"`` for diagnostic logging.
    """
    ds_store = DatasourceStore(data_dir / "datasources.json")
    datasources_api.set_store(ds_store)
    active_cfg = ds_store.get_active()
    if active_cfg is not None:
        chosen = _build_datasource_from_config(active_cfg, embedder_dim)
        if chosen is not None:
            log.info(
                "datasource.from_saved",
                name=active_cfg["name"],
                type=active_cfg["type"],
            )
            return chosen, "active"
        log.warning(
            "datasource.active_load_failed",
            name=active_cfg["name"],
            type=active_cfg["type"],
        )
    try:
        chosen = build_datasource(
            DatasourceConfig(
                name="default",
                type="vector",
                options={"backend": "memory", "dim": embedder_dim},
            )
        )
        log.info("datasource.default_in_memory", dim=embedder_dim)
        return chosen, "default"
    except Exception as e:  # noqa: BLE001
        log.warning("datasource.init_failed", reason=str(e))
        return None, "none"


def _build_default_components():
    """Wire a default embedder + datasource + retrieval pipeline.

    Embedder priority (matches ``Settings.embed_backend`` default):
    1. ``openai-compat`` — production default. Talks to Ollama at
       ``KB_OPENAI_BASE_URL`` by default; falls back to ``mock-hash`` if the
       endpoint cannot be constructed (missing dep, refused connection, …).
    2. ``bge-m3`` — local sentence-transformers snapshot. Falls back to
       ``mock-hash`` if the package is not installed.
    3. ``mock-hash`` — deterministic 1024-dim mock for tests.

    Datasource priority:
    1. ``datasources.json`` -> ``active`` config (user-saved via UI).
    2. In-memory vector (always works).
    """
    backend = settings.embed_backend
    options: dict = {
        "model": settings.embed_model,
        "dim": settings.embed_dim,
        "base_url": settings.openai_base_url or "",
        "api_key": settings.openai_api_key or "",
        "model_openai": settings.openai_model or settings.embed_model,
        "timeout": 60.0,
    }
    try:
        embedder = build_embedder(EmbedderConfig(name="default", type=backend, options=options))
        log.info("embedder.ready", backend=backend, dim=embedder.dim)
    except Exception as e:  # noqa: BLE001
        # Single fallback path: any failure → deterministic mock so the API
        # still responds. The log event names the missing dep + remediation.
        hint = _embedder_hint(backend, str(e))
        log.warning("embedder.fallback_to_mock", reason=str(e), backend=backend, hint=hint)
        embedder = build_embedder(
            EmbedderConfig(name="mock", type="mock-hash", options={"dim": settings.embed_dim})
        )

    data_dir = Path(settings.data_dir).expanduser()
    chosen, _source = _resolve_default_datasource(data_dir, embedder.dim)
    health_api.set_runtime_state(
        embedder=embedder,
        embedder_backend=embedder.type,
        embedder_fallback=embedder.type != settings.embed_backend,
        datasource=chosen,
        datasource_source=_source,
        data_dir=str(data_dir),
    )
    return embedder, chosen


def _build_blackboard_controller(embedder, datasource, projection_path):
    """Build the blackboard controller used by the default production path."""
    vocabulary = BlackboardVocabulary()
    event_bus = BlackboardEventBus()
    blackboard = Blackboard(vocabulary=vocabulary, event_bus=event_bus)
    resources = ResourceManager(
        {
            "parser": 1,
            "chunker": 1,
            "embedder": 1,
            "datasource_write": 1,
            "search": 1,
            "llm": 1,
        }
    )
    registry = KnowledgeSourceRegistry(vocabulary, known_resources=set(resources.capacities))
    datasource_resource = DatasourceResource(datasource)
    controller = BlackboardController(
        blackboard=blackboard,
        event_bus=event_bus,
        registry=registry,
        resource_manager=resources,
        datasource_resource=datasource_resource,
    )

    controller.register_knowledge_source(ParseFileKS())
    controller.register_knowledge_source(ChunkTextKS())
    controller.register_knowledge_source(ChunkEmbeddingKS(embedder))
    controller.register_knowledge_source(WriteDatasourceKS(datasource_resource))
    controller.register_knowledge_source(QueryEmbeddingKS(embedder))
    controller.register_knowledge_source(SemanticRetrievalKS(datasource_resource))
    controller.register_knowledge_source(BrowseKS(datasource_resource))

    projector = BlackboardProjector(projection_path)
    event_bus.subscribe(projector.on_change)
    log.info(
        "blackboard.ready",
        knowledge_sources=[ks.descriptor.ks_id for ks in registry.list()],
        projection=str(projection_path),
    )
    return controller


def _embedder_hint(backend: str, reason: str) -> str:
    """Return a one-line remediation hint per backend.

    The fallback log surfaces this directly so the user knows the single
    command to run before restarting the server.
    """
    if backend == "openai-compat":
        return (
            "start Ollama with `ollama serve` and pull bge-m3 with "
            "`ollama pull bge-m3`; or set KB_EMBED_BACKEND=mock-hash for tests"
        )
    if backend == "bge-m3":
        return (
            "install with `pip install -e '.[embedding-local]'` and download "
            "weights via `scripts/download_bge_m3.sh`"
        )
    return f"unset KB_EMBED_BACKEND or fix the configured backend: {reason}"


def create_app() -> FastAPI:
    app = FastAPI(
        title="KB Server",
        version="0.1.0",
        description="灵知 (Gnosis) 后端：文件解析、embedding、向量检索。",
    )
    install_request_context(app)

    data_dir = Path(settings.data_dir).expanduser()
    task_store = TaskStore(data_dir / "tasks.db")
    files_api.set_task_store(task_store)

    embedder, ds = _build_default_components()
    if ds is not None:
        controller = _build_blackboard_controller(embedder, ds, task_store.path)
        datasources_api.set_controller(controller)
        datasources_api.set_embedder_dim(embedder.dim)
        datasources_api.set_active_datasource(ds)
        files_api.set_controller(controller)
        search_api.set_controller(controller)
        chunks_api.set_controller(controller)
        chunks_api.set_active_datasource(ds)

    app.include_router(health_api.router)
    app.include_router(ha_api.router)
    app.include_router(datasources_api.router)
    app.include_router(backups_api.router)
    app.include_router(files_api.router)
    app.include_router(search_api.router)
    app.include_router(chunks_api.router)
    return app


# Module-level singleton that respects ``$KB_DATA_DIR`` (or its default).
# Tests can override by setting ``os.environ['KB_DATA_DIR']`` before import.
app = create_app()
_auto_backup_tasks: set[asyncio.Task] = set()
_health_monitor_tasks: set[asyncio.Task] = set()


async def _auto_backup_loop(
    data_dir: Path,
    backup_root: Path,
    keep: int,
    interval_hours: float,
) -> None:
    log.info(
        "backup.auto_scheduled",
        data_dir=str(data_dir),
        backup_dir=str(backup_root),
        interval_hours=interval_hours,
        keep=keep,
    )
    while True:
        try:
            created, path = backup_if_due(data_dir, backup_root, keep, interval_hours)
            if created:
                log.info("backup.auto_created", path=str(path))
            else:
                log.info("backup.auto_skipped", latest=str(path))
        except Exception as exc:  # noqa: BLE001
            log.warning("backup.auto_failed", reason=str(exc))
        await asyncio.sleep(3600)


def _start_auto_backup() -> None:
    if not settings.backup_auto:
        return
    data_dir = Path(settings.data_dir).expanduser()
    backup_root = Path(settings.backup_dir or str(data_dir / "backups")).expanduser()
    task = asyncio.create_task(
        _auto_backup_loop(
            data_dir,
            backup_root,
            settings.backup_keep,
            settings.backup_interval_hours,
        )
    )
    _auto_backup_tasks.add(task)
    task.add_done_callback(_auto_backup_tasks.discard)


async def _health_monitor_loop(interval_seconds: int) -> None:
    log.info("health.monitor_scheduled", interval_seconds=interval_seconds)
    previous_ok: bool | None = None
    consecutive_ds_failures = 0
    consecutive_ds_healthy = 0
    while True:
        try:
            checks = await health_api.refresh_runtime_health()
            ok = all(c.ok for c in checks)
            if previous_ok is not None and ok != previous_ok:
                event = "health.monitor_recovered" if ok else "health.monitor_degraded"
                log.warning(
                    event,
                    checks=[{"name": c.name, "ok": c.ok, "message": c.message} for c in checks],
                )
            previous_ok = ok
            ds_check = next((c for c in checks if c.name == "datasource"), None)
            if ds_check is not None and ds_check.ok is False:
                consecutive_ds_failures += 1
                if (
                    settings.failover_enabled
                    and consecutive_ds_failures == settings.failover_consecutive_failures
                ):
                    result = await datasources_api.failover_datasource()
                    if result is not None:
                        consecutive_ds_failures = 0
            else:
                consecutive_ds_failures = 0
                if settings.failover_enabled and settings.failover_auto_recover:
                    consecutive_ds_healthy += 1
                    if consecutive_ds_healthy == settings.failover_recover_consecutive_checks:
                        await datasources_api.recover_primary()
                        consecutive_ds_healthy = 0
                else:
                    consecutive_ds_healthy = 0
        except Exception as exc:  # noqa: BLE001
            log.warning("health.monitor_failed", reason=str(exc))
        await asyncio.sleep(interval_seconds)


def _start_health_monitor() -> None:
    if not settings.health_monitor:
        return
    task = asyncio.create_task(
        _health_monitor_loop(settings.health_monitor_interval_seconds)
    )
    _health_monitor_tasks.add(task)
    task.add_done_callback(_health_monitor_tasks.discard)


@app.on_event("startup")
async def _on_startup() -> None:
    log.info(
        "kb-server.startup",
        host=settings.host,
        port=settings.port,
        embed_backend=settings.embed_backend,
        embed_dim=settings.embed_dim,
        openai_base_url=settings.openai_base_url,
        openai_model=settings.openai_model,
        datasources=all_types(),
    )
    _start_auto_backup()
    _start_health_monitor()


@app.on_event("shutdown")
async def _on_shutdown() -> None:
    for task in list(_auto_backup_tasks) + list(_health_monitor_tasks):
        task.cancel()
    for task in list(_auto_backup_tasks) + list(_health_monitor_tasks):
        try:
            await task
        except asyncio.CancelledError:
            pass
    _auto_backup_tasks.clear()
    _health_monitor_tasks.clear()


def main() -> None:
    """Entrypoint for `python -m app.main` (used by the desktop ServerManager)."""
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
