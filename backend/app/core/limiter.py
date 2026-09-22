"""Rate limiting configuration using slowapi.

Provides a centralized Limiter instance with IP-based rate limiting
for auth endpoints and quota-sensitive LLM endpoints (trainee chat).
"""

from os import getenv

from fastapi import Request, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

# Read optional Redis storage URL, default to in-memory
storage_uri = getenv("REDIS_URL", "memory://")

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri=storage_uri,
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Return structured RFC 7807 429 response when rate limit is tripped."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": f"Rate limit exceeded: {exc.detail}",
            "code": "RATE_LIMIT_EXCEEDED",
        },
    )
