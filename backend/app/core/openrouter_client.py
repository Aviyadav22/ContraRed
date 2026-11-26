"""
OpenRouter backend for the AI wrapper in vertex_client.

Selected with AI_PROVIDER=openrouter. Mirrors _GenaiModelWrapper so the
analysis pipeline and agents don't change: generate_content() takes the same
contents/generation_config and returns an object with .text,
.candidates[0].content.parts[0].text, finish_reason and usage_metadata.

Unlike Vertex AI there is no data-residency guarantee. OPENROUTER_DATA_COLLECTION
defaults to "deny", which skips providers that store or train on prompts;
many free models are only reachable with "allow".
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 4
_HTTP: Optional[httpx.Client] = None
_HTTP_LOCK = threading.Lock()


@dataclass
class _Part:
    text: str


@dataclass
class _Content:
    parts: List[_Part]
    role: str = "model"


@dataclass
class _Candidate:
    content: _Content
    finish_reason: Optional[str] = None


@dataclass
class _Usage:
    prompt_token_count: Optional[int] = None
    candidates_token_count: Optional[int] = None
    total_token_count: Optional[int] = None


@dataclass
class OpenRouterResponse:
    """Shaped like a google-genai GenerateContentResponse for our callers."""

    text: str
    candidates: List[_Candidate] = field(default_factory=list)
    usage_metadata: Optional[_Usage] = None


def is_configured() -> bool:
    return bool(settings.OPENROUTER_API_KEY)


def parse_model_list(value: str) -> List[str]:
    return [m.strip() for m in value.split(",") if m.strip()]


def _http() -> httpx.Client:
    global _HTTP
    with _HTTP_LOCK:
        if _HTTP is None:
            _HTTP = httpx.Client(
                base_url=settings.OPENROUTER_BASE_URL,
                # Full-contract analysis can take minutes on free models.
                timeout=httpx.Timeout(300.0, connect=15.0),
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "HTTP-Referer": "https://contrared.neetiq.in",
                    "X-Title": "ContraRed",
                },
            )
        return _HTTP


def _to_messages(contents: Any) -> List[dict]:
    """Convert google-genai style contents into chat messages."""
    if isinstance(contents, str):
        return [{"role": "user", "content": contents}]
    messages = []
    for item in contents if isinstance(contents, (list, tuple)) else [contents]:
        if isinstance(item, str):
            messages.append({"role": "user", "content": item})
        elif isinstance(item, dict):
            role = "assistant" if item.get("role") == "model" else item.get("role", "user")
            text = "".join(
                p.get("text", "") if isinstance(p, dict) else getattr(p, "text", "") or ""
                for p in item.get("parts", [])
            )
            messages.append({"role": role, "content": text})
        else:
            messages.append({"role": "user", "content": getattr(item, "text", "") or str(item)})
    return messages


def _config_dict(generation_config: Any) -> dict:
    if not generation_config:
        return {}
    if isinstance(generation_config, dict):
        return generation_config
    return {k: v for k, v in vars(generation_config).items() if v is not None}


def _retry_delay(response: Optional[httpx.Response], attempt: int) -> float:
    if response is not None:
        retry_after = response.headers.get("retry-after")
        if retry_after and retry_after.isdigit():
            return min(float(retry_after), 60.0)
    return min(4.0 * (2 ** (attempt - 1)), 60.0)  # 4s, 8s, 16s


class OpenRouterModel:
    """Drop-in for _GenaiModelWrapper backed by OpenRouter chat completions."""

    def __init__(self, models: List[str]):
        if not models:
            raise RuntimeError("OPENROUTER_MODEL must name at least one model.")
        self._models = models
        self.model_name = models[0]  # public attribute for logging

    def _body(self, contents: Any, generation_config: Any) -> dict:
        gc = _config_dict(generation_config)
        body: dict = {
            "model": self._models[0],
            "messages": _to_messages(contents),
            "provider": {"data_collection": settings.OPENROUTER_DATA_COLLECTION},
        }
        if len(self._models) > 1:
            body["models"] = self._models
        for ours, theirs in (("temperature", "temperature"), ("top_p", "top_p"),
                             ("top_k", "top_k"), ("max_output_tokens", "max_tokens")):
            if gc.get(ours) is not None:
                body[theirs] = gc[ours]
        if gc.get("response_mime_type") == "application/json":
            body["response_format"] = {"type": "json_object"}
        return body

    def _post(self, body: dict) -> dict:
        last_exc: Optional[BaseException] = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            response = None
            try:
                response = _http().post("/chat/completions", json=body)
                try:
                    data = response.json() if response.content else {}
                except ValueError:
                    data = {"error": response.text[:300]}
                error = data.get("error") if isinstance(data, dict) else None
                status = response.status_code
                if error and status == 200:
                    # Upstream failures sometimes come back as 200 with an error body.
                    code = error.get("code") if isinstance(error, dict) else None
                    status = code if isinstance(code, int) else 502
                reset_ms = response.headers.get("x-ratelimit-reset", "")
                if status == 429 and reset_ms.isdigit() and int(reset_ms) / 1000 - time.time() > 60:
                    # The free daily cap; it resets at midnight UTC, so don't retry.
                    resets = time.strftime("%H:%M UTC", time.gmtime(int(reset_ms) / 1000))
                    raise RuntimeError(f"OpenRouter daily request limit reached; resets at {resets}")
                if status == 429 or status >= 500:
                    raise httpx.HTTPStatusError(f"OpenRouter {status}: {error}", request=response.request, response=response)
                if status >= 400:
                    raise RuntimeError(f"OpenRouter request failed ({status}): {error or response.text[:300]}")
                return data
            except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                last_exc = exc
                if attempt < _MAX_ATTEMPTS:
                    delay = _retry_delay(response, attempt)
                    logger.warning("OpenRouter attempt %d/%d failed (%s) — retrying in %.0fs",
                                   attempt, _MAX_ATTEMPTS, exc, delay)
                    time.sleep(delay)
        assert last_exc is not None
        raise last_exc

    def generate_content(self, contents, *, generation_config=None, **kwargs) -> OpenRouterResponse:
        data = self._post(self._body(contents, generation_config))
        choice = (data.get("choices") or [{}])[0]
        text = (choice.get("message") or {}).get("content") or ""
        usage = data.get("usage") or {}
        if data.get("model"):
            logger.debug("OpenRouter served by %s", data["model"])
        return OpenRouterResponse(
            text=text,
            candidates=[_Candidate(_Content([_Part(text)]), choice.get("finish_reason"))],
            usage_metadata=_Usage(usage.get("prompt_tokens"), usage.get("completion_tokens"),
                                  usage.get("total_tokens")),
        )

    async def generate_content_async(self, contents, *, generation_config=None, **kwargs):
        import asyncio
        return await asyncio.to_thread(
            self.generate_content, contents, generation_config=generation_config, **kwargs
        )


def get_model(gemini_model_name: str) -> OpenRouterModel:
    """Map the Gemini model a caller asked for onto the OpenRouter model lists."""
    if gemini_model_name == settings.GEMINI_SCOUT_MODEL:
        return OpenRouterModel(parse_model_list(settings.OPENROUTER_FAST_MODEL))
    return OpenRouterModel(parse_model_list(settings.OPENROUTER_MODEL))
