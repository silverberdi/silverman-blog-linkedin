"""Shared test fixtures and helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from silverman_blog_linkedin.comfyui_config import (
    ENV_API_KEY,
    ENV_API_PREFIX,
    ENV_AUTH_HEADER_NAME,
    ENV_BASE_URL,
    ENV_DRY_RUN,
    ENV_EXTRA_DATA_API_KEY_FIELD,
    ENV_IMAGE_ENABLED,
    ENV_IMAGE_HEIGHT,
    ENV_IMAGE_WIDTH,
    ENV_TIMEOUT_SECONDS,
    ENV_WORKFLOW_PATH,
)
from silverman_blog_linkedin.config import Settings
from silverman_blog_linkedin.editorial_calendar_store import (
    ENV_CALENDAR_DATABASE_URL,
    MemoryCalendarStore,
    reset_calendar_store_for_tests,
)
from silverman_blog_linkedin.flow_b_gap_operator_settings_store import (
    MemoryGapOperatorSettingsStore,
    reset_gap_operator_settings_store_for_tests,
)
from silverman_blog_linkedin.paths import EXPECTED_FOLDERS

COMFYUI_ENV_VARS: tuple[str, ...] = (
    ENV_IMAGE_ENABLED,
    ENV_BASE_URL,
    ENV_API_PREFIX,
    ENV_API_KEY,
    ENV_AUTH_HEADER_NAME,
    ENV_EXTRA_DATA_API_KEY_FIELD,
    ENV_WORKFLOW_PATH,
    ENV_TIMEOUT_SECONDS,
    ENV_IMAGE_WIDTH,
    ENV_IMAGE_HEIGHT,
    ENV_DRY_RUN,
)


def clear_comfyui_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove ComfyUI env vars so tests do not inherit the operator shell."""
    for name in COMFYUI_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def isolate_comfyui_env(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_comfyui_env(monkeypatch)


@pytest.fixture(autouse=True)
def isolate_calendar_store(monkeypatch: pytest.MonkeyPatch) -> MemoryCalendarStore:
    """Use an isolated in-memory calendar store for every test."""
    monkeypatch.setenv(ENV_CALENDAR_DATABASE_URL, "memory://")
    store = MemoryCalendarStore()
    reset_calendar_store_for_tests(store)
    yield store
    reset_calendar_store_for_tests(None)


@pytest.fixture(autouse=True)
def isolate_gap_operator_settings_store(
    monkeypatch: pytest.MonkeyPatch,
) -> MemoryGapOperatorSettingsStore:
    """Use an isolated in-memory Flow B gap settings store for every test."""
    monkeypatch.setenv(ENV_CALENDAR_DATABASE_URL, "memory://")
    store = MemoryGapOperatorSettingsStore()
    reset_gap_operator_settings_store_for_tests(store)
    yield store
    reset_gap_operator_settings_store_for_tests(None)


@pytest.fixture(autouse=True)
def isolate_gap_trigger_batch_store(
    monkeypatch: pytest.MonkeyPatch,
) -> "MemoryGapTriggerBatchStore":
    """Use an isolated in-memory Flow B gap-trigger batch store for every test."""
    from silverman_blog_linkedin.flow_b_gap_trigger_batch_store import (
        MemoryGapTriggerBatchStore,
        reset_gap_trigger_batch_store_for_tests,
    )

    monkeypatch.setenv(ENV_CALENDAR_DATABASE_URL, "memory://")
    store = MemoryGapTriggerBatchStore()
    reset_gap_trigger_batch_store_for_tests(store)
    yield store
    reset_gap_trigger_batch_store_for_tests(None)


@pytest.fixture(autouse=True)
def default_operator_timezone(monkeypatch: pytest.MonkeyPatch) -> None:
    """US-040K: density-gated mutations need a valid TZ (request or env).

    Baseline tests rely on env fallback; density-specific tests that assert
    fail-closed missing TZ pass ``environ={}`` explicitly.
    """
    from silverman_blog_linkedin.local_day_density import ENV_OPERATOR_TIMEZONE

    monkeypatch.setenv(ENV_OPERATOR_TIMEZONE, "America/Chicago")


def seed_editorial_calendar(payload: dict[str, Any]) -> None:
    """Replace the test calendar store contents with a validated document."""
    from silverman_blog_linkedin.editorial_calendar_store import get_calendar_store

    store = get_calendar_store()
    force = getattr(store, "force_replace", None)
    if not callable(force):
        raise RuntimeError("test calendar store does not support force_replace")
    errors = force(payload)
    if errors:
        raise AssertionError(f"seed_editorial_calendar failed: {errors}")


def inject_unvalidated_calendar(payload: dict[str, Any]) -> None:
    """Inject calendar JSON into the memory store without validation (negative tests)."""
    from copy import deepcopy

    from silverman_blog_linkedin.editorial_calendar_store import (
        MemoryCalendarStore,
        _MemoryState,
        canonical_calendar_digest,
        get_calendar_store,
    )

    store = get_calendar_store()
    if not isinstance(store, MemoryCalendarStore):
        raise RuntimeError("inject_unvalidated_calendar requires MemoryCalendarStore")
    document = deepcopy(payload)
    if "updated_at_utc" not in document:
        document["updated_at_utc"] = "2026-07-09T20:00:00Z"
    if "schema_version" not in document:
        document["schema_version"] = "1"
    # Digest best-effort for concurrency tests; invalid shapes still load for validation.
    try:
        digest = canonical_calendar_digest(
            {
                "schema_version": document.get("schema_version"),
                "updated_at_utc": document.get("updated_at_utc"),
                "items": document.get("items", [])
                if isinstance(document.get("items"), list)
                else [],
            }
        )
    except Exception:
        digest = "0" * 64
    store._state = _MemoryState(
        document=document,
        row_version=1,
        content_sha256=digest,
    )


def write_and_seed_calendar(base: Path, payload: dict[str, Any]) -> Path:
    """Write optional legacy calendar.json and seed the DB/memory store (test helper)."""
    import json

    calendar_dir = base / "editorial-calendar"
    calendar_dir.mkdir(parents=True, exist_ok=True)
    path = calendar_dir / "calendar.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    seed_editorial_calendar(payload)
    return path


def create_full_layout(base: Path) -> None:
    base.mkdir(parents=True, exist_ok=True)
    for relative in EXPECTED_FOLDERS:
        (base / relative).mkdir(parents=True, exist_ok=True)


def make_settings(base: Path, api_key: str = "test-secret-key") -> Settings:
    return Settings(base_path=base.resolve(), api_key=api_key, port=8000)


def auth_header(api_key: str = "test-secret-key") -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}
