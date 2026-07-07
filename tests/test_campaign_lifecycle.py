"""Tests for campaign lifecycle metadata and duplicate-prevention helpers."""

import json
from pathlib import Path

import pytest

from silverman_blog_linkedin.campaign_lifecycle import (
    ACTOR_WORKER,
    FLOW_A,
    FLOW_B,
    METADATA_CAMPAIGNS_RELATIVE,
    CampaignLifecycleError,
    CampaignMetadataWriteResult,
    InvalidStateTransition,
    STATE_BLOG_PUBLISH_PENDING,
    STATE_BLOG_PUBLISHED,
    STATE_DERIVATIVES_GENERATED,
    STATE_DERIVATIVES_PENDING,
    STATE_DISTRIBUTION_COMPLETE,
    STATE_DISTRIBUTION_SCHEDULED,
    STATE_ERROR,
    STATE_FLOW_A_COMPLETE,
    STATE_READY,
    STATE_VALIDATED,
    STATE_VALIDATION_FAILED,
    build_blog_publish_idempotency_key,
    build_derivative_idempotency_key,
    build_initial_campaign_metadata,
    build_schedule_idempotency_key,
    campaign_metadata_relative_path,
    check_metadata_campaigns_ready,
    compute_source_content_sha256,
    generate_campaign_id,
    mark_source_error,
    mark_source_processed,
    read_campaign_metadata,
    sanitize_campaign_metadata,
    transition_state,
    validate_campaign_id,
    validate_variant_id,
    write_campaign_metadata,
)

CANONICAL_CAMPAIGN_ID = "flow-a-2026-07-06-why-i-did-not-start-with-the-database"
SOURCE_SLUG = "01-why-i-did-not-start-with-the-database"
PUBLIC_SLUG = "why-i-did-not-start-with-the-database"
PUBLICATION_DATE = "2026-07-06"
SOURCE_RELATIVE = f"blog-posts/ready/{SOURCE_SLUG}.md"
IMAGE_RELATIVE = f"blog-posts/ready/{SOURCE_SLUG}.png"
SOURCE_MARKDOWN = "# Why I did not start with the database\n\nBody text.\n"
CONTENT_SHA256 = compute_source_content_sha256(SOURCE_MARKDOWN)


def _build_campaign(*, flow: str = FLOW_A, created_at: str = "2026-07-06T14:30:00Z"):
    return build_initial_campaign_metadata(
        flow=flow,
        source_slug=SOURCE_SLUG,
        public_slug=PUBLIC_SLUG,
        source_relative_path=SOURCE_RELATIVE,
        image_relative_path=IMAGE_RELATIVE,
        source_content=SOURCE_MARKDOWN,
        publication_date=PUBLICATION_DATE,
        created_at=created_at,
    )


def test_generate_campaign_id_canonical_example():
    campaign_id = generate_campaign_id(FLOW_A, PUBLICATION_DATE, PUBLIC_SLUG)

    assert campaign_id == CANONICAL_CAMPAIGN_ID


def test_generate_campaign_id_rejects_unsafe_slug():
    with pytest.raises(CampaignLifecycleError) as exc_info:
        generate_campaign_id(FLOW_A, PUBLICATION_DATE, "../evil-slug")

    assert exc_info.value.error_code == "unsafe_public_slug"


def test_generate_campaign_id_rejects_uppercase_slug():
    with pytest.raises(CampaignLifecycleError) as exc_info:
        generate_campaign_id(FLOW_A, PUBLICATION_DATE, "Why-I-Did-Not")

    assert exc_info.value.error_code == "unsafe_public_slug"


def test_initial_campaign_metadata_shape():
    campaign = _build_campaign()

    assert campaign["campaign_id"] == CANONICAL_CAMPAIGN_ID
    assert campaign["flow"] == FLOW_A
    assert campaign["state"] == STATE_READY
    assert campaign["source_slug"] == SOURCE_SLUG
    assert campaign["public_slug"] == PUBLIC_SLUG
    assert campaign["source_relative_path"] == SOURCE_RELATIVE
    assert campaign["image_relative_path"] == IMAGE_RELATIVE
    assert campaign["source_content_sha256"] == CONTENT_SHA256
    assert campaign["publication_date"] == PUBLICATION_DATE
    assert campaign["source_public_url"] is None
    assert campaign["variants"] == []
    assert campaign["errors"] == []
    assert campaign["warnings"] == []
    assert campaign["blog_publish"]["status"] == "pending"
    assert campaign["source_file_status"]["location"] == "ready"
    assert len(campaign["state_history"]) == 1
    assert campaign["state_history"][0]["to_state"] == STATE_READY
    assert "markdown_content" not in campaign
    assert "generated_draft_content" not in campaign
    assert "draft_content" not in campaign


