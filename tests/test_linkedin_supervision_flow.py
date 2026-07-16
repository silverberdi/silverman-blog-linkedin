"""Behavioral tests for Flow A LinkedIn variant supervision (US-017)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.campaign_lifecycle import read_campaign_metadata
from silverman_blog_linkedin.linkedin_publication_flow import (
    LINKEDIN_PUBLISH_CANCEL_NOT_ALLOWED,
    LINKEDIN_SUPERVISION_ACTION_NOT_ALLOWED,
    PUBLISH_STATE_CANCELLED,
    PUBLISH_STATE_PENDING,
    PUBLISH_STATE_QUEUED,
    cancel_linkedin_publication,
    publish_linkedin_due_variants,
)
from silverman_blog_linkedin.linkedin_supervision_flow import (
    LINKEDIN_SUPERVISION_DEFER_TIME_INVALID,
    LINKEDIN_SUPERVISION_EDIT_UNCHANGED,
    LINKEDIN_SUPERVISION_IDEMPOTENCY_CONFLICT,
    LINKEDIN_SUPERVISION_VARIANT_NOT_PENDING,
    correct_linkedin_variant,
    defer_linkedin_variant,
)
from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, make_settings
from tests.test_linkedin_publication import (
    CANONICAL_CAMPAIGN_ID,
    TARGET_VARIANT,
    _distribution_scheduled_campaign,
    _queue_variant,
    _real_publish_env,
)

NEW_DRAFT = (
    "Revised LinkedIn draft for executive recruiters.\n"
    "Read the full story here: https://silverman.pro/2026/07/06/why-i-did-not-start-with-the-database/\n"
)
FUTURE_SCHEDULE = "2026-08-01T14:00:00Z"
DEFER_NOW = datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def editorial_base(tmp_path: Path) -> Path:
    from tests.test_linkedin_publication import _setup_metadata_campaigns

    _setup_metadata_campaigns(tmp_path)
    (tmp_path / "linkedin-posts").mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def scheduled_base(editorial_base: Path) -> Path:
    _distribution_scheduled_campaign(editorial_base)
    return editorial_base


@pytest.fixture
def client(scheduled_base: Path) -> TestClient:
    return TestClient(create_app(make_settings(scheduled_base)))


def _variant_entry(base: Path) -> dict:
    campaign = read_campaign_metadata(base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    return next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)


def test_correct_pending_variant_updates_artifact_hash_and_history(scheduled_base: Path):
    before = _variant_entry(scheduled_base)
    old_hash = before["derivative_content_sha256"]

    result = correct_linkedin_variant(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        draft_content=NEW_DRAFT,
        dry_run=False,
        reason="criteria_failure",
    )

    assert result.status == "completed"
    assert result.metadata_written is True
    assert result.artifact_written is True
    assert result.phase == "pre_queue"

    entry = _variant_entry(scheduled_base)
    assert entry["publish_state"] == PUBLISH_STATE_PENDING
    assert entry["derivative_content_sha256"] != old_hash
    assert entry["derivative_content_sha256"] == hashlib.sha256(NEW_DRAFT.encode()).hexdigest()

    artifact_path = scheduled_base / entry["artifact_relative_path"]
    assert artifact_path.read_text(encoding="utf-8") == NEW_DRAFT

    supervision = entry["operator_supervision"]
    assert supervision["last_action"] == "edit"
    assert supervision["auto_queue_eligible"] is True
    assert len(supervision["edit_history"]) == 1
    assert supervision["edit_history"][0]["previous_content_sha256"] == old_hash
    assert supervision["edit_history"][0]["reason"] == "criteria_failure"


def test_defer_pending_variant_updates_schedule_and_blocks_auto_queue(scheduled_base: Path):
    before = _variant_entry(scheduled_base)
    previous_schedule = before["scheduled_at_utc"]

    result = defer_linkedin_variant(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc=FUTURE_SCHEDULE,
        dry_run=False,
        now=DEFER_NOW,
    )

    assert result.status == "completed"
    assert result.scheduled_at_utc == FUTURE_SCHEDULE

    entry = _variant_entry(scheduled_base)
    assert entry["publish_state"] == PUBLISH_STATE_PENDING
    assert entry["scheduled_at_utc"] == FUTURE_SCHEDULE
    supervision = entry["operator_supervision"]
    assert supervision["last_action"] == "defer"
    assert supervision["auto_queue_eligible"] is False
    assert len(supervision["deferral_history"]) == 1
    assert supervision["deferral_history"][0]["previous_scheduled_at_utc"] == previous_schedule


def test_cancel_pending_variant_sets_pre_queue_phase(scheduled_base: Path):
    result = cancel_linkedin_publication(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        reason="operator_choice",
    )

    assert result.status == "completed"
    assert result.publish_state == PUBLISH_STATE_CANCELLED
    assert result.phase == "pre_queue"

    entry = _variant_entry(scheduled_base)
    assert entry["publish_state"] == PUBLISH_STATE_CANCELLED
    supervision = entry["operator_supervision"]
    assert supervision["cancellation"]["phase"] == "pre_queue"
    assert supervision["auto_queue_eligible"] is False
    assert "linkedin_publication" not in entry


def test_cancel_queued_variant_preserves_post_queue_semantics(scheduled_base: Path):
    _queue_variant(scheduled_base)

    result = cancel_linkedin_publication(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
    )

    assert result.status == "completed"
    assert result.phase == "post_queue"

    entry = _variant_entry(scheduled_base)
    assert entry["publish_state"] == PUBLISH_STATE_CANCELLED
    assert entry["linkedin_publication"]["cancelled_at"]
    supervision = entry["operator_supervision"]
    assert supervision["cancellation"]["phase"] == "post_queue"


def test_reject_edit_and_defer_on_queued(scheduled_base: Path):
    _queue_variant(scheduled_base)

    edit_result = correct_linkedin_variant(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        draft_content=NEW_DRAFT,
        dry_run=False,
    )
    assert edit_result.status == "failed"
    assert LINKEDIN_SUPERVISION_VARIANT_NOT_PENDING in edit_result.errors

    defer_result = defer_linkedin_variant(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc=FUTURE_SCHEDULE,
        dry_run=False,
        now=DEFER_NOW,
    )
    assert defer_result.status == "failed"
    assert LINKEDIN_SUPERVISION_VARIANT_NOT_PENDING in defer_result.errors


def test_reject_cancel_on_published(scheduled_base: Path):
    from unittest.mock import MagicMock

    past = datetime(2026, 7, 7, 10, 0, 0, tzinfo=timezone.utc)
    _queue_variant(scheduled_base, publish_after_utc="2026-07-07T09:00:00Z", now=past)

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.headers = {"x-restli-id": "urn:li:share:published"}
    mock_client.post.return_value = mock_response

    publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )

    result = cancel_linkedin_publication(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
    )
    assert result.status == "failed"
    assert LINKEDIN_PUBLISH_CANCEL_NOT_ALLOWED in result.errors


def test_dry_run_does_not_mutate(scheduled_base: Path):
    before = _variant_entry(scheduled_base)
    artifact_path = scheduled_base / before["artifact_relative_path"]
    before_artifact = artifact_path.read_text(encoding="utf-8")

    correct = correct_linkedin_variant(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        draft_content=NEW_DRAFT,
        dry_run=True,
    )
    defer = defer_linkedin_variant(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc=FUTURE_SCHEDULE,
        dry_run=True,
        now=DEFER_NOW,
    )
    cancel = cancel_linkedin_publication(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=True,
    )

    assert correct.status == "completed" and correct.dry_run is True
    assert defer.status == "completed" and defer.dry_run is True
    assert cancel.status == "completed" and cancel.dry_run is True

    after = _variant_entry(scheduled_base)
    assert after["publish_state"] == PUBLISH_STATE_PENDING
    assert after["derivative_content_sha256"] == before["derivative_content_sha256"]
    assert after["scheduled_at_utc"] == before["scheduled_at_utc"]
    assert artifact_path.read_text(encoding="utf-8") == before_artifact
    assert "operator_supervision" not in after


def test_idempotent_defer_replay(scheduled_base: Path):
    first = defer_linkedin_variant(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc=FUTURE_SCHEDULE,
        dry_run=False,
        idempotency_key="defer-key-1",
        now=DEFER_NOW,
    )
    assert first.status == "completed"

    entry_after_first = _variant_entry(scheduled_base)
    history_len = len(entry_after_first["operator_supervision"]["deferral_history"])

    second = defer_linkedin_variant(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc=FUTURE_SCHEDULE,
        dry_run=False,
        idempotency_key="defer-key-1",
        now=DEFER_NOW,
    )
    assert second.status == "completed"

    entry_after_second = _variant_entry(scheduled_base)
    assert (
        len(entry_after_second["operator_supervision"]["deferral_history"]) == history_len
    )


def test_idempotency_conflict_on_mismatched_payload(scheduled_base: Path):
    defer_linkedin_variant(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc=FUTURE_SCHEDULE,
        dry_run=False,
        idempotency_key="defer-key-conflict",
        now=DEFER_NOW,
    )

    conflict = defer_linkedin_variant(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc="2026-08-02T14:00:00Z",
        dry_run=False,
        idempotency_key="defer-key-conflict",
        now=DEFER_NOW,
    )
    assert conflict.status == "failed"
    assert LINKEDIN_SUPERVISION_IDEMPOTENCY_CONFLICT in conflict.errors


def test_edit_unchanged_content_rejected(scheduled_base: Path):
    entry = _variant_entry(scheduled_base)
    artifact_path = scheduled_base / entry["artifact_relative_path"]
    same_content = artifact_path.read_text(encoding="utf-8")

    result = correct_linkedin_variant(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        draft_content=same_content,
        dry_run=False,
    )
    assert result.status == "failed"
    assert LINKEDIN_SUPERVISION_EDIT_UNCHANGED in result.errors


def test_defer_past_time_rejected(scheduled_base: Path):
    result = defer_linkedin_variant(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc="2026-07-06T14:00:00Z",
        dry_run=False,
        now=DEFER_NOW,
    )
    assert result.status == "failed"
    assert LINKEDIN_SUPERVISION_DEFER_TIME_INVALID in result.errors


def test_supervision_endpoints_do_not_require_publication_enabled(client: TestClient):
    """Supervision routes are pre-API and do not consult publication enablement."""
    response_correct = client.post(
        "/correct-linkedin-variant",
        headers=auth_header(),
        json={
            "campaign_id": CANONICAL_CAMPAIGN_ID,
            "variant": TARGET_VARIANT,
            "draft_content": NEW_DRAFT,
            "dry_run": True,
        },
    )
    assert response_correct.status_code == 200
    assert response_correct.json()["status"] == "completed"

    response_defer = client.post(
        "/defer-linkedin-variant",
        headers=auth_header(),
        json={
            "campaign_id": CANONICAL_CAMPAIGN_ID,
            "variant": TARGET_VARIANT,
            "new_scheduled_at_utc": FUTURE_SCHEDULE,
            "dry_run": True,
        },
    )
    assert response_defer.status_code == 200
    assert response_defer.json()["status"] == "completed"


def test_cancel_failed_variant_rejected(scheduled_base: Path):
    from unittest.mock import MagicMock

    _queue_variant(scheduled_base, publish_after_utc="2026-07-07T09:00:00Z")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_client.post.return_value = mock_response

    publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )

    entry = _variant_entry(scheduled_base)
    assert entry["publish_state"] == "failed"

    result = cancel_linkedin_publication(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
    )
    assert result.status == "failed"
    assert LINKEDIN_SUPERVISION_ACTION_NOT_ALLOWED in result.errors
