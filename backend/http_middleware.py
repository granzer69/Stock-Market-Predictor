"""Request logging and lightweight research rate limiting."""

from __future__ import annotations

import logging
import threading
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app_config import research_max_concurrent

logger = logging.getLogger("bharat_desk")

_research_lock = threading.Lock()
_research_active = 0


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-Id"] = request_id
        logger.info(
            "%s %s %s %.1fms",
            request_id,
            request.method,
            request.url.path,
            elapsed_ms,
        )
        return response


class ResearchRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api/research/backtest"):
            return await call_next(request)

        global _research_active
        limit = research_max_concurrent()
        with _research_lock:
            if _research_active >= limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": f"Too many concurrent backtests (limit {limit}). Retry shortly."},
                )
            _research_active += 1
        try:
            return await call_next(request)
        finally:
            with _research_lock:
                _research_active -= 1
