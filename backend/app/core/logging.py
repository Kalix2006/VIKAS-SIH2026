"""Structured JSON logging and request tracing.

Provides:
- ContextVars for tracking request_id and authenticated user_id.
- JSONFormatter for structured machine-readable log records.
- RequestTracingMiddleware injecting X-Request-ID and logging request latency.
"""

import json
import logging
import time
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variables for correlation tracking across async tasks
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
user_id_ctx: ContextVar[str] = ContextVar("user_id", default="")


class StructuredJSONFormatter(logging.Formatter):
    """Custom logging formatter outputting JSON lines for log aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get() or getattr(record, "request_id", None),
            "user_id": user_id_ctx.get() or getattr(record, "user_id", None),
        }

        # Include latency or endpoint if passed in extra
        if hasattr(record, "endpoint"):
            log_data["endpoint"] = record.endpoint
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        if hasattr(record, "latency_ms"):
            log_data["latency_ms"] = record.latency_ms

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


# Configure root logger
logger = logging.getLogger("vikas")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
handler.setFormatter(StructuredJSONFormatter())
logger.handlers = [handler]
logger.propagate = False


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Middleware injecting correlation ID (X-Request-ID) and logging latency."""

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Response:
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = req_id
        token = request_id_ctx.set(req_id)

        start_time = time.perf_counter()
        try:
            response: Response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            response.headers["X-Request-ID"] = req_id

            # Log non-health endpoints at INFO level
            if request.url.path != "/health":
                logger.info(
                    f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)",
                    extra={
                        "endpoint": request.url.path,
                        "status_code": response.status_code,
                        "latency_ms": duration_ms,
                    },
                )
            return response
        finally:
            request_id_ctx.reset(token)

