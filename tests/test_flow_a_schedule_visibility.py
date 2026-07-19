"""Behavioral tests for US-040B Flow A schedule-visibility read aggregation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.flow_a_schedule_visibility import (
    DISPLAY_BLOCKED,
    DISPLAY_DEFERRED,
    DISPLAY_FAILED,
    DISPLAY_PENDING,
    DISPLAY_PLANNED,
    DISPLAY_PUBLISHED,
    DISPLAY_QUEUED,
    get_flow_a_schedule_visibility,
)
from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, make_settings, write_and_seed_calendar

CAMPAIGN_ID = "flow-a-2026-07-18-schedule-visibility"
SCHEDULE_API = "/flow-a/schedule-visibility"
PENDING_API = "/flow-a/linkedin-variants/pending-supervision"


@pytest.fixture
def schedule_base(tmp_path: Path) -> Path:
    base = tmp_path / "editorial"
    for relative in (
        "metadata/campaigns",
        "editorial-calendar",
        "blog-posts/ready",
        "linkedin-posts/generated",
    ):
        (base / relative).mkdir(parents=True, exist_ok=True)
    return base


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _variant(
    variant_id: str,
    *,
    publish_state: str = "pending",
    audience: str = "senior practitioners",
    scheduled_at_utc: str = "2026-07-20T14:00:00Z",
    **extra: object,
) -> dict:
    return {
        "variant": variant_id,
        "audience": audience,
        "publish_state": publish_state,
        "scheduled_at_utc": scheduled_at_utc,
        **extra,
    }


def _write_campaign(
    base: Path,
    campaign_id: str = CAMPAIGN_ID,
    *,
    variants: list[dict] | None = None,
    flow: str = "flow_a",
) -> Path:
    payload = {
        "campaign_id": campaign_id,
        "flow": flow,
        "state": "distribution_scheduled",
        "updated_at": "2026-07-18T10:00:00Z",
        "source_file_status": {
            "location": "processed",
            "execution_state": "idle",
            "recovery_classification": "no_action",
        },
        "variants": [] if variants is None else variants,
    }
    return _write_json(base / "metadata/campaigns" / f"{campaign_id}.json", payload)


def _write_calendar(base: Path, items: list[dict]) -> Path:
    return write_and_seed_calendar(
        base,
        {
            "schema_version": "1",
            "updated_at_utc": "2026-07-18T09:00:00Z",
            "items": items,
        },
    )


def _calendar_item(
    item_id: str,
    *,
    campaign_id: str | None = CAMPAIGN_ID,
    due_at_utc: str = "2026-07-19T11:00:00Z",
    status: str = "scheduled",
    title: str | None = None,
) -> dict:
    item = {
        "item_id": item_id,
        "title": title or f"Item {item_id}",
        "status": status,
        "due_at_utc": due_at_utc,
        "source_folder": "blog-posts/ready",
        "source_relative_path": f"blog-posts/ready/{item_id}.md",
        "flow_type": "flow_a_ready_blog_post",
        "content_mode": "user_provided_approved_blog",
        "target_audience": "executive-recruiter",
        "topic_theme": "architecture",
    }
    if campaign_id is not None:
        item["campaign_id"] = campaign_id
    return item


def _snapshot_tree(base: Path) -> dict[str, tuple[bytes, int]]:
    return {
        str(path.relative_to(base)): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in sorted(base.rglob("*"))
        if path.is_file()
    }


def test_auth_rejection_without_api_key(schedule_base: Path):
    client = TestClient(create_app(make_settings(schedule_base)))
    response = client.get(SCHEDULE_API, params={"year": 2026, "month": 7})
    assert response.status_code == 401


def test_happy_path_blog_and_linkedin_items(schedule_base: Path):
    _write_calendar(
        schedule_base,
        [
            _calendar_item(
                "blog-july-19",
                due_at_utc="2026-07-19T11:00:00Z",
                status="planned",
            ),
            _calendar_item(
                "blog-completed",
                due_at_utc="2026-07-22T09:00:00Z",
                status="completed",
                title="Completed handoff post",
            ),
        ],
    )
    _write_campaign(
        schedule_base,
        variants=[
            _variant("engineering-leadership", publish_state="pending"),
            _variant(
                "executive-recruiter",
                publish_state="queued",
                scheduled_at_utc="2026-07-21T16:00:00Z",
            ),
            _variant(
                "published-variant",
                publish_state="published",
                scheduled_at_utc="2026-07-10T12:00:00Z",
            ),
            _variant(
                "failed-variant",
                publish_state="failed",
                scheduled_at_utc="2026-07-15T08:00:00Z",
                linkedin_publication={
                    "last_error_code": "linkedin_http_error",
                    "http_status": 503,
                },
            ),
            _variant(
                "deferred-variant",
                publish_state="pending",
                scheduled_at_utc="2026-07-25T10:00:00Z",
                operator_supervision={
                    "last_action": "defer",
                    "auto_queue_eligible": False,
                    "reason": "operator defer",
                },
            ),
            _variant(
                "outside-month",
                publish_state="pending",
                scheduled_at_utc="2026-08-01T10:00:00Z",
            ),
        ],
    )

    result = get_flow_a_schedule_visibility(
        schedule_base, year=2026, month=7, environ={"SILVERMAN_LINKEDIN_PUBLICATION_ENABLED": "true"}
    )
    assert result.status == "ok"
    assert result.read_only is True
    assert result.year == 2026
    assert result.month == 7

    by_id = {item.item_id: item for item in result.items}
    assert "blog:blog-july-19" in by_id
    blog = by_id["blog:blog-july-19"]
    assert blog.channel == "blog"
    assert blog.publication_state == DISPLAY_PLANNED
    assert blog.linkedin_api_published is False
    assert blog.scheduled_at_utc == "2026-07-19T11:00:00Z"

    completed = by_id["blog:blog-completed"]
    assert completed.publication_state == DISPLAY_PLANNED
    assert completed.source_state == "completed"
    assert completed.linkedin_api_published is False
    assert "not LinkedIn API published" in (completed.title or "")

    pending = by_id["linkedin:flow-a-2026-07-18-schedule-visibility:engineering-leadership"]
    assert pending.publication_state == DISPLAY_PENDING
    assert pending.linkedin_api_published is False

    queued = by_id["linkedin:flow-a-2026-07-18-schedule-visibility:executive-recruiter"]
    assert queued.publication_state == DISPLAY_QUEUED
    assert queued.linkedin_api_published is False

    published = by_id["linkedin:flow-a-2026-07-18-schedule-visibility:published-variant"]
    assert published.publication_state == DISPLAY_PUBLISHED
    assert published.linkedin_api_published is True

    failed = by_id["linkedin:flow-a-2026-07-18-schedule-visibility:failed-variant"]
    assert failed.publication_state == DISPLAY_FAILED
    assert failed.critical is True
    assert failed.linkedin_api_published is False

    deferred = by_id["linkedin:flow-a-2026-07-18-schedule-visibility:deferred-variant"]
    assert deferred.publication_state == DISPLAY_DEFERRED

    assert "linkedin:flow-a-2026-07-18-schedule-visibility:outside-month" not in by_id


def test_empty_calendar_still_returns_linkedin_items(schedule_base: Path):
    _write_campaign(
        schedule_base,
        variants=[_variant("engineering-leadership")],
    )
    result = get_flow_a_schedule_visibility(
        schedule_base,
        year=2026,
        month=7,
        environ={"SILVERMAN_LINKEDIN_PUBLICATION_ENABLED": "true"},
    )
    assert result.status == "ok"
    assert result.issues == []
    assert len(result.items) == 1
    assert result.items[0].channel == "linkedin"


def test_month_windowing_excludes_other_months(schedule_base: Path):
    _write_calendar(
        schedule_base,
        [
            _calendar_item("in-month", due_at_utc="2026-07-31T23:00:00Z"),
            _calendar_item("next-month", due_at_utc="2026-08-01T00:00:00Z"),
            _calendar_item("prev-month", due_at_utc="2026-06-30T23:59:59Z"),
        ],
    )
    _write_campaign(schedule_base, variants=[])
    result = get_flow_a_schedule_visibility(schedule_base, year=2026, month=7)
    ids = {item.calendar_item_id for item in result.items if item.channel == "blog"}
    assert ids == {"in-month"}


def test_enablement_off_maps_pending_to_blocked_without_published_claim(
    schedule_base: Path,
):
    _write_campaign(
        schedule_base,
        variants=[_variant("engineering-leadership", publish_state="pending")],
    )
    result = get_flow_a_schedule_visibility(
        schedule_base,
        year=2026,
        month=7,
        environ={"SILVERMAN_LINKEDIN_PUBLICATION_ENABLED": "false"},
    )
    assert len(result.items) == 1
    item = result.items[0]
    assert item.publication_state == DISPLAY_BLOCKED
    assert item.blocked is True
    assert item.linkedin_api_published is False


def test_read_does_not_mutate_files(schedule_base: Path):
    _write_calendar(
        schedule_base,
        [_calendar_item("blog-july-19")],
    )
    _write_campaign(
        schedule_base,
        variants=[_variant("engineering-leadership")],
    )
    before = _snapshot_tree(schedule_base)
    first = get_flow_a_schedule_visibility(schedule_base, year=2026, month=7)
    after_first = _snapshot_tree(schedule_base)
    second = get_flow_a_schedule_visibility(schedule_base, year=2026, month=7)
    after_second = _snapshot_tree(schedule_base)
    assert before == after_first == after_second
    assert first.to_dict()["items"] == second.to_dict()["items"]


def test_http_happy_path_and_pending_supervision_unchanged(
    schedule_base: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("SILVERMAN_LINKEDIN_PUBLICATION_ENABLED", "true")
    _write_calendar(
        schedule_base,
        [_calendar_item("blog-july-19")],
    )
    _write_campaign(
        schedule_base,
        variants=[
            _variant("engineering-leadership", publish_state="pending"),
            _variant(
                "queued-variant",
                publish_state="queued",
                scheduled_at_utc="2026-07-22T12:00:00Z",
            ),
        ],
    )
    client = TestClient(create_app(make_settings(schedule_base)))
    headers = auth_header()

    schedule = client.get(
        SCHEDULE_API, params={"year": 2026, "month": 7}, headers=headers
    )
    assert schedule.status_code == 200
    body = schedule.json()
    assert body["read_only"] is True
    assert body["year"] == 2026
    assert body["month"] == 7
    channels = {item["channel"] for item in body["items"]}
    assert channels == {"blog", "linkedin"}
    states = {item["publication_state"] for item in body["items"]}
    assert DISPLAY_PLANNED in states
    assert DISPLAY_PENDING in states
    assert DISPLAY_QUEUED in states

    pending = client.get(PENDING_API, headers=headers)
    assert pending.status_code == 200
    pending_body = pending.json()
    assert len(pending_body["variants"]) == 1
    assert pending_body["variants"][0]["publish_state"] == "pending"
    assert pending_body["variants"][0]["variant_id"] == "engineering-leadership"


def test_schedule_editable_hints_and_fingerprint(schedule_base: Path):
    _write_calendar(
        schedule_base,
        [
            _calendar_item(
                "blog-editable",
                due_at_utc="2026-07-19T11:00:00Z",
                status="scheduled",
            ),
            _calendar_item(
                "blog-completed",
                due_at_utc="2026-07-22T09:00:00Z",
                status="completed",
            ),
        ],
    )
    _write_campaign(
        schedule_base,
        variants=[
            _variant("engineering-leadership", publish_state="pending"),
            _variant(
                "queued-variant",
                publish_state="queued",
                scheduled_at_utc="2026-07-21T16:00:00Z",
            ),
            _variant(
                "published-variant",
                publish_state="published",
                scheduled_at_utc="2026-07-10T12:00:00Z",
            ),
        ],
    )
    before = _snapshot_tree(schedule_base)
    result = get_flow_a_schedule_visibility(schedule_base, year=2026, month=7)
    after = _snapshot_tree(schedule_base)
    assert before == after
    assert result.calendar_fingerprint is not None
    assert len(result.calendar_fingerprint) == 64

    by_id = {item.item_id: item for item in result.items}
    assert by_id["blog:blog-editable"].schedule_editable is True
    assert by_id["blog:blog-editable"].schedule_edit_block_reason is None
    assert by_id["blog:blog-completed"].schedule_editable is False
    assert by_id["blog:blog-completed"].schedule_edit_block_reason == (
        "calendar_schedule_unsupported_state"
    )
    pending = by_id[f"linkedin:{CAMPAIGN_ID}:engineering-leadership"]
    assert pending.schedule_editable is True
    queued = by_id[f"linkedin:{CAMPAIGN_ID}:queued-variant"]
    assert queued.schedule_editable is False
    published = by_id[f"linkedin:{CAMPAIGN_ID}:published-variant"]
    assert published.schedule_editable is False
    # US-040B baseline fields remain present.
    assert pending.channel == "linkedin"
    assert pending.linkedin_api_published is False
    assert published.linkedin_api_published is True
