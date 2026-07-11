"""Live-site confirmation configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

from silverman_blog_linkedin.github_pages_publish import DEFAULT_SITE_URL, ENV_SITE_URL

ENV_CONFIRMATION_ENABLED = "SILVERMAN_BLOG_LIVE_SITE_CONFIRMATION_ENABLED"
ENV_PROBE_TIMEOUT_SECONDS = "SILVERMAN_BLOG_LIVE_SITE_PROBE_TIMEOUT_SECONDS"
ENV_PROBE_MAX_ATTEMPTS = "SILVERMAN_BLOG_LIVE_SITE_PROBE_MAX_ATTEMPTS"
ENV_PROBE_RETRY_DELAY_SECONDS = "SILVERMAN_BLOG_LIVE_SITE_PROBE_RETRY_DELAY_SECONDS"

DEFAULT_PROBE_TIMEOUT_SECONDS = 10
DEFAULT_PROBE_MAX_ATTEMPTS = 5
DEFAULT_PROBE_RETRY_DELAY_SECONDS = 2


@dataclass(frozen=True)
class LiveSiteConfirmationSettings:
    confirmation_enabled: bool
    probe_timeout_seconds: int
    probe_max_attempts: int
    probe_retry_delay_seconds: int
    site_base_url: str
    allowed_host: str


def _parse_bool(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _parse_positive_int(raw: str, default: int) -> int:
    try:
        value = int(raw.strip())
    except ValueError:
        return default
    if value <= 0:
        return default
    return value


def _host_from_site_url(site_url: str) -> str:
    parsed = urlparse(site_url)
    host = parsed.netloc.strip().lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def load_live_site_confirmation_settings(
    environ: dict[str, str] | None = None,
) -> LiveSiteConfirmationSettings:
    """Load live-site confirmation settings from environment."""
    env = os.environ if environ is None else environ
    confirmation_enabled = _parse_bool(env.get(ENV_CONFIRMATION_ENABLED, ""))
    probe_timeout_seconds = _parse_positive_int(
        env.get(ENV_PROBE_TIMEOUT_SECONDS, str(DEFAULT_PROBE_TIMEOUT_SECONDS)),
        DEFAULT_PROBE_TIMEOUT_SECONDS,
    )
    probe_max_attempts = _parse_positive_int(
        env.get(ENV_PROBE_MAX_ATTEMPTS, str(DEFAULT_PROBE_MAX_ATTEMPTS)),
        DEFAULT_PROBE_MAX_ATTEMPTS,
    )
    probe_retry_delay_seconds = _parse_positive_int(
        env.get(
            ENV_PROBE_RETRY_DELAY_SECONDS,
            str(DEFAULT_PROBE_RETRY_DELAY_SECONDS),
        ),
        DEFAULT_PROBE_RETRY_DELAY_SECONDS,
    )
    site_base_url = env.get(ENV_SITE_URL, DEFAULT_SITE_URL).strip().rstrip("/") or DEFAULT_SITE_URL
    allowed_host = _host_from_site_url(site_base_url)
    return LiveSiteConfirmationSettings(
        confirmation_enabled=confirmation_enabled,
        probe_timeout_seconds=probe_timeout_seconds,
        probe_max_attempts=probe_max_attempts,
        probe_retry_delay_seconds=probe_retry_delay_seconds,
        site_base_url=site_base_url,
        allowed_host=allowed_host,
    )
