"""
Vertex AI Client — Enterprise-grade AI backend for ContraRed.

Uses Google Cloud Vertex AI exclusively. The consumer google.generativeai SDK
has been removed — all production traffic must go through Vertex AI which
provides data residency (asia-south1, Mumbai), DPA coverage, VPC-SC, CMEK,
and audit logging.

Authentication (in priority order):
  1. GOOGLE_APPLICATION_CREDENTIALS env var containing raw JSON (Render-friendly)
  2. GOOGLE_APPLICATION_CREDENTIALS env var containing a file path
  3. Application Default Credentials (GCE metadata, Workload Identity, etc.)
"""

import json
import logging
import threading
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_INITIALIZED: bool = False
_init_lock = threading.Lock()
_credentials = None  # Cached credentials object


def _resolve_credentials():
    """Resolve GCP credentials from env var (inline JSON or file path) or ADC."""
    import os
    creds_value = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")

    if not creds_value:
        # No explicit credentials — fall back to Application Default Credentials
        logger.info("No GOOGLE_APPLICATION_CREDENTIALS set, using Application Default Credentials")
        return None

    # Check if the value is raw JSON (starts with '{') vs a file path
    stripped = creds_value.strip()
    if stripped.startswith("{"):
        try:
            from google.oauth2 import service_account  # type: ignore[import-untyped]
            creds_info = json.loads(stripped)
            credentials = service_account.Credentials.from_service_account_info(
                creds_info,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            logger.info(
                "Loaded service account credentials from inline JSON (email=%s)",
                creds_info.get("client_email", "unknown"),
            )
            return credentials
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.error("Failed to parse inline JSON credentials: %s", exc)
            raise RuntimeError(
                "GOOGLE_APPLICATION_CREDENTIALS contains invalid JSON. "
                "Paste the full service account key JSON."
            ) from exc
    else:
        # It's a file path — let the SDK handle it via ADC
        logger.info("GOOGLE_APPLICATION_CREDENTIALS points to file: %s", stripped)
        return None


def _init_vertex() -> bool:
    """Initialise the Vertex AI SDK. Returns True on success."""
    global _credentials

    if not settings.VERTEX_PROJECT_ID:
        logger.error(
            "VERTEX_PROJECT_ID is not set. Vertex AI is required for production. "
            "Set VERTEX_PROJECT_ID and GOOGLE_APPLICATION_CREDENTIALS."
        )
        return False
    try:
        import vertexai  # type: ignore[import-untyped]

        _credentials = _resolve_credentials()

        init_kwargs = {
            "project": settings.VERTEX_PROJECT_ID,
            "location": settings.VERTEX_LOCATION,
        }
        if _credentials is not None:
            init_kwargs["credentials"] = _credentials

        vertexai.init(**init_kwargs)

        logger.info(
            "Vertex AI initialised (project=%s, location=%s, auth=%s)",
            settings.VERTEX_PROJECT_ID,
            settings.VERTEX_LOCATION,
            "service_account_json" if _credentials else "ADC",
        )
        return True
    except ImportError:
        logger.error(
            "google-cloud-aiplatform is not installed. "
            "Install with: pip install google-cloud-aiplatform"
        )
        return False
    except Exception as exc:
        logger.error("Vertex AI init failed: %s", exc)
        return False


def _ensure_init() -> bool:
    """Thread-safe lazy initialisation using double-checked locking."""
    global _INITIALIZED
    if _INITIALIZED:
        return True
    with _init_lock:
        if _INITIALIZED:
            return True
        _INITIALIZED = _init_vertex()
    return _INITIALIZED


def get_backend() -> Optional[str]:
    """Return 'vertex' if Vertex AI is available, else None."""
    if _ensure_init():
        return "vertex"
    return None


def get_generative_model(model_name: str) -> Any:
    """Return a Vertex AI GenerativeModel for the given model name.

    Raises:
        RuntimeError: If Vertex AI is not available.
    """
    if not _ensure_init():
        raise RuntimeError(
            "Vertex AI is not available. Set VERTEX_PROJECT_ID and "
            "GOOGLE_APPLICATION_CREDENTIALS, and install google-cloud-aiplatform."
        )
    from vertexai.generative_models import GenerativeModel  # type: ignore[import-untyped]
    return GenerativeModel(model_name)


def is_available() -> bool:
    """Return True if Vertex AI is usable."""
    return _ensure_init()
