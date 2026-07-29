"""
Field-level Encryption — AES-256 via Fernet for stored clause text.

Usage::

    from app.core.encryption import encrypt_text, decrypt_text

    cipher = encrypt_text("Confidential clause content")
    plain  = decrypt_text(cipher)

When ``ENCRYPTION_KEY`` is not configured the helpers degrade gracefully:
- ``encrypt_text`` returns the plaintext unchanged.
- ``decrypt_text`` returns its input unchanged (assumes plaintext).

Generate a key::

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_fernet = None  # type: ignore[assignment]
_enabled: bool = False


def _init_fernet() -> None:
    """Lazy-initialise the Fernet cipher from settings."""
    global _fernet, _enabled

    if _fernet is not None or _enabled:
        return  # already initialised (or already failed)

    if not settings.ENCRYPTION_KEY:
        logger.info("ENCRYPTION_KEY not set — field-level encryption is disabled")
        return

    try:
        from cryptography.fernet import Fernet

        _fernet = Fernet(settings.ENCRYPTION_KEY.encode())
        _enabled = True
        logger.info("Field-level encryption enabled (AES-256 / Fernet)")
    except Exception as exc:
        logger.error("Failed to initialise Fernet encryption: %s — encryption disabled", exc)
        _fernet = None
        _enabled = False


def is_encryption_enabled() -> bool:
    """Return True if encryption is configured and usable."""
    _init_fernet()
    return _enabled


def encrypt_text(plaintext: str) -> str:
    """Encrypt *plaintext* with AES-256 Fernet.

    Returns the Fernet token as a UTF-8 string.  If encryption is not
    configured, returns *plaintext* unchanged.
    """
    _init_fernet()
    if not _enabled or _fernet is None:
        return plaintext
    try:
        return _fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")
    except Exception as exc:
        logger.error("Encryption failed: %s", exc)
        raise RuntimeError(f"Encryption failed — cannot store sensitive data in plaintext: {exc}") from exc


def decrypt_text(ciphertext: str) -> str:
    """Decrypt a Fernet token back to plaintext.

    If encryption is not configured or the token is not valid Fernet,
    returns *ciphertext* unchanged (assumes it was stored as plaintext
    before encryption was enabled).
    """
    _init_fernet()
    if not _enabled or _fernet is None:
        return ciphertext
    try:
        return _fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except Exception:
        # Not a valid Fernet token — likely pre-encryption plaintext.
        return ciphertext


def rotate_key(old_key: str, new_key: str, ciphertext: str) -> str:
    """Re-encrypt *ciphertext* from *old_key* to *new_key*.

    Useful during key rotation. Returns the re-encrypted Fernet token.
    Raises on failure so the caller can handle it explicitly.
    """
    from cryptography.fernet import Fernet

    old_fernet = Fernet(old_key.encode())
    new_fernet = Fernet(new_key.encode())
    plaintext = old_fernet.decrypt(ciphertext.encode("utf-8"))
    return new_fernet.encrypt(plaintext).decode("utf-8")
