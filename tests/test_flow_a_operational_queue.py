"""Tests for Flow A operational queue lifecycle."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from silverman_blog_linkedin.campaign_lifecycle import (
    ACTOR_WORKER,
    CampaignMetadataWriteResult,
    EXECUTION_STATE_IDLE,
    EXECUTION_STATE_PROCESSING,
    EXECUTION_STATE_STALE,
    FLOW_A,
    FLOW_B,
    INVALID_OPERATIONAL_TRANSITION,
    RECOVERY_NO_ACTION,
    RECOVERY_MANUAL_INTERVENTION_REQUIRED,
    RECOVERY_REPAIR_REQUIRED,
    RECOVERY_RETRYABLE,
    RECOVERY_REQUEUE_REQUIRED,
    SOURCE_LOCATION_ERROR,
    SOURCE_LOCATION_PROCESSED,
    SOURCE_LOCATION_QUEUED,
    SOURCE_LOCATION_READY,
    PHYSICAL_MOVE_STATE_FAILED,
    PHYSICAL_MOVE_STATE_PARTIAL,
    STATE_BLOG_PUBLISH_PENDING,
    STATE_BLOG_PUBLISHED,
    STATE_DERIVATIVES_GENERATED,
    STATE_DERIVATIVES_PENDING,
    STATE_DISTRIBUTION_SCHEDULED,
    STATE_FLOW_A_COMPLETE,
    STATE_READY,
    STATE_VALIDATED,
    InvalidOperationalTransition,
    build_initial_campaign_metadata,
    build_blog_publish_idempotency_key,
    compute_source_content_sha256,
    read_campaign_metadata,
    transition_state,
    validate_operational_transition,
    write_campaign_metadata,
)
from silverman_blog_linkedin.flow_a_config import (
    ENV_FLOW_A_PROCESSING_STALE_SECONDS,
    FLOW_A_PROCESSING_STALE_SECONDS_INVALID,
    FlowAConfigurationError,
    load_flow_a_processing_stale_seconds,
)
from silverman_blog_linkedin.flow_a_hidden_artifacts import is_hidden_artifact_basename
from silverman_blog_linkedin.flow_a_operational_queue import (
    CALENDAR_CAMPAIGN_ID_CONFLICT,
    CAMPAIGN_METADATA_WRITE_FAILED,
    FLOW_A_EXECUTION_ALREADY_CLAIMED,
    FLOW_A_EXECUTION_ALREADY_RELEASED,
    FLOW_A_EXECUTION_STALE_RELEASE_NOT_ALLOWED,
    FLOW_A_QUEUE_DESTINATION_COLLISION,
    FLOW_A_QUEUE_PATH_UNSAFE,
    FLOW_A_REQUEUE_NOT_IN_ERROR,
    QUEUE_ACCEPTANCE_COMPLETED,
    QUEUE_ACCEPTANCE_FAILED,
    QUEUE_ACCEPTANCE_PARTIAL,
    QUEUE_ACCEPTANCE_REPAIR_REQUIRED,
    QUEUE_ACCEPTANCE_SKIPPED_ALREADY_QUEUED,
    accept_flow_a_source_for_queue,
    claim_flow_a_execution,
    detect_stale_flow_a_execution,
    ExecutionClaimResult,
    is_execution_stale,
    move_queued_source_to_error,
    record_flow_a_progress,
    requeue_flow_a_source_from_error,
    release_flow_a_execution,
)
from silverman_blog_linkedin.flow_a_source_lifecycle import complete_flow_a_source_lifecycle
from silverman_blog_linkedin.flow_a_source_moves import (
    CoordinatedMoveResult,
    ComponentMoveResult,
    DestinationFolder,
    coordinated_source_move,
)
from silverman_blog_linkedin.ready_scan import scan_ready_folder
from tests.conftest import create_full_layout

SOURCE_SLUG = "02-example-post"
PUBLIC_SLUG = "example-post"
PUBLICATION_DATE = "2026-07-06"
READY_RELATIVE = f"blog-posts/ready/{SOURCE_SLUG}.md"
QUEUED_RELATIVE = f"blog-posts/queued/{SOURCE_SLUG}.md"
IMAGE_READY = f"blog-posts/ready/{SOURCE_SLUG}.png"
CAMPAIGN_ID = f"flow-a-{PUBLICATION_DATE}-{PUBLIC_SLUG}"
SOURCE_MARKDOWN = "# Example\n\nBody content.\n"
CALENDAR_ITEM = {
    "campaign_id": CAMPAIGN_ID,
    "due_at_utc": "2026-07-06T14:00:00Z",
}


@pytest.fixture
def editorial_base(tmp_path: Path) -> Path:
    base = tmp_path / "editorial"
    create_full_layout(base)
    return base


def _write_ready(base: Path, *, with_image: bool = True) -> None:
    ready = base / "blog-posts" / "ready"
    ready.mkdir(parents=True, exist_ok=True)
    (ready / f"{SOURCE_SLUG}.md").write_text(SOURCE_MARKDOWN, encoding="utf-8")
    if with_image:
        (ready / f"{SOURCE_SLUG}.png").write_bytes(b"png")


def _calendar_item(**overrides) -> dict:
    payload = dict(CALENDAR_ITEM)
    payload.update(overrides)
    return payload


def test_operational_transition_table_allows_ready_to_queued():
    validate_operational_transition(
        from_location=SOURCE_LOCATION_READY,
        from_execution=EXECUTION_STATE_IDLE,
        to_location=SOURCE_LOCATION_QUEUED,
        to_execution=EXECUTION_STATE_IDLE,
    )


def test_invalid_ready_to_processed_transition_rejected():
    with pytest.raises(InvalidOperationalTransition) as exc:
        validate_operational_transition(
            from_location=SOURCE_LOCATION_READY,
            from_execution=EXECUTION_STATE_IDLE,
            to_location=SOURCE_LOCATION_PROCESSED,
            to_execution=EXECUTION_STATE_IDLE,
        )
    assert exc.value.error_code == INVALID_OPERATIONAL_TRANSITION


def test_stale_seconds_config_defaults_and_minimum():
    assert load_flow_a_processing_stale_seconds({}) == 3600
    assert load_flow_a_processing_stale_seconds({ENV_FLOW_A_PROCESSING_STALE_SECONDS: "60"}) == 60


def test_stale_seconds_invalid_raises():
    with pytest.raises(FlowAConfigurationError) as exc:
        load_flow_a_processing_stale_seconds({ENV_FLOW_A_PROCESSING_STALE_SECONDS: "30"})
    assert exc.value.error_code == FLOW_A_PROCESSING_STALE_SECONDS_INVALID


def test_queue_acceptance_moves_ready_to_queued_preserving_filename(editorial_base: Path):
    _write_ready(editorial_base, with_image=False)
    result = accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    assert result.queue_acceptance_status == QUEUE_ACCEPTANCE_COMPLETED
    assert (editorial_base / QUEUED_RELATIVE).is_file()
    assert not (editorial_base / READY_RELATIVE).exists()
    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["source_file_status"]["location"] == SOURCE_LOCATION_QUEUED
    assert campaign["source_slug"] == SOURCE_SLUG
    assert campaign["public_slug"] == PUBLIC_SLUG


def test_source_without_calendar_match_not_accepted(editorial_base: Path):
    _write_ready(editorial_base, with_image=False)
    result = accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=None,
    )
    assert result.status == "failed"
    assert (editorial_base / READY_RELATIVE).is_file()


def test_unsafe_path_never_moves_to_error(editorial_base: Path):
    result = accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path="blog-posts/ready/../processed/evil.md",
        calendar_item=_calendar_item(),
    )
    assert FLOW_A_QUEUE_PATH_UNSAFE in result.errors
    assert not list((editorial_base / "blog-posts" / "error").glob("*.md"))


def test_same_campaign_same_hash_queued_collision_idempotent(editorial_base: Path):
    _write_ready(editorial_base, with_image=False)
    first = accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    assert first.queue_acceptance_status == QUEUE_ACCEPTANCE_COMPLETED
    second = accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    assert second.queue_acceptance_status == QUEUE_ACCEPTANCE_SKIPPED_ALREADY_QUEUED


def test_conflicting_queued_destination_rejected(editorial_base: Path):
    _write_ready(editorial_base, with_image=False)
    queued = editorial_base / "blog-posts" / "queued" / f"{SOURCE_SLUG}.md"
    queued.parent.mkdir(parents=True, exist_ok=True)
    queued.write_text("different content", encoding="utf-8")
    other_campaign = build_initial_campaign_metadata(
        flow=FLOW_A,
        source_slug=SOURCE_SLUG,
        public_slug=PUBLIC_SLUG,
        source_relative_path=QUEUED_RELATIVE,
        image_relative_path="",
        source_content="different content",
        publication_date=PUBLICATION_DATE,
    )
    other_campaign["campaign_id"] = "flow-a-2026-07-06-other"
    write_campaign_metadata(editorial_base, other_campaign["campaign_id"], other_campaign)

    result = accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    assert FLOW_A_QUEUE_DESTINATION_COLLISION in result.errors
    assert result.recovery_classification == RECOVERY_REPAIR_REQUIRED


def test_claim_and_duplicate_active_claim_rejection(editorial_base: Path):
    _write_ready(editorial_base, with_image=False)
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    first_claim = claim_flow_a_execution(editorial_base, campaign_id=CAMPAIGN_ID)
    assert first_claim.status == "completed"
    assert first_claim.execution_state == EXECUTION_STATE_PROCESSING

    duplicate = claim_flow_a_execution(editorial_base, campaign_id=CAMPAIGN_ID)
    assert duplicate.status == "failed"
    assert FLOW_A_EXECUTION_ALREADY_CLAIMED in duplicate.errors
    assert duplicate.already_claimed is True
    assert duplicate.recovery_classification == RECOVERY_MANUAL_INTERVENTION_REQUIRED
    assert duplicate.metadata_written is False


def test_stale_detection_from_last_progress_at(editorial_base: Path):
    _write_ready(editorial_base, with_image=False)
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    claim_flow_a_execution(editorial_base, campaign_id=CAMPAIGN_ID)
    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    status = campaign["source_file_status"]
    past = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    status["last_progress_at"] = past
    status["processing_lease_expires_at"] = past
    campaign["source_file_status"] = status
    write_campaign_metadata(editorial_base, CAMPAIGN_ID, campaign)

    assert is_execution_stale(status, stale_seconds=60) is True
    stale_result = detect_stale_flow_a_execution(editorial_base, campaign_id=CAMPAIGN_ID)
    assert stale_result.execution_state == EXECUTION_STATE_STALE


def test_stale_reclaim_with_new_attempt_id(editorial_base: Path):
    _write_ready(editorial_base, with_image=False)
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    first = claim_flow_a_execution(editorial_base, campaign_id=CAMPAIGN_ID)
    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    status = campaign["source_file_status"]
    status["execution_state"] = EXECUTION_STATE_STALE
    status["last_progress_at"] = "2020-01-01T00:00:00Z"
    campaign["source_file_status"] = status
    write_campaign_metadata(editorial_base, CAMPAIGN_ID, campaign)

    reclaimed = claim_flow_a_execution(editorial_base, campaign_id=CAMPAIGN_ID)
    assert reclaimed.status == "completed"
    assert reclaimed.reclaimed_from_stale is True
    assert reclaimed.attempt_count == (first.attempt_count or 0) + 1
    assert reclaimed.execution_attempt_id != first.execution_attempt_id


def test_transient_failure_release_and_retry(editorial_base: Path):
    _write_ready(editorial_base, with_image=False)
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    claim_flow_a_execution(editorial_base, campaign_id=CAMPAIGN_ID)
    release = release_flow_a_execution(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        recovery_classification=RECOVERY_RETRYABLE,
    )
    assert release.status == "completed"
    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["source_file_status"]["execution_state"] == EXECUTION_STATE_IDLE
    assert campaign["source_file_status"]["recovery_classification"] == RECOVERY_RETRYABLE
    assert (editorial_base / QUEUED_RELATIVE).is_file()


def test_defensive_release_after_terminal_completion_is_idempotent(editorial_base: Path):
    _write_ready(editorial_base, with_image=True)
    campaign = build_initial_campaign_metadata(
        flow=FLOW_A,
        source_slug=SOURCE_SLUG,
        public_slug=PUBLIC_SLUG,
        source_relative_path=QUEUED_RELATIVE,
        image_relative_path=f"blog-posts/queued/{SOURCE_SLUG}.png",
        source_content=SOURCE_MARKDOWN,
        publication_date=PUBLICATION_DATE,
    )
    for to_state, reason in (
        (STATE_VALIDATED, "validated"),
        (STATE_BLOG_PUBLISH_PENDING, "publish pending"),
        (STATE_BLOG_PUBLISHED, "published"),
        (STATE_DERIVATIVES_PENDING, "derivatives pending"),
        (STATE_DERIVATIVES_GENERATED, "derivatives generated"),
        (STATE_DISTRIBUTION_SCHEDULED, "scheduled"),
    ):
        transition_state(campaign, to_state, reason=reason, actor=ACTOR_WORKER)
    campaign["queued_source_relative_path"] = QUEUED_RELATIVE
    campaign["source_file_status"]["location"] = SOURCE_LOCATION_QUEUED
    write_campaign_metadata(editorial_base, CAMPAIGN_ID, campaign)
    queued = editorial_base / "blog-posts" / "queued"
    (queued / f"{SOURCE_SLUG}.md").write_text(SOURCE_MARKDOWN, encoding="utf-8")
    (queued / f"{SOURCE_SLUG}.png").write_bytes(b"png")

    complete_flow_a_source_lifecycle(editorial_base, campaign_id=CAMPAIGN_ID)
    release = release_flow_a_execution(editorial_base, campaign_id=CAMPAIGN_ID)
    assert release.already_released is True
    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["state"] == STATE_FLOW_A_COMPLETE
    assert campaign["source_file_status"]["location"] == SOURCE_LOCATION_PROCESSED


def test_requeue_preserves_campaign_identity(editorial_base: Path):
    _write_ready(editorial_base, with_image=False)
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    move_result = coordinated_source_move(
        editorial_base,
        markdown_relative=QUEUED_RELATIVE,
        image_relative=None,
        destination_folder=DestinationFolder.ERROR,
    )
    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    campaign["source_file_status"]["location"] = SOURCE_LOCATION_ERROR
    campaign["error_source_relative_path"] = move_result.destination_markdown_relative
    campaign["source_relative_path"] = move_result.destination_markdown_relative
    campaign["blog_publish"] = {"status": "completed", "idempotency_key": "blog:key"}
    write_campaign_metadata(editorial_base, CAMPAIGN_ID, campaign)

    requeue = requeue_flow_a_source_from_error(editorial_base, campaign_id=CAMPAIGN_ID)
    assert requeue.status == "completed"
    updated = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert updated is not None
    assert updated["campaign_id"] == CAMPAIGN_ID
    assert updated["source_content_sha256"] == compute_source_content_sha256(SOURCE_MARKDOWN)
    assert updated["blog_publish"]["status"] == "completed"
    assert updated["source_file_status"]["location"] == SOURCE_LOCATION_QUEUED


def test_requeue_from_non_error_fails(editorial_base: Path):
    _write_ready(editorial_base, with_image=False)
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    result = requeue_flow_a_source_from_error(editorial_base, campaign_id=CAMPAIGN_ID)
    assert FLOW_A_REQUEUE_NOT_IN_ERROR in result.errors


def test_partial_image_move_classification(editorial_base: Path):
    _write_ready(editorial_base, with_image=True)
    image_path = editorial_base / IMAGE_READY

    def _fail_image_move(*args, **kwargs):
        if kwargs.get("destination_folder") == DestinationFolder.QUEUED:
            markdown_relative = kwargs["markdown_relative"]
            md_source = editorial_base / markdown_relative
            dest = editorial_base / "blog-posts" / "queued" / md_source.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(md_source.read_text(encoding="utf-8"), encoding="utf-8")
            md_source.unlink()
            from silverman_blog_linkedin.flow_a_source_moves import (
                CoordinatedMoveResult,
                ComponentMoveResult,
                PHYSICAL_MOVE_STATE_PARTIAL,
            )

            return CoordinatedMoveResult(
                status="partial",
                physical_move_state=PHYSICAL_MOVE_STATE_PARTIAL,
                markdown=ComponentMoveResult(
                    source_path=markdown_relative,
                    destination_path=f"blog-posts/queued/{md_source.name}",
                    status="completed",
                ),
                image=ComponentMoveResult(
                    source_path=kwargs.get("image_relative"),
                    destination_path=None,
                    status="failed",
                    error_code="image_move_failed",
                ),
                destination_markdown_relative=f"blog-posts/queued/{md_source.name}",
                errors=["image_move_failed"],
            )
        raise AssertionError("unexpected call")

    with patch(
        "silverman_blog_linkedin.flow_a_operational_queue.coordinated_source_move",
        side_effect=_fail_image_move,
    ):
        result = accept_flow_a_source_for_queue(
            editorial_base,
            source_relative_path=READY_RELATIVE,
            calendar_item=_calendar_item(),
        )
    assert result.recovery_classification == RECOVERY_REPAIR_REQUIRED
    assert image_path.is_file()


def test_hidden_macos_artifact_filtering(editorial_base: Path):
    ready = editorial_base / "blog-posts" / "ready"
    (ready / ".DS_Store").write_bytes(b"ds")
    (ready / "._post.md").write_bytes(b"meta")
    (ready / f"{SOURCE_SLUG}.md").write_text(SOURCE_MARKDOWN, encoding="utf-8")

    scan = scan_ready_folder(editorial_base)
    assert scan.valid_count == 1
    assert scan.ignored_count >= 2
    assert is_hidden_artifact_basename(".DS_Store")
    assert is_hidden_artifact_basename("._post.md")


def test_dry_run_does_not_move_or_claim(editorial_base: Path):
    _write_ready(editorial_base, with_image=False)
    result = accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(),
        dry_run=True,
    )
    assert result.would_queue_accept is True
    assert (editorial_base / READY_RELATIVE).is_file()
    assert not (editorial_base / QUEUED_RELATIVE).exists()
    claim = claim_flow_a_execution(editorial_base, campaign_id=CAMPAIGN_ID)
    assert claim.status == "failed"


def test_legacy_processed_campaign_path_resolution(editorial_base: Path):
    campaign = build_initial_campaign_metadata(
        flow=FLOW_A,
        source_slug=SOURCE_SLUG,
        public_slug=PUBLIC_SLUG,
        source_relative_path=READY_RELATIVE,
        image_relative_path=IMAGE_READY,
        source_content=SOURCE_MARKDOWN,
        publication_date=PUBLICATION_DATE,
    )
    campaign["processed_source_relative_path"] = f"blog-posts/processed/{SOURCE_SLUG}.md"
    campaign["source_file_status"]["location"] = SOURCE_LOCATION_PROCESSED
    write_campaign_metadata(editorial_base, CAMPAIGN_ID, campaign)
    processed = editorial_base / "blog-posts" / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    (processed / f"{SOURCE_SLUG}.md").write_text(SOURCE_MARKDOWN, encoding="utf-8")

    from silverman_blog_linkedin.campaign_lifecycle import resolve_campaign_source_paths

    md_path, _ = resolve_campaign_source_paths(campaign)
    assert md_path == f"blog-posts/processed/{SOURCE_SLUG}.md"


def _mock_metadata_write_failure():
    return CampaignMetadataWriteResult(
        written=False,
        error_code=CAMPAIGN_METADATA_WRITE_FAILED,
    )


def test_queue_acceptance_metadata_write_failure_after_move(editorial_base: Path):
    _write_ready(editorial_base, with_image=False)
    with patch(
        "silverman_blog_linkedin.flow_a_operational_queue.write_campaign_metadata",
        return_value=_mock_metadata_write_failure(),
    ):
        result = accept_flow_a_source_for_queue(
            editorial_base,
            source_relative_path=READY_RELATIVE,
            calendar_item=_calendar_item(),
        )
    assert result.status == QUEUE_ACCEPTANCE_REPAIR_REQUIRED
    assert result.metadata_written is False
    assert result.metadata_error_code == CAMPAIGN_METADATA_WRITE_FAILED
    assert CAMPAIGN_METADATA_WRITE_FAILED in result.errors
    assert (editorial_base / QUEUED_RELATIVE).is_file()


def test_reconcile_metadata_preserves_ready_original_path(editorial_base: Path):
    _write_ready(editorial_base, with_image=False)
    queued = editorial_base / "blog-posts" / "queued" / f"{SOURCE_SLUG}.md"
    queued.parent.mkdir(parents=True, exist_ok=True)
    queued.write_text(SOURCE_MARKDOWN, encoding="utf-8")
    campaign = build_initial_campaign_metadata(
        flow=FLOW_A,
        source_slug=SOURCE_SLUG,
        public_slug=PUBLIC_SLUG,
        source_relative_path=READY_RELATIVE,
        image_relative_path="",
        source_content=SOURCE_MARKDOWN,
        publication_date=PUBLICATION_DATE,
    )
    campaign["queued_source_relative_path"] = QUEUED_RELATIVE
    campaign["source_file_status"]["location"] = SOURCE_LOCATION_READY
    write_campaign_metadata(editorial_base, CAMPAIGN_ID, campaign)

    result = accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    assert result.status == QUEUE_ACCEPTANCE_REPAIR_REQUIRED
    updated = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert updated is not None
    assert updated["original_source_relative_path"] == READY_RELATIVE
    assert updated["source_relative_path"] == QUEUED_RELATIVE
    assert updated["source_file_status"]["location"] == SOURCE_LOCATION_QUEUED


def test_lost_response_reconciliation_idempotent(editorial_base: Path):
    _write_ready(editorial_base, with_image=False)
    first = accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    assert first.queue_acceptance_status == QUEUE_ACCEPTANCE_COMPLETED
    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    campaign["source_file_status"]["location"] = SOURCE_LOCATION_READY
    campaign["source_relative_path"] = READY_RELATIVE
    campaign.pop("original_source_relative_path", None)
    write_campaign_metadata(editorial_base, CAMPAIGN_ID, campaign)

    second = accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    assert second.status == QUEUE_ACCEPTANCE_REPAIR_REQUIRED
    updated = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert updated is not None
    assert updated["source_file_status"]["location"] == SOURCE_LOCATION_QUEUED


def test_explicit_calendar_campaign_id_used_for_new_metadata(editorial_base: Path):
    _write_ready(editorial_base, with_image=False)
    explicit_id = "flow-a-2026-07-06-custom-campaign"
    result = accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(campaign_id=explicit_id),
    )
    assert result.queue_acceptance_status == QUEUE_ACCEPTANCE_COMPLETED
    assert result.campaign_id == explicit_id
    campaign = read_campaign_metadata(editorial_base, explicit_id)
    assert campaign is not None
    assert campaign["campaign_id"] == explicit_id


def test_explicit_calendar_campaign_id_conflict_rejected(editorial_base: Path):
    _write_ready(editorial_base, with_image=False)
    other = build_initial_campaign_metadata(
        flow=FLOW_A,
        source_slug=SOURCE_SLUG,
        public_slug=PUBLIC_SLUG,
        source_relative_path=READY_RELATIVE,
        image_relative_path="",
        source_content="different body",
        publication_date=PUBLICATION_DATE,
    )
    other["campaign_id"] = "flow-a-2026-07-06-other"
    write_campaign_metadata(editorial_base, other["campaign_id"], other)

    result = accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(campaign_id=CAMPAIGN_ID),
    )
    assert result.status == QUEUE_ACCEPTANCE_FAILED
    assert CALENDAR_CAMPAIGN_ID_CONFLICT in result.errors


def test_retry_resolves_same_explicit_calendar_campaign_id(editorial_base: Path):
    _write_ready(editorial_base, with_image=False)
    explicit_id = "flow-a-2026-07-06-custom-campaign"
    calendar = _calendar_item(campaign_id=explicit_id)
    first = accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=calendar,
    )
    second = accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=calendar,
    )
    assert first.campaign_id == explicit_id
    assert second.queue_acceptance_status == QUEUE_ACCEPTANCE_SKIPPED_ALREADY_QUEUED
    assert second.campaign_id == explicit_id


def _queued_campaign(editorial_base: Path) -> None:
    _write_ready(editorial_base, with_image=False)
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(),
    )


def test_move_queued_source_to_error_completed(editorial_base: Path):
    _queued_campaign(editorial_base)
    result = move_queued_source_to_error(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        error_code="editorial_validation_failed",
        category="editorial_validation",
    )
    assert result.status == QUEUE_ACCEPTANCE_COMPLETED
    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["source_file_status"]["location"] == SOURCE_LOCATION_ERROR
    assert campaign["source_file_status"]["recovery_classification"] == RECOVERY_REQUEUE_REQUIRED
    assert campaign.get("error_source_relative_path")


def test_move_queued_source_to_error_partial(editorial_base: Path):
    _queued_campaign(editorial_base)

    def _partial_error_move(base_path, **kwargs):
        error_md = base_path / f"blog-posts/error/{SOURCE_SLUG}.md"
        error_md.parent.mkdir(parents=True, exist_ok=True)
        error_md.write_text(SOURCE_MARKDOWN, encoding="utf-8")
        return CoordinatedMoveResult(
            status="partial",
            physical_move_state=PHYSICAL_MOVE_STATE_PARTIAL,
            markdown=ComponentMoveResult(
                source_path=QUEUED_RELATIVE,
                destination_path=f"blog-posts/error/{SOURCE_SLUG}.md",
                status="completed",
            ),
            image=ComponentMoveResult(
                source_path=IMAGE_READY,
                destination_path=None,
                status="failed",
                error_code="image_move_failed",
            ),
            destination_markdown_relative=f"blog-posts/error/{SOURCE_SLUG}.md",
            errors=["image_move_failed"],
        )

    with patch(
        "silverman_blog_linkedin.flow_a_operational_queue.coordinated_source_move",
        side_effect=_partial_error_move,
    ):
        result = move_queued_source_to_error(
            editorial_base,
            campaign_id=CAMPAIGN_ID,
            error_code="editorial_validation_failed",
            category="editorial_validation",
        )
    assert result.status == QUEUE_ACCEPTANCE_PARTIAL
    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["source_file_status"]["location"] == SOURCE_LOCATION_ERROR
    assert campaign["source_file_status"]["execution_state"] == EXECUTION_STATE_IDLE
    assert campaign["source_file_status"]["physical_move_state"] == PHYSICAL_MOVE_STATE_PARTIAL
    assert campaign["source_file_status"]["recovery_classification"] == RECOVERY_REPAIR_REQUIRED
    assert campaign["source_relative_path"] == f"blog-posts/error/{SOURCE_SLUG}.md"
    assert campaign["error_source_relative_path"] == f"blog-posts/error/{SOURCE_SLUG}.md"


def test_move_queued_source_to_error_failed(editorial_base: Path):
    _queued_campaign(editorial_base)

    def _failed_error_move(*args, **kwargs):
        return CoordinatedMoveResult(
            status="failed",
            physical_move_state=PHYSICAL_MOVE_STATE_FAILED,
            markdown=ComponentMoveResult(
                source_path=QUEUED_RELATIVE,
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
        result = move_queued_source_to_error(
            editorial_base,
            campaign_id=CAMPAIGN_ID,
            error_code="editorial_validation_failed",
            category="editorial_validation",
        )
    assert result.status == QUEUE_ACCEPTANCE_FAILED
    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["source_file_status"]["location"] == SOURCE_LOCATION_QUEUED
    assert campaign["source_file_status"]["execution_state"] == EXECUTION_STATE_PROCESSING
    assert campaign["source_file_status"]["recovery_classification"] == RECOVERY_REPAIR_REQUIRED
    assert "error_source_relative_path" not in campaign
    assert (editorial_base / QUEUED_RELATIVE).is_file()


def test_claim_metadata_write_failure(editorial_base: Path):
    _queued_campaign(editorial_base)
    with patch(
        "silverman_blog_linkedin.flow_a_operational_queue.write_campaign_metadata_cas",
        return_value=_mock_metadata_write_failure(),
    ):
        result = claim_flow_a_execution(editorial_base, campaign_id=CAMPAIGN_ID)
    assert result.status == "failed"
    assert result.metadata_written is False
    assert CAMPAIGN_METADATA_WRITE_FAILED in result.errors


def test_progress_metadata_write_failure(editorial_base: Path):
    _queued_campaign(editorial_base)
    claim_flow_a_execution(editorial_base, campaign_id=CAMPAIGN_ID)
    with patch(
        "silverman_blog_linkedin.flow_a_operational_queue.write_campaign_metadata",
        return_value=_mock_metadata_write_failure(),
    ):
        result = record_flow_a_progress(editorial_base, campaign_id=CAMPAIGN_ID)
    assert result.status == "failed"
    assert CAMPAIGN_METADATA_WRITE_FAILED in result.errors


def test_release_metadata_write_failure(editorial_base: Path):
    _queued_campaign(editorial_base)
    claim_flow_a_execution(editorial_base, campaign_id=CAMPAIGN_ID)
    with patch(
        "silverman_blog_linkedin.flow_a_operational_queue.write_campaign_metadata",
        return_value=_mock_metadata_write_failure(),
    ):
        result = release_flow_a_execution(editorial_base, campaign_id=CAMPAIGN_ID)
    assert result.status == "failed"
    assert CAMPAIGN_METADATA_WRITE_FAILED in result.errors


def test_error_move_metadata_write_failure(editorial_base: Path):
    _queued_campaign(editorial_base)
    with patch(
        "silverman_blog_linkedin.flow_a_operational_queue.write_campaign_metadata",
        return_value=_mock_metadata_write_failure(),
    ):
        result = move_queued_source_to_error(
            editorial_base,
            campaign_id=CAMPAIGN_ID,
            error_code="editorial_validation_failed",
            category="editorial_validation",
        )
    assert result.status == QUEUE_ACCEPTANCE_REPAIR_REQUIRED
    assert CAMPAIGN_METADATA_WRITE_FAILED in result.errors


def test_requeue_metadata_write_failure(editorial_base: Path):
    _queued_campaign(editorial_base)
    move_queued_source_to_error(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        error_code="editorial_validation_failed",
        category="editorial_validation",
    )
    with patch(
        "silverman_blog_linkedin.flow_a_operational_queue.write_campaign_metadata",
        return_value=_mock_metadata_write_failure(),
    ):
        result = requeue_flow_a_source_from_error(editorial_base, campaign_id=CAMPAIGN_ID)
    assert result.status == "failed"
    assert CAMPAIGN_METADATA_WRITE_FAILED in result.errors


def test_error_collision_suffix_preserves_logical_slug(editorial_base: Path):
    _queued_campaign(editorial_base)
    error_dir = editorial_base / "blog-posts" / "error"
    error_dir.mkdir(parents=True, exist_ok=True)
    (error_dir / f"{SOURCE_SLUG}.md").write_text("blocker", encoding="utf-8")
    result = move_queued_source_to_error(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        error_code="editorial_validation_failed",
        category="editorial_validation",
    )
    assert result.status == QUEUE_ACCEPTANCE_COMPLETED
    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["source_slug"] == SOURCE_SLUG
    assert campaign["error_source_relative_path"].endswith(f"{SOURCE_SLUG}-error-1.md")


def test_partial_error_move_real_filesystem_md_in_error_image_stays_queued(editorial_base: Path):
    _write_ready(editorial_base, with_image=True)
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(),
    )

    original_move_file = None

    def _block_image_move(source_path, target_path):
        if source_path.suffix.lower() == ".png":
            raise OSError("image_move_blocked_for_test")
        if original_move_file is None:
            raise RuntimeError("original_move_file not set")
        original_move_file(source_path, target_path)

    import silverman_blog_linkedin.flow_a_source_moves as source_moves

    original_move_file = source_moves._move_file
    with patch.object(source_moves, "_move_file", side_effect=_block_image_move):
        result = move_queued_source_to_error(
            editorial_base,
            campaign_id=CAMPAIGN_ID,
            error_code="editorial_validation_failed",
            category="editorial_validation",
        )
    assert result.status == QUEUE_ACCEPTANCE_PARTIAL
    error_md = editorial_base / "blog-posts" / "error" / f"{SOURCE_SLUG}.md"
    queued_image = editorial_base / "blog-posts" / "queued" / f"{SOURCE_SLUG}.png"
    assert error_md.is_file()
    assert not (editorial_base / QUEUED_RELATIVE).exists()
    assert queued_image.is_file()
    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["source_file_status"]["location"] == SOURCE_LOCATION_ERROR
    assert campaign["source_file_status"]["physical_move_state"] == PHYSICAL_MOVE_STATE_PARTIAL
    assert campaign["source_file_status"]["recovery_classification"] == RECOVERY_REPAIR_REQUIRED
    assert campaign["source_relative_path"] == f"blog-posts/error/{SOURCE_SLUG}.md"
    assert campaign["error_source_relative_path"] == f"blog-posts/error/{SOURCE_SLUG}.md"
    assert campaign["queued_image_relative_path"] == f"blog-posts/queued/{SOURCE_SLUG}.png"
    assert campaign["image_relative_path"] == f"blog-posts/queued/{SOURCE_SLUG}.png"


def test_failed_error_move_real_filesystem_md_stays_queued(editorial_base: Path):
    _queued_campaign(editorial_base)
    queued_md = editorial_base / QUEUED_RELATIVE
    queued_md.unlink()
    result = move_queued_source_to_error(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        error_code="editorial_validation_failed",
        category="editorial_validation",
    )
    assert result.status == QUEUE_ACCEPTANCE_FAILED
    assert not list((editorial_base / "blog-posts" / "error").glob(f"{SOURCE_SLUG}.md"))
    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["source_file_status"]["location"] == SOURCE_LOCATION_QUEUED
    assert campaign["source_file_status"]["execution_state"] == EXECUTION_STATE_PROCESSING
    assert campaign["source_relative_path"] == QUEUED_RELATIVE


def test_release_processing_returns_idle(editorial_base: Path):
    _queued_campaign(editorial_base)
    claim_flow_a_execution(editorial_base, campaign_id=CAMPAIGN_ID)
    release = release_flow_a_execution(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        recovery_classification=RECOVERY_RETRYABLE,
    )
    assert release.status == "completed"
    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["source_file_status"]["execution_state"] == EXECUTION_STATE_IDLE


def test_release_queued_idle_already_released(editorial_base: Path):
    _queued_campaign(editorial_base)
    release = release_flow_a_execution(editorial_base, campaign_id=CAMPAIGN_ID)
    assert release.status == "skipped"
    assert release.already_released is True
    assert FLOW_A_EXECUTION_ALREADY_RELEASED in release.errors


def test_release_stale_rejected_without_exception(editorial_base: Path):
    _queued_campaign(editorial_base)
    claim_flow_a_execution(editorial_base, campaign_id=CAMPAIGN_ID)
    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    status = campaign["source_file_status"]
    status["execution_state"] = EXECUTION_STATE_STALE
    status["recovery_classification"] = RECOVERY_RETRYABLE
    campaign["source_file_status"] = status
    write_campaign_metadata(editorial_base, CAMPAIGN_ID, campaign)

    release = release_flow_a_execution(editorial_base, campaign_id=CAMPAIGN_ID)
    assert release.status == "failed"
    assert FLOW_A_EXECUTION_STALE_RELEASE_NOT_ALLOWED in release.errors
    updated = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert updated is not None
    assert updated["source_file_status"]["execution_state"] == EXECUTION_STATE_STALE
    assert updated["source_file_status"]["recovery_classification"] == RECOVERY_RETRYABLE


def _claim_with_last_progress(
    editorial_base: Path,
    *,
    last_progress_at: str,
    now_utc: str,
    stale_seconds: int = 60,
) -> ExecutionClaimResult:
    _queued_campaign(editorial_base)
    with patch.dict("os.environ", {ENV_FLOW_A_PROCESSING_STALE_SECONDS: str(stale_seconds)}):
        claim_flow_a_execution(editorial_base, campaign_id=CAMPAIGN_ID, now_utc=now_utc)
        campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
        assert campaign is not None
        status = campaign["source_file_status"]
        status["last_progress_at"] = last_progress_at
        status["processing_lease_expires_at"] = last_progress_at
        campaign["source_file_status"] = status
        write_campaign_metadata(editorial_base, CAMPAIGN_ID, campaign)
        return claim_flow_a_execution(
            editorial_base, campaign_id=CAMPAIGN_ID, now_utc=now_utc
        )


def test_claim_stale_boundary_one_second_before_threshold(editorial_base: Path):
    progress = "2026-07-06T12:00:00Z"
    now = "2026-07-06T12:00:59Z"
    with patch.dict("os.environ", {ENV_FLOW_A_PROCESSING_STALE_SECONDS: "60"}):
        result = _claim_with_last_progress(
            editorial_base, last_progress_at=progress, now_utc=now, stale_seconds=60
        )
    assert result.status == "failed"
    assert FLOW_A_EXECUTION_ALREADY_CLAIMED in result.errors


def test_claim_stale_boundary_exactly_at_threshold(editorial_base: Path):
    progress = "2026-07-06T12:00:00Z"
    now = "2026-07-06T12:01:00Z"
    with patch.dict("os.environ", {ENV_FLOW_A_PROCESSING_STALE_SECONDS: "60"}):
        result = _claim_with_last_progress(
            editorial_base, last_progress_at=progress, now_utc=now, stale_seconds=60
        )
    assert result.status == "completed"
    assert result.reclaimed_from_stale is True


def test_claim_stale_boundary_one_second_after_threshold(editorial_base: Path):
    progress = "2026-07-06T12:00:00Z"
    now = "2026-07-06T12:01:01Z"
    with patch.dict("os.environ", {ENV_FLOW_A_PROCESSING_STALE_SECONDS: "60"}):
        result = _claim_with_last_progress(
            editorial_base, last_progress_at=progress, now_utc=now, stale_seconds=60
        )
    assert result.status == "completed"
    assert result.reclaimed_from_stale is True


def test_claim_uses_supplied_now_utc_not_system_clock(editorial_base: Path):
    _queued_campaign(editorial_base)
    controlled_now = "2030-01-01T00:00:00Z"
    result = claim_flow_a_execution(
        editorial_base, campaign_id=CAMPAIGN_ID, now_utc=controlled_now
    )
    assert result.status == "completed"
    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    status = campaign["source_file_status"]
    assert status["processing_claimed_at"] == controlled_now
    assert status["last_progress_at"] == controlled_now


def test_same_hash_incompatible_slug_rejected(editorial_base: Path):
    _write_ready(editorial_base, with_image=False)
    content_hash = compute_source_content_sha256(SOURCE_MARKDOWN.encode())
    other = build_initial_campaign_metadata(
        flow=FLOW_A,
        source_slug="different-slug",
        public_slug=PUBLIC_SLUG,
        source_relative_path=READY_RELATIVE,
        image_relative_path="",
        source_content=SOURCE_MARKDOWN,
        publication_date=PUBLICATION_DATE,
    )
    other["campaign_id"] = CAMPAIGN_ID
    other["source_content_sha256"] = content_hash
    write_campaign_metadata(editorial_base, CAMPAIGN_ID, other)

    result = accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(campaign_id=CAMPAIGN_ID),
    )
    assert CALENDAR_CAMPAIGN_ID_CONFLICT in result.errors


def test_same_hash_incompatible_source_path_rejected(editorial_base: Path):
    _write_ready(editorial_base, with_image=False)
    alt_ready = "blog-posts/ready/99-other-post.md"
    (editorial_base / "blog-posts" / "ready" / "99-other-post.md").write_text(
        SOURCE_MARKDOWN, encoding="utf-8"
    )
    content_hash = compute_source_content_sha256(SOURCE_MARKDOWN.encode())
    other = build_initial_campaign_metadata(
        flow=FLOW_A,
        source_slug=SOURCE_SLUG,
        public_slug=PUBLIC_SLUG,
        source_relative_path=READY_RELATIVE,
        image_relative_path="",
        source_content=SOURCE_MARKDOWN,
        publication_date=PUBLICATION_DATE,
    )
    other["campaign_id"] = CAMPAIGN_ID
    other["source_content_sha256"] = content_hash
    write_campaign_metadata(editorial_base, CAMPAIGN_ID, other)

    result = accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=alt_ready,
        calendar_item=_calendar_item(campaign_id=CAMPAIGN_ID),
    )
    assert CALENDAR_CAMPAIGN_ID_CONFLICT in result.errors


def test_non_flow_a_existing_campaign_with_explicit_id_rejected(editorial_base: Path):
    _write_ready(editorial_base, with_image=False)
    explicit_id = "flow-b-2026-07-06-custom"
    other = build_initial_campaign_metadata(
        flow=FLOW_B,
        source_slug=SOURCE_SLUG,
        public_slug=PUBLIC_SLUG,
        source_relative_path=READY_RELATIVE,
        image_relative_path="",
        source_content=SOURCE_MARKDOWN,
        publication_date=PUBLICATION_DATE,
        campaign_id=explicit_id,
    )
    write_campaign_metadata(editorial_base, explicit_id, other)

    result = accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(campaign_id=explicit_id),
    )
    assert CALENDAR_CAMPAIGN_ID_CONFLICT in result.errors


def test_explicit_calendar_id_reflected_in_id_derived_fields(editorial_base: Path):
    _write_ready(editorial_base, with_image=False)
    explicit_id = "flow-a-2026-07-06-custom-campaign"
    result = accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(campaign_id=explicit_id),
    )
    assert result.campaign_id == explicit_id
    campaign = read_campaign_metadata(editorial_base, explicit_id)
    assert campaign is not None
    assert campaign["campaign_id"] == explicit_id
    expected_key = build_blog_publish_idempotency_key(
        source_slug=SOURCE_SLUG,
        public_slug=PUBLIC_SLUG,
        publication_date=PUBLICATION_DATE,
        source_content_sha256=compute_source_content_sha256(SOURCE_MARKDOWN.encode()),
    )
    assert campaign["blog_publish"]["idempotency_key"] == expected_key
    assert campaign["blog_publish"]["idempotency_key"] != explicit_id
