"""Shared fixtures for datasource tests.

The Milvus 1:1 tests live behind a guard: if no Milvus server is reachable at
``KB_MILVUS_URI`` (default ``http://127.0.0.1:19530``), the tests are skipped
with a clear hint, so the rest of the suite (in-memory + es + pg + mysql) can
keep running on machines without Docker / without Milvus.

Start Milvus locally with ``bash scripts/start_milvus.sh``.
"""
from __future__ import annotations

import os
import socket
import uuid
from collections.abc import Iterator

import pytest

DEFAULT_MILVUS_URI = "http://127.0.0.1:19530"
DEFAULT_MILVUS_HOST = "127.0.0.1"
DEFAULT_MILVUS_PORT = 19530


def _resolve_milvus_endpoint() -> tuple[str, str | None, int | None]:
    """Return ``(uri, host, port)`` honoring ``KB_MILVUS_URI``.

    For http(s) URIs the host/port are parsed out so a TCP probe can run.
    For local Lite URIs (file path) the host/port come back as ``None``.
    """
    uri = os.environ.get("KB_MILVUS_URI", DEFAULT_MILVUS_URI)
    if "://" in uri:
        scheme, rest = uri.split("://", 1)
        if scheme in ("http", "https"):
            if ":" in rest:
                host, port_s = rest.rsplit(":", 1)
                return uri, host, int(port_s)
            return uri, rest, DEFAULT_MILVUS_PORT
        # other schemes (e.g. file://...) — no TCP probe
        return uri, None, None
    # bare host[:port] or local file path
    if ":" in uri and not uri.startswith("/"):
        host, port_s = uri.rsplit(":", 1)
        return uri, host, int(port_s)
    return uri, None, None


def _tcp_reachable(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def require_milvus(uri: str) -> "MilvusClient":  # type: ignore[name-defined]
    """Return a connected ``MilvusClient`` or raise ``pytest.skip``.

    Supports:
      * http(s)://host:port  -> standalone Milvus (docker); TCP-probed first.
      * bare local path      -> Milvus Lite (embedded engine); no TCP probe.

    Imported lazily so the rest of the suite does not depend on pymilvus.
    """
    _, host, port = _resolve_milvus_endpoint()
    if host is not None and port is not None and not _tcp_reachable(host, port):
        pytest.skip(
            f"milvus not reachable at {uri}; start it with `bash scripts/start_milvus.sh`"
            " or set KB_MILVUS_URI to a Milvus Lite path"
        )
    try:
        from pymilvus import MilvusClient  # type: ignore
    except ImportError as e:  # pragma: no cover
        pytest.skip(f"pymilvus not installed: {e}; install with `pip install -e '.[vector]'`")
    try:
        client = MilvusClient(uri=uri)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"milvus handshake failed at {uri}: {e}")
    return client


@pytest.fixture
def milvus_uri() -> str:
    """The Milvus URI used by the 1:1 tests; overridable via ``KB_MILVUS_URI``."""
    uri, _, _ = _resolve_milvus_endpoint()
    return uri


@pytest.fixture
def milvus_collection(milvus_uri: str) -> Iterator[str]:
    """A fresh Milvus collection per test; dropped on teardown.

    Yields the collection name. Skips the test if Milvus is unreachable.
    """
    client = require_milvus(milvus_uri)
    name = f"kb_test_{uuid.uuid4().hex[:8]}"
    try:
        yield name
    finally:
        try:
            if client.has_collection(name):
                client.drop_collection(name)
        except Exception:  # noqa: BLE001
            pass
        try:
            client.close()
        except Exception:  # noqa: BLE001
            pass