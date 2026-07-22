"""Operator Google OIDC identity + allowlist (US-097 / BL-035 Story 1).

Server-side authorization-code + PKCE exchange, fail-closed email allowlist,
and HMAC-signed HttpOnly session cookies for the separated operator UI.

Does not implement US-098 JWT-only console→API cutover or US-099 public tunnel.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

# Normative US-097 allowlist (case-normalized compare).
OPERATOR_GOOGLE_EMAIL_ALLOWLIST: frozenset[str] = frozenset(
    {
        "silverio.bernal@gmail.com",
        "ltmoralesp84@gmail.com",
    }
)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/userinfo"

OPERATOR_SESSION_COOKIE = "silverman_operator_session"
OIDC_PENDING_COOKIE = "silverman_oidc_pending"

SESSION_TTL = timedelta(hours=12)
OIDC_PENDING_TTL = timedelta(minutes=10)


class TokenExchanger(Protocol):
    def exchange(
        self,
        *,
        code: str,
        code_verifier: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> dict[str, Any]:
        """Exchange authorization code for tokens / identity claims."""


@dataclass(frozen=True)
class OperatorSession:
    email: str
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_allowlisted_email(email: str) -> bool:
    return normalize_email(email) in OPERATOR_GOOGLE_EMAIL_ALLOWLIST


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def _sign(payload: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()
    return _b64url_encode(digest)


def _seal(data: dict[str, Any], secret: str) -> str:
    payload = _b64url_encode(
        json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    return f"{payload}.{_sign(payload.encode('ascii'), secret)}"


def _unseal(token: str, secret: str) -> dict[str, Any] | None:
    try:
        payload, signature = token.rsplit(".", 1)
    except ValueError:
        return None
    expected = _sign(payload.encode("ascii"), secret)
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        data = json.loads(_b64url_decode(payload))
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def create_operator_session_cookie_value(
    email: str,
    secret: str,
    *,
    now: datetime | None = None,
    ttl: timedelta = SESSION_TTL,
) -> str:
    """Seal allowlisted operator identity into an opaque cookie value."""
    if not is_allowlisted_email(email):
        raise ValueError("refusing to mint session for non-allowlisted email")
    instant = now or datetime.now(timezone.utc)
    expires = instant + ttl
    return _seal(
        {
            "email": normalize_email(email),
            "exp": int(expires.timestamp()),
        },
        secret,
    )


def parse_operator_session_cookie(
    token: str | None,
    secret: str,
    *,
    now: datetime | None = None,
) -> OperatorSession | None:
    if not token or not secret:
        return None
    data = _unseal(token, secret)
    if data is None:
        return None
    email = data.get("email")
    exp = data.get("exp")
    if not isinstance(email, str) or not isinstance(exp, int):
        return None
    if not is_allowlisted_email(email):
        return None
    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
    session = OperatorSession(email=normalize_email(email), expires_at=expires_at)
    instant = now or datetime.now(timezone.utc)
    if session.expires_at <= instant:
        return None
    return session


def create_oidc_pending_cookie_value(
    *,
    state: str,
    code_verifier: str,
    secret: str,
    now: datetime | None = None,
) -> str:
    instant = now or datetime.now(timezone.utc)
    return _seal(
        {
            "state": state,
            "code_verifier": code_verifier,
            "exp": int((instant + OIDC_PENDING_TTL).timestamp()),
        },
        secret,
    )


def parse_oidc_pending_cookie(
    token: str | None,
    secret: str,
    *,
    now: datetime | None = None,
) -> tuple[str, str] | None:
    if not token or not secret:
        return None
    data = _unseal(token, secret)
    if data is None:
        return None
    state = data.get("state")
    code_verifier = data.get("code_verifier")
    exp = data.get("exp")
    if (
        not isinstance(state, str)
        or not isinstance(code_verifier, str)
        or not isinstance(exp, int)
    ):
        return None
    instant = now or datetime.now(timezone.utc)
    if datetime.fromtimestamp(exp, tz=timezone.utc) <= instant:
        return None
    return state, code_verifier


def generate_pkce_pair() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) for S256 PKCE."""
    verifier = _b64url_encode(secrets.token_bytes(32))
    challenge = _b64url_encode(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def build_google_authorize_url(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
) -> str:
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "access_type": "online",
            "prompt": "select_account",
        }
    )
    return f"{GOOGLE_AUTH_URL}?{query}"


class HttpxGoogleTokenExchanger:
    """Live Google token + userinfo exchange (secrets never logged)."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client

    def exchange(
        self,
        *,
        code: str,
        code_verifier: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> dict[str, Any]:
        owns = self._client is None
        client = self._client or httpx.Client(timeout=30.0)
        try:
            token_response = client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                    "code_verifier": code_verifier,
                },
            )
            if token_response.status_code >= 400:
                logger.warning(
                    "Google token exchange failed status=%s",
                    token_response.status_code,
                )
                raise ValueError("google_token_exchange_failed")
            token_payload = token_response.json()
            access_token = token_payload.get("access_token")
            if not isinstance(access_token, str) or not access_token:
                raise ValueError("google_access_token_missing")

            userinfo_response = client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_response.status_code >= 400:
                logger.warning(
                    "Google userinfo failed status=%s",
                    userinfo_response.status_code,
                )
                raise ValueError("google_userinfo_failed")
            userinfo = userinfo_response.json()
            if not isinstance(userinfo, dict):
                raise ValueError("google_userinfo_invalid")
            return userinfo
        except httpx.HTTPError:
            logger.warning("Google OIDC HTTP error during token/userinfo exchange")
            raise ValueError("google_http_error") from None
        finally:
            if owns:
                client.close()


def email_from_userinfo(userinfo: dict[str, Any]) -> str | None:
    email = userinfo.get("email")
    if not isinstance(email, str) or not email.strip():
        return None
    # Google may omit email_verified for some accounts; require verified when present.
    verified = userinfo.get("email_verified")
    if verified is False or verified == "false":
        return None
    return normalize_email(email)


def build_ui_auth_redirect(success_redirect: str, auth_result: str) -> str:
    """Append ?auth=… to the configured UI success redirect URL."""
    from urllib.parse import parse_qsl, urlencode as _urlencode, urlparse, urlunparse

    parsed = urlparse(success_redirect.strip())
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["auth"] = auth_result
    return urlunparse(parsed._replace(query=_urlencode(query)))
