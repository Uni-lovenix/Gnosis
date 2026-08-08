"""MySQL adapter using a JSON column to store the vector.

This is a low-friction option when pgvector / Milvus are unavailable. It is
NOT suitable for > 1M vectors: similarity is computed in Python after a
prefilter (e.g. by document_id) or a full table scan for small libraries.

KI-02 mitigation (C8):
  * ``capabilities()`` declares ``scan_limit_risk`` so callers can warn users.
  * ``__init__`` emits a structured warning (``mysql.adapter.small_dataset_only``)
    pointing at pgvector / Milvus as the downgrade path.
  * ``search()`` logs ``mysql.adapter.scan_limit_hit`` when the scan returned
    ``>= max_scan_rows`` rows, signalling that results may be truncated.

This adapter provides **no** ANN index and **no** full-result guarantee.

Schema:
  kb_chunks(id VARCHAR(64) PK, document_id VARCHAR(64), text TEXT,
            metadata JSON, vector JSON, dim INT)
"""
from __future__ import annotations

import json
import math
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
from app.observability.models import Chunk, Hit

log = get_logger(__name__)


class MysqlConfig(DatasourceConfig):
    type: str = "mysql"
    options: dict[str, Any] = Field(
        default_factory=lambda: {
            "host": "127.0.0.1",
            "port": 3306,
            "user": "root",
            "password": "",
            "database": "kb",
            "table": "kb_chunks",
            "dim": 1024,
            "max_scan_rows": 100_000,  # safety limit
        }
    )


def _import_pymysql():
    try:
        import pymysql  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise DatasourceError("PyMySQL not installed. `pip install -e '.[mysql]'`.") from e
    return pymysql


class MysqlAdapter(DataSource):
    type = "mysql"

    def __init__(self, config: DatasourceConfig) -> None:
        if not isinstance(config, MysqlConfig):
            config = MysqlConfig(**config.model_dump())
        super().__init__(config)
        self._cfg: MysqlConfig = config  # type: ignore[assignment]
        self._dim = int(self._cfg.options.get("dim", 1024))
        self._table = self._cfg.options.get("table", "kb_chunks")
        self._max_scan = int(self._cfg.options.get("max_scan_rows", 100_000))
        self._pymysql = _import_pymysql()
        self._ensure_schema()
        log.info(
            "mysql.adapter.initialized",
            table=self._table,
            dim=self._dim,
            max_scan_rows=self._max_scan,
            host=self._cfg.options.get("host"),
        )
        # KI-02: surface the O(N) limitation up-front so operators can act
        # before the first slow query.
        log.warning(
            "mysql.adapter.small_dataset_only",
            max_scan_rows=self._max_scan,
            hint=(
                "MySQL adapter performs O(N) Python cosine; suitable only for "
                "small datasets (default max_scan_rows=100000). For larger "
                "libraries, switch to PostgreSQL pgvector or Milvus."
            ),
        )

    def _connect(self):
        o = self._cfg.options
        return self._pymysql.connect(
            host=o.get("host", "127.0.0.1"),
            port=int(o.get("port", 3306)),
            user=o.get("user", "root"),
            password=o.get("password", ""),
            database=o.get("database", "kb"),
            charset="utf8mb4",
            autocommit=True,
        )

    def _ensure_schema(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._table} (
                    id VARCHAR(64) PRIMARY KEY,
                    document_id VARCHAR(64) NOT NULL,
                    text TEXT NOT NULL,
                    metadata JSON NOT NULL,
                    vector JSON NOT NULL,
                    dim INT NOT NULL,
                    INDEX idx_document (document_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        log.info("mysql.schema.ready", table=self._table, dim=self._dim)

    def capabilities(self) -> set[str]:
        # In-Python similarity is O(N) — recommend small datasets only.
        # ``scan_limit_risk`` signals callers that ``max_scan_rows`` truncation
        # is possible (see KI-02).
        return {"metadata_filter", "small_dataset_only", "scan_limit_risk"}

    async def add(self, chunks: Iterable[Chunk]) -> list[str]:
        ids: list[str] = []
        rows: list[tuple[Any, ...]] = []
        for c in chunks:
            if c.vector is None:
                raise DatasourceError(f"chunk {c.id} has no vector; embed first")
            if len(c.vector) != self._dim:
                raise DatasourceError(
                    f"chunk {c.id} vector dim {len(c.vector)} != configured {self._dim}"
                )
            ids.append(c.id)
            rows.append(
                (
                    c.id,
                    c.document_id,
                    c.text,
                    json.dumps(c.metadata, ensure_ascii=False),
                    json.dumps(c.vector),
                    self._dim,
                )
            )
        if not rows:
            return ids
        with self._connect() as conn, conn.cursor() as cur:
            cur.executemany(
                f"""
                INSERT INTO {self._table}
                    (id, document_id, text, metadata, vector, dim)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    document_id=VALUES(document_id),
                    text=VALUES(text),
                    metadata=VALUES(metadata),
                    vector=VALUES(vector),
                    dim=VALUES(dim)
                """,
                rows,
            )
        return ids

    async def search(
        self,
        vector: list[float],
        top_k: int = 5,
        filter: dict[str, Any] | None = None,
    ) -> list[Hit]:
        where = ["1=1"]
        params: list[Any] = []
        if filter:
            for k, v in filter.items():
                where.append("JSON_EXTRACT(metadata, %s) = %s")
                params.extend([f"$.{k}", json.dumps(v)])
        sql = (
            f"SELECT id, text, metadata, vector FROM {self._table} "
            f"WHERE {' AND '.join(where)} LIMIT {self._max_scan}"
        )
        scored: list[Hit] = []
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            scanned = len(rows)
            for cid, text, metadata, vec_json in rows:
                v = json.loads(vec_json) if isinstance(vec_json, (str, bytes)) else vec_json
                score = _cosine(vector, v)
                scored.append(
                    Hit(id=cid, score=score, text=text, metadata=_loads(metadata))
                )
        # KI-02: when the scan returned >= max_scan_rows, results are likely
        # truncated. Surface a structured warning so operators can pivot to
        # pgvector / Milvus before users feel the latency.
        if scanned >= self._max_scan:
            log.warning(
                "mysql.adapter.scan_limit_hit",
                scanned_rows=scanned,
                max_scan_rows=self._max_scan,
                hint=(
                    "search() hit max_scan_rows; result set may be truncated. "
                    "Consider narrowing the filter, or migrating to PostgreSQL "
                    "pgvector / Milvus."
                ),
            )
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:top_k]

    async def delete(self, ids: Iterable[str]) -> int:
        id_list = list(ids)
        if not id_list:
            return 0
        placeholders = ",".join(["%s"] * len(id_list))
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(f"DELETE FROM {self._table} WHERE id IN ({placeholders})", id_list)
            return cur.rowcount

    async def health(self) -> HealthStatus:
        start = time.perf_counter()
        try:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            return HealthStatus(ok=True, latency_ms=(time.perf_counter() - start) * 1000)
        except Exception as e:  # noqa: BLE001
            return HealthStatus(ok=False, message=str(e))


def _cosine(a: list[float], b: list[float]) -> float:
    s = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        s += x * y
        na += x * x
        nb += y * y
    if na == 0 or nb == 0:
        return 0.0
    return s / (math.sqrt(na) * math.sqrt(nb))


def _loads(s: Any) -> dict[str, Any]:
    if isinstance(s, (dict, list)):
        return s
    if isinstance(s, (bytes, bytearray)):
        s = s.decode("utf-8")
    return json.loads(s)


register_datasource("mysql", MysqlAdapter)