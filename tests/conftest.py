"""Shared test fixtures and helpers."""

from pathlib import Path

from silverman_blog_linkedin.config import Settings
from silverman_blog_linkedin.paths import EXPECTED_FOLDERS


def create_full_layout(base: Path) -> None:
    base.mkdir(parents=True, exist_ok=True)
    for relative in EXPECTED_FOLDERS:
        (base / relative).mkdir(parents=True, exist_ok=True)


def make_settings(base: Path, api_key: str = "test-secret-key") -> Settings:
    return Settings(base_path=base.resolve(), api_key=api_key, port=8000)


def auth_header(api_key: str = "test-secret-key") -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}
