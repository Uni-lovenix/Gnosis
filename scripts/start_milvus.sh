#!/usr/bin/env bash
# scripts/start_milvus.sh — start a local Milvus standalone container for 1:1 tests.
#
# Idempotent:
#   - if the container `kb_milvus` is running, prints its id and exits 0.
#   - if a stopped container with the same name exists, it is started.
#   - otherwise, the image is pulled and a new container is created.
#
# Defaults match VectorDBConfig.options["uri"] = "http://127.0.0.1:19530".
# Override with env vars: IMAGE / CONTAINER_NAME / MILVUS_PORT / VOLUME_NAME.

set -euo pipefail

IMAGE="${IMAGE:-milvusdb/milvus:v2.4.10-standalone}"
CONTAINER_NAME="${CONTAINER_NAME:-kb_milvus}"
MILVUS_PORT="${MILVUS_PORT:-19530}"
VOLUME_NAME="${VOLUME_NAME:-kb_milvus_data}"

log() { printf '[start_milvus] %s\n' "$*" >&2; }

if ! command -v docker >/dev/null 2>&1; then
  log "docker not found in PATH; install Docker Desktop or set KB_MILVUS_URI to a remote endpoint"
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  log "docker daemon not reachable; start Docker Desktop and retry"
  exit 1
fi

# 1. Container already running? print and exit.
if docker ps --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
  cid=$(docker ps --filter "name=${CONTAINER_NAME}" --format '{{.ID}}')
  log "already running: ${CONTAINER_NAME} (${cid}); port ${MILVUS_PORT}"
  exit 0
fi

# 2. Stopped container with same name? start it.
if docker ps -a --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
  log "starting existing container: ${CONTAINER_NAME}"
  docker start "${CONTAINER_NAME}" >/dev/null
  log "started ${CONTAINER_NAME}; port ${MILVUS_PORT}"
  exit 0
fi

# 3. Fresh container. Pull image if missing.
if ! docker image inspect "${IMAGE}" >/dev/null 2>&1; then
  log "pulling image ${IMAGE} (~1GB; this may take a while)"
  docker pull "${IMAGE}"
fi

log "creating container ${CONTAINER_NAME} from ${IMAGE}"
docker run -d \
  --name "${CONTAINER_NAME}" \
  --restart unless-stopped \
  -p "${MILVUS_PORT}:19530" \
  -v "${VOLUME_NAME}:/var/lib/milvus" \
  "${IMAGE}" >/dev/null

log "container created; give it ~10s to become ready"
log "verify with: curl -s http://127.0.0.1:${MILVUS_PORT}/health"