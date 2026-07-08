"""Resolve LinkedIn access tokens for publication via OAuth store or env fallback."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from silverman_blog_linkedin.linkedin_config import (
    ENV_ACCESS_TOKEN,
    ENV_MEMBER_URN,
)
from silverman_blog_linkedin.linkedin_oauth_client import (
    OAuthHttpClientProtocol,
    refresh_access_token,
)
from silverman_blog_linkedin.linkedin_oauth_config import load_linkedin_oauth_settings
from silverman_blog_linkedin.linkedin_token_store import (
    LinkedInTokenRecord,
    load_token_record,
    parse_expires_at,
    save_token_record,
)

LINKEDIN_OAUTH_TOKEN_MISSING = "linkedin_oauth_token_missing"
LINKEDIN_OAUTH_REFRESH_FAILED = "linkedin_oauth_refresh_failed"
LINKEDIN_OAUTH_REAUTHORIZATION_REQUIRED = "linkedin_oauth_reauthorization_required"
LINKEDIN_PUBLISH_TOKEN_MISSING = "linkedin_publish_token_missing"
LINKEDIN_PUBLISH_MEMBER_URN_MISSING = "linkedin_publish_member_urn_missing"

_ENV_FALLBACK_ALLOWED_CODES = frozenset({LINKEDIN_OAUTH_TOKEN_MISSING})


@dataclass(frozen=True)
class TokenResolutionResult:
    status: Literal["ok", "action_required"]
    access_token: str | None
    member_urn: str | None
    error_code: str | None = None


def _env_fallback(environ: dict[str, str]) -> TokenResolutionResult | None:
    access_token = environ.get(ENV_ACCESS_TOKEN, "").strip()
    member_urn = environ.get(ENV_MEMBER_URN, "").strip()
    if access_token and member_urn:
        return TokenResolutionResult(
            status="ok",
            access_token=access_token,
            member_urn=member_urn,
            error_code=None,
        )
    return None


def _token_needs_refresh(
    record: LinkedInTokenRecord,
    *,
    now: datetime,
    refresh_skew_seconds: int,
) -> bool:
    expires_at = parse_expires_at(record.expires_at)
    if expires_at is None:
        return True
    skew_boundary = expires_at - timedelta(seconds=refresh_skew_seconds)
    return now >= skew_boundary


def _ok_from_record(record: LinkedInTokenRecord) -> TokenResolutionResult:
    return TokenResolutionResult(
        status="ok",
        access_token=record.access_token,
        member_urn=record.member_urn,
        error_code=None,
    )


def _resolve_from_store(
    store_path: Path,
    *,
    oauth_settings,
    refresh_skew_seconds: int,
    http_client: OAuthHttpClientProtocol | None,
    now: datetime,
) -> TokenResolutionResult:
    record = load_token_record(store_path)
    if record is None:
        return TokenResolutionResult(
            status="action_required",
            access_token=None,
            member_urn=None,
            error_code=LINKEDIN_OAUTH_TOKEN_MISSING,
        )

    if not _token_needs_refresh(
        record, now=now, refresh_skew_seconds=refresh_skew_seconds
    ):
        return _ok_from_record(record)

    if not record.refresh_token:
        return TokenResolutionResult(
            status="action_required",
            access_token=None,
            member_urn=None,
            error_code=LINKEDIN_OAUTH_REAUTHORIZATION_REQUIRED,
        )

    if record.refresh_expires_at:
        refresh_expires = parse_expires_at(record.refresh_expires_at)
        if refresh_expires is not None and now >= refresh_expires:
            return TokenResolutionResult(
                status="action_required",
                access_token=None,
                member_urn=None,
                error_code=LINKEDIN_OAUTH_REAUTHORIZATION_REQUIRED,
            )

    if not oauth_settings.oauth_configured:
        return TokenResolutionResult(
            status="action_required",
            access_token=None,
            member_urn=None,
            error_code=LINKEDIN_OAUTH_REFRESH_FAILED,
        )

    refresh_result = refresh_access_token(
        oauth_settings,
        refresh_token=record.refresh_token,
        existing_member_urn=record.member_urn,
        existing_refresh_expires_at=record.refresh_expires_at,
        client=http_client,
        now=now,
    )
    if not refresh_result.success or refresh_result.record is None:
        return TokenResolutionResult(
            status="action_required",
            access_token=None,
            member_urn=None,
            error_code=refresh_result.error_code or LINKEDIN_OAUTH_REFRESH_FAILED,
        )

    if not save_token_record(store_path, refresh_result.record):
        return TokenResolutionResult(
            status="action_required",
            access_token=None,
            member_urn=None,
            error_code=LINKEDIN_OAUTH_REFRESH_FAILED,
        )
    return _ok_from_record(refresh_result.record)


def resolve_linkedin_access_token(
    environ: dict[str, str] | None = None,
    *,
    http_client: OAuthHttpClientProtocol | None = None,
    now: datetime | None = None,
) -> TokenResolutionResult:
    """Resolve a valid access token and member URN for real LinkedIn publication."""
    env = os.environ if environ is None else environ
    current = now or datetime.now(timezone.utc)
    oauth_load = load_linkedin_oauth_settings(env)
    oauth_settings = oauth_load.settings

    if oauth_settings.has_token_store_path:
        store_path = Path(oauth_settings.token_store_path)
        store_result = _resolve_from_store(
            store_path,
            oauth_settings=oauth_settings,
            refresh_skew_seconds=oauth_settings.refresh_skew_seconds,
            http_client=http_client,
            now=current,
        )
        if store_result.status == "ok":
            return store_result
        if store_result.error_code in _ENV_FALLBACK_ALLOWED_CODES:
            fallback = _env_fallback(env)
            if fallback is not None:
                return fallback
        return store_result

    fallback = _env_fallback(env)
    if fallback is not None:
        return fallback

    access_token = env.get(ENV_ACCESS_TOKEN, "").strip()
    if not access_token:
        return TokenResolutionResult(
            status="action_required",
            access_token=None,
            member_urn=None,
            error_code=LINKEDIN_PUBLISH_TOKEN_MISSING,
        )
    member_urn = env.get(ENV_MEMBER_URN, "").strip()
    if not member_urn:
        return TokenResolutionResult(
            status="action_required",
            access_token=None,
            member_urn=None,
            error_code=LINKEDIN_PUBLISH_MEMBER_URN_MISSING,
        )
    return TokenResolutionResult(
        status="ok",
        access_token=access_token,
        member_urn=member_urn,
        error_code=None,
    )
