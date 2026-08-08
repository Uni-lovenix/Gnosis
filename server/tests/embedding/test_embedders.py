"""Tests for embedders."""
from __future__ import annotations

import asyncio

import httpx
import pytest

from app.embedding import list_embedder_types
from app.embedding.base import EmbedderConfig, EmbedderError, get_embedder_cls
from app.embedding.mock_embedder import HashMockEmbedder


# ---------------------------------------------------------------------------
# Helpers shared by the openai-compat retry tests below (and the original
# `test_openai_compat_uses_httpx`).
# ---------------------------------------------------------------------------


class _Resp:
    status_code = 200

    def __init__(self, body, text=""):
        self._body = body
        self.text = text

    def json(self):
        return self._body


def test_registry_includes_bge_and_openai():
    types = set(list_embedder_types())
    assert {"bge-m3", "openai-compat", "mock-hash"} <= types


def test_unknown_embedder_raises():
    with pytest.raises(EmbedderError):
        get_embedder_cls("nope")


@pytest.mark.asyncio
async def test_mock_embedder_returns_normalized_vectors():
    e = HashMockEmbedder(EmbedderConfig(name="m", type="mock-hash", options={"dim": 16}))
    vecs = await e.embed(["hello world", "goodbye world"])
    assert len(vecs) == 2
    assert all(len(v) == 16 for v in vecs)
    # normalize_embeddings-like: norm ≈ 1
    for v in vecs:
        norm = sum(x * x for x in v) ** 0.5
        assert abs(norm - 1.0) < 1e-6


@pytest.mark.asyncio
async def test_mock_embedder_is_deterministic():
    e = HashMockEmbedder(EmbedderConfig(name="m", type="mock-hash", options={"dim": 16}))
    a = await e.embed(["alpha beta gamma"])
    b = await e.embed(["alpha beta gamma"])
    assert a == b


@pytest.mark.asyncio
async def test_mock_embedder_similar_texts_have_high_cosine():
    e = HashMockEmbedder(EmbedderConfig(name="m", type="mock-hash", options={"dim": 64}))
    v1 = (await e.embed(["apple banana cherry"]))[0]
    v2 = (await e.embed(["apple banana grape"]))[0]
    v3 = (await e.embed(["quantum entanglement photon"]))[0]
    cos_sim = lambda a, b: sum(x * y for x, y in zip(a, b))
    assert cos_sim(v1, v2) > cos_sim(v1, v3)


@pytest.mark.asyncio
async def test_openai_compat_requires_base_url_and_api_key():
    from app.embedding.openai_compat import OpenAICompatEmbedder

    with pytest.raises(EmbedderError):
        OpenAICompatEmbedder(EmbedderConfig(name="o", type="openai-compat", options={}))


@pytest.mark.asyncio
async def test_openai_compat_uses_httpx(monkeypatch):
    import httpx

    from app.embedding.openai_compat import OpenAICompatEmbedder

    captured: dict = {}

    class _Resp:
        status_code = 200

        def __init__(self, body):
            self._body = body

        def json(self):
            return self._body

        @property
        def text(self):
            return ""

    class _Client:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return _Resp(
                {"data": [{"index": 0, "embedding": [0.1, 0.2, 0.3]}, {"index": 1, "embedding": [0.4, 0.5, 0.6]}]}
            )

    monkeypatch.setattr(httpx, "AsyncClient", _Client)

    e = OpenAICompatEmbedder(
        EmbedderConfig(
            name="o",
            type="openai-compat",
            options={"base_url": "https://example.com/v1", "api_key": "k", "model": "bge-m3"},
        )
    )
    vecs = await e.embed(["a", "b"])
    assert vecs == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    assert captured["url"] == "https://example.com/v1/embeddings"


# ---------------------------------------------------------------------------
# KI-03: OpenAI-compat retry / backoff
# ---------------------------------------------------------------------------


