"""US-076: Flow B gap operator settings store, loader, and HTTP API."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.flow_b_gap_operator_settings import (
    DEFAULT_DENSITY_MAX_PER_LOCAL_DAY,
    DEFAULT_GAP_TRIGGER_ENABLED,
    DEFAULT_MAX_DRAFTS_PER_WEEKLY_RUN,
    DEFAULT_MIN_LEAD_DAYS,
    ERROR_OPERATOR_TIMEZONE_INVALID,
    documented_defaults,
    load_gap_operator_settings,
    save_gap_operator_settings,
    validate_gap_operator_settings_document,
)
from silverman_blog_linkedin.flow_b_gap_operator_settings_store import (
    MemoryGapOperatorSettingsStore,
    get_gap_operator_settings_store,
)
from silverman_blog_linkedin.linkedin_config import (
    ENV_PUBLICATION_ENABLED,
    load_linkedin_publication_settings,
)
from silverman_blog_linkedin.local_day_density import ENV_OPERATOR_TIMEZONE
from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, make_settings

SETTINGS_PATH = "/flow-b/gap-operator-settings"

VALID_DOCUMENT = {
    "operator_timezone": "America/Chicago",
    "gap_trigger_enabled": False,
    "gap_scan_mode": "next_week",
    "weekly_run_local_day": "friday",
    "weekly_run_local_time": "15:00",
    "min_lead_days": 5,
    "gap_posts_threshold": 0,
    "max_drafts_per_weekly_run": 2,
    "density_max_per_local_day": 2,
}


def test_defaults_when_row_missing(isolate_gap_operator_settings_store) -> None:
    snapshot = load_gap_operator_settings(environ={ENV_OPERATOR_TIMEZONE: "America/Chicago"})
    assert snapshot.source == "defaults"
    assert snapshot.updated_at_utc is None
    assert snapshot.row_version is None
    assert snapshot.settings["gap_trigger_enabled"] is False
    assert snapshot.settings["gap_scan_mode"] == "next_week"
    assert snapshot.settings["weekly_run_local_day"] == "friday"
    assert snapshot.settings["weekly_run_local_time"] == "15:00"
    assert snapshot.settings["min_lead_days"] == DEFAULT_MIN_LEAD_DAYS
    assert snapshot.settings["max_drafts_per_weekly_run"] == DEFAULT_MAX_DRAFTS_PER_WEEKLY_RUN
    assert snapshot.settings["density_max_per_local_day"] == DEFAULT_DENSITY_MAX_PER_LOCAL_DAY
    assert snapshot.settings["operator_timezone"] == "America/Chicago"


def test_defaults_placeholder_timezone_when_env_missing() -> None:
    defaults = documented_defaults(environ={})
    assert defaults["operator_timezone"] == "UTC"
    assert defaults["gap_trigger_enabled"] is DEFAULT_GAP_TRIGGER_ENABLED


def test_round_trip_persist(isolate_gap_operator_settings_store) -> None:
    doc = {
        **VALID_DOCUMENT,
        "max_drafts_per_weekly_run": 1,
        "gap_trigger_enabled": False,
    }
    snapshot, errors = save_gap_operator_settings(doc)
    assert errors == []
    assert snapshot is not None
    assert snapshot.source == "database"
    assert snapshot.settings["max_drafts_per_weekly_run"] == 1

    reloaded = load_gap_operator_settings()
    assert reloaded.source == "database"
    assert reloaded.settings["max_drafts_per_weekly_run"] == 1
    assert reloaded.settings["gap_trigger_enabled"] is False


def test_invalid_timezone_rejected_without_partial_persist(
    isolate_gap_operator_settings_store,
) -> None:
    snapshot, errors = save_gap_operator_settings(
        {**VALID_DOCUMENT, "operator_timezone": "Not/AZone"}
    )
    assert snapshot is None
    assert any(e["code"] == ERROR_OPERATOR_TIMEZONE_INVALID for e in errors)
    assert load_gap_operator_settings().source == "defaults"


def test_negative_integer_rejected() -> None:
    errors = validate_gap_operator_settings_document(
        {**VALID_DOCUMENT, "min_lead_days": -1}
    )
    assert any(e["field"] == "min_lead_days" for e in errors)


def test_get_requires_auth(tmp_path: Path) -> None:
    client = TestClient(create_app(make_settings(tmp_path)))
    assert client.get(SETTINGS_PATH).status_code == 401


def test_get_defaults_when_missing(tmp_path: Path) -> None:
    client = TestClient(create_app(make_settings(tmp_path)))
    response = client.get(SETTINGS_PATH, headers=auth_header())
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "defaults"
    assert body["gap_trigger_enabled"] is False
    assert body["gap_scan_mode"] == "next_week"
    assert body["weekly_run_local_day"] == "friday"
    assert body["weekly_run_local_time"] == "15:00"
    assert body["updated_at_utc"] is None
    _assert_no_secrets(body)


def test_put_round_trip(tmp_path: Path) -> None:
    client = TestClient(create_app(make_settings(tmp_path)))
    put = client.put(
        SETTINGS_PATH,
        headers=auth_header(),
        json={**VALID_DOCUMENT, "max_drafts_per_weekly_run": 1},
    )
    assert put.status_code == 200
    body = put.json()
    assert body["source"] == "database"
    assert body["max_drafts_per_weekly_run"] == 1
    assert body["row_version"] == 1
    _assert_no_secrets(body)

    get = client.get(SETTINGS_PATH, headers=auth_header())
    assert get.status_code == 200
    assert get.json()["max_drafts_per_weekly_run"] == 1


def test_put_invalid_timezone_422(tmp_path: Path) -> None:
    client = TestClient(create_app(make_settings(tmp_path)))
    # Seed a valid row first so we can prove it is unchanged after rejection.
    seed = client.put(SETTINGS_PATH, headers=auth_header(), json=VALID_DOCUMENT)
    assert seed.status_code == 200
    version = seed.json()["row_version"]

    bad = client.put(
        SETTINGS_PATH,
        headers=auth_header(),
        json={**VALID_DOCUMENT, "operator_timezone": "Fake/Zone"},
    )
    assert bad.status_code == 422

    get = client.get(SETTINGS_PATH, headers=auth_header())
    assert get.json()["operator_timezone"] == "America/Chicago"
    assert get.json()["row_version"] == version


def test_put_does_not_enable_linkedin_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_PUBLICATION_ENABLED, "false")
    before = load_linkedin_publication_settings().settings.publication_enabled
    assert before is False

    client = TestClient(create_app(make_settings(tmp_path)))
    response = client.put(
        SETTINGS_PATH,
        headers=auth_header(),
        json={**VALID_DOCUMENT, "gap_trigger_enabled": True},
    )
    assert response.status_code == 200
    assert response.json()["gap_trigger_enabled"] is True

    assert os.environ.get(ENV_PUBLICATION_ENABLED) == "false"
    after = load_linkedin_publication_settings().settings.publication_enabled
    assert after is False
    _assert_no_secrets(response.json())


def test_gap_trigger_disabled_has_no_side_effect_routes(tmp_path: Path) -> None:
    """US-076 must not start trigger/discovery as a side effect of settings.

    `/flow-b/gap-trigger` MAY exist (US-082). Settings save still must not
    start discovery or draft generation by itself.
    """
    app = create_app(make_settings(tmp_path))
    paths = {getattr(route, "path", None) for route in app.routes}
    # Legacy placeholder paths that settings must never introduce.
    forbidden = {
        "/flow-b/draft",
        "/flow-b/approve",
        "/flow-b/promote",
    }
    assert not (paths & forbidden)
    # Saving settings must not create pending-approval drafts (side-effect check).
    pending = tmp_path / "blog-posts" / "pending-approval"
    pending.mkdir(parents=True, exist_ok=True)
    before = {p.name for p in pending.iterdir()}
    client = TestClient(app)
    response = client.put(
        SETTINGS_PATH,
        headers=auth_header(),
        json={**VALID_DOCUMENT, "gap_trigger_enabled": True},
    )
    assert response.status_code == 200
    after = {p.name for p in pending.iterdir()}
    assert after == before


def test_memory_store_isolated_from_calendar(
    isolate_gap_operator_settings_store: MemoryGapOperatorSettingsStore,
) -> None:
    store = get_gap_operator_settings_store()
    assert isinstance(store, MemoryGapOperatorSettingsStore)
    assert store.load()[0] is None


def _assert_no_secrets(body: dict) -> None:
    blob = str(body).lower()
    for needle in (
        "password",
        "api_key",
        "apikey",
        "oauth",
        "token",
        "postgresql://",
        "secret",
    ):
        assert needle not in blob
