#!/usr/bin/env bash
# scripts/stop_milvus.sh — stop the local Milvus standalone container started by start_milvus.sh.
# Does NOT remove the container or volume; restart via start_milvus.sh keeps data.

set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-kb_milvus}"

log() { printf '[stop_milvus] %s\n' "$*" >&2; }

if ! command -v docker >/dev/null 2>&1; then
  log "docker not found in PATH"
  exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
  log "${CONTAINER_NAME} is not running; nothing to stop"
  exit 0
fi

docker stop "${CONTAINER_NAME}" >/dev/null
log "stopped ${CONTAINER_NAME}; restart with scripts/start_milvus.sh"