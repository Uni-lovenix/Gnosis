"""OpenAI-compatible remote embedder.

Talks to ``POST {base_url}/embeddings`` with the standard ``{"input": [...],
"model": "..."}`` body. Works against any compatible endpoint (Ollama,
DashScope, vLLM, OpenRouter, etc.).

Resilience (KI-03):

* Transient network errors (``httpx.TransportError`` — connection refused,
  timeout, broken pipe) are retried with exponential backoff + jitter.
* HTTP 5xx and 429 responses are retried; other 4xx responses (bad request,
  unauthorized, …) are configuration errors and surface immediately.
* Max attempts is configurable via the ``max_retries`` option (default 3,
  i.e. initial attempt + up to 3 retries). Backoff is bounded by
  ``initial_backoff`` / ``max_backoff``; a small jitter fraction
  (``backoff_jitter``) avoids synchronized retry storms.
* Each retry emits a structured ``embedder.retry`` log event with attempt
  number, status code / error kind, and the planned sleep duration so an
  operator can correlate a slow embedding call with its retry ladder.
"""
from __future__ import annotations

import asyncio
import random

import httpx

from app.embedding.base import Embedder, EmbedderConfig, EmbedderError, register_embedder
from app.observability.logging import get_logger

log = get_logger(__name__)


def _is_retryable_response(status_code: int) -> bool:
    """5xx and 429 are retryable; other 4xx are configuration errors."""
    if status_code == 429:
        return True
    return 500 <= status_code < 600


class OpenAICompatEmbedder(Embedder):
    type = "openai-compat"

    def __init__(self, config: EmbedderConfig) -> None:
        super().__init__(config)
        opts = config.options
        if "base_url" not in opts or "api_key" not in opts:
            raise EmbedderError("openai-compat requires base_url and api_key")
        self.base_url = opts["base_url"].rstrip("/")
        self.api_key = opts["api_key"]
        self.model = opts.get("model", "bge-m3")
        self.dim = int(opts.get("dim", 1024))
        self.timeout = float(opts.get("timeout", 60))
        # KI-03: retry policy. Defaults tuned for an Ollama daemon on localhost.
        self.max_retries = max(0, int(opts.get("max_retries", 3)))
        self.initial_backoff = max(0.0, float(opts.get("initial_backoff", 0.5)))
        self.max_backoff = max(0.0, float(opts.get("max_backoff", 8.0)))
        # Fraction of the computed backoff applied as +/- jitter (0.0–1.0).
        self.backoff_jitter = max(0.0, min(1.0, float(opts.get("backoff_jitter", 0.1))))

    def _backoff_for(self, attempt: int) -> float:
        """Return sleep seconds before retry N (1-indexed) with bounded jitter."""
        if self.initial_backoff == 0 or self.max_backoff == 0:
            return 0.0
        base = min(self.initial_backoff * (2 ** (attempt - 1)), self.max_backoff)
        if self.backoff_jitter > 0:
            spread = base * self.backoff_jitter
            base = base + random.uniform(-spread, spread)
        return max(0.0, base)

    async def _post_embeddings(self, client: httpx.AsyncClient, texts: list[str]) -> list[list[float]]:
        r = await client.post(
            f"{self.base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={"model": self.model, "input": texts},
        )
        if r.status_code >= 400:
            # Tag with structured metadata so the retry helper can decide policy.
            err = EmbedderError(f"remote embed failed {r.status_code}: {r.text[:200]}")
            err.kb_status_code = r.status_code  # type: ignore[attr-defined]
            err.kb_retryable = _is_retryable_response(r.status_code)  # type: ignore[attr-defined]
            raise err
        body = r.json()
        items = sorted(body.get("data", []), key=lambda x: x.get("index", 0))
        return [item["embedding"] for item in items]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        last_error: EmbedderError | None = None
        # Attempt 0 = initial call; attempts 1..max_retries = retries.
        total_attempts = self.max_retries + 1
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(total_attempts):
                try:
                    vecs = await self._post_embeddings(client, texts)
                except httpx.TransportError as exc:
                    kind = type(exc).__name__
                    if attempt >= self.max_retries:
                        raise EmbedderError(
                            f"remote embed failed after {attempt + 1} attempt(s): {kind}: {exc}"
                        ) from exc
                    sleep_s = self._backoff_for(attempt + 1)
                    log.warning(
                        "embedder.retry",
                        attempt=attempt + 1,
                        max_attempts=total_attempts,
                        error_kind=kind,
                        sleep_seconds=round(sleep_s, 3),
                        reason=str(exc)[:200],
                    )
                    await asyncio.sleep(sleep_s)
                    last_error = EmbedderError(str(exc))
                    last_error.kb_retryable = True  # type: ignore[attr-defined]
                    continue
                except EmbedderError as exc:
                    status = getattr(exc, "kb_status_code", None)
                    retryable = getattr(exc, "kb_retryable", False)
                    if not retryable or attempt >= self.max_retries:
                        # Either a permanent 4xx, or retries exhausted.
                        raise
                    sleep_s = self._backoff_for(attempt + 1)
                    log.warning(
                        "embedder.retry",
                        attempt=attempt + 1,
                        max_attempts=total_attempts,
                        status_code=status,
                        sleep_seconds=round(sleep_s, 3),
                    )
                    await asyncio.sleep(sleep_s)
                    last_error = exc
                    continue
                # Success path.
                if vecs:
                    self.dim = len(vecs[0])
                return vecs
        # Loop exits only via raise/return; keep type-checkers happy.
        raise EmbedderError(
            f"remote embed failed after {total_attempts} attempt(s): {last_error}"
        )


register_embedder("openai-compat", OpenAICompatEmbedder)
