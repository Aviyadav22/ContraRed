"""
AI Backend Client — Vertex AI ONLY (enterprise, data residency compliant).

Consumer Gemini API is PROHIBITED — contract data must not transit public
Google AI endpoints. All AI calls go through Vertex AI with project-level
IAM, audit logging, and data residency guarantees.

Requires:
  - VERTEX_PROJECT_ID set in environment
  - google-cloud-aiplatform installed
  - Service account credentials via one of:
    a) GOOGLE_APPLICATION_CREDENTIALS pointing to a JSON key file
    b) GOOGLE_APPLICATION_CREDENTIALS containing raw JSON (Render/Heroku)
    c) Workload Identity (GKE/Cloud Run)
"""

import json
import logging
import os
import tempfile
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_INITIALIZED: bool = False
_CREDENTIALS_FILE: Optional[str] = None  # temp file path if we created one


def _setup_credentials() -> None:
    """Handle GOOGLE_APPLICATION_CREDENTIALS containing raw JSON.

    On PaaS platforms like Render, the service account JSON is pasted
    directly into an env var. The Google SDK expects a *file path*, so
    we write the JSON to a temp file and update the env var to point to it.
    """
    global _CREDENTIALS_FILE
    creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if not creds:
        return

    # Already a file path — nothing to do
    if not creds.strip().startswith("{"):
        return

    # It's raw JSON — validate and write to a temp file
    try:
        creds_dict = json.loads(creds)
        if creds_dict.get("type") != "service_account":
            logger.warning("GOOGLE_APPLICATION_CREDENTIALS JSON is not a service account key")
    except json.JSONDecodeError:
        logger.error("GOOGLE_APPLICATION_CREDENTIALS looks like JSON but failed to parse")
        return

    fd, path = tempfile.mkstemp(suffix=".json", prefix="gcp_sa_")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(creds)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path
        _CREDENTIALS_FILE = path
        logger.info("Wrote GCP service account credentials to temp file")
    except Exception as exc:
        logger.error("Failed to write credentials temp file: %s", exc)
        os.close(fd)


def _ensure_initialized() -> bool:
    """Initialize Vertex AI SDK once. Returns True if ready."""
    global _INITIALIZED
    if _INITIALIZED:
        return True

    if not settings.VERTEX_PROJECT_ID:
        logger.error(
            "VERTEX_PROJECT_ID is not set. AI features are disabled. "
            "Consumer Gemini API is prohibited for contract data."
        )
        return False

    # Handle raw JSON credentials from PaaS env vars
    _setup_credentials()

    try:
        import vertexai  # type: ignore[import-untyped]
        vertexai.init(
            project=settings.VERTEX_PROJECT_ID,
            location=settings.VERTEX_LOCATION,
        )
        logger.info(
            "Vertex AI initialised (project=%s, location=%s)",
            settings.VERTEX_PROJECT_ID,
            settings.VERTEX_LOCATION,
        )
        _INITIALIZED = True
        return True
    except ImportError:
        logger.error(
            "google-cloud-aiplatform is not installed. "
            "Run: pip install google-cloud-aiplatform"
        )
        return False
    except Exception as exc:
        logger.error("Vertex AI init failed: %s", exc)
        return False


def get_backend() -> Optional[str]:
    """Return 'vertex' if Vertex AI is available, else None."""
    if _ensure_initialized():
        return "vertex"
    return None


def get_generative_model(model_name: str) -> Any:
    """
    Return a Vertex AI GenerativeModel for the given model name.

    Raises:
        RuntimeError: If Vertex AI is not configured or available.
    """
    if not _ensure_initialized():
        raise RuntimeError(
            "Vertex AI is not available. Set VERTEX_PROJECT_ID and ensure "
            "google-cloud-aiplatform is installed with valid credentials. "
            "Consumer Gemini API is prohibited for contract data."
        )

    from vertexai.generative_models import GenerativeModel  # type: ignore[import-untyped]
    return GenerativeModel(model_name)


def is_available() -> bool:
    """Return True if Vertex AI is configured and ready."""
    return _ensure_initialized()
