"""
Vertex AI Client Wrapper — Enterprise-grade AI backend with consumer API fallback.

Uses Google Cloud Vertex AI when VERTEX_PROJECT_ID is set and google-cloud-aiplatform
is installed. Falls back to the consumer google.generativeai SDK otherwise.

NOTE: A Data Processing Agreement (DPA) must be executed with Google Cloud before
sending customer data through Vertex AI in production.  Vertex AI provides
enterprise compliance controls (VPC-SC, CMEK, audit logging) that the consumer
API does not.
"""

import logging
import threading
from typing import Any, Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Sentinel indicating which backend is active
_BACKEND: Optional[str] = None  # "vertex" | "consumer" | None
_init_lock = threading.Lock()


def _try_init_vertex() -> bool:
    """Attempt to initialise the Vertex AI SDK. Returns True on success."""
    if not settings.VERTEX_PROJECT_ID:
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
        return True
    except ImportError:
        logger.warning(
            "google-cloud-aiplatform not installed — falling back to consumer Gemini API. "
            "Install with: pip install google-cloud-aiplatform"
        )
        return False
    except Exception as exc:
        logger.warning("Vertex AI init failed (%s) — falling back to consumer API", exc)
        return False


def _try_init_consumer() -> bool:
    """Attempt to initialise the consumer google.generativeai SDK."""
    if not settings.GEMINI_API_KEY:
        return False
    try:
        import google.generativeai as genai  # type: ignore[import-untyped]
        genai.configure(api_key=settings.GEMINI_API_KEY)
        return True
    except ImportError:
        logger.warning("google-generativeai not installed")
        return False
    except Exception as exc:
        logger.warning("Consumer Gemini init failed: %s", exc)
        return False


def get_backend() -> Optional[str]:
    """Return which backend is active: 'vertex', 'consumer', or None.

    Thread-safe: uses double-checked locking to avoid race conditions
    when multiple threads call this concurrently during startup.

    When REQUIRE_VERTEX_AI is True, refuses to fall back to the consumer
    Gemini API — contract text must only go through Vertex AI (which has
    DPA and enterprise compliance controls).
    """
    global _BACKEND
    if _BACKEND is not None:
        return _BACKEND
    with _init_lock:
        # Double-check after acquiring lock
        if _BACKEND is not None:
            return _BACKEND
        # Lazy first-call initialisation
        if _try_init_vertex():
            _BACKEND = "vertex"
        elif settings.REQUIRE_VERTEX_AI:
            logger.error(
                "REQUIRE_VERTEX_AI is True but Vertex AI init failed. "
                "Refusing to fall back to consumer Gemini API. "
                "Set VERTEX_PROJECT_ID and install google-cloud-aiplatform, "
                "or set REQUIRE_VERTEX_AI=false for development."
            )
            _BACKEND = None
        elif _try_init_consumer():
            logger.warning(
                "Using consumer Gemini API — NOT suitable for production with "
                "privileged data. Set VERTEX_PROJECT_ID for enterprise compliance."
            )
            _BACKEND = "consumer"
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
