"""
JWT Authentication utilities.

Security features:
- Token type validation (access vs refresh) to prevent token type confusion.
- JTI (JWT ID) on every token for revocation support.
- Integration with Redis-backed blacklist via ``token_service``.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
import jwt
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)


class TokenData(BaseModel):
    """JWT token payload data."""
    user_id: uuid.UUID
    email: str
    role: str
    organization_id: Optional[str] = None
    jti: Optional[str] = None
    token_type: str = "access"


class Token(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    csrf_token: Optional[str] = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    password_bytes = plain_password.encode('utf-8')
    hash_bytes = hashed_password.encode('utf-8')
    try:
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except ValueError:
        return False


def get_password_hash(password: str) -> str:
    """Hash a password."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


# Initialize dummy hash after get_password_hash is defined
_DUMMY_HASH = get_password_hash("dummy-timing-oracle-prevention-value")


def get_dummy_hash() -> str:
    """Return a pre-computed hash for constant-time comparison when user not found."""
    return _DUMMY_HASH


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token with a unique JTI for revocation support."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    jti = str(uuid.uuid4())
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": jti,
    })
    # Preserve caller-specified type (e.g. "mfa_challenge"); default to "access"
    if "type" not in to_encode:
        to_encode["type"] = "access"
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token with a unique JTI for revocation support."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
        "jti": jti,
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> Optional[TokenData]:
    """Decode and validate a JWT token.

    Validates:
    - Signature and expiry (via PyJWT).
    - Token type (access vs refresh) to prevent type confusion.
    - Required claims (sub, email) are present.
    - ``iat`` (issued-at) is not in the future (clock skew tolerance: 60s).

    Does NOT check the blacklist — that requires async and is done in the
    ``get_current_user`` dependency.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"require": ["exp", "type", "jti"]},
        )
        # Validate token type to prevent access tokens being used as refresh tokens
        token_type = payload.get("type")
        if token_type != expected_type:
            return None

        # Validate issued-at is not in the future (with 60s clock skew tolerance)
        iat = payload.get("iat")
        if iat is not None:
            issued_at = datetime.fromtimestamp(iat, tz=timezone.utc)
            if issued_at > datetime.now(timezone.utc) + timedelta(seconds=60):
                logger.warning("Token has future iat — possible clock skew or forgery")
                return None

        # Validate required claims are present
        sub = payload.get("sub")
        email = payload.get("email")
        if not sub or not email:
            return None
        try:
            user_id = uuid.UUID(str(sub))
        except (AttributeError, TypeError, ValueError):
            logger.warning("Rejected token with non-UUID subject claim")
            return None

        return TokenData(
            user_id=user_id,
            email=email,
            role=payload.get("role", ""),
            organization_id=payload.get("org_id"),
            jti=payload.get("jti"),
            token_type=token_type,
        )
    except jwt.InvalidTokenError:
        return None
