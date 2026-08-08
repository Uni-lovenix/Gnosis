"""FastAPI application entrypoint."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from app.api import chunks as chunks_api
from app.api import datasources as datasources_api
from app.api import files as files_api
from app.api import health as health_api
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
from app.observability.logging import configure_logging, get_logger
from app.observability.task_store import TaskStore
from app.pipeline.retrieval import RetrievalPipeline

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
    return embedder, chosen


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
        description="Personal Knowledge Base backend: parsing, embedding, search.",
    )

    data_dir = Path(settings.data_dir).expanduser()
    task_store = TaskStore(data_dir / "tasks.db")
    files_api.set_task_store(task_store)

    embedder, ds = _build_default_components()
    if ds is not None:
        from app.pipeline.indexing import IndexingPipeline

        files_api.set_pipeline(IndexingPipeline(ds, embedder))
        search_api.set_pipeline(RetrievalPipeline(ds, embedder))
        # G7: bind the same DataSource to the browse endpoint so users can
        # inspect what they just imported. Per G2 design, the active handle
        # only changes on server restart; runtime hot-swap is intentionally
        # out of scope (see RUNBOOK §2).
        chunks_api.set_active_datasource(ds)

    app.include_router(health_api.router)
    app.include_router(datasources_api.router)
    app.include_router(files_api.router)
    app.include_router(search_api.router)
    app.include_router(chunks_api.router)
    return app


# Module-level singleton that respects ``$KB_DATA_DIR`` (or its default).
# Tests can override by setting ``os.environ['KB_DATA_DIR']`` before import.
app = create_app()


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
