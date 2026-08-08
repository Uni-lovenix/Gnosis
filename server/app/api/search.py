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

router = APIRouter(prefix="/v1/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    datasource: str | None = None
    filter: dict[str, Any] | None = None


class SearchResponse(BaseModel):
    hits: list[Hit]


_pipeline: RetrievalPipeline | None = None


def set_pipeline(p: RetrievalPipeline | None) -> None:
    global _pipeline
    _pipeline = p


def get_pipeline() -> RetrievalPipeline:
    if _pipeline is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "search pipeline not configured; set KB_EMBED_BACKEND and a default datasource"
            ),
        )
    return _pipeline


@router.post("", response_model=SearchResponse)
async def search(req: SearchRequest) -> SearchResponse:
    p = get_pipeline()
    hits = await p.search(req.query, top_k=req.top_k, filter=req.filter)
    return SearchResponse(hits=hits)