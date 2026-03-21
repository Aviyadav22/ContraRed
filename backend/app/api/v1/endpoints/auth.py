"""
Authentication endpoints.

Includes:
  - Registration & login (with MFA support)
  - Token refresh
  - Password change
  - MFA setup / verify / disable
  - Current user profile
"""

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import sqlalchemy.exc
from sqlalchemy.orm import selectinload
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.db.session import get_db
from app.models.user import User, UserRole, SubscriptionTier
from app.models.audit_log import log_audit_event
from app.core.security import (
    verify_password,
    get_password_hash,
    get_dummy_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    Token,
)
from app.services.mfa_service import (
    setup_mfa,
    confirm_mfa_setup,
    verify_mfa,
    disable_mfa,
    regenerate_backup_codes,
    is_mfa_required_for_org,
)
from app.services.token_service import get_token_blacklist

logger = logging.getLogger(__name__)

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

# Short-lived MFA challenge token expiry (5 minutes)
MFA_CHALLENGE_EXPIRE_MINUTES = 5

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def _get_client_ip(request: Request) -> Optional[str]:
    """Get real client IP, respecting X-Forwarded-For from reverse proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


# Request/Response schemas
class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    subscription_tier: str
    organization_id: Optional[str] = None
    mfa_enabled: bool = False

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
    mfa_required: bool = False
    mfa_setup_required: bool = False
    mfa_challenge_token: Optional[str] = None
    new_ip_detected: Optional[bool] = None
    message: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh_token: str


# --- MFA schemas ---
class MFASetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    backup_codes: List[str]
    qr_uri: str  # Same as provisioning_uri, convenience alias


class MFAVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=8, description="6-digit TOTP code or backup code")


class MFAChallengeRequest(BaseModel):
    mfa_challenge_token: str = Field(..., description="Temporary token from login response")
    code: str = Field(..., min_length=4, max_length=10, description="TOTP code or backup code (e.g. A3K9-M2X7)")


# Dependency to get current user
async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Extract and validate user from JWT token (header or cookie).

    Checks:
    1. Token from Authorization header or access_token cookie
    2. CSRF validation for cookie-based auth
    3. Token signature + expiry (via decode_token)
    4. Token not on Redis blacklist (via token_service)
    5. User exists and is active
    """
    from app.core.cookies import get_token_from_request, validate_csrf

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Resolve token: Authorization header (via oauth2_scheme) > cookie
    if not token:
        token = request.cookies.get("access_token")
        if token and not validate_csrf(request):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF validation failed",
            )

    if not token:
        raise credentials_exception

    token_data = decode_token(token)
    if token_data is None:
        # Also try mfa_setup tokens so setup endpoints work
        token_data = decode_token(token, expected_type="mfa_setup")
        if token_data is None:
            raise credentials_exception

    # Check token blacklist (gracefully degrades if Redis unavailable)
    if token_data.jti:
        blacklist = await get_token_blacklist()
        if await blacklist.is_revoked(token_data.jti):
            logger.info("Rejected revoked token jti=%s", token_data.jti[:8] + "...")
            raise credentials_exception

    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise credentials_exception

    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def register(
    request: Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user."""
    try:
        # Check if email already exists
        result = await db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Create new user
        user = User(
            email=user_data.email,
            name=user_data.name,
            password_hash=get_password_hash(user_data.password),
            role=UserRole.REVIEWER,
            subscription_tier=SubscriptionTier.FREE,
        )

        db.add(user)
        await db.flush()

        # Audit log
        await log_audit_event(
            db, user=user, action="user_registered", resource_type="auth",
            resource_name=user.email,
            ip_address=_get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        await db.commit()
        await db.refresh(user)

        return UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            role=user.role.value,
            subscription_tier=user.subscription_tier.value,
            organization_id=str(user.organization_id) if user.organization_id else None,
        )
    except HTTPException:
        raise
    except sqlalchemy.exc.IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    except Exception as e:
        logger.error("Registration failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Login with email and password.

    If the user has MFA enabled (or the org requires it), the response will
    include `mfa_required: true` and a short-lived `mfa_challenge_token`.
    The client must then call POST /auth/mfa/challenge with the token + TOTP code.
    """
    # Eagerly load organization to check mfa_required
    result = await db.execute(
        select(User)
        .options(selectinload(User.organization))
        .where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()

    # Check account lockout
    if user and user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked due to too many failed attempts. Try again later.",
        )

    if not user:
        # Constant-time: run password verification even when user not found
        verify_password(form_data.password, get_dummy_hash())
        await log_audit_event(
            db, user=None, action="login_failed", resource_type="auth",
            resource_name=form_data.username, status="failure",
            ip_address=_get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            user_email=form_data.username,
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, user.password_hash or ""):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        await log_audit_event(
            db, user=user, action="login_failed", resource_type="auth",
            resource_name=form_data.username, status="failure",
            ip_address=_get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            user_email=form_data.username,
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )

    # Reset lockout on successful password verification
    user.failed_login_attempts = 0
    user.locked_until = None

    # ----- MFA check -----
    org_requires_mfa = is_mfa_required_for_org(user.organization)
    user_has_mfa = user.mfa_enabled

    if user_has_mfa or org_requires_mfa:
        if not user_has_mfa and org_requires_mfa:
            # Org requires MFA but user hasn't set it up yet.
            # Let them log in but flag that MFA setup is required.
            await log_audit_event(
                db, user=user, action="login_mfa_setup_required", resource_type="auth",
                resource_name=user.email,
                ip_address=_get_client_ip(request),
                user_agent=request.headers.get("user-agent"),
            )
            await db.commit()
            # Issue a limited token that only allows MFA setup
            mfa_setup_token = create_access_token(
                {
                    "sub": str(user.id),
                    "email": user.email,
                    "role": user.role.value,
                    "org_id": str(user.organization_id) if user.organization_id else None,
                    "type": "mfa_setup",
                    "mfa_setup_required": True,
                },
                expires_delta=timedelta(minutes=MFA_CHALLENGE_EXPIRE_MINUTES),
            )
            return {
                "mfa_required": True,
                "mfa_setup_required": True,
                "mfa_challenge_token": mfa_setup_token,
                "access_token": "",
                "refresh_token": "",
                "token_type": "bearer",
                "user": _user_response_dict(user),
                "message": "Your organization requires MFA. Please set up MFA to continue.",
            }

        # User has MFA enabled — issue a challenge token (not a full auth token)
        mfa_challenge_token = create_access_token(
            {
                "sub": str(user.id),
                "email": user.email,
                "type": "mfa_challenge",
                "role": user.role.value,
                "org_id": str(user.organization_id) if user.organization_id else None,
            },
            expires_delta=timedelta(minutes=MFA_CHALLENGE_EXPIRE_MINUTES),
        )

        await log_audit_event(
            db, user=user, action="login_mfa_challenge", resource_type="auth",
            resource_name=user.email,
            ip_address=_get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        await db.commit()

        return {
            "mfa_required": True,
            "mfa_setup_required": False,
            "mfa_challenge_token": mfa_challenge_token,
            "access_token": "",
            "refresh_token": "",
            "token_type": "bearer",
            "user": _user_response_dict(user),
        }

    # ----- No MFA — standard login -----
    user.last_login = datetime.now(timezone.utc)
    client_ip = _get_client_ip(request)

    # IP anomaly detection
    blacklist = await get_token_blacklist()
    ip_is_new = await blacklist.record_login_ip(str(user.id), client_ip)

    await log_audit_event(
        db, user=user, action="login_success", resource_type="auth",
        resource_name=user.email,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
        details=json.dumps({"new_ip": ip_is_new}) if ip_is_new else None,
    )
    await db.commit()

    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "org_id": str(user.organization_id) if user.organization_id else None,
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Register session + enforce concurrent session limit
    access_td = decode_token(access_token)
    if access_td and access_td.jti:
        evicted = await blacklist.register_session(str(user.id), access_td.jti)
        if evicted:
            logger.info("Evicted %d old sessions for user %s", len(evicted), user.email)

    # Set HttpOnly auth cookies
    from app.core.cookies import set_auth_cookies
    set_auth_cookies(response, access_token, refresh_token)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "mfa_required": False,
        "mfa_challenge_token": None,
        "new_ip_detected": ip_is_new,
        "user": _user_response_dict(user),
    }


def _user_response_dict(user: User) -> dict:
    """Build a user response dict (avoids repeating this everywhere)."""
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role.value,
        "subscription_tier": user.subscription_tier.value,
        "organization_id": str(user.organization_id) if user.organization_id else None,
        "mfa_enabled": user.mfa_enabled,
    }


