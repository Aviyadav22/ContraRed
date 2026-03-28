"""
AI Backend Client — Vertex AI ONLY (enterprise, data residency compliant).

Consumer Gemini API is PROHIBITED — contract data must not transit public
Google AI endpoints. All AI calls go through Vertex AI with project-level
IAM, audit logging, and data residency guarantees.

Requires:
  - VERTEX_PROJECT_ID set in environment
  - google-cloud-aiplatform installed
  - Service account credentials (GOOGLE_APPLICATION_CREDENTIALS or Workload Identity)
"""

import logging
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_INITIALIZED: bool = False


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
