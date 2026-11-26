"""Tests for the OpenRouter backend behind vertex_client.get_generative_model."""

import json

import httpx
import pytest

from app.core import openrouter_client, vertex_client
from app.core.config import settings


@pytest.fixture
def openrouter(monkeypatch):
    """Select OpenRouter and capture outgoing requests; `replies` feeds responses."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "openrouter")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(settings, "OPENROUTER_MODEL", "big:free,backup:free")
    monkeypatch.setattr(settings, "OPENROUTER_FAST_MODEL", "small:free")
    monkeypatch.setattr(openrouter_client.time, "sleep", lambda s: None)

    state = {"replies": [], "bodies": []}

    def handler(request: httpx.Request) -> httpx.Response:
        state["bodies"].append(json.loads(request.content))
        return state["replies"].pop(0)

    monkeypatch.setattr(
        openrouter_client, "_HTTP",
        httpx.Client(base_url="https://openrouter.test/api/v1", transport=httpx.MockTransport(handler)),
    )
    return state


def _chat(text, finish="stop"):
    return httpx.Response(200, json={
        "model": "big:free",
        "choices": [{"message": {"content": text}, "finish_reason": finish}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 3, "total_tokens": 14},
    })


def test_backend_selection_and_model_mapping(openrouter):
    assert vertex_client.is_available() is True
    assert vertex_client.get_backend() == "openrouter"
    assert vertex_client.get_generative_model(settings.GEMINI_ANALYSIS_MODEL).model_name == "big:free"
    assert vertex_client.get_generative_model(settings.GEMINI_SCOUT_MODEL).model_name == "small:free"


def test_not_available_without_key(monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "openrouter")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "")
    assert vertex_client.is_available() is False
    assert vertex_client.get_backend() is None
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        vertex_client.get_generative_model(settings.GEMINI_MODEL)


def test_response_has_the_shape_callers_read(openrouter):
    openrouter["replies"].append(_chat('{"risks": []}'))
    model = vertex_client.get_generative_model(settings.GEMINI_MODEL)

    response = model.generate_content(
        [{"role": "user", "parts": [{"text": "Find risks"}]}],
        generation_config={"temperature": 0.2, "max_output_tokens": 4096,
                           "response_mime_type": "application/json"},
    )

    assert response.text == '{"risks": []}'
    assert response.candidates[0].content.parts[0].text == '{"risks": []}'
    assert response.candidates[0].finish_reason == "stop"
    assert response.usage_metadata.total_token_count == 14

    body = openrouter["bodies"][0]
    assert body["messages"] == [{"role": "user", "content": "Find risks"}]
    assert body["models"] == ["big:free", "backup:free"]
    assert body["max_tokens"] == 4096
    assert body["temperature"] == 0.2
    assert body["response_format"] == {"type": "json_object"}
    assert body["provider"] == {"data_collection": "deny"}
    assert body["reasoning"] == {"enabled": False}


def test_accepts_genai_config_objects_and_plain_strings(openrouter):
    from google.genai.types import GenerateContentConfig

    openrouter["replies"].append(_chat("ok"))
    model = vertex_client.get_generative_model(settings.GEMINI_SCOUT_MODEL)
    model.generate_content("hello", generation_config=GenerateContentConfig(temperature=0.0, max_output_tokens=50))

    body = openrouter["bodies"][0]
    assert body["messages"] == [{"role": "user", "content": "hello"}]
    assert body["max_tokens"] == 50
    assert "models" not in body  # single-model list


def test_model_role_maps_to_assistant(openrouter):
    openrouter["replies"].append(_chat("ok"))
    model = vertex_client.get_generative_model(settings.GEMINI_MODEL)
    model.generate_content([
        {"role": "user", "parts": [{"text": "a"}]},
        {"role": "model", "parts": [{"text": "b"}, {"text": "c"}]},
    ])
    assert openrouter["bodies"][0]["messages"][1] == {"role": "assistant", "content": "bc"}


def test_retries_rate_limit_and_error_bodies(openrouter):
    openrouter["replies"] += [
        httpx.Response(429, json={"error": {"message": "slow down"}}),
        httpx.Response(200, json={"error": {"code": 502, "message": "upstream"}}),
        httpx.Response(503, text="<html>bad gateway</html>"),
        _chat("finally"),
    ]
    model = vertex_client.get_generative_model(settings.GEMINI_MODEL)
    assert model.generate_content("x").text == "finally"
    assert len(openrouter["bodies"]) == 4


def test_client_errors_are_not_retried(openrouter):
    openrouter["replies"].append(httpx.Response(400, json={"error": {"message": "bad model"}}))
    model = vertex_client.get_generative_model(settings.GEMINI_MODEL)
    with pytest.raises(RuntimeError, match="400"):
        model.generate_content("x")
    assert len(openrouter["bodies"]) == 1


@pytest.mark.asyncio
async def test_async_variant(openrouter):
    openrouter["replies"].append(_chat("async ok"))
    model = vertex_client.get_generative_model(settings.GEMINI_MODEL)
    assert (await model.generate_content_async("x")).text == "async ok"


def test_services_enable_ai_with_openrouter(openrouter):
    from app.services.ai_service import AIService
    from app.services.gemini_analyzer import GeminiAnalyzer

    assert AIService().is_enabled is True
    assert GeminiAnalyzer().is_enabled is True


def test_daily_limit_fails_fast_with_reset_time(openrouter):
    import time

    reset_ms = str(int((time.time() + 5 * 3600) * 1000))
    openrouter["replies"].append(httpx.Response(429, headers={"x-ratelimit-reset": reset_ms},
                                                json={"error": {"message": "free-models-per-day"}}))
    model = vertex_client.get_generative_model(settings.GEMINI_MODEL)
    with pytest.raises(RuntimeError, match="daily request limit reached; resets at"):
        model.generate_content("x")
    assert len(openrouter["bodies"]) == 1
