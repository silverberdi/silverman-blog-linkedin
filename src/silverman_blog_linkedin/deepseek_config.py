"""Lazy DeepSeek configuration loaded at request time (not worker startup)."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_MAX_OUTPUT_TOKENS = 1024

ENV_API_KEY = "DEEPSEEK_API_KEY"
ENV_BASE_URL = "DEEPSEEK_BASE_URL"
ENV_MODEL = "DEEPSEEK_MODEL"
ENV_TIMEOUT_SECONDS = "DEEPSEEK_TIMEOUT_SECONDS"
ENV_MAX_OUTPUT_TOKENS = "DEEPSEEK_MAX_OUTPUT_TOKENS"


@dataclass(frozen=True)
class DeepSeekSettings:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: float
    max_output_tokens: int

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key.strip())

    @property
    def chat_completions_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/chat/completions"


@dataclass(frozen=True)
class DeepSeekSettingsLoadResult:
    settings: DeepSeekSettings | None
    config_invalid: bool


def _parse_positive_number(raw: str) -> float | None:
    try:
        value = float(raw)
    except ValueError:
        return None
    if value <= 0:
        return None
    return value


def _parse_positive_int(raw: str) -> int | None:
    try:
        value = int(raw)
    except ValueError:
        return None
    if value <= 0:
        return None
    return value


def load_deepseek_settings(
    environ: dict[str, str] | None = None,
) -> DeepSeekSettingsLoadResult:
    """Load DeepSeek settings from environment; validate optional numeric fields."""
    env = os.environ if environ is None else environ

    base_url = env.get(ENV_BASE_URL, DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL
    model = env.get(ENV_MODEL, DEFAULT_MODEL).strip() or DEFAULT_MODEL
    api_key = env.get(ENV_API_KEY, "").strip()

    raw_timeout = env.get(ENV_TIMEOUT_SECONDS, str(DEFAULT_TIMEOUT_SECONDS)).strip()
    timeout_seconds = _parse_positive_number(raw_timeout)
    if timeout_seconds is None:
        return DeepSeekSettingsLoadResult(settings=None, config_invalid=True)

    raw_max_tokens = env.get(
        ENV_MAX_OUTPUT_TOKENS, str(DEFAULT_MAX_OUTPUT_TOKENS)
    ).strip()
    max_output_tokens = _parse_positive_int(raw_max_tokens)
    if max_output_tokens is None:
        return DeepSeekSettingsLoadResult(settings=None, config_invalid=True)

    return DeepSeekSettingsLoadResult(
        settings=DeepSeekSettings(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
        ),
        config_invalid=False,
    )
