"""Shared test fixtures for VIKAS backend test suite."""

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.deps import get_db
from app.core.limiter import limiter
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.district import District
from app.models.enums import UserRole
from app.models.institute import Institute
from app.models.user import User

# Test database engine using NullPool to prevent asyncpg loop conflicts across tests
test_db_url = settings.database_url_test or settings.database_url

import asyncio


async def _init_vikas_role():
    engine = create_async_engine(test_db_url, poolclass=NullPool)
    async with engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        try:
            await conn.execute(text("CREATE ROLE vikas_app NOLOGIN"))
            await conn.execute(text("GRANT USAGE ON SCHEMA public TO vikas_app"))
            await conn.execute(
                text("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO vikas_app")
            )
            await conn.execute(
                text(
                    "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO vikas_app"
                )
            )
            await conn.execute(text("GRANT vikas_app TO current_user"))
        except Exception:
            pass
    await engine.dispose()


asyncio.run(_init_vikas_role())

test_engine = create_async_engine(
    test_db_url,
    poolclass=NullPool,
    echo=False,
)

test_session_maker = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db() -> AsyncIterator[AsyncSession]:
    """Dependency override for get_db during tests."""
    async with test_session_maker() as session:
        yield session


# Apply dependency override to app
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> None:
    """Reset slowapi rate limits before each test execution."""
    limiter.reset()


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Yield an async database session for testing using NullPool."""
    async with test_session_maker() as session:
        yield session


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Async HTTP client for testing FastAPI endpoints."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
async def test_district(db_session: AsyncSession) -> District:
    """Ensure at least one test district exists."""
    stmt = select(District).where(District.name == "Pune")
    district = (await db_session.execute(stmt)).scalar_one_or_none()
    if not district:
        district = District(
            name="Pune",
            state="Maharashtra",
            centroid_lat=18.5204,
            centroid_lng=73.8567,
        )
        db_session.add(district)
        await db_session.commit()
        await db_session.refresh(district)
    return district


@pytest.fixture
async def test_district_beed(db_session: AsyncSession) -> District:
    """Ensure a second test district (Beed) exists for cross-district tests."""
    stmt = select(District).where(District.name == "Beed")
    district = (await db_session.execute(stmt)).scalar_one_or_none()
    if not district:
        district = District(
            name="Beed",
            state="Maharashtra",
            centroid_lat=18.9891,
            centroid_lng=75.7601,
        )
        db_session.add(district)
        await db_session.commit()
        await db_session.refresh(district)
    return district


@pytest.fixture
async def test_institute(
    db_session: AsyncSession, test_district: District
) -> Institute:
    """Ensure a test institute exists in Pune."""
    stmt = select(Institute).where(Institute.name == "Government ITI Pune")
    institute = (await db_session.execute(stmt)).scalar_one_or_none()
    if not institute:
        institute = Institute(
            name="Government ITI Pune",
            district_id=test_district.id,
            type="ITI",
        )
        db_session.add(institute)
        await db_session.commit()
        await db_session.refresh(institute)
    return institute


@pytest.fixture
def create_test_user(db_session: AsyncSession):
    """Factory fixture to create test users with specific roles and districts."""

    async def _create(
        email: str,
        role: UserRole,
        district_id: uuid.UUID,
        institute_id: uuid.UUID | None = None,
        password: str = "testpass123",
    ) -> User:
        stmt = select(User).where(User.email == email)
        existing = (await db_session.execute(stmt)).scalar_one_or_none()
        if existing:
            return existing

        user = User(
            email=email,
            password_hash=hash_password(password),
            role=role,
            full_name=f"Test {role.value}",
            district_id=district_id,
            institute_id=institute_id,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    return _create


@pytest.fixture
def auth_token_for():
    """Generate a valid JWT access token for a given user."""

    def _token(user: User) -> str:
        return create_access_token(
            subject=str(user.id),
            role=user.role.value if hasattr(user.role, "value") else str(user.role),
            district_id=str(user.district_id),
            institute_id=str(user.institute_id) if user.institute_id else None,
        )

    return _token
