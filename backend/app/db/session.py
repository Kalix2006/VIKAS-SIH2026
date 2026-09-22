"""Async database engine, session factory, and RLS context helper.

Uses SQLAlchemy 2.0 async API with asyncpg driver.
"""

import contextlib

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# Create async engine — pool settings tuned for a web application
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Set True for SQL query logging during development
    pool_size=5,  # Reasonable default for a modular monolith
    max_overflow=10,  # Allow burst connections beyond pool_size
    connect_args={
        "prepared_statement_cache_size": 0,
        "statement_cache_size": 0,
    },
)

# Session factory — each request gets its own session via get_db dependency
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def set_rls_context(
    session: AsyncSession,
    user_id: str,
    role: str,
    district_id: str,
    institute_id: str | None = None,
) -> None:
    """Set PostgreSQL session variables for Row-Level Security policies.

    MUST be called at the start of every authenticated request/transaction.
    Uses SET LOCAL so variables are scoped to the current transaction
    and automatically reset when the transaction ends — prevents stale
    values from leaking across requests sharing a pooled connection.

    Args:
        session: Active async database session.
        user_id: Current user's UUID as string.
        role: Current user's RBAC role.
        district_id: Current user's district UUID as string.
        institute_id: Current user's institute UUID (None if not applicable).
    """
    # Switch to non-superuser role so PostgreSQL enforces RLS policies
    # (Superusers always bypass RLS regardless of FORCE ROW LEVEL SECURITY)
    try:
        async with session.begin_nested():
            await session.execute(text("SET LOCAL ROLE vikas_app"))
    except Exception:
        pass

    # set_config(name, value, is_local=true) is transaction-scoped
    # and properly supports parameterized bindings in PostgreSQL
    await session.execute(
        text("SELECT set_config('app.current_user_id', :uid, true)"),
        {"uid": user_id},
    )
    await session.execute(
        text("SELECT set_config('app.current_user_role', :role, true)"),
        {"role": role},
    )
    await session.execute(
        text("SELECT set_config('app.current_district_id', :did, true)"),
        {"did": district_id},
    )
    await session.execute(
        text("SELECT set_config('app.current_institute_id', :iid, true)"),
        {"iid": institute_id or ""},
    )
