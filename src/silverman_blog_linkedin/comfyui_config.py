"""ComfyUI blog image generation configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TIMEOUT_SECONDS = 120.0
DEFAULT_IMAGE_WIDTH = 1200
DEFAULT_IMAGE_HEIGHT = 900

ENV_IMAGE_ENABLED = "SILVERMAN_COMFYUI_IMAGE_ENABLED"
ENV_BASE_URL = "SILVERMAN_COMFYUI_BASE_URL"
ENV_API_PREFIX = "SILVERMAN_COMFYUI_API_PREFIX"
ENV_API_KEY = "SILVERMAN_COMFYUI_API_KEY"
ENV_AUTH_HEADER_NAME = "SILVERMAN_COMFYUI_AUTH_HEADER_NAME"
ENV_EXTRA_DATA_API_KEY_FIELD = "SILVERMAN_COMFYUI_EXTRA_DATA_API_KEY_FIELD"
ENV_WORKFLOW_PATH = "SILVERMAN_COMFYUI_WORKFLOW_PATH"
ENV_TIMEOUT_SECONDS = "SILVERMAN_COMFYUI_TIMEOUT_SECONDS"
ENV_IMAGE_WIDTH = "SILVERMAN_COMFYUI_IMAGE_WIDTH"
ENV_IMAGE_HEIGHT = "SILVERMAN_COMFYUI_IMAGE_HEIGHT"
ENV_DRY_RUN = "SILVERMAN_COMFYUI_DRY_RUN"

DEFAULT_AUTH_HEADER_NAME = "Authorization"

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_COMFYUI_PROMPTS_DIR = _REPO_ROOT / "prompts" / "comfyui"
DEFAULT_WORKFLOW_PATH = _COMFYUI_PROMPTS_DIR / "silverman-blog-openai-gpt-image.json"
LOCAL_WORKFLOW_PATH = _COMFYUI_PROMPTS_DIR / "blog-image-workflow.json"


def _parse_bool(raw: str | None, *, default: bool = False) -> bool:
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    return default


def _parse_positive_number(raw: str, default: float) -> float | None:
    try:
        value = float(raw)
    except ValueError:
        return None
    if value <= 0:
        return None
    return value


def _parse_positive_int(raw: str, default: int) -> int | None:
    try:
        value = int(raw)
    except ValueError:
        return None
    if value <= 0:
        return None
    return value


@dataclass(frozen=True)
class ComfyUISettings:
    enabled: bool
    base_url: str | None
    api_prefix: str
    api_key: str | None
    auth_header_name: str
    extra_data_api_key_field: str | None
    workflow_path: Path
    timeout_seconds: float
    image_width: int
    image_height: int
    dry_run: bool

    @property
    def is_configured(self) -> bool:
        return bool(self.enabled and self.base_url and self.base_url.strip())

    @property
    def generation_enabled(self) -> bool:
        """True when ``SILVERMAN_COMFYUI_IMAGE_ENABLED`` is set (``enabled`` field)."""
        return self.enabled


@dataclass(frozen=True)
class ComfyUISettingsLoadResult:
    settings: ComfyUISettings
    config_invalid: bool = False


def _load_cloud_compat_fields(env: dict[str, str]) -> dict[str, str | None]:
    return {
        "api_prefix": env.get(ENV_API_PREFIX, "").strip(),
        "api_key": env.get(ENV_API_KEY, "").strip() or None,
        "auth_header_name": (
            env.get(ENV_AUTH_HEADER_NAME, DEFAULT_AUTH_HEADER_NAME).strip()
            or DEFAULT_AUTH_HEADER_NAME
        ),
        "extra_data_api_key_field": (
            env.get(ENV_EXTRA_DATA_API_KEY_FIELD, "").strip() or None
        ),
    }


def load_comfyui_settings(
    environ: dict[str, str] | None = None,
) -> ComfyUISettingsLoadResult:
    """Load ComfyUI image generation settings from environment."""
    env = os.environ if environ is None else environ

    enabled = _parse_bool(env.get(ENV_IMAGE_ENABLED), default=False)
    dry_run = _parse_bool(env.get(ENV_DRY_RUN), default=False)

    raw_workflow = env.get(ENV_WORKFLOW_PATH, "").strip()
    workflow_path = (
        Path(raw_workflow).expanduser().resolve()
        if raw_workflow
        else DEFAULT_WORKFLOW_PATH
    )

    raw_timeout = env.get(ENV_TIMEOUT_SECONDS, str(DEFAULT_TIMEOUT_SECONDS)).strip()
    timeout_seconds = _parse_positive_number(raw_timeout, DEFAULT_TIMEOUT_SECONDS)
    if timeout_seconds is None:
        cloud = _load_cloud_compat_fields(env)
        return ComfyUISettingsLoadResult(
            settings=ComfyUISettings(
                enabled=enabled,
                base_url=None,
                api_prefix=cloud["api_prefix"],
                api_key=cloud["api_key"],
                auth_header_name=cloud["auth_header_name"],
                extra_data_api_key_field=cloud["extra_data_api_key_field"],
                workflow_path=workflow_path,
                timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
                image_width=DEFAULT_IMAGE_WIDTH,
                image_height=DEFAULT_IMAGE_HEIGHT,
                dry_run=dry_run,
            ),
            config_invalid=True,
        )

    raw_width = env.get(ENV_IMAGE_WIDTH, str(DEFAULT_IMAGE_WIDTH)).strip()
    image_width = _parse_positive_int(raw_width, DEFAULT_IMAGE_WIDTH)
    if image_width is None:
        cloud = _load_cloud_compat_fields(env)
        return ComfyUISettingsLoadResult(
            settings=ComfyUISettings(
                enabled=enabled,
                base_url=None,
                api_prefix=cloud["api_prefix"],
                api_key=cloud["api_key"],
                auth_header_name=cloud["auth_header_name"],
                extra_data_api_key_field=cloud["extra_data_api_key_field"],
                workflow_path=workflow_path,
                timeout_seconds=timeout_seconds,
                image_width=DEFAULT_IMAGE_WIDTH,
                image_height=DEFAULT_IMAGE_HEIGHT,
                dry_run=dry_run,
            ),
            config_invalid=True,
        )

    raw_height = env.get(ENV_IMAGE_HEIGHT, str(DEFAULT_IMAGE_HEIGHT)).strip()
    image_height = _parse_positive_int(raw_height, DEFAULT_IMAGE_HEIGHT)
    if image_height is None:
        cloud = _load_cloud_compat_fields(env)
        return ComfyUISettingsLoadResult(
            settings=ComfyUISettings(
                enabled=enabled,
                base_url=None,
                api_prefix=cloud["api_prefix"],
                api_key=cloud["api_key"],
                auth_header_name=cloud["auth_header_name"],
                extra_data_api_key_field=cloud["extra_data_api_key_field"],
                workflow_path=workflow_path,
                timeout_seconds=timeout_seconds,
                image_width=image_width,
                image_height=DEFAULT_IMAGE_HEIGHT,
                dry_run=dry_run,
            ),
            config_invalid=True,
        )

    cloud = _load_cloud_compat_fields(env)
    base_url = env.get(ENV_BASE_URL, "").strip() or None

    return ComfyUISettingsLoadResult(
        settings=ComfyUISettings(
            enabled=enabled,
            base_url=base_url,
            api_prefix=cloud["api_prefix"],
            api_key=cloud["api_key"],
            auth_header_name=cloud["auth_header_name"],
            extra_data_api_key_field=cloud["extra_data_api_key_field"],
            workflow_path=workflow_path,
            timeout_seconds=timeout_seconds,
            image_width=image_width,
            image_height=image_height,
            dry_run=dry_run,
        ),
        config_invalid=False,
    )
