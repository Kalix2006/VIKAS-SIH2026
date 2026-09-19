from unittest.mock import patch
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app


async def test_request_id_header_injected_in_all_responses(client: AsyncClient) -> None:
    """Verify X-Request-ID is attached to every HTTP response."""
    response = await client.get("/health")
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) > 10


async def test_strict_schema_validation_rejects_extra_fields(client: AsyncClient) -> None:
    """Verify Pydantic extra='forbid' rejects unexpected fields with 422."""
    payload = {
        "email": "test@vikas.dev",
        "password": "validpassword123",
        "malicious_extra_field": "injected_value",
    }
    response = await client.post("/auth/login", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "extra_forbidden" in str(data) or "extra fields not permitted" in str(data).lower()


async def test_global_exception_handler_sanitizes_errors_in_production() -> None:
    """Verify unhandled exceptions do not leak stack traces or internals in production mode."""
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as ac:
        with patch.object(settings, "environment", "production"):
            with patch("app.routers.auth.svc_login", side_effect=Exception("Database syntax error near 'SELECT * FROM secrets'")):
                err_resp = await ac.post(
                    "/auth/login",
                    json={"email": "admin@vikas.gov", "password": "password123"},
                )
                assert err_resp.status_code == 500
                err_data = err_resp.json()
                assert "request_id" in err_data
                assert err_data["code"] == "INTERNAL_SERVER_ERROR"
                # Assert secret details are NOT leaked
                assert "Database syntax error" not in err_data["detail"]
                assert "An internal server error occurred" in err_data["detail"]


async def test_auth_login_rate_limiting(client: AsyncClient) -> None:
    """Verify rapid-fire requests trip the slowapi rate limiter (HTTP 429)."""
    # /auth/login is limited to 5/minute
    tripped = False
    for _ in range(8):
        resp = await client.post(
            "/auth/login",
            json={"email": "bruteforce@test.com", "password": "wrong"},
        )
        if resp.status_code == 429:
            tripped = True
            data = resp.json()
            assert data["code"] == "RATE_LIMIT_EXCEEDED"
            break
    assert tripped, "Rate limiter was expected to trigger HTTP 429 within 8 rapid requests"
