"""Tests for Flow A editorial calendar execution connector."""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.blog_publish_flow import BlogPublishResult
from silverman_blog_linkedin.campaign_lifecycle import (
    STATE_BLOG_PUBLISHED,
    STATE_DISTRIBUTION_SCHEDULED,
)
from silverman_blog_linkedin.editorial_calendar_flow_a_execute import (
    CALENDAR_CAMPAIGN_ID_CONFLICT,
    EXECUTION_STATUS_EXECUTED,
    EXECUTION_STATUS_FAILED,
    EXECUTION_STATUS_SKIPPED_EXISTING_CAMPAIGN,
    EXECUTION_STATUS_SKIPPED_NOT_FLOW_A,
    EXECUTION_STATUS_SKIPPED_REVIEW_REQUIRED,
    EXECUTION_STATUS_WOULD_EXECUTE,
    FAILED_STEP_GENERATE_LINKEDIN_PACKAGE,
    FAILED_STEP_PUBLISH_BLOG,
    FAILED_STEP_SCHEDULE_LINKEDIN_DISTRIBUTION,
    execute_due_editorial_calendar_flow_a,
)
from silverman_blog_linkedin.editorial_calendar_plan import (
    CALENDAR_FILE_NOT_FOUND,
    FLOW_A_PLANNED_STEPS,
)
from silverman_blog_linkedin.linkedin_distribution_schedule import (
    LinkedInDistributionScheduleResult,
)
from silverman_blog_linkedin.linkedin_package_flow import LinkedInPackageResult
from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, create_full_layout, make_settings

NOW_UTC = "2026-07-09T20:00:00Z"
FUTURE_UTC = "2026-12-01T14:00:00Z"
PAST_UTC = "2026-07-01T14:00:00Z"
CAMPAIGN_ID = "flow-a-2026-07-01-example"
CONFLICT_CAMPAIGN_ID = "flow-a-2026-07-06-different-slug"


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
    campaign_id: str | None = None,
    public_slug: str | None = None,
    site_url: str | None = None,
    strategy: str | None = None,
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
    if campaign_id is not None:
        item["campaign_id"] = campaign_id
    if public_slug is not None:
        item["public_slug"] = public_slug
    if site_url is not None:
        item["site_url"] = site_url
    if strategy is not None:
        item["strategy"] = strategy
    return item


def _calendar_hash(base: Path) -> str:
    content = (base / "editorial-calendar" / "calendar.json").read_bytes()
    return hashlib.sha256(content).hexdigest()


def _completed_publish(**overrides) -> BlogPublishResult:
    payload = {
        "status": "completed",
        "source_relative_path": "blog-posts/ready/post.md",
        "campaign_id": CONFLICT_CAMPAIGN_ID,
        "state": STATE_BLOG_PUBLISHED,
        "source_public_url": "https://silverman.pro/post",
    }
    payload.update(overrides)
    return BlogPublishResult(**payload)


def _completed_package(**overrides) -> LinkedInPackageResult:
    payload = {
        "status": "completed",
        "campaign_id": CONFLICT_CAMPAIGN_ID,
        "source_relative_path": "blog-posts/ready/post.md",
        "package_id": f"{CONFLICT_CAMPAIGN_ID}-pkg",
    }
    payload.update(overrides)
    return LinkedInPackageResult(**payload)


def _completed_schedule(**overrides) -> LinkedInDistributionScheduleResult:
    payload = {
        "status": "completed",
        "campaign_id": CONFLICT_CAMPAIGN_ID,
        "state": STATE_DISTRIBUTION_SCHEDULED,
        "strategy": "stagger_48h",
    }
    payload.update(overrides)
    return LinkedInDistributionScheduleResult(**payload)


def _write_distribution_scheduled_campaign(
    base: Path, campaign_id: str = CAMPAIGN_ID
) -> None:
    metadata_path = base / "metadata" / "campaigns" / f"{campaign_id}.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(
            {
                "campaign_id": campaign_id,
                "state": STATE_DISTRIBUTION_SCHEDULED,
            }
        ),
        encoding="utf-8",
    )


