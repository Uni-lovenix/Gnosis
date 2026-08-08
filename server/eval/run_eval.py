"""End-to-end retrieval evaluation harness.

Ingest the corpus into the running server via the /v1/files/import endpoint
(or directly through the pipeline), then run the cases and report hit rate.
Designed to be run against a live or in-process app.

Backend selection
-----------------
The harness accepts ``--embedder``:

* ``mock``  — HashMockEmbedder (dim 64). Default; no external deps.
* ``bge-m3`` — real ``BGEM3Embedder`` (dim 1024). Requires
  ``pip install -e ".[embedding-local]"`` and ``BGE_M3_LOCAL`` pointing to a
  model snapshot downloaded via ``scripts/download_bge_m3.sh``.

Reports a structured JSON result with hit count, rate, threshold, and a
``backend`` field so CI can tell which path produced the score.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from app.datasources.base import DatasourceConfig
from app.datasources.vector_db_adapter import VectorDBAdapter
from app.embedding.base import Embedder, EmbedderConfig
from app.embedding.mock_embedder import HashMockEmbedder
from app.observability.models import Document
from app.pipeline.indexing import IndexingPipeline


# Backends known to this harness. Anything else is treated as a real embedder
# and resolved through the registry; ``--dim`` can override the registry value
# if a custom embedding has a different vector size.
_MOCK_DIM = 64


def _corpus_docs(corpus_path: Path) -> list[Document]:
    """Parse `corpus/snippets.md` into per-section Documents."""
    raw = corpus_path.read_text(encoding="utf-8")
    docs: list[Document] = []
    current_id = ""
    current: list[str] = []
    for line in raw.splitlines():
        if line.startswith("## doc:"):
            if current_id and current:
                docs.append(
                    Document(
                        id=current_id,
                        source_path=str(corpus_path),
                        text="\n".join(current).strip(),
                        metadata={"corpus_id": current_id},
                    )
                )
            current_id = line.split(":", 1)[1].strip()
            current = []
        elif line.startswith("# "):
            continue  # top heading
        else:
            current.append(line)
    if current_id and current:
        docs.append(
            Document(
                id=current_id,
                source_path=str(corpus_path),
                text="\n".join(current).strip(),
                metadata={"corpus_id": current_id},
            )
        )
    return docs


def _build_embedder(backend: str, dim_override: int | None) -> Embedder:
    if backend == "mock":
        dim = dim_override or _MOCK_DIM
        return HashMockEmbedder(EmbedderConfig(name="m", type="mock-hash", options={"dim": dim}))
    if backend == "bge-m3":
        # Late import so the harness stays import-clean when bge-m3 deps
        # are not installed.
        from app.embedding.bge_m3 import BGEM3Embedder

        local = Path(__file__).resolve().parents[2] / "server" / "models" / "bge-m3"
        opts: dict = {"model": "BAAI/bge-m3"}
        if local.exists():
            opts["model"] = str(local)
        cfg = EmbedderConfig(name="bge", type="bge-m3", options=opts)
        embedder = BGEM3Embedder(cfg)
        if dim_override and dim_override != embedder.dim:
            # Allow callers to benchmark against a dim-reduced vector; the
            # registry dim still wins for storage consistency.
            embedder.dim = dim_override  # type: ignore[misc]
        return embedder
    if backend == "openai-compat":
        # Use any OpenAI-compatible endpoint (Ollama, vLLM, DashScope, etc.).
        # Env vars mirror the ones ``app.main`` reads:
        #   KB_OPENAI_BASE_URL (required), KB_OPENAI_API_KEY (required),
        #   KB_OPENAI_MODEL (default "bge-m3"), KB_EMBED_DIM (default 1024).
        import os
        from app.embedding.openai_compat import OpenAICompatEmbedder

        base_url = os.environ.get("KB_OPENAI_BASE_URL") or "http://127.0.0.1:11434/v1"
        api_key = os.environ.get("KB_OPENAI_API_KEY") or "ollama"
        model = os.environ.get("KB_OPENAI_MODEL") or os.environ.get("KB_EMBED_MODEL") or "bge-m3"
        dim = dim_override or int(os.environ.get("KB_EMBED_DIM", "1024"))
        embedder = OpenAICompatEmbedder(
            EmbedderConfig(
                name="oai",
                type="openai-compat",
                options={
                    "model": model,
                    "model_openai": model,
                    "base_url": base_url,
                    "api_key": api_key,
                    "dim": dim,
                    "timeout": float(os.environ.get("KB_OPENAI_TIMEOUT", "120")),
                },
            )
        )
        return embedder
    raise SystemExit(f"unknown embedder backend: {backend}")


def evaluate(
    cases_path: Path,
    corpus_path: Path,
    backend: str = "mock",
    dim_override: int | None = None,
) -> dict:
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    docs = _corpus_docs(corpus_path)
    if not docs:
        raise SystemExit(f"no documents found in corpus {corpus_path}")

    embedder = _build_embedder(backend, dim_override)
    dim = embedder.dim
    ds = VectorDBAdapter(
        DatasourceConfig(name="mem", type="vector", options={"backend": "memory", "dim": dim})
    )
    pipeline = IndexingPipeline(ds, embedder, embed_batch_size=4)

    async def _index():
        for d in docs:
            await pipeline.run(d)

    asyncio.run(_index())

    from app.pipeline.retrieval import RetrievalPipeline

    retriever = RetrievalPipeline(ds, embedder)

    async def _query():
        results = []
        for c in cases["cases"]:
            hits = await retriever.search(c["query"], top_k=3)
            joined = "\n".join(h.text for h in hits).lower()
            matched = any(s.lower() in joined for s in c["must_contain_any"])
            results.append({"id": c["id"], "matched": matched, "hits": len(hits)})
        return results

    results = asyncio.run(_query())
    passed = sum(1 for r in results if r["matched"])
    total = len(results)
    rate = passed / total if total else 0.0
    return {
        "passed": passed,
        "total": total,
        "rate": rate,
        "threshold": cases.get("pass_threshold", 0.6),
        "backend": backend,
        "dim": dim,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default=str(Path(__file__).parent / "fixtures" / "cases.json"))
    parser.add_argument("--corpus", default=str(Path(__file__).parent / "corpus" / "snippets.md"))
    parser.add_argument(
        "--embedder",
        default="openai-compat",
        choices=["openai-compat", "mock", "bge-m3"],
        help=(
            "Embedding backend. Default: openai-compat (Ollama bge-m3 via "
            "KB_OPENAI_* env vars). Use `mock` for offline / deterministic "
            "checks; `bge-m3` for the local sentence-transformers snapshot."
        ),
    )
    parser.add_argument(
        "--dim",
        type=int,
        default=None,
        help="Override vector dim. Use only for sanity checks; usually leave unset.",
    )
    args = parser.parse_args()
    report = evaluate(Path(args.cases), Path(args.corpus), args.embedder, args.dim)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["rate"] >= report["threshold"] else 1


if __name__ == "__main__":
    sys.exit(main())