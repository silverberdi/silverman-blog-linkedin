"""Tests for Flow A LinkedIn publication queue, publish-due, and cancel."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

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
    LINKEDIN_PUBLISH_ARTIFACT_HASH_CHANGED,
    LINKEDIN_PUBLISH_ARTIFACT_MISSING,
    LINKEDIN_PUBLISH_CANCEL_NOT_ALLOWED,
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
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_CANCELLED


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
    result = cancel_linkedin_publication(
        scheduled_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
    )

    assert result.status == "failed"
    assert LINKEDIN_PUBLISH_VARIANT_NOT_QUEUED in result.errors


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
