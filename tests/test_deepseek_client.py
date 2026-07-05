"""Tests for DeepSeek chat completions client."""

import json
from unittest.mock import MagicMock

import httpx
import pytest

from silverman_blog_linkedin.deepseek_client import (
    DeepSeekGenerationResult,
    build_chat_completions_url,
    generate_linkedin_draft_content,
)
from silverman_blog_linkedin.deepseek_config import DeepSeekSettings


def _settings(**overrides) -> DeepSeekSettings:
    defaults = {
        "api_key": "sk-secret-key",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-v4-flash",
        "timeout_seconds": 60.0,
        "max_output_tokens": 1024,
    }
    defaults.update(overrides)
    return DeepSeekSettings(**defaults)


def test_build_chat_completions_url_default():
    assert (
        build_chat_completions_url("https://api.deepseek.com")
        == "https://api.deepseek.com/chat/completions"
    )


def test_build_chat_completions_url_strips_trailing_slash():
    assert (
        build_chat_completions_url("https://api.deepseek.com/")
        == "https://api.deepseek.com/chat/completions"
    )


def test_build_chat_completions_url_custom_gateway_prefix():
    assert (
        build_chat_completions_url("https://gateway.example.com/v1")
        == "https://gateway.example.com/v1/chat/completions"
    )


def test_build_chat_completions_url_no_automatic_v1():
    url = build_chat_completions_url("https://api.deepseek.com")
    assert "/v1/" not in url
    assert url.endswith("/chat/completions")


def _mock_response(status_code: int, json_body: dict | None = None) -> httpx.Response:
    content = json.dumps(json_body or {}).encode("utf-8")
    request = httpx.Request("POST", "https://api.deepseek.com/chat/completions")
    return httpx.Response(status_code, content=content, request=request)


def test_successful_content_extraction():
    settings = _settings()
    messages = [{"role": "user", "content": "hello"}]
    response = _mock_response(
        200,
        {"choices": [{"message": {"content": "  Draft text here.  "}}]},
    )
    mock_client = MagicMock()
    mock_client.post.return_value = response

    result = generate_linkedin_draft_content(
        settings, messages, client=mock_client
    )

    assert result == DeepSeekGenerationResult(
        content="Draft text here.", error_code=None
    )
    call_kwargs = mock_client.post.call_args
    assert call_kwargs[0][0] == "https://api.deepseek.com/chat/completions"
    posted = call_kwargs[1]["json"]
    assert posted["model"] == "deepseek-v4-flash"
    assert posted["max_tokens"] == 1024
    assert posted["temperature"] == 0.7
    assert posted["messages"] == messages
    assert call_kwargs[1]["headers"]["Authorization"] == "Bearer sk-secret-key"
    assert "sk-secret-key" not in str(result)


@pytest.mark.parametrize(
    "status_code,expected_error",
    [
        (401, "deepseek_auth_failed"),
        (403, "deepseek_auth_failed"),
        (402, "deepseek_insufficient_balance"),
        (422, "deepseek_invalid_request"),
        (429, "deepseek_rate_limited"),
        (500, "deepseek_unavailable"),
        (503, "deepseek_unavailable"),
        (404, "deepseek_unavailable"),
    ],
)
def test_http_status_error_mapping(status_code, expected_error):
    settings = _settings()
    mock_client = MagicMock()
    mock_client.post.return_value = _mock_response(status_code)

    result = generate_linkedin_draft_content(
        settings, [{"role": "user", "content": "x"}], client=mock_client
    )

    assert result.content is None
    assert result.error_code == expected_error


def test_empty_content_returns_deepseek_empty_response():
    settings = _settings()
    mock_client = MagicMock()
    mock_client.post.return_value = _mock_response(
        200, {"choices": [{"message": {"content": "   "}}]}
    )

    result = generate_linkedin_draft_content(
        settings, [{"role": "user", "content": "x"}], client=mock_client
    )

    assert result.error_code == "deepseek_empty_response"


def test_missing_choices_returns_empty_response():
    settings = _settings()
    mock_client = MagicMock()
    mock_client.post.return_value = _mock_response(200, {"choices": []})

    result = generate_linkedin_draft_content(
        settings, [{"role": "user", "content": "x"}], client=mock_client
    )

    assert result.error_code == "deepseek_empty_response"


def test_timeout_returns_deepseek_timeout():
    settings = _settings()
    mock_client = MagicMock()
    mock_client.post.side_effect = httpx.TimeoutException("timed out")

    result = generate_linkedin_draft_content(
        settings, [{"role": "user", "content": "x"}], client=mock_client
    )

    assert result.error_code == "deepseek_timeout"


def test_network_error_returns_deepseek_unavailable():
    settings = _settings()
    mock_client = MagicMock()
    mock_client.post.side_effect = httpx.ConnectError("connection failed")

    result = generate_linkedin_draft_content(
        settings, [{"role": "user", "content": "x"}], client=mock_client
    )

    assert result.error_code == "deepseek_unavailable"


def test_invalid_json_returns_deepseek_unavailable():
    settings = _settings()
    request = httpx.Request("POST", "https://api.deepseek.com/chat/completions")
    response = httpx.Response(200, content=b"not-json", request=request)
    mock_client = MagicMock()
    mock_client.post.return_value = response

    result = generate_linkedin_draft_content(
        settings, [{"role": "user", "content": "x"}], client=mock_client
    )

    assert result.error_code == "deepseek_unavailable"


def test_custom_base_url_used_in_request():
    settings = _settings(base_url="https://gateway.example.com/v1/")
    mock_client = MagicMock()
    mock_client.post.return_value = _mock_response(
        200, {"choices": [{"message": {"content": "ok"}}]}
    )

    generate_linkedin_draft_content(
        settings, [{"role": "user", "content": "x"}], client=mock_client
    )

    assert mock_client.post.call_args[0][0] == (
        "https://gateway.example.com/v1/chat/completions"
    )


def test_no_api_key_in_result_or_exception():
    settings = _settings(api_key="super-secret-key")
    mock_client = MagicMock()
    mock_client.post.return_value = _mock_response(500)

    result = generate_linkedin_draft_content(
        settings, [{"role": "user", "content": "x"}], client=mock_client
    )

    assert "super-secret-key" not in repr(result)
    assert "super-secret-key" not in str(result.error_code)
