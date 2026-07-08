"""LinkedIn OAuth configuration loaded at request time."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_OAUTH_STATE_TTL_SECONDS = 600
DEFAULT_TOKEN_REFRESH_SKEW_SECONDS = 300
OAUTH_SCOPE = "openid profile w_member_social"

ENV_CLIENT_ID = "SILVERMAN_LINKEDIN_CLIENT_ID"
ENV_CLIENT_SECRET = "SILVERMAN_LINKEDIN_CLIENT_SECRET"
ENV_REDIRECT_URI = "SILVERMAN_LINKEDIN_REDIRECT_URI"
ENV_TOKEN_STORE_PATH = "SILVERMAN_LINKEDIN_TOKEN_STORE_PATH"
ENV_OAUTH_STATE_TTL_SECONDS = "SILVERMAN_LINKEDIN_OAUTH_STATE_TTL_SECONDS"
ENV_TOKEN_REFRESH_SKEW_SECONDS = "SILVERMAN_LINKEDIN_TOKEN_REFRESH_SKEW_SECONDS"


@dataclass(frozen=True)
class LinkedInOAuthSettings:
    client_id: str
    client_secret: str
    redirect_uri: str
    token_store_path: str
    state_ttl_seconds: int
    refresh_skew_seconds: int

    @property
    def oauth_configured(self) -> bool:
        return bool(
            self.client_id.strip()
            and self.client_secret.strip()
            and self.redirect_uri.strip()
        )

    @property
    def has_token_store_path(self) -> bool:
        return bool(self.token_store_path.strip())


@dataclass(frozen=True)
class LinkedInOAuthSettingsLoadResult:
    settings: LinkedInOAuthSettings
    config_invalid: bool


def _parse_positive_int(raw: str, default: int) -> int | None:
    stripped = raw.strip()
    if not stripped:
        return default
    try:
        value = int(stripped)
    except ValueError:
        return None
    if value <= 0:
        return None
    return value


def load_linkedin_oauth_settings(
    environ: dict[str, str] | None = None,
) -> LinkedInOAuthSettingsLoadResult:
    """Load LinkedIn OAuth settings from environment."""
    env = os.environ if environ is None else environ

    client_id = env.get(ENV_CLIENT_ID, "").strip()
    client_secret = env.get(ENV_CLIENT_SECRET, "").strip()
    redirect_uri = env.get(ENV_REDIRECT_URI, "").strip()
    token_store_path = env.get(ENV_TOKEN_STORE_PATH, "").strip()

    state_ttl = _parse_positive_int(
        env.get(ENV_OAUTH_STATE_TTL_SECONDS, ""),
        DEFAULT_OAUTH_STATE_TTL_SECONDS,
    )
    refresh_skew = _parse_positive_int(
        env.get(ENV_TOKEN_REFRESH_SKEW_SECONDS, ""),
        DEFAULT_TOKEN_REFRESH_SKEW_SECONDS,
    )
    if state_ttl is None or refresh_skew is None:
        return LinkedInOAuthSettingsLoadResult(
            settings=LinkedInOAuthSettings(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                token_store_path=token_store_path,
                state_ttl_seconds=DEFAULT_OAUTH_STATE_TTL_SECONDS,
                refresh_skew_seconds=DEFAULT_TOKEN_REFRESH_SKEW_SECONDS,
            ),
            config_invalid=True,
        )

    return LinkedInOAuthSettingsLoadResult(
        settings=LinkedInOAuthSettings(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            token_store_path=token_store_path,
            state_ttl_seconds=state_ttl,
            refresh_skew_seconds=refresh_skew,
        ),
        config_invalid=False,
    )
