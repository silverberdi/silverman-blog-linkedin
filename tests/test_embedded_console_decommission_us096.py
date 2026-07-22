"""US-096: embedded operator console decommissioned from worker API."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from silverman_blog_linkedin.linkedin_variant_pending_supervision import (
    DECOMMISSIONED_CONSOLE_ASSETS_PREFIX,
    DECOMMISSIONED_CONSOLE_PATH,
    DEFAULT_OPERATOR_UI_EXAMPLE_URL,
    OPERATOR_UI_LAN_PORT,
)
from silverman_blog_linkedin.main import create_app
from tests.conftest import make_settings

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_CONSOLE_STATIC = (
    REPO_ROOT
    / "src"
    / "silverman_blog_linkedin"
    / "static"
    / "linkedin-variant-supervision-console"
)
ROOT_DOCKERFILE = REPO_ROOT / "Dockerfile"


def test_console_index_path_fails_closed_with_410_html(tmp_path: Path):
    client = TestClient(create_app(make_settings(tmp_path)))
    response = client.get(DECOMMISSIONED_CONSOLE_PATH)
    assert response.status_code == 410
    assert "text/html" in response.headers["content-type"]
    body = response.text
    assert "decommissioned" in body.lower()
    assert str(OPERATOR_UI_LAN_PORT) in body
    assert DEFAULT_OPERATOR_UI_EXAMPLE_URL in body
    # Must not return the Vite SPA shell.
    assert 'id="root"' not in body
    assert "/assets/index-" not in body
    assert "type=\"module\"" not in body


def test_console_index_trailing_slash_fails_closed(tmp_path: Path):
    client = TestClient(create_app(make_settings(tmp_path)))
    response = client.get(f"{DECOMMISSIONED_CONSOLE_PATH}/")
    assert response.status_code == 410
    assert "decommissioned" in response.text.lower()


def test_console_asset_path_fails_closed(tmp_path: Path):
    client = TestClient(create_app(make_settings(tmp_path)))
    response = client.get(
        f"{DECOMMISSIONED_CONSOLE_ASSETS_PREFIX}/index-deadbeef.js",
    )
    assert response.status_code == 410
    assert "decommissioned" in response.text.lower()
    assert "text/html" in response.headers["content-type"]
    # Must not serve hashed console JS.
    assert "function" not in response.text
    assert "export " not in response.text


def test_console_decommission_json_accept(tmp_path: Path):
    client = TestClient(create_app(make_settings(tmp_path)))
    response = client.get(
        DECOMMISSIONED_CONSOLE_PATH,
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 410
    payload = response.json()
    assert payload["error"] == "embedded_operator_console_decommissioned"
    assert payload["supported_console_lan_port"] == OPERATOR_UI_LAN_PORT
    assert "sk-" not in response.text
    assert "Bearer " not in response.text
    assert "CHANGE_ME" not in response.text


def test_worker_package_does_not_ship_console_static_assets():
    assert not WORKER_CONSOLE_STATIC.exists(), (
        "worker must not ship linkedin-variant-supervision-console static tree"
    )


def test_worker_dockerfile_does_not_require_build_embedded():
    text = ROOT_DOCKERFILE.read_text(encoding="utf-8")
    assert "build:embedded" not in text
    assert "npm run build" not in text
    assert "API-only" in text