def test_happy_path_transitions_to_flow_a_complete():
    campaign = _build_campaign()

    path = [
        (STATE_VALIDATED, "Validation passed"),
        (STATE_BLOG_PUBLISH_PENDING, "Blog publish requested"),
        (STATE_BLOG_PUBLISHED, "Blog published"),
        (STATE_DERIVATIVES_PENDING, "Derivatives requested"),
        (STATE_DERIVATIVES_GENERATED, "Derivatives generated"),
        (STATE_DISTRIBUTION_SCHEDULED, "Distribution scheduled"),
        (STATE_DISTRIBUTION_COMPLETE, "Distribution complete"),
        (STATE_FLOW_A_COMPLETE, "Flow A complete"),
    ]

    for to_state, reason in path:
        transition_state(
            campaign,
            to_state,
            reason=reason,
            actor=ACTOR_WORKER,
        )

    assert campaign["state"] == STATE_FLOW_A_COMPLETE
    assert campaign["source_file_status"]["location"] == "processed"
    assert campaign["source_file_status"]["marked_processed_at"] is not None
    assert len(campaign["state_history"]) == 9


def test_invalid_transition_rejected():
    campaign = _build_campaign()

    with pytest.raises(InvalidStateTransition) as exc_info:
        transition_state(
            campaign,
            STATE_BLOG_PUBLISHED,
            reason="Invalid skip",
            actor=ACTOR_WORKER,
        )

    assert exc_info.value.error_code == "invalid_state_transition"
    assert campaign["state"] == STATE_READY


def test_failure_transition_requires_error_code():
    campaign = _build_campaign()

    with pytest.raises(CampaignLifecycleError) as exc_info:
        transition_state(
            campaign,
            STATE_VALIDATION_FAILED,
            reason="Validation failed",
            actor=ACTOR_WORKER,
        )

    assert exc_info.value.error_code == "missing_error_code"


def test_failure_transition_records_error_code_and_errors_list():
    campaign = _build_campaign()

    transition_state(
        campaign,
        STATE_VALIDATION_FAILED,
        reason="Frontmatter invalid",
        actor=ACTOR_WORKER,
        error_code="validation_frontmatter_invalid",
    )

    last_entry = campaign["state_history"][-1]
    assert last_entry["to_state"] == STATE_VALIDATION_FAILED
    assert last_entry["error_code"] == "validation_frontmatter_invalid"
    assert "validation_frontmatter_invalid" in campaign["errors"]
    assert campaign["source_file_status"]["location"] == "error"
    assert campaign["source_file_status"]["marked_error_at"] is not None


def test_blog_idempotency_key_stability():
    key_a = build_blog_publish_idempotency_key(
        source_slug=SOURCE_SLUG,
        public_slug=PUBLIC_SLUG,
        publication_date=PUBLICATION_DATE,
        source_content_sha256=CONTENT_SHA256,
    )
    key_b = build_blog_publish_idempotency_key(
        source_slug=SOURCE_SLUG,
        public_slug=PUBLIC_SLUG,
        publication_date=PUBLICATION_DATE,
        source_content_sha256=CONTENT_SHA256,
    )

    assert key_a == key_b
    assert key_a == (
        f"blog:{SOURCE_SLUG}:{PUBLIC_SLUG}:{PUBLICATION_DATE}:{CONTENT_SHA256}"
    )


def test_blog_idempotency_key_changes_with_content_hash():
    key_a = build_blog_publish_idempotency_key(
        source_slug=SOURCE_SLUG,
        public_slug=PUBLIC_SLUG,
        publication_date=PUBLICATION_DATE,
        source_content_sha256=CONTENT_SHA256,
    )
    key_b = build_blog_publish_idempotency_key(
        source_slug=SOURCE_SLUG,
        public_slug=PUBLIC_SLUG,
        publication_date=PUBLICATION_DATE,
        source_content_sha256="different-hash",
    )

    assert key_a != key_b


