"""
JWT Authentication utilities.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
import jwt
from pydantic import BaseModel

from app.core.config import settings


class TokenData(BaseModel):
    """JWT token payload data."""
    user_id: str
    email: str
    role: str
    organization_id: Optional[str] = None
    jti: Optional[str] = None


class Token(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


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
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({
        "exp": expire,
        "type": "access",
        "jti": str(uuid.uuid4()),
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> Optional[TokenData]:
    """Decode and validate a JWT token. Validates token type to prevent misuse."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # Validate token type to prevent access tokens being used as refresh tokens
        token_type = payload.get("type")
        if token_type != expected_type:
            return None
        # Validate required claims are present
        sub = payload.get("sub")
        email = payload.get("email")
        if not sub or not email:
            return None
        return TokenData(
            user_id=sub,
            email=email,
            role=payload.get("role", ""),
            organization_id=payload.get("org_id"),
            jti=payload.get("jti"),
        )
    except jwt.InvalidTokenError:
        return None
