"""Behavioral tests for the read-only Flow A operational status view."""

from __future__ import annotations

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
    CAMPAIGN_FILE_PATH_OUTSIDE_SOURCE,
    CAMPAIGN_ID_FILENAME_MISMATCH,
    LINKEDIN_PUBLISH_STATE_INVALID,
    LINKEDIN_TIMESTAMP_INVALID,
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


def test_aggregation_module_has_no_mutating_or_external_service_imports():
    source = Path(operational_status_module.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "write_campaign_metadata",
        "save_calendar_atomic",
        "detect_stale_flow_a_execution",
        "flow_a_operational_queue",
        "linkedin_publication_flow",
        "github_pages",
        "httpx",
        "requests",
        "subprocess",
        "deepseek",
        "comfyui",
    ):
        assert forbidden not in source


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
        "data_issues",
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
