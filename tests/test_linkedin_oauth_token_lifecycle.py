"""Tests for LinkedIn OAuth token lifecycle."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.linkedin_oauth_client import (
    build_authorization_url,
    exchange_authorization_code,
    refresh_access_token,
)
from silverman_blog_linkedin.linkedin_oauth_config import (
    ENV_CLIENT_ID,
    ENV_CLIENT_SECRET,
    ENV_OAUTH_STATE_TTL_SECONDS,
    ENV_REDIRECT_URI,
    ENV_TOKEN_REFRESH_SKEW_SECONDS,
    ENV_TOKEN_STORE_PATH,
    OAUTH_SCOPE,
    load_linkedin_oauth_settings,
)
from silverman_blog_linkedin.linkedin_oauth_flow import (
    build_authorize_result,
    handle_oauth_callback,
)
from silverman_blog_linkedin.linkedin_oauth_state_store import (
    create_oauth_state,
    state_store_path_for_token_store,
    validate_and_consume_oauth_state,
)
from silverman_blog_linkedin.linkedin_token_provider import (
    LINKEDIN_OAUTH_REAUTHORIZATION_REQUIRED,
    LINKEDIN_OAUTH_REFRESH_FAILED,
    LINKEDIN_OAUTH_TOKEN_MISSING,
    resolve_linkedin_access_token,
)
from silverman_blog_linkedin.linkedin_token_store import (
    LinkedInTokenRecord,
    REDACTED,
    load_token_record,
    save_token_record,
)
from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, make_settings

CLIENT_ID = "test-client-id"
CLIENT_SECRET = "test-client-secret-should-not-appear"
REDIRECT_URI = "https://api.silverman.pro/linkedin/oauth/callback"
ACCESS_TOKEN = "test-oauth-access-token-secret"
REFRESH_TOKEN = "test-oauth-refresh-token-secret"
MEMBER_URN = "urn:li:person:test-member"
AUTH_CODE = "test-authorization-code-secret"


def _oauth_env(tmp_path: Path, **overrides: str) -> dict[str, str]:
    env = {
        ENV_CLIENT_ID: CLIENT_ID,
        ENV_CLIENT_SECRET: CLIENT_SECRET,
        ENV_REDIRECT_URI: REDIRECT_URI,
        ENV_TOKEN_STORE_PATH: str(tmp_path / "secrets" / "linkedin-oauth-tokens.json"),
        ENV_OAUTH_STATE_TTL_SECONDS: "600",
        ENV_TOKEN_REFRESH_SKEW_SECONDS: "300",
        "SILVERMAN_LINKEDIN_PUBLICATION_ENABLED": "false",
    }
    env.update(overrides)
    return env


def _token_record(
    *,
    expires_at: str,
    refresh_token: str | None = REFRESH_TOKEN,
) -> LinkedInTokenRecord:
    return LinkedInTokenRecord(
        access_token=ACCESS_TOKEN,
        refresh_token=refresh_token,
        scope=OAUTH_SCOPE,
        token_type="Bearer",
        created_at="2026-07-08T18:00:00Z",
        expires_at=expires_at,
        refresh_expires_at=None,
        member_urn=MEMBER_URN,
    )


def test_authorization_url_includes_required_parameters(tmp_path: Path):
    env = _oauth_env(tmp_path)
    oauth_settings = load_linkedin_oauth_settings(env).settings
    state = "random-state-value"
    url = build_authorization_url(oauth_settings, state=state)
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    assert parsed.path.endswith("/oauth/v2/authorization")
    assert params["response_type"] == ["code"]
    assert params["client_id"] == [CLIENT_ID]
    assert params["redirect_uri"] == [REDIRECT_URI]
    assert params["state"] == [state]
    assert params["scope"] == [OAUTH_SCOPE]


def test_authorize_endpoint_returns_url_without_secrets(tmp_path: Path):
    client = TestClient(create_app(make_settings(tmp_path)))
    env = _oauth_env(tmp_path)
    with pytest.MonkeyPatch.context() as mp:
        for key, value in env.items():
            mp.setenv(key, value)
        response = client.get("/linkedin/oauth/authorize", headers=auth_header())

    assert response.status_code == 200
    body = response.json()
    assert "authorization_url" in body
    assert CLIENT_SECRET not in json.dumps(body)
    assert ACCESS_TOKEN not in json.dumps(body)


def test_authorize_endpoint_requires_api_key(tmp_path: Path):
    client = TestClient(create_app(make_settings(tmp_path)))
    response = client.get("/linkedin/oauth/authorize")
    assert response.status_code == 401


def test_oauth_state_single_use_and_ttl(tmp_path: Path):
    store_path = tmp_path / "tokens.json"
    state_path = state_store_path_for_token_store(store_path)
    fixed_now = datetime(2026, 7, 8, 18, 0, 0, tzinfo=timezone.utc)

    state = create_oauth_state(state_path, ttl_seconds=600, now=fixed_now)
    assert validate_and_consume_oauth_state(state_path, state, now=fixed_now) is True
    assert validate_and_consume_oauth_state(state_path, state, now=fixed_now) is False

    state2 = create_oauth_state(state_path, ttl_seconds=60, now=fixed_now)
    expired_now = fixed_now + timedelta(seconds=61)
    assert validate_and_consume_oauth_state(state_path, state2, now=expired_now) is False


def test_callback_rejects_invalid_state(tmp_path: Path):
    env = _oauth_env(tmp_path)
    result = handle_oauth_callback(
        code=AUTH_CODE,
        state="unknown-state",
        error=None,
        error_description=None,
        environ=env,
    )
    assert result.status == "failed"
    assert "state" in result.message.lower()
    assert ACCESS_TOKEN not in result.message
    assert CLIENT_SECRET not in result.message


def test_callback_handles_linkedin_error(tmp_path: Path):
    env = _oauth_env(tmp_path)
    result = handle_oauth_callback(
        code=None,
        state=None,
        error="access_denied",
        error_description="User denied access",
        environ=env,
    )
    assert result.status == "failed"
    assert ACCESS_TOKEN not in result.message
    assert CLIENT_SECRET not in result.message


def test_callback_success_persists_tokens_without_secrets_in_response(tmp_path: Path):
    env = _oauth_env(tmp_path)
    authorize = build_authorize_result(env)
    assert authorize.authorization_url
    state = parse_qs(urlparse(authorize.authorization_url).query)["state"][0]

    mock_client = MagicMock()
    token_response = MagicMock()
    token_response.status_code = 200
    token_response.json.return_value = {
        "access_token": ACCESS_TOKEN,
        "expires_in": 3600,
        "refresh_token": REFRESH_TOKEN,
        "scope": OAUTH_SCOPE,
        "token_type": "Bearer",
        "sub": "test-member",
    }
    mock_client.post.return_value = token_response

    result = handle_oauth_callback(
        code=AUTH_CODE,
        state=state,
        error=None,
        error_description=None,
        environ=env,
        http_client=mock_client,
    )
    assert result.status == "completed"
    assert ACCESS_TOKEN not in result.message
    assert REFRESH_TOKEN not in result.message
    assert MEMBER_URN in result.message

    store_path = Path(env[ENV_TOKEN_STORE_PATH])
    record = load_token_record(store_path)
    assert record is not None
    assert record.access_token == ACCESS_TOKEN
    assert record.member_urn == MEMBER_URN


def test_callback_exchange_failure(tmp_path: Path):
    env = _oauth_env(tmp_path)
    authorize = build_authorize_result(env)
    state = parse_qs(urlparse(authorize.authorization_url).query)["state"][0]

    mock_client = MagicMock()
    token_response = MagicMock()
    token_response.status_code = 400
    mock_client.post.return_value = token_response

    result = handle_oauth_callback(
        code=AUTH_CODE,
        state=state,
        error=None,
        error_description=None,
        environ=env,
        http_client=mock_client,
    )
    assert result.status == "failed"
    assert ACCESS_TOKEN not in result.message


def test_token_store_redaction(tmp_path: Path):
    store_path = tmp_path / "tokens.json"
    record = _token_record(expires_at="2026-07-08T19:00:00Z")
    assert save_token_record(store_path, record)

    loaded = load_token_record(store_path)
    assert loaded is not None
    assert ACCESS_TOKEN not in repr(loaded)
    assert REFRESH_TOKEN not in repr(loaded)
    safe = loaded.to_safe_dict()
    assert safe["access_token"] == REDACTED
    assert safe["refresh_token"] == REDACTED


def test_status_endpoint_metadata_without_secrets(tmp_path: Path):
    env = _oauth_env(tmp_path)
    store_path = Path(env[ENV_TOKEN_STORE_PATH])
    save_token_record(store_path, _token_record(expires_at="2026-07-08T19:00:00Z"))

    client = TestClient(create_app(make_settings(tmp_path)))
    with pytest.MonkeyPatch.context() as mp:
        for key, value in env.items():
            mp.setenv(key, value)
        response = client.get("/linkedin/oauth/status", headers=auth_header())

    assert response.status_code == 200
    body = response.json()
    serialized = json.dumps(body)
    assert body["token_present"] is True
    assert body["member_urn"] == MEMBER_URN
    assert body["access_token_expires_at"] == "2026-07-08T19:00:00Z"
    assert ACCESS_TOKEN not in serialized
    assert REFRESH_TOKEN not in serialized
    assert CLIENT_SECRET not in serialized


def test_status_endpoint_requires_api_key(tmp_path: Path):
    client = TestClient(create_app(make_settings(tmp_path)))
    response = client.get("/linkedin/oauth/status")
    assert response.status_code == 401


def test_resolve_valid_token_without_refresh(tmp_path: Path):
    env = _oauth_env(tmp_path)
    store_path = Path(env[ENV_TOKEN_STORE_PATH])
    save_token_record(
        store_path,
        _token_record(expires_at="2026-07-08T20:00:00Z"),
    )
    now = datetime(2026, 7, 8, 18, 0, 0, tzinfo=timezone.utc)

    result = resolve_linkedin_access_token(env, now=now)
    assert result.status == "ok"
    assert result.access_token == ACCESS_TOKEN
    assert result.member_urn == MEMBER_URN


def test_resolve_refreshes_near_expiry_token(tmp_path: Path):
    env = _oauth_env(tmp_path)
    store_path = Path(env[ENV_TOKEN_STORE_PATH])
    save_token_record(
        store_path,
        _token_record(expires_at="2026-07-08T18:04:00Z"),
    )
    now = datetime(2026, 7, 8, 18, 0, 0, tzinfo=timezone.utc)

    mock_client = MagicMock()
    token_response = MagicMock()
    token_response.status_code = 200
    token_response.json.return_value = {
        "access_token": "refreshed-access-token",
        "expires_in": 3600,
        "scope": OAUTH_SCOPE,
        "token_type": "Bearer",
        "sub": "test-member",
    }
    mock_client.post.return_value = token_response

    result = resolve_linkedin_access_token(env, http_client=mock_client, now=now)
    assert result.status == "ok"
    assert result.access_token == "refreshed-access-token"
    mock_client.post.assert_called_once()


def test_resolve_expired_without_refresh_token_action_required(tmp_path: Path):
    env = _oauth_env(tmp_path)
    store_path = Path(env[ENV_TOKEN_STORE_PATH])
    save_token_record(
        store_path,
        _token_record(expires_at="2026-07-08T17:00:00Z", refresh_token=None),
    )
    now = datetime(2026, 7, 8, 18, 0, 0, tzinfo=timezone.utc)

    result = resolve_linkedin_access_token(env, now=now)
    assert result.status == "action_required"
    assert result.error_code == LINKEDIN_OAUTH_REAUTHORIZATION_REQUIRED


def test_resolve_empty_store_action_required(tmp_path: Path):
    env = _oauth_env(tmp_path)
    result = resolve_linkedin_access_token(env)
    assert result.status == "action_required"
    assert result.error_code == LINKEDIN_OAUTH_TOKEN_MISSING


def test_env_fallback_when_store_empty(tmp_path: Path):
    env = _oauth_env(tmp_path)
    env["SILVERMAN_LINKEDIN_ACCESS_TOKEN"] = "fallback-token"
    env["SILVERMAN_LINKEDIN_MEMBER_URN"] = MEMBER_URN

    result = resolve_linkedin_access_token(env)
    assert result.status == "ok"
    assert result.access_token == "fallback-token"


def test_exchange_authorization_code_mocked(tmp_path: Path):
    oauth_settings = load_linkedin_oauth_settings(_oauth_env(tmp_path)).settings
    mock_client = MagicMock()
    token_response = MagicMock()
    token_response.status_code = 200
    token_response.json.return_value = {
        "access_token": ACCESS_TOKEN,
        "expires_in": 3600,
        "refresh_token": REFRESH_TOKEN,
        "scope": OAUTH_SCOPE,
        "sub": "test-member",
    }
    mock_client.post.return_value = token_response

    result = exchange_authorization_code(
        oauth_settings,
        code=AUTH_CODE,
        client=mock_client,
    )
    assert result.success is True
    assert result.record is not None
    assert result.record.member_urn == MEMBER_URN
    mock_client.post.assert_called_once()


def test_refresh_access_token_failure_codes(tmp_path: Path):
    oauth_settings = load_linkedin_oauth_settings(_oauth_env(tmp_path)).settings
    mock_client = MagicMock()
    token_response = MagicMock()
    token_response.status_code = 401
    mock_client.post.return_value = token_response

    result = refresh_access_token(
        oauth_settings,
        refresh_token=REFRESH_TOKEN,
        existing_member_urn=MEMBER_URN,
        client=mock_client,
    )
    assert result.success is False
    assert result.error_code == LINKEDIN_OAUTH_REAUTHORIZATION_REQUIRED


def test_callback_html_escapes_provider_error_description(tmp_path: Path):
    client = TestClient(create_app(make_settings(tmp_path)))
    env = _oauth_env(tmp_path)
    xss_payload = '<script>alert("xss")</script>'

    with pytest.MonkeyPatch.context() as mp:
        for key, value in env.items():
            mp.setenv(key, value)
        response = client.get(
            "/linkedin/oauth/callback",
            params={
                "error": "access_denied",
                "error_description": xss_payload,
            },
        )

    assert response.status_code == 400
    body = response.text
    assert xss_payload not in body
    assert "&lt;script&gt;" in body


def test_expired_store_refresh_failure_does_not_use_env_fallback(tmp_path: Path):
    env = _oauth_env(tmp_path)
    env["SILVERMAN_LINKEDIN_ACCESS_TOKEN"] = "fallback-token"
    env["SILVERMAN_LINKEDIN_MEMBER_URN"] = MEMBER_URN
    store_path = Path(env[ENV_TOKEN_STORE_PATH])
    save_token_record(
        store_path,
        _token_record(expires_at="2026-07-08T17:00:00Z"),
    )
    now = datetime(2026, 7, 8, 18, 0, 0, tzinfo=timezone.utc)

    mock_client = MagicMock()
    token_response = MagicMock()
    token_response.status_code = 401
    mock_client.post.return_value = token_response

    result = resolve_linkedin_access_token(env, http_client=mock_client, now=now)
    assert result.status == "action_required"
    assert result.error_code == LINKEDIN_OAUTH_REAUTHORIZATION_REQUIRED
    assert result.access_token is None


def test_expired_store_missing_refresh_token_does_not_use_env_fallback(tmp_path: Path):
    env = _oauth_env(tmp_path)
    env["SILVERMAN_LINKEDIN_ACCESS_TOKEN"] = "fallback-token"
    env["SILVERMAN_LINKEDIN_MEMBER_URN"] = MEMBER_URN
    store_path = Path(env[ENV_TOKEN_STORE_PATH])
    save_token_record(
        store_path,
        _token_record(expires_at="2026-07-08T17:00:00Z", refresh_token=None),
    )
    now = datetime(2026, 7, 8, 18, 0, 0, tzinfo=timezone.utc)

    result = resolve_linkedin_access_token(env, now=now)
    assert result.status == "action_required"
    assert result.error_code == LINKEDIN_OAUTH_REAUTHORIZATION_REQUIRED
    assert result.access_token is None


def test_refresh_expires_at_past_skips_linkedin_call(tmp_path: Path):
    env = _oauth_env(tmp_path)
    store_path = Path(env[ENV_TOKEN_STORE_PATH])
    record = _token_record(expires_at="2026-07-08T17:00:00Z")
    record = LinkedInTokenRecord(
        access_token=record.access_token,
        refresh_token=record.refresh_token,
        scope=record.scope,
        token_type=record.token_type,
        created_at=record.created_at,
        expires_at=record.expires_at,
        refresh_expires_at="2026-07-08T17:30:00Z",
        member_urn=record.member_urn,
    )
    save_token_record(store_path, record)
    now = datetime(2026, 7, 8, 18, 0, 0, tzinfo=timezone.utc)

    mock_client = MagicMock()
    result = resolve_linkedin_access_token(env, http_client=mock_client, now=now)
    assert result.status == "action_required"
    assert result.error_code == LINKEDIN_OAUTH_REAUTHORIZATION_REQUIRED
    mock_client.post.assert_not_called()


def test_refresh_preserves_refresh_expires_at_when_not_returned(tmp_path: Path):
    env = _oauth_env(tmp_path)
    store_path = Path(env[ENV_TOKEN_STORE_PATH])
    existing_refresh_expires = "2026-12-31T23:59:59Z"
    record = _token_record(expires_at="2026-07-08T18:04:00Z")
    record = LinkedInTokenRecord(
        access_token=record.access_token,
        refresh_token=record.refresh_token,
        scope=record.scope,
        token_type=record.token_type,
        created_at=record.created_at,
        expires_at=record.expires_at,
        refresh_expires_at=existing_refresh_expires,
        member_urn=record.member_urn,
    )
    save_token_record(store_path, record)
    now = datetime(2026, 7, 8, 18, 0, 0, tzinfo=timezone.utc)

    mock_client = MagicMock()
    token_response = MagicMock()
    token_response.status_code = 200
    token_response.json.return_value = {
        "access_token": "refreshed-access-token",
        "expires_in": 3600,
        "refresh_token": REFRESH_TOKEN,
        "scope": OAUTH_SCOPE,
        "token_type": "Bearer",
        "sub": "test-member",
    }
    mock_client.post.return_value = token_response

    result = resolve_linkedin_access_token(env, http_client=mock_client, now=now)
    assert result.status == "ok"

    updated = load_token_record(store_path)
    assert updated is not None
    assert updated.refresh_expires_at == existing_refresh_expires


def test_oauth_state_consume_fails_when_persist_fails(tmp_path: Path, monkeypatch):
    store_path = tmp_path / "tokens.json"
    state_path = state_store_path_for_token_store(store_path)
    fixed_now = datetime(2026, 7, 8, 18, 0, 0, tzinfo=timezone.utc)
    state = create_oauth_state(state_path, ttl_seconds=600, now=fixed_now)

    def fail_save(_path, _state_map):
        return False

    monkeypatch.setattr(
        "silverman_blog_linkedin.linkedin_oauth_state_store._save_state_map",
        fail_save,
    )

    assert validate_and_consume_oauth_state(state_path, state, now=fixed_now) is False
    state_map = json.loads(state_path.read_text(encoding="utf-8"))
    assert state in state_map
