"""
HttpOnly cookie utilities for secure token storage.

Sets access_token and refresh_token as HttpOnly cookies, plus a
non-HttpOnly csrf_token cookie for double-submit CSRF protection.
"""

import secrets
from fastapi import Request, Response
from app.core.config import settings


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
) -> str:
    """
    Set HttpOnly auth cookies + CSRF cookie on the response.
    Returns the CSRF token value (also sent as cookie).
    """
    csrf_token = secrets.token_urlsafe(32)

    common = dict(
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )
    if settings.COOKIE_DOMAIN:
        common["domain"] = settings.COOKIE_DOMAIN

    # Access token — HttpOnly, short-lived
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **common,
    )

    # Refresh token — HttpOnly, long-lived
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        **common,
    )

    # CSRF token — NOT HttpOnly (JS must read it for double-submit pattern)
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **common,
    )

    return csrf_token


def clear_auth_cookies(response: Response) -> None:
    """Remove all auth cookies."""
    common = dict(
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )
    if settings.COOKIE_DOMAIN:
        common["domain"] = settings.COOKIE_DOMAIN

    for key in ("access_token", "refresh_token", "csrf_token"):
        response.delete_cookie(key=key, **common)


def get_token_from_request(request: Request) -> str | None:
    """
    Extract access token from request.
    Priority: Authorization header > access_token cookie.
    """
    # 1. Check Authorization header (Bearer token)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if token:
            return token

    # 2. Fall back to HttpOnly cookie
    return request.cookies.get("access_token")


def validate_csrf(request: Request) -> bool:
    """
    Validate CSRF double-submit: X-CSRF-Token header must match csrf_token cookie.
    Only required for state-changing methods (POST, PUT, PATCH, DELETE).
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return True

    csrf_cookie = request.cookies.get("csrf_token")
    csrf_header = request.headers.get("X-CSRF-Token")

    # If no CSRF cookie is set, the request is using Bearer auth (no CSRF needed)
    if not csrf_cookie:
        return True

    return csrf_cookie == csrf_header
