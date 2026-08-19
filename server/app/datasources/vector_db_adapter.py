"""Vector database adapter.

Default implementation is an in-process store backed by numpy; this keeps the
adapter functional with zero extra dependencies and is suitable for tests and
small personal libraries (≤ ~50k vectors). Production users can switch to
Milvus / Qdrant via the ``backend`` option.

Backend options:
  - ``memory`` (default): pure-Python, cosine via numpy.
  - ``milvus``:        uses ``pymilvus`` to talk to a Milvus server.
"""
from __future__ import annotations

import time
from typing import Any, Iterable

import numpy as np
from pydantic import Field

from app.datasources.base import (
    DataSource,
    DatasourceConfig,
    DatasourceError,
    HealthStatus,
    register_datasource,
)
from app.observability.logging import get_logger
from app.observability.models import Chunk, Hit

log = get_logger(__name__)


class VectorDBConfig(DatasourceConfig):
    type: str = "vector"
    options: dict[str, Any] = Field(
        default_factory=lambda: {
            "backend": "memory",
            "collection": "kb_chunks",
            "dim": 1024,
            "uri": "http://127.0.0.1:19530",  # milvus
        }
    )


class _MemoryBackend:
    def __init__(self, dim: int) -> None:
        self.dim = dim
        self._ids: list[str] = []
        self._vecs: np.ndarray = np.zeros((0, dim), dtype=np.float32)
        self._texts: list[str] = []
        self._meta: list[dict[str, Any]] = []

    def upsert(self, ids: list[str], vecs: np.ndarray, texts: list[str], meta: list[dict[str, Any]]) -> None:
        # remove existing ids first (idempotent add)
        keep_idx = [i for i, x in enumerate(self._ids) if x not in set(ids)]
        self._ids = [self._ids[i] for i in keep_idx]
        self._texts = [self._texts[i] for i in keep_idx]
        self._meta = [self._meta[i] for i in keep_idx]
        self._vecs = self._vecs[keep_idx]
        self._ids.extend(ids)
        self._texts.extend(texts)
        self._meta.extend(meta)
        self._vecs = np.vstack([self._vecs, vecs])

    def search(self, vec: np.ndarray, top_k: int) -> list[tuple[int, float]]:
        if len(self._ids) == 0:
            return []
        norms = np.linalg.norm(self._vecs, axis=1) * np.linalg.norm(vec) + 1e-12
        sims = (self._vecs @ vec) / norms
        idx = np.argsort(-sims)[:top_k]
        return [(int(i), float(sims[i])) for i in idx]

    def delete(self, ids: list[str]) -> int:
        s = set(ids)
        keep_idx = [i for i, x in enumerate(self._ids) if x not in s]
        removed = len(self._ids) - len(keep_idx)
        self._ids = [self._ids[i] for i in keep_idx]
        self._texts = [self._texts[i] for i in keep_idx]
        self._meta = [self._meta[i] for i in keep_idx]
        self._vecs = self._vecs[keep_idx]
        return removed


class _MilvusBackend:
    """Thin Milvus wrapper; lazily imported.

    The collection is created with a custom schema so that the primary key is
    VARCHAR (max_length=64). pymilvus ≥ 3 defaults to int64 auto-id, which
    would clash with the adapter's string ids (``uuid4().hex[:16]``).
    """

    _PK_MAX_LENGTH = 64

    def __init__(self, uri: str, collection: str, dim: int) -> None:
        try:
            from pymilvus import DataType, MilvusClient  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise DatasourceError("pymilvus not installed. `pip install -e '.[vector]'`.") from e
        self.client = MilvusClient(uri=uri)
        self.collection = collection
        self.dim = dim
        if not self.client.has_collection(collection):
            schema = MilvusClient.create_schema(auto_id=False)
            schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=self._PK_MAX_LENGTH)
            schema.add_field("vector", DataType.FLOAT_VECTOR, dim=dim)
            schema.add_field("text", DataType.VARCHAR, max_length=4096)
            schema.add_field("metadata", DataType.JSON)
            self.client.create_collection(
                collection_name=collection,
                schema=schema,
                metric_type="COSINE",
            )

    def upsert(self, ids, vecs, texts, meta) -> None:  # noqa: D401
        rows = [
            {"id": i, "vector": v.tolist(), "text": t, "metadata": m}
            for i, v, t, m in zip(ids, vecs, texts, meta)
        ]
        self.client.upsert(collection_name=self.collection, data=rows)

    def search(self, vec: np.ndarray, top_k: int) -> list[tuple[int, float]]:
        res = self.client.search(
            collection_name=self.collection,
            data=[vec.tolist()],
            limit=top_k,
            output_fields=["text", "metadata"],
        )
        out: list[tuple[int, float]] = []
        for hit in res[0]:
            # Milvus returns by primary key (string in our case); we need its index
            out.append((hit["id"], float(hit["distance"])))
        return out

    def delete(self, ids: list[str]) -> int:
        self.client.delete(collection_name=self.collection, ids=ids)
        return len(ids)


