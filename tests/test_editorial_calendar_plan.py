"""Tests for read-only editorial calendar planning."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.editorial_calendar_plan import (
    CALENDAR_AMBIGUOUS_SOURCE_SELECTION,
    CALENDAR_FILE_NOT_FOUND,
    CALENDAR_INVALID_FLOW_POLICY,
    CALENDAR_ITEM_OVERDUE_BUT_PLANNED,
    CALENDAR_SCHEMA_INVALID,
    FLOW_A_PLANNED_STEPS,
    FLOW_B_PLANNED_STEPS,
    get_editorial_calendar_status,
    plan_editorial_calendar_due,
    plan_result_to_comparable_dict,
)
from silverman_blog_linkedin.main import create_app
from silverman_blog_linkedin.paths import EXPECTED_FOLDERS
from tests.conftest import auth_header, create_full_layout, make_settings

NOW_UTC = "2026-07-09T20:00:00Z"
FUTURE_UTC = "2026-12-01T14:00:00Z"
PAST_UTC = "2026-07-01T14:00:00Z"


def _write_calendar(base: Path, payload: dict) -> Path:
    calendar_dir = base / "editorial-calendar"
    calendar_dir.mkdir(parents=True, exist_ok=True)
    path = calendar_dir / "calendar.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _base_calendar(*, items: list[dict]) -> dict:
    return {
        "schema_version": "1",
        "updated_at_utc": "2026-07-09T20:00:00Z",
        "items": items,
    }


def _flow_a_item(
    *,
    item_id: str = "due-flow-a",
    status: str = "scheduled",
    due_at_utc: str = PAST_UTC,
    source_relative_path: str | None = "blog-posts/ready/post.md",
    source_selection_mode: str | None = None,
) -> dict:
    item: dict = {
        "item_id": item_id,
        "title": "Flow A sample",
        "status": status,
        "due_at_utc": due_at_utc,
        "source_folder": "blog-posts/ready",
        "flow_type": "flow_a_ready_blog_post",
        "content_mode": "user_provided_approved_blog",
        "target_audience": "executive-recruiter",
        "topic_theme": "architecture",
    }
    if source_relative_path is not None:
        item["source_relative_path"] = source_relative_path
    if source_selection_mode is not None:
        item["source_selection_mode"] = source_selection_mode
    return item


@pytest.fixture
def editorial_base(tmp_path: Path) -> Path:
    base = tmp_path / "editorial"
    create_full_layout(base)
    ready = base / "blog-posts" / "ready"
    (ready / "post.md").write_text("# Sample\n", encoding="utf-8")
    return base


def test_missing_calendar_returns_calendar_missing(editorial_base: Path):
    result = plan_editorial_calendar_due(editorial_base, now_utc=NOW_UTC)

    assert result.status == "calendar_missing"
    assert result.errors == [CALENDAR_FILE_NOT_FOUND]
    assert result.read_only is True
    assert result.due_items == []


def test_missing_calendar_status_endpoint_shape(editorial_base: Path):
    result = get_editorial_calendar_status(editorial_base)

    assert result.status == "calendar_missing"
    assert result.calendar_present is False
    assert result.errors == [CALENDAR_FILE_NOT_FOUND]


def test_invalid_calendar_shape(editorial_base: Path):
    _write_calendar(editorial_base, {"schema_version": "1"})

    result = plan_editorial_calendar_due(editorial_base, now_utc=NOW_UTC)

    assert result.status == "calendar_invalid"
    assert CALENDAR_SCHEMA_INVALID in result.errors


def test_no_due_items(editorial_base: Path):
    _write_calendar(
        editorial_base,
        _base_calendar(
            items=[
                _flow_a_item(
                    status="scheduled",
                    due_at_utc=FUTURE_UTC,
                )
            ]
        ),
    )

    result = plan_editorial_calendar_due(editorial_base, now_utc=NOW_UTC)

    assert result.status == "no_due_items"
    assert result.due_items == []


def test_one_due_flow_a_item_with_explicit_path(editorial_base: Path):
    _write_calendar(
        editorial_base,
        _base_calendar(items=[_flow_a_item()]),
    )

    result = plan_editorial_calendar_due(editorial_base, now_utc=NOW_UTC)

    assert result.status == "completed"
    assert len(result.due_items) == 1
    plan = result.due_items[0]
    assert plan.selection_status == "selected"
    assert plan.source_relative_path == "blog-posts/ready/post.md"
    assert plan.review_required is False
    assert plan.planned_flow_steps == list(FLOW_A_PLANNED_STEPS)


def test_future_item_not_in_due_items(editorial_base: Path):
    _write_calendar(
        editorial_base,
        _base_calendar(
            items=[
                _flow_a_item(status="scheduled", due_at_utc=FUTURE_UTC),
                _flow_a_item(item_id="due-now"),
            ]
        ),
    )

    result = plan_editorial_calendar_due(editorial_base, now_utc=NOW_UTC)

    assert len(result.due_items) == 1
    assert result.due_items[0].item_id == "due-now"


def test_ambiguous_folder_rejected(editorial_base: Path):
    ready = editorial_base / "blog-posts" / "ready"
    (ready / "second.md").write_text("# Second\n", encoding="utf-8")

    _write_calendar(
        editorial_base,
        _base_calendar(
            items=[
                _flow_a_item(
                    source_relative_path=None,
                    source_selection_mode="single_markdown_in_folder",
                )
            ]
        ),
    )

    result = plan_editorial_calendar_due(editorial_base, now_utc=NOW_UTC)

    assert result.status == "partial"
    plan = result.due_items[0]
    assert plan.selection_status == "rejected"
    assert CALENDAR_AMBIGUOUS_SOURCE_SELECTION in plan.errors


def test_ambiguous_empty_folder_rejected(editorial_base: Path):
    ready = editorial_base / "blog-posts" / "ready"
    (ready / "post.md").unlink()

    _write_calendar(
        editorial_base,
        _base_calendar(
            items=[
                _flow_a_item(
                    source_relative_path=None,
                    source_selection_mode="single_markdown_in_folder",
                )
            ]
        ),
    )

    result = plan_editorial_calendar_due(editorial_base, now_utc=NOW_UTC)

    plan = result.due_items[0]
    assert plan.selection_status == "rejected"
    assert CALENDAR_AMBIGUOUS_SOURCE_SELECTION in plan.errors


def test_system_generated_source_material_requires_review(editorial_base: Path):
    item = _flow_a_item()
    item["content_mode"] = "system_generated_source_material"
    item["flow_type"] = "flow_b_source_material"
    _write_calendar(editorial_base, _base_calendar(items=[item]))

    result = plan_editorial_calendar_due(editorial_base, now_utc=NOW_UTC)

    plan = result.due_items[0]
    assert plan.review_required is True
    assert plan.planned_flow_steps == list(FLOW_B_PLANNED_STEPS)
    assert "publish_blog" not in plan.planned_flow_steps


def test_overdue_planned_emits_warning_not_selected(editorial_base: Path):
    _write_calendar(
        editorial_base,
        _base_calendar(
            items=[
                _flow_a_item(status="planned", due_at_utc=PAST_UTC),
            ]
        ),
    )

    result = plan_editorial_calendar_due(editorial_base, now_utc=NOW_UTC)

    assert result.status == "no_due_items"
    assert CALENDAR_ITEM_OVERDUE_BUT_PLANNED in result.warnings


def test_idempotent_read_only(editorial_base: Path):
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))
    campaigns_dir = editorial_base / "metadata" / "campaigns"
    before_campaigns = list(campaigns_dir.glob("*.json"))
    calendar_path = editorial_base / "editorial-calendar" / "calendar.json"
    calendar_mtime = calendar_path.stat().st_mtime

    first = plan_editorial_calendar_due(editorial_base, now_utc=NOW_UTC)
    second = plan_editorial_calendar_due(editorial_base, now_utc=NOW_UTC)

    assert plan_result_to_comparable_dict(first) == plan_result_to_comparable_dict(
        second
    )
    assert list(campaigns_dir.glob("*.json")) == before_campaigns
    assert calendar_path.stat().st_mtime == calendar_mtime


def test_invalid_flow_policy_rejected(editorial_base: Path):
    item = _flow_a_item()
    item["flow_type"] = "flow_b_source_material"
    _write_calendar(editorial_base, _base_calendar(items=[item]))

    result = plan_editorial_calendar_due(editorial_base, now_utc=NOW_UTC)

    plan = result.due_items[0]
    assert plan.selection_status == "rejected"
    assert CALENDAR_INVALID_FLOW_POLICY in plan.errors


def test_http_plan_due_requires_auth(editorial_base: Path):
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))
    client = TestClient(create_app(make_settings(editorial_base)))

    unauth = client.post("/editorial-calendar/plan-due", json={})
    assert unauth.status_code == 401

    bad_key = client.post(
        "/editorial-calendar/plan-due",
        headers={"Authorization": "Bearer wrong-key"},
        json={},
    )
    assert bad_key.status_code == 401


def test_http_plan_due_success_shape(editorial_base: Path):
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))
    client = TestClient(create_app(make_settings(editorial_base)))

    response = client.post(
        "/editorial-calendar/plan-due",
        headers=auth_header(),
        json={"now_utc": NOW_UTC},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["now_utc"] == NOW_UTC
    assert body["read_only"] is True
    assert len(body["due_items"]) == 1
    assert "errors" in body
    assert "warnings" in body
    assert "markdown_content" not in json.dumps(body)


def test_http_plan_due_invalid_body_422(editorial_base: Path):
    client = TestClient(create_app(make_settings(editorial_base)))

    response = client.post(
        "/editorial-calendar/plan-due",
        headers=auth_header(),
        json={"unexpected": "field"},
    )
    assert response.status_code == 422


def test_http_plan_due_invalid_now_utc_422(editorial_base: Path):
    client = TestClient(create_app(make_settings(editorial_base)))

    for invalid_now in ("not-a-timestamp", "2026-07-09T20:00:00", ""):
        response = client.post(
            "/editorial-calendar/plan-due",
            headers=auth_header(),
            json={"now_utc": invalid_now},
        )
        assert response.status_code == 422


def test_http_status_requires_auth(editorial_base: Path):
    client = TestClient(create_app(make_settings(editorial_base)))

    assert client.get("/editorial-calendar/status").status_code == 401


def test_http_status_ok_with_calendar(editorial_base: Path):
    _write_calendar(
        editorial_base,
        _base_calendar(
            items=[
                _flow_a_item(status="planned", due_at_utc=FUTURE_UTC),
                _flow_a_item(item_id="scheduled-one", status="scheduled"),
            ]
        ),
    )
    client = TestClient(create_app(make_settings(editorial_base)))

    response = client.get("/editorial-calendar/status", headers=auth_header())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["calendar_present"] is True
    assert body["schema_version"] == "1"
    assert body["item_counts_by_status"]["planned"] == 1
    assert body["item_counts_by_status"]["scheduled"] == 1


def test_http_calendar_missing_when_file_absent(editorial_base: Path):
    client = TestClient(create_app(make_settings(editorial_base)))

    plan_response = client.post(
        "/editorial-calendar/plan-due",
        headers=auth_header(),
        json={},
    )
    status_response = client.get(
        "/editorial-calendar/status",
        headers=auth_header(),
    )

    assert plan_response.json()["status"] == "calendar_missing"
    assert plan_response.json()["errors"] == [CALENDAR_FILE_NOT_FOUND]
    assert status_response.json()["status"] == "calendar_missing"
    assert status_response.json()["errors"] == [CALENDAR_FILE_NOT_FOUND]


def test_health_healthy_without_calendar_json(editorial_base: Path):
    assert (editorial_base / "editorial-calendar").is_dir()
    calendar_file = editorial_base / "editorial-calendar" / "calendar.json"
    assert not calendar_file.exists()

    client = TestClient(create_app(make_settings(editorial_base)))
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["folders_ready"] is True
    assert body["folders"]["editorial-calendar"] == {
        "exists": True,
        "is_directory": True,
    }


def test_health_degraded_without_editorial_calendar_folder(tmp_path: Path):
    base = tmp_path / "editorial"
    for relative in EXPECTED_FOLDERS:
        if relative == "editorial-calendar":
            continue
        (base / relative).mkdir(parents=True, exist_ok=True)

    client = TestClient(create_app(make_settings(base)))
    response = client.get("/health")

    body = response.json()
    assert body["status"] == "degraded"
    assert body["folders_ready"] is False
    assert body["folders"]["editorial-calendar"]["exists"] is False
