"""Health check endpoint.

Performs active async database ping (SELECT 1) and returns 200 (healthy)
or 503 (unhealthy) for container orchestrators and deployment platforms.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Return service and database health status.

    Returns 200 if API and DB are connected; 503 if DB is unreachable.
    """
    try:
        await db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "service": "vikas-api",
        }
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "service": "vikas-api",
        }
