"""Tests for DeepSeek configuration loading."""

import pytest

from silverman_blog_linkedin.config import load_settings
from silverman_blog_linkedin.deepseek_config import (
    DEFAULT_BASE_URL,
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
    load_deepseek_settings,
)
from silverman_blog_linkedin.main import create_app
from fastapi.testclient import TestClient

from tests.conftest import create_full_layout, make_settings


def test_default_deepseek_settings():
    result = load_deepseek_settings({})

    assert result.config_invalid is False
    assert result.settings is not None
    assert result.settings.base_url == DEFAULT_BASE_URL
    assert result.settings.model == DEFAULT_MODEL
    assert result.settings.timeout_seconds == DEFAULT_TIMEOUT_SECONDS
    assert result.settings.max_output_tokens == DEFAULT_MAX_OUTPUT_TOKENS
    assert result.settings.is_configured is False


def test_deepseek_settings_with_api_key():
    result = load_deepseek_settings({"DEEPSEEK_API_KEY": "sk-test"})

    assert result.settings is not None
    assert result.settings.is_configured is True
    assert result.settings.api_key == "sk-test"


def test_deepseek_settings_custom_values():
    env = {
        "DEEPSEEK_BASE_URL": "https://gateway.example.com/v1",
        "DEEPSEEK_MODEL": "custom-model",
        "DEEPSEEK_TIMEOUT_SECONDS": "30.5",
        "DEEPSEEK_MAX_OUTPUT_TOKENS": "2048",
    }
    result = load_deepseek_settings(env)

    assert result.config_invalid is False
    assert result.settings is not None
    assert result.settings.base_url == "https://gateway.example.com/v1"
    assert result.settings.model == "custom-model"
    assert result.settings.timeout_seconds == 30.5
    assert result.settings.max_output_tokens == 2048


@pytest.mark.parametrize(
    "timeout_value",
    ["0", "-1", "abc", ""],
)
def test_invalid_timeout_returns_config_invalid(timeout_value):
    result = load_deepseek_settings({"DEEPSEEK_TIMEOUT_SECONDS": timeout_value})

    assert result.config_invalid is True
    assert result.settings is None


@pytest.mark.parametrize(
    "max_tokens_value",
    ["0", "-5", "1.5", "abc"],
)
def test_invalid_max_output_tokens_returns_config_invalid(max_tokens_value):
    result = load_deepseek_settings(
        {"DEEPSEEK_MAX_OUTPUT_TOKENS": max_tokens_value}
    )

    assert result.config_invalid is True
    assert result.settings is None


def test_worker_starts_with_invalid_deepseek_timeout(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_TIMEOUT_SECONDS", "not-a-number")
    base = tmp_path / "editorial"
    create_full_layout(base)

    client = TestClient(create_app(make_settings(base)))
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] in ("healthy", "degraded")


def test_load_settings_unchanged_without_deepseek(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    settings = load_settings(
        {
            "SILVERMAN_BLOG_LINKEDIN_API_KEY": "test-key",
            "SILVERMAN_BLOG_LINKEDIN_BASE_PATH": str(tmp_path),
        }
    )
    assert settings.api_key == "test-key"
