"""API key and operator JWT authentication for processing endpoints."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from silverman_blog_linkedin.config import Settings
from silverman_blog_linkedin.operator_google_auth import (
    OPERATOR_SESSION_COOKIE,
    parse_operator_session_cookie,
)

_bearer = HTTPBearer(auto_error=False)


def _api_key_valid(
    credentials: HTTPAuthorizationCredentials | None, api_key: str
) -> bool:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return False
    return secrets.compare_digest(credentials.credentials, api_key)


def _operator_session_valid(request: Request, settings: Settings) -> bool:
    """US-098: allowlisted Google identity operator JWT (HttpOnly cookie)."""
    if not settings.operator_session_secret:
        return False
    if not settings.operator_jwt_issuer or not settings.operator_jwt_audience:
        return False
    raw = request.cookies.get(OPERATOR_SESSION_COOKIE)
    session = parse_operator_session_cookie(
        raw,
        settings.operator_session_secret,
        issuer=settings.operator_jwt_issuer,
        audience=settings.operator_jwt_audience,
    )
    return session is not None


def require_api_key(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ] = None,
) -> None:
    """Validate Bearer API key **or** allowlisted operator JWT (US-098).

    n8n and machine clients continue to use the worker API key (ADR-0001).
    Browser console on the Google path uses the HttpOnly operator JWT cookie
    (credentials: include) — not the worker API key.
    """
    settings: Settings = request.app.state.settings

    if _api_key_valid(credentials, settings.api_key):
        return

    if _operator_session_valid(request, settings):
        return

    raise HTTPException(status_code=401, detail="Unauthorized")