class VectorDBAdapter(DataSource):
    type = "vector"

    def __init__(self, config: DatasourceConfig) -> None:
        if not isinstance(config, VectorDBConfig):
            config = VectorDBConfig(**config.model_dump())
        super().__init__(config)
        self._cfg: VectorDBConfig = config  # type: ignore[assignment]
        opts = self._cfg.options
        self._dim = int(opts.get("dim", 1024))
        backend = opts.get("backend", "memory")
        if backend == "memory":
            self._backend: Any = _MemoryBackend(self._dim)
        elif backend == "milvus":
            self._backend = _MilvusBackend(
                uri=opts["uri"],
                collection=opts["collection"],
                dim=self._dim,
            )
        else:
            raise DatasourceError(f"unknown vector backend: {backend}")
        log.info("vector.ready", backend=backend, dim=self._dim)

    def capabilities(self) -> set[str]:
        caps = {"metadata_filter"}
        if isinstance(self._backend, _MemoryBackend):
            caps.add("dump")
        return caps

    async def add(self, chunks: Iterable[Chunk]) -> list[str]:
        ids: list[str] = []
        vecs: list[np.ndarray] = []
        texts: list[str] = []
        meta: list[dict[str, Any]] = []
        for c in chunks:
            if c.vector is None:
                raise DatasourceError(f"chunk {c.id} has no vector; embed first")
            ids.append(c.id)
            vecs.append(np.asarray(c.vector, dtype=np.float32))
            texts.append(c.text)
            meta.append(c.metadata)
        if not ids:
            return ids
        self._backend.upsert(ids, np.vstack(vecs), texts, meta)
        return ids

    async def search(
        self,
        vector: list[float],
        top_k: int = 5,
        filter: dict[str, Any] | None = None,
    ) -> list[Hit]:
        q = np.asarray(vector, dtype=np.float32)
        results = self._backend.search(q, top_k)
        if isinstance(self._backend, _MemoryBackend):
            hits = [
                Hit(
                    id=self._backend._ids[i],
                    score=s,
                    text=self._backend._texts[i],
                    metadata=self._backend._meta[i],
                    document_id=self._backend._meta[i].get("document_id"),
                )
                for i, s in results
                if not filter or _matches(self._backend._meta[i], filter)
            ]
        else:
            # For Milvus, fetch metadata via get
            ids_only = [r[0] for r in results]
            rows = self._backend.client.get(
                collection_name=self._backend.collection, ids=ids_only, output_fields=["text", "metadata"]
            )
            by_id = {r["id"]: r for r in rows}
            hits = []
            for idx, score in results:
                row = by_id.get(idx)
                if row is None:
                    continue
                if filter and not _matches(row.get("metadata", {}), filter):
                    continue
                hits.append(
                    Hit(
                        id=idx,
                        score=score,
                        text=row["text"],
                        metadata=row.get("metadata", {}),
                        document_id=row.get("metadata", {}).get("document_id"),
                    )
                )
        return hits

    async def delete(self, ids: Iterable[str]) -> int:
        return self._backend.delete(list(ids))

    async def dump_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[Chunk], int]:
        if not isinstance(self._backend, _MemoryBackend):
            from app.datasources.base import NotSupportedError

            raise NotSupportedError("vector milvus backend does not support dump_all yet")
        start = max(0, offset)
        end = min(len(self._backend._ids), start + max(1, limit))
        rows: list[Chunk] = []
        for i in range(start, end):
            meta = dict(self._backend._meta[i])
            rows.append(
                Chunk(
                    id=self._backend._ids[i],
                    document_id=meta.get("document_id", ""),
                    text=self._backend._texts[i],
                    metadata=meta,
                )
            )
        return rows, len(self._backend._ids)

    async def health(self) -> HealthStatus:
        start = time.perf_counter()
        try:
            if isinstance(self._backend, _MilvusBackend):
                # quick liveness check
                self._backend.client.list_collections()
            return HealthStatus(ok=True, latency_ms=(time.perf_counter() - start) * 1000)
        except Exception as e:  # noqa: BLE001
            return HealthStatus(ok=False, message=str(e))


def _matches(meta: dict[str, Any], flt: dict[str, Any]) -> bool:
    for k, v in flt.items():
        if meta.get(k) != v:
            return False
    return True


register_datasource("vector", VectorDBAdapter)