@pytest.fixture
def editorial_base(tmp_path: Path) -> Path:
    base = tmp_path / "editorial"
    create_full_layout(base)
    ready = base / "blog-posts" / "ready"
    (ready / "post.md").write_text("# Sample\n", encoding="utf-8")
    return base


def test_dry_run_does_not_call_downstream_or_write(editorial_base: Path):
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))
    campaigns_dir = editorial_base / "metadata" / "campaigns"
    before_campaigns = list(campaigns_dir.glob("*.json"))
    calendar_hash = _calendar_hash(editorial_base)

    with (
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post"
        ) as publish_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.generate_linkedin_package"
        ) as package_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.schedule_linkedin_distribution"
        ) as schedule_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=True,
        )

    publish_mock.assert_not_called()
    package_mock.assert_not_called()
    schedule_mock.assert_not_called()
    assert result.read_only is True
    assert list(campaigns_dir.glob("*.json")) == before_campaigns
    assert _calendar_hash(editorial_base) == calendar_hash
    item = result.items[0]
    assert item.execution_status == EXECUTION_STATUS_WOULD_EXECUTE
    item_dict = item.to_dict()
    assert "campaign_id" not in item_dict
    assert "source_public_url" not in item_dict


def test_missing_calendar_propagates_planner_status(editorial_base: Path):
    with patch(
        "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post"
    ) as publish_mock:
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
        )

    publish_mock.assert_not_called()
    assert result.status == "calendar_missing"
    assert result.errors == [CALENDAR_FILE_NOT_FOUND]
    assert result.items == []


def test_no_due_items(editorial_base: Path):
    _write_calendar(
        editorial_base,
        _base_calendar(items=[_flow_a_item(due_at_utc=FUTURE_UTC)]),
    )

    with patch(
        "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post"
    ) as publish_mock:
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
        )

    publish_mock.assert_not_called()
    assert result.status == "no_due_items"
    assert result.items == []


def test_due_flow_a_item_dry_run_would_execute(editorial_base: Path):
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))

    result = execute_due_editorial_calendar_flow_a(
        editorial_base,
        now_utc=NOW_UTC,
        dry_run=True,
    )

    assert result.read_only is True
    assert result.status == "completed"
    assert len(result.items) == 1
    item = result.items[0]
    assert item.execution_status == EXECUTION_STATUS_WOULD_EXECUTE
    assert item.planned_flow_steps == list(FLOW_A_PLANNED_STEPS)


def test_real_execution_sequence_with_chained_inputs(editorial_base: Path):
    _write_calendar(
        editorial_base,
        _base_calendar(
            items=[
                _flow_a_item(
                    site_url="https://silverman.pro",
                    public_slug="sample-post",
                    strategy="stagger_48h",
                )
            ]
        ),
    )

    publish_result = _completed_publish()
    package_result = _completed_package()
    schedule_result = _completed_schedule()

    with (
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post",
            return_value=publish_result,
        ) as publish_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.generate_linkedin_package",
            return_value=package_result,
        ) as package_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.schedule_linkedin_distribution",
            return_value=schedule_result,
        ) as schedule_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    publish_mock.assert_called_once_with(
        editorial_base,
        "blog-posts/ready/post.md",
        site_url="https://silverman.pro",
        public_slug_override="sample-post",
    )
    package_mock.assert_called_once_with(
        editorial_base,
        campaign_id=CONFLICT_CAMPAIGN_ID,
        source_relative_path=None,
        site_url="https://silverman.pro",
        topic_theme="architecture",
    )
    schedule_mock.assert_called_once_with(
        editorial_base,
        campaign_id=CONFLICT_CAMPAIGN_ID,
        source_relative_path=None,
        strategy="stagger_48h",
    )
    assert result.items[0].execution_status == EXECUTION_STATUS_EXECUTED
    assert result.read_only is False


def test_publish_failure_stops_package_and_schedule(editorial_base: Path):
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))

    with (
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post",
            return_value=BlogPublishResult(
                status="failed",
                source_relative_path="blog-posts/ready/post.md",
                errors=["blog_publish_failed"],
            ),
        ) as publish_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.generate_linkedin_package"
        ) as package_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.schedule_linkedin_distribution"
        ) as schedule_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    publish_mock.assert_called_once()
    package_mock.assert_not_called()
    schedule_mock.assert_not_called()
    item = result.items[0]
    assert item.execution_status == EXECUTION_STATUS_FAILED
    assert item.failed_step == FAILED_STEP_PUBLISH_BLOG


