"""Elasticsearch 8+ adapter using ``dense_vector``.

The adapter indexes chunks into a single index per datasource. Vectors use
cosine similarity. Metadata is stored under ``_source`` alongside text.

In addition to the minimum capability set (add / search / delete / health)
this adapter implements ``list_chunks`` and ``aggregate_by_document`` for
the browse UI (G7), advertised via the ``chunk_list`` capability.
"""
from __future__ import annotations

import time
from typing import Any, Iterable

from pydantic import Field

from app.datasources.base import (
    DataSource,
    DatasourceConfig,
    DatasourceError,
    HealthStatus,
    register_datasource,
)
from app.observability.logging import get_logger
from app.observability.models import Chunk, ChunkSummary, DocumentSummary, Hit

log = get_logger(__name__)

_BROWSE_TEXT_MAX = 240  # server-side truncation for the browse endpoint
_BROWSE_AGG_DOCS = 1000  # cap on documents returned by aggregate_by_document


class ElasticsearchConfig(DatasourceConfig):
    type: str = "elasticsearch"
    options: dict[str, Any] = Field(
        default_factory=lambda: {
            "hosts": ["http://127.0.0.1:9200"],
            "index": "kb_chunks",
            "dim": 1024,
            "username": None,
            "password": None,
            "api_key": None,
            "verify_certs": True,
        }
    )


def _client_or_error(cfg: ElasticsearchConfig):
    try:
        from elasticsearch import Elasticsearch  # type: ignore
    except ImportError as e:  # pragma: no cover - exercised on missing dep
        raise DatasourceError(
            "elasticsearch package not installed. `pip install -e '.[es]'`."
        ) from e

    opts = cfg.options
    kwargs: dict[str, Any] = {"hosts": opts.get("hosts", ["http://127.0.0.1:9200"]), "verify_certs": opts.get("verify_certs", True)}
    if opts.get("api_key"):
        kwargs["api_key"] = opts["api_key"]
    elif opts.get("username") and opts.get("password"):
        kwargs["basic_auth"] = (opts["username"], opts["password"])
    return Elasticsearch(**kwargs)


