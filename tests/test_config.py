"""Tests for configuration loading."""

import os

import pytest

from silverman_blog_linkedin.config import (
    DEFAULT_BASE_PATH,
    DEFAULT_PORT,
    ENV_API_KEY,
    ENV_BASE_PATH,
    ENV_PORT,
    ConfigurationError,
    load_settings,
)


def _minimal_env(**overrides: str) -> dict[str, str]:
    env = {ENV_API_KEY: "test-secret-key"}
    env.update(overrides)
    return env


def test_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    env = _minimal_env()
    settings = load_settings(env)

    assert settings.port == DEFAULT_PORT
    expected_base = (tmp_path / DEFAULT_BASE_PATH.lstrip("./")).resolve()
    assert settings.base_path == expected_base
    assert settings.api_key == "test-secret-key"


def test_env_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path):
    custom_base = tmp_path / "custom-data"
    custom_base.mkdir()
    env = _minimal_env(
        **{
            ENV_BASE_PATH: str(custom_base),
            ENV_PORT: "9000",
            ENV_API_KEY: "override-key",
        }
    )
    settings = load_settings(env)

    assert settings.base_path == custom_base.resolve()
    assert settings.port == 9000
    assert settings.api_key == "override-key"


def test_missing_api_key():
    env = {k: v for k, v in os.environ.items() if k != ENV_API_KEY}
    env.pop(ENV_API_KEY, None)

    with pytest.raises(ConfigurationError, match="API_KEY"):
        load_settings({ENV_BASE_PATH: "/tmp/data"})


def test_empty_api_key():
    with pytest.raises(ConfigurationError, match="API_KEY"):
        load_settings({ENV_API_KEY: "   "})


def test_path_resolution(monkeypatch: pytest.MonkeyPatch, tmp_path):
    relative = tmp_path / "relative" / "base"
    relative.mkdir(parents=True)
    env = _minimal_env(**{ENV_BASE_PATH: str(relative)})
    settings = load_settings(env)

    assert settings.base_path.is_absolute()
    assert settings.base_path == relative.resolve()


def test_invalid_port():
    with pytest.raises(ConfigurationError, match="PORT"):
        load_settings(_minimal_env(**{ENV_PORT: "not-a-number"}))


def test_port_out_of_range():
    with pytest.raises(ConfigurationError, match="PORT"):
        load_settings(_minimal_env(**{ENV_PORT: "0"}))
