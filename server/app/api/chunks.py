"""/v1/chunks — read-only browse endpoint over the active datasource (G7).

Returns a paginated list of stored chunks plus a per-document rollup so the
desktop UI can render an "imported data inspector". The endpoint requires
the active datasource to advertise the ``chunk_list`` capability; otherwise
it returns 501 with a clear message that lists the migration paths.

This endpoint is intentionally a thin wrapper over the active datasource
instance bound at server startup (the same instance the import pipeline
uses). The active datasource handle is set by ``app.main`` after
``_resolve_default_datasource`` succeeds.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.datasources.base import DataSource, NotSupportedError
from app.observability.logging import get_logger
from app.observability.models import ChunkSummary, DocumentSummary

log = get_logger(__name__)

router = APIRouter(prefix="/v1/chunks", tags=["chunks"])


# Active datasource handle set by ``app.main`` after _resolve_default_datasource
# succeeds. Tests can override by calling ``set_active_datasource``.
_active_datasource: DataSource | None = None


def set_active_datasource(ds: DataSource | None) -> None:
    global _active_datasource
    _active_datasource = ds


def get_active_datasource() -> DataSource:
    if _active_datasource is None:
        raise HTTPException(
            status_code=503,
            detail="no active datasource bound; check server startup logs",
        )
    return _active_datasource


class BrowseResponse(BaseModel):
    chunks: list[ChunkSummary]
    total: int
    aggregations: dict[str, DocumentSummary]


@router.get("", response_model=BrowseResponse)
async def browse(
    document_id: str | None = Query(None, description="Filter to one document_id"),
    parser: str | None = Query(None, description="Filter to one parser (metadata.parser)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Page size; capped at 100"),
) -> BrowseResponse:
    """Browse chunks stored in the active datasource.

    Adapters that do not implement ``list_chunks`` / ``aggregate_by_document``
    return 501; the message names the missing capability so the UI can show
    a useful "datasource X does not support chunk_list — see RUNBOOK §3"
    banner.
    """
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be in [1, 100]")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be >= 0")

    ds = get_active_datasource()
    caps = ds.capabilities()
    if "chunk_list" not in caps:
        raise HTTPException(
            status_code=501,
            detail=(
                f"datasource '{ds.name}' (type={ds.type}) does not support "
                "chunk_list; see docs/RUNBOOK.md §3 for migration paths"
            ),
        )

    try:
        chunks, total = await ds.list_chunks(
            document_id=document_id,
            parser=parser,
            offset=offset,
            limit=limit,
        )
        aggregations = await ds.aggregate_by_document()
    except NotSupportedError as e:
        # Race: capability says yes but the adapter raised (e.g. dynamic agg
        # failure on ES). Surface as 501 to match the contract.
        log.warning("chunks.browse_not_supported", error=str(e))
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:  # noqa: BLE001
        log.error("chunks.browse_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"browse failed: {e}")

    log.info(
        "chunks.browse",
        document_id=document_id,
        parser=parser,
        offset=offset,
        limit=limit,
        returned=len(chunks),
        total=total,
        aggregations=len(aggregations),
    )
    return BrowseResponse(chunks=chunks, total=total, aggregations=aggregations)