class _ScriptedTransport:
    """Drive the embedder through a pre-arranged sequence of outcomes.

    Each entry is one of:
      * ("ok", body)              → 200 with the given JSON body
      * ("status", code, retryable bool) → raises EmbedderError with attrs
      * ("transport", "name")     → raises httpx.TransportError subclass with
                                    the given class name
    """

    def __init__(self, script: list[tuple]):
        self.script = list(script)
        self.calls: list = []
        self._idx = 0

    async def post(self, url, headers=None, json=None):
        self.calls.append({"url": url, "json": json})
        entry = self.script[self._idx]
        self._idx += 1
        kind = entry[0]
        if kind == "ok":
            return _Resp({"data": [{"index": i, "embedding": [float(i), float(i) + 1]} for i in range(len(json["input"]))]})
        if kind == "status":
            _, code, retryable = entry
            err = EmbedderError(f"remote embed failed {code}")
            err.kb_status_code = code  # type: ignore[attr-defined]
            err.kb_retryable = retryable  # type: ignore[attr-defined]
            raise err
        if kind == "transport":
            cls_name = entry[1]

            class _T(httpx.TransportError):
                pass

            raise _T(f"simulated {cls_name}")
        raise AssertionError(f"unknown scripted outcome: {entry}")


class _RecordingClient:
    def __init__(self, transport: _ScriptedTransport, *a, **kw):
        self._transport = transport

    async def __aenter__(self):
        return self._transport

    async def __aexit__(self, *exc):
        return False

    def post(self, *a, **kw):
        # httpx.AsyncClient.post returns a coroutine; route to transport.
        return self._transport.post(*a, **kw)


@pytest.mark.asyncio
async def test_openai_compat_retries_then_succeeds_on_transport_error(monkeypatch):
    """Transient httpx.TransportError on attempt 1 → retry → success on 2."""
    import httpx

    from app.embedding.openai_compat import OpenAICompatEmbedder

    sleep_calls: list[float] = []

    async def fake_sleep(s):
        sleep_calls.append(s)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    transport = _ScriptedTransport(
        [
            ("transport", "ConnectError"),
            ("ok", None),
        ]
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **kw: _RecordingClient(transport, *a, **kw))

    e = OpenAICompatEmbedder(
        EmbedderConfig(
            name="o",
            type="openai-compat",
            options={
                "base_url": "https://example.com/v1",
                "api_key": "k",
                "model": "bge-m3",
                "max_retries": 3,
                "initial_backoff": 0.0,  # deterministic, no real sleep
                "backoff_jitter": 0.0,
            },
        )
    )
    vecs = await e.embed(["a"])
    assert vecs == [[0.0, 1.0]]
    assert len(transport.calls) == 2
    assert sleep_calls == [0.0]


@pytest.mark.asyncio
async def test_openai_compat_exhausts_retries_and_raises(monkeypatch):
    """When every attempt hits a transient error, surface EmbedderError."""
    import httpx

    from app.embedding.openai_compat import OpenAICompatEmbedder

    async def fake_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    transport = _ScriptedTransport(
        [
            ("transport", "TimeoutException"),
            ("transport", "TimeoutException"),
            ("transport", "TimeoutException"),
            ("transport", "TimeoutException"),  # initial + 3 retries = 4 calls
        ]
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **kw: _RecordingClient(transport, *a, **kw))

    e = OpenAICompatEmbedder(
        EmbedderConfig(
            name="o",
            type="openai-compat",
            options={
                "base_url": "https://example.com/v1",
                "api_key": "k",
                "model": "bge-m3",
                "max_retries": 3,
                "initial_backoff": 0.0,
                "backoff_jitter": 0.0,
            },
        )
    )
    with pytest.raises(EmbedderError) as exc_info:
        await e.embed(["a"])
    msg = str(exc_info.value)
    assert "4 attempt(s)" in msg
    assert "TimeoutException" in msg
    assert len(transport.calls) == 4


@pytest.mark.asyncio
async def test_openai_compat_does_not_retry_4xx(monkeypatch):
    """A 400 surfaces immediately — no retry, no sleep."""
    import httpx

    from app.embedding.openai_compat import OpenAICompatEmbedder

    sleep_called = []

    async def fake_sleep(_):
        sleep_called.append(1)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    transport = _ScriptedTransport([("status", 400, False)])
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **kw: _RecordingClient(transport, *a, **kw))

    e = OpenAICompatEmbedder(
        EmbedderConfig(
            name="o",
            type="openai-compat",
            options={
                "base_url": "https://example.com/v1",
                "api_key": "k",
                "model": "bge-m3",
                "max_retries": 3,
            },
        )
    )
    with pytest.raises(EmbedderError):
        await e.embed(["a"])
    assert len(transport.calls) == 1
    assert sleep_called == []


