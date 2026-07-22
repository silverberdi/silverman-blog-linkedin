"""Environment-based configuration for the worker."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_BASE_PATH = "./data/silverman-blog-linkedin"
DEFAULT_PORT = 8000

ENV_BASE_PATH = "SILVERMAN_BLOG_LINKEDIN_BASE_PATH"
ENV_API_KEY = "SILVERMAN_BLOG_LINKEDIN_API_KEY"
ENV_PORT = "PORT"
ENV_OPERATOR_UI_ORIGINS = "SILVERMAN_OPERATOR_UI_ORIGINS"


class ConfigurationError(ValueError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    base_path: Path
    api_key: str
    port: int
    # Comma-separated absolute UI origins for CORS (US-093). Empty = no CORS wildcard.
    operator_ui_origins: tuple[str, ...] = ()


def _parse_operator_ui_origins(raw: str) -> tuple[str, ...]:
    """Parse comma-separated absolute http(s) origins; skip blanks; reject wildcards."""
    if not raw.strip():
        return ()
    origins: list[str] = []
    for part in raw.split(","):
        origin = part.strip().rstrip("/")
        if not origin:
            continue
        if origin == "*":
            raise ConfigurationError(
                f"{ENV_OPERATOR_UI_ORIGINS} must not use wildcard '*'; "
                "list explicit UI origins (for example http://192.168.0.194:8011)"
            )
        parsed = urlparse(origin)
        if parsed.scheme not in {"http", "https"}:
            raise ConfigurationError(
                f"{ENV_OPERATOR_UI_ORIGINS} entries must be absolute http(s) "
                f"origins, got {origin!r}"
            )
        if not parsed.netloc or parsed.path not in {"", "/"}:
            raise ConfigurationError(
                f"{ENV_OPERATOR_UI_ORIGINS} entries must be absolute origins "
                f"without paths, got {origin!r}"
            )
        # Reconstruct canonical origin (scheme://netloc).
        origins.append(f"{parsed.scheme}://{parsed.netloc}")
    return tuple(origins)


def load_settings(environ: dict[str, str] | None = None) -> Settings:
    """Load and validate settings from environment variables."""
    env = os.environ if environ is None else environ

    raw_base = env.get(ENV_BASE_PATH, DEFAULT_BASE_PATH).strip()
    base_path = Path(raw_base).expanduser().resolve()

    api_key = env.get(ENV_API_KEY, "").strip()
    if not api_key:
        raise ConfigurationError(
            f"{ENV_API_KEY} is required and must not be empty"
        )

    raw_port = env.get(ENV_PORT, str(DEFAULT_PORT)).strip()
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise ConfigurationError(
            f"{ENV_PORT} must be a valid integer, got {raw_port!r}"
        ) from exc

    if port < 1 or port > 65535:
        raise ConfigurationError(
            f"{ENV_PORT} must be between 1 and 65535, got {port}"
        )

    operator_ui_origins = _parse_operator_ui_origins(
        env.get(ENV_OPERATOR_UI_ORIGINS, "")
    )

    return Settings(
        base_path=base_path,
        api_key=api_key,
        port=port,
        operator_ui_origins=operator_ui_origins,
    )
