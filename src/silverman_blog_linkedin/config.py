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
ENV_DEPLOYMENT_ENVIRONMENT = "SILVERMAN_DEPLOYMENT_ENVIRONMENT"

# US-097 Google OIDC operator console identity (LAN). Secrets stay on the worker.
ENV_OPERATOR_GOOGLE_AUTH_ENABLED = "SILVERMAN_OPERATOR_GOOGLE_AUTH_ENABLED"
ENV_OPERATOR_GOOGLE_CLIENT_ID = "SILVERMAN_OPERATOR_GOOGLE_CLIENT_ID"
ENV_OPERATOR_GOOGLE_CLIENT_SECRET = "SILVERMAN_OPERATOR_GOOGLE_CLIENT_SECRET"
ENV_OPERATOR_GOOGLE_REDIRECT_URI = "SILVERMAN_OPERATOR_GOOGLE_REDIRECT_URI"
ENV_OPERATOR_SESSION_SECRET = "SILVERMAN_OPERATOR_SESSION_SECRET"
ENV_OPERATOR_UI_SUCCESS_REDIRECT = "SILVERMAN_OPERATOR_UI_SUCCESS_REDIRECT"

# Closed vocabulary for UI↔API pairing (US-094). No lan/dev tokens.
DEPLOYMENT_ENVIRONMENTS = frozenset({"uat", "prod"})


class ConfigurationError(ValueError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    base_path: Path
    api_key: str
    port: int
    # Comma-separated absolute UI origins for CORS (US-093). Empty = no CORS wildcard.
    operator_ui_origins: tuple[str, ...] = ()
    # Non-secret stack identity for separated UI pairing (US-094). None when unset.
    deployment_environment: str | None = None
    # US-097 Google OIDC (disabled by default).
    operator_google_auth_enabled: bool = False
    operator_google_client_id: str = ""
    operator_google_client_secret: str = ""
    operator_google_redirect_uri: str = ""
    operator_session_secret: str = ""
    operator_ui_success_redirect: str = ""

    @property
    def operator_google_auth_configured(self) -> bool:
        """True when enablement flag is on and all required Google/session env is set."""
        if not self.operator_google_auth_enabled:
            return False
        return bool(
            self.operator_google_client_id
            and self.operator_google_client_secret
            and self.operator_google_redirect_uri
            and self.operator_session_secret
            and self.operator_ui_success_redirect
        )


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


def _parse_deployment_environment(raw: str) -> str | None:
    """Parse closed-set deployment environment; empty → unset; invalid → fail closed."""
    value = raw.strip().lower()
    if not value:
        return None
    if value not in DEPLOYMENT_ENVIRONMENTS:
        allowed = ", ".join(sorted(DEPLOYMENT_ENVIRONMENTS))
        raise ConfigurationError(
            f"{ENV_DEPLOYMENT_ENVIRONMENT} must be one of {{{allowed}}} "
            f"(case-insensitive); got {raw.strip()!r}"
        )
    return value


def _parse_bool_flag(raw: str, env_name: str) -> bool:
    value = raw.strip().lower()
    if not value or value in {"0", "false", "no", "off"}:
        return False
    if value in {"1", "true", "yes", "on"}:
        return True
    raise ConfigurationError(
        f"{env_name} must be a boolean (true/false); got {raw.strip()!r}"
    )


def _parse_absolute_http_url(raw: str, env_name: str) -> str:
    value = raw.strip()
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigurationError(
            f"{env_name} must be an absolute http(s) URL; got {raw.strip()!r}"
        )
    return value


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
    deployment_environment = _parse_deployment_environment(
        env.get(ENV_DEPLOYMENT_ENVIRONMENT, "")
    )

    google_enabled = _parse_bool_flag(
        env.get(ENV_OPERATOR_GOOGLE_AUTH_ENABLED, ""),
        ENV_OPERATOR_GOOGLE_AUTH_ENABLED,
    )
    google_client_id = env.get(ENV_OPERATOR_GOOGLE_CLIENT_ID, "").strip()
    google_client_secret = env.get(ENV_OPERATOR_GOOGLE_CLIENT_SECRET, "").strip()
    google_redirect_uri = _parse_absolute_http_url(
        env.get(ENV_OPERATOR_GOOGLE_REDIRECT_URI, ""),
        ENV_OPERATOR_GOOGLE_REDIRECT_URI,
    )
    session_secret = env.get(ENV_OPERATOR_SESSION_SECRET, "").strip()
    ui_success_redirect = _parse_absolute_http_url(
        env.get(ENV_OPERATOR_UI_SUCCESS_REDIRECT, ""),
        ENV_OPERATOR_UI_SUCCESS_REDIRECT,
    )
    # When enabled but incomplete, worker still loads; OIDC start/callback and UI
    # status fail closed with clear messaging (US-097). Do not open anonymous console.

    return Settings(
        base_path=base_path,
        api_key=api_key,
        port=port,
        operator_ui_origins=operator_ui_origins,
        deployment_environment=deployment_environment,
        operator_google_auth_enabled=google_enabled,
        operator_google_client_id=google_client_id,
        operator_google_client_secret=google_client_secret,
        operator_google_redirect_uri=google_redirect_uri,
        operator_session_secret=session_secret,
        operator_ui_success_redirect=ui_success_redirect,
    )
