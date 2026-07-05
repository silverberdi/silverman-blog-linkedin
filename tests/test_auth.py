"""Tests for API key authentication."""

import json

from fastapi.testclient import TestClient

from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, create_full_layout, make_settings


def test_valid_token_allows_process_ready(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    client = TestClient(create_app(make_settings(base)))

    response = client.post("/process-ready", headers=auth_header())

    assert response.status_code == 200


def test_missing_authorization_returns_401(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    client = TestClient(create_app(make_settings(base)))

    response = client.post("/process-ready")

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}


def test_invalid_token_returns_401(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    client = TestClient(create_app(make_settings(base)))

    response = client.post("/process-ready", headers=auth_header("wrong-key"))

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}


def test_malformed_authorization_returns_401(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    client = TestClient(create_app(make_settings(base)))

    response = client.post(
        "/process-ready",
        headers={"Authorization": "Token not-bearer"},
    )

    assert response.status_code == 401


def test_auth_failure_does_not_expose_secrets(tmp_path):
    secret = "super-secret-api-key-value"
    base = tmp_path / "editorial"
    create_full_layout(base)
    client = TestClient(create_app(make_settings(base, api_key=secret)))

    response = client.post("/process-ready", headers=auth_header("wrong-key"))
    raw = response.text

    assert response.status_code == 401
    assert secret not in raw
    assert secret not in json.dumps(response.json())
