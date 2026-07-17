"""Tests for Flow A LinkedIn publication queue, publish-due, and cancel."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.campaign_lifecycle import (
    ACTOR_WORKER,
    CANONICAL_VARIANT_IDS,
    FLOW_A,
    FLOW_B,
    METADATA_CAMPAIGNS_RELATIVE,
    STATE_BLOG_PUBLISHED,
    STATE_BLOG_PUBLISH_PENDING,
    STATE_DERIVATIVES_GENERATED,
    STATE_DERIVATIVES_PENDING,
    STATE_DISTRIBUTION_SCHEDULED,
    STATE_FLOW_A_COMPLETE,
    STATE_VALIDATED,
    build_derivative_idempotency_key,
    build_initial_campaign_metadata,
    read_campaign_metadata,
    transition_state,
    write_campaign_metadata,
)
from silverman_blog_linkedin.linkedin_distribution_schedule import schedule_linkedin_distribution
from silverman_blog_linkedin.linkedin_package_flow import (
    GENERATED_RELATIVE,
    build_package_idempotency_key,
)
from silverman_blog_linkedin.linkedin_publication_flow import (
    LINKEDIN_OAUTH_REAUTHORIZATION_REQUIRED,
    LINKEDIN_OAUTH_TOKEN_MISSING,
    LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_NOT_DUE,
    LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_SEQUENCE,
    LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_STATE,
    LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_SUPERVISION,
    LINKEDIN_PUBLISH_BLOCKED_CADENCE,
    LINKEDIN_PUBLISH_BLOCKED_EVIDENCE_INVALID,
    LINKEDIN_PUBLISH_BLOCKED_SEQUENCE,
    LINKEDIN_PUBLISH_ARTIFACT_HASH_CHANGED,
    LINKEDIN_PUBLISH_ARTIFACT_MISSING,
    LINKEDIN_PUBLISH_CANCEL_NOT_ALLOWED,
    LINKEDIN_PUBLISH_CONTENT_INVALID,
    LINKEDIN_PUBLISH_API_ERROR,
    LINKEDIN_PUBLISH_INVALID_CAMPAIGN_STATE,
    LINKEDIN_PUBLISH_MEMBER_URN_MISSING,
    LINKEDIN_PUBLISH_NOT_ENABLED,
    LINKEDIN_PUBLISH_TOKEN_MISSING,
    LINKEDIN_PUBLISH_VARIANT_NOT_DUE,
    LINKEDIN_PUBLISH_VARIANT_NOT_PENDING,
    LINKEDIN_PUBLISH_VARIANT_NOT_QUEUED,
    PUBLISH_STATE_CANCELLED,
    PUBLISH_STATE_FAILED,
    PUBLISH_STATE_PENDING,
    PUBLISH_STATE_PUBLISHED,
    PUBLISH_STATE_QUEUED,
    cancel_linkedin_publication,
    publish_linkedin_due_variants,
    queue_linkedin_publication,
)
from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, make_settings

SOURCE_SLUG = "01-why-i-did-not-start-with-the-database"
PUBLIC_SLUG = "why-i-did-not-start-with-the-database"
PUBLICATION_DATE = "2026-07-06"
SOURCE_RELATIVE = f"blog-posts/ready/{SOURCE_SLUG}.md"
IMAGE_RELATIVE = f"blog-posts/ready/{SOURCE_SLUG}.png"
CANONICAL_CAMPAIGN_ID = f"flow-a-{PUBLICATION_DATE}-{PUBLIC_SLUG}"
PUBLIC_URL = "https://silverman.pro/2026/07/06/why-i-did-not-start-with-the-database/"
ANCHOR_UTC = "2026-07-07T14:00:00Z"
TITLE = "Why I Did Not Start With the Database"
TARGET_VARIANT = "executive-recruiter"
MEMBER_URN = "urn:li:person:test-member-id"
ACCESS_TOKEN = "test-linkedin-access-token-should-not-appear-in-responses"


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
    transition_state(campaign, STATE_VALIDATED, reason="validated", actor=ACTOR_WORKER)
    transition_state(
        campaign, STATE_BLOG_PUBLISH_PENDING, reason="publish pending", actor=ACTOR_WORKER
    )
    transition_state(campaign, STATE_BLOG_PUBLISHED, reason="published", actor=ACTOR_WORKER)
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

    campaign["variants"] = variant_entries
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
        campaign, STATE_DERIVATIVES_PENDING, reason="derivatives pending", actor=ACTOR_WORKER
    )
    transition_state(
        campaign, STATE_DERIVATIVES_GENERATED, reason="derivatives generated", actor=ACTOR_WORKER
    )
    write_campaign_metadata(base, CANONICAL_CAMPAIGN_ID, campaign)
    return campaign


def _distribution_scheduled_campaign(base: Path) -> dict:
    _derivatives_generated_campaign(base)
    result = schedule_linkedin_distribution(
        base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        start_at_utc=ANCHOR_UTC,
    )
    assert result.status == "completed"
    campaign = read_campaign_metadata(base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["state"] == STATE_DISTRIBUTION_SCHEDULED
    return campaign


def _real_publish_env(**overrides: str) -> dict[str, str]:
    env = {
        "SILVERMAN_LINKEDIN_ACCESS_TOKEN": ACCESS_TOKEN,
        "SILVERMAN_LINKEDIN_MEMBER_URN": MEMBER_URN,
        "SILVERMAN_LINKEDIN_PUBLICATION_ENABLED": "true",
        "SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES": "120",
    }
    env.update(overrides)
    return env


def _queue_variant(
    base: Path,
    *,
    variant: str = TARGET_VARIANT,
    dry_run: bool = False,
    safety_delay_minutes: int | None = None,
    publish_after_utc: str | None = None,
    now: datetime | None = None,
) -> None:
    result = queue_linkedin_publication(
        base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=variant,
        dry_run=dry_run,
        safety_delay_minutes=safety_delay_minutes,
        publish_after_utc=publish_after_utc,
        now=now,
    )
    assert result.status == "completed", result.errors


def _update_variant(base: Path, variant: str = TARGET_VARIANT, **updates: object) -> dict:
    campaign = read_campaign_metadata(base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(item for item in campaign["variants"] if item["variant"] == variant)
    entry.update(updates)
    write_result = write_campaign_metadata(base, CANONICAL_CAMPAIGN_ID, campaign)
    assert write_result.written
    return entry


@pytest.fixture
def editorial_base(tmp_path: Path) -> Path:
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


def test_queue_pending_to_queued_with_default_safety_delay(scheduled_base: Path):
    fixed_now = datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc)

    result = queue_linkedin_publication(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        now=fixed_now,
    )

    assert result.status == "completed"
    assert result.dry_run is False
    assert result.publish_state == PUBLISH_STATE_QUEUED
    assert result.publication_safety_delay_minutes == 120
    assert result.publish_after_utc == "2026-07-07T14:00:00Z"
    assert result.publication_mode == "safety_delay"
    assert result.publication_queued_at

    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_QUEUED
    assert entry["publish_after_utc"] == "2026-07-07T14:00:00Z"
    assert campaign["state"] == STATE_DISTRIBUTION_SCHEDULED


def test_queue_dry_run_does_not_mutate(scheduled_base: Path):
    result = queue_linkedin_publication(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=True,
    )

    assert result.status == "completed"
    assert result.dry_run is True
    assert result.publish_after_utc
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_PENDING


def test_publish_due_publishes_due_variant_with_mocked_client(scheduled_base: Path):
    past = datetime(2026, 7, 7, 10, 0, 0, tzinfo=timezone.utc)
    _queue_variant(
        scheduled_base,
        publish_after_utc="2026-07-07T09:00:00Z",
        now=past,
    )

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.headers = {"x-restli-id": "urn:li:share:1234567890"}
    mock_client.post.return_value = mock_response

    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert result.status == "completed"
    assert len(result.results) == 1
    item = result.results[0]
    assert item.publish_state == PUBLISH_STATE_PUBLISHED
    assert item.linkedin_post_urn == "urn:li:share:1234567890"
    assert item.published_at
    mock_client.post.assert_called_once()

    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_PUBLISHED
    assert entry["linkedin_post_urn"] == "urn:li:share:1234567890"
    assert campaign["state"] == STATE_DISTRIBUTION_SCHEDULED


def test_publish_due_skips_not_yet_due_unless_publish_now(scheduled_base: Path):
    future = datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc)
    _queue_variant(
        scheduled_base,
        publish_after_utc="2026-07-07T18:00:00Z",
        now=future,
    )

    skipped = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        publish_now=False,
        environ=_real_publish_env(),
        now=future,
    )
    assert skipped.results[0].skipped is True
    assert skipped.results[0].skip_reason == LINKEDIN_PUBLISH_VARIANT_NOT_DUE

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.headers = {"x-restli-id": "urn:li:share:999"}
    mock_client.post.return_value = mock_response

    forced = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        publish_now=True,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=future,
    )
    assert forced.results[0].publish_state == PUBLISH_STATE_PUBLISHED
    mock_client.post.assert_called_once()


def test_cancel_queued_to_cancelled(scheduled_base: Path):
    _queue_variant(scheduled_base)

    result = cancel_linkedin_publication(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
    )

    assert result.status == "completed"
    assert result.publish_state == PUBLISH_STATE_CANCELLED
    assert result.phase == "post_queue"
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_CANCELLED
    assert entry["operator_supervision"]["cancellation"]["phase"] == "post_queue"
    assert entry["linkedin_publication"]["cancelled_at"]


def test_cancel_pending_to_cancelled(scheduled_base: Path):
    result = cancel_linkedin_publication(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
    )

    assert result.status == "completed"
    assert result.publish_state == PUBLISH_STATE_CANCELLED
    assert result.phase == "pre_queue"
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_CANCELLED
    assert entry["operator_supervision"]["cancellation"]["phase"] == "pre_queue"
    assert entry["operator_supervision"]["auto_queue_eligible"] is False


def test_cancel_published_rejected(scheduled_base: Path):
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


@pytest.mark.parametrize(
    "env_overrides,expected_error",
    [
        ({"SILVERMAN_LINKEDIN_ACCESS_TOKEN": ""}, LINKEDIN_PUBLISH_TOKEN_MISSING),
        ({"SILVERMAN_LINKEDIN_MEMBER_URN": ""}, LINKEDIN_PUBLISH_MEMBER_URN_MISSING),
        ({"SILVERMAN_LINKEDIN_PUBLICATION_ENABLED": "false"}, LINKEDIN_PUBLISH_NOT_ENABLED),
    ],
)
def test_config_errors_do_not_mark_variant_failed(
    scheduled_base: Path, env_overrides: dict[str, str], expected_error: str
):
    _queue_variant(scheduled_base, publish_after_utc="2026-07-07T09:00:00Z")

    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        environ=_real_publish_env(**env_overrides),
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert result.status == "failed"
    assert expected_error in result.errors
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_QUEUED


def test_oauth_action_required_does_not_call_linkedin_or_mark_failed(
    scheduled_base: Path, tmp_path: Path
):
    _queue_variant(scheduled_base, publish_after_utc="2026-07-07T09:00:00Z")

    token_store = tmp_path / "secrets" / "linkedin-oauth-tokens.json"
    env = _real_publish_env(
        SILVERMAN_LINKEDIN_TOKEN_STORE_PATH=str(token_store),
        SILVERMAN_LINKEDIN_ACCESS_TOKEN="",
        SILVERMAN_LINKEDIN_MEMBER_URN="",
        SILVERMAN_LINKEDIN_CLIENT_ID="test-client",
        SILVERMAN_LINKEDIN_CLIENT_SECRET="test-secret",
        SILVERMAN_LINKEDIN_REDIRECT_URI="https://api.silverman.pro/linkedin/oauth/callback",
    )

    mock_client = MagicMock()
    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        environ=env,
        http_client=mock_client,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert result.status == "failed"
    assert LINKEDIN_OAUTH_TOKEN_MISSING in result.errors
    mock_client.post.assert_not_called()
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_QUEUED


def test_oauth_reauthorization_required_preserves_queued_state(
    scheduled_base: Path, tmp_path: Path
):
    _queue_variant(scheduled_base, publish_after_utc="2026-07-07T09:00:00Z")

    token_store = tmp_path / "secrets" / "linkedin-oauth-tokens.json"
    token_store.parent.mkdir(parents=True, exist_ok=True)
    from silverman_blog_linkedin.linkedin_token_store import (
        LinkedInTokenRecord,
        save_token_record,
    )

    save_token_record(
        token_store,
        LinkedInTokenRecord(
            access_token="expired-token",
            refresh_token=None,
            scope="openid profile w_member_social",
            token_type="Bearer",
            created_at="2026-07-07T08:00:00Z",
            expires_at="2026-07-07T08:30:00Z",
            refresh_expires_at=None,
            member_urn=MEMBER_URN,
        ),
    )

    env = _real_publish_env(
        SILVERMAN_LINKEDIN_TOKEN_STORE_PATH=str(token_store),
        SILVERMAN_LINKEDIN_ACCESS_TOKEN="",
        SILVERMAN_LINKEDIN_MEMBER_URN="",
        SILVERMAN_LINKEDIN_CLIENT_ID="test-client",
        SILVERMAN_LINKEDIN_CLIENT_SECRET="test-secret",
        SILVERMAN_LINKEDIN_REDIRECT_URI="https://api.silverman.pro/linkedin/oauth/callback",
    )

    mock_client = MagicMock()
    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        environ=env,
        http_client=mock_client,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert result.status == "failed"
    assert LINKEDIN_OAUTH_REAUTHORIZATION_REQUIRED in result.errors
    mock_client.post.assert_not_called()
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_QUEUED


def test_real_api_failure_marks_variant_failed(scheduled_base: Path):
    _queue_variant(scheduled_base, publish_after_utc="2026-07-07T09:00:00Z")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_client.post.return_value = mock_response

    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert result.status == "failed"
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_FAILED
    assert entry["linkedin_publication"]["last_error_code"]


def test_dry_run_defaults_on_all_endpoints(client: TestClient, scheduled_base: Path):
    queue_resp = client.post(
        "/queue-linkedin-publication",
        headers=auth_header(),
        json={"campaign_id": CANONICAL_CAMPAIGN_ID, "variant": TARGET_VARIANT},
    )
    assert queue_resp.status_code == 200
    queue_body = queue_resp.json()
    assert queue_body["dry_run"] is True
    assert queue_body["status"] == "completed"

    _queue_variant(scheduled_base, publish_after_utc="2026-07-07T09:00:00Z")

    publish_resp = client.post(
        "/publish-linkedin-due-variants",
        headers=auth_header(),
        json={"campaign_id": CANONICAL_CAMPAIGN_ID, "variant": TARGET_VARIANT},
    )
    assert publish_resp.status_code == 200
    publish_body = publish_resp.json()
    assert publish_body["dry_run"] is True

    cancel_resp = client.post(
        "/cancel-linkedin-publication",
        headers=auth_header(),
        json={"campaign_id": CANONICAL_CAMPAIGN_ID, "variant": TARGET_VARIANT},
    )
    assert cancel_resp.status_code == 200
    cancel_body = cancel_resp.json()
    assert cancel_body["dry_run"] is True


def test_idempotent_published_rerun(scheduled_base: Path):
    past = datetime(2026, 7, 7, 10, 0, 0, tzinfo=timezone.utc)
    _queue_variant(scheduled_base, publish_after_utc="2026-07-07T09:00:00Z", now=past)

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.headers = {"x-restli-id": "urn:li:share:once"}
    mock_client.post.return_value = mock_response

    first = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert first.results[0].publish_state == PUBLISH_STATE_PUBLISHED

    second = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 13, 0, 0, tzinfo=timezone.utc),
    )
    assert second.results[0].status == "completed"
    assert second.results[0].publish_state == PUBLISH_STATE_PUBLISHED
    assert mock_client.post.call_count == 1


def test_wrong_campaign_state_rejected(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)

    result = queue_linkedin_publication(
        editorial_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
    )

    assert result.status == "failed"
    assert LINKEDIN_PUBLISH_INVALID_CAMPAIGN_STATE in result.errors


def test_flow_a_complete_campaign_can_queue(scheduled_base: Path):
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    transition_state(
        campaign,
        STATE_FLOW_A_COMPLETE,
        reason="flow a complete for publication validation",
        actor=ACTOR_WORKER,
    )
    write_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID, campaign)

    result = queue_linkedin_publication(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
    )

    assert result.status == "completed"
    assert result.publish_state == PUBLISH_STATE_QUEUED


def test_missing_artifact_rejected(scheduled_base: Path):
    artifact = (
        scheduled_base
        / GENERATED_RELATIVE
        / CANONICAL_CAMPAIGN_ID
        / f"{TARGET_VARIANT}.md"
    )
    artifact.unlink()

    result = queue_linkedin_publication(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
    )

    assert result.status == "failed"
    assert LINKEDIN_PUBLISH_ARTIFACT_MISSING in result.errors


def test_artifact_hash_mismatch_rejected(scheduled_base: Path):
    artifact = (
        scheduled_base
        / GENERATED_RELATIVE
        / CANONICAL_CAMPAIGN_ID
        / f"{TARGET_VARIANT}.md"
    )
    artifact.write_text("changed on disk\n", encoding="utf-8")

    result = queue_linkedin_publication(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
    )

    assert result.status == "failed"
    assert LINKEDIN_PUBLISH_ARTIFACT_HASH_CHANGED in result.errors


def test_queue_rejects_non_pending_state(scheduled_base: Path):
    _queue_variant(scheduled_base)

    result = queue_linkedin_publication(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
    )

    assert result.status == "failed"
    assert LINKEDIN_PUBLISH_VARIANT_NOT_PENDING in result.errors


def test_http_auth_required(client: TestClient):
    for path, payload in [
        (
            "/queue-linkedin-publication",
            {"campaign_id": CANONICAL_CAMPAIGN_ID, "variant": TARGET_VARIANT},
        ),
        (
            "/publish-linkedin-due-variants",
            {"campaign_id": CANONICAL_CAMPAIGN_ID, "variant": TARGET_VARIANT},
        ),
        (
            "/cancel-linkedin-publication",
            {"campaign_id": CANONICAL_CAMPAIGN_ID, "variant": TARGET_VARIANT},
        ),
    ]:
        missing = client.post(path, json=payload)
        assert missing.status_code == 401
        invalid = client.post(path, headers=auth_header("wrong"), json=payload)
        assert invalid.status_code == 401


@pytest.mark.parametrize(
    "path,payload",
    [
        (
            "/queue-linkedin-publication",
            {
                "campaign_id": CANONICAL_CAMPAIGN_ID,
                "variant": TARGET_VARIANT,
                "unexpected": True,
            },
        ),
        (
            "/publish-linkedin-due-variants",
            {
                "campaign_id": CANONICAL_CAMPAIGN_ID,
                "variant": TARGET_VARIANT,
                "unexpected": True,
            },
        ),
        (
            "/cancel-linkedin-publication",
            {
                "campaign_id": CANONICAL_CAMPAIGN_ID,
                "variant": TARGET_VARIANT,
                "unexpected": True,
            },
        ),
    ],
)
def test_http_422_for_extra_fields(client: TestClient, path: str, payload: dict):
    response = client.post(path, headers=auth_header(), json=payload)
    assert response.status_code == 422


def test_responses_exclude_tokens(client: TestClient, scheduled_base: Path):
    _queue_variant(scheduled_base, publish_after_utc="2026-07-07T09:00:00Z")

    response = client.post(
        "/publish-linkedin-due-variants",
        headers=auth_header(),
        json={
            "campaign_id": CANONICAL_CAMPAIGN_ID,
            "variant": TARGET_VARIANT,
            "dry_run": False,
        },
    )
    assert response.status_code == 200
    serialized = json.dumps(response.json())
    assert ACCESS_TOKEN not in serialized
    assert "CHANGE_ME" not in serialized


def test_openapi_includes_publication_paths(client: TestClient):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    for path in [
        "/queue-linkedin-publication",
        "/publish-linkedin-due-variants",
        "/cancel-linkedin-publication",
    ]:
        assert path in paths


def test_flow_b_rejected(editorial_base: Path):
    _distribution_scheduled_campaign(editorial_base)
    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    campaign = dict(campaign)
    campaign["flow"] = FLOW_B
    write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, campaign)

    result = queue_linkedin_publication(
        editorial_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
    )

    assert result.status == "failed"
    assert "linkedin_publish_flow_not_allowed" in result.errors


def test_cancel_wrong_state_rejected(scheduled_base: Path):
    _update_variant(scheduled_base, publish_state=PUBLISH_STATE_FAILED)
    result = cancel_linkedin_publication(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
    )

    assert result.status == "failed"
    assert "linkedin_supervision_action_not_allowed" in result.errors


def test_publish_due_dry_run_does_not_call_api(scheduled_base: Path):
    _queue_variant(scheduled_base, publish_after_utc="2026-07-07T09:00:00Z")

    mock_client = MagicMock()
    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=True,
        http_client=mock_client,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert result.status == "completed"
    mock_client.post.assert_not_called()
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_QUEUED


def test_auto_queue_defaults_off_and_preserves_response_contract(
    scheduled_base: Path,
):
    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        publish_now=True,
        environ=_real_publish_env(),
    )

    payload = result.to_dict()
    assert payload == {
        "status": "failed",
        "dry_run": False,
        "publish_now": True,
        "results": [
            {
                "campaign_id": CANONICAL_CAMPAIGN_ID,
                "variant": TARGET_VARIANT,
                "publish_state": PUBLISH_STATE_PENDING,
                "publish_after_utc": None,
                "published_at": None,
                "linkedin_post_urn": None,
                "status": "failed",
                "errors": [LINKEDIN_PUBLISH_VARIANT_NOT_QUEUED],
                "warnings": [],
                "skipped": False,
                "skip_reason": None,
            }
        ],
        "errors": [LINKEDIN_PUBLISH_VARIANT_NOT_QUEUED],
        "warnings": [],
    }
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_PENDING


def test_auto_queue_due_pending_publishes_once(scheduled_base: Path):
    _update_variant(scheduled_base, scheduled_at_utc="2026-07-07T11:00:00Z")
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.headers = {"x-restli-id": "urn:li:share:auto-once"}
    mock_client.post.return_value = mock_response

    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        publish_now=True,
        auto_queue_pending=True,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert result.status == "completed"
    assert result.auto_queue_results[0].publish_state == PUBLISH_STATE_QUEUED
    assert result.results[0].publish_state == PUBLISH_STATE_PUBLISHED
    assert result.results[0].linkedin_post_urn == "urn:li:share:auto-once"
    mock_client.post.assert_called_once()


@pytest.mark.parametrize(
    ("updates", "publish_now", "expected_reason", "expected_state"),
    [
        (
            {"scheduled_at_utc": "2026-07-07T13:00:00Z"},
            False,
            LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_NOT_DUE,
            PUBLISH_STATE_PENDING,
        ),
        (
            {"scheduled_at_utc": "not-a-timestamp"},
            True,
            LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_NOT_DUE,
            PUBLISH_STATE_PENDING,
        ),
        (
            {
                "publish_state": PUBLISH_STATE_CANCELLED,
                "operator_supervision": {
                    "last_action": "cancel",
                    "auto_queue_eligible": False,
                },
            },
            True,
            LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_SUPERVISION,
            PUBLISH_STATE_CANCELLED,
        ),
        (
            {
                "scheduled_at_utc": "2026-07-07T13:00:00Z",
                "operator_supervision": {
                    "last_action": "defer",
                    "auto_queue_eligible": False,
                },
            },
            True,
            LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_SUPERVISION,
            PUBLISH_STATE_PENDING,
        ),
        (
            {"publish_state": PUBLISH_STATE_FAILED},
            True,
            LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_STATE,
            PUBLISH_STATE_FAILED,
        ),
    ],
)
def test_auto_queue_exclusions_do_not_mutate(
    scheduled_base: Path,
    updates: dict,
    publish_now: bool,
    expected_reason: str,
    expected_state: str,
):
    _update_variant(scheduled_base, **updates)

    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        publish_now=publish_now,
        auto_queue_pending=True,
        environ=_real_publish_env(),
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert result.status == "completed"
    assert result.results == []
    assert result.auto_queue_results[0].skipped is True
    assert result.auto_queue_results[0].skip_reason == expected_reason
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["publish_state"] == expected_state
    if "operator_supervision" in updates:
        assert entry["operator_supervision"] == updates["operator_supervision"]


def test_deferred_variant_becomes_eligible_when_due_without_persisted_flip(
    scheduled_base: Path,
):
    supervision = {"last_action": "defer", "auto_queue_eligible": False}
    _update_variant(
        scheduled_base,
        scheduled_at_utc="2026-07-07T11:00:00Z",
        operator_supervision=supervision,
    )

    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        publish_now=False,
        auto_queue_pending=True,
        environ=_real_publish_env(
            SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES="120"
        ),
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert result.status == "completed"
    assert result.auto_queue_results[0].publish_state == PUBLISH_STATE_QUEUED
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["operator_supervision"]["auto_queue_eligible"] is False


def test_publish_now_bypasses_only_strategy_schedule_gate(scheduled_base: Path):
    _update_variant(scheduled_base, scheduled_at_utc="2026-07-07T18:00:00Z")

    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=True,
        publish_now=True,
        auto_queue_pending=True,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert result.auto_queue_results[0].skipped is False
    assert result.auto_queue_results[0].publish_state == PUBLISH_STATE_QUEUED
    assert result.results[0].warnings == ["linkedin_publish_dry_run"]


def test_auto_queue_repeat_is_once_only_and_does_not_requeue(scheduled_base: Path):
    _update_variant(scheduled_base, scheduled_at_utc="2026-07-07T11:00:00Z")
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.headers = {"x-restli-id": "urn:li:share:auto-idempotent"}
    mock_client.post.return_value = mock_response
    request = {
        "campaign_id": CANONICAL_CAMPAIGN_ID,
        "variant": TARGET_VARIANT,
        "dry_run": False,
        "publish_now": True,
        "auto_queue_pending": True,
        "environ": _real_publish_env(),
        "http_client": mock_client,
    }

    first = publish_linkedin_due_variants(
        scheduled_base,
        **request,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    first_entry = next(
        v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT
    )
    queued_at = first_entry["publication_queued_at"]
    published_at = first_entry["published_at"]
    post_urn = first_entry["linkedin_post_urn"]

    second = publish_linkedin_due_variants(
        scheduled_base,
        **request,
        now=datetime(2026, 7, 7, 13, 0, 0, tzinfo=timezone.utc),
    )

    assert first.status == second.status == "completed"
    assert second.auto_queue_results[0].skip_reason == (
        LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_STATE
    )
    assert second.results[0].warnings == ["linkedin_publish_already_published"]
    mock_client.post.assert_called_once()
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    second_entry = next(
        v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT
    )
    assert second_entry["publication_queued_at"] == queued_at
    assert second_entry["published_at"] == published_at
    assert second_entry["linkedin_post_urn"] == post_urn


def test_auto_queue_fail_closed_and_dry_run_have_no_unsafe_side_effects(
    scheduled_base: Path,
):
    _update_variant(scheduled_base, scheduled_at_utc="2026-07-07T11:00:00Z")
    mock_client = MagicMock()

    dry_run = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=True,
        publish_now=True,
        auto_queue_pending=True,
        http_client=mock_client,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert dry_run.status == "completed"
    mock_client.post.assert_not_called()
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_PENDING

    real_disabled = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        publish_now=True,
        auto_queue_pending=True,
        environ=_real_publish_env(SILVERMAN_LINKEDIN_PUBLICATION_ENABLED="false"),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert real_disabled.status == "failed"
    assert LINKEDIN_PUBLISH_NOT_ENABLED in real_disabled.errors
    mock_client.post.assert_not_called()
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_QUEUED


def test_auto_queue_safety_delay_is_second_due_gate(scheduled_base: Path):
    _update_variant(scheduled_base, scheduled_at_utc="2026-07-07T11:00:00Z")
    mock_client = MagicMock()

    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        publish_now=False,
        auto_queue_pending=True,
        environ=_real_publish_env(
            SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES="120"
        ),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert result.status == "completed"
    assert result.auto_queue_results[0].publish_after_utc == "2026-07-07T14:00:00Z"
    assert result.results[0].publish_state == PUBLISH_STATE_QUEUED
    assert result.results[0].skip_reason == LINKEDIN_PUBLISH_VARIANT_NOT_DUE
    mock_client.post.assert_not_called()


def test_auto_queue_http_contract_and_variant_filter_validation(client: TestClient):
    accepted = client.post(
        "/publish-linkedin-due-variants",
        headers=auth_header(),
        json={
            "campaign_id": CANONICAL_CAMPAIGN_ID,
            "variant": TARGET_VARIANT,
            "auto_queue_pending": True,
        },
    )
    assert accepted.status_code == 200
    assert accepted.json()["auto_queue_pending"] is True
    assert accepted.json()["dry_run"] is True

    invalid_filter = client.post(
        "/publish-linkedin-due-variants",
        headers=auth_header(),
        json={"variant": TARGET_VARIANT, "auto_queue_pending": True},
    )
    assert invalid_filter.status_code == 422

    unknown = client.post(
        "/publish-linkedin-due-variants",
        headers=auth_header(),
        json={"auto_queue_pending": True, "safety_delay_minutes": 0},
    )
    assert unknown.status_code == 422


def test_publish_pending_workflow_is_inactive_safe_http_only():
    workflow_path = (
        Path(__file__).resolve().parents[1]
        / "n8n"
        / "workflows"
        / "silverman-blog-linkedin-publish-pending.json"
    )
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    assert workflow["active"] is False
    node_types = {node["type"] for node in workflow["nodes"]}
    assert "n8n-nodes-base.manualTrigger" in node_types
    assert "n8n-nodes-base.executeCommand" not in node_types
    serialized = json.dumps(workflow)
    assert "/health" in serialized
    assert "/publish-linkedin-due-variants" in serialized
    assert "auto_queue_pending" in serialized
    config = next(
        node for node in workflow["nodes"] if node["name"] == "Set Configuration"
    )
    values = {
        item["name"]: item["value"]
        for item in config["parameters"]["assignments"]["assignments"]
    }
    assert values["dry_run"] is True


def _assert_no_secrets_or_body_text(payload: object) -> None:
    serialized = json.dumps(payload)
    assert ACCESS_TOKEN not in serialized
    assert "The real problem is not persistence" not in serialized
    assert _artifact_content(TARGET_VARIANT) not in serialized


# --- US-019 publication evidence / failure taxonomy / auto-queue evidence ---


def test_us019_complete_evidence_after_real_publish_success(scheduled_base: Path):
    _queue_variant(scheduled_base, publish_after_utc="2026-07-07T09:00:00Z")
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.headers = {"x-restli-id": "urn:li:share:us019-success"}
    mock_client.post.return_value = mock_response

    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert result.status == "completed"
    item = result.results[0]
    assert item.publish_state == PUBLISH_STATE_PUBLISHED
    assert item.linkedin_post_urn == "urn:li:share:us019-success"
    assert item.published_at
    assert item.published_at.endswith("Z")

    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["linkedin_post_urn"] == "urn:li:share:us019-success"
    assert entry["published_at"] == item.published_at
    publication = entry["linkedin_publication"]
    assert publication["provider"] == "linkedin_rest_posts"
    assert publication["post_urn"] == entry["linkedin_post_urn"]
    assert publication["published_at"] == entry["published_at"]
    assert publication["http_status"] == 201
    assert isinstance(publication["http_status"], int)
    _assert_no_secrets_or_body_text(result.to_dict())
    _assert_no_secrets_or_body_text(entry)


def test_us019_failure_context_shape_api_and_transport_errors(scheduled_base: Path):
    _queue_variant(scheduled_base, publish_after_utc="2026-07-07T09:00:00Z")
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_client.post.return_value = mock_response

    api_failure = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert api_failure.status == "failed"
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    failed_entry = next(
        v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT
    )
    assert failed_entry["publish_state"] == PUBLISH_STATE_FAILED
    failure_ctx = failed_entry["linkedin_publication"]
    assert failure_ctx["last_error_code"] == "linkedin_publish_insufficient_permission"
    assert failure_ctx["last_failed_at"].endswith("Z")
    assert failure_ctx["retryable"] is False
    assert failure_ctx["http_status"] == 403
    assert isinstance(failure_ctx["http_status"], int)
    _assert_no_secrets_or_body_text(api_failure.to_dict())
    _assert_no_secrets_or_body_text(failed_entry)

    _update_variant(
        scheduled_base,
        publish_state=PUBLISH_STATE_QUEUED,
        linkedin_publication=None,
    )
    transport_client = MagicMock()
    transport_client.post.side_effect = httpx.ConnectError("connection refused")

    transport_failure = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        environ=_real_publish_env(),
        http_client=transport_client,
        now=datetime(2026, 7, 7, 12, 5, 0, tzinfo=timezone.utc),
    )
    assert transport_failure.status == "failed"
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    transport_entry = next(
        v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT
    )
    assert transport_entry["publish_state"] == PUBLISH_STATE_FAILED
    transport_ctx = transport_entry["linkedin_publication"]
    assert transport_ctx["last_error_code"] == LINKEDIN_PUBLISH_API_ERROR
    assert transport_ctx["last_failed_at"].endswith("Z")
    assert transport_ctx["retryable"] is True
    assert "http_status" in transport_ctx
    assert transport_ctx["http_status"] is None
    _assert_no_secrets_or_body_text(transport_failure.to_dict())
    _assert_no_secrets_or_body_text(transport_entry)


def test_us019_content_rejection_uses_dedicated_stable_code(scheduled_base: Path):
    _queue_variant(scheduled_base, publish_after_utc="2026-07-07T09:00:00Z")
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 422
    mock_client.post.return_value = mock_response

    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert result.status == "failed"
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_FAILED
    assert entry["linkedin_publication"]["last_error_code"] == (
        LINKEDIN_PUBLISH_CONTENT_INVALID
    )
    assert entry["linkedin_publication"]["last_error_code"] != LINKEDIN_PUBLISH_API_ERROR
    assert entry["linkedin_publication"]["http_status"] == 422
    assert isinstance(entry["linkedin_publication"]["http_status"], int)


def test_us019_success_without_post_identifier_treated_as_failure(
    scheduled_base: Path,
):
    _queue_variant(scheduled_base, publish_after_utc="2026-07-07T09:00:00Z")
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.headers = {}
    mock_client.post.return_value = mock_response

    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert result.status == "failed"
    assert LINKEDIN_PUBLISH_API_ERROR in result.errors
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_FAILED
    assert entry.get("linkedin_post_urn") in (None, "")
    assert entry["linkedin_publication"]["last_error_code"] == LINKEDIN_PUBLISH_API_ERROR
    assert entry["linkedin_publication"]["http_status"] == 201


@pytest.mark.parametrize(
    "env_overrides,expected_error",
    [
        ({"SILVERMAN_LINKEDIN_PUBLICATION_ENABLED": "false"}, LINKEDIN_PUBLISH_NOT_ENABLED),
        ({"SILVERMAN_LINKEDIN_MEMBER_URN": ""}, LINKEDIN_PUBLISH_MEMBER_URN_MISSING),
        ({"SILVERMAN_LINKEDIN_ACCESS_TOKEN": ""}, LINKEDIN_PUBLISH_TOKEN_MISSING),
    ],
)
def test_us019_blocked_conditions_leave_publish_state_unchanged(
    scheduled_base: Path, env_overrides: dict[str, str], expected_error: str
):
    _queue_variant(scheduled_base, publish_after_utc="2026-07-07T09:00:00Z")
    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        environ=_real_publish_env(**env_overrides),
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert result.status == "failed"
    assert expected_error in result.errors
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_QUEUED
    assert entry["publish_state"] != PUBLISH_STATE_FAILED


def test_us019_oauth_action_required_leaves_publish_state_unchanged(
    scheduled_base: Path, tmp_path: Path
):
    _queue_variant(scheduled_base, publish_after_utc="2026-07-07T09:00:00Z")
    token_store = tmp_path / "secrets" / "linkedin-oauth-tokens.json"
    env = _real_publish_env(
        SILVERMAN_LINKEDIN_TOKEN_STORE_PATH=str(token_store),
        SILVERMAN_LINKEDIN_ACCESS_TOKEN="",
        SILVERMAN_LINKEDIN_MEMBER_URN="",
        SILVERMAN_LINKEDIN_CLIENT_ID="test-client",
        SILVERMAN_LINKEDIN_CLIENT_SECRET="test-secret",
        SILVERMAN_LINKEDIN_REDIRECT_URI="https://api.silverman.pro/linkedin/oauth/callback",
    )
    mock_client = MagicMock()
    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        environ=env,
        http_client=mock_client,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert result.status == "failed"
    assert LINKEDIN_OAUTH_TOKEN_MISSING in result.errors
    mock_client.post.assert_not_called()
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_QUEUED


def test_us019_response_carries_evidence_for_published_and_already_published(
    scheduled_base: Path,
):
    _queue_variant(scheduled_base, publish_after_utc="2026-07-07T09:00:00Z")
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.headers = {"x-restli-id": "urn:li:share:us019-response"}
    mock_client.post.return_value = mock_response

    first = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert first.results[0].linkedin_post_urn == "urn:li:share:us019-response"
    assert first.results[0].published_at

    second = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 13, 0, 0, tzinfo=timezone.utc),
    )
    assert second.results[0].warnings == ["linkedin_publish_already_published"]
    assert second.results[0].linkedin_post_urn == first.results[0].linkedin_post_urn
    assert second.results[0].published_at == first.results[0].published_at
    mock_client.post.assert_called_once()


def test_us019_idempotency_preserves_evidence_across_rerun_modes(
    scheduled_base: Path,
):
    _update_variant(scheduled_base, scheduled_at_utc="2026-07-07T11:00:00Z")
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.headers = {"x-restli-id": "urn:li:share:us019-idempotent"}
    mock_client.post.return_value = mock_response

    first = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        publish_now=True,
        auto_queue_pending=True,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert first.status == "completed"
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    stored_urn = entry["linkedin_post_urn"]
    stored_published_at = entry["published_at"]
    assert stored_urn == "urn:li:share:us019-idempotent"
    assert first.auto_queue_results[0].linkedin_post_urn == stored_urn
    assert first.auto_queue_results[0].published_at == stored_published_at

    direct = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 12, 30, 0, tzinfo=timezone.utc),
    )
    assert direct.results[0].linkedin_post_urn == stored_urn
    assert direct.results[0].published_at == stored_published_at

    with_publish_now = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        publish_now=True,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 12, 45, 0, tzinfo=timezone.utc),
    )
    assert with_publish_now.results[0].linkedin_post_urn == stored_urn
    assert with_publish_now.results[0].published_at == stored_published_at

    with_auto_queue = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        publish_now=True,
        auto_queue_pending=True,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 13, 0, 0, tzinfo=timezone.utc),
    )
    assert with_auto_queue.auto_queue_results[0].skip_reason == (
        LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_STATE
    )
    assert with_auto_queue.auto_queue_results[0].linkedin_post_urn == stored_urn
    assert with_auto_queue.auto_queue_results[0].published_at == stored_published_at
    assert with_auto_queue.results[0].linkedin_post_urn == stored_urn
    assert with_auto_queue.results[0].published_at == stored_published_at

    mock_client.post.assert_called_once()
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    final_entry = next(
        v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT
    )
    assert final_entry["linkedin_post_urn"] == stored_urn
    assert final_entry["published_at"] == stored_published_at


def test_us019_auto_queue_results_carry_evidence_including_cross_campaign_scan(
    scheduled_base: Path,
):
    _update_variant(scheduled_base, scheduled_at_utc="2026-07-07T11:00:00Z")
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.headers = {"x-restli-id": "urn:li:share:us019-auto-queue"}
    mock_client.post.return_value = mock_response

    published = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        publish_now=True,
        auto_queue_pending=True,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )
    aq = published.auto_queue_results[0]
    assert aq.linkedin_post_urn == "urn:li:share:us019-auto-queue"
    assert aq.published_at
    assert published.results[0].linkedin_post_urn == aq.linkedin_post_urn

    already = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        publish_now=True,
        auto_queue_pending=True,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 13, 0, 0, tzinfo=timezone.utc),
    )
    already_aq = already.auto_queue_results[0]
    assert already_aq.skip_reason == LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_STATE
    assert already_aq.linkedin_post_urn == aq.linkedin_post_urn
    assert already_aq.published_at == aq.published_at

    for variant_id in CANONICAL_VARIANT_IDS:
        if variant_id == TARGET_VARIANT:
            continue
        _update_variant(
            scheduled_base,
            variant=variant_id,
            scheduled_at_utc="2026-07-07T18:00:00Z",
            publish_state=PUBLISH_STATE_PENDING,
        )
    other_variant = next(
        variant_id
        for variant_id in CANONICAL_VARIANT_IDS
        if variant_id != TARGET_VARIANT
    )

    cross = publish_linkedin_due_variants(
        scheduled_base,
        dry_run=False,
        publish_now=False,
        auto_queue_pending=True,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 14, 0, 0, tzinfo=timezone.utc),
    )
    cross_entries = [
        item
        for item in cross.auto_queue_results
        if item.campaign_id == CANONICAL_CAMPAIGN_ID
        and item.variant == TARGET_VARIANT
    ]
    assert len(cross_entries) == 1
    assert cross_entries[0].skip_reason == LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_STATE
    assert cross_entries[0].linkedin_post_urn == aq.linkedin_post_urn
    assert cross_entries[0].published_at == aq.published_at

    no_evidence = next(
        item
        for item in cross.auto_queue_results
        if item.variant == other_variant
    )
    assert no_evidence.skip_reason == LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_NOT_DUE
    payload = no_evidence.to_dict()
    assert payload["linkedin_post_urn"] is None
    assert payload["published_at"] is None

    mock_client.post.assert_called_once()


def test_us019_no_automatic_retry_after_failed_real_attempt(scheduled_base: Path):
    _update_variant(scheduled_base, scheduled_at_utc="2026-07-07T11:00:00Z")
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_client.post.return_value = mock_response

    first = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        publish_now=True,
        auto_queue_pending=True,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert first.status == "failed"
    mock_client.post.assert_called_once()
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_FAILED

    second = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        publish_now=True,
        auto_queue_pending=True,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 13, 0, 0, tzinfo=timezone.utc),
    )
    assert second.auto_queue_results[0].skip_reason == (
        LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_STATE
    )
    assert second.auto_queue_results[0].publish_state == PUBLISH_STATE_FAILED
    assert second.auto_queue_results[0].linkedin_post_urn is None
    assert second.auto_queue_results[0].published_at is None
    mock_client.post.assert_called_once()
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    final_entry = next(
        v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT
    )
    assert final_entry["publish_state"] == PUBLISH_STATE_FAILED


def test_us019_auto_queue_fields_null_when_no_publication_evidence(
    scheduled_base: Path,
):
    _update_variant(
        scheduled_base,
        scheduled_at_utc="2026-07-07T13:00:00Z",
    )
    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=True,
        auto_queue_pending=True,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert result.auto_queue_results[0].skipped is True
    payload = result.auto_queue_results[0].to_dict()
    assert payload["linkedin_post_urn"] is None
    assert payload["published_at"] is None
    assert "linkedin_post_urn" in payload
    assert "published_at" in payload
    assert "publish_state" in payload
    assert "skip_reason" in payload


# --- US-020 publish-time sequence and cadence guard ---

SECOND_VARIANT = "engineering-leadership"
THIRD_VARIANT = "technical-architect"
US020_NOW = datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc)
PAST_DUE_UTC = "2026-07-07T09:00:00Z"


def _mock_success_client(urn: str) -> MagicMock:
    client = MagicMock()
    response = MagicMock()
    response.status_code = 201
    response.headers = {"x-restli-id": urn}
    client.post.return_value = response
    return client


def _read_variant_entry(base: Path, campaign_id: str, variant: str) -> dict:
    campaign = read_campaign_metadata(base, campaign_id)
    assert campaign is not None
    return next(v for v in campaign["variants"] if v["variant"] == variant)


def _update_campaign_variant(
    base: Path,
    campaign_id: str,
    variant: str,
    *,
    remove: tuple[str, ...] = (),
    **updates: object,
) -> dict:
    campaign = read_campaign_metadata(base, campaign_id)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == variant)
    for key in remove:
        entry.pop(key, None)
    entry.update(updates)
    assert write_campaign_metadata(base, campaign_id, campaign).written
    return entry


def _queue_campaign_variant(
    base: Path, campaign_id: str, variant: str, *, publish_after_utc: str
) -> None:
    result = queue_linkedin_publication(
        base,
        campaign_id=campaign_id,
        variant=variant,
        dry_run=False,
        publish_after_utc=publish_after_utc,
    )
    assert result.status == "completed", result.errors


def _clone_campaign(base: Path, new_campaign_id: str) -> None:
    campaign = read_campaign_metadata(base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    clone = deepcopy(campaign)
    clone["campaign_id"] = new_campaign_id
    src_dir = base / GENERATED_RELATIVE / CANONICAL_CAMPAIGN_ID
    dst_dir = base / GENERATED_RELATIVE / new_campaign_id
    dst_dir.mkdir(parents=True, exist_ok=True)
    for entry in clone["variants"]:
        variant_id = entry["variant"]
        (dst_dir / f"{variant_id}.md").write_bytes(
            (src_dir / f"{variant_id}.md").read_bytes()
        )
        entry["artifact_relative_path"] = (
            f"{GENERATED_RELATIVE}/{new_campaign_id}/{variant_id}.md"
        )
        entry["campaign_id"] = new_campaign_id
    assert write_campaign_metadata(base, new_campaign_id, clone).written


def test_us020_sequence_blocks_later_queued_variant_while_earlier_queued(
    scheduled_base: Path,
):
    _queue_variant(
        scheduled_base, variant=TARGET_VARIANT, publish_after_utc=PAST_DUE_UTC
    )
    _queue_variant(
        scheduled_base, variant=SECOND_VARIANT, publish_after_utc=PAST_DUE_UTC
    )
    mock_client = _mock_success_client("urn:li:share:us020-sequence")

    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        dry_run=False,
        auto_queue_pending=True,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=US020_NOW,
    )

    assert result.status == "completed"
    by_variant = {item.variant: item for item in result.results}
    assert by_variant[TARGET_VARIANT].publish_state == PUBLISH_STATE_PUBLISHED
    blocked = by_variant[SECOND_VARIANT]
    assert blocked.skipped is True
    assert blocked.skip_reason == LINKEDIN_PUBLISH_BLOCKED_SEQUENCE
    assert blocked.publish_state == PUBLISH_STATE_QUEUED
    mock_client.post.assert_called_once()
    entry = _read_variant_entry(scheduled_base, CANONICAL_CAMPAIGN_ID, SECOND_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_QUEUED


def test_us020_plain_publish_due_enforces_sequence_guard(scheduled_base: Path):
    _queue_variant(
        scheduled_base, variant=TARGET_VARIANT, publish_after_utc=PAST_DUE_UTC
    )
    _queue_variant(
        scheduled_base, variant=SECOND_VARIANT, publish_after_utc=PAST_DUE_UTC
    )
    mock_client = _mock_success_client("urn:li:share:us020-plain")

    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        dry_run=False,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=US020_NOW,
    )

    assert result.status == "completed"
    by_variant = {item.variant: item for item in result.results}
    assert by_variant[TARGET_VARIANT].publish_state == PUBLISH_STATE_PUBLISHED
    assert by_variant[SECOND_VARIANT].skip_reason == LINKEDIN_PUBLISH_BLOCKED_SEQUENCE
    mock_client.post.assert_called_once()
    entry = _read_variant_entry(scheduled_base, CANONICAL_CAMPAIGN_ID, SECOND_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_QUEUED


def test_us020_publish_now_bypasses_neither_sequence_nor_cadence(
    scheduled_base: Path,
):
    _queue_variant(
        scheduled_base,
        variant=TARGET_VARIANT,
        publish_after_utc="2026-07-08T09:00:00Z",
    )
    _queue_variant(
        scheduled_base,
        variant=SECOND_VARIANT,
        publish_after_utc="2026-07-08T09:00:00Z",
    )
    mock_client = MagicMock()

    sequence_blocked = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=SECOND_VARIANT,
        dry_run=False,
        publish_now=True,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=US020_NOW,
    )
    assert sequence_blocked.status == "completed"
    assert sequence_blocked.results[0].skipped is True
    assert sequence_blocked.results[0].skip_reason == LINKEDIN_PUBLISH_BLOCKED_SEQUENCE
    mock_client.post.assert_not_called()

    _update_variant(
        scheduled_base,
        variant=TARGET_VARIANT,
        publish_state=PUBLISH_STATE_PUBLISHED,
        published_at="2026-07-06T12:00:00Z",
        linkedin_post_urn="urn:li:share:us020-recent",
    )

    cadence_blocked = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=SECOND_VARIANT,
        dry_run=False,
        publish_now=True,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=US020_NOW,
    )
    assert cadence_blocked.status == "completed"
    assert cadence_blocked.results[0].skipped is True
    assert cadence_blocked.results[0].skip_reason == LINKEDIN_PUBLISH_BLOCKED_CADENCE
    mock_client.post.assert_not_called()
    entry = _read_variant_entry(scheduled_base, CANONICAL_CAMPAIGN_ID, SECOND_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_QUEUED


def test_us020_cadence_blocks_publication_under_72_hours(scheduled_base: Path):
    _update_variant(
        scheduled_base,
        variant=TARGET_VARIANT,
        publish_state=PUBLISH_STATE_PUBLISHED,
        published_at="2026-07-06T12:00:00Z",
        linkedin_post_urn="urn:li:share:us020-under-72h",
    )
    _queue_variant(
        scheduled_base, variant=SECOND_VARIANT, publish_after_utc=PAST_DUE_UTC
    )
    mock_client = MagicMock()

    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        dry_run=False,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=US020_NOW,
    )

    assert result.status == "completed"
    assert result.results[0].variant == SECOND_VARIANT
    assert result.results[0].skipped is True
    assert result.results[0].skip_reason == LINKEDIN_PUBLISH_BLOCKED_CADENCE
    mock_client.post.assert_not_called()
    entry = _read_variant_entry(scheduled_base, CANONICAL_CAMPAIGN_ID, SECOND_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_QUEUED


def test_us020_cadence_allows_publication_at_or_after_72_hours(
    scheduled_base: Path,
):
    _update_variant(
        scheduled_base,
        variant=TARGET_VARIANT,
        publish_state=PUBLISH_STATE_PUBLISHED,
        published_at="2026-07-04T11:00:00Z",
        linkedin_post_urn="urn:li:share:us020-over-72h",
    )
    _queue_variant(
        scheduled_base, variant=SECOND_VARIANT, publish_after_utc=PAST_DUE_UTC
    )
    mock_client = _mock_success_client("urn:li:share:us020-next")

    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        dry_run=False,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=US020_NOW,
    )

    assert result.status == "completed"
    assert result.results[0].variant == SECOND_VARIANT
    assert result.results[0].publish_state == PUBLISH_STATE_PUBLISHED
    mock_client.post.assert_called_once()
    entry = _read_variant_entry(scheduled_base, CANONICAL_CAMPAIGN_ID, SECOND_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_PUBLISHED


def test_us020_within_run_cadence_blocks_second_same_campaign_publish(
    scheduled_base: Path,
):
    _update_variant(
        scheduled_base,
        variant=SECOND_VARIANT,
        publish_state=PUBLISH_STATE_CANCELLED,
    )
    _queue_variant(
        scheduled_base, variant=TARGET_VARIANT, publish_after_utc=PAST_DUE_UTC
    )
    _queue_variant(
        scheduled_base, variant=THIRD_VARIANT, publish_after_utc=PAST_DUE_UTC
    )
    mock_client = _mock_success_client("urn:li:share:us020-within-run")

    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        dry_run=False,
        auto_queue_pending=True,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=US020_NOW,
    )

    assert result.status == "completed"
    by_variant = {item.variant: item for item in result.results}
    assert by_variant[TARGET_VARIANT].publish_state == PUBLISH_STATE_PUBLISHED
    blocked = by_variant[THIRD_VARIANT]
    assert blocked.skipped is True
    assert blocked.skip_reason == LINKEDIN_PUBLISH_BLOCKED_CADENCE
    mock_client.post.assert_called_once()
    entry = _read_variant_entry(scheduled_base, CANONICAL_CAMPAIGN_ID, THIRD_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_QUEUED


def test_us020_failed_and_cancelled_release_sequence_without_retry(
    scheduled_base: Path,
):
    failure_evidence = {
        "last_error_code": LINKEDIN_PUBLISH_API_ERROR,
        "last_failed_at": "2026-07-06T10:00:00Z",
        "retryable": True,
        "http_status": 500,
    }
    _update_variant(
        scheduled_base,
        variant=TARGET_VARIANT,
        publish_state=PUBLISH_STATE_FAILED,
        linkedin_publication=failure_evidence,
    )
    _update_variant(
        scheduled_base,
        variant=SECOND_VARIANT,
        publish_state=PUBLISH_STATE_CANCELLED,
    )
    _queue_variant(
        scheduled_base, variant=THIRD_VARIANT, publish_after_utc=PAST_DUE_UTC
    )
    failed_before = json.dumps(
        _read_variant_entry(scheduled_base, CANONICAL_CAMPAIGN_ID, TARGET_VARIANT),
        sort_keys=True,
    )
    mock_client = _mock_success_client("urn:li:share:us020-released")

    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        dry_run=False,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=US020_NOW,
    )

    assert result.status == "completed"
    assert result.results[0].variant == THIRD_VARIANT
    assert result.results[0].publish_state == PUBLISH_STATE_PUBLISHED
    mock_client.post.assert_called_once()
    failed_after = json.dumps(
        _read_variant_entry(scheduled_base, CANONICAL_CAMPAIGN_ID, TARGET_VARIANT),
        sort_keys=True,
    )
    assert failed_after == failed_before


def test_us020_deferred_earlier_variant_blocks_followers_without_mutation(
    scheduled_base: Path,
):
    deferred_supervision = {"last_action": "defer", "auto_queue_eligible": False}
    _update_variant(
        scheduled_base,
        variant=TARGET_VARIANT,
        scheduled_at_utc="2026-07-09T14:00:00Z",
        operator_supervision=deferred_supervision,
    )
    _queue_variant(
        scheduled_base, variant=SECOND_VARIANT, publish_after_utc=PAST_DUE_UTC
    )
    _update_variant(
        scheduled_base,
        variant=THIRD_VARIANT,
        scheduled_at_utc="2026-07-07T11:00:00Z",
    )
    deferred_before = json.dumps(
        _read_variant_entry(scheduled_base, CANONICAL_CAMPAIGN_ID, TARGET_VARIANT),
        sort_keys=True,
    )
    mock_client = MagicMock()

    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        dry_run=False,
        publish_now=True,
        auto_queue_pending=True,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=US020_NOW,
    )

    assert result.status == "completed"
    auto_by_variant = {item.variant: item for item in result.auto_queue_results}
    assert auto_by_variant[TARGET_VARIANT].skip_reason == (
        LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_SUPERVISION
    )
    assert auto_by_variant[THIRD_VARIANT].skip_reason == (
        LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_SEQUENCE
    )
    assert result.results[0].variant == SECOND_VARIANT
    assert result.results[0].skipped is True
    assert result.results[0].skip_reason == LINKEDIN_PUBLISH_BLOCKED_SEQUENCE
    mock_client.post.assert_not_called()
    deferred_after = json.dumps(
        _read_variant_entry(scheduled_base, CANONICAL_CAMPAIGN_ID, TARGET_VARIANT),
        sort_keys=True,
    )
    assert deferred_after == deferred_before
    assert (
        _read_variant_entry(scheduled_base, CANONICAL_CAMPAIGN_ID, THIRD_VARIANT)[
            "publish_state"
        ]
        == PUBLISH_STATE_PENDING
    )
    assert (
        _read_variant_entry(scheduled_base, CANONICAL_CAMPAIGN_ID, SECOND_VARIANT)[
            "publish_state"
        ]
        == PUBLISH_STATE_QUEUED
    )


def test_us020_cross_campaign_scan_evaluates_campaigns_independently(
    scheduled_base: Path,
):
    other_campaign_id = "flow-a-2026-07-06-other-campaign"
    _clone_campaign(scheduled_base, other_campaign_id)
    _update_variant(
        scheduled_base,
        variant=TARGET_VARIANT,
        publish_state=PUBLISH_STATE_PUBLISHED,
        published_at="2026-07-06T12:00:00Z",
        linkedin_post_urn="urn:li:share:us020-campaign-a",
    )
    _queue_variant(
        scheduled_base, variant=SECOND_VARIANT, publish_after_utc=PAST_DUE_UTC
    )
    _queue_campaign_variant(
        scheduled_base,
        other_campaign_id,
        TARGET_VARIANT,
        publish_after_utc=PAST_DUE_UTC,
    )
    mock_client = _mock_success_client("urn:li:share:us020-campaign-b")

    result = publish_linkedin_due_variants(
        scheduled_base,
        dry_run=False,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=US020_NOW,
    )

    assert result.status == "completed"
    by_key = {(item.campaign_id, item.variant): item for item in result.results}
    blocked = by_key[(CANONICAL_CAMPAIGN_ID, SECOND_VARIANT)]
    assert blocked.skipped is True
    assert blocked.skip_reason == LINKEDIN_PUBLISH_BLOCKED_CADENCE
    published = by_key[(other_campaign_id, TARGET_VARIANT)]
    assert published.publish_state == PUBLISH_STATE_PUBLISHED
    mock_client.post.assert_called_once()
    entry = _read_variant_entry(scheduled_base, other_campaign_id, TARGET_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_PUBLISHED


def test_us020_dry_run_reports_guard_blocks_without_mutation_or_calls(
    scheduled_base: Path,
):
    evidence_campaign_id = "flow-a-2026-07-06-evidence-campaign"
    cadence_campaign_id = "flow-a-2026-07-06-cadence-campaign"
    _clone_campaign(scheduled_base, evidence_campaign_id)
    _clone_campaign(scheduled_base, cadence_campaign_id)

    _queue_variant(
        scheduled_base, variant=TARGET_VARIANT, publish_after_utc=PAST_DUE_UTC
    )
    _queue_variant(
        scheduled_base, variant=SECOND_VARIANT, publish_after_utc=PAST_DUE_UTC
    )

    _queue_campaign_variant(
        scheduled_base,
        evidence_campaign_id,
        SECOND_VARIANT,
        publish_after_utc=PAST_DUE_UTC,
    )
    _update_campaign_variant(
        scheduled_base,
        evidence_campaign_id,
        TARGET_VARIANT,
        publish_state=PUBLISH_STATE_PUBLISHED,
        published_at="not-a-timestamp",
        linkedin_post_urn="urn:li:share:us020-evidence",
    )

    _queue_campaign_variant(
        scheduled_base,
        cadence_campaign_id,
        SECOND_VARIANT,
        publish_after_utc=PAST_DUE_UTC,
    )
    _update_campaign_variant(
        scheduled_base,
        cadence_campaign_id,
        TARGET_VARIANT,
        publish_state=PUBLISH_STATE_PUBLISHED,
        published_at="2026-07-06T12:00:00Z",
        linkedin_post_urn="urn:li:share:us020-cadence",
    )

    metadata_dir = scheduled_base / METADATA_CAMPAIGNS_RELATIVE
    snapshots = {
        path.name: path.read_bytes() for path in metadata_dir.glob("*.json")
    }
    mock_client = MagicMock()

    result = publish_linkedin_due_variants(
        scheduled_base,
        dry_run=True,
        http_client=mock_client,
        now=US020_NOW,
    )

    assert result.status == "completed"
    by_key = {(item.campaign_id, item.variant): item for item in result.results}
    assert by_key[(CANONICAL_CAMPAIGN_ID, SECOND_VARIANT)].skip_reason == (
        LINKEDIN_PUBLISH_BLOCKED_SEQUENCE
    )
    assert by_key[(evidence_campaign_id, SECOND_VARIANT)].skip_reason == (
        LINKEDIN_PUBLISH_BLOCKED_EVIDENCE_INVALID
    )
    assert by_key[(cadence_campaign_id, SECOND_VARIANT)].skip_reason == (
        LINKEDIN_PUBLISH_BLOCKED_CADENCE
    )
    assert by_key[(CANONICAL_CAMPAIGN_ID, TARGET_VARIANT)].warnings == (
        ["linkedin_publish_dry_run"]
    )
    mock_client.post.assert_not_called()
    for path in metadata_dir.glob("*.json"):
        assert path.read_bytes() == snapshots[path.name]


def test_us020_missing_published_at_fails_closed_and_visibly(
    scheduled_base: Path,
):
    other_campaign_id = "flow-a-2026-07-06-healthy-campaign"
    _clone_campaign(scheduled_base, other_campaign_id)

    _queue_variant(
        scheduled_base, variant=SECOND_VARIANT, publish_after_utc=PAST_DUE_UTC
    )
    _update_variant(
        scheduled_base,
        variant=TARGET_VARIANT,
        publish_state=PUBLISH_STATE_PUBLISHED,
        linkedin_post_urn="urn:li:share:us020-missing-evidence",
    )
    _update_campaign_variant(
        scheduled_base,
        CANONICAL_CAMPAIGN_ID,
        TARGET_VARIANT,
        remove=("published_at",),
    )
    _queue_campaign_variant(
        scheduled_base,
        other_campaign_id,
        TARGET_VARIANT,
        publish_after_utc=PAST_DUE_UTC,
    )
    mock_client = _mock_success_client("urn:li:share:us020-healthy")

    result = publish_linkedin_due_variants(
        scheduled_base,
        dry_run=False,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=US020_NOW,
    )

    assert result.status == "completed"
    by_key = {(item.campaign_id, item.variant): item for item in result.results}
    blocked = by_key[(CANONICAL_CAMPAIGN_ID, SECOND_VARIANT)]
    assert blocked.skipped is True
    assert blocked.skip_reason == LINKEDIN_PUBLISH_BLOCKED_EVIDENCE_INVALID
    healthy = by_key[(other_campaign_id, TARGET_VARIANT)]
    assert healthy.publish_state == PUBLISH_STATE_PUBLISHED
    mock_client.post.assert_called_once()
    entry = _read_variant_entry(scheduled_base, CANONICAL_CAMPAIGN_ID, SECOND_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_QUEUED


def test_us020_manually_queued_out_of_order_variant_blocked_at_publish_time(
    scheduled_base: Path,
):
    _queue_variant(
        scheduled_base, variant=SECOND_VARIANT, publish_after_utc=PAST_DUE_UTC
    )
    mock_client = MagicMock()

    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=SECOND_VARIANT,
        dry_run=False,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=US020_NOW,
    )

    assert result.status == "completed"
    assert result.results[0].skipped is True
    assert result.results[0].skip_reason == LINKEDIN_PUBLISH_BLOCKED_SEQUENCE
    mock_client.post.assert_not_called()
    entry = _read_variant_entry(scheduled_base, CANONICAL_CAMPAIGN_ID, SECOND_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_QUEUED
    assert (
        _read_variant_entry(scheduled_base, CANONICAL_CAMPAIGN_ID, TARGET_VARIANT)[
            "publish_state"
        ]
        == PUBLISH_STATE_PENDING
    )


def test_us020_not_due_precedence_over_sequence_at_auto_queue(
    scheduled_base: Path,
):
    _update_variant(
        scheduled_base,
        variant=TARGET_VARIANT,
        scheduled_at_utc="2026-07-07T11:00:00Z",
    )

    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        dry_run=True,
        auto_queue_pending=True,
        now=US020_NOW,
    )

    auto_by_variant = {item.variant: item for item in result.auto_queue_results}
    assert auto_by_variant[SECOND_VARIANT].skipped is True
    assert auto_by_variant[SECOND_VARIANT].skip_reason == (
        LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_NOT_DUE
    )


def test_us020_auto_queue_sequence_pre_filter_skips_later_pending(
    scheduled_base: Path,
):
    _update_variant(
        scheduled_base,
        variant=TARGET_VARIANT,
        scheduled_at_utc="2026-07-07T11:00:00Z",
    )
    _update_variant(
        scheduled_base,
        variant=SECOND_VARIANT,
        scheduled_at_utc="2026-07-07T11:00:00Z",
    )

    result = publish_linkedin_due_variants(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        dry_run=False,
        auto_queue_pending=True,
        environ=_real_publish_env(),
        now=US020_NOW,
    )

    assert result.status == "completed"
    auto_by_variant = {item.variant: item for item in result.auto_queue_results}
    assert auto_by_variant[TARGET_VARIANT].publish_state == PUBLISH_STATE_QUEUED
    assert auto_by_variant[SECOND_VARIANT].skipped is True
    assert auto_by_variant[SECOND_VARIANT].skip_reason == (
        LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_SEQUENCE
    )
    entry = _read_variant_entry(scheduled_base, CANONICAL_CAMPAIGN_ID, SECOND_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_PENDING
