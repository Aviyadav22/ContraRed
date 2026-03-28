"""
AI Backend Client — Vertex AI ONLY via google-genai SDK.

Consumer Gemini API is PROHIBITED — contract data must not transit public
Google AI endpoints. All AI calls go through Vertex AI with project-level
IAM, audit logging, and data residency guarantees.

Uses the lightweight google-genai SDK (no heavy grpc/protobuf) with
vertexai=True mode for enterprise compliance.

Requires:
  - VERTEX_PROJECT_ID set in environment
  - google-genai installed
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

_CLIENT: Optional[Any] = None
_INITIALIZED: bool = False


def _setup_credentials() -> None:
    """Handle GOOGLE_APPLICATION_CREDENTIALS containing raw JSON.

    On PaaS platforms like Render, the service account JSON is pasted
    directly into an env var. The Google SDK expects a *file path*, so
    we write the JSON to a temp file and update the env var to point to it.
    """
    creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if not creds:
        return

    # Already a file path — nothing to do
    if not creds.strip().startswith("{"):
        return

    # It's raw JSON — validate, parse, and write to a temp file.
    # We parse and re-serialize to ensure proper encoding (newlines in
    # private_key may be mangled by PaaS env var handling).
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
            # Re-serialize the parsed dict to ensure clean JSON with proper escaping
            json.dump(creds_dict, f)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path
        logger.info("Wrote GCP service account credentials to temp file")
    except Exception as exc:
        logger.error("Failed to write credentials temp file: %s", exc)
        try:
            os.close(fd)
        except OSError:
            pass


def _get_client() -> Any:
    """Get or create the google-genai Client in Vertex AI mode."""
    global _CLIENT, _INITIALIZED

    if _CLIENT is not None:
        return _CLIENT

    if _INITIALIZED:
        return None  # Already tried and failed

    _INITIALIZED = True

    if not settings.VERTEX_PROJECT_ID:
        logger.error(
            "VERTEX_PROJECT_ID is not set. AI features are disabled. "
            "Consumer Gemini API is prohibited for contract data."
        )
        return None

    # Handle raw JSON credentials from PaaS env vars
    _setup_credentials()

    try:
        from google import genai

        _CLIENT = genai.Client(
            vertexai=True,
            project=settings.VERTEX_PROJECT_ID,
            location=settings.VERTEX_LOCATION,
        )
        logger.info(
            "Vertex AI client ready (project=%s, location=%s, sdk=google-genai)",
            settings.VERTEX_PROJECT_ID,
            settings.VERTEX_LOCATION,
        )
        return _CLIENT
    except ImportError:
        logger.error(
            "google-genai is not installed. "
            "Run: pip install google-genai"
        )
        return None
    except Exception as exc:
        logger.error("Vertex AI client init failed: %s", exc)
        return None


def get_backend() -> Optional[str]:
    """Return 'vertex' if Vertex AI is available, else None."""
    if _get_client() is not None:
        return "vertex"
    return None


def get_generative_model(model_name: str) -> Any:
    """
    Return a wrapper that exposes generate_content() via the google-genai Client.

    The wrapper mimics the old GenerativeModel interface so that
    gemini_analyzer.py doesn't need changes.

    Raises:
        RuntimeError: If Vertex AI is not configured or available.
    """
    client = _get_client()
    if client is None:
        raise RuntimeError(
            "Vertex AI is not available. Set VERTEX_PROJECT_ID and ensure "
            "google-genai is installed with valid credentials. "
            "Consumer Gemini API is prohibited for contract data."
        )

    return _GenaiModelWrapper(client, model_name)


class _GenaiModelWrapper:
    """Wraps google-genai Client to match the old GenerativeModel interface.

    gemini_analyzer.py calls model.generate_content(prompt, generation_config=...)
    and expects .text on the response. This wrapper translates those calls.
    """

    def __init__(self, client: Any, model_name: str):
        self._client = client
        self._model_name = model_name
        self.model_name = model_name  # public attribute for logging

    def generate_content(self, contents, *, generation_config=None, **kwargs):
        """Call the google-genai API and return a compatible response."""
        from google.genai.types import GenerateContentConfig

        config_kwargs = {}
        if generation_config:
            # Handle both dict and object-style generation_config
            if isinstance(generation_config, dict):
                gc = generation_config
            else:
                gc = generation_config.__dict__ if hasattr(generation_config, '__dict__') else {}

            if "temperature" in gc:
                config_kwargs["temperature"] = gc["temperature"]
            if "max_output_tokens" in gc:
                config_kwargs["max_output_tokens"] = gc["max_output_tokens"]
            if "response_mime_type" in gc:
                config_kwargs["response_mime_type"] = gc["response_mime_type"]
            if "top_p" in gc:
                config_kwargs["top_p"] = gc["top_p"]
            if "top_k" in gc:
                config_kwargs["top_k"] = gc["top_k"]

        config = GenerateContentConfig(**config_kwargs) if config_kwargs else None

        response = self._client.models.generate_content(
            model=self._model_name,
            contents=contents,
            config=config,
        )
        return response

    async def generate_content_async(self, contents, *, generation_config=None, **kwargs):
        """Async version — delegates to the sync client in a thread."""
        import asyncio
        return await asyncio.to_thread(
            self.generate_content, contents, generation_config=generation_config, **kwargs
        )


def is_available() -> bool:
    """Return True if Vertex AI is configured and ready."""
    return _get_client() is not None
