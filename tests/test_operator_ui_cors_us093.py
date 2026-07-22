"""US-093 operator UI CORS allowlist; US-096 console decommission hold."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.config import (
    ConfigurationError,
    ENV_OPERATOR_UI_ORIGINS,
    load_settings,
)
from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, make_settings


def test_load_settings_parses_operator_ui_origins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SILVERMAN_BLOG_LINKEDIN_BASE_PATH", str(tmp_path))
    monkeypatch.setenv("SILVERMAN_BLOG_LINKEDIN_API_KEY", "test-key")
    monkeypatch.setenv(
        ENV_OPERATOR_UI_ORIGINS,
        "http://192.168.0.194:8011, https://ui.example.local ",
    )
    settings = load_settings()
    assert settings.operator_ui_origins == (
        "http://192.168.0.194:8011",
        "https://ui.example.local",
    )


def test_load_settings_rejects_wildcard_operator_ui_origins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("SILVERMAN_BLOG_LINKEDIN_BASE_PATH", str(tmp_path))
    monkeypatch.setenv("SILVERMAN_BLOG_LINKEDIN_API_KEY", "test-key")
    monkeypatch.setenv(ENV_OPERATOR_UI_ORIGINS, "*")
    with pytest.raises(ConfigurationError, match="wildcard"):
        load_settings()


def test_cors_allowlisted_origin_receives_aca_origin(tmp_path: Path):
    settings = make_settings(tmp_path)
    settings = type(settings)(
        base_path=settings.base_path,
        api_key=settings.api_key,
        port=settings.port,
        operator_ui_origins=("http://192.168.0.194:8011",),
    )
    client = TestClient(create_app(settings))
    origin = "http://192.168.0.194:8011"
    preflight = client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers.get("access-control-allow-origin") == origin

    response = client.get("/health", headers={"Origin": origin})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin


def test_cors_allowlisted_origin_can_read_health_with_deployment_environment(
    tmp_path: Path,
):
    """US-094: pairing GET /health from UI origin stays CORS-covered (no wildcard)."""
    settings = make_settings(tmp_path)
    settings = type(settings)(
        base_path=settings.base_path,
        api_key=settings.api_key,
        port=settings.port,
        operator_ui_origins=("http://192.168.0.194:8011",),
        deployment_environment="prod",
    )
    client = TestClient(create_app(settings))
    origin = "http://192.168.0.194:8011"
    response = client.get("/health", headers={"Origin": origin})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.json()["deployment_environment"] == "prod"
    assert settings.api_key not in response.text


def test_cors_empty_allowlist_does_not_advertise_foreign_origin(tmp_path: Path):
    client = TestClient(create_app(make_settings(tmp_path)))
    origin = "http://192.168.0.194:8011"
    response = client.get("/health", headers={"Origin": origin})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in {
        k.lower(): v for k, v in response.headers.items()
    }
    # Starlette may omit the header entirely; ensure no wildcard either.
    acao = response.headers.get("access-control-allow-origin")
    assert acao is None


def test_former_embedded_console_route_decommissioned(tmp_path: Path):
    """US-096: former worker console URL fails closed (not SPA)."""
    client = TestClient(create_app(make_settings(tmp_path)))
    response = client.get("/flow-a/console/linkedin-variant-supervision")
    assert response.status_code == 410
    assert "decommissioned" in response.text.lower()
    assert 'id="root"' not in response.text
    assert "sk-" not in response.text
    assert "Bearer " not in response.text