@pytest.mark.asyncio
async def test_openai_compat_retries_429(monkeypatch):
    """Rate-limit responses (429) are retried like 5xx."""
    import httpx

    from app.embedding.openai_compat import OpenAICompatEmbedder

    sleep_calls: list[float] = []

    async def fake_sleep(s):
        sleep_calls.append(s)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    transport = _ScriptedTransport(
        [
            ("status", 429, True),
            ("ok", None),
        ]
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **kw: _RecordingClient(transport, *a, **kw))

    e = OpenAICompatEmbedder(
        EmbedderConfig(
            name="o",
            type="openai-compat",
            options={
                "base_url": "https://example.com/v1",
                "api_key": "k",
                "model": "bge-m3",
                "max_retries": 3,
                "initial_backoff": 0.0,
                "backoff_jitter": 0.0,
            },
        )
    )
    vecs = await e.embed(["a"])
    assert vecs == [[0.0, 1.0]]
    assert len(transport.calls) == 2
    assert sleep_calls  # one backoff applied


@pytest.mark.asyncio
async def test_openai_compat_retries_5xx(monkeypatch):
    """Server errors (5xx) are retried."""
    import httpx

    from app.embedding.openai_compat import OpenAICompatEmbedder

    async def fake_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    transport = _ScriptedTransport(
        [
            ("status", 503, True),
            ("status", 502, True),
            ("ok", None),
        ]
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **kw: _RecordingClient(transport, *a, **kw))

    e = OpenAICompatEmbedder(
        EmbedderConfig(
            name="o",
            type="openai-compat",
            options={
                "base_url": "https://example.com/v1",
                "api_key": "k",
                "model": "bge-m3",
                "max_retries": 3,
                "initial_backoff": 0.0,
                "backoff_jitter": 0.0,
            },
        )
    )
    vecs = await e.embed(["a"])
    assert vecs == [[0.0, 1.0]]
    assert len(transport.calls) == 3


@pytest.mark.asyncio
async def test_openai_compat_backoff_doubles_and_caps(monkeypatch):
    """Verify exponential ladder: 0.5, 1.0, 2.0 (capped at max_backoff)."""
    from app.embedding.openai_compat import OpenAICompatEmbedder

    # No httpx mocking — purely unit-test the math.
    e = OpenAICompatEmbedder(
        EmbedderConfig(
            name="o",
            type="openai-compat",
            options={
                "base_url": "https://example.com/v1",
                "api_key": "k",
                "model": "bge-m3",
                "initial_backoff": 0.5,
                "max_backoff": 2.0,
                "backoff_jitter": 0.0,
            },
        )
    )
    assert e._backoff_for(1) == 0.5
    assert e._backoff_for(2) == 1.0
    assert e._backoff_for(3) == 2.0  # would be 2.0 (capped)
    assert e._backoff_for(4) == 2.0  # capped, no growth


@pytest.mark.asyncio
async def test_openai_compat_emits_structured_retry_log(monkeypatch):
    """Each retry writes one embedder.retry log event with attempt metadata."""
    import httpx
    import structlog.testing

    from app.embedding.openai_compat import OpenAICompatEmbedder

    async def fake_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    transport = _ScriptedTransport(
        [
            ("transport", "ConnectError"),
            ("ok", None),
        ]
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **kw: _RecordingClient(transport, *a, **kw))

    e = OpenAICompatEmbedder(
        EmbedderConfig(
            name="o",
            type="openai-compat",
            options={
                "base_url": "https://example.com/v1",
                "api_key": "k",
                "model": "bge-m3",
                "max_retries": 3,
                "initial_backoff": 0.0,
                "backoff_jitter": 0.0,
            },
        )
    )
    with structlog.testing.capture_logs() as cap:
        await e.embed(["a"])
    retry_events = [e for e in cap if e.get("event") == "embedder.retry"]
    assert len(retry_events) == 1
    rec = retry_events[0]
    assert rec["log_level"] == "warning"
    assert rec["attempt"] == 1
    assert rec["max_attempts"] == 4  # 1 initial + 3 retries
    assert rec["error_kind"] == "_T"


@pytest.mark.asyncio
async def test_bge_m3_lazy_load_without_dep(monkeypatch):
    """If sentence-transformers is missing, embed() raises EmbedderError."""
    from app.embedding.bge_m3 import BGEM3Embedder

    # Force lazy load to fail by raising ImportError on import.
    import sys

    sys.modules["sentence_transformers"] = None  # type: ignore[assignment]
    try:
        e = BGEM3Embedder(EmbedderConfig(name="b", type="bge-m3", options={}))
        with pytest.raises(EmbedderError):
            await e.embed(["x"])
    finally:
        sys.modules.pop("sentence_transformers", None)