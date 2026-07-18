"""Tests for POST /editorial-calendar/update-item-schedule (US-040C)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.editorial_calendar_plan import (
    CALENDAR_COMPLETION_CONCURRENT_UPDATE,
    CALENDAR_ITEM_NOT_FOUND,
    calendar_fingerprint,
    load_calendar,
)
from silverman_blog_linkedin.editorial_calendar_schedule_update import (
    CALENDAR_SCHEDULE_DUPLICATE_SLOT,
    CALENDAR_SCHEDULE_IDEMPOTENCY_CONFLICT,
    CALENDAR_SCHEDULE_TIME_INVALID,
    CALENDAR_SCHEDULE_UNSUPPORTED_STATE,
    RELATED_LINKEDIN_UNCHANGED,
    update_editorial_calendar_item_schedule,
)
from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, create_full_layout, make_settings
from tests.test_editorial_calendar_flow_a_execute import (
    _base_calendar,
    _flow_a_item,
    _write_calendar,
)

NOW = datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc)
FUTURE_DUE = "2026-08-15T14:00:00Z"
OTHER_DAY = "2026-08-20T14:00:00Z"
ITEM_ID = "sched-flow-a"


@pytest.fixture
def editorial_base(tmp_path: Path) -> Path:
    base = tmp_path / "editorial"
    create_full_layout(base)
    ready = base / "blog-posts" / "ready"
    (ready / "post.md").write_text("# Sample\n", encoding="utf-8")
    return base


@pytest.fixture
def calendar_base(editorial_base: Path) -> Path:
    _write_calendar(
        editorial_base,
        _base_calendar(
            items=[
                _flow_a_item(
                    item_id=ITEM_ID,
                    status="scheduled",
                    due_at_utc="2026-08-01T14:00:00Z",
                ),
            ]
        ),
    )
    return editorial_base


@pytest.fixture
def client(calendar_base: Path) -> TestClient:
    return TestClient(create_app(make_settings(calendar_base)))


def test_update_schedule_unauthenticated_rejected(client: TestClient):
    response = client.post(
        "/editorial-calendar/update-item-schedule",
        json={"item_id": ITEM_ID, "new_due_at_utc": FUTURE_DUE},
    )
    assert response.status_code == 401


def test_update_schedule_dry_run_default_does_not_mutate(calendar_base: Path):
    before = (calendar_base / "editorial-calendar" / "calendar.json").read_bytes()
    result = update_editorial_calendar_item_schedule(
        calendar_base,
        item_id=ITEM_ID,
        new_due_at_utc=FUTURE_DUE,
        now=NOW,
    )
    assert result.status == "completed"
    assert result.dry_run is True
    assert result.calendar_written is False
    assert result.previous_due_at_utc == "2026-08-01T14:00:00Z"
    assert result.new_due_at_utc == FUTURE_DUE
    assert (
        calendar_base / "editorial-calendar" / "calendar.json"
    ).read_bytes() == before


def test_update_schedule_real_persists_atomically(calendar_base: Path):
    fingerprint = calendar_fingerprint(calendar_base)
    result = update_editorial_calendar_item_schedule(
        calendar_base,
        item_id=ITEM_ID,
        new_due_at_utc=FUTURE_DUE,
        dry_run=False,
        reason="operator_choice",
        actor="operator",
        source="linkedin_variant_supervision_console",
        idempotency_key="sched-1",
        expected_calendar_fingerprint=fingerprint,
        now=NOW,
    )
    assert result.status == "completed"
    assert result.dry_run is False
    assert result.calendar_written is True
    assert result.related_linkedin_variants_outcome == RELATED_LINKEDIN_UNCHANGED
    assert result.audit is not None
    assert result.audit["previous_due_at_utc"] == "2026-08-01T14:00:00Z"
    assert result.audit["new_due_at_utc"] == FUTURE_DUE
    assert result.audit["source"] == "linkedin_variant_supervision_console"

    calendar, _ = load_calendar(calendar_base)
    assert calendar is not None
    item = next(i for i in calendar["items"] if i["item_id"] == ITEM_ID)
    assert item["due_at_utc"] == FUTURE_DUE
    assert len(item["schedule_change_history"]) == 1
    assert item["schedule_change_history"][0]["idempotency_key"] == "sched-1"


def test_update_schedule_concurrent_fingerprint_conflict(calendar_base: Path):
    result = update_editorial_calendar_item_schedule(
        calendar_base,
        item_id=ITEM_ID,
        new_due_at_utc=FUTURE_DUE,
        dry_run=False,
        expected_calendar_fingerprint="0" * 64,
        now=NOW,
    )
    assert result.status == "failed"
    assert CALENDAR_COMPLETION_CONCURRENT_UPDATE in result.errors
    calendar, _ = load_calendar(calendar_base)
    assert calendar is not None
    item = next(i for i in calendar["items"] if i["item_id"] == ITEM_ID)
    assert item["due_at_utc"] == "2026-08-01T14:00:00Z"


def test_update_schedule_completed_unsupported(calendar_base: Path):
    _write_calendar(
        calendar_base,
        _base_calendar(
            items=[
                _flow_a_item(
                    item_id=ITEM_ID,
                    status="completed",
                    due_at_utc="2026-08-01T14:00:00Z",
                ),
            ]
        ),
    )
    result = update_editorial_calendar_item_schedule(
        calendar_base,
        item_id=ITEM_ID,
        new_due_at_utc=FUTURE_DUE,
        dry_run=False,
        now=NOW,
    )
    assert result.status == "failed"
    assert CALENDAR_SCHEDULE_UNSUPPORTED_STATE in result.errors


def test_update_schedule_past_time_rejected(calendar_base: Path):
    result = update_editorial_calendar_item_schedule(
        calendar_base,
        item_id=ITEM_ID,
        new_due_at_utc="2026-07-01T14:00:00Z",
        dry_run=False,
        now=NOW,
    )
    assert result.status == "failed"
    assert CALENDAR_SCHEDULE_TIME_INVALID in result.errors


def test_update_schedule_duplicate_day_rejected(calendar_base: Path):
    _write_calendar(
        calendar_base,
        _base_calendar(
            items=[
                _flow_a_item(
                    item_id=ITEM_ID,
                    status="scheduled",
                    due_at_utc="2026-08-01T14:00:00Z",
                ),
                _flow_a_item(
                    item_id="other-item",
                    status="planned",
                    due_at_utc="2026-08-15T10:00:00Z",
                ),
            ]
        ),
    )
    before = (calendar_base / "editorial-calendar" / "calendar.json").read_bytes()
    result = update_editorial_calendar_item_schedule(
        calendar_base,
        item_id=ITEM_ID,
        new_due_at_utc=FUTURE_DUE,
        dry_run=False,
        now=NOW,
    )
    assert result.status == "failed"
    assert CALENDAR_SCHEDULE_DUPLICATE_SLOT in result.errors
    assert (
        calendar_base / "editorial-calendar" / "calendar.json"
    ).read_bytes() == before


def test_update_schedule_idempotent_replay(calendar_base: Path):
    fingerprint = calendar_fingerprint(calendar_base)
    first = update_editorial_calendar_item_schedule(
        calendar_base,
        item_id=ITEM_ID,
        new_due_at_utc=FUTURE_DUE,
        dry_run=False,
        idempotency_key="replay-key",
        expected_calendar_fingerprint=fingerprint,
        now=NOW,
    )
    assert first.status == "completed"
    assert first.calendar_written is True

    second = update_editorial_calendar_item_schedule(
        calendar_base,
        item_id=ITEM_ID,
        new_due_at_utc=FUTURE_DUE,
        dry_run=False,
        idempotency_key="replay-key",
        now=NOW,
    )
    assert second.status == "completed"
    assert second.idempotency_result == "replay"
    assert second.calendar_written is False
    calendar, _ = load_calendar(calendar_base)
    assert calendar is not None
    item = next(i for i in calendar["items"] if i["item_id"] == ITEM_ID)
    assert len(item["schedule_change_history"]) == 1


def test_update_schedule_idempotency_conflict(calendar_base: Path):
    fingerprint = calendar_fingerprint(calendar_base)
    first = update_editorial_calendar_item_schedule(
        calendar_base,
        item_id=ITEM_ID,
        new_due_at_utc=FUTURE_DUE,
        dry_run=False,
        idempotency_key="conflict-key",
        expected_calendar_fingerprint=fingerprint,
        now=NOW,
    )
    assert first.status == "completed"

    second = update_editorial_calendar_item_schedule(
        calendar_base,
        item_id=ITEM_ID,
        new_due_at_utc=OTHER_DAY,
        dry_run=False,
        idempotency_key="conflict-key",
        now=NOW,
    )
    assert second.status == "failed"
    assert CALENDAR_SCHEDULE_IDEMPOTENCY_CONFLICT in second.errors


def test_update_schedule_item_not_found(calendar_base: Path):
    result = update_editorial_calendar_item_schedule(
        calendar_base,
        item_id="missing-item",
        new_due_at_utc=FUTURE_DUE,
        dry_run=False,
        now=NOW,
    )
    assert result.status == "failed"
    assert CALENDAR_ITEM_NOT_FOUND in result.errors


def test_update_schedule_http_dry_run_and_secrets_safe(client: TestClient):
    response = client.post(
        "/editorial-calendar/update-item-schedule",
        headers=auth_header(),
        json={"item_id": ITEM_ID, "new_due_at_utc": FUTURE_DUE},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["dry_run"] is True
    dumped = json.dumps(body)
    assert "api_key" not in dumped.lower()
    assert "token" not in dumped.lower() or "idempotency" in dumped.lower()


def test_update_schedule_same_item_may_move_within_day(calendar_base: Path):
    """Rescheduling the same item to another time on an empty day is allowed."""
    fingerprint = calendar_fingerprint(calendar_base)
    result = update_editorial_calendar_item_schedule(
        calendar_base,
        item_id=ITEM_ID,
        new_due_at_utc="2026-08-01T18:00:00Z",
        dry_run=False,
        expected_calendar_fingerprint=fingerprint,
        now=NOW,
    )
    assert result.status == "completed"
    calendar, _ = load_calendar(calendar_base)
    assert calendar is not None
    item = next(i for i in calendar["items"] if i["item_id"] == ITEM_ID)
    assert item["due_at_utc"] == "2026-08-01T18:00:00Z"
