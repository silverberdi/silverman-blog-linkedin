"""US-094: worker deployment environment identity and health advertisement."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.config import (
    ENV_API_KEY,
    ENV_BASE_PATH,
    ENV_DEPLOYMENT_ENVIRONMENT,
    ConfigurationError,
    Settings,
    load_settings,
)
from silverman_blog_linkedin.main import create_app
from silverman_blog_linkedin.paths import EXPECTED_FOLDERS


def _create_full_layout(base: Path) -> None:
    base.mkdir(parents=True, exist_ok=True)
    for relative in EXPECTED_FOLDERS:
        (base / relative).mkdir(parents=True, exist_ok=True)


def _minimal_env(base: Path, **overrides: str) -> dict[str, str]:
    env = {
        ENV_API_KEY: "test-secret-key",
        ENV_BASE_PATH: str(base),
    }
    env.update(overrides)
    return env


@pytest.mark.parametrize("value", ["uat", "prod", "UAT", "Prod"])
def test_load_settings_accepts_closed_deployment_environment(
    tmp_path: Path, value: str
) -> None:
    base = tmp_path / "data"
    base.mkdir()
    settings = load_settings(
        _minimal_env(base, **{ENV_DEPLOYMENT_ENVIRONMENT: value})
    )
    assert settings.deployment_environment == value.strip().lower()


def test_load_settings_unset_deployment_environment_is_none(tmp_path: Path) -> None:
    base = tmp_path / "data"
    base.mkdir()
    settings = load_settings(_minimal_env(base))
    assert settings.deployment_environment is None


def test_load_settings_rejects_invalid_deployment_environment(tmp_path: Path) -> None:
    base = tmp_path / "data"
    base.mkdir()
    with pytest.raises(ConfigurationError, match=ENV_DEPLOYMENT_ENVIRONMENT):
        load_settings(
            _minimal_env(base, **{ENV_DEPLOYMENT_ENVIRONMENT: "lan"})
        )


def test_health_advertises_deployment_environment_when_configured(
    tmp_path: Path,
) -> None:
    base = tmp_path / "editorial"
    _create_full_layout(base)
    settings = Settings(
        base_path=base.resolve(),
        api_key="test-secret-key",
        port=8000,
        deployment_environment="prod",
    )
    client = TestClient(create_app(settings))

    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["deployment_environment"] == "prod"
    assert "test-secret-key" not in response.text
    assert "api_key" not in body


def test_health_omits_deployment_environment_when_unset(tmp_path: Path) -> None:
    base = tmp_path / "editorial"
    _create_full_layout(base)
    settings = Settings(
        base_path=base.resolve(),
        api_key="test-secret-key",
        port=8000,
        deployment_environment=None,
    )
    client = TestClient(create_app(settings))

    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert "deployment_environment" not in body
    assert "test-secret-key" not in json.dumps(body)