def test_package_failure_stops_schedule(editorial_base: Path):
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))

    with (
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post",
            return_value=_completed_publish(),
        ) as publish_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.generate_linkedin_package",
            return_value=LinkedInPackageResult(
                status="failed",
                campaign_id=CONFLICT_CAMPAIGN_ID,
                errors=["linkedin_package_failed"],
            ),
        ) as package_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.schedule_linkedin_distribution"
        ) as schedule_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    publish_mock.assert_called_once()
    package_mock.assert_called_once()
    schedule_mock.assert_not_called()
    item = result.items[0]
    assert item.execution_status == EXECUTION_STATUS_FAILED
    assert item.failed_step == FAILED_STEP_GENERATE_LINKEDIN_PACKAGE


def test_schedule_failure_marks_item_failed(editorial_base: Path):
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))

    with (
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post",
            return_value=_completed_publish(),
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.generate_linkedin_package",
            return_value=_completed_package(),
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.schedule_linkedin_distribution",
            return_value=LinkedInDistributionScheduleResult(
                status="failed",
                campaign_id=CONFLICT_CAMPAIGN_ID,
                errors=["linkedin_schedule_failed"],
            ),
        ) as schedule_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    schedule_mock.assert_called_once()
    item = result.items[0]
    assert item.execution_status == EXECUTION_STATUS_FAILED
    assert item.failed_step == FAILED_STEP_SCHEDULE_LINKEDIN_DISTRIBUTION


def test_publish_campaign_id_conflict_stops_chain(editorial_base: Path):
    _write_calendar(
        editorial_base,
        _base_calendar(items=[_flow_a_item(campaign_id=CAMPAIGN_ID)]),
    )

    with (
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post",
            return_value=_completed_publish(campaign_id=CONFLICT_CAMPAIGN_ID),
        ) as publish_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.generate_linkedin_package"
        ) as package_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.schedule_linkedin_distribution"
        ) as schedule_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    publish_mock.assert_called_once()
    package_mock.assert_not_called()
    schedule_mock.assert_not_called()
    item = result.items[0]
    assert item.execution_status == EXECUTION_STATUS_FAILED
    assert item.failed_step == FAILED_STEP_PUBLISH_BLOG
    assert CALENDAR_CAMPAIGN_ID_CONFLICT in item.errors


def test_package_campaign_id_conflict_stops_schedule(editorial_base: Path):
    _write_calendar(
        editorial_base,
        _base_calendar(items=[_flow_a_item(campaign_id=CAMPAIGN_ID)]),
    )

    with (
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post",
            return_value=_completed_publish(campaign_id=CAMPAIGN_ID),
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.generate_linkedin_package",
            return_value=_completed_package(campaign_id=CONFLICT_CAMPAIGN_ID),
        ) as package_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.schedule_linkedin_distribution"
        ) as schedule_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    package_mock.assert_called_once()
    schedule_mock.assert_not_called()
    item = result.items[0]
    assert item.execution_status == EXECUTION_STATUS_FAILED
    assert item.failed_step == FAILED_STEP_GENERATE_LINKEDIN_PACKAGE
    assert CALENDAR_CAMPAIGN_ID_CONFLICT in item.errors


def test_existing_distribution_scheduled_campaign_skipped(editorial_base: Path):
    _write_distribution_scheduled_campaign(editorial_base, CAMPAIGN_ID)
    _write_calendar(
        editorial_base,
        _base_calendar(items=[_flow_a_item(campaign_id=CAMPAIGN_ID)]),
    )

    with (
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post"
        ) as publish_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.generate_linkedin_package"
        ) as package_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.schedule_linkedin_distribution"
        ) as schedule_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    publish_mock.assert_not_called()
    package_mock.assert_not_called()
    schedule_mock.assert_not_called()
    assert result.items[0].execution_status == EXECUTION_STATUS_SKIPPED_EXISTING_CAMPAIGN