def test_derivative_idempotency_keys_use_canonical_variant_ids():
    key_exec = build_derivative_idempotency_key(
        campaign_id=CANONICAL_CAMPAIGN_ID,
        source_content_sha256="abc123",
        variant="executive-recruiter",
        flow=FLOW_A,
    )
    key_tech = build_derivative_idempotency_key(
        campaign_id=CANONICAL_CAMPAIGN_ID,
        source_content_sha256="abc123",
        variant="technical-architect",
        flow=FLOW_A,
    )
    key_short = build_derivative_idempotency_key(
        campaign_id=CANONICAL_CAMPAIGN_ID,
        source_content_sha256="abc123",
        variant="short-provocative",
        flow=FLOW_A,
    )

    assert key_exec == (
        f"derivative:{CANONICAL_CAMPAIGN_ID}:abc123:executive-recruiter:flow_a"
    )
    assert key_tech == (
        f"derivative:{CANONICAL_CAMPAIGN_ID}:abc123:technical-architect:flow_a"
    )
    assert key_short == (
        f"derivative:{CANONICAL_CAMPAIGN_ID}:abc123:short-provocative:flow_a"
    )
    assert key_exec != key_tech


def test_schedule_idempotency_key_uses_normalized_utc_timestamp():
    key = build_schedule_idempotency_key(
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant="engineering-leadership",
        scheduled_at="2026-07-08T14:00:00Z",
    )

    assert key == (
        "schedule:flow-a-2026-07-06-why-i-did-not-start-with-the-database:"
        "engineering-leadership:2026-07-08T14:00:00Z"
    )


def test_non_canonical_variant_ids_rejected():
    for variant in ("executive", "short_provocative", "technical"):
        with pytest.raises(CampaignLifecycleError) as exc_info:
            validate_variant_id(variant)

        assert exc_info.value.error_code == "invalid_variant_id"

    with pytest.raises(CampaignLifecycleError) as exc_info:
        build_derivative_idempotency_key(
            campaign_id=CANONICAL_CAMPAIGN_ID,
            source_content_sha256="abc123",
            variant="executive",
            flow=FLOW_A,
        )

    assert exc_info.value.error_code == "invalid_variant_id"


def test_sanitize_campaign_metadata_removes_forbidden_fields():
    payload = {
        "campaign_id": CANONICAL_CAMPAIGN_ID,
        "markdown_content": "secret body",
        "generated_draft_content": "draft body",
        "draft_content": "another draft",
        "api_key": "super-secret",
        "variants": [
            {
                "variant": "executive-recruiter",
                "draft_content": "nested draft",
            }
        ],
    }

    sanitized = sanitize_campaign_metadata(payload)

    assert "markdown_content" not in sanitized
    assert "generated_draft_content" not in sanitized
    assert "draft_content" not in sanitized
    assert "api_key" not in sanitized
    assert "draft_content" not in sanitized["variants"][0]
    assert sanitized["campaign_id"] == CANONICAL_CAMPAIGN_ID


def test_flow_b_campaign_rejected_by_transition_helper():
    campaign = _build_campaign(flow=FLOW_B)

    with pytest.raises(CampaignLifecycleError) as exc_info:
        transition_state(
            campaign,
            STATE_VALIDATED,
            reason="Should not run",
            actor=ACTOR_WORKER,
        )

    assert exc_info.value.error_code == "flow_b_not_eligible_for_flow_a"


def test_campaign_metadata_relative_path():
    assert (
        campaign_metadata_relative_path(CANONICAL_CAMPAIGN_ID)
        == f"{METADATA_CAMPAIGNS_RELATIVE}/{CANONICAL_CAMPAIGN_ID}.json"
    )


@pytest.mark.parametrize(
    "invalid_campaign_id",
    [
        "../evil",
        "flow-a-2026-07-06-../evil",
        "flow-a-2026-07-06-Bad-Slug",
        "flow-a-2026-07-06-bad slug",
        "random-file",
    ],
)
def test_campaign_metadata_relative_path_rejects_invalid_campaign_id(
    invalid_campaign_id,
):
    with pytest.raises(CampaignLifecycleError) as exc_info:
        campaign_metadata_relative_path(invalid_campaign_id)

    assert exc_info.value.error_code == "invalid_campaign_id"


