"""FastAPI application factory and configuration.

This is the entry point for the VIKAS backend API.
Run with: uvicorn app.main:app --reload
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.errors import global_exception_handler, http_exception_handler
from app.core.limiter import limiter, rate_limit_exceeded_handler
from app.core.logging import RequestTracingMiddleware
from app.routers import (
    auth,
    employer,
    health,
    institute,
    internal,
    panel,
    planner,
    trainee,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    yield
    # Shutdown


app = FastAPI(
    title="VIKAS API",
    description=(
        "Viksit India Kaushal Alignment System"
        " \u2014 Skill Demand-Supply Gap Platform"
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# Attach rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Global sanitized exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Request ID & latency tracing middleware
app.add_middleware(RequestTracingMiddleware)

# CORS middleware — origins loaded from environment, wildcard forbidden in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(internal.router)
app.include_router(panel.router)
app.include_router(trainee.router)
app.include_router(institute.router)
app.include_router(planner.router)
app.include_router(employer.router)
