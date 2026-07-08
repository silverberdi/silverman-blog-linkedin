"""LinkedIn OAuth 2.0 client for authorization, exchange, and refresh."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from urllib.parse import urlencode

import httpx

from silverman_blog_linkedin.linkedin_oauth_config import (
    OAUTH_SCOPE,
    LinkedInOAuthSettings,
)
from silverman_blog_linkedin.linkedin_token_store import (
    LinkedInTokenRecord,
    compute_expires_at,
    utc_now_iso,
)

LINKEDIN_AUTHORIZE_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"


class OAuthHttpClientProtocol(Protocol):
    def post(
        self,
        url: str,
        *,
        data: dict[str, str],
        headers: dict[str, str] | None = None,
    ) -> httpx.Response: ...

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str],
    ) -> httpx.Response: ...


@dataclass(frozen=True)
class TokenExchangeResult:
    success: bool
    record: LinkedInTokenRecord | None = None
    error_code: str | None = None


def build_authorization_url(
    settings: LinkedInOAuthSettings,
    *,
    state: str,
) -> str:
    """Build LinkedIn OAuth authorization URL with required parameters."""
    params = {
        "response_type": "code",
        "client_id": settings.client_id,
        "redirect_uri": settings.redirect_uri,
        "state": state,
        "scope": OAUTH_SCOPE,
    }
    return f"{LINKEDIN_AUTHORIZE_URL}?{urlencode(params)}"


def member_urn_from_sub(sub: str) -> str:
    """Convert OIDC subject to LinkedIn member URN."""
    return f"urn:li:person:{sub.strip()}"


def _resolve_member_urn(
    access_token: str,
    *,
    client: OAuthHttpClientProtocol,
    token_payload: dict[str, Any],
) -> str | None:
    if isinstance(token_payload.get("sub"), str) and token_payload["sub"].strip():
        return member_urn_from_sub(token_payload["sub"])
    try:
        response = client.get(
            LINKEDIN_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        return None
    try:
        userinfo = response.json()
    except ValueError:
        return None
    sub = userinfo.get("sub")
    if isinstance(sub, str) and sub.strip():
        return member_urn_from_sub(sub)
    return None


def _build_token_record(
    payload: dict[str, Any],
    *,
    member_urn: str,
    now: datetime,
) -> LinkedInTokenRecord | None:
    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        return None
    expires_in = payload.get("expires_in")
    if not isinstance(expires_in, int) or expires_in <= 0:
        return None
    refresh_expires_at = None
    refresh_expires_in = payload.get("refresh_token_expires_in")
    if isinstance(refresh_expires_in, int) and refresh_expires_in > 0:
        refresh_expires_at = compute_expires_at(
            now=now, expires_in_seconds=refresh_expires_in
        )
    refresh_token = payload.get("refresh_token")
    refresh_value = (
        refresh_token.strip()
        if isinstance(refresh_token, str) and refresh_token.strip()
        else None
    )
    created_at = utc_now_iso() if now is None else now.astimezone(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    return LinkedInTokenRecord(
        access_token=access_token.strip(),
        refresh_token=refresh_value,
        scope=str(payload.get("scope") or OAUTH_SCOPE),
        token_type=str(payload.get("token_type") or "Bearer"),
        created_at=created_at,
        expires_at=compute_expires_at(now=now, expires_in_seconds=expires_in),
        refresh_expires_at=refresh_expires_at,
        member_urn=member_urn,
    )


def exchange_authorization_code(
    settings: LinkedInOAuthSettings,
    *,
    code: str,
    client: OAuthHttpClientProtocol | None = None,
    now: datetime | None = None,
) -> TokenExchangeResult:
    """Exchange authorization code for tokens."""
    current = now or datetime.now(timezone.utc)
    owns_client = client is None
    if owns_client:
        client = httpx.Client(timeout=30.0)
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": settings.client_id,
        "client_secret": settings.client_secret,
        "redirect_uri": settings.redirect_uri,
    }
    try:
        response = client.post(
            LINKEDIN_TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.status_code != 200:
            return TokenExchangeResult(
                success=False,
                error_code="linkedin_oauth_refresh_failed",
            )
        try:
            payload = response.json()
        except ValueError:
            return TokenExchangeResult(
                success=False,
                error_code="linkedin_oauth_refresh_failed",
            )
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token.strip():
            return TokenExchangeResult(
                success=False,
                error_code="linkedin_oauth_refresh_failed",
            )
        member_urn = _resolve_member_urn(
            access_token.strip(),
            client=client,
            token_payload=payload,
        )
        if member_urn is None:
            return TokenExchangeResult(
                success=False,
                error_code="linkedin_oauth_refresh_failed",
            )
        record = _build_token_record(payload, member_urn=member_urn, now=current)
        if record is None:
            return TokenExchangeResult(
                success=False,
                error_code="linkedin_oauth_refresh_failed",
            )
        return TokenExchangeResult(success=True, record=record)
    except httpx.HTTPError:
        return TokenExchangeResult(success=False, error_code="linkedin_oauth_refresh_failed")
    finally:
        if owns_client and isinstance(client, httpx.Client):
            client.close()


def refresh_access_token(
    settings: LinkedInOAuthSettings,
    *,
    refresh_token: str,
    existing_member_urn: str | None = None,
    existing_refresh_expires_at: str | None = None,
    client: OAuthHttpClientProtocol | None = None,
    now: datetime | None = None,
) -> TokenExchangeResult:
    """Refresh access token using stored refresh token."""
    current = now or datetime.now(timezone.utc)
    owns_client = client is None
    if owns_client:
        client = httpx.Client(timeout=30.0)
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": settings.client_id,
        "client_secret": settings.client_secret,
    }
    try:
        response = client.post(
            LINKEDIN_TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.status_code != 200:
            error_code = "linkedin_oauth_reauthorization_required"
            if response.status_code not in (400, 401):
                error_code = "linkedin_oauth_refresh_failed"
            return TokenExchangeResult(success=False, error_code=error_code)

        try:
            payload = response.json()
        except ValueError:
            return TokenExchangeResult(
                success=False,
                error_code="linkedin_oauth_refresh_failed",
            )

        member_urn = None
        if isinstance(payload.get("sub"), str):
            member_urn = member_urn_from_sub(payload["sub"])
        access_token = payload.get("access_token")
        if member_urn is None and isinstance(access_token, str):
            member_urn = _resolve_member_urn(
                access_token.strip(),
                client=client,
                token_payload=payload,
            )
        if member_urn is None and existing_member_urn:
            member_urn = existing_member_urn
        if member_urn is None:
            return TokenExchangeResult(
                success=False,
                error_code="linkedin_oauth_reauthorization_required",
            )

        record = _build_token_record(payload, member_urn=member_urn, now=current)
        if record is None:
            return TokenExchangeResult(
                success=False,
                error_code="linkedin_oauth_refresh_failed",
            )
        if not record.refresh_token:
            record = LinkedInTokenRecord(
                access_token=record.access_token,
                refresh_token=refresh_token,
                scope=record.scope,
                token_type=record.token_type,
                created_at=record.created_at,
                expires_at=record.expires_at,
                refresh_expires_at=record.refresh_expires_at,
                member_urn=record.member_urn,
            )
        if record.refresh_expires_at is None and existing_refresh_expires_at:
            record = LinkedInTokenRecord(
                access_token=record.access_token,
                refresh_token=record.refresh_token,
                scope=record.scope,
                token_type=record.token_type,
                created_at=record.created_at,
                expires_at=record.expires_at,
                refresh_expires_at=existing_refresh_expires_at,
                member_urn=record.member_urn,
            )
        return TokenExchangeResult(success=True, record=record)
    except httpx.HTTPError:
        return TokenExchangeResult(
            success=False,
            error_code="linkedin_oauth_refresh_failed",
        )
    finally:
        if owns_client and isinstance(client, httpx.Client):
            client.close()