@router.post("/refresh", response_model=Token)
@limiter.limit("30/minute")
async def refresh_token(
    request: Request,
    response: Response,
    body: Optional[RefreshRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token (revokes old refresh token).

    Accepts refresh_token from request body or from HttpOnly cookie.
    """
    # Get refresh token from body or cookie
    raw_refresh = (body.refresh_token if body and body.refresh_token else None) or request.cookies.get("refresh_token")
    if not raw_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required"
        )

    token_data = decode_token(raw_refresh, expected_type="refresh")

    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Check if the refresh token has been revoked
    if token_data.jti:
        blacklist = await get_token_blacklist()
        if await blacklist.is_revoked(token_data.jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked"
            )

    # Verify user still exists and is active
    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Revoke the old refresh token (one-time use)
    if token_data.jti:
        blacklist = await get_token_blacklist()
        await blacklist.revoke(token_data.jti)

    # Create new tokens
    new_token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "org_id": str(user.organization_id) if user.organization_id else None,
    }

    new_access = create_access_token(new_token_data)
    new_refresh = create_refresh_token(new_token_data)

    # Set HttpOnly auth cookies
    from app.core.cookies import set_auth_cookies
    set_auth_cookies(response, new_access, new_refresh)

    return Token(
        access_token=new_access,
        refresh_token=new_refresh,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        role=current_user.role.value,
        subscription_tier=current_user.subscription_tier.value,
        organization_id=str(current_user.organization_id) if current_user.organization_id else None,
        mfa_enabled=current_user.mfa_enabled,
    )


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v


@router.post("/change-password")
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    data: ChangePasswordRequest,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change current user's password and revoke current token."""
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    current_user.password_hash = get_password_hash(data.new_password)

    # Revoke the current token — forces re-login with new password
    token_data = decode_token(token)
    if token_data and token_data.jti:
        blacklist = await get_token_blacklist()
        await blacklist.revoke(token_data.jti)

    await log_audit_event(
        db=db, user=current_user, action="password_changed",
        resource_type="auth", resource_name=current_user.email,
        ip_address=_get_client_ip(request),
    )
    await db.commit()

    # Issue fresh tokens
    new_token_data = {
        "sub": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role.value,
        "org_id": str(current_user.organization_id) if current_user.organization_id else None,
    }

    return {
        "message": "Password changed successfully",
        "access_token": create_access_token(new_token_data),
        "refresh_token": create_refresh_token(new_token_data),
    }


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    token: Optional[str] = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Logout -- revoke current token via Redis blacklist and clear cookies."""
    # Resolve token from header or cookie
    raw_token = token or request.cookies.get("access_token")
    if raw_token:
        token_data = decode_token(raw_token)
        if token_data and token_data.jti:
            blacklist = await get_token_blacklist()
            await blacklist.revoke(token_data.jti)
            await blacklist.remove_session(str(current_user.id), token_data.jti)

    # Clear HttpOnly auth cookies
    from app.core.cookies import clear_auth_cookies
    clear_auth_cookies(response)

    await log_audit_event(
        db, user=current_user, action="logout",
        resource_type="auth", status="success",
        ip_address=_get_client_ip(request),
    )
    await db.commit()
    return {"message": "Logged out successfully"}


# ---------------------------------------------------------------------------
# MFA Challenge (second step of login)
# ---------------------------------------------------------------------------

@router.post("/mfa/challenge")
@limiter.limit("10/minute")
async def mfa_challenge(
    request: Request,
    response: Response,
    data: MFAChallengeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Second step of MFA login: verify the TOTP code using the challenge token.

    The client receives a `mfa_challenge_token` from the login endpoint and
    sends it here along with the 6-digit TOTP code (or backup code).
    On success, returns full access + refresh tokens.
    """
    # Decode the MFA challenge token (must be type "mfa_challenge", NOT "access")
    token_data = decode_token(data.mfa_challenge_token, expected_type="mfa_challenge")
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired MFA challenge token. Please log in again.",
        )

    # Fetch user
    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    if not user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled for this user",
        )

    # Verify the TOTP/backup code
    valid = await verify_mfa(user, data.code, db)

    if not valid:
        await log_audit_event(
            db, user=user, action="mfa_verify_failed", resource_type="auth",
            resource_name=user.email, status="failure",
            ip_address=_get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code",
        )

    # MFA verified — complete login
    user.last_login = datetime.now(timezone.utc)
    client_ip = _get_client_ip(request)

    # IP anomaly detection
    blacklist = await get_token_blacklist()
    ip_is_new = await blacklist.record_login_ip(str(user.id), client_ip)

    await log_audit_event(
        db, user=user, action="login_success_mfa", resource_type="auth",
        resource_name=user.email,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
        details=json.dumps({"new_ip": ip_is_new}) if ip_is_new else None,
    )
    await db.commit()

    token_data_dict = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "org_id": str(user.organization_id) if user.organization_id else None,
    }

    access_token = create_access_token(token_data_dict)
    refresh_token_str = create_refresh_token(token_data_dict)

    # Register session + enforce concurrent session limit
    access_td = decode_token(access_token)
    if access_td and access_td.jti:
        await blacklist.register_session(str(user.id), access_td.jti)

    # Set HttpOnly auth cookies
    from app.core.cookies import set_auth_cookies
    set_auth_cookies(response, access_token, refresh_token_str)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token_str,
        "token_type": "bearer",
        "mfa_required": False,
        "new_ip_detected": ip_is_new,
        "user": _user_response_dict(user),
    }


