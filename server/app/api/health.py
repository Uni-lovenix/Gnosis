"""GET /v1/health — minimal liveness probe."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.config.settings import get_settings
from app.datasources.registry import all_types

router = APIRouter(prefix="/v1/health", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"
    embed_backend: str
    embed_dim: int
    datasources: list[str]


@router.get("", response_model=HealthResponse)
async def health() -> HealthResponse:
    s = get_settings()
    return HealthResponse(
        status="ok",
        embed_backend=s.embed_backend,
        embed_dim=s.embed_dim,
        datasources=all_types(),
    )