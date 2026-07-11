"""Tests for Flow A editorial calendar execution connector."""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.blog_publish_flow import (
    BLOG_PUBLISH_VALIDATION_FAILED,
    BlogPublishResult,
    publish_blog_post,
)
from silverman_blog_linkedin.campaign_lifecycle import (
    CampaignMetadataWriteResult,
    STATE_BLOG_PUBLISHED,
    STATE_DISTRIBUTION_SCHEDULED,
    STATE_FLOW_A_COMPLETE,
    EXECUTION_STATE_IDLE,
    EXECUTION_STATE_PROCESSING,
    PHYSICAL_MOVE_STATE_FAILED,
    PHYSICAL_MOVE_STATE_PARTIAL,
    RECOVERY_REPAIR_REQUIRED,
    RECOVERY_RETRYABLE,
    SOURCE_LOCATION_ERROR,
    SOURCE_LOCATION_PROCESSED,
    SOURCE_LOCATION_QUEUED,
    read_campaign_metadata,
    read_campaign_metadata as _read_campaign_metadata_from_disk,
    write_campaign_metadata,
)
from silverman_blog_linkedin.editorial_calendar_flow_a_execute import (
    CALENDAR_CAMPAIGN_ID_CONFLICT,
    CALENDAR_UPDATE_COMPLETED,
    CALENDAR_UPDATE_FAILED,
    CALENDAR_UPDATE_RECONCILED,
    CALENDAR_UPDATE_SKIPPED_ALREADY_COMPLETED,
    EXECUTION_STATUS_EXECUTED,
    EXECUTION_STATUS_FAILED,
    EXECUTION_STATUS_RECONCILED,
    EXECUTION_STATUS_SKIPPED_EXISTING_CAMPAIGN,
    EXECUTION_STATUS_SKIPPED_NOT_FLOW_A,
    EXECUTION_STATUS_SKIPPED_REVIEW_REQUIRED,
    EXECUTION_STATUS_WOULD_EXECUTE,
    FAILED_STEP_COMPLETE_SOURCE_LIFECYCLE,
    FAILED_STEP_GENERATE_LINKEDIN_PACKAGE,
    FAILED_STEP_PUBLISH_BLOG,
    FAILED_STEP_QUEUE_ACCEPTANCE,
    FAILED_STEP_SCHEDULE_LINKEDIN_DISTRIBUTION,
    SOURCE_LIFECYCLE_COMPLETED,
    SOURCE_LIFECYCLE_FAILED,
    SOURCE_LIFECYCLE_SKIPPED,
    execute_due_editorial_calendar_flow_a,
)
from silverman_blog_linkedin.flow_a_operational_queue import (
    CAMPAIGN_METADATA_WRITE_FAILED,
    QUEUE_ACCEPTANCE_COMPLETED,
    QUEUE_ACCEPTANCE_PARTIAL,
    QUEUE_ACCEPTANCE_REPAIR_REQUIRED,
    accept_flow_a_source_for_queue,
    claim_flow_a_execution,
    release_flow_a_execution,
)
from silverman_blog_linkedin.flow_a_source_moves import (
    CoordinatedMoveResult,
    ComponentMoveResult,
    DestinationFolder,
    coordinated_source_move,
)
from silverman_blog_linkedin.flow_a_source_lifecycle import FlowASourceLifecycleResult
from silverman_blog_linkedin.editorial_calendar_plan import (
    CALENDAR_COMPLETION_CAMPAIGN_UNRESOLVED,
    CALENDAR_COMPLETION_CONCURRENT_UPDATE,
    CALENDAR_COMPLETION_FACTS_CONFLICT,
    CALENDAR_COMPLETION_WRITE_FAILED,
    CALENDAR_FILE_NOT_FOUND,
    CALENDAR_SOURCE_NOT_FOUND,
    EditorialCalendarPlanResult,
    FLOW_A_PLANNED_STEPS,
    build_item_plan,
    plan_editorial_calendar_due,
)
from silverman_blog_linkedin.linkedin_distribution_schedule import (
    LinkedInDistributionScheduleResult,
)
from silverman_blog_linkedin.linkedin_package_flow import LinkedInPackageResult
from silverman_blog_linkedin.main import create_app
from silverman_blog_linkedin.ready_post_validation import ReadyPostValidationResult
from tests.conftest import auth_header, create_full_layout, make_settings

NOW_UTC = "2026-07-09T20:00:00Z"
FUTURE_UTC = "2026-12-01T14:00:00Z"
PAST_UTC = "2026-07-01T14:00:00Z"
CAMPAIGN_ID = "flow-a-2026-07-01-example"
CONFLICT_CAMPAIGN_ID = "flow-a-2026-07-06-different-slug"
QUEUED_POST_RELATIVE = "blog-posts/queued/post.md"


