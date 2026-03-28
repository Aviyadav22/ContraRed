"""
AI Backend Client — Vertex AI (enterprise) with consumer Gemini API fallback.

Priority order:
  1. Vertex AI (if VERTEX_PROJECT_ID is set and google-cloud-aiplatform installed)
  2. Consumer Gemini API (if GEMINI_API_KEY is set)
  3. None (AI features disabled)
"""

import logging
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_BACKEND: Optional[str] = None
_BACKEND_CHECKED: bool = False


def get_backend() -> Optional[str]:
    """Return 'vertex', 'consumer', or None depending on available config."""
    global _BACKEND, _BACKEND_CHECKED
    if _BACKEND_CHECKED:
        return _BACKEND

    _BACKEND_CHECKED = True

    # Try Vertex AI first (enterprise)
    if settings.VERTEX_PROJECT_ID:
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
            _BACKEND = "vertex"
            return _BACKEND
        except ImportError:
            logger.warning(
                "google-cloud-aiplatform not installed — falling back to consumer Gemini API"
            )
        except Exception as exc:
            logger.warning("Vertex AI init failed: %s — falling back to consumer API", exc)

    # Fall back to consumer Gemini API
    if settings.GEMINI_API_KEY:
        try:
            import google.generativeai as genai  # type: ignore[import-untyped]
            genai.configure(api_key=settings.GEMINI_API_KEY)
            logger.warning(
                "Using consumer Gemini API — NOT suitable for production with privileged data. "
                "Set VERTEX_PROJECT_ID for enterprise compliance."
            )
            _BACKEND = "consumer"
        except ImportError:
            logger.error("google-generativeai package not installed — AI features disabled")
        except Exception as exc:
            logger.error("Consumer Gemini init failed: %s", exc)
    else:
        _BACKEND = None

    return _BACKEND


def get_generative_model(model_name: str) -> Any:
    """
    Return a GenerativeModel for the given model name.

    Uses Vertex AI when available, otherwise falls back to consumer SDK.
    Both SDKs expose a compatible ``GenerativeModel`` interface for
    ``generate_content()``.

    Raises:
        RuntimeError: If neither backend is available.
    """
    backend = get_backend()

    if backend == "vertex":
        from vertexai.generative_models import GenerativeModel  # type: ignore[import-untyped]
        return GenerativeModel(model_name)

    if backend == "consumer":
        import google.generativeai as genai  # type: ignore[import-untyped]
        return genai.GenerativeModel(model_name)

    raise RuntimeError(
        "No AI backend available. Set VERTEX_PROJECT_ID for Vertex AI "
        "or GEMINI_API_KEY for the consumer Gemini API."
    )


def is_available() -> bool:
    """Return True if at least one AI backend is usable."""
    return get_backend() is not None