@pytest.mark.parametrize(
    "invalid_campaign_id",
    [
        "../evil",
        "flow-a-2026-07-06-../evil",
        "flow-a-2026-07-06-Bad-Slug",
        "flow-a-2026-07-06-bad slug",
        "random-file",
    ],
)
def test_write_campaign_metadata_rejects_invalid_campaign_id(
    tmp_path, invalid_campaign_id
):
    metadata_dir = tmp_path / METADATA_CAMPAIGNS_RELATIVE
    metadata_dir.mkdir(parents=True)
    campaign = _build_campaign()

    result = write_campaign_metadata(tmp_path, invalid_campaign_id, campaign)

    assert result == CampaignMetadataWriteResult(
        written=False, error_code="invalid_campaign_id"
    )


@pytest.mark.parametrize(
    "invalid_campaign_id",
    [
        "../evil",
        "flow-a-2026-07-06-../evil",
        "flow-a-2026-07-06-Bad-Slug",
        "flow-a-2026-07-06-bad slug",
        "random-file",
    ],
)
def test_read_campaign_metadata_rejects_invalid_campaign_id(
    tmp_path, invalid_campaign_id
):
    assert read_campaign_metadata(tmp_path, invalid_campaign_id) is None


def test_validate_campaign_id_accepts_flow_b_format():
    campaign_id = "flow-b-2026-07-06-why-i-did-not-start-with-the-database"

    validate_campaign_id(campaign_id)


def test_check_metadata_campaigns_ready_when_writable(tmp_path):
    metadata_dir = tmp_path / METADATA_CAMPAIGNS_RELATIVE
    metadata_dir.mkdir(parents=True)

    readiness = check_metadata_campaigns_ready(tmp_path)

    assert readiness.ready is True
    assert readiness.error_code is None


def test_check_metadata_campaigns_missing(tmp_path):
    readiness = check_metadata_campaigns_ready(tmp_path)

    assert readiness.ready is False
    assert readiness.error_code == "metadata_campaigns_not_ready"


def test_campaign_metadata_write_read_round_trip(tmp_path):
    metadata_dir = tmp_path / METADATA_CAMPAIGNS_RELATIVE
    metadata_dir.mkdir(parents=True)
    campaign = _build_campaign()
    campaign["markdown_content"] = "must not persist"

    result = write_campaign_metadata(
        tmp_path, campaign["campaign_id"], campaign
    )

    assert result.written is True
    assert result.error_code is None
    metadata_file = tmp_path / campaign_metadata_relative_path(campaign["campaign_id"])
    assert metadata_file.is_file()
    on_disk = json.loads(metadata_file.read_text(encoding="utf-8"))
    assert "markdown_content" not in on_disk

    loaded = read_campaign_metadata(tmp_path, campaign["campaign_id"])
    assert loaded == on_disk
    assert loaded["campaign_id"] == CANONICAL_CAMPAIGN_ID


def test_write_campaign_metadata_skipped_when_missing(tmp_path):
    campaign = _build_campaign()

    result = write_campaign_metadata(
        tmp_path, campaign["campaign_id"], campaign
    )

    assert result.written is False
    assert result.error_code == "metadata_campaigns_not_ready"


def test_mark_source_processed_updates_metadata_only():
    campaign = _build_campaign()

    mark_source_processed(campaign)

    assert campaign["source_file_status"]["location"] == "processed"
    assert campaign["source_file_status"]["marked_processed_at"] is not None


def test_mark_source_error_updates_metadata_only():
    campaign = _build_campaign()

    mark_source_error(campaign)

    assert campaign["source_file_status"]["location"] == "error"
    assert campaign["source_file_status"]["marked_error_at"] is not None


def test_error_transition_records_error_code():
    campaign = _build_campaign()

    transition_state(
        campaign,
        STATE_ERROR,
        reason="Unrecoverable failure",
        actor=ACTOR_WORKER,
        error_code="publish_failed",
    )

    last_entry = campaign["state_history"][-1]
    assert last_entry["to_state"] == STATE_ERROR
    assert last_entry["error_code"] == "publish_failed"
    assert "publish_failed" in campaign["errors"]