class ElasticsearchAdapter(DataSource):
    type = "elasticsearch"

    def __init__(self, config: DatasourceConfig) -> None:
        if not isinstance(config, ElasticsearchConfig):
            config = ElasticsearchConfig(**config.model_dump())
        super().__init__(config)
        self._cfg: ElasticsearchConfig = config  # type: ignore[assignment]
        self._client = _client_or_error(self._cfg)
        self._dim = int(self._cfg.options.get("dim", 1024))
        self._index = self._cfg.options.get("index", "kb_chunks")

    # ---- Capabilities ---------------------------------------------------------

    def capabilities(self) -> set[str]:
        return {"metadata_filter", "delete_by_filter", "bm25_hybrid", "chunk_list", "dump"}

    # ---- Bootstrap ------------------------------------------------------------

    def ensure_index(self) -> None:
        if self._client.indices.exists(index=self._index):
            return
        body = {
            "mappings": {
                "properties": {
                    "chunk_id": {"type": "keyword"},
                    "document_id": {"type": "keyword"},
                    "text": {"type": "text"},
                    "metadata": {"type": "object", "enabled": True},
                    "vector": {
                        "type": "dense_vector",
                        "dims": self._dim,
                        "index": True,
                        "similarity": "cosine",
                    },
                }
            }
        }
        self._client.indices.create(index=self._index, **body)
        log.info("elasticsearch.index.created", index=self._index, dim=self._dim)

    # ---- Operations -----------------------------------------------------------

    async def add(self, chunks: Iterable[Chunk]) -> list[str]:
        ids: list[str] = []
        ops: list[dict[str, Any]] = []
        for c in chunks:
            if c.vector is None:
                raise DatasourceError(f"chunk {c.id} has no vector; embed first")
            ids.append(c.id)
            ops.append({"index": {"_index": self._index, "_id": c.id}})
            ops.append(
                {
                    "chunk_id": c.id,
                    "document_id": c.document_id,
                    "text": c.text,
                    "metadata": c.metadata,
                    "vector": c.vector,
                }
            )
        if ops:
            self.ensure_index()
            resp = self._client.bulk(operations=ops, refresh="wait_for")
            if resp.get("errors"):
                raise DatasourceError(f"bulk errors: {resp}")
        return ids

    async def search(
        self,
        vector: list[float],
        top_k: int = 5,
        filter: dict[str, Any] | None = None,
    ) -> list[Hit]:
        body: dict[str, Any] = {
            "knn": {
                "field": "vector",
                "query_vector": vector,
                "k": top_k,
                "num_candidates": max(50, top_k * 10),
            },
            "size": top_k,
            "_source": ["chunk_id", "document_id", "text", "metadata"],
        }
        if filter:
            body["knn"]["filter"] = {"term": filter}
        resp = self._client.search(index=self._index, **body)
        return [
            Hit(
                id=h["_source"].get("chunk_id", h["_id"]),
                score=float(h["_score"] or 0.0),
                text=h["_source"].get("text", ""),
                metadata=h["_source"].get("metadata", {}),
                document_id=h["_source"].get("document_id"),
            )
            for h in resp["hits"]["hits"]
        ]

    async def delete(self, ids: Iterable[str]) -> int:
        id_list = list(ids)
        if not id_list:
            return 0
        resp = self._client.bulk(
            operations=[{"delete": {"_index": self._index, "_id": i}} for i in id_list],
            refresh="wait_for",
        )
        return sum(1 for item in resp.get("items", []) if "delete" in item)

    async def health(self) -> HealthStatus:
        start = time.perf_counter()
        try:
            info = self._client.info()
            return HealthStatus(
                ok=True,
                latency_ms=(time.perf_counter() - start) * 1000,
                message=info.get("version", {}).get("number", "unknown"),
            )
        except Exception as e:  # noqa: BLE001
            return HealthStatus(ok=False, message=str(e))

    # ---- Browse (G7) --------------------------------------------------------

    @staticmethod
    def _truncate(text: str) -> str:
        """Return ``text`` truncated to ``_BROWSE_TEXT_MAX`` characters with a
        trailing ellipsis if it was longer. The original length is reported
        alongside via ``ChunkSummary.text_length``."""
        if len(text) <= _BROWSE_TEXT_MAX:
            return text
        return text[:_BROWSE_TEXT_MAX] + "…"

    async def list_chunks(
        self,
        *,
        document_id: str | None = None,
        parser: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ChunkSummary], int]:
        """List stored chunks with optional filters and pagination.

        ``match_all`` + bool filter; sorted by ``(document_id, chunk_id)`` so
        the same document's chunks cluster together in the UI. We do not
        return ``vector`` (large, not needed for browsing) and limit
        ``_source`` to the fields the UI actually displays.
        """
        filters: list[dict[str, Any]] = []
        if document_id:
            filters.append({"term": {"document_id": document_id}})
        if parser:
            filters.append({"term": {"metadata.parser": parser}})

        body: dict[str, Any] = {
            "query": {"bool": {"filter": filters or [{"match_all": {}}]}},
            "sort": [{"document_id": "asc"}, {"chunk_id": "asc"}],
            "from": max(0, offset),
            "size": max(1, min(limit, 100)),
            "_source": ["chunk_id", "document_id", "text", "metadata"],
        }
        resp = self._client.search(index=self._index, **body)
        hits_raw = resp.get("hits", {}).get("hits", [])
        total_block = resp.get("hits", {}).get("total", {})
        if isinstance(total_block, dict):
            total = int(total_block.get("value", len(hits_raw)))
        else:  # ES < 7.0 fallback
            total = int(total_block or len(hits_raw))

        summaries: list[ChunkSummary] = []
        for h in hits_raw:
            src = h.get("_source", {})
            full_text = src.get("text", "") or ""
            summaries.append(
                ChunkSummary(
                    chunk_id=src.get("chunk_id", h.get("_id", "")),
                    document_id=src.get("document_id", ""),
                    text=self._truncate(full_text),
                    text_length=len(full_text),
                    metadata=src.get("metadata", {}) or {},
                )
            )
        return summaries, total

    async def dump_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[Chunk], int]:
        body: dict[str, Any] = {
            "query": {"match_all": {}},
            "sort": [{"document_id": "asc"}, {"chunk_id": "asc"}],
            "from": max(0, offset),
            "size": max(1, min(limit, 100)),
            "_source": ["chunk_id", "document_id", "text", "metadata"],
        }
        resp = self._client.search(index=self._index, **body)
        hits_raw = resp.get("hits", {}).get("hits", [])
        total_block = resp.get("hits", {}).get("total", {})
        if isinstance(total_block, dict):
            total = int(total_block.get("value", len(hits_raw)))
        else:
            total = int(total_block or len(hits_raw))

        chunks: list[Chunk] = []
        for h in hits_raw:
            src = h.get("_source", {})
            chunks.append(
                Chunk(
                    id=src.get("chunk_id", h.get("_id", "")),
                    document_id=src.get("document_id", ""),
                    text=src.get("text", "") or "",
                    metadata=src.get("metadata", {}) or {},
                )
            )
        return chunks, total

    async def aggregate_by_document(self) -> dict[str, DocumentSummary]:
        """Roll up chunks per ``document_id``: chunk count, distinct parser
        values, sample text from the first chunk.

        Returns ``{}`` when the index has no chunks. Cap at
        ``_BROWSE_AGG_DOCS`` documents so a runaway corpus doesn't blow up
        the payload.
        """
        try:
            resp = self._client.search(
                index=self._index,
                size=0,
                aggs={
                    "by_doc": {
                        "terms": {"field": "document_id", "size": _BROWSE_AGG_DOCS},
                        "aggs": {
                            "parsers": {
                                "terms": {
                                    "field": "metadata.parser",
                                    "size": 10,
                                }
                            },
                            "sample": {
                                "top_hits": {
                                    "size": 1,
                                    "_source": ["chunk_id", "text"],
                                }
                            },
                        },
                    }
                },
            )
        except Exception as e:  # noqa: BLE001
            log.warning("elasticsearch.aggregate_failed", error=str(e))
            return {}

        out: dict[str, DocumentSummary] = {}
        for bucket in resp.get("aggregations", {}).get("by_doc", {}).get("buckets", []):
            doc_id = str(bucket.get("key", ""))
            sample_hits = (
                bucket.get("sample", {}).get("hits", {}).get("hits", [])
            )
            sample_src = sample_hits[0].get("_source", {}) if sample_hits else {}
            parsers = [
                str(b.get("key", "")) for b in bucket.get("parsers", {}).get("buckets", [])
            ]
            out[doc_id] = DocumentSummary(
                document_id=doc_id,
                chunk_count=int(bucket.get("doc_count", 0)),
                parsers=parsers,
                first_chunk_id=sample_src.get("chunk_id"),
                sample_text=self._truncate(sample_src.get("text", "") or ""),
            )
        return out


register_datasource("elasticsearch", ElasticsearchAdapter)
