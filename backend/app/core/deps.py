"""FastAPI dependency injection functions.

Centralized dependencies for database sessions, authentication,
RBAC enforcement, and RLS context.
"""

from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_token
from app.db.session import async_session_maker, set_rls_context

# Bearer token scheme for JWT authentication
security_scheme = HTTPBearer()


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield a database session, ensuring cleanup on exit."""
    async with async_session_maker() as session:
        yield session


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_scheme)],
) -> dict[str, Any]:
    """Extract and validate the current user from the JWT bearer token.

    Returns:
        Dict with 'sub', 'role', 'district_id', 'institute_id' keys.

    Raises:
        HTTPException 401: If token is missing, invalid, or expired.
    """
    try:
        payload = verify_token(credentials.credentials)
        user_id: str | None = payload.get("sub")
        role: str | None = payload.get("role")
        district_id: str | None = payload.get("district_id")
        token_type: str | None = payload.get("type")

        if user_id is None or role is None or district_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        return {
            "sub": user_id,
            "role": role,
            "district_id": district_id,
            "institute_id": payload.get("institute_id"),
        }
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from None


def require_role(
    *allowed_roles: str,
) -> Callable[..., Coroutine[Any, Any, dict[str, Any]]]:
    """Factory for role-based access control dependencies.

    Usage::

        @router.get(
            "/admin",
            dependencies=[Depends(require_role("planner"))],
        )

    Returns:
        A FastAPI dependency that checks the user's role.
    """

    async def _check_role(
        current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    ) -> dict[str, Any]:
        if current_user["role"] not in allowed_roles:
            role = current_user["role"]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' not authorized",
            )
        return current_user

    return _check_role


async def get_db_with_rls(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> AsyncSession:
    """Yield a DB session with RLS context set for the current user.

    MUST be used instead of get_db for any route that accesses
    RLS-protected tables. Sets SET LOCAL variables at the start
    of the transaction so RLS policies can read the current user's
    identity.

    The SET LOCAL scope is per-transaction, so the variables
    automatically reset when the session/transaction ends — no risk
    of stale values leaking across pooled connections.
    """
    await set_rls_context(
        session=db,
        user_id=current_user["sub"],
        role=current_user["role"],
        district_id=current_user["district_id"],
        institute_id=current_user.get("institute_id"),
    )
    return db


def require_own_scope(
    scope_field: str,
) -> Callable[..., Coroutine[Any, Any, dict[str, Any]]]:
    """Factory for ownership-scoped access control.

    Checks that the current user's scope (district_id, institute_id,
    or user_id) matches the requested resource. Planners bypass
    scope checks since they have cross-district access.

    This is the application-layer mirror of the RLS policies —
    defense in depth, not a replacement.

    Args:
        scope_field: Which JWT claim to check. One of:
            - 'district_id': compare user's district with resource
            - 'institute_id': compare user's institute with resource
            - 'user_id': compare user's sub with resource

    Usage::

        @router.get("/courses/{district_id}")
        async def get_courses(
            district_id: uuid.UUID,
            user: dict = Depends(
                require_own_scope("district_id")
            ),
        ):
            ...
    """

    async def _check_scope(
        request: Request,
        current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    ) -> dict[str, Any]:
        # Planners have cross-district/institute read access
        if current_user["role"] == "planner":
            return current_user

        # Determine the claim key in the JWT
        if scope_field == "user_id":
            jwt_value = current_user["sub"]
        else:
            jwt_value = current_user.get(scope_field)

        # Get the resource value from path params or query
        resource_value = request.path_params.get(
            scope_field
        ) or request.query_params.get(scope_field)

        if resource_value is None:
            # If the scope field isn't in the request,
            # let the route handler deal with it
            return current_user

        if str(jwt_value) != str(resource_value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(f"Access denied: {scope_field} mismatch"),
            )

        return current_user

    return _check_scope
