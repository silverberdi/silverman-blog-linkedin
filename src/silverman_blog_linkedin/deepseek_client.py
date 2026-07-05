"""DeepSeek OpenAI-compatible chat completions client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from silverman_blog_linkedin.deepseek_config import DeepSeekSettings

DEFAULT_TEMPERATURE = 0.7


@dataclass(frozen=True)
class DeepSeekGenerationResult:
    content: str | None
    error_code: str | None


def build_chat_completions_url(base_url: str) -> str:
    """Build chat completions URL from base URL (strip trailing slash, no /v1)."""
    return f"{base_url.rstrip('/')}/chat/completions"


def _map_http_status(status_code: int) -> str:
    if status_code in (401, 403):
        return "deepseek_auth_failed"
    if status_code == 402:
        return "deepseek_insufficient_balance"
    if status_code == 422:
        return "deepseek_invalid_request"
    if status_code == 429:
        return "deepseek_rate_limited"
    if status_code in (500, 503):
        return "deepseek_unavailable"
    return "deepseek_unavailable"


def _extract_message_content(data: dict[str, Any]) -> str | None:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if not isinstance(content, str):
        return None
    return content.strip() or None


def generate_linkedin_draft_content(
    settings: DeepSeekSettings,
    messages: list[dict[str, str]],
    *,
    client: httpx.Client | None = None,
) -> DeepSeekGenerationResult:
    """Call DeepSeek chat completions and return trimmed draft text or error code."""
    url = build_chat_completions_url(settings.base_url)
    payload = {
        "model": settings.model,
        "messages": messages,
        "max_tokens": settings.max_output_tokens,
        "temperature": DEFAULT_TEMPERATURE,
    }
    headers = {
        "Authorization": f"Bearer {settings.api_key}",
        "Content-Type": "application/json",
    }

    owns_client = client is None
    if owns_client:
        client = httpx.Client(timeout=settings.timeout_seconds)

    try:
        response = client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException:
        return DeepSeekGenerationResult(content=None, error_code="deepseek_timeout")
    except httpx.HTTPError:
        return DeepSeekGenerationResult(content=None, error_code="deepseek_unavailable")
    finally:
        if owns_client:
            client.close()

    if response.status_code != 200:
        return DeepSeekGenerationResult(
            content=None,
            error_code=_map_http_status(response.status_code),
        )

    try:
        data = response.json()
    except ValueError:
        return DeepSeekGenerationResult(content=None, error_code="deepseek_unavailable")

    content = _extract_message_content(data)
    if content is None:
        return DeepSeekGenerationResult(
            content=None, error_code="deepseek_empty_response"
        )

    return DeepSeekGenerationResult(content=content, error_code=None)