# ---------------------------------------------------------------------------
# MFA Setup / Verify / Disable
# ---------------------------------------------------------------------------

@router.post("/mfa/setup", response_model=MFASetupResponse)
async def mfa_setup_endpoint(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate MFA setup — returns a TOTP secret, provisioning URI (for QR code),
    and 10 backup codes.

    MFA is NOT yet active after this call. The user must verify their first
    TOTP code via POST /auth/mfa/verify to activate MFA.
    """
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled. Disable it first to re-setup.",
        )

    secret, uri, backup_codes = await setup_mfa(current_user, db)

    await log_audit_event(
        db, user=current_user, action="mfa_setup_initiated", resource_type="auth",
        resource_name=current_user.email,
        ip_address=_get_client_ip(request),
    )
    await db.commit()

    return MFASetupResponse(
        secret=secret,
        provisioning_uri=uri,
        qr_uri=uri,
        backup_codes=backup_codes,
    )


@router.post("/mfa/verify")
@limiter.limit("10/minute")
async def mfa_verify_endpoint(
    request: Request,
    data: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm MFA setup by verifying the first TOTP code.

    This activates MFA for the user. Must be called after /mfa/setup.
    """
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled",
        )

    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA setup has not been initiated. Call POST /auth/mfa/setup first.",
        )

    success = await confirm_mfa_setup(current_user, data.code, db)

    if not success:
        await log_audit_event(
            db, user=current_user, action="mfa_setup_verify_failed", resource_type="auth",
            resource_name=current_user.email, status="failure",
            ip_address=_get_client_ip(request),
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code. Please check your authenticator app and try again.",
        )

    await log_audit_event(
        db, user=current_user, action="mfa_enabled", resource_type="auth",
        resource_name=current_user.email,
        ip_address=_get_client_ip(request),
    )
    await db.commit()

    return {"message": "MFA has been enabled successfully", "mfa_enabled": True}


