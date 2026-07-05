"""Tests for GET /health."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin import SERVICE_NAME, __version__
from silverman_blog_linkedin.config import Settings
from silverman_blog_linkedin.main import create_app
from silverman_blog_linkedin.paths import EXPECTED_FOLDERS


def _create_full_layout(base: Path) -> None:
    base.mkdir(parents=True, exist_ok=True)
    for relative in EXPECTED_FOLDERS:
        (base / relative).mkdir(parents=True, exist_ok=True)


def _settings(base: Path, api_key: str = "test-secret-key") -> Settings:
    return Settings(base_path=base.resolve(), api_key=api_key, port=8000)


def test_health_healthy(tmp_path):
    base = tmp_path / "editorial"
    _create_full_layout(base)
    client = TestClient(create_app(_settings(base)))

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == SERVICE_NAME
    assert body["version"] == __version__
    assert body["base_path"] == str(base.resolve())
    assert body["folders_ready"] is True
    assert set(body["folders"].keys()) == set(EXPECTED_FOLDERS)
    for folder_status in body["folders"].values():
        assert folder_status == {"exists": True, "is_directory": True}


def test_health_degraded(tmp_path):
    base = tmp_path / "editorial"
    base.mkdir()
    client = TestClient(create_app(_settings(base)))

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["folders_ready"] is False


def test_health_does_not_expose_secrets(tmp_path):
    secret = "super-secret-api-key-value"
    base = tmp_path / "editorial"
    _create_full_layout(base)
    client = TestClient(create_app(_settings(base, api_key=secret)))

    response = client.get("/health")
    raw = response.text

    assert response.status_code == 200
    assert secret not in raw
    body = response.json()
    assert "api_key" not in body
    assert secret not in json.dumps(body)


def test_health_is_read_only(tmp_path):
    base = tmp_path / "editorial"
    _create_full_layout(base)
    ready_dir = base / "blog-posts" / "ready"
    marker = ready_dir / "probe.txt"
    marker.write_text("unchanged")
    mtime_before = marker.stat().st_mtime

    client = TestClient(create_app(_settings(base)))
    client.get("/health")

    assert marker.read_text() == "unchanged"
    assert marker.stat().st_mtime == mtime_before
