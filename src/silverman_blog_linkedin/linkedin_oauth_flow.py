"""LinkedIn OAuth HTTP flow handlers for authorize, callback, and status."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.linkedin_config import load_linkedin_publication_settings
from silverman_blog_linkedin.linkedin_oauth_client import (
    OAuthHttpClientProtocol,
    build_authorization_url,
    exchange_authorization_code,
)
from silverman_blog_linkedin.linkedin_oauth_config import load_linkedin_oauth_settings
from silverman_blog_linkedin.linkedin_oauth_state_store import (
    create_oauth_state,
    state_store_path_for_token_store,
    validate_and_consume_oauth_state,
)
from silverman_blog_linkedin.linkedin_token_store import (
    load_token_record,
    save_token_record,
    token_present,
)

logger = logging.getLogger(__name__)


@dataclass
class AuthorizeResult:
    status: str
    authorization_url: str | None = None
    errors: list[str] = field(default_factory=list)


@dataclass
class CallbackResult:
    status: str
    message: str
    http_status: int = 200


@dataclass
class OAuthStatusResult:
    status: str
    token_store_configured: bool = False
    token_present: bool = False
    access_token_expires_at: str | None = None
    refresh_token_present: bool = False
    refresh_expires_at: str | None = None
    scopes: str | None = None
    member_urn: str | None = None
    publication_enabled: bool = False
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _oauth_config_errors(oauth_settings) -> list[str]:
    if not oauth_settings.oauth_configured:
        return ["linkedin_oauth_not_configured"]
    if not oauth_settings.has_token_store_path:
        return ["linkedin_oauth_token_store_not_configured"]
    return []


def build_authorize_result(
    environ: dict[str, str] | None = None,
    *,
    now: datetime | None = None,
) -> AuthorizeResult:
    """Generate authorization URL with server-side state."""
    oauth_load = load_linkedin_oauth_settings(environ)
    oauth_settings = oauth_load.settings
    if oauth_load.config_invalid:
        return AuthorizeResult(status="failed", errors=["linkedin_oauth_config_invalid"])

    config_errors = _oauth_config_errors(oauth_settings)
    if config_errors:
        return AuthorizeResult(status="failed", errors=config_errors)

    store_path = Path(oauth_settings.token_store_path)
    state_path = state_store_path_for_token_store(store_path)
    try:
        state = create_oauth_state(
            state_path,
            ttl_seconds=oauth_settings.state_ttl_seconds,
            now=now,
        )
    except OSError:
        return AuthorizeResult(status="failed", errors=["linkedin_oauth_state_write_failed"])

    authorization_url = build_authorization_url(oauth_settings, state=state)
    return AuthorizeResult(status="completed", authorization_url=authorization_url)


def handle_oauth_callback(
    *,
    code: str | None,
    state: str | None,
    error: str | None,
    error_description: str | None,
    environ: dict[str, str] | None = None,
    http_client: OAuthHttpClientProtocol | None = None,
    now: datetime | None = None,
) -> CallbackResult:
    """Validate callback parameters, exchange code, and persist tokens."""
    if error:
        logger.info("LinkedIn OAuth callback received provider error")
        message = "LinkedIn authorization was not completed. Please try again."
        if error_description:
            message = f"{message} ({error_description})"
        return CallbackResult(status="failed", message=message, http_status=400)

    if not code or not state:
        return CallbackResult(
            status="failed",
            message="Missing authorization code or state.",
            http_status=400,
        )

    oauth_load = load_linkedin_oauth_settings(environ)
    oauth_settings = oauth_load.settings
    if oauth_load.config_invalid or not oauth_settings.oauth_configured:
        return CallbackResult(
            status="failed",
            message="OAuth is not configured on this worker.",
            http_status=500,
        )
    if not oauth_settings.has_token_store_path:
        return CallbackResult(
            status="failed",
            message="Token store is not configured on this worker.",
            http_status=500,
        )

    store_path = Path(oauth_settings.token_store_path)
    state_path = state_store_path_for_token_store(store_path)
    if not validate_and_consume_oauth_state(state_path, state, now=now):
        logger.info("LinkedIn OAuth callback rejected invalid or expired state")
        return CallbackResult(
            status="failed",
            message="Invalid or expired authorization state. Please start again.",
            http_status=400,
        )

    exchange_result = exchange_authorization_code(
        oauth_settings,
        code=code,
        client=http_client,
        now=now,
    )
    if not exchange_result.success or exchange_result.record is None:
        logger.info("LinkedIn OAuth token exchange failed")
        return CallbackResult(
            status="failed",
            message="Token exchange failed. Please try authorizing again.",
            http_status=502,
        )

    if not save_token_record(store_path, exchange_result.record):
        return CallbackResult(
            status="failed",
            message="Failed to save tokens. Contact the operator.",
            http_status=500,
        )

    member_urn = exchange_result.record.member_urn
    logger.info("LinkedIn OAuth callback succeeded; member_urn=%s", member_urn)
    return CallbackResult(
        status="completed",
        message=(
            "LinkedIn authorization succeeded. "
            f"Member URN: {member_urn}. You may close this window."
        ),
        http_status=200,
    )


def build_oauth_status(
    environ: dict[str, str] | None = None,
) -> OAuthStatusResult:
    """Build safe OAuth diagnostics without token values."""
    oauth_load = load_linkedin_oauth_settings(environ)
    oauth_settings = oauth_load.settings
    publication_settings = load_linkedin_publication_settings(environ).settings

    store_path_str = oauth_settings.token_store_path
    store_configured = bool(store_path_str.strip())
    present = False
    expires_at = None
    refresh_present = False
    refresh_expires_at = None
    scopes = None
    member_urn = None

    if store_configured:
        store_path = Path(store_path_str)
        present = token_present(store_path)
        record = load_token_record(store_path)
        if record is not None:
            expires_at = record.expires_at or None
            refresh_present = bool(record.refresh_token)
            refresh_expires_at = record.refresh_expires_at
            scopes = record.scope or None
            member_urn = record.member_urn or None

    return OAuthStatusResult(
        status="completed",
        token_store_configured=store_configured,
        token_present=present,
        access_token_expires_at=expires_at,
        refresh_token_present=refresh_present,
        refresh_expires_at=refresh_expires_at,
        scopes=scopes,
        member_urn=member_urn,
        publication_enabled=publication_settings.publication_enabled,
    )
