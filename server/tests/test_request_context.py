"""Tests for the X-Request-Id correlation middleware (C10)."""
from __future__ import annotations

import structlog.testing
from fastapi.testclient import TestClient

from app.main import create_app


def test_request_id_is_generated_and_echoed():
    client = TestClient(create_app())
    r = client.get("/v1/health")
    rid = r.headers.get("X-Request-Id")
    assert rid and len(rid) == 32

    r2 = client.get("/v1/health", headers={"X-Request-Id": "caller-supplied-id"})
    assert r2.headers["X-Request-Id"] == "caller-supplied-id"


def test_http_request_log_carries_same_request_id():
    client = TestClient(create_app())
    with structlog.testing.capture_logs() as cap:
        r = client.get("/v1/health")
    rid = r.headers["X-Request-Id"]
    events = [e for e in cap if e.get("event") == "http.request"]
    assert events
    assert events[0]["request_id"] == rid
    assert events[0]["path"] == "/v1/health"
