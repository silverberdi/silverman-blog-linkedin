"""LinkedIn publication configuration loaded at request time."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_API_VERSION = "202606"
DEFAULT_SAFETY_DELAY_MINUTES = 120

ENV_ACCESS_TOKEN = "SILVERMAN_LINKEDIN_ACCESS_TOKEN"
ENV_MEMBER_URN = "SILVERMAN_LINKEDIN_MEMBER_URN"
ENV_PUBLICATION_ENABLED = "SILVERMAN_LINKEDIN_PUBLICATION_ENABLED"
ENV_DEFAULT_SAFETY_DELAY_MINUTES = "SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES"
ENV_API_VERSION = "SILVERMAN_LINKEDIN_API_VERSION"


@dataclass(frozen=True)
class LinkedInPublicationSettings:
    access_token: str
    member_urn: str
    publication_enabled: bool
    default_safety_delay_minutes: int
    api_version: str

    @property
    def has_access_token(self) -> bool:
        return bool(self.access_token.strip())

    @property
    def has_member_urn(self) -> bool:
        return bool(self.member_urn.strip())

    @property
    def real_publish_ready(self) -> bool:
        return (
            self.publication_enabled
            and self.has_access_token
            and self.has_member_urn
        )


@dataclass(frozen=True)
class LinkedInPublicationSettingsLoadResult:
    settings: LinkedInPublicationSettings
    config_invalid: bool


def _parse_non_negative_int(raw: str) -> int | None:
    try:
        value = int(raw)
    except ValueError:
        return None
    if value < 0:
        return None
    return value


def _parse_bool(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_linkedin_publication_settings(
    environ: dict[str, str] | None = None,
) -> LinkedInPublicationSettingsLoadResult:
    """Load LinkedIn publication settings from environment."""
    env = os.environ if environ is None else environ

    access_token = env.get(ENV_ACCESS_TOKEN, "").strip()
    member_urn = env.get(ENV_MEMBER_URN, "").strip()
    publication_enabled = _parse_bool(env.get(ENV_PUBLICATION_ENABLED, ""))
    api_version = env.get(ENV_API_VERSION, DEFAULT_API_VERSION).strip() or DEFAULT_API_VERSION

    raw_delay = env.get(
        ENV_DEFAULT_SAFETY_DELAY_MINUTES, str(DEFAULT_SAFETY_DELAY_MINUTES)
    ).strip()
    default_safety_delay_minutes = _parse_non_negative_int(raw_delay)
    if default_safety_delay_minutes is None:
        return LinkedInPublicationSettingsLoadResult(
            settings=LinkedInPublicationSettings(
                access_token=access_token,
                member_urn=member_urn,
                publication_enabled=publication_enabled,
                default_safety_delay_minutes=DEFAULT_SAFETY_DELAY_MINUTES,
                api_version=api_version,
            ),
            config_invalid=True,
        )

    return LinkedInPublicationSettingsLoadResult(
        settings=LinkedInPublicationSettings(
            access_token=access_token,
            member_urn=member_urn,
            publication_enabled=publication_enabled,
            default_safety_delay_minutes=default_safety_delay_minutes,
            api_version=api_version,
        ),
        config_invalid=False,
    )
