"""Shared test fixtures and helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from silverman_blog_linkedin.comfyui_config import (
    ENV_API_KEY,
    ENV_API_PREFIX,
    ENV_AUTH_HEADER_NAME,
    ENV_BASE_URL,
    ENV_DRY_RUN,
    ENV_EXTRA_DATA_API_KEY_FIELD,
    ENV_IMAGE_ENABLED,
    ENV_IMAGE_HEIGHT,
    ENV_IMAGE_WIDTH,
    ENV_TIMEOUT_SECONDS,
    ENV_WORKFLOW_PATH,
)
from silverman_blog_linkedin.config import Settings
from silverman_blog_linkedin.paths import EXPECTED_FOLDERS

COMFYUI_ENV_VARS: tuple[str, ...] = (
    ENV_IMAGE_ENABLED,
    ENV_BASE_URL,
    ENV_API_PREFIX,
    ENV_API_KEY,
    ENV_AUTH_HEADER_NAME,
    ENV_EXTRA_DATA_API_KEY_FIELD,
    ENV_WORKFLOW_PATH,
    ENV_TIMEOUT_SECONDS,
    ENV_IMAGE_WIDTH,
    ENV_IMAGE_HEIGHT,
    ENV_DRY_RUN,
)


def clear_comfyui_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove ComfyUI env vars so tests do not inherit the operator shell."""
    for name in COMFYUI_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def isolate_comfyui_env(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_comfyui_env(monkeypatch)


def create_full_layout(base: Path) -> None:
    base.mkdir(parents=True, exist_ok=True)
    for relative in EXPECTED_FOLDERS:
        (base / relative).mkdir(parents=True, exist_ok=True)


def make_settings(base: Path, api_key: str = "test-secret-key") -> Settings:
    return Settings(base_path=base.resolve(), api_key=api_key, port=8000)


def auth_header(api_key: str = "test-secret-key") -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}
