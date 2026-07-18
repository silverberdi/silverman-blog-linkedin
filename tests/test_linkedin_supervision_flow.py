"""Behavioral tests for Flow A LinkedIn variant supervision (US-017, US-022)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.campaign_lifecycle import read_campaign_metadata
from silverman_blog_linkedin.linkedin_publication_flow import (
    LINKEDIN_PUBLISH_CANCEL_NOT_ALLOWED,
    LINKEDIN_PUBLISH_CONTENT_INVALID,
    LINKEDIN_PUBLISH_METADATA_WRITE_FAILED,
    LINKEDIN_PUBLISH_RECOVERY_EVIDENCE_INVALID,
    LINKEDIN_PUBLISH_TOKEN_INVALID,
    LINKEDIN_SUPERVISION_ACTION_NOT_ALLOWED,
    PUBLISH_STATE_CANCELLED,
    PUBLISH_STATE_FAILED,
    PUBLISH_STATE_PENDING,
    PUBLISH_STATE_QUEUED,
    RECOVERY_CLASS_CONTENT_INVALID,
    RECOVERY_CLASS_UNCERTAIN,
    cancel_linkedin_publication,
    publish_linkedin_due_variants,
    queue_linkedin_publication,
)
from silverman_blog_linkedin.linkedin_supervision_flow import (
    LINKEDIN_SUPERVISION_DEFER_DUPLICATE_SLOT,
    LINKEDIN_SUPERVISION_DEFER_SATURATION,
    LINKEDIN_SUPERVISION_DEFER_TIME_INVALID,
    LINKEDIN_SUPERVISION_EDIT_UNCHANGED,
    LINKEDIN_SUPERVISION_IDEMPOTENCY_CONFLICT,
    LINKEDIN_SUPERVISION_VARIANT_NOT_PENDING,
    SUPERVISION_PHASE_RECOVERY,
    correct_linkedin_variant,
    defer_linkedin_variant,
)
from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, make_settings
from tests.test_linkedin_publication import (
    CANONICAL_CAMPAIGN_ID,
    PAST_DUE_UTC,
    TARGET_VARIANT,
    US022_FAILED_AT,
    _distribution_scheduled_campaign,
    _make_failed_variant,
    _queue_variant,
    _real_publish_env,
    _update_variant,
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


def test_defer_with_console_source_audited(scheduled_base: Path):
    result = defer_linkedin_variant(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc=FUTURE_SCHEDULE,
        dry_run=False,
        reason="operator_choice",
        actor="operator",
        source="linkedin_variant_supervision_console",
        now=DEFER_NOW,
    )
    assert result.status == "completed"
    entry = _variant_entry(scheduled_base)
    supervision = entry["operator_supervision"]
    assert supervision["actor"] == "operator"
    assert supervision["source"] == "linkedin_variant_supervision_console"
    history = supervision["deferral_history"][0]
    assert history["source"] == "linkedin_variant_supervision_console"
    assert history["actor"] == "operator"
    assert history["previous_scheduled_at_utc"]
    assert history["new_scheduled_at_utc"] == FUTURE_SCHEDULE


def test_defer_without_source_remains_compatible(scheduled_base: Path):
    result = defer_linkedin_variant(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc=FUTURE_SCHEDULE,
        dry_run=False,
        now=DEFER_NOW,
    )
    assert result.status == "completed"
    entry = _variant_entry(scheduled_base)
    supervision = entry["operator_supervision"]
    assert supervision["actor"] == "operator"
    assert "source" not in supervision
    assert "source" not in supervision["deferral_history"][0]


def test_defer_duplicate_slot_rejected(scheduled_base: Path):
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    sibling = next(
        v
        for v in campaign["variants"]
        if v["variant"] != TARGET_VARIANT and v.get("publish_state") == PUBLISH_STATE_PENDING
    )
    sibling_id = sibling["variant"]
    _update_variant(scheduled_base, variant=sibling_id, scheduled_at_utc=FUTURE_SCHEDULE)

    before = json.dumps(_variant_entry(scheduled_base), sort_keys=True)
    result = defer_linkedin_variant(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc=FUTURE_SCHEDULE,
        dry_run=True,
        now=DEFER_NOW,
    )
    assert result.status == "failed"
    assert LINKEDIN_SUPERVISION_DEFER_DUPLICATE_SLOT in result.errors
    assert json.dumps(_variant_entry(scheduled_base), sort_keys=True) == before


def test_defer_same_day_saturation_rejected(scheduled_base: Path):
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    sibling = next(
        v
        for v in campaign["variants"]
        if v["variant"] != TARGET_VARIANT and v.get("publish_state") == PUBLISH_STATE_PENDING
    )
    sibling_id = sibling["variant"]
    # Same UTC day, different instant — within 72h by definition.
    _update_variant(
        scheduled_base,
        variant=sibling_id,
        scheduled_at_utc="2026-08-01T10:00:00Z",
    )

    before = json.dumps(_variant_entry(scheduled_base), sort_keys=True)
    result = defer_linkedin_variant(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc="2026-08-01T18:00:00Z",
        dry_run=False,
        now=DEFER_NOW,
    )
    assert result.status == "failed"
    assert LINKEDIN_SUPERVISION_DEFER_SATURATION in result.errors
    assert json.dumps(_variant_entry(scheduled_base), sort_keys=True) == before


def test_defer_does_not_write_calendar_json(scheduled_base: Path):
    calendar_path = scheduled_base / "editorial-calendar" / "calendar.json"
    calendar_path.parent.mkdir(parents=True, exist_ok=True)
    calendar_path.write_text('{"schema_version":"1","updated_at_utc":"2026-07-01T00:00:00Z","items":[]}', encoding="utf-8")
    before = calendar_path.read_bytes()

    result = defer_linkedin_variant(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc=FUTURE_SCHEDULE,
        dry_run=False,
        now=DEFER_NOW,
    )
    assert result.status == "completed"
    assert calendar_path.read_bytes() == before


def test_defer_endpoint_accepts_optional_source(client: TestClient):
    response = client.post(
        "/defer-linkedin-variant",
        headers=auth_header(),
        json={
            "campaign_id": CANONICAL_CAMPAIGN_ID,
            "variant": TARGET_VARIANT,
            "new_scheduled_at_utc": FUTURE_SCHEDULE,
            "dry_run": True,
            "source": "linkedin_variant_supervision_console",
            "actor": "operator",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_defer_endpoint_rejects_unauthenticated(client: TestClient):
    response = client.post(
        "/defer-linkedin-variant",
        json={
            "campaign_id": CANONICAL_CAMPAIGN_ID,
            "variant": TARGET_VARIANT,
            "new_scheduled_at_utc": FUTURE_SCHEDULE,
            "dry_run": True,
        },
    )
    assert response.status_code == 401


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


def test_cancel_failed_variant_now_supported_preserves_evidence(
    scheduled_base: Path,
):
    """US-022 extends cancel to `failed -> cancelled`; evidence is retained."""
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
    failure_evidence = dict(entry["linkedin_publication"])

    result = cancel_linkedin_publication(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
    )
    assert result.status == "completed"
    assert result.publish_state == PUBLISH_STATE_CANCELLED
    assert result.phase == "recovery"

    entry = _variant_entry(scheduled_base)
    assert entry["publish_state"] == PUBLISH_STATE_CANCELLED
    assert entry["linkedin_publication"] == failure_evidence
    assert len(entry["linkedin_publication_attempts"]) == 1
    assert entry["linkedin_recovery_history"][0]["action"] == "recovery_cancelled"
    mock_client.post.assert_called_once()


# --- US-022 failed-state correction and cancellation ---


def _make_content_invalid_failed_variant(
    base: Path, *, with_history: bool = True
) -> dict:
    return _make_failed_variant(
        base,
        error_code=LINKEDIN_PUBLISH_CONTENT_INVALID,
        http_status=422,
        retryable=False,
        with_history=with_history,
    )


def test_us022_correct_failed_content_invalid_keeps_failed_and_audits(
    scheduled_base: Path,
):
    before = _make_content_invalid_failed_variant(scheduled_base)
    old_hash = before["derivative_content_sha256"]
    attempts_before = json.dumps(
        before["linkedin_publication_attempts"], sort_keys=True
    )

    result = correct_linkedin_variant(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        draft_content=NEW_DRAFT,
        dry_run=False,
        reason="content_rejected_by_linkedin",
    )

    assert result.status == "completed"
    assert result.publish_state == PUBLISH_STATE_FAILED
    assert result.phase == SUPERVISION_PHASE_RECOVERY
    assert result.recovery_classification == RECOVERY_CLASS_CONTENT_INVALID
    assert result.artifact_written is True
    assert result.metadata_written is True

    entry = _variant_entry(scheduled_base)
    assert entry["publish_state"] == PUBLISH_STATE_FAILED
    new_hash = hashlib.sha256(NEW_DRAFT.encode()).hexdigest()
    assert entry["derivative_content_sha256"] == new_hash
    artifact_path = scheduled_base / entry["artifact_relative_path"]
    assert artifact_path.read_text(encoding="utf-8") == NEW_DRAFT

    # Original attempt evidence is retained byte-for-byte.
    assert (
        json.dumps(entry["linkedin_publication_attempts"], sort_keys=True)
        == attempts_before
    )
    assert entry["linkedin_publication"]["last_error_code"] == (
        LINKEDIN_PUBLISH_CONTENT_INVALID
    )

    event = entry["linkedin_recovery_history"][-1]
    assert event["action"] == "content_corrected"
    assert event["attempt_number"] == 1
    assert event["classification"] == RECOVERY_CLASS_CONTENT_INVALID
    assert event["previous_content_sha256"] == old_hash
    assert event["new_content_sha256"] == new_hash

    supervision = entry["operator_supervision"]
    assert supervision["last_action"] == "edit"
    assert supervision["phase"] == SUPERVISION_PHASE_RECOVERY
    assert supervision["auto_queue_eligible"] is False
    assert len(supervision["edit_history"]) == 1

    # No variant body text or secrets in the response payload.
    serialized = json.dumps(result.to_dict())
    assert NEW_DRAFT.splitlines()[0] not in serialized

    # Correction never queues or publishes: auto-queue still excludes it and
    # an explicit manual queue is required (and now allowed without
    # confirmation because correction evidence is mechanical).
    auto = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        publish_now=True,
        auto_queue_pending=True,
        environ=_real_publish_env(),
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert auto.auto_queue_results[0].skipped is True
    assert _variant_entry(scheduled_base)["publish_state"] == PUBLISH_STATE_FAILED

    queue_result = queue_linkedin_publication(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        publish_after_utc=PAST_DUE_UTC,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert queue_result.status == "completed", queue_result.errors
    assert queue_result.recovery_classification == RECOVERY_CLASS_CONTENT_INVALID
    assert _variant_entry(scheduled_base)["publish_state"] == PUBLISH_STATE_QUEUED


def test_us022_correct_failed_dry_run_and_idempotent_replay(scheduled_base: Path):
    _make_content_invalid_failed_variant(scheduled_base)
    before = json.dumps(_variant_entry(scheduled_base), sort_keys=True)
    artifact_path = scheduled_base / _variant_entry(scheduled_base)[
        "artifact_relative_path"
    ]
    artifact_before = artifact_path.read_text(encoding="utf-8")

    dry = correct_linkedin_variant(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        draft_content=NEW_DRAFT,
        dry_run=True,
    )
    assert dry.status == "completed"
    assert dry.dry_run is True
    assert dry.phase == SUPERVISION_PHASE_RECOVERY
    assert dry.publish_state == PUBLISH_STATE_FAILED
    assert json.dumps(_variant_entry(scheduled_base), sort_keys=True) == before
    assert artifact_path.read_text(encoding="utf-8") == artifact_before

    first = correct_linkedin_variant(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        draft_content=NEW_DRAFT,
        dry_run=False,
        idempotency_key="us022-correct-1",
    )
    assert first.status == "completed"
    entry_after_first = _variant_entry(scheduled_base)
    events_len = len(entry_after_first["linkedin_recovery_history"])
    edits_len = len(entry_after_first["operator_supervision"]["edit_history"])

    # Repeating the identical correction is rejected as unchanged (same
    # contract as pending edits) and never double-applies audit history.
    replay = correct_linkedin_variant(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        draft_content=NEW_DRAFT,
        dry_run=False,
        idempotency_key="us022-correct-1",
    )
    assert replay.status == "failed"
    assert LINKEDIN_SUPERVISION_EDIT_UNCHANGED in replay.errors
    entry_after_replay = _variant_entry(scheduled_base)
    assert len(entry_after_replay["linkedin_recovery_history"]) == events_len
    assert (
        len(entry_after_replay["operator_supervision"]["edit_history"]) == edits_len
    )


def test_us022_correct_failed_unchanged_content_rejected(scheduled_base: Path):
    _make_content_invalid_failed_variant(scheduled_base)
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
    assert _variant_entry(scheduled_base)["publish_state"] == PUBLISH_STATE_FAILED


@pytest.mark.parametrize(
    ("error_code", "http_status"),
    [
        ("linkedin_publish_api_error", 500),
        (LINKEDIN_PUBLISH_TOKEN_INVALID, 401),
        ("linkedin_publish_api_error", None),
    ],
)
def test_us022_correct_failed_other_class_rejected_without_mutation(
    scheduled_base: Path, error_code: str, http_status: int | None
):
    _make_failed_variant(
        scheduled_base, error_code=error_code, http_status=http_status
    )
    before = json.dumps(_variant_entry(scheduled_base), sort_keys=True)
    artifact_path = scheduled_base / _variant_entry(scheduled_base)[
        "artifact_relative_path"
    ]
    artifact_before = artifact_path.read_text(encoding="utf-8")

    result = correct_linkedin_variant(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        draft_content=NEW_DRAFT,
        dry_run=False,
    )

    assert result.status == "failed"
    assert LINKEDIN_SUPERVISION_ACTION_NOT_ALLOWED in result.errors
    assert json.dumps(_variant_entry(scheduled_base), sort_keys=True) == before
    assert artifact_path.read_text(encoding="utf-8") == artifact_before


def test_us022_correct_failed_invalid_evidence_fails_closed(scheduled_base: Path):
    _update_variant(
        scheduled_base,
        publish_state=PUBLISH_STATE_FAILED,
        linkedin_publication={"last_error_code": LINKEDIN_PUBLISH_CONTENT_INVALID},
    )
    before = json.dumps(_variant_entry(scheduled_base), sort_keys=True)

    result = correct_linkedin_variant(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        draft_content=NEW_DRAFT,
        dry_run=False,
    )

    assert result.status == "failed"
    assert LINKEDIN_PUBLISH_RECOVERY_EVIDENCE_INVALID in result.errors
    assert json.dumps(_variant_entry(scheduled_base), sort_keys=True) == before


def test_us022_correct_failed_legacy_variant_normalizes_attempt_first(
    scheduled_base: Path,
):
    before = _make_content_invalid_failed_variant(scheduled_base, with_history=False)
    assert "linkedin_publication_attempts" not in before
    original_hash = before["derivative_content_sha256"]

    result = correct_linkedin_variant(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        draft_content=NEW_DRAFT,
        dry_run=False,
    )
    assert result.status == "completed"

    entry = _variant_entry(scheduled_base)
    attempts = entry["linkedin_publication_attempts"]
    assert len(attempts) == 1
    assert attempts[0]["attempt_number"] == 1
    assert attempts[0]["attempted_at"] == US022_FAILED_AT
    # Attempt 1 records the original (pre-correction) content hash.
    assert attempts[0]["derivative_content_sha256"] == original_hash
    event = entry["linkedin_recovery_history"][-1]
    assert event["action"] == "content_corrected"
    assert event["previous_content_sha256"] == original_hash


def test_us022_correct_failed_metadata_write_failure_reported(scheduled_base: Path):
    _make_content_invalid_failed_variant(scheduled_base)

    with patch(
        "silverman_blog_linkedin.linkedin_supervision_flow.write_campaign_metadata",
        return_value=MagicMock(written=False),
    ):
        result = correct_linkedin_variant(
            scheduled_base,
            campaign_id=CANONICAL_CAMPAIGN_ID,
            variant=TARGET_VARIANT,
            draft_content=NEW_DRAFT,
            dry_run=False,
        )

    assert result.status == "failed"
    assert LINKEDIN_PUBLISH_METADATA_WRITE_FAILED in result.errors
    assert result.artifact_written is True
    assert result.metadata_written is False
    # Persisted metadata still holds the original hash and no recovery event.
    entry = _variant_entry(scheduled_base)
    assert "linkedin_recovery_history" not in entry


def test_us022_cancel_exhausted_failed_variant_preserves_all_evidence(
    scheduled_base: Path,
):
    _make_failed_variant(scheduled_base, attempt_count=3)
    before = _variant_entry(scheduled_base)
    evidence_before = json.dumps(before["linkedin_publication"], sort_keys=True)
    attempts_before = json.dumps(
        before["linkedin_publication_attempts"], sort_keys=True
    )

    result = cancel_linkedin_publication(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        reason="retry_budget_exhausted",
    )

    assert result.status == "completed"
    assert result.publish_state == PUBLISH_STATE_CANCELLED
    assert result.phase == SUPERVISION_PHASE_RECOVERY
    assert result.publication_attempt_count == 3
    assert result.manual_retries_used == 2
    assert result.manual_retries_remaining == 0

    entry = _variant_entry(scheduled_base)
    assert entry["publish_state"] == PUBLISH_STATE_CANCELLED
    assert json.dumps(entry["linkedin_publication"], sort_keys=True) == (
        evidence_before
    )
    assert (
        json.dumps(entry["linkedin_publication_attempts"], sort_keys=True)
        == attempts_before
    )
    event = entry["linkedin_recovery_history"][-1]
    assert event["action"] == "recovery_cancelled"
    assert event["attempt_number"] == 3
    assert event["reason"] == "retry_budget_exhausted"
    assert entry["operator_supervision"]["auto_queue_eligible"] is False
    assert "cancelled_at" not in entry["linkedin_publication"]


def test_us022_cancel_failed_dry_run_reports_counters_without_mutation(
    scheduled_base: Path,
):
    _make_failed_variant(
        scheduled_base, error_code="linkedin_publish_api_error", http_status=None
    )
    before = json.dumps(_variant_entry(scheduled_base), sort_keys=True)

    result = cancel_linkedin_publication(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=True,
    )

    assert result.status == "completed"
    assert result.dry_run is True
    assert result.phase == SUPERVISION_PHASE_RECOVERY
    assert result.recovery_classification == RECOVERY_CLASS_UNCERTAIN
    assert result.publication_attempt_count == 1
    assert result.metadata_written is False
    assert json.dumps(_variant_entry(scheduled_base), sort_keys=True) == before


def test_us022_cancel_failed_invalid_evidence_fails_closed(scheduled_base: Path):
    _update_variant(
        scheduled_base,
        publish_state=PUBLISH_STATE_FAILED,
        linkedin_publication=None,
    )
    before = json.dumps(_variant_entry(scheduled_base), sort_keys=True)

    result = cancel_linkedin_publication(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
    )

    assert result.status == "failed"
    assert LINKEDIN_PUBLISH_RECOVERY_EVIDENCE_INVALID in result.errors
    assert json.dumps(_variant_entry(scheduled_base), sort_keys=True) == before