@router.post("/mfa/disable")
async def mfa_disable_endpoint(
    request: Request,
    data: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Disable MFA for the current user.

    Requires a valid TOTP code to confirm the action (prevents accidental disable).
    """
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled",
        )

    # Check if the org requires MFA — if so, users cannot disable it
    result = await db.execute(
        select(User)
        .options(selectinload(User.organization))
        .where(User.id == current_user.id)
    )
    user_with_org = result.scalar_one_or_none()
    if user_with_org and is_mfa_required_for_org(user_with_org.organization):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your organization requires MFA. You cannot disable it.",
        )

    # Verify TOTP code before disabling
    valid = await verify_mfa(current_user, data.code, db)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code. MFA was NOT disabled.",
        )

    await disable_mfa(current_user, db)

    await log_audit_event(
        db, user=current_user, action="mfa_disabled", resource_type="auth",
        resource_name=current_user.email,
        ip_address=_get_client_ip(request),
    )
    await db.commit()

    return {"message": "MFA has been disabled", "mfa_enabled": False}


@router.post("/mfa/backup-codes")
async def mfa_regenerate_backup_codes(
    request: Request,
    data: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Regenerate backup codes (invalidates all previous codes).

    Requires a valid TOTP code to confirm.
    Returns the new plaintext backup codes — show them to the user exactly once.
    """
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled",
        )

    # Verify current TOTP code
    valid = await verify_mfa(current_user, data.code, db)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code",
        )

    new_codes = await regenerate_backup_codes(current_user, db)

    await log_audit_event(
        db, user=current_user, action="mfa_backup_codes_regenerated", resource_type="auth",
        resource_name=current_user.email,
        ip_address=_get_client_ip(request),
    )
    await db.commit()

    return {"backup_codes": new_codes, "count": len(new_codes)}


