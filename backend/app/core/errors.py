"""Global error handling and exception sanitization.

Ensures no raw stack traces or internal DB errors leak to clients in production.
"""

import uuid

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import logger, request_id_ctx


async def global_exception_handler(request: Request, exc: Exception) -> Response:
    """Sanitize unhandled 500 errors and log with request correlation ID."""
    req_id = (
        getattr(request.state, "request_id", None)
        or request_id_ctx.get()
        or str(uuid.uuid4())
    )

    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: {exc}",
        exc_info=True,
        extra={"endpoint": request.url.path},
    )

    if settings.environment == "production":
        # Mask internals completely in production
        detail = "An internal server error occurred. Please contact system support."
    else:
        # Include exception summary during local development & testing
        detail = f"Internal server error: {type(exc).__name__}: {str(exc)}"

    return JSONResponse(
        status_code=500,
        content={
            "detail": detail,
            "request_id": req_id,
            "code": "INTERNAL_SERVER_ERROR",
        },
        headers={"X-Request-ID": req_id},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> Response:
    """Ensure standard HTTPExceptions also include correlation ID."""
    req_id = (
        getattr(request.state, "request_id", None)
        or request_id_ctx.get()
        or str(uuid.uuid4())
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "request_id": req_id,
            "code": f"HTTP_{exc.status_code}",
        },
        headers={"X-Request-ID": req_id},
    )

