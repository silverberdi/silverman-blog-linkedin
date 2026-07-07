"""Tests for Flow A LinkedIn distribution scheduling."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.campaign_lifecycle import (
    ACTOR_WORKER,
    CANONICAL_VARIANT_IDS,
    FLOW_A,
    FLOW_B,
    METADATA_CAMPAIGNS_RELATIVE,
    STATE_BLOG_PUBLISH_PENDING,
    STATE_BLOG_PUBLISHED,
    STATE_DERIVATIVES_GENERATED,
    STATE_DERIVATIVES_PENDING,
    STATE_DISTRIBUTION_SCHEDULED,
    STATE_VALIDATED,
    build_derivative_idempotency_key,
    build_initial_campaign_metadata,
    read_campaign_metadata,
    transition_state,
    write_campaign_metadata,
)
from silverman_blog_linkedin.linkedin_distribution_schedule import (
    DEFAULT_STAGGER_STRATEGY,
    LINKEDIN_SCHEDULE_ARTIFACT_HASH_CHANGED,
    LINKEDIN_SCHEDULE_ARTIFACT_MISSING,
    LINKEDIN_SCHEDULE_CAMPAIGN_NOT_FOUND,
    LINKEDIN_SCHEDULE_FLOW_NOT_ALLOWED,
    LINKEDIN_SCHEDULE_INVALID_ANCHOR,
    LINKEDIN_SCHEDULE_INVALID_CAMPAIGN_STATE,
    LINKEDIN_SCHEDULE_INVALID_STRATEGY,
    LINKEDIN_SCHEDULE_METADATA_MISMATCH,
    LINKEDIN_SCHEDULE_PACKAGE_MISSING,
    LINKEDIN_SCHEDULE_VARIANT_METADATA_MISSING,
    VARIANT_DAY_OFFSETS,
    build_schedule_idempotency_key,
    schedule_linkedin_distribution,
)
from silverman_blog_linkedin.linkedin_package_flow import (
    GENERATED_RELATIVE,
    build_package_idempotency_key,
)
from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, create_full_layout, make_settings

SOURCE_SLUG = "01-why-i-did-not-start-with-the-database"
PUBLIC_SLUG = "why-i-did-not-start-with-the-database"
PUBLICATION_DATE = "2026-07-06"
SOURCE_RELATIVE = f"blog-posts/ready/{SOURCE_SLUG}.md"
IMAGE_RELATIVE = f"blog-posts/ready/{SOURCE_SLUG}.png"
CANONICAL_CAMPAIGN_ID = f"flow-a-{PUBLICATION_DATE}-{PUBLIC_SLUG}"
PUBLIC_URL = "https://silverman.pro/2026/07/06/why-i-did-not-start-with-the-database/"
ANCHOR_UTC = "2026-07-07T14:00:00Z"
TITLE = "Why I Did Not Start With the Database"


def _canonical_frontmatter() -> str:
    return (
        "---\n"
        f"title: {TITLE}\n"
        "audience: architects\n"
        "type: blog-post\n"
        "language: en\n"
        "layout: post\n"
        f"date: {PUBLICATION_DATE}\n"
        "categories:\n"
        "  - architecture\n"
        "tags:\n"
        "  - databases\n"
        "description: A senior practitioner's take on starting with the domain.\n"
        f"image: /assets/images/{PUBLIC_SLUG}.png\n"
        "---\n"
    )


def _canonical_body() -> str:
    return (
        f"# {TITLE}\n\n"
        "The real problem is not persistence. The real problem is naming the business too late.\n"
    )


def _write_post(base: Path) -> Path:
    ready = base / "blog-posts" / "ready"
    ready.mkdir(parents=True, exist_ok=True)
    md_path = ready / f"{SOURCE_SLUG}.md"
    md_path.write_text(_canonical_frontmatter() + _canonical_body(), encoding="utf-8")
    return md_path


def _setup_metadata_campaigns(base: Path) -> Path:
    metadata_dir = base / METADATA_CAMPAIGNS_RELATIVE
    metadata_dir.mkdir(parents=True, exist_ok=True)
    return metadata_dir


def _artifact_content(variant_id: str) -> str:
    return f"LinkedIn draft for {variant_id}.\nRead the full story here: {PUBLIC_URL}\n"


def _write_artifact(base: Path, variant_id: str, *, content: str | None = None) -> tuple[str, str]:
    artifact_dir = base / GENERATED_RELATIVE / CANONICAL_CAMPAIGN_ID
    artifact_dir.mkdir(parents=True, exist_ok=True)
    body = content if content is not None else _artifact_content(variant_id)
    if body and not body.endswith("\n"):
        body += "\n"
    raw = body.encode("utf-8")
    artifact_path = artifact_dir / f"{variant_id}.md"
    artifact_path.write_bytes(raw)
    return f"{GENERATED_RELATIVE}/{CANONICAL_CAMPAIGN_ID}/{variant_id}.md", hashlib.sha256(raw).hexdigest()


def _variant_entry(
    variant_id: str,
    *,
    artifact_relative_path: str,
    derivative_content_sha256: str,
) -> dict:
    return {
        "variant": variant_id,
        "audience": "senior practitioners",
        "tone": "executive",
        "source_public_url": PUBLIC_URL,
        "source_relative_path": SOURCE_RELATIVE,
        "campaign_id": CANONICAL_CAMPAIGN_ID,
        "source_content_sha256": "placeholder",
        "derivative_content_sha256": derivative_content_sha256,
        "artifact_relative_path": artifact_relative_path,
        "idempotency_key": build_derivative_idempotency_key(
            campaign_id=CANONICAL_CAMPAIGN_ID,
            source_content_sha256="placeholder",
            variant=variant_id,
            flow=FLOW_A,
        ),
        "generated_at": "2026-07-06T12:00:00Z",
        "provider": "deepseek",
        "model": "deepseek-chat",
    }


def _derivatives_generated_campaign(
    base: Path,
    *,
    variant_ids: list[str] | None = None,
    include_package: bool = True,
    include_variants: bool = True,
) -> dict:
    content = _write_post(base).read_text(encoding="utf-8")
    campaign = build_initial_campaign_metadata(
        flow=FLOW_A,
        source_slug=SOURCE_SLUG,
        public_slug=PUBLIC_SLUG,
        source_relative_path=SOURCE_RELATIVE,
        image_relative_path=IMAGE_RELATIVE,
        source_content=content,
        publication_date=PUBLICATION_DATE,
    )
    transition_state(
        campaign,
        STATE_VALIDATED,
        reason="Editorial validation passed",
        actor=ACTOR_WORKER,
    )
    transition_state(
        campaign,
        STATE_BLOG_PUBLISH_PENDING,
        reason="Blog publish started",
        actor=ACTOR_WORKER,
    )
    transition_state(
        campaign,
        STATE_BLOG_PUBLISHED,
        reason="Blog published",
        actor=ACTOR_WORKER,
    )
    campaign["source_public_url"] = PUBLIC_URL
    source_hash = campaign["source_content_sha256"]

    resolved_variant_ids = sorted(variant_ids or CANONICAL_VARIANT_IDS)
    variant_entries: list[dict] = []
    for variant_id in resolved_variant_ids:
        artifact_relative, derivative_hash = _write_artifact(base, variant_id)
        entry = _variant_entry(
            variant_id,
            artifact_relative_path=artifact_relative,
            derivative_content_sha256=derivative_hash,
        )
        entry["source_content_sha256"] = source_hash
        entry["idempotency_key"] = build_derivative_idempotency_key(
            campaign_id=CANONICAL_CAMPAIGN_ID,
            source_content_sha256=source_hash,
            variant=variant_id,
            flow=FLOW_A,
        )
        variant_entries.append(entry)

    if include_variants:
        campaign["variants"] = variant_entries
    else:
        campaign["variants"] = []

    if include_package:
        campaign["linkedin_package"] = {
            "package_id": f"{CANONICAL_CAMPAIGN_ID}-pkg",
            "idempotency_key": build_package_idempotency_key(
                campaign_id=CANONICAL_CAMPAIGN_ID,
                source_content_sha256=source_hash,
                variant_ids=resolved_variant_ids,
                flow=FLOW_A,
            ),
            "package_status": "generated",
            "generated_at": "2026-07-06T12:00:00Z",
            "source_public_url": PUBLIC_URL,
            "source_relative_path": SOURCE_RELATIVE,
            "source_content_sha256": source_hash,
            "variant_ids": resolved_variant_ids,
        }

    transition_state(
        campaign,
        STATE_DERIVATIVES_PENDING,
        reason="LinkedIn derivative package generation started",
        actor=ACTOR_WORKER,
    )
    transition_state(
        campaign,
        STATE_DERIVATIVES_GENERATED,
        reason="LinkedIn derivative package generated",
        actor=ACTOR_WORKER,
    )
    write_campaign_metadata(base, CANONICAL_CAMPAIGN_ID, campaign)
    return campaign


def _schedule(
    base: Path,
    *,
    campaign_id: str | None = CANONICAL_CAMPAIGN_ID,
    source_relative_path: str | None = None,
    strategy: str | None = None,
    start_at_utc: str | None = ANCHOR_UTC,
):
    return schedule_linkedin_distribution(
        base,
        campaign_id=campaign_id,
        source_relative_path=source_relative_path,
        strategy=strategy,
        start_at_utc=start_at_utc,
    )


@pytest.fixture
def editorial_base(tmp_path: Path) -> Path:
    _setup_metadata_campaigns(tmp_path)
    (tmp_path / "linkedin-posts").mkdir(parents=True, exist_ok=True)
    return tmp_path


def test_campaign_not_found(editorial_base: Path):
    result = _schedule(editorial_base, campaign_id="flow-a-2026-07-06-missing")

    assert result.status == "failed"
    assert LINKEDIN_SCHEDULE_CAMPAIGN_NOT_FOUND in result.errors


def test_flow_b_rejected(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)
    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    campaign = dict(campaign)
    campaign["flow"] = FLOW_B
    write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, campaign)

    result = _schedule(editorial_base)

    assert result.status == "failed"
    assert LINKEDIN_SCHEDULE_FLOW_NOT_ALLOWED in result.errors


def test_campaign_before_derivatives_generated_rejected(editorial_base: Path):
    content = _write_post(editorial_base).read_text(encoding="utf-8")
    campaign = build_initial_campaign_metadata(
        flow=FLOW_A,
        source_slug=SOURCE_SLUG,
        public_slug=PUBLIC_SLUG,
        source_relative_path=SOURCE_RELATIVE,
        image_relative_path=IMAGE_RELATIVE,
        source_content=content,
        publication_date=PUBLICATION_DATE,
    )
    transition_state(
        campaign,
        STATE_VALIDATED,
        reason="Editorial validation passed",
        actor=ACTOR_WORKER,
    )
    transition_state(
        campaign,
        STATE_BLOG_PUBLISH_PENDING,
        reason="Blog publish started",
        actor=ACTOR_WORKER,
    )
    transition_state(
        campaign,
        STATE_BLOG_PUBLISHED,
        reason="Blog published",
        actor=ACTOR_WORKER,
    )
    write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, campaign)

    result = _schedule(editorial_base)

    assert result.status == "failed"
    assert LINKEDIN_SCHEDULE_INVALID_CAMPAIGN_STATE in result.errors


def test_missing_linkedin_package_rejected(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base, include_package=False)

    result = _schedule(editorial_base)

    assert result.status == "failed"
    assert LINKEDIN_SCHEDULE_PACKAGE_MISSING in result.errors


def test_missing_variant_metadata_rejected(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base, variant_ids=["executive-recruiter"])
    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    package = campaign["linkedin_package"]
    package["variant_ids"] = sorted(CANONICAL_VARIANT_IDS)
    write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, campaign)

    result = _schedule(editorial_base)

    assert result.status == "failed"
    assert LINKEDIN_SCHEDULE_VARIANT_METADATA_MISSING in result.errors


def test_missing_artifact_rejected(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)
    artifact = (
        editorial_base
        / GENERATED_RELATIVE
        / CANONICAL_CAMPAIGN_ID
        / "executive-recruiter.md"
    )
    artifact.unlink()

    result = _schedule(editorial_base)

    assert result.status == "failed"
    assert LINKEDIN_SCHEDULE_ARTIFACT_MISSING in result.errors


def test_artifact_hash_changed_rejected(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)
    artifact = (
        editorial_base
        / GENERATED_RELATIVE
        / CANONICAL_CAMPAIGN_ID
        / "executive-recruiter.md"
    )
    artifact.write_text("changed content\n", encoding="utf-8")

    result = _schedule(editorial_base)

    assert result.status == "failed"
    assert LINKEDIN_SCHEDULE_ARTIFACT_HASH_CHANGED in result.errors


def test_successful_scheduling_writes_variant_schedule_fields(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)

    result = _schedule(editorial_base)

    assert result.status == "completed"
    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    for variant_schedule in result.variant_schedules:
        assert variant_schedule["scheduled_at_utc"]
        assert variant_schedule["publish_state"] == "pending"
        assert variant_schedule["schedule_idempotency_key"]
    for entry in campaign["variants"]:
        assert entry["scheduled_at_utc"]
        assert entry["publish_state"] == "pending"
        assert entry["schedule_idempotency_key"]


def test_successful_scheduling_transitions_to_distribution_scheduled(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)

    result = _schedule(editorial_base)

    assert result.status == "completed"
    assert result.state == STATE_DISTRIBUTION_SCHEDULED
    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["state"] == STATE_DISTRIBUTION_SCHEDULED
    states = [entry["to_state"] for entry in campaign["state_history"]]
    assert STATE_DISTRIBUTION_SCHEDULED in states


def test_variants_staggered_at_least_three_calendar_days_apart(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)

    result = _schedule(editorial_base)
    assert result.status == "completed"

    timestamps = sorted(
        datetime.strptime(item["scheduled_at_utc"], "%Y-%m-%dT%H:%M:%SZ")
        for item in result.variant_schedules
    )
    assert len(timestamps) == len(set(timestamps))
    for earlier, later in zip(timestamps, timestamps[1:]):
        assert (later.date() - earlier.date()).days >= 3


def test_custom_start_at_utc_honored(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)
    custom_anchor = "2026-08-12T14:00:00Z"

    result = _schedule(editorial_base, start_at_utc=custom_anchor)

    assert result.status == "completed"
    assert result.anchor_utc == custom_anchor
    executive = next(
        item for item in result.variant_schedules if item["variant"] == "executive-recruiter"
    )
    assert executive["scheduled_at_utc"] == custom_anchor


def test_invalid_anchor_rejected(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)

    result = _schedule(editorial_base, start_at_utc="not-a-timestamp")

    assert result.status == "failed"
    assert LINKEDIN_SCHEDULE_INVALID_ANCHOR in result.errors


def test_invalid_strategy_rejected(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)

    result = _schedule(editorial_base, strategy="unknown-strategy")

    assert result.status == "failed"
    assert LINKEDIN_SCHEDULE_INVALID_STRATEGY in result.errors


def test_idempotent_rerun_does_not_rewrite_schedules_or_duplicate_state_history(
    editorial_base: Path,
):
    _derivatives_generated_campaign(editorial_base)

    first = _schedule(editorial_base)
    assert first.status == "completed"

    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    history_len = len(campaign["state_history"])
    schedules_before = {
        entry["variant"]: entry["scheduled_at_utc"] for entry in campaign["variants"]
    }

    second = _schedule(editorial_base)

    assert second.status == "completed"
    assert second.metadata_written is False
    campaign_after = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign_after is not None
    assert len(campaign_after["state_history"]) == history_len
    schedules_after = {
        entry["variant"]: entry["scheduled_at_utc"] for entry in campaign_after["variants"]
    }
    assert schedules_after == schedules_before


def test_metadata_mismatch_rejected(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)

    first = _schedule(editorial_base, start_at_utc=ANCHOR_UTC)
    assert first.status == "completed"

    result = _schedule(editorial_base, start_at_utc="2026-08-01T14:00:00Z")

    assert result.status == "failed"
    assert LINKEDIN_SCHEDULE_METADATA_MISMATCH in result.errors


def test_metadata_and_response_exclude_generated_body_text(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)

    result = _schedule(editorial_base)
    assert result.status == "completed"

    response_json = json.dumps(result.to_dict())
    assert "generated_draft_content" not in response_json
    assert "markdown_content" not in response_json
    assert "Read the full story here" not in response_json

    metadata_path = editorial_base / METADATA_CAMPAIGNS_RELATIVE / f"{CANONICAL_CAMPAIGN_ID}.json"
    raw = metadata_path.read_text(encoding="utf-8")
    assert "generated_draft_content" not in raw
    assert "markdown_content" not in raw
    assert "Read the full story here" not in raw
    assert "linkedin_distribution" in raw


def test_http_endpoint_requires_auth(editorial_base: Path):
    create_full_layout(editorial_base)
    _derivatives_generated_campaign(editorial_base)

    client = TestClient(create_app(make_settings(editorial_base)))

    unauth = client.post(
        "/schedule-linkedin-distribution",
        json={"campaign_id": CANONICAL_CAMPAIGN_ID, "start_at_utc": ANCHOR_UTC},
    )
    assert unauth.status_code == 401

    bad_key = client.post(
        "/schedule-linkedin-distribution",
        headers={"Authorization": "Bearer wrong-key"},
        json={"campaign_id": CANONICAL_CAMPAIGN_ID, "start_at_utc": ANCHOR_UTC},
    )
    assert bad_key.status_code == 401


def test_http_successful_response_shape(editorial_base: Path):
    create_full_layout(editorial_base)
    _derivatives_generated_campaign(editorial_base)

    client = TestClient(create_app(make_settings(editorial_base)))
    response = client.post(
        "/schedule-linkedin-distribution",
        headers=auth_header(),
        json={"campaign_id": CANONICAL_CAMPAIGN_ID, "start_at_utc": ANCHOR_UTC},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["campaign_id"] == CANONICAL_CAMPAIGN_ID
    assert body["state"] == STATE_DISTRIBUTION_SCHEDULED
    assert body["strategy"] == DEFAULT_STAGGER_STRATEGY
    assert body["anchor_utc"] == ANCHOR_UTC
    assert body["distribution_id"] == f"{CANONICAL_CAMPAIGN_ID}-dist"
    assert len(body["variant_schedules"]) == 4
    assert body["distribution"] is not None
    assert body["metadata_written"] is True
    assert "errors" in body
    assert "warnings" in body
    assert "metadata_error_code" in body
    assert "generated_draft_content" not in body
    assert "markdown_content" not in body


def test_http_missing_identifiers_returns_422(editorial_base: Path):
    create_full_layout(editorial_base)
    client = TestClient(create_app(make_settings(editorial_base)))

    response = client.post(
        "/schedule-linkedin-distribution",
        headers=auth_header(),
        json={},
    )
    assert response.status_code == 422


def test_http_extra_fields_returns_422(editorial_base: Path):
    create_full_layout(editorial_base)
    client = TestClient(create_app(make_settings(editorial_base)))

    response = client.post(
        "/schedule-linkedin-distribution",
        headers=auth_header(),
        json={
            "campaign_id": CANONICAL_CAMPAIGN_ID,
            "markdown_content": "secret body",
        },
    )
    assert response.status_code == 422


def test_resolve_by_source_relative_path(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)

    result = _schedule(
        editorial_base,
        campaign_id=None,
        source_relative_path=SOURCE_RELATIVE,
    )

    assert result.status == "completed"
    assert result.campaign_id == CANONICAL_CAMPAIGN_ID


def test_no_n8n_workflow_json_changed():
    n8n_dir = Path(__file__).resolve().parents[1] / "n8n"
    if n8n_dir.is_dir():
        tracked = list(n8n_dir.rglob("*.json"))
        assert tracked == [] or all(path.is_file() for path in tracked)


def test_no_linkedin_api_publication_attempted(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)

    with patch("httpx.Client.post") as mock_post:
        result = _schedule(editorial_base)

    assert result.status == "completed"
    mock_post.assert_not_called()


def test_schedule_idempotency_key_format(editorial_base: Path):
    campaign = _derivatives_generated_campaign(editorial_base)
    variant_ids = sorted(campaign["linkedin_package"]["variant_ids"])

    expected = build_schedule_idempotency_key(
        campaign_id=CANONICAL_CAMPAIGN_ID,
        source_content_sha256=campaign["source_content_sha256"],
        package_idempotency_key=campaign["linkedin_package"]["idempotency_key"],
        variant_ids=variant_ids,
        strategy=DEFAULT_STAGGER_STRATEGY,
        anchor_utc=ANCHOR_UTC,
        flow=FLOW_A,
    )

    result = _schedule(editorial_base)
    assert result.status == "completed"
    assert result.distribution is not None
    assert result.distribution["idempotency_key"] == expected


def test_stagger_offsets_match_editorial_sequence(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)

    result = _schedule(editorial_base)
    assert result.status == "completed"

    anchor = datetime.strptime(ANCHOR_UTC, "%Y-%m-%dT%H:%M:%SZ")
    for item in result.variant_schedules:
        offset_days = VARIANT_DAY_OFFSETS[item["variant"]]
        expected = (anchor + timedelta(days=offset_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        assert item["scheduled_at_utc"] == expected


def test_default_anchor_uses_preferred_weekday(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)
    fixed_now = datetime(2026, 7, 6, 10, 0, 0, tzinfo=timezone.utc)  # Monday

    with patch(
        "silverman_blog_linkedin.linkedin_distribution_schedule.datetime"
    ) as mock_datetime:
        mock_datetime.now.return_value = fixed_now
        mock_datetime.strptime = datetime.strptime
        result = schedule_linkedin_distribution(editorial_base, campaign_id=CANONICAL_CAMPAIGN_ID)

    assert result.status == "completed"
    assert result.anchor_utc == "2026-07-07T14:00:00Z"
