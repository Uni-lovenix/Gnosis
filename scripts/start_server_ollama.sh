#!/usr/bin/env bash
#
# scripts/start_server_ollama.sh -- start the KB server using a local Ollama
# bge-m3 endpoint as the embedder.
#
# Prerequisite: Ollama daemon running at 127.0.0.1:11434 with ``bge-m3`` pulled:
#
#     ollama pull bge-m3
#     ollama list    # confirm bge-m3:latest is present
#
# What this does:
#   * Points the server at the Ollama OpenAI-compatible endpoint
#     (POST /v1/embeddings).
#   * Uses an isolated data dir so we never collide with the ``~/.kb-server``
#     default. Override with ``KB_DATA_DIR=...``.
#   * Runs uvicorn in the foreground; Ctrl-C to stop.
#
# Side effects: writes to ``$KB_DATA_DIR`` (default ``./var/kb-server-ollama``).

set -euo pipefail

KB_DATA_DIR=${KB_DATA_DIR:-./var/kb-server-ollama}
KB_PORT=${KB_PORT:-8765}

mkdir -p "$KB_DATA_DIR"

export KB_DATA_DIR
export KB_EMBED_BACKEND=openai-compat
# Ollama's OpenAI-compatible endpoint.
export KB_OPENAI_BASE_URL=${KB_OPENAI_BASE_URL:-http://127.0.0.1:11434/v1}
# Ollama does not validate the key, but ``openai_compat`` requires a non-empty
# value; any string works.
export KB_OPENAI_API_KEY=${KB_OPENAI_API_KEY:-ollama}
# Must match the Ollama tag (run ``ollama list`` to confirm).
export KB_OPENAI_MODEL=${KB_OPENAI_MODEL:-bge-m3}
export KB_EMBED_MODEL=${KB_EMBED_MODEL:-bge-m3}
export KB_EMBED_DIM=${KB_EMBED_DIM:-1024}

cd "$(dirname "$0")/../server"
exec python3 -m uvicorn app.main:app \
  --host "${KB_HOST:-127.0.0.1}" \
  --port "$KB_PORT" \
  --log-level "${KB_LOG_LEVEL:-info}"
