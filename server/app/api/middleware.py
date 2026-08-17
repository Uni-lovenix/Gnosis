"""Request correlation middleware.

Every HTTP request gets an ``X-Request-Id`` header (either echoed from the
caller or generated server-side) and the same id is bound into structlog's
contextvars so all logs emitted while handling that request can be correlated.
"""
from __future__ import annotations

import time
import uuid
from typing import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.observability.logging import get_logger

log = get_logger("http")


def install_request_context(app: FastAPI) -> None:
    """Register the correlation middleware on a FastAPI app."""

    @app.middleware("http")
    async def _request_context(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex
        clear_contextvars()
        bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        start = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            if response is not None:
                response.headers.setdefault("X-Request-Id", request_id)
                log.info(
                    "http.request",
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                )
            else:
                log.warning(
                    "http.request_failed",
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    duration_ms=duration_ms,
                )
            clear_contextvars()
