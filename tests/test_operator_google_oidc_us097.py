"""US-097 Google OIDC operator auth: allowlist, dual-accept, secrets hygiene."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.config import Settings
from silverman_blog_linkedin.main import create_app
from silverman_blog_linkedin.operator_google_auth import (
    OPERATOR_GOOGLE_EMAIL_ALLOWLIST,
    OPERATOR_SESSION_COOKIE,
    create_operator_session_cookie_value,
    is_allowlisted_email,
    normalize_email,
)
from tests.conftest import auth_header, create_full_layout, make_settings


ALLOWLISTED_A = "silverio.bernal@gmail.com"
ALLOWLISTED_B = "ltmoralesp84@gmail.com"
NON_ALLOWLISTED = "intruder@gmail.com"
SESSION_SECRET = "test-operator-session-secret-us097"
CLIENT_SECRET = "test-google-client-secret-us097"


class FakeExchanger:
    def __init__(self, email: str, *, verified: bool = True) -> None:
        self.email = email
        self.verified = verified
        self.calls = 0

    def exchange(
        self,
        *,
        code: str,
        code_verifier: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> dict[str, Any]:
        self.calls += 1
        assert client_secret == CLIENT_SECRET
        return {
            "email": self.email,
            "email_verified": self.verified,
            "sub": "google-sub-test",
        }


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
        "operator_ui_success_redirect": "http://192.168.0.194:8011/",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_allowlist_exact_set():
    assert OPERATOR_GOOGLE_EMAIL_ALLOWLIST == frozenset(
        {ALLOWLISTED_A, ALLOWLISTED_B}
    )
    assert is_allowlisted_email(ALLOWLISTED_A)
    assert is_allowlisted_email(ALLOWLISTED_B.upper())
    assert is_allowlisted_email(f"  {ALLOWLISTED_A}  ")
    assert not is_allowlisted_email(NON_ALLOWLISTED)
    assert normalize_email("Silverio.Bernal@Gmail.com") == ALLOWLISTED_A


def test_google_status_reports_enabled_without_secrets(tmp_path: Path):
    create_full_layout(tmp_path)
    client = TestClient(create_app(_google_settings(tmp_path)))
    response = client.get("/auth/google/status")
    assert response.status_code == 200
    body = response.json()
    assert body == {"enabled": True, "configured": True}
    raw = response.text
    assert CLIENT_SECRET not in raw
    assert SESSION_SECRET not in raw


def test_google_status_enabled_but_not_configured(tmp_path: Path):
    create_full_layout(tmp_path)
    settings = _google_settings(
        tmp_path,
        operator_google_client_secret="",
    )
    client = TestClient(create_app(settings))
    response = client.get("/auth/google/status")
    assert response.status_code == 200
    assert response.json() == {"enabled": True, "configured": False}


def test_google_start_fails_closed_when_not_configured(tmp_path: Path):
    create_full_layout(tmp_path)
    settings = _google_settings(
        tmp_path,
        operator_session_secret="",
    )
    client = TestClient(create_app(settings))
    response = client.get("/auth/google/start", follow_redirects=False)
    assert response.status_code == 503
    body = response.json()
    assert body["error_code"] == "operator_google_auth_not_configured"
    assert CLIENT_SECRET not in response.text
    assert "operator_session_secret" not in response.text.lower()


def test_allowlisted_callback_sets_session_cookie(tmp_path: Path):
    create_full_layout(tmp_path)
    app = create_app(_google_settings(tmp_path))
    app.state.google_token_exchanger = FakeExchanger(ALLOWLISTED_A)
    client = TestClient(app)

    start = client.get("/auth/google/start", follow_redirects=False)
    assert start.status_code == 302
    assert "accounts.google.com" in start.headers["location"]
    assert CLIENT_SECRET not in start.headers["location"]
    pending = start.cookies.get("silverman_oidc_pending")
    assert pending
    client.cookies.set("silverman_oidc_pending", pending)

    # Extract state from authorize URL.
    from urllib.parse import parse_qs, urlparse

    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    callback = client.get(
        "/auth/google/callback",
        params={"code": "test-code", "state": state},
        follow_redirects=False,
    )
    assert callback.status_code == 302
    assert "auth=ok" in callback.headers["location"]
    assert callback.headers["location"].startswith("http://192.168.0.194:8011/")
    session_cookie = callback.cookies.get(OPERATOR_SESSION_COOKIE)
    assert session_cookie
    assert CLIENT_SECRET not in callback.text
    assert SESSION_SECRET not in callback.text
    assert ALLOWLISTED_A not in (callback.headers.get("location") or "")

    client.cookies.set(OPERATOR_SESSION_COOKIE, session_cookie)
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json() == {
        "authenticated": True,
        "email": ALLOWLISTED_A,
        "can_mutate": True,
    }


def test_non_allowlisted_callback_forbidden_without_session(tmp_path: Path):
    create_full_layout(tmp_path)
    app = create_app(_google_settings(tmp_path))
    app.state.google_token_exchanger = FakeExchanger(NON_ALLOWLISTED)
    client = TestClient(app)

    start = client.get("/auth/google/start", follow_redirects=False)
    from urllib.parse import parse_qs, urlparse

    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    pending = start.cookies.get("silverman_oidc_pending")
    assert pending
    client.cookies.set("silverman_oidc_pending", pending)
    callback = client.get(
        "/auth/google/callback",
        params={"code": "test-code", "state": state},
        follow_redirects=False,
    )
    assert callback.status_code == 302
    assert "auth=forbidden" in callback.headers["location"]
    assert callback.cookies.get(OPERATOR_SESSION_COOKIE) in (None, "")
    # Explicitly ensure no authenticated session was minted.
    me = client.get("/auth/me")
    assert me.json()["authenticated"] is False


def test_dual_accept_operator_session_or_api_key(tmp_path: Path):
    create_full_layout(tmp_path)
    settings = _google_settings(tmp_path)
    client = TestClient(create_app(settings))

    # API key path (n8n / ADR-0001) unchanged.
    keyed = client.post("/process-ready", headers=auth_header(settings.api_key))
    assert keyed.status_code == 200

    # Operator session cookie path (US-097 bridge).
    cookie_value = create_operator_session_cookie_value(
        ALLOWLISTED_B, SESSION_SECRET
    )
    client.cookies.set(OPERATOR_SESSION_COOKIE, cookie_value)
    cookied = client.post("/process-ready")
    assert cookied.status_code == 200

    client.cookies.clear()
    # Neither → 401.
    denied = client.post("/process-ready")
    assert denied.status_code == 401
    assert settings.api_key not in denied.text
    assert SESSION_SECRET not in denied.text
    assert CLIENT_SECRET not in denied.text


def test_cors_allows_credentials_for_operator_origin(tmp_path: Path):
    create_full_layout(tmp_path)
    client = TestClient(create_app(_google_settings(tmp_path)))
    origin = "http://192.168.0.194:8011"
    response = client.get("/auth/me", headers={"Origin": origin})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_refuses_session_mint_for_non_allowlisted_email():
    with pytest.raises(ValueError, match="non-allowlisted"):
        create_operator_session_cookie_value(NON_ALLOWLISTED, SESSION_SECRET)
