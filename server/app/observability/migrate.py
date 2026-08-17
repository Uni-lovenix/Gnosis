"""Data source migration helpers: dump full text + metadata, then reload.

Migration deliberately drops vectors: chunks are re-embedded with the current
embedder during ``load`` so model/dimension changes do not leave stale vectors
behind. Sources must advertise the ``dump`` capability.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.datasources.base import DatasourceConfig
from app.datasources.factory import build
from app.datasources import elasticsearch_adapter  # noqa: F401  (populate registry)
from app.datasources import mysql_adapter  # noqa: F401  (populate registry)
from app.datasources import postgres_adapter  # noqa: F401  (populate registry)
from app.datasources import vector_db_adapter  # noqa: F401  (populate registry)
from app.embedding import bge_m3  # noqa: F401  (populate registry)
from app.embedding import mock_embedder  # noqa: F401  (populate registry)
from app.embedding import openai_compat  # noqa: F401  (populate registry)
from app.embedding.base import EmbedderConfig
from app.embedding.factory import build_embedder
from app.observability.models import Chunk, new_id


async def dump_chunks(ds, output_path: str | Path, page_size: int = 100) -> int:
    """Write all chunks from ``ds`` as JSONL (document_id / text / metadata)."""
    if "dump" not in ds.capabilities():
        raise ValueError(f"datasource {ds.name} does not support dump; add 'dump' capability")
    out = Path(output_path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    offset = 0
    written = 0
    with out.open("w", encoding="utf-8") as fh:
        while True:
            chunks, total = await ds.dump_all(offset=offset, limit=max(1, page_size))
            for c in chunks:
                fh.write(
                    json.dumps(
                        {
                            "document_id": c.document_id,
                            "text": c.text,
                            "metadata": c.metadata,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                written += 1
            if not chunks or offset + len(chunks) >= total:
                break
            offset += len(chunks)
    return written


async def load_chunks(
    ds,
    embedder,
    input_path: str | Path,
    batch_size: int = 16,
) -> int:
    """Read JSONL chunks, embed in batches, and write them to ``ds``."""
    inp = Path(input_path).expanduser()
    lines: list[dict] = []
    with inp.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                lines.append(json.loads(line))

    written = 0
    for start in range(0, len(lines), max(1, batch_size)):
        batch = lines[start : start + batch_size]
        texts = [item["text"] for item in batch]
        vectors = await embedder.embed(texts)
        chunks = [
            Chunk(
                id=new_id(),
                document_id=item.get("document_id", ""),
                text=item["text"],
                metadata=item.get("metadata", {}),
                vector=vec,
            )
            for item, vec in zip(batch, vectors)
        ]
        written += len(await ds.add(chunks))
    return written


async def _run(args) -> None:
    options = json.loads(args.options or "{}")
    ds = build(DatasourceConfig(name="migrate", type=args.type, options=options))
    if args.command == "dump":
        written = await dump_chunks(ds, args.output, page_size=args.page_size)
        print(f"dumped {written} chunks to {args.output}", flush=True)
        return
    embedder = build_embedder(
        EmbedderConfig(
            name="migrate",
            type=args.embed,
            options={"dim": args.dim},
        )
    )
    written = await load_chunks(ds, embedder, args.input, batch_size=args.batch_size)
    print(f"loaded {written} chunks into {ds.name}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(prog="kb-migrate", description="灵知数据源迁移")
    sub = parser.add_subparsers(dest="command", required=True)

    dump_p = sub.add_parser("dump")
    dump_p.add_argument("--type", required=True)
    dump_p.add_argument("--options", default="{}")
    dump_p.add_argument("--output", required=True)
    dump_p.add_argument("--page-size", type=int, default=100)

    load_p = sub.add_parser("load")
    load_p.add_argument("--type", required=True)
    load_p.add_argument("--options", default="{}")
    load_p.add_argument("--input", required=True)
    load_p.add_argument("--embed", default="mock-hash")
    load_p.add_argument("--dim", type=int, default=64)
    load_p.add_argument("--batch-size", type=int, default=16)

    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
