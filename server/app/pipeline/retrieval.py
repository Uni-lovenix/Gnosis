"""Retrieval pipeline: embed query → search datasource → return hits."""
from __future__ import annotations

from typing import Any

from app.datasources.base import DataSource
from app.embedding.base import Embedder
from app.observability.models import Hit


class RetrievalPipeline:
    def __init__(self, datasource: DataSource, embedder: Embedder) -> None:
        self.datasource = datasource
        self.embedder = embedder

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter: dict[str, Any] | None = None,
    ) -> list[Hit]:
        if not query.strip():
            return []
        vecs = await self.embedder.embed([query])
        return await self.datasource.search(vecs[0], top_k=top_k, filter=filter)