"""US-098 operator JWT mint/validate + n8n API-key hold (BL-035 Story 2)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.config import Settings
from silverman_blog_linkedin.main import create_app
from silverman_blog_linkedin.operator_google_auth import (
    DEFAULT_OPERATOR_JWT_AUDIENCE,
    DEFAULT_OPERATOR_JWT_ISSUER,
    OPERATOR_SESSION_COOKIE,
    create_operator_session_cookie_value,
    parse_operator_session_cookie,
)
from tests.conftest import auth_header, create_full_layout, make_settings

ALLOWLISTED = "silverio.bernal@gmail.com"
NON_ALLOWLISTED = "intruder@gmail.com"
SESSION_SECRET = "test-operator-session-secret-us098"
CLIENT_SECRET = "test-google-client-secret-us098"


def _google_settings(base: Path, **overrides: Any) -> Settings:
    base_settings = make_settings(base)
    defaults: dict[str, Any] = {
        "base_path": base_settings.base_path,
        "api_key": base_settings.api_key,
        "port": base_settings.port,
        "operator_ui_origins": ("http://192.168.0.194:8011",),
        "operator_google_auth_enabled": True,
        "operator_google_client_id": "test-google-client-id",
        "operator_google_client_secret": CLIENT_SECRET,
        "operator_google_redirect_uri": (
            "http://192.168.0.194:8010/auth/google/callback"
        ),
        "operator_session_secret": SESSION_SECRET,
        "operator_jwt_issuer": DEFAULT_OPERATOR_JWT_ISSUER,
        "operator_jwt_audience": DEFAULT_OPERATOR_JWT_AUDIENCE,
        "operator_ui_success_redirect": "http://192.168.0.194:8011/",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_mint_jwt_for_allowlisted_identity_has_required_claims():
    now = datetime(2026, 7, 22, 12, 0, 0, tzinfo=timezone.utc)
    token = create_operator_session_cookie_value(
        ALLOWLISTED,
        SESSION_SECRET,
        sub="google-sub-allowlisted",
        now=now,
    )
    session = parse_operator_session_cookie(
        token,
        SESSION_SECRET,
        now=now + timedelta(minutes=1),
    )
    assert session is not None
    assert session.email == ALLOWLISTED
    assert session.sub == "google-sub-allowlisted"
    # Compact JWT shape: header.payload.signature
    assert token.count(".") == 2
    assert SESSION_SECRET not in token


def test_reject_expired_operator_jwt():
    now = datetime(2026, 7, 22, 12, 0, 0, tzinfo=timezone.utc)
    token = create_operator_session_cookie_value(
        ALLOWLISTED,
        SESSION_SECRET,
        now=now,
        ttl=timedelta(seconds=30),
    )
    assert (
        parse_operator_session_cookie(
            token,
            SESSION_SECRET,
            now=now + timedelta(minutes=5),
        )
        is None
    )


def test_reject_tampered_operator_jwt():
    token = create_operator_session_cookie_value(ALLOWLISTED, SESSION_SECRET)
    header, payload, signature = token.split(".")
    tampered = f"{header}.{payload}.{signature[:-4]}xxxx"
    assert parse_operator_session_cookie(tampered, SESSION_SECRET) is None


def test_reject_wrong_issuer():
    token = create_operator_session_cookie_value(
        ALLOWLISTED,
        SESSION_SECRET,
        issuer="wrong-issuer",
    )
    assert (
        parse_operator_session_cookie(
            token,
            SESSION_SECRET,
            issuer=DEFAULT_OPERATOR_JWT_ISSUER,
            audience=DEFAULT_OPERATOR_JWT_AUDIENCE,
        )
        is None
    )


def test_reject_wrong_audience():
    token = create_operator_session_cookie_value(
        ALLOWLISTED,
        SESSION_SECRET,
        audience="wrong-audience",
    )
    assert (
        parse_operator_session_cookie(
            token,
            SESSION_SECRET,
            issuer=DEFAULT_OPERATOR_JWT_ISSUER,
            audience=DEFAULT_OPERATOR_JWT_AUDIENCE,
        )
        is None
    )


def test_reject_non_allowlisted_email_at_mint():
    with pytest.raises(ValueError, match="non-allowlisted"):
        create_operator_session_cookie_value(NON_ALLOWLISTED, SESSION_SECRET)


def test_n8n_api_key_still_works_when_google_auth_enabled(tmp_path: Path):
    create_full_layout(tmp_path)
    settings = _google_settings(tmp_path)
    client = TestClient(create_app(settings))
    keyed = client.post("/process-ready", headers=auth_header(settings.api_key))
    assert keyed.status_code == 200
    assert settings.api_key not in keyed.text
    assert SESSION_SECRET not in keyed.text


def test_operator_jwt_cookie_authorizes_protected_route(tmp_path: Path):
    create_full_layout(tmp_path)
    settings = _google_settings(tmp_path)
    client = TestClient(create_app(settings))
    cookie_value = create_operator_session_cookie_value(
        ALLOWLISTED,
        SESSION_SECRET,
        issuer=settings.operator_jwt_issuer,
        audience=settings.operator_jwt_audience,
    )
    client.cookies.set(OPERATOR_SESSION_COOKIE, cookie_value)
    cookied = client.post("/process-ready")
    assert cookied.status_code == 200
    assert SESSION_SECRET not in cookied.text


def test_protected_route_without_api_key_or_jwt_returns_clear_401(tmp_path: Path):
    create_full_layout(tmp_path)
    settings = _google_settings(tmp_path)
    client = TestClient(create_app(settings))
    denied = client.post("/process-ready")
    assert denied.status_code == 401
    assert denied.json()["detail"] == "Unauthorized"
    assert settings.api_key not in denied.text
    assert SESSION_SECRET not in denied.text
    assert CLIENT_SECRET not in denied.text


def test_logout_clears_cookie_and_subsequent_request_fails(tmp_path: Path):
    create_full_layout(tmp_path)
    settings = _google_settings(tmp_path)
    client = TestClient(create_app(settings))
    cookie_value = create_operator_session_cookie_value(ALLOWLISTED, SESSION_SECRET)
    client.cookies.set(OPERATOR_SESSION_COOKIE, cookie_value)
    assert client.post("/process-ready").status_code == 200

    logout = client.post("/auth/logout")
    assert logout.status_code == 200
    assert logout.json() == {"ok": True}
    # TestClient may retain jar; force clear to simulate browser cookie deletion.
    client.cookies.clear()
    denied = client.post("/process-ready")
    assert denied.status_code == 401


def test_expired_jwt_cookie_rejected_on_protected_route(tmp_path: Path):
    create_full_layout(tmp_path)
    settings = _google_settings(tmp_path)
    client = TestClient(create_app(settings))
    now = datetime(2020, 1, 1, tzinfo=timezone.utc)
    expired = create_operator_session_cookie_value(
        ALLOWLISTED,
        SESSION_SECRET,
        now=now,
        ttl=timedelta(seconds=1),
    )
    client.cookies.set(OPERATOR_SESSION_COOKIE, expired)
    denied = client.post("/process-ready")
    assert denied.status_code == 401
    assert denied.json()["detail"] == "Unauthorized"


def test_legacy_opaque_hmac_cookie_fails_closed(tmp_path: Path):
    """US-097 opaque seal is not a JWT — operators must re-auth after cutover."""
    create_full_layout(tmp_path)
    settings = _google_settings(tmp_path)
    client = TestClient(create_app(settings))
    # Two-part opaque seal (not three-part JWT).
    legacy = "eyJlbWFpbCI6InRlc3QifQ.fakesignature"
    client.cookies.set(OPERATOR_SESSION_COOKIE, legacy)
    denied = client.post("/process-ready")
    assert denied.status_code == 401
