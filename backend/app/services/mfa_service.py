"""
MFA (Multi-Factor Authentication) Service — TOTP-based.

Uses pyotp for TOTP generation/verification and provides:
  - Secret generation + provisioning URI (for QR codes)
  - TOTP code verification
  - Backup code generation, hashing, and verification
  - Enable / disable MFA on a user record

Backup codes are bcrypt-hashed before storage so a DB leak does not
compromise them.
"""

from __future__ import annotations

import logging
import secrets
import string
from typing import List, Optional, Tuple

import bcrypt
import pyotp
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

logger = logging.getLogger(__name__)

# Number of one-time backup codes generated during MFA setup
BACKUP_CODE_COUNT = 10
BACKUP_CODE_LENGTH = 8  # 8-char alphanumeric codes


# ---------------------------------------------------------------------------
# Secret / provisioning helpers
# ---------------------------------------------------------------------------

def generate_totp_secret() -> str:
    """Generate a new base32-encoded TOTP secret."""
    return pyotp.random_base32()


def get_provisioning_uri(secret: str, email: str, issuer: str = "ContraRed") -> str:
    """
    Return an otpauth:// URI suitable for QR code rendering.

    Clients scan this with Google Authenticator, Authy, 1Password, etc.
    """
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def verify_totp_code(secret: str, code: str) -> bool:
    """
    Verify a 6-digit TOTP code against the secret.

    Allows a 1-step window (±30 s) to account for clock drift.
    """
    if not secret or not code:
        return False
    from app.core.encryption import decrypt_text
    decrypted_secret = decrypt_text(secret)
    totp = pyotp.TOTP(decrypted_secret)
    return totp.verify(code, valid_window=1)


# ---------------------------------------------------------------------------
# Backup codes
# ---------------------------------------------------------------------------

def _generate_raw_backup_code() -> str:
    """Generate a single human-readable backup code (e.g. 'A3K9-M2X7')."""
    chars = string.ascii_uppercase + string.digits
    part1 = "".join(secrets.choice(chars) for _ in range(BACKUP_CODE_LENGTH // 2))
    part2 = "".join(secrets.choice(chars) for _ in range(BACKUP_CODE_LENGTH // 2))
    return f"{part1}-{part2}"


def generate_backup_codes(count: int = BACKUP_CODE_COUNT) -> List[str]:
    """Generate a list of unique plaintext backup codes."""
    codes: set[str] = set()
    while len(codes) < count:
        codes.add(_generate_raw_backup_code())
    return sorted(codes)


def hash_backup_code(code: str) -> str:
    """Bcrypt-hash a single backup code for safe DB storage."""
    return bcrypt.hashpw(
        code.replace("-", "").upper().encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def verify_backup_code(code: str, hashed: str) -> bool:
    """Verify a plaintext backup code against its bcrypt hash."""
    try:
        return bcrypt.checkpw(
            code.replace("-", "").upper().encode("utf-8"),
            hashed.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def hash_backup_codes(codes: List[str]) -> List[str]:
    """Hash all backup codes for DB storage."""
    return [hash_backup_code(c) for c in codes]


# ---------------------------------------------------------------------------
# High-level service functions (operate on User + DB session)
# ---------------------------------------------------------------------------

async def setup_mfa(user: User, db: AsyncSession) -> Tuple[str, str, List[str]]:
    """
    Initialize MFA for a user.

    Returns:
        (secret, provisioning_uri, plaintext_backup_codes)

    The caller MUST show the backup codes to the user exactly once.
    After this call, `user.mfa_enabled` is still False — it becomes True
    only after the user verifies their first TOTP code via `confirm_mfa_setup`.
    """
    secret = generate_totp_secret()
    uri = get_provisioning_uri(secret, user.email)
    backup_codes = generate_backup_codes()

    # Encrypt secret before storage (degrades gracefully if key not set)
    from app.core.encryption import encrypt_text
    user.mfa_secret = encrypt_text(secret)
    user.mfa_backup_codes = {"codes": hash_backup_codes(backup_codes)}
    # mfa_enabled stays False until confirm_mfa_setup

    await db.flush()

    logger.info(f"MFA setup initiated for user {user.email}")
    return secret, uri, backup_codes


async def confirm_mfa_setup(user: User, code: str, db: AsyncSession) -> bool:
    """
    Verify the first TOTP code to confirm MFA setup.

    If the code is valid, sets `user.mfa_enabled = True`.
    Returns True on success, False on failure.
    """
    if not user.mfa_secret:
        return False

    if not verify_totp_code(user.mfa_secret, code):
        return False

    user.mfa_enabled = True
    await db.flush()

    logger.info(f"MFA confirmed and enabled for user {user.email}")
    return True


async def verify_mfa(user: User, code: str, db: AsyncSession) -> bool:
    """
    Verify a TOTP code OR a backup code during login.

    If a backup code is used, it is consumed (removed from the stored list).
    Returns True on success, False on failure.
    """
    if not user.mfa_enabled or not user.mfa_secret:
        return False

    # Try TOTP first
    if verify_totp_code(user.mfa_secret, code):
        return True

    # Try backup codes
    return await _try_backup_code(user, code, db)


async def _try_backup_code(user: User, code: str, db: AsyncSession) -> bool:
    """Check code against stored backup codes; consume on match."""
    backup_data = user.mfa_backup_codes
    if not backup_data or "codes" not in backup_data:
        return False

    hashed_codes: List[str] = backup_data["codes"]
    for idx, hashed in enumerate(hashed_codes):
        if verify_backup_code(code, hashed):
            # Consume the backup code
            remaining = hashed_codes[:idx] + hashed_codes[idx + 1:]
            user.mfa_backup_codes = {"codes": remaining}
            await db.flush()
            logger.info(
                f"Backup code used for user {user.email}. "
                f"{len(remaining)} codes remaining."
            )
            return True

    return False


async def disable_mfa(user: User, db: AsyncSession) -> None:
    """Disable MFA for a user and clear stored secrets."""
    user.mfa_enabled = False
    user.mfa_secret = None
    user.mfa_backup_codes = None
    await db.flush()
    logger.info(f"MFA disabled for user {user.email}")


async def regenerate_backup_codes(user: User, db: AsyncSession) -> List[str]:
    """
    Generate a fresh set of backup codes (invalidates all previous ones).

    Returns the plaintext codes — caller must show them to the user.
    """
    if not user.mfa_enabled:
        raise ValueError("MFA is not enabled for this user")

    backup_codes = generate_backup_codes()
    user.mfa_backup_codes = {"codes": hash_backup_codes(backup_codes)}
    await db.flush()

    logger.info(f"Backup codes regenerated for user {user.email}")
    return backup_codes


def is_mfa_required_for_org(org) -> bool:
    """Check if the user's organization enforces MFA."""
    if org is None:
        return False
    return getattr(org, "mfa_required", False)