@pytest.fixture(autouse=True)
def _stub_editorial_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Connector no longer calls validate_ready_post directly; fixture retained for compatibility."""
    return None


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
    campaign_id: str | None = CONFLICT_CAMPAIGN_ID,
    public_slug: str | None = None,
    site_url: str | None = None,
    strategy: str | None = None,
    notes: str | None = None,
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
    if notes is not None:
        item["notes"] = notes
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


def _write_flow_a_complete_campaign(
    base: Path,
    campaign_id: str,
    *,
    source_relative_path: str = "blog-posts/ready/post.md",
    processed_source_relative_path: str = "blog-posts/processed/post.md",
    public_slug: str = "example",
    source_public_url: str = "https://silverman.pro/example",
) -> None:
    metadata_path = base / "metadata" / "campaigns" / f"{campaign_id}.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(
            {
                "campaign_id": campaign_id,
                "state": STATE_FLOW_A_COMPLETE,
                "public_slug": public_slug,
                "source_relative_path": source_relative_path,
                "processed_source_relative_path": processed_source_relative_path,
                "source_public_url": source_public_url,
                "source_file_status": {
                    "location": SOURCE_LOCATION_PROCESSED,
                    "execution_state": EXECUTION_STATE_IDLE,
                    "recovery_classification": "no_action",
                },
                "blog_publish": {"status": "completed"},
                "linkedin_package": {
                    "package_id": f"pkg-{campaign_id}",
                    "package_status": "generated",
                    "variant_ids": ["executive", "technical"],
                },
                "linkedin_distribution": {
                    "distribution_id": f"dist-{campaign_id}",
                    "strategy": "stagger_48h",
                    "anchor_utc": "2026-07-10T10:00:00Z",
                    "variant_ids": ["executive", "technical"],
                },
                "variants": [
                    {
                        "variant": "executive",
                        "scheduled_at_utc": "2026-07-10T10:00:00Z",
                        "publish_state": "pending",
                    },
                    {
                        "variant": "technical",
                        "scheduled_at_utc": "2026-07-12T10:00:00Z",
                        "publish_state": "pending",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def _ensure_ready_planner_gate(editorial_base: Path) -> None:
    """Keep a ready-folder copy so the calendar planner can resolve due items."""
    ready = editorial_base / "blog-posts" / "ready"
    queued = editorial_base / QUEUED_POST_RELATIVE
    ready.mkdir(parents=True, exist_ok=True)
    if queued.is_file():
        (ready / "post.md").write_text(
            queued.read_text(encoding="utf-8"), encoding="utf-8"
        )
    elif not (ready / "post.md").is_file():
        (ready / "post.md").write_text("# Sample\n", encoding="utf-8")


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
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.complete_flow_a_source_lifecycle"
        ) as lifecycle_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=True,
        )

    publish_mock.assert_not_called()
    package_mock.assert_not_called()
    schedule_mock.assert_not_called()
    lifecycle_mock.assert_not_called()
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
    assert item.would_queue_accept is True
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

    def _lifecycle_and_complete_campaign(base_path, campaign_id, source_relative_path):
        campaign = read_campaign_metadata(base_path, campaign_id)
        if campaign is not None:
            campaign = dict(campaign)
            campaign["state"] = STATE_FLOW_A_COMPLETE
            campaign["processed_source_relative_path"] = "blog-posts/processed/post.md"
            campaign["public_slug"] = "sample-post"
            campaign["source_file_status"] = {
                "location": SOURCE_LOCATION_PROCESSED,
                "execution_state": EXECUTION_STATE_IDLE,
                "recovery_classification": "no_action",
            }
            campaign["blog_publish"] = {"status": "completed"}
            campaign["linkedin_package"] = {"status": "completed"}
            campaign["linkedin_distribution"] = {"status": "completed"}
            write_campaign_metadata(base_path, campaign_id, campaign)
        return FlowASourceLifecycleResult(
            status="completed",
            campaign_id=campaign_id,
            processed_source_relative_path="blog-posts/processed/post.md",
        )

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
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.complete_flow_a_source_lifecycle",
            side_effect=_lifecycle_and_complete_campaign,
        ) as lifecycle_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    publish_mock.assert_called_once_with(
        editorial_base,
        QUEUED_POST_RELATIVE,
        site_url="https://silverman.pro",
        public_slug_override="sample-post",
        git_publication=False,
        live_site_confirmation=False,
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
    lifecycle_mock.assert_called_once_with(
        editorial_base,
        campaign_id=CONFLICT_CAMPAIGN_ID,
        source_relative_path=QUEUED_POST_RELATIVE,
    )
    assert result.items[0].execution_status == EXECUTION_STATUS_EXECUTED
    assert result.items[0].source_lifecycle_status == SOURCE_LIFECYCLE_COMPLETED
    assert result.items[0].calendar_update_status == CALENDAR_UPDATE_COMPLETED
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
    assert result.read_only is True


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


def test_flow_a_complete_campaign_reconciles_without_side_effects(editorial_base: Path):
    _write_flow_a_complete_campaign(editorial_base, CAMPAIGN_ID)
    _write_calendar(
        editorial_base,
        _base_calendar(
            items=[
                _flow_a_item(
                    campaign_id=CAMPAIGN_ID,
                    notes="Keep this note intact.",
                )
            ]
        ),
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
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.complete_flow_a_source_lifecycle"
        ) as lifecycle_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    publish_mock.assert_not_called()
    package_mock.assert_not_called()
    schedule_mock.assert_not_called()
    lifecycle_mock.assert_not_called()
    item = result.items[0]
    assert item.execution_status == EXECUTION_STATUS_RECONCILED
    assert item.calendar_update_status == CALENDAR_UPDATE_RECONCILED
    calendar = json.loads(
        (editorial_base / "editorial-calendar" / "calendar.json").read_text(encoding="utf-8")
    )
    completed = calendar["items"][0]
    assert completed["status"] == "completed"
    assert completed["notes"] == "Keep this note intact."
    assert completed["flow_a_completion"]["linkedin_package_status"] == "completed"
    assert completed["flow_a_completion"]["linkedin_distribution_status"] == "completed"
    assert result.read_only is False


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


def test_real_execution_marks_calendar_item_completed(editorial_base: Path):
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item(notes="Operator note.")]))

    def _lifecycle_and_complete_campaign(base_path, campaign_id, source_relative_path):
        campaign = read_campaign_metadata(base_path, campaign_id)
        if campaign is not None:
            campaign = dict(campaign)
            campaign["state"] = STATE_FLOW_A_COMPLETE
            campaign["processed_source_relative_path"] = "blog-posts/processed/post.md"
            campaign["source_public_url"] = "https://silverman.pro/post"
            campaign["source_file_status"] = {
                "location": SOURCE_LOCATION_PROCESSED,
                "execution_state": EXECUTION_STATE_IDLE,
                "recovery_classification": "no_action",
            }
            campaign["blog_publish"] = {"status": "completed"}
            campaign["linkedin_package"] = {"status": "completed"}
            campaign["linkedin_distribution"] = {"status": "completed"}
            write_campaign_metadata(base_path, campaign_id, campaign)
        return FlowASourceLifecycleResult(
            status="completed",
            campaign_id=campaign_id,
            processed_source_relative_path="blog-posts/processed/post.md",
        )

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
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.complete_flow_a_source_lifecycle",
            side_effect=_lifecycle_and_complete_campaign,
        ),
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    assert result.items[0].execution_status == EXECUTION_STATUS_EXECUTED
    assert result.items[0].calendar_update_status == CALENDAR_UPDATE_COMPLETED
    calendar = json.loads(
        (editorial_base / "editorial-calendar" / "calendar.json").read_text(encoding="utf-8")
    )
    item = calendar["items"][0]
    assert item["status"] == "completed"
    assert item["notes"] == "Operator note."
    assert item["processed_source_relative_path"] == "blog-posts/processed/post.md"


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


def test_schedule_failure_does_not_invoke_source_lifecycle(editorial_base: Path):
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
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.complete_flow_a_source_lifecycle"
        ) as lifecycle_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    lifecycle_mock.assert_not_called()
    assert result.items[0].execution_status == EXECUTION_STATUS_FAILED
    assert (editorial_base / QUEUED_POST_RELATIVE).is_file()
    assert not (editorial_base / "blog-posts/ready/post.md").exists()


def test_post_schedule_lifecycle_failure_keeps_executed_status(editorial_base: Path):
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
            return_value=_completed_schedule(),
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.complete_flow_a_source_lifecycle",
            return_value=FlowASourceLifecycleResult(
                status="failed",
                campaign_id=CONFLICT_CAMPAIGN_ID,
                errors=["flow_a_source_move_failed"],
                warnings=["repair guidance"],
            ),
        ),
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    item = result.items[0]
    assert item.execution_status == EXECUTION_STATUS_EXECUTED
    assert item.source_lifecycle_status == SOURCE_LIFECYCLE_FAILED
    assert "flow_a_source_move_failed" in item.errors
    assert "repair guidance" in item.warnings


def test_post_schedule_lifecycle_failure_persists_repair_metadata(editorial_base: Path):
    _write_calendar(
        editorial_base,
        _base_calendar(items=[_flow_a_item(campaign_id=CONFLICT_CAMPAIGN_ID)]),
    )
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path="blog-posts/ready/post.md",
        calendar_item={
            "campaign_id": CONFLICT_CAMPAIGN_ID,
            "due_at_utc": PAST_UTC,
        },
    )
    campaign = read_campaign_metadata(editorial_base, CONFLICT_CAMPAIGN_ID)
    assert campaign is not None
    campaign["state"] = STATE_DISTRIBUTION_SCHEDULED
    campaign["linkedin_distribution"] = {
        "strategy": "stagger_48h",
        "status": "completed",
    }
    write_campaign_metadata(editorial_base, CONFLICT_CAMPAIGN_ID, campaign)
    _ensure_ready_planner_gate(editorial_base)

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
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.complete_flow_a_source_lifecycle"
        ) as lifecycle_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    publish_mock.assert_not_called()
    package_mock.assert_not_called()
    schedule_mock.assert_not_called()
    lifecycle_mock.assert_not_called()
    assert result.items[0].execution_status == EXECUTION_STATUS_SKIPPED_EXISTING_CAMPAIGN
    campaign = read_campaign_metadata(editorial_base, CONFLICT_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["state"] == STATE_DISTRIBUTION_SCHEDULED
    assert campaign.get("linkedin_distribution") is not None


def test_partial_queue_acceptance_blocks_publish(editorial_base: Path):
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))

    with (
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.accept_flow_a_source_for_queue",
            return_value=type(
                "QueueResult",
                (),
                {
                    "status": QUEUE_ACCEPTANCE_REPAIR_REQUIRED,
                    "queue_acceptance_status": QUEUE_ACCEPTANCE_PARTIAL,
                    "campaign_id": CONFLICT_CAMPAIGN_ID,
                    "queued_source_relative_path": QUEUED_POST_RELATIVE,
                    "metadata_written": True,
                    "metadata_error_code": None,
                    "errors": ["image_move_failed"],
                    "warnings": [],
                },
            )(),
        ) as queue_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post"
        ) as publish_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    queue_mock.assert_called_once()
    publish_mock.assert_not_called()
    item = result.items[0]
    assert item.execution_status == EXECUTION_STATUS_FAILED
    assert item.failed_step == FAILED_STEP_QUEUE_ACCEPTANCE
    assert item.queue_acceptance_status == QUEUE_ACCEPTANCE_PARTIAL


def test_already_queued_transient_retry_resumes_flow(editorial_base: Path):
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path="blog-posts/ready/post.md",
        calendar_item={
            "campaign_id": CONFLICT_CAMPAIGN_ID,
            "due_at_utc": PAST_UTC,
        },
    )
    claim_flow_a_execution(editorial_base, campaign_id=CONFLICT_CAMPAIGN_ID)
    release_flow_a_execution(
        editorial_base,
        campaign_id=CONFLICT_CAMPAIGN_ID,
        recovery_classification=RECOVERY_RETRYABLE,
    )
    _write_calendar(
        editorial_base,
        _base_calendar(items=[_flow_a_item(campaign_id=CONFLICT_CAMPAIGN_ID)]),
    )
    _ensure_ready_planner_gate(editorial_base)

    with (
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post",
            return_value=_completed_publish(campaign_id=CONFLICT_CAMPAIGN_ID),
        ) as publish_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.generate_linkedin_package",
            return_value=_completed_package(campaign_id=CONFLICT_CAMPAIGN_ID),
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.schedule_linkedin_distribution",
            return_value=_completed_schedule(campaign_id=CONFLICT_CAMPAIGN_ID),
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.complete_flow_a_source_lifecycle",
            return_value=FlowASourceLifecycleResult(
                status="completed",
                campaign_id=CONFLICT_CAMPAIGN_ID,
            ),
        ),
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    publish_mock.assert_called_once()
    assert result.items[0].execution_status == EXECUTION_STATUS_EXECUTED


def test_stale_reclaim_through_connector(editorial_base: Path):
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path="blog-posts/ready/post.md",
        calendar_item={
            "campaign_id": CONFLICT_CAMPAIGN_ID,
            "due_at_utc": PAST_UTC,
        },
    )
    claim_flow_a_execution(editorial_base, campaign_id=CONFLICT_CAMPAIGN_ID)
    campaign = read_campaign_metadata(editorial_base, CONFLICT_CAMPAIGN_ID)
    assert campaign is not None
    status = campaign["source_file_status"]
    status["execution_state"] = "stale"
    status["last_progress_at"] = "2020-01-01T00:00:00Z"
    campaign["source_file_status"] = status
    from silverman_blog_linkedin.campaign_lifecycle import write_campaign_metadata

    write_campaign_metadata(editorial_base, CONFLICT_CAMPAIGN_ID, campaign)
    _write_calendar(
        editorial_base,
        _base_calendar(items=[_flow_a_item(campaign_id=CONFLICT_CAMPAIGN_ID)]),
    )
    _ensure_ready_planner_gate(editorial_base)

    with (
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post",
            return_value=_completed_publish(campaign_id=CONFLICT_CAMPAIGN_ID),
        ) as publish_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.generate_linkedin_package",
            return_value=_completed_package(campaign_id=CONFLICT_CAMPAIGN_ID),
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.schedule_linkedin_distribution",
            return_value=_completed_schedule(campaign_id=CONFLICT_CAMPAIGN_ID),
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.complete_flow_a_source_lifecycle",
            return_value=FlowASourceLifecycleResult(
                status="completed",
                campaign_id=CONFLICT_CAMPAIGN_ID,
            ),
        ),
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    publish_mock.assert_called_once()
    assert result.items[0].execution_status == EXECUTION_STATUS_EXECUTED


def test_distribution_scheduled_campaign_skips_without_lifecycle(editorial_base: Path):
    _write_distribution_scheduled_campaign(editorial_base, CONFLICT_CAMPAIGN_ID)
    queued = editorial_base / "blog-posts" / "queued"
    queued.mkdir(parents=True, exist_ok=True)
    (queued / "post.md").write_text("# Sample\n", encoding="utf-8")
    campaign = read_campaign_metadata(editorial_base, CONFLICT_CAMPAIGN_ID)
    assert campaign is not None
    campaign["queued_source_relative_path"] = QUEUED_POST_RELATIVE
    campaign["source_relative_path"] = QUEUED_POST_RELATIVE
    campaign["source_file_status"] = {
        "location": SOURCE_LOCATION_QUEUED,
        "execution_state": EXECUTION_STATE_IDLE,
        "recovery_classification": RECOVERY_REPAIR_REQUIRED,
    }
    write_campaign_metadata(editorial_base, CONFLICT_CAMPAIGN_ID, campaign)
    _write_calendar(
        editorial_base,
        _base_calendar(items=[_flow_a_item(campaign_id=CONFLICT_CAMPAIGN_ID)]),
    )
    _ensure_ready_planner_gate(editorial_base)

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
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.complete_flow_a_source_lifecycle"
        ) as lifecycle_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    publish_mock.assert_not_called()
    package_mock.assert_not_called()
    schedule_mock.assert_not_called()
    lifecycle_mock.assert_not_called()
    assert result.items[0].execution_status == EXECUTION_STATUS_SKIPPED_EXISTING_CAMPAIGN


def test_post_publish_failure_stays_queued_with_retryable(editorial_base: Path):
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))

    with patch(
        "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post",
        return_value=BlogPublishResult(
            status="failed",
            source_relative_path=QUEUED_POST_RELATIVE,
            campaign_id=CONFLICT_CAMPAIGN_ID,
            errors=["blog_publish_failed"],
        ),
    ):
        execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    campaign = read_campaign_metadata(editorial_base, CONFLICT_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["source_file_status"]["location"] == SOURCE_LOCATION_QUEUED
    assert campaign["source_file_status"]["recovery_classification"] == RECOVERY_RETRYABLE
    assert (editorial_base / QUEUED_POST_RELATIVE).is_file()


def test_post_package_failure_stays_queued_with_repair_required(editorial_base: Path):
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path="blog-posts/ready/post.md",
        calendar_item={
            "campaign_id": CONFLICT_CAMPAIGN_ID,
            "due_at_utc": PAST_UTC,
        },
    )
    campaign = read_campaign_metadata(editorial_base, CONFLICT_CAMPAIGN_ID)
    assert campaign is not None
    campaign["state"] = STATE_BLOG_PUBLISHED
    from silverman_blog_linkedin.campaign_lifecycle import write_campaign_metadata

    write_campaign_metadata(editorial_base, CONFLICT_CAMPAIGN_ID, campaign)
    _ensure_ready_planner_gate(editorial_base)

    with (
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post",
            return_value=_completed_publish(campaign_id=CONFLICT_CAMPAIGN_ID),
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.generate_linkedin_package",
            return_value=LinkedInPackageResult(
                status="failed",
                campaign_id=CONFLICT_CAMPAIGN_ID,
                errors=["linkedin_package_failed"],
            ),
        ),
    ):
        execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    campaign = read_campaign_metadata(editorial_base, CONFLICT_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["source_file_status"]["location"] == SOURCE_LOCATION_QUEUED
    assert campaign["source_file_status"]["recovery_classification"] == RECOVERY_REPAIR_REQUIRED
    assert (editorial_base / QUEUED_POST_RELATIVE).is_file()


def test_retry_idempotency_no_duplicate_side_effect_records(editorial_base: Path):
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))

    publish_result = _completed_publish(campaign_id=CONFLICT_CAMPAIGN_ID)
    package_result = _completed_package(campaign_id=CONFLICT_CAMPAIGN_ID)
    schedule_result = _completed_schedule(campaign_id=CONFLICT_CAMPAIGN_ID)

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
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.complete_flow_a_source_lifecycle",
            return_value=FlowASourceLifecycleResult(
                status="completed",
                campaign_id=CONFLICT_CAMPAIGN_ID,
            ),
        ),
    ):
        first = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    completed_campaign = read_campaign_metadata(editorial_base, CONFLICT_CAMPAIGN_ID)
    assert completed_campaign is not None
    completed_campaign = dict(completed_campaign)
    completed_campaign["state"] = STATE_FLOW_A_COMPLETE
    completed_campaign["processed_source_relative_path"] = "blog-posts/processed/post.md"
    completed_campaign["source_public_url"] = "https://silverman.pro/post"
    completed_campaign["source_file_status"] = {
        "location": SOURCE_LOCATION_PROCESSED,
        "execution_state": EXECUTION_STATE_IDLE,
        "recovery_classification": "no_action",
    }
    completed_campaign["blog_publish"] = {"status": "completed"}
    completed_campaign["linkedin_package"] = {"status": "completed"}
    completed_campaign["linkedin_distribution"] = {"status": "completed"}
    write_campaign_metadata(editorial_base, CONFLICT_CAMPAIGN_ID, completed_campaign)
    calendar = json.loads(
        (editorial_base / "editorial-calendar" / "calendar.json").read_text(encoding="utf-8")
    )
    calendar["items"][0]["status"] = "scheduled"
    calendar["items"][0].pop("completed_at_utc", None)
    calendar["items"][0].pop("processed_source_relative_path", None)
    calendar["items"][0].pop("flow_a_completion", None)
    (editorial_base / "editorial-calendar" / "calendar.json").write_text(
        json.dumps(calendar, indent=2), encoding="utf-8"
    )
    _ensure_ready_planner_gate(editorial_base)
    second = execute_due_editorial_calendar_flow_a(
        editorial_base,
        now_utc=NOW_UTC,
        dry_run=False,
    )

    assert publish_mock.call_count == 1
    assert package_mock.call_count == 1
    assert schedule_mock.call_count == 1
    assert first.items[0].execution_status == EXECUTION_STATUS_EXECUTED
    assert second.items[0].execution_status == EXECUTION_STATUS_RECONCILED
    assert second.items[0].calendar_update_status == CALENDAR_UPDATE_RECONCILED


def test_queue_acceptance_metadata_write_failure_blocks_connector(editorial_base: Path):
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))

    with (
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.accept_flow_a_source_for_queue",
            return_value=type(
                "QueueResult",
                (),
                {
                    "status": QUEUE_ACCEPTANCE_REPAIR_REQUIRED,
                    "queue_acceptance_status": "completed",
                    "campaign_id": CONFLICT_CAMPAIGN_ID,
                    "queued_source_relative_path": QUEUED_POST_RELATIVE,
                    "metadata_written": False,
                    "metadata_error_code": CAMPAIGN_METADATA_WRITE_FAILED,
                    "errors": [CAMPAIGN_METADATA_WRITE_FAILED],
                    "warnings": [],
                },
            )(),
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post"
        ) as publish_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    publish_mock.assert_not_called()
    item = result.items[0]
    assert item.execution_status == EXECUTION_STATUS_FAILED
    assert item.failed_step == FAILED_STEP_QUEUE_ACCEPTANCE
    assert CAMPAIGN_METADATA_WRITE_FAILED in item.errors


def _validation_failure(monkeypatch: pytest.MonkeyPatch, errors: list[str] | None = None) -> None:
    failure_errors = errors or ["editorial_validation_failed"]

    def _failed_publish(
        base_path: Path,
        source_relative_path: str,
        **kwargs,
    ) -> BlogPublishResult:
        return BlogPublishResult(
            status="failed",
            source_relative_path=source_relative_path,
            campaign_id=CONFLICT_CAMPAIGN_ID,
            errors=[BLOG_PUBLISH_VALIDATION_FAILED, *failure_errors],
            validation={"ok": False, "errors": failure_errors},
        )

    monkeypatch.setattr(
        "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post",
        _failed_publish,
    )


def test_validation_failure_completed_error_move_no_release(editorial_base: Path, monkeypatch):
    _validation_failure(monkeypatch, ["missing_frontmatter"])
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))

    with patch(
        "silverman_blog_linkedin.editorial_calendar_flow_a_execute.release_flow_a_execution"
    ) as release_mock:
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    release_mock.assert_not_called()
    item = result.items[0]
    assert item.execution_status == EXECUTION_STATUS_FAILED
    assert item.failed_step == FAILED_STEP_PUBLISH_BLOG
    assert "missing_frontmatter" in item.errors
    campaign = read_campaign_metadata(editorial_base, CONFLICT_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["source_file_status"]["location"] == SOURCE_LOCATION_ERROR
    assert campaign["source_file_status"]["execution_state"] == EXECUTION_STATE_IDLE


def test_validation_failure_partial_error_move_surfaces_repair(editorial_base: Path, monkeypatch):
    _validation_failure(monkeypatch)
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))

    def _partial_error_move(base_path, **kwargs):
        if kwargs.get("destination_folder") != DestinationFolder.ERROR:
            return coordinated_source_move(base_path, **kwargs)
        error_md = base_path / "blog-posts" / "error" / "post.md"
        error_md.parent.mkdir(parents=True, exist_ok=True)
        error_md.write_text("# Sample\n", encoding="utf-8")
        return CoordinatedMoveResult(
            status="partial",
            physical_move_state=PHYSICAL_MOVE_STATE_PARTIAL,
            markdown=ComponentMoveResult(
                source_path=QUEUED_POST_RELATIVE,
                destination_path="blog-posts/error/post.md",
                status="completed",
            ),
            image=ComponentMoveResult(
                source_path="blog-posts/queued/post.png",
                destination_path=None,
                status="failed",
                error_code="image_move_failed",
            ),
            destination_markdown_relative="blog-posts/error/post.md",
            errors=["image_move_failed"],
        )

    with (
        patch(
            "silverman_blog_linkedin.flow_a_operational_queue.coordinated_source_move",
            side_effect=_partial_error_move,
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.release_flow_a_execution"
        ) as release_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    release_mock.assert_not_called()
    item = result.items[0]
    assert item.execution_status == EXECUTION_STATUS_FAILED
    assert "editorial_validation_failed" in item.errors
    assert "image_move_failed" in item.errors
    campaign = read_campaign_metadata(editorial_base, CONFLICT_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["source_file_status"]["location"] == SOURCE_LOCATION_ERROR
    assert campaign["source_file_status"]["recovery_classification"] == RECOVERY_REPAIR_REQUIRED


def test_validation_failure_failed_error_move_releases_once(editorial_base: Path, monkeypatch):
    _validation_failure(monkeypatch)
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))

    def _failed_error_move(base_path, **kwargs):
        if kwargs.get("destination_folder") != DestinationFolder.ERROR:
            return coordinated_source_move(base_path, **kwargs)
        return CoordinatedMoveResult(
            status="failed",
            physical_move_state=PHYSICAL_MOVE_STATE_FAILED,
            markdown=ComponentMoveResult(
                source_path=QUEUED_POST_RELATIVE,
                destination_path=None,
                status="failed",
                error_code="markdown_move_failed",
            ),
            errors=["markdown_move_failed"],
        )

    with patch(
        "silverman_blog_linkedin.flow_a_operational_queue.coordinated_source_move",
        side_effect=_failed_error_move,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    item = result.items[0]
    assert item.execution_status == EXECUTION_STATUS_FAILED
    assert "markdown_move_failed" in item.errors
    campaign = read_campaign_metadata(editorial_base, CONFLICT_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["source_file_status"]["location"] == SOURCE_LOCATION_QUEUED
    assert campaign["source_file_status"]["execution_state"] == EXECUTION_STATE_IDLE
    assert campaign["source_file_status"]["recovery_classification"] == RECOVERY_REPAIR_REQUIRED


def test_validation_failure_error_move_metadata_write_failure_reported(
    editorial_base: Path, monkeypatch
):
    _validation_failure(monkeypatch)
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))
    real_write = __import__(
        "silverman_blog_linkedin.flow_a_operational_queue",
        fromlist=["write_campaign_metadata"],
    ).write_campaign_metadata
    error_move_attempts = {"count": 0}

    def _write_side_effect(base_path, campaign_id, campaign):
        if campaign.get("source_file_status", {}).get("marked_error_at"):
            error_move_attempts["count"] += 1
            return CampaignMetadataWriteResult(
                written=False,
                error_code=CAMPAIGN_METADATA_WRITE_FAILED,
            )
        return real_write(base_path, campaign_id, campaign)

    with (
        patch(
            "silverman_blog_linkedin.flow_a_operational_queue.write_campaign_metadata",
            side_effect=_write_side_effect,
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.release_flow_a_execution"
        ) as release_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    assert error_move_attempts["count"] >= 1
    release_mock.assert_called_once()
    item = result.items[0]
    assert CAMPAIGN_METADATA_WRITE_FAILED in item.errors
    assert item.execution_status == EXECUTION_STATUS_FAILED


def test_reconciliation_before_missing_source_when_ready_file_gone(editorial_base: Path):
    _write_flow_a_complete_campaign(editorial_base, CAMPAIGN_ID)
    (editorial_base / "blog-posts" / "ready" / "post.md").unlink()
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
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.complete_flow_a_source_lifecycle"
        ) as lifecycle_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    publish_mock.assert_not_called()
    package_mock.assert_not_called()
    schedule_mock.assert_not_called()
    lifecycle_mock.assert_not_called()
    item = result.items[0]
    assert item.execution_status == EXECUTION_STATUS_RECONCILED
    assert CALENDAR_SOURCE_NOT_FOUND not in item.errors


def test_completed_calendar_item_excluded_from_planner(editorial_base: Path):
    item = _flow_a_item(status="completed")
    item.update(
        {
            "campaign_id": CAMPAIGN_ID,
            "completed_at_utc": "2026-07-10T12:00:00Z",
            "processed_source_relative_path": "blog-posts/processed/post.md",
        }
    )
    _write_calendar(editorial_base, _base_calendar(items=[item]))
    (editorial_base / "blog-posts" / "ready" / "post.md").unlink()

    result = plan_editorial_calendar_due(editorial_base, now_utc=NOW_UTC)
    assert result.status == "no_due_items"
    assert result.due_items == []


def test_genuine_missing_source_without_completed_campaign(editorial_base: Path):
    (editorial_base / "blog-posts" / "ready" / "post.md").unlink()
    _write_calendar(
        editorial_base,
        _base_calendar(items=[_flow_a_item(campaign_id=CAMPAIGN_ID)]),
    )

    result = execute_due_editorial_calendar_flow_a(
        editorial_base,
        now_utc=NOW_UTC,
        dry_run=False,
    )
    item = result.items[0]
    assert item.execution_status == EXECUTION_STATUS_SKIPPED_NOT_FLOW_A
    assert CALENDAR_SOURCE_NOT_FOUND in item.errors
    assert CALENDAR_COMPLETION_CAMPAIGN_UNRESOLVED not in item.errors


def test_legacy_source_path_fallback_single_match_with_missing_ready(editorial_base: Path):
    _write_flow_a_complete_campaign(editorial_base, CAMPAIGN_ID)
    (editorial_base / "blog-posts" / "ready" / "post.md").unlink()
    _write_calendar(
        editorial_base,
        _base_calendar(items=[_flow_a_item(campaign_id=None)]),
    )

    result = execute_due_editorial_calendar_flow_a(
        editorial_base,
        now_utc=NOW_UTC,
        dry_run=False,
    )
    assert result.items[0].execution_status == EXECUTION_STATUS_RECONCILED
    calendar = json.loads(
        (editorial_base / "editorial-calendar" / "calendar.json").read_text(encoding="utf-8")
    )
    assert calendar["items"][0]["status"] == "completed"


def test_legacy_source_path_fallback_single_match(editorial_base: Path):
    _write_flow_a_complete_campaign(editorial_base, CAMPAIGN_ID)
    _write_calendar(
        editorial_base,
        _base_calendar(items=[_flow_a_item(campaign_id=None)]),
    )

    result = execute_due_editorial_calendar_flow_a(
        editorial_base,
        now_utc=NOW_UTC,
        dry_run=False,
    )
    assert result.items[0].execution_status == EXECUTION_STATUS_RECONCILED


def test_legacy_fallback_zero_matches_returns_unresolved(editorial_base: Path):
    (editorial_base / "blog-posts" / "ready" / "post.md").unlink()
    _write_calendar(
        editorial_base,
        _base_calendar(items=[_flow_a_item(campaign_id=None)]),
    )

    result = execute_due_editorial_calendar_flow_a(
        editorial_base,
        now_utc=NOW_UTC,
        dry_run=False,
    )
    assert CALENDAR_COMPLETION_CAMPAIGN_UNRESOLVED in result.items[0].errors
    assert CALENDAR_SOURCE_NOT_FOUND not in result.items[0].errors
    assert result.read_only is True
    calendar = json.loads(
        (editorial_base / "editorial-calendar" / "calendar.json").read_text(encoding="utf-8")
    )
    assert calendar["items"][0]["status"] == "scheduled"


def test_legacy_fallback_multiple_matches_returns_unresolved(editorial_base: Path):
    _write_flow_a_complete_campaign(editorial_base, CAMPAIGN_ID)
    _write_flow_a_complete_campaign(
        editorial_base,
        "flow-a-2026-07-02-second-example",
        source_relative_path="blog-posts/ready/post.md",
        processed_source_relative_path="blog-posts/processed/post-2.md",
        public_slug="second-example",
    )
    _write_calendar(
        editorial_base,
        _base_calendar(items=[_flow_a_item(campaign_id=None)]),
    )
    calendar_before = (
        editorial_base / "editorial-calendar" / "calendar.json"
    ).read_text(encoding="utf-8")

    result = execute_due_editorial_calendar_flow_a(
        editorial_base,
        now_utc=NOW_UTC,
        dry_run=False,
    )
    assert CALENDAR_COMPLETION_CAMPAIGN_UNRESOLVED in result.items[0].errors
    assert result.items[0].execution_status == EXECUTION_STATUS_FAILED
    assert result.read_only is True
    assert (
        editorial_base / "editorial-calendar" / "calendar.json"
    ).read_text(encoding="utf-8") == calendar_before


def test_equivalent_completed_item_skips_calendar_write(editorial_base: Path):
    from silverman_blog_linkedin.editorial_calendar_flow_a_execute import (
        _try_reconcile_flow_a_calendar_item,
    )
    from silverman_blog_linkedin.editorial_calendar_plan import build_item_plan, load_calendar

    _write_flow_a_complete_campaign(editorial_base, CAMPAIGN_ID)
    calendar_item = _flow_a_item(campaign_id=CAMPAIGN_ID, status="completed", notes="Keep.")
    calendar_item.update(
        {
            "completed_at_utc": "2026-07-10T12:00:00Z",
            "processed_source_relative_path": "blog-posts/processed/post.md",
            "flow_a_completion": {
                "campaign_state": STATE_FLOW_A_COMPLETE,
                "execution_status": EXECUTION_STATUS_RECONCILED,
                "source_lifecycle_status": SOURCE_LIFECYCLE_COMPLETED,
                "blog_publish_status": "completed",
                "public_url": "https://silverman.pro/example",
                "linkedin_package_status": "completed",
                "linkedin_distribution_status": "completed",
            },
        }
    )
    calendar = _base_calendar(items=[calendar_item])
    _write_calendar(editorial_base, calendar)
    calendar_hash = _calendar_hash(editorial_base)
    plan_item = build_item_plan(calendar_item, calendar_item["source_relative_path"], "selected", [])

    first, first_persisted = _try_reconcile_flow_a_calendar_item(
        editorial_base,
        calendar=calendar,
        calendar_item=calendar_item,
        plan_item=plan_item,
        dry_run=False,
    )
    reloaded, _ = load_calendar(editorial_base)
    assert reloaded is not None
    second, second_persisted = _try_reconcile_flow_a_calendar_item(
        editorial_base,
        calendar=reloaded,
        calendar_item=reloaded["items"][0],
        plan_item=plan_item,
        dry_run=False,
    )

    assert first is not None
    assert second is not None
    assert first_persisted is False
    assert second_persisted is False
    assert first.calendar_update_status == CALENDAR_UPDATE_SKIPPED_ALREADY_COMPLETED
    assert second.calendar_update_status == CALENDAR_UPDATE_SKIPPED_ALREADY_COMPLETED
    assert _calendar_hash(editorial_base) == calendar_hash


def test_calendar_write_failure_returns_partial(editorial_base: Path):
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))

    def _lifecycle_and_complete_campaign(base_path, campaign_id, source_relative_path):
        campaign = read_campaign_metadata(base_path, campaign_id)
        if campaign is not None:
            campaign = dict(campaign)
            campaign["state"] = STATE_FLOW_A_COMPLETE
            campaign["processed_source_relative_path"] = "blog-posts/processed/post.md"
            campaign["source_file_status"] = {
                "location": SOURCE_LOCATION_PROCESSED,
                "execution_state": EXECUTION_STATE_IDLE,
                "recovery_classification": "no_action",
            }
            campaign["blog_publish"] = {"status": "completed"}
            campaign["linkedin_package"] = {"status": "completed"}
            campaign["linkedin_distribution"] = {"status": "completed"}
            write_campaign_metadata(base_path, campaign_id, campaign)
        return FlowASourceLifecycleResult(
            status="completed",
            campaign_id=campaign_id,
            processed_source_relative_path="blog-posts/processed/post.md",
        )

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
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.complete_flow_a_source_lifecycle",
            side_effect=_lifecycle_and_complete_campaign,
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.save_calendar_atomic",
            return_value=[CALENDAR_COMPLETION_WRITE_FAILED],
        ),
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    assert result.status == "partial"
    assert result.items[0].calendar_update_status == CALENDAR_UPDATE_FAILED
    assert CALENDAR_COMPLETION_WRITE_FAILED in result.items[0].errors
    assert result.read_only is True


def test_flow_a_success_with_concurrent_calendar_update_returns_partial(editorial_base: Path):
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))

    def _lifecycle_and_complete_campaign(base_path, campaign_id, source_relative_path):
        campaign = read_campaign_metadata(base_path, campaign_id)
        if campaign is not None:
            campaign = dict(campaign)
            campaign["state"] = STATE_FLOW_A_COMPLETE
            campaign["processed_source_relative_path"] = "blog-posts/processed/post.md"
            campaign["source_file_status"] = {
                "location": SOURCE_LOCATION_PROCESSED,
                "execution_state": EXECUTION_STATE_IDLE,
                "recovery_classification": "no_action",
            }
            campaign["blog_publish"] = {"status": "completed"}
            campaign["linkedin_package"] = {"status": "completed"}
            campaign["linkedin_distribution"] = {"status": "completed"}
            write_campaign_metadata(base_path, campaign_id, campaign)
        return FlowASourceLifecycleResult(
            status="completed",
            campaign_id=campaign_id,
            processed_source_relative_path="blog-posts/processed/post.md",
        )

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
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.complete_flow_a_source_lifecycle",
            side_effect=_lifecycle_and_complete_campaign,
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.save_calendar_atomic",
            return_value=[CALENDAR_COMPLETION_CONCURRENT_UPDATE],
        ),
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    assert result.status == "partial"
    assert result.items[0].execution_status == EXECUTION_STATUS_EXECUTED
    assert result.items[0].calendar_update_status == CALENDAR_UPDATE_FAILED
    assert CALENDAR_COMPLETION_CONCURRENT_UPDATE in result.items[0].errors
    assert result.read_only is True
    campaign = read_campaign_metadata(editorial_base, CONFLICT_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["state"] == STATE_FLOW_A_COMPLETE


def test_retry_after_concurrent_update_reconciles_without_republication(editorial_base: Path):
    _write_flow_a_complete_campaign(editorial_base, CAMPAIGN_ID)
    _write_calendar(
        editorial_base,
        _base_calendar(items=[_flow_a_item(campaign_id=CAMPAIGN_ID)]),
    )
    (editorial_base / "blog-posts" / "ready" / "post.md").unlink()

    with patch(
        "silverman_blog_linkedin.editorial_calendar_flow_a_execute.save_calendar_atomic",
        return_value=[CALENDAR_COMPLETION_CONCURRENT_UPDATE],
    ):
        first = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )
    assert first.items[0].execution_status == EXECUTION_STATUS_FAILED
    assert first.items[0].calendar_update_status == CALENDAR_UPDATE_FAILED
    assert CALENDAR_COMPLETION_CONCURRENT_UPDATE in first.items[0].errors

    publish_mock = patch(
        "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post",
        return_value=_completed_publish(),
    )
    with publish_mock as mocked_publish:
        second = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )
    assert second.items[0].execution_status == EXECUTION_STATUS_RECONCILED
    assert second.items[0].calendar_update_status == CALENDAR_UPDATE_RECONCILED
    mocked_publish.assert_not_called()
    calendar = json.loads(
        (editorial_base / "editorial-calendar" / "calendar.json").read_text(encoding="utf-8")
    )
    assert calendar["items"][0]["status"] == "completed"


def test_equivalent_completed_item_executor_skips_filesystem_write(editorial_base: Path):
    _write_flow_a_complete_campaign(editorial_base, CAMPAIGN_ID)
    calendar_item = _flow_a_item(
        campaign_id=CAMPAIGN_ID,
        status="completed",
        notes="Keep this note.",
    )
    calendar_item.update(
        {
            "completed_at_utc": "2026-07-10T12:00:00Z",
            "processed_source_relative_path": "blog-posts/processed/post.md",
            "flow_a_completion": {
                "campaign_state": STATE_FLOW_A_COMPLETE,
                "execution_status": EXECUTION_STATUS_RECONCILED,
                "source_lifecycle_status": SOURCE_LIFECYCLE_COMPLETED,
                "blog_publish_status": "completed",
                "public_url": "https://silverman.pro/example",
                "linkedin_package_status": "completed",
                "linkedin_distribution_status": "completed",
            },
        }
    )
    calendar_path = _write_calendar(editorial_base, _base_calendar(items=[calendar_item]))
    path = editorial_base / "editorial-calendar" / "calendar.json"
    original_bytes = path.read_bytes()
    original_mtime = path.stat().st_mtime_ns
    completed_at = calendar_item["completed_at_utc"]
    notes = calendar_item["notes"]

    plan_item = build_item_plan(
        calendar_item,
        calendar_item["source_relative_path"],
        "selected",
        [],
    )
    plan = EditorialCalendarPlanResult(
        status="completed",
        calendar_path=str(calendar_path),
        calendar_version="1",
        now_utc=NOW_UTC,
        due_items=[plan_item],
        read_only=True,
    )

    with (
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.plan_editorial_calendar_due",
            return_value=plan,
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.save_calendar_atomic"
        ) as mock_save,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    mock_save.assert_not_called()
    assert path.read_bytes() == original_bytes
    assert path.stat().st_mtime_ns == original_mtime
    reloaded = json.loads(path.read_text(encoding="utf-8"))
    assert reloaded["items"][0]["completed_at_utc"] == completed_at
    assert reloaded["items"][0]["notes"] == notes
    assert result.items[0].calendar_update_status == CALENDAR_UPDATE_SKIPPED_ALREADY_COMPLETED
    assert result.read_only is True


def test_dry_run_reconciliation_preview_stays_read_only(editorial_base: Path):
    _write_flow_a_complete_campaign(editorial_base, CAMPAIGN_ID)
    _write_calendar(
        editorial_base,
        _base_calendar(items=[_flow_a_item(campaign_id=CAMPAIGN_ID)]),
    )
    calendar_hash = _calendar_hash(editorial_base)

    result = execute_due_editorial_calendar_flow_a(
        editorial_base,
        now_utc=NOW_UTC,
        dry_run=True,
    )

    assert result.dry_run is True
    assert result.read_only is True
    assert result.items[0].execution_status == EXECUTION_STATUS_RECONCILED
    assert result.items[0].calendar_update_status == CALENDAR_UPDATE_RECONCILED
    assert _calendar_hash(editorial_base) == calendar_hash


def test_calendar_git_publication_opt_in_passthrough(editorial_base: Path) -> None:
    _write_calendar(
        editorial_base,
        _base_calendar(
            items=[
                _flow_a_item(
                    site_url="https://silverman.pro",
                    public_slug="sample-post",
                )
            ]
        ),
    )

    with (
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post"
        ) as publish_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.generate_linkedin_package",
            return_value=_completed_package(),
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.schedule_linkedin_distribution",
            return_value=_completed_schedule(),
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.complete_flow_a_source_lifecycle",
            return_value=FlowASourceLifecycleResult(
                status=SOURCE_LIFECYCLE_COMPLETED,
                campaign_id=CONFLICT_CAMPAIGN_ID,
                errors=[],
                warnings=[],
            ),
        ),
    ):
        publish_mock.return_value = BlogPublishResult(
            status="completed",
            source_relative_path=QUEUED_POST_RELATIVE,
            campaign_id=CONFLICT_CAMPAIGN_ID,
            blog_publish={"status": "published"},
            blog_git_publication={"status": "pushed", "commit_sha": "abc"},
        )
        execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
            limit=1,
            git_publication=True,
        )

    publish_mock.assert_called_once()
    assert publish_mock.call_args.kwargs.get("git_publication") is True


def test_calendar_environment_only_without_opt_in(editorial_base: Path) -> None:
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))

    with (
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post"
        ) as publish_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.generate_linkedin_package",
            return_value=_completed_package(),
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.schedule_linkedin_distribution",
            return_value=_completed_schedule(),
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.complete_flow_a_source_lifecycle",
            return_value=FlowASourceLifecycleResult(
                status=SOURCE_LIFECYCLE_COMPLETED,
                campaign_id=CONFLICT_CAMPAIGN_ID,
                errors=[],
                warnings=[],
            ),
        ),
    ):
        publish_mock.return_value = BlogPublishResult(
            status="completed",
            source_relative_path=QUEUED_POST_RELATIVE,
            campaign_id=CONFLICT_CAMPAIGN_ID,
            blog_publish={"status": "published"},
        )
        execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
            limit=1,
            git_publication=False,
        )

    publish_mock.assert_called_once()
    assert publish_mock.call_args.kwargs.get("git_publication") is False


def test_calendar_partial_publish_surfaces_git_errors(editorial_base: Path) -> None:
    from silverman_blog_linkedin.github_pages_git_publication import (
        BLOG_GIT_PUBLICATION_PUSH_FAILED,
    )

    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))

    with (
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post"
        ) as publish_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.generate_linkedin_package",
            return_value=_completed_package(),
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.schedule_linkedin_distribution",
            return_value=_completed_schedule(),
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.complete_flow_a_source_lifecycle",
            return_value=FlowASourceLifecycleResult(
                status=SOURCE_LIFECYCLE_COMPLETED,
                campaign_id=CONFLICT_CAMPAIGN_ID,
                errors=[],
                warnings=[],
            ),
        ),
    ):
        publish_mock.return_value = BlogPublishResult(
            status="partial",
            source_relative_path=QUEUED_POST_RELATIVE,
            campaign_id=CONFLICT_CAMPAIGN_ID,
            blog_publish={"status": "published"},
            blog_git_publication={
                "status": "failed",
                "error_code": BLOG_GIT_PUBLICATION_PUSH_FAILED,
            },
            errors=[BLOG_GIT_PUBLICATION_PUSH_FAILED],
        )
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
            limit=1,
            git_publication=True,
        )

    item = result.items[0]
    assert item.publish_status == "partial"
    assert item.blog_git_publication is not None
    assert BLOG_GIT_PUBLICATION_PUSH_FAILED in item.errors


def test_calendar_live_site_confirmation_passthrough(editorial_base: Path) -> None:
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))

    with (
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post"
        ) as publish_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.generate_linkedin_package",
            return_value=_completed_package(),
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.schedule_linkedin_distribution",
            return_value=_completed_schedule(),
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.complete_flow_a_source_lifecycle",
            return_value=FlowASourceLifecycleResult(
                status=SOURCE_LIFECYCLE_COMPLETED,
                campaign_id=CONFLICT_CAMPAIGN_ID,
                errors=[],
                warnings=[],
            ),
        ),
    ):
        publish_mock.return_value = BlogPublishResult(
            status="completed",
            source_relative_path=QUEUED_POST_RELATIVE,
            campaign_id=CONFLICT_CAMPAIGN_ID,
            blog_publish={"status": "published"},
            blog_git_publication={"status": "pushed", "commit_sha": "abc"},
            blog_live_site_publication={"status": "confirmed", "http_status": 200},
        )
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
            limit=1,
            git_publication=True,
            live_site_confirmation=True,
        )

    publish_mock.assert_called_once()
    assert publish_mock.call_args.kwargs.get("live_site_confirmation") is True
    item = result.items[0]
    assert item.blog_live_site_publication is not None
    assert item.blog_live_site_publication["status"] == "confirmed"


def test_calendar_partial_live_site_confirmation_surfaces_errors(
    editorial_base: Path,
) -> None:
    from silverman_blog_linkedin.blog_live_site_confirmation import (
        BLOG_LIVE_SITE_CONFIRMATION_UNREACHABLE,
    )

    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))

    with (
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post"
        ) as publish_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.generate_linkedin_package",
            return_value=_completed_package(),
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.schedule_linkedin_distribution",
            return_value=_completed_schedule(),
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.complete_flow_a_source_lifecycle",
            return_value=FlowASourceLifecycleResult(
                status=SOURCE_LIFECYCLE_COMPLETED,
                campaign_id=CONFLICT_CAMPAIGN_ID,
                errors=[],
                warnings=[],
            ),
        ),
    ):
        publish_mock.return_value = BlogPublishResult(
            status="partial",
            source_relative_path=QUEUED_POST_RELATIVE,
            campaign_id=CONFLICT_CAMPAIGN_ID,
            blog_publish={"status": "published"},
            blog_git_publication={"status": "pushed", "commit_sha": "abc"},
            blog_live_site_publication={
                "status": "failed",
                "error_code": BLOG_LIVE_SITE_CONFIRMATION_UNREACHABLE,
            },
            errors=[BLOG_LIVE_SITE_CONFIRMATION_UNREACHABLE],
        )
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
            limit=1,
            git_publication=True,
            live_site_confirmation=True,
        )

    item = result.items[0]
    assert item.publish_status == "partial"
    assert item.blog_live_site_publication is not None
    assert BLOG_LIVE_SITE_CONFIRMATION_UNREACHABLE in item.errors
