"""Behavioral tests for the read-only Flow A operational status view."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import silverman_blog_linkedin.flow_a_operational_status as operational_status_module
from silverman_blog_linkedin.flow_a_config import (
    DEFAULT_FLOW_A_PROCESSING_STALE_SECONDS,
    ENV_FLOW_A_PROCESSING_STALE_SECONDS,
    FLOW_A_PROCESSING_STALE_SECONDS_INVALID,
    FlowAConfigurationError,
)
from silverman_blog_linkedin.flow_a_operational_status import (
    CALENDAR_FILE_NOT_FOUND,
    CALENDAR_ITEM_PAST_DUE,
    CAMPAIGN_ATTEMPT_CLOCK_INVERTED,
    CAMPAIGN_FILE_PATH_OUTSIDE_SOURCE,
    CAMPAIGN_ID_FILENAME_MISMATCH,
    CAMPAIGN_STAGE_CLOCK_INVERTED,
    CAMPAIGN_STAGE_HISTORY_INVALID,
    CAMPAIGN_STAGE_HISTORY_STATE_INCONSISTENT,
    LINKEDIN_PUBLISH_STATE_INVALID,
    LINKEDIN_TIMESTAMP_INVALID,
    RUN_CLOCK_INVERTED,
    RUN_DOCUMENT_INVALID,
    RUN_STATUS_INVALID,
    FlowAOperationalStatusResult,
    get_flow_a_operational_status,
)
from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, make_settings

NOW = "2026-07-17T12:00:00Z"
CAMPAIGN_ID = "flow-a-2026-07-17-operational-status"


@pytest.fixture
def operational_base(tmp_path: Path) -> Path:
    base = tmp_path / "editorial"
    for relative in (
        "metadata/runs",
        "metadata/campaigns",
        "editorial-calendar",
        "blog-posts/ready",
        "blog-posts/queued",
        "blog-posts/processed",
        "blog-posts/error",
        "linkedin-posts/review",
        "linkedin-posts/approved",
        "linkedin-posts/published",
    ):
        (base / relative).mkdir(parents=True, exist_ok=True)
    _write_calendar(base, [])
    return base


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _write_run(
    base: Path,
    run_id: str,
    *,
    status: str = "completed",
    started_at: str = "2026-07-17T10:00:00Z",
    completed_at: str = "2026-07-17T10:01:00Z",
    **extra: object,
) -> Path:
    payload = {
        "run_id": run_id,
        "trigger": "POST /process-ready",
        "status": status,
        "started_at": started_at,
        "completed_at": completed_at,
        **extra,
    }
    return _write_json(base / "metadata/runs" / f"{run_id}.json", payload)


def _campaign_id(slug: str) -> str:
    return f"flow-a-2026-07-17-{slug}"


def _write_campaign(
    base: Path,
    campaign_id: str = CAMPAIGN_ID,
    *,
    state: str = "ready",
    source_status: dict | None = None,
    variants: object = None,
    linkedin_distribution: object = None,
    updated_at: str = "2026-07-17T10:00:00Z",
    **extra: object,
) -> Path:
    payload: dict[str, object] = {
        "campaign_id": campaign_id,
        "flow": "flow_a",
        "state": state,
        "updated_at": updated_at,
        "source_file_status": source_status
        or {
            "location": "ready",
            "execution_state": "idle",
            "recovery_classification": "no_action",
        },
        "variants": [] if variants is None else variants,
        **extra,
    }
    if linkedin_distribution is not None:
        payload["linkedin_distribution"] = linkedin_distribution
    return _write_json(
        base / "metadata/campaigns" / f"{campaign_id}.json",
        payload,
    )


def _calendar_item(
    item_id: str,
    *,
    status: str = "scheduled",
    due_at_utc: str = "2026-07-17T11:00:00Z",
    campaign_id: str | None = None,
) -> dict:
    item = {
        "item_id": item_id,
        "title": f"Item {item_id}",
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


def _write_calendar(base: Path, items: list[dict]) -> Path:
    return _write_json(
        base / "editorial-calendar/calendar.json",
        {
            "schema_version": "1",
            "updated_at_utc": "2026-07-17T09:00:00Z",
            "items": items,
        },
    )


def _snapshot_tree(base: Path) -> dict[str, tuple[bytes, int]]:
    return {
        str(path.relative_to(base)): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in sorted(base.rglob("*"))
        if path.is_file()
    }


def _campaign(result: FlowAOperationalStatusResult, campaign_id: str) -> dict:
    return next(
        item.to_dict()
        for item in result.campaigns
        if item.campaign_id == campaign_id
    )


def test_run_classification_safe_fields_ordering_and_no_synthetic_history(
    operational_base: Path,
):
    _write_run(
        operational_base,
        "run-older",
        status="completed",
        completed_at="2026-07-17T10:01:00Z",
        base_path="/secret/base",
        markdown_content="FORBIDDEN-BODY",
    )
    _write_run(
        operational_base,
        "run-newer",
        status="failed",
        completed_at="2026-07-17T11:01:00Z",
        errors=["metadata_write_failed", "raw exception text!"],
        api_key="FORBIDDEN-KEY",
    )
    _write_run(
        operational_base,
        "run-newest-success",
        completed_at="2026-07-17T11:30:00Z",
    )
    _write_run(operational_base, "run-unknown", status="running")
    _write_campaign(
        operational_base,
        source_status={
            "location": "queued",
            "execution_state": "idle",
            "recovery_classification": "retryable",
            "execution_attempt_id": "attempt-current",
            "attempt_count": 9,
        },
        state_history=[
            {"to_state": "error"},
            {"to_state": "flow_a_complete"},
        ],
    )

    result = get_flow_a_operational_status(operational_base, now_utc=NOW)
    body = result.to_dict()

    assert [item["run_id"] for item in body["executions"]["failed"]] == [
        "run-newer"
    ]
    assert [item["run_id"] for item in body["executions"]["successful"]] == [
        "run-newest-success",
        "run-older",
    ]
    assert body["summary"]["successful_executions"] == 2
    assert body["summary"]["failed_executions"] == 1
    assert body["campaigns"][0]["attempt_count"] == 9
    assert sum(len(items) for items in body["executions"].values()) == 3
    assert {issue["reason"] for issue in body["data_issues"]} >= {
        RUN_STATUS_INVALID,
        "run_error_code_invalid",
    }
    serialized = json.dumps(body)
    for forbidden in (
        "/secret/base",
        "FORBIDDEN-BODY",
        "FORBIDDEN-KEY",
        "raw exception text!",
        "state_history",
    ):
        assert forbidden not in serialized
    assert set(body["executions"]["failed"][0]) == {
        "run_id",
        "trigger",
        "status",
        "outcome",
        "started_at",
        "completed_at",
        "duration_seconds",
        "error_codes",
    }


@pytest.mark.parametrize(
    ("state", "location", "execution_state", "recovery", "expected"),
    [
        (
            "flow_a_complete",
            "processed",
            "idle",
            "no_action",
            (True, False, False, False),
        ),
        (
            "validation_failed",
            "error",
            "idle",
            "requeue_required",
            (False, True, True, False),
        ),
        (
            "error",
            "queued",
            "idle",
            "retryable",
            (False, True, True, False),
        ),
        (
            "validated",
            "queued",
            "idle",
            "repair_required",
            (False, False, True, True),
        ),
        (
            "validated",
            "queued",
            "idle",
            "manual_intervention_required",
            (False, False, True, True),
        ),
        (
            "validated",
            "queued",
            "idle",
            "retryable",
            (False, False, False, True),
        ),
    ],
)
def test_campaign_independent_health_flags(
    operational_base: Path,
    state: str,
    location: str,
    execution_state: str,
    recovery: str,
    expected: tuple[bool, bool, bool, bool],
):
    _write_campaign(
        operational_base,
        state=state,
        source_status={
            "location": location,
            "execution_state": execution_state,
            "recovery_classification": recovery,
        },
        variants=[
            {
                "variant": "executive-recruiter",
                "publish_state": "failed",
                "linkedin_publication": {
                    "last_error_code": "linkedin_publish_api_error"
                },
            }
        ],
    )

    campaign = _campaign(
        get_flow_a_operational_status(operational_base, now_utc=NOW),
        CAMPAIGN_ID,
    )

    assert (
        campaign["successful"],
        campaign["failed"],
        campaign["blocked"],
        campaign["in_progress"],
    ) == expected
    assert campaign["linkedin"]["publish_state_counts"]["failed"] == 1
    if expected[0]:
        assert campaign["failed"] is False


def test_all_blocking_recovery_classes_and_combined_stale_flags(
    operational_base: Path,
):
    for index, recovery in enumerate(
        (
            "repair_required",
            "requeue_required",
            "manual_intervention_required",
        )
    ):
        _write_campaign(
            operational_base,
            _campaign_id(f"blocked-{index}"),
            state="validated",
            source_status={
                "location": "queued",
                "execution_state": "stale",
                "recovery_classification": recovery,
            },
        )

    result = get_flow_a_operational_status(operational_base, now_utc=NOW)
    assert result.summary["blocked_campaigns"] == 3
    assert result.summary["stale_campaigns"] == 3
    assert result.summary["in_progress_campaigns"] == 3
    for campaign in result.campaigns:
        assert campaign.blocked and campaign.stale and campaign.in_progress
    assert [campaign.campaign_id for campaign in result.campaigns] == sorted(
        [campaign.campaign_id for campaign in result.campaigns],
        reverse=True,
    )


@pytest.mark.parametrize(
    ("last_progress_at", "lease", "expected_stale", "reason"),
    [
        (
            "2026-07-17T11:00:01Z",
            "2026-07-17T11:00:02Z",
            False,
            None,
        ),
        (
            "2026-07-17T11:00:00Z",
            "2099-01-01T00:00:00Z",
            True,
            "processing_inactivity_threshold_reached",
        ),
        (
            "2026-07-17T10:59:59Z",
            "2099-01-01T00:00:00Z",
            True,
            "processing_inactivity_threshold_reached",
        ),
        (None, None, True, "processing_last_progress_at_missing"),
        (
            "invalid",
            "2099-01-01T00:00:00Z",
            True,
            "processing_last_progress_at_invalid",
        ),
    ],
)
def test_processing_stale_threshold_boundaries_and_divergent_lease(
    operational_base: Path,
    monkeypatch: pytest.MonkeyPatch,
    last_progress_at: str | None,
    lease: str | None,
    expected_stale: bool,
    reason: str | None,
):
    monkeypatch.setenv(ENV_FLOW_A_PROCESSING_STALE_SECONDS, "3600")
    status = {
        "location": "queued",
        "execution_state": "processing",
        "recovery_classification": "retryable",
        "last_progress_at": last_progress_at,
        "processing_lease_expires_at": lease,
    }
    _write_campaign(operational_base, source_status=status)

    campaign = _campaign(
        get_flow_a_operational_status(operational_base, now_utc=NOW),
        CAMPAIGN_ID,
    )

    assert campaign["stale"] is expected_stale
    if reason is not None:
        assert reason in campaign["health_reasons"]
    assert campaign["processing_lease_expires_at"] == lease


def test_persisted_stale_and_stale_configuration_validation(
    operational_base: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _write_campaign(
        operational_base,
        source_status={
            "location": "queued",
            "execution_state": "stale",
            "recovery_classification": "retryable",
        },
    )
    monkeypatch.delenv(ENV_FLOW_A_PROCESSING_STALE_SECONDS, raising=False)
    result = get_flow_a_operational_status(operational_base, now_utc=NOW)
    assert result.stale_after_seconds == DEFAULT_FLOW_A_PROCESSING_STALE_SECONDS
    assert result.campaigns[0].stale is True

    monkeypatch.setenv(ENV_FLOW_A_PROCESSING_STALE_SECONDS, "59")
    with pytest.raises(FlowAConfigurationError) as error:
        get_flow_a_operational_status(operational_base, now_utc=NOW)
    assert error.value.error_code == FLOW_A_PROCESSING_STALE_SECONDS_INVALID


def test_linkedin_counts_anchors_elapsed_windows_and_invalid_evidence(
    operational_base: Path,
):
    _write_campaign(
        operational_base,
        state="flow_a_complete",
        source_status={
            "location": "processed",
            "execution_state": "idle",
            "recovery_classification": "no_action",
        },
        linkedin_distribution={
            "strategy": "flow_a_staggered",
            "anchor_utc": "2026-07-17T08:00:00Z",
        },
        variants=[
            {
                "variant": "executive-recruiter",
                "publish_state": "pending",
                "scheduled_at_utc": "2026-07-17T12:00:00Z",
            },
            {
                "variant": "technical-architect",
                "publish_state": "pending",
                "scheduled_at_utc": "2026-07-18T12:00:00Z",
            },
            {
                "variant": "engineering-leadership",
                "publish_state": "queued",
                "publish_after_utc": "2026-07-17T11:59:00Z",
            },
            {
                "variant": "short-provocative",
                "publish_state": "published",
                "published_at": "2026-07-17T09:00:00Z",
            },
            {
                "variant": "other",
                "publish_state": "failed",
                "linkedin_publication": {
                    "last_error_code": "linkedin_publish_api_error"
                },
            },
            {
                "variant": "invalid-state",
                "publish_state": "publishing",
                "scheduled_at_utc": "invalid",
            },
            {
                "variant": "invalid-time",
                "publish_state": "pending",
                "scheduled_at_utc": "invalid",
            },
        ],
    )

    result = get_flow_a_operational_status(operational_base, now_utc=NOW)
    linkedin = result.campaigns[0].linkedin.to_dict()

    assert linkedin["publish_state_counts"] == {
        "pending": 3,
        "queued": 1,
        "published": 1,
        "failed": 1,
        "cancelled": 0,
    }
    assert linkedin["strategy"] == "flow_a_staggered"
    assert linkedin["anchor_utc"] == "2026-07-17T08:00:00Z"
    assert (
        linkedin["earliest_pending_scheduled_at_utc"]
        == "2026-07-17T12:00:00Z"
    )
    assert linkedin["earliest_queued_publish_after_utc"] == "2026-07-17T11:59:00Z"
    assert linkedin["latest_published_at"] == "2026-07-17T09:00:00Z"
    assert linkedin["elapsed_pending_scheduled_windows"] == 1
    assert linkedin["elapsed_queued_publish_windows"] == 1
    assert linkedin["elapsed_windows_are_descriptive_only"] is True
    assert linkedin["failure_codes"] == ["linkedin_publish_api_error"]
    assert result.campaigns[0].successful is True
    reasons = {issue.reason for issue in result.data_issues}
    assert LINKEDIN_PUBLISH_STATE_INVALID in reasons
    assert LINKEDIN_TIMESTAMP_INVALID in reasons


def test_calendar_delay_statuses_boundaries_terminal_exclusions_and_ordering(
    operational_base: Path,
):
    items = [
        _calendar_item("planned", status="planned", due_at_utc="2026-07-17T10:00:00Z"),
        _calendar_item(
            "scheduled",
            status="scheduled",
            due_at_utc="2026-07-17T09:00:00Z",
            campaign_id=CAMPAIGN_ID,
        ),
        _calendar_item("due", status="due", due_at_utc="2026-07-17T10:00:00Z"),
        _calendar_item(
            "in-progress",
            status="in_progress",
            due_at_utc="2026-07-17T11:00:00Z",
        ),
        _calendar_item("equal", status="scheduled", due_at_utc=NOW),
        _calendar_item(
            "future", status="scheduled", due_at_utc="2026-07-17T12:00:01Z"
        ),
        _calendar_item(
            "completed", status="completed", due_at_utc="2026-07-17T08:00:00Z"
        ),
        _calendar_item(
            "skipped", status="skipped", due_at_utc="2026-07-17T08:00:00Z"
        ),
        _calendar_item(
            "failed", status="failed", due_at_utc="2026-07-17T08:00:00Z"
        ),
    ]
    _write_calendar(operational_base, items)

    result = get_flow_a_operational_status(operational_base, now_utc=NOW)

    assert [item.item_id for item in result.delayed_calendar_items] == [
        "scheduled",
        "due",
        "planned",
        "in-progress",
    ]
    assert all(
        item.reason == CALENDAR_ITEM_PAST_DUE
        for item in result.delayed_calendar_items
    )
    assert result.delayed_calendar_items[0].campaign_id == CAMPAIGN_ID
    assert result.summary["delayed_calendar_items"] == 4


def test_malformed_mismatch_symlink_missing_and_partial_results(
    operational_base: Path,
    tmp_path: Path,
):
    _write_run(operational_base, "run-valid")
    (operational_base / "metadata/runs/broken.json").write_text(
        "{broken", encoding="utf-8"
    )
    _write_campaign(operational_base)
    mismatched = _write_campaign(
        operational_base,
        _campaign_id("filename"),
    )
    mismatch_payload = json.loads(mismatched.read_text(encoding="utf-8"))
    mismatch_payload["campaign_id"] = _campaign_id("persisted")
    _write_json(mismatched, mismatch_payload)
    outside = _write_json(
        tmp_path / "outside.json",
        {"campaign_id": _campaign_id("outside"), "flow": "flow_a"},
    )
    (operational_base / "metadata/campaigns/escaping.json").symlink_to(outside)
    (operational_base / "editorial-calendar/calendar.json").unlink()

    result = get_flow_a_operational_status(operational_base, now_utc=NOW)

    assert result.status == "partial"
    assert result.summary["successful_executions"] == 1
    assert result.summary["campaigns_total"] == 1
    reasons = {issue.reason for issue in result.data_issues}
    assert {
        RUN_DOCUMENT_INVALID,
        CAMPAIGN_ID_FILENAME_MISMATCH,
        CAMPAIGN_FILE_PATH_OUTSIDE_SOURCE,
        CALENDAR_FILE_NOT_FOUND,
    } <= reasons
    serialized = json.dumps(result.to_dict())
    assert str(tmp_path) not in serialized
    assert "{broken" not in serialized
    issue_keys = [
        (issue.source, issue.identifier or "", issue.reason)
        for issue in result.data_issues
    ]
    assert issue_keys == sorted(issue_keys)


def test_invalid_calendar_and_malformed_campaign_preserve_valid_runs(
    operational_base: Path,
):
    _write_run(operational_base, "run-valid")
    (
        operational_base
        / "metadata/campaigns"
        / f"{_campaign_id('broken')}.json"
    ).write_text(
        "{not-json",
        encoding="utf-8",
    )
    _write_json(
        operational_base / "editorial-calendar/calendar.json",
        {"schema_version": "1", "items": "not-a-list"},
    )

    result = get_flow_a_operational_status(operational_base, now_utc=NOW)

    assert result.status == "partial"
    assert result.summary["successful_executions"] == 1
    assert result.campaigns == []
    assert result.delayed_calendar_items == []
    reasons = {issue.reason for issue in result.data_issues}
    assert "campaign_file_invalid" in reasons
    assert "calendar_schema_invalid" in reasons


def test_missing_directories_and_empty_valid_sources(
    operational_base: Path,
):
    empty = get_flow_a_operational_status(operational_base, now_utc=NOW)
    assert empty.status == "ok"
    assert empty.summary["campaigns_total"] == 0
    assert empty.summary["data_issues"] == 0

    (operational_base / "metadata/runs").rmdir()
    missing = get_flow_a_operational_status(operational_base, now_utc=NOW)
    assert missing.status == "partial"
    assert {issue.reason for issue in missing.data_issues} == {
        "runs_directory_not_found"
    }


def test_repeated_service_calls_are_byte_for_byte_read_only(
    operational_base: Path,
):
    _write_run(operational_base, "run-success")
    _write_campaign(
        operational_base,
        state="validated",
        source_status={
            "location": "queued",
            "execution_state": "processing",
            "recovery_classification": "repair_required",
            "last_progress_at": "2026-07-17T10:00:00Z",
        },
    )
    _write_calendar(
        operational_base,
        [_calendar_item("delayed", due_at_utc="2026-07-17T10:00:00Z")],
    )
    before = _snapshot_tree(operational_base)

    with (
        patch("subprocess.run") as git_or_shell,
        patch("httpx.request") as external_http,
    ):
        first = get_flow_a_operational_status(operational_base, now_utc=NOW)
        second = get_flow_a_operational_status(operational_base, now_utc=NOW)

    assert first.to_dict() == second.to_dict()
    assert first.campaigns[0].stale is True
    assert first.campaigns[0].blocked is True
    assert _snapshot_tree(operational_base) == before
    git_or_shell.assert_not_called()
    external_http.assert_not_called()


def test_stage_durations_completed_open_intervals_and_execution_duration(
    operational_base: Path,
):
    _write_run(
        operational_base,
        "run-timed",
        started_at="2026-07-17T10:00:00Z",
        completed_at="2026-07-17T10:01:30Z",
    )
    _write_campaign(
        operational_base,
        state="blog_publish_pending",
        source_status={
            "location": "queued",
            "execution_state": "idle",
            "recovery_classification": "no_action",
            "processing_started_at": "2026-07-17T09:00:00Z",
            "last_progress_at": "2026-07-17T09:05:00Z",
        },
        state_history=[
            {
                "at": "2026-07-17T08:00:00Z",
                "from_state": None,
                "to_state": "ready",
                "reason": "Campaign created",
            },
            {
                "at": "2026-07-17T08:00:30Z",
                "from_state": "ready",
                "to_state": "validated",
                "reason": "FORBIDDEN-REASON-TEXT",
            },
            {
                "at": "2026-07-17T08:10:30Z",
                "from_state": "validated",
                "to_state": "blog_publish_pending",
                "reason": "FORBIDDEN-REASON-TEXT",
            },
        ],
    )

    result = get_flow_a_operational_status(operational_base, now_utc=NOW)
    body = result.to_dict()

    assert result.status == "ok"
    assert body["executions"]["successful"][0]["duration_seconds"] == 90

    campaign = _campaign(result, CAMPAIGN_ID)
    assert campaign["attempt_duration_seconds"] == 300
    assert campaign["stage_durations"] == [
        {
            "stage": "ready",
            "started_at": "2026-07-17T08:00:00Z",
            "ended_at": "2026-07-17T08:00:30Z",
            "duration_seconds": 30,
            "open": False,
            "from_state": "ready",
            "to_state": "validated",
        },
        {
            "stage": "validated",
            "started_at": "2026-07-17T08:00:30Z",
            "ended_at": "2026-07-17T08:10:30Z",
            "duration_seconds": 600,
            "open": False,
            "from_state": "validated",
            "to_state": "blog_publish_pending",
        },
        {
            "stage": "blog_publish_pending",
            "started_at": "2026-07-17T08:10:30Z",
            "ended_at": None,
            "duration_seconds": 13770,
            "open": True,
            "from_state": None,
            "to_state": None,
        },
    ]
    assert body["summary"]["stage_durations"] == {
        "campaigns_with_stage_durations": 1,
        "executions_with_duration": 1,
        "stage_intervals_reported": 3,
    }
    assert "FORBIDDEN-REASON-TEXT" not in json.dumps(body)


def test_open_stage_duration_is_observation_relative(operational_base: Path):
    _write_campaign(
        operational_base,
        state="derivatives_pending",
        state_history=[
            {
                "at": "2026-07-17T11:00:00Z",
                "from_state": None,
                "to_state": "derivatives_pending",
            },
        ],
    )

    earlier = _campaign(
        get_flow_a_operational_status(
            operational_base, now_utc="2026-07-17T11:30:00Z"
        ),
        CAMPAIGN_ID,
    )
    later = _campaign(
        get_flow_a_operational_status(operational_base, now_utc=NOW),
        CAMPAIGN_ID,
    )

    assert earlier["stage_durations"][0]["open"] is True
    assert earlier["stage_durations"][0]["duration_seconds"] == 1800
    assert later["stage_durations"][0]["duration_seconds"] == 3600


def test_dependency_buckets_precedence_dedupe_and_no_external_calls(
    operational_base: Path,
):
    _write_run(
        operational_base,
        "run-failed-deps",
        status="failed",
        errors=[
            "deepseek_timeout",
            "deepseek_timeout",
            "comfyui_connection_refused",
        ],
    )
    _write_campaign(
        operational_base,
        state="error",
        source_status={
            "location": "error",
            "execution_state": "idle",
            "recovery_classification": "manual_intervention_required",
            "last_error": {
                "error_code": "blog_git_publication_push_failed",
            },
        },
        errors=[
            "blog_image_generation_comfyui_failed",
            "deepseek_timeout",
            "mystery_code",
        ],
        state_history=[
            {
                "at": "2026-07-17T08:00:00Z",
                "from_state": None,
                "to_state": "ready",
            },
            {
                "at": "2026-07-17T08:05:00Z",
                "from_state": "ready",
                "to_state": "error",
                "error_code": "linkedin_oauth_refresh_failed",
            },
        ],
        variants=[
            {
                "variant": "executive-recruiter",
                "publish_state": "failed",
                "linkedin_publication": {
                    "last_error_code": "linkedin_publish_api_error"
                },
            },
            {
                "variant": "technical-architect",
                "publish_state": "failed",
                "linkedin_publication": {
                    "last_error_code": (
                        "linkedin_article_preview_public_repo_not_configured"
                    )
                },
            },
            {
                "variant": "engineering-leadership",
                "publish_state": "failed",
                "linkedin_publication": {
                    "last_error_code": (
                        "linkedin_preview_validation_checkout_missing"
                    )
                },
            },
        ],
    )

    with (
        patch("subprocess.run") as git_or_shell,
        patch("httpx.request") as external_http,
    ):
        result = get_flow_a_operational_status(operational_base, now_utc=NOW)
    git_or_shell.assert_not_called()
    external_http.assert_not_called()

    body = result.to_dict()
    assert body["summary"]["dependency_failures"] == {
        "comfyui": 2,
        "deepseek": 2,
        "github_pages_checkout": 3,
        "linkedin": 2,
        "unclassified": 1,
    }
    entries = {
        entry["dependency"]: entry for entry in body["dependency_failures"]
    }
    assert [entry["dependency"] for entry in body["dependency_failures"]] == [
        "comfyui",
        "deepseek",
        "github_pages_checkout",
        "linkedin",
        "unclassified",
    ]
    assert entries["comfyui"]["error_codes"] == [
        "blog_image_generation_comfyui_failed",
        "comfyui_connection_refused",
    ]
    assert entries["deepseek"] == {
        "dependency": "deepseek",
        "failure_count": 2,
        "error_codes": ["deepseek_timeout"],
        "campaign_ids": [CAMPAIGN_ID],
        "run_ids": ["run-failed-deps"],
    }
    assert entries["github_pages_checkout"]["error_codes"] == [
        "blog_git_publication_push_failed",
        "linkedin_article_preview_public_repo_not_configured",
        "linkedin_preview_validation_checkout_missing",
    ]
    assert entries["linkedin"]["error_codes"] == [
        "linkedin_oauth_refresh_failed",
        "linkedin_publish_api_error",
    ]
    assert entries["unclassified"] == {
        "dependency": "unclassified",
        "failure_count": 1,
        "error_codes": ["mystery_code"],
        "campaign_ids": [CAMPAIGN_ID],
        "run_ids": [],
    }
    campaign = _campaign(result, CAMPAIGN_ID)
    assert campaign["dependency_failures"] == [
        {
            "dependency": "comfyui",
            "error_codes": ["blog_image_generation_comfyui_failed"],
        },
        {"dependency": "deepseek", "error_codes": ["deepseek_timeout"]},
        {
            "dependency": "github_pages_checkout",
            "error_codes": [
                "blog_git_publication_push_failed",
                "linkedin_article_preview_public_repo_not_configured",
                "linkedin_preview_validation_checkout_missing",
            ],
        },
        {
            "dependency": "linkedin",
            "error_codes": [
                "linkedin_oauth_refresh_failed",
                "linkedin_publish_api_error",
            ],
        },
        {"dependency": "unclassified", "error_codes": ["mystery_code"]},
    ]


def test_healthy_campaign_history_error_codes_are_not_dependency_failures(
    operational_base: Path,
):
    _write_campaign(
        operational_base,
        state="flow_a_complete",
        source_status={
            "location": "processed",
            "execution_state": "idle",
            "recovery_classification": "no_action",
        },
        errors=["deepseek_timeout"],
        state_history=[
            {
                "at": "2026-07-17T08:00:00Z",
                "from_state": None,
                "to_state": "flow_a_complete",
                "error_code": "comfyui_connection_refused",
            },
        ],
    )

    result = get_flow_a_operational_status(operational_base, now_utc=NOW)

    assert result.campaigns[0].successful is True
    assert result.dependency_failures == []
    assert result.summary["dependency_failures"] == {
        "comfyui": 0,
        "deepseek": 0,
        "github_pages_checkout": 0,
        "linkedin": 0,
        "unclassified": 0,
    }


def test_inverted_missing_clocks_and_inconsistent_history_data_issues(
    operational_base: Path,
):
    _write_run(
        operational_base,
        "run-inverted",
        started_at="2026-07-17T10:02:00Z",
        completed_at="2026-07-17T10:01:00Z",
    )
    _write_run(
        operational_base,
        "run-open",
        started_at="2026-07-17T10:00:00Z",
        completed_at=None,
    )
    _write_campaign(
        operational_base,
        state="validated",
        source_status={
            "location": "queued",
            "execution_state": "idle",
            "recovery_classification": "no_action",
            "processing_started_at": "2026-07-17T10:00:00Z",
            "last_progress_at": "2026-07-17T09:00:00Z",
        },
        state_history=[
            "not-a-dict",
            {
                "at": "2026-07-17T08:10:00Z",
                "from_state": None,
                "to_state": "ready",
            },
            {
                "at": "2026-07-17T08:00:00Z",
                "from_state": "ready",
                "to_state": "validated",
            },
            {
                "at": "2026-07-17T08:20:00Z",
                "from_state": "validated",
                "to_state": "blog_publish_pending",
            },
        ],
    )
    _write_campaign(
        operational_base,
        _campaign_id("future-history"),
        state="derivatives_pending",
        state_history=[
            {
                "at": "2099-01-01T00:00:00Z",
                "from_state": None,
                "to_state": "derivatives_pending",
            },
        ],
    )

    result = get_flow_a_operational_status(operational_base, now_utc=NOW)
    body = result.to_dict()

    assert result.status == "partial"
    reasons = {issue.reason for issue in result.data_issues}
    assert {
        RUN_CLOCK_INVERTED,
        CAMPAIGN_STAGE_HISTORY_INVALID,
        CAMPAIGN_STAGE_CLOCK_INVERTED,
        CAMPAIGN_STAGE_HISTORY_STATE_INCONSISTENT,
        CAMPAIGN_ATTEMPT_CLOCK_INVERTED,
    } <= reasons

    inverted_run = body["executions"]["successful"][0]
    assert inverted_run["run_id"] == "run-inverted"
    assert inverted_run["duration_seconds"] is None
    open_run = next(
        item
        for item in body["executions"]["successful"]
        if item["run_id"] == "run-open"
    )
    assert open_run["duration_seconds"] is None

    campaign = _campaign(result, CAMPAIGN_ID)
    assert campaign["attempt_duration_seconds"] is None
    # The inverted pair is omitted; the valid pair and the open stage remain.
    assert [
        (item["stage"], item["open"]) for item in campaign["stage_durations"]
    ] == [
        ("validated", False),
        ("blog_publish_pending", True),
    ]
    assert campaign["stage_durations"][0]["duration_seconds"] == 1200

    future = _campaign(result, _campaign_id("future-history"))
    assert future["stage_durations"] == [
        {
            "stage": "derivatives_pending",
            "started_at": "2099-01-01T00:00:00Z",
            "ended_at": None,
            "duration_seconds": None,
            "open": True,
            "from_state": None,
            "to_state": None,
        }
    ]


def test_stage_and_dependency_collections_sort_deterministically(
    operational_base: Path,
):
    _write_campaign(
        operational_base,
        state="validated",
        state_history=[
            {
                "at": "2026-07-17T08:00:00Z",
                "from_state": None,
                "to_state": "ready",
            },
            {
                "at": "2026-07-17T08:00:00Z",
                "from_state": "ready",
                "to_state": "validation_failed",
            },
            {
                "at": "2026-07-17T08:00:00Z",
                "from_state": "validation_failed",
                "to_state": "validated",
            },
        ],
    )
    before = _snapshot_tree(operational_base)

    first = get_flow_a_operational_status(operational_base, now_utc=NOW)
    second = get_flow_a_operational_status(operational_base, now_utc=NOW)

    assert first.to_dict() == second.to_dict()
    assert _snapshot_tree(operational_base) == before
    stages = [item.stage for item in first.campaigns[0].stage_durations]
    # Equal started_at values fall back to stage-name ascending order.
    assert stages == ["ready", "validated", "validation_failed"]
    open_flags = [item.open for item in first.campaigns[0].stage_durations]
    assert open_flags == [False, True, False]


def test_aggregation_module_has_no_mutating_or_external_service_imports():
    # US-027 requires dependency-bucket name constants such as "comfyui" and
    # "github_pages_checkout" in the module, so this guard inspects actual
    # imports instead of raw substrings while keeping the same intent: no
    # mutating helpers and no external-service clients.
    source = Path(operational_status_module.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "write_campaign_metadata",
        "save_calendar_atomic",
        "detect_stale_flow_a_execution",
    ):
        assert forbidden not in source

    imported_modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)
    for module_name in imported_modules:
        for forbidden in (
            "flow_a_operational_queue",
            "linkedin_publication_flow",
            "linkedin_client",
            "linkedin_oauth",
            "github_pages",
            "httpx",
            "requests",
            "subprocess",
            "deepseek",
            "comfyui",
        ):
            assert forbidden not in module_name


def test_http_auth_validation_shape_determinism_secrets_and_zero_mutation(
    operational_base: Path,
):
    _write_run(
        operational_base,
        "run-http",
        api_key="NEVER-RETURN-THIS",
        authorization="Bearer NEVER-RETURN-THIS",
        markdown_content="NEVER-RETURN-BODY",
    )
    _write_campaign(operational_base)
    before = _snapshot_tree(operational_base)
    client = TestClient(create_app(make_settings(operational_base)))

    with patch(
        "silverman_blog_linkedin.main.get_flow_a_operational_status"
    ) as aggregate:
        assert client.get("/flow-a/operational-status").status_code == 401
        aggregate.assert_not_called()
    invalid = client.get(
        "/flow-a/operational-status",
        headers=auth_header(),
        params={"now_utc": "2026-07-17T12:00:00+00:00"},
    )
    assert invalid.status_code == 422

    first = client.get(
        "/flow-a/operational-status",
        headers=auth_header(),
        params={"now_utc": NOW},
    )
    second = client.get(
        "/flow-a/operational-status",
        headers=auth_header(),
        params={"now_utc": NOW},
    )

    assert first.status_code == 200
    assert first.content == second.content
    body = first.json()
    assert body["observed_at_utc"] == NOW
    assert body["read_only"] is True
    assert set(body) == {
        "status",
        "observed_at_utc",
        "read_only",
        "stale_after_seconds",
        "summary",
        "executions",
        "campaigns",
        "delayed_calendar_items",
        "dependency_failures",
        "data_issues",
    }
    assert set(body["summary"]["dependency_failures"]) == {
        "comfyui",
        "deepseek",
        "github_pages_checkout",
        "linkedin",
        "unclassified",
    }
    assert set(body["summary"]["stage_durations"]) == {
        "campaigns_with_stage_durations",
        "executions_with_duration",
        "stage_intervals_reported",
    }
    serialized = first.text
    for forbidden in (
        "NEVER-RETURN-THIS",
        "NEVER-RETURN-BODY",
        str(operational_base),
        "authorization",
        "markdown_content",
    ):
        assert forbidden not in serialized
    assert _snapshot_tree(operational_base) == before
