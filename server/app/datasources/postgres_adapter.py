"""PostgreSQL adapter using the pgvector extension.

Schema (created on first use):
  chunks(id text PK, document_id text, text text, metadata jsonb, vector vector(dim))
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
from app.observability.models import Chunk, Hit

log = get_logger(__name__)


class PostgresConfig(DatasourceConfig):
    type: str = "postgresql"
    options: dict[str, Any] = Field(
        default_factory=lambda: {
            "dsn": "postgresql://postgres:postgres@127.0.0.1:5432/postgres",
            "table": "kb_chunks",
            "dim": 1024,
        }
    )


def _import_psycopg():
    try:
        import psycopg  # type: ignore
        from pgvector.psycopg import register_vector  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise DatasourceError(
            "psycopg / pgvector not installed. `pip install -e '.[pg]'`."
        ) from e
    return psycopg, register_vector


class PostgresAdapter(DataSource):
    type = "postgresql"

    def __init__(self, config: DatasourceConfig) -> None:
        if not isinstance(config, PostgresConfig):
            config = PostgresConfig(**config.model_dump())
        super().__init__(config)
        self._cfg: PostgresConfig = config  # type: ignore[assignment]
        self._dim = int(self._cfg.options.get("dim", 1024))
        self._table = self._cfg.options.get("table", "kb_chunks")
        self._dsn = self._cfg.options["dsn"]
        self._psycopg, self._register_vector = _import_psycopg()
        self._ensure_schema()

    def _connect(self):
        conn = self._psycopg.connect(self._dsn)
        self._register_vector(conn)
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._table} (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                    vector vector({self._dim}) NOT NULL
                )
                """
            )
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS {self._table}_vec_idx "
                f"ON {self._table} USING ivfflat (vector vector_cosine_ops) WITH (lists = 100)"
            )
        log.info("postgres.schema.ready", table=self._table, dim=self._dim)

    def capabilities(self) -> set[str]:
        return {"metadata_filter", "delete_by_filter"}

    async def add(self, chunks: Iterable[Chunk]) -> list[str]:
        ids: list[str] = []
        rows: list[tuple[str, str, str, str, list[float]]] = []
        for c in chunks:
            if c.vector is None:
                raise DatasourceError(f"chunk {c.id} has no vector; embed first")
            ids.append(c.id)
            rows.append((c.id, c.document_id, c.text, _json(c.metadata), c.vector))
        if not rows:
            return ids
        with self._connect() as conn, conn.cursor() as cur:
            cur.executemany(
                f"""
                INSERT INTO {self._table} (id, document_id, text, metadata, vector)
                VALUES (%s, %s, %s, %s::jsonb, %s)
                ON CONFLICT (id) DO UPDATE SET
                    document_id = EXCLUDED.document_id,
                    text = EXCLUDED.text,
                    metadata = EXCLUDED.metadata,
                    vector = EXCLUDED.vector
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
        where = ""
        params: list[Any] = [vector, top_k]
        if filter:
            # naive equality on metadata JSONB keys, e.g. {"document_id": "abc"}
            where = " AND " + " AND ".join(f"metadata ->> %s = %s" for _ in filter)
            for k, v in filter.items():
                params.extend([k, v])
        sql = (
            f"SELECT id, text, metadata, 1 - (vector <=> %s::vector) AS score "
            f"FROM {self._table} "
            f"WHERE TRUE{where} "
            f"ORDER BY vector <=> %s::vector "
            f"LIMIT %s"
        )
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, params + [vector, top_k])
            rows = cur.fetchall()
        return [
            Hit(id=r[0], score=float(r[3]), text=r[1], metadata=_loads(r[2]))
            for r in rows
        ]

    async def delete(self, ids: Iterable[str]) -> int:
        id_list = list(ids)
        if not id_list:
            return 0
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"DELETE FROM {self._table} WHERE id = ANY(%s)",
                (id_list,),
            )
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


def _json(d: dict[str, Any]) -> str:
    import json

    return json.dumps(d, ensure_ascii=False)


def _loads(s: Any) -> dict[str, Any]:
    import json

    if isinstance(s, (dict, list)):
        return s
    if isinstance(s, (bytes, bytearray)):
        s = s.decode("utf-8")
    return json.loads(s)


register_datasource("postgresql", PostgresAdapter)