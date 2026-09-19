"""Authentication and authorization utilities.

Handles JWT token creation/verification, password hashing (argon2),
and refresh token generation.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Argon2 is the primary hashing scheme (OWASP recommendation).
# bcrypt kept as deprecated fallback for any legacy hashes.
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    default="argon2",
    deprecated=["bcrypt"],
)


def create_access_token(
    subject: str,
    role: str,
    district_id: str,
    institute_id: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token.

    Payload includes user ID, role, district_id, and institute_id
    so downstream dependencies and RLS context can use them
    without a DB lookup on every request.
    """
    now = datetime.now(UTC)
    default_delta = timedelta(minutes=settings.access_token_expire_minutes)
    expire = now + (expires_delta or default_delta)
    to_encode: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "district_id": district_id,
        "institute_id": institute_id,
        "exp": expire,
        "iat": now,
        "type": "access",
    }
    encoded: str = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return encoded


def verify_token(token: str) -> dict[str, Any]:
    """Verify and decode a JWT token.

    Supports dual-secret verification for seamless zero-downtime rotation.

    Raises:
        JWTError: If the token is invalid or expired with all known secrets.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as primary_err:
        if settings.jwt_secret_fallback:
            try:
                payload = jwt.decode(
                    token,
                    settings.jwt_secret_fallback,
                    algorithms=[settings.jwt_algorithm],
                )
                return payload
            except JWTError:
                pass
        raise primary_err


def generate_refresh_token() -> str:
    """Generate a cryptographically secure refresh token.

    Returns a 64-byte hex string (128 chars). The raw token is sent
    to the client; only the SHA-256 hash is stored in the DB.
    """
    return secrets.token_hex(64)


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token with SHA-256 for DB storage.

    Refresh tokens are high-entropy random strings, not passwords,
    so a fast hash (SHA-256) is sufficient — no need for argon2.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def hash_password(password: str) -> str:
    """Hash a plaintext password using argon2."""
    result: str = pwd_context.hash(password)
    return result


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored hash.

    Handles both argon2 (current) and bcrypt (legacy) hashes
    transparently via passlib's deprecated scheme support.
    """
    valid: bool = pwd_context.verify(plain_password, hashed_password)
    return valid
