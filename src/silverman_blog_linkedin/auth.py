"""API key authentication for processing endpoints."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from silverman_blog_linkedin.config import Settings

_bearer = HTTPBearer(auto_error=False)


def require_api_key(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ] = None,
) -> None:
    """Validate Bearer token against configured API key."""
    settings: Settings = request.app.state.settings

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not secrets.compare_digest(credentials.credentials, settings.api_key):
        raise HTTPException(status_code=401, detail="Unauthorized")
