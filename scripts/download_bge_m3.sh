#!/usr/bin/env bash
# Download the BAAI/bge-m3 model snapshot into ./server/models/bge-m3 so the
# eval harness can load it offline. The script is idempotent — re-running it
# after a successful download is a no-op.
#
# Requirements:
#   - python3 with the `huggingface_hub` package (pulled in by
#     `pip install -e ".[embedding-local]"`).
#   - ~2.4 GB free disk.
#
# Usage:
#   ./scripts/download_bge_m3.sh                  # default location
#   HF_HOME=... ./scripts/download_bge_m3.sh      # custom cache root
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${ROOT}/server/models/bge-m3"

if [[ -d "${TARGET}" && -f "${TARGET}/config.json" ]]; then
    echo "[bge-m3] already present at ${TARGET}; nothing to do."
    exit 0
fi

mkdir -p "${TARGET}"

echo "[bge-m3] downloading BAAI/bge-m3 → ${TARGET}"
export BGE_M3_TARGET="${TARGET}"
python3 - <<'PY'
import os
from pathlib import Path

target = Path(os.environ["BGE_M3_TARGET"]).resolve()
target.mkdir(parents=True, exist_ok=True)

from huggingface_hub import snapshot_download  # type: ignore

path = snapshot_download(
    repo_id="BAAI/bge-m3",
    local_dir=str(target),
    local_dir_use_symlinks=False,
    allow_patterns=[
        "*.json",
        "*.txt",
        "sentencepiece.bpe.model",
        "tokenizer.json",
        "vocab.txt",
        "1_Pooling/*",
        "sentence_bert_config.json",
    ],
)
print("[bge-m3] snapshot at", path)
PY

echo "[bge-m3] done. Use --embedder bge-m3 in eval/run_eval.py."