# ---------------------------------------------------------------------------
# Password Reset Endpoints
# ---------------------------------------------------------------------------

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Request a password reset link.

    Always returns 200 regardless of whether the email exists
    to prevent email enumeration attacks.
    """
    # Check if user exists (for logging only — response is always the same)
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if user:
        from app.services.email_service import send_password_reset_email

        reset_token = create_access_token(
            {"sub": str(user.id), "type": "password_reset"},
            expires_delta=timedelta(hours=1),
        )
        await send_password_reset_email(user.email, reset_token)
        logger.info("Password reset requested for existing user (id=%s)", str(user.id)[:8])
        await log_audit_event(
            db, user=user, action="password_reset_requested", resource_type="auth",
            resource_name=user.email,
            ip_address=_get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        await db.commit()
    else:
        logger.info("Password reset requested for non-existent email")

    return {"message": "If an account exists with this email, a password reset link has been sent."}


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    token: str = Body(...),
    new_password: str = Body(..., min_length=8),
    db: AsyncSession = Depends(get_db),
):
    """
    Reset password using a valid reset token.

    The token must be a password_reset type JWT issued by /forgot-password.
    """
    # Decode the reset token
    token_data = decode_token(token, expected_type="password_reset")
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Find the user
    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Update password
    user.password_hash = get_password_hash(new_password)

    await log_audit_event(
        db, user=user, action="password_reset_completed", resource_type="auth",
        resource_name=user.email,
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()

    return {"message": "Password has been reset successfully"}