def test_review_required_item_skipped(editorial_base: Path):
    item = _flow_a_item()
    item["content_mode"] = "system_generated_source_material"
    item["flow_type"] = "flow_b_source_material"
    _write_calendar(editorial_base, _base_calendar(items=[item]))

    with patch(
        "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post"
    ) as publish_mock:
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    publish_mock.assert_not_called()
    assert result.items[0].execution_status == EXECUTION_STATUS_SKIPPED_REVIEW_REQUIRED


def test_rejected_source_selection_skipped(editorial_base: Path):
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

    with patch(
        "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post"
    ) as publish_mock:
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    publish_mock.assert_not_called()
    assert result.items[0].execution_status == EXECUTION_STATUS_SKIPPED_NOT_FLOW_A


def test_limit_caps_processed_items(editorial_base: Path):
    _write_calendar(
        editorial_base,
        _base_calendar(
            items=[
                _flow_a_item(item_id="due-1"),
                _flow_a_item(item_id="due-2"),
                _flow_a_item(item_id="due-3"),
            ]
        ),
    )

    result = execute_due_editorial_calendar_flow_a(
        editorial_base,
        now_utc=NOW_UTC,
        dry_run=True,
        limit=1,
    )

    would_execute = [
        item for item in result.items if item.execution_status == EXECUTION_STATUS_WOULD_EXECUTE
    ]
    assert len(would_execute) == 1
    assert result.counts[EXECUTION_STATUS_WOULD_EXECUTE] == 1


def test_real_execution_does_not_modify_calendar(editorial_base: Path):
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))
    calendar_hash = _calendar_hash(editorial_base)

    with (
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post",
            return_value=_completed_publish(),
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.generate_linkedin_package",
            return_value=_completed_package(),
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.schedule_linkedin_distribution",
            return_value=_completed_schedule(),
        ),
    ):
        execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    assert _calendar_hash(editorial_base) == calendar_hash


def test_no_linkedin_publication_import_or_call():
    module = importlib.import_module(
        "silverman_blog_linkedin.editorial_calendar_flow_a_execute"
    )
    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "linkedin_publication_flow" not in source
    assert "publish_linkedin_due_variants" not in source


def test_http_execute_requires_auth(editorial_base: Path):
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))
    client = TestClient(create_app(make_settings(editorial_base)))

    assert client.post("/editorial-calendar/execute-flow-a-due", json={}).status_code == 401


def test_http_execute_invalid_body_422(editorial_base: Path):
    client = TestClient(create_app(make_settings(editorial_base)))

    response = client.post(
        "/editorial-calendar/execute-flow-a-due",
        headers=auth_header(),
        json={"unexpected": "field"},
    )
    assert response.status_code == 422


def test_http_execute_invalid_now_utc_422(editorial_base: Path):
    client = TestClient(create_app(make_settings(editorial_base)))

    response = client.post(
        "/editorial-calendar/execute-flow-a-due",
        headers=auth_header(),
        json={"now_utc": "not-a-timestamp"},
    )
    assert response.status_code == 422


def test_http_execute_invalid_limit_422(editorial_base: Path):
    client = TestClient(create_app(make_settings(editorial_base)))

    for invalid_limit in (0, -1):
        response = client.post(
            "/editorial-calendar/execute-flow-a-due",
            headers=auth_header(),
            json={"limit": invalid_limit},
        )
        assert response.status_code == 422


def test_http_execute_default_dry_run_on_empty_body(editorial_base: Path):
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))
    client = TestClient(create_app(make_settings(editorial_base)))

    with patch(
        "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post"
    ) as publish_mock:
        response = client.post(
            "/editorial-calendar/execute-flow-a-due",
            headers=auth_header(),
            json={},
        )

    publish_mock.assert_not_called()
    assert response.status_code == 200
    body = response.json()
    assert body["dry_run"] is True
    assert body["read_only"] is True


def test_http_execute_success_shape(editorial_base: Path):
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))
    client = TestClient(create_app(make_settings(editorial_base)))

    response = client.post(
        "/editorial-calendar/execute-flow-a-due",
        headers=auth_header(),
        json={"now_utc": NOW_UTC},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["now_utc"] == NOW_UTC
    assert body["counts"][EXECUTION_STATUS_WOULD_EXECUTE] == 1
    assert "markdown_content" not in json.dumps(body)
