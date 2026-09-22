"""Tests for the database-connected health check endpoint."""

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient


async def test_health_returns_200_when_database_healthy(client: AsyncClient) -> None:
    """Verify /health returns 200 and reports database connected."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["service"] == "vikas-api"


async def test_health_returns_503_when_database_unreachable(
    client: AsyncClient,
) -> None:
    """Verify /health returns 503 and reports database disconnected when query fails."""
    with patch(
        "app.routers.health.AsyncSession.execute", new_callable=AsyncMock
    ) as mock_exec:
        mock_exec.side_effect = Exception("DB Connection Timeout")
        response = await client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"
