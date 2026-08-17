"""Search API: POST /v1/search.

The endpoint is wired by main.py to a configured RetrievalPipeline. If no
embedder/datasource are configured, we return a clear 503.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.observability.models import Hit
from app.pipeline.retrieval import RetrievalPipeline
from app.observability.models import new_id

router = APIRouter(prefix="/v1/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    datasource: str | None = None
    filter: dict[str, Any] | None = None


class SearchResponse(BaseModel):
    hits: list[Hit]


_pipeline: RetrievalPipeline | None = None
_controller = None


def set_pipeline(p: RetrievalPipeline | None) -> None:
    global _pipeline
    _pipeline = p


def set_controller(controller) -> None:
    global _controller
    _controller = controller


def get_pipeline() -> RetrievalPipeline | None:
    return _pipeline


def get_controller():
    return _controller


@router.post("", response_model=SearchResponse)
async def search(req: SearchRequest) -> SearchResponse:
    if get_controller() is not None and get_pipeline() is None:
        if not req.query.strip():
            return SearchResponse(hits=[])
        snapshot = await get_controller().submit_search(
            new_id(),
            query=req.query,
            top_k=req.top_k,
            filter=req.filter,
        )
        result = next(
            (entry for entry in snapshot if entry.kind == "search_result"),
            None,
        )
        if result is None:
            return SearchResponse(hits=[])
        return SearchResponse(hits=[Hit(**hit) for hit in result.payload["hits"]])

    p = get_pipeline()
    if p is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "search pipeline not configured; set KB_EMBED_BACKEND and a default datasource"
            ),
        )
    hits = await p.search(req.query, top_k=req.top_k, filter=req.filter)
    return SearchResponse(hits=hits)
