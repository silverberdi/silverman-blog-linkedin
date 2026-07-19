"""US-035 restart / crash-recovery validation for mid-flight Flow A interruption.

Simulates worker/process interruption by freezing durable campaign metadata and
filesystem evidence mid-stage, then re-entering via claim, stale reclaim,
calendar execute, incomplete-campaign resume, or LinkedIn publish-due.
Uses shortened SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS (minimum 60).
Does not kill real processes or call real ComfyUI/LinkedIn APIs.
"""

from __future__ import annotations

import hashlib
import inspect
import threading
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from silverman_blog_linkedin.blog_image_generation import (
    SKIP_REASON_PUBLIC_ASSET_REUSE,
    ensure_blog_image,
)
from silverman_blog_linkedin.blog_publish_flow import (
    BLOG_PUBLISH_TARGET_EXISTS,
    publish_blog_post,
)
from silverman_blog_linkedin.campaign_lifecycle import (
    ACTOR_WORKER,
    CANONICAL_VARIANT_IDS,
    EXECUTION_STATE_PROCESSING,
    EXECUTION_STATE_STALE,
    FLOW_A,
    RECOVERY_MANUAL_INTERVENTION_REQUIRED,
    RECOVERY_RETRYABLE,
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
from silverman_blog_linkedin.comfyui_client import FakeComfyUIClient
from silverman_blog_linkedin.comfyui_config import (
    LOCAL_WORKFLOW_PATH,
    ComfyUISettings,
    ComfyUISettingsLoadResult,
)
from silverman_blog_linkedin.editorial_calendar_flow_a_execute import (
    EXECUTION_STATUS_FAILED,
    execute_due_editorial_calendar_flow_a,
)
from silverman_blog_linkedin.flow_a_incomplete_campaign_recovery import (
    REASON_ACTIVE_CLAIM,
    resume_incomplete_campaign_recovery,
)
from silverman_blog_linkedin.flow_a_operational_queue import (
    FLOW_A_EXECUTION_ALREADY_CLAIMED,
    accept_flow_a_source_for_queue,
    claim_flow_a_execution,
    detect_stale_flow_a_execution,
)
from silverman_blog_linkedin.linkedin_distribution_schedule import (
    LINKEDIN_SCHEDULE_METADATA_MISMATCH,
    schedule_linkedin_distribution,
)
from silverman_blog_linkedin.linkedin_package_flow import (
    GENERATED_RELATIVE,
    build_package_idempotency_key,
)
from silverman_blog_linkedin.linkedin_publication_flow import (
    LINKEDIN_PUBLISH_API_ERROR,
    LINKEDIN_PUBLISH_RECOVERY_CONFIRMATION_REQUIRED,
    PUBLISH_STATE_FAILED,
    PUBLISH_STATE_PENDING,
    PUBLISH_STATE_PUBLISHED,
    PUBLISH_STATE_QUEUED,
    RECOVERY_CLASS_UNCERTAIN,
    classify_linkedin_recovery,
    publish_linkedin_due_variants,
    queue_linkedin_publication,
)
from silverman_blog_linkedin.main import create_app
from tests.conftest import create_full_layout, make_settings

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
SITE_URL = "https://silverman.pro"

QUEUE_SOURCE_SLUG = "02-example-post"
QUEUE_PUBLIC_SLUG = "example-post"
QUEUE_READY_RELATIVE = f"blog-posts/ready/{QUEUE_SOURCE_SLUG}.md"
QUEUE_CAMPAIGN_ID = f"flow-a-{PUBLICATION_DATE}-{QUEUE_PUBLIC_SLUG}"
QUEUE_MARKDOWN = "# Example\n\nBody content.\n"

STALE_SECONDS = "60"
PAST_PROGRESS = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime(
    "%Y-%m-%dT%H:%M:%SZ"
)


@pytest.fixture
def editorial_base(tmp_path: Path) -> Path:
    base = tmp_path / "editorial"
    create_full_layout(base)
    return base


@pytest.fixture
def public_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "public-blog"
    (repo / "_posts").mkdir(parents=True)
    (repo / "assets" / "images").mkdir(parents=True)
    return repo


def _calendar_item(campaign_id: str = QUEUE_CAMPAIGN_ID) -> dict:
    return {"campaign_id": campaign_id, "due_at_utc": "2026-07-06T14:00:00Z"}


def _write_queue_ready(base: Path) -> None:
    ready = base / "blog-posts" / "ready"
    ready.mkdir(parents=True, exist_ok=True)
    (ready / f"{QUEUE_SOURCE_SLUG}.md").write_text(QUEUE_MARKDOWN, encoding="utf-8")


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


def _write_post(base: Path, *, with_png: bool = True) -> Path:
    ready = base / "blog-posts" / "ready"
    ready.mkdir(parents=True, exist_ok=True)
    md_path = ready / f"{SOURCE_SLUG}.md"
    md_path.write_text(_canonical_frontmatter() + _canonical_body(), encoding="utf-8")
    if with_png:
        (ready / f"{SOURCE_SLUG}.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    return md_path


def _artifact_content(variant_id: str) -> str:
    return f"LinkedIn draft for {variant_id}.\nRead the full story here: {PUBLIC_URL}\n"


def _write_artifact(base: Path, variant_id: str) -> tuple[str, str]:
    artifact_dir = base / GENERATED_RELATIVE / CANONICAL_CAMPAIGN_ID
    artifact_dir.mkdir(parents=True, exist_ok=True)
    body = _artifact_content(variant_id)
    raw = body.encode("utf-8")
    (artifact_dir / f"{variant_id}.md").write_bytes(raw)
    return (
        f"{GENERATED_RELATIVE}/{CANONICAL_CAMPAIGN_ID}/{variant_id}.md",
        hashlib.sha256(raw).hexdigest(),
    )


def _variant_entry(
    variant_id: str,
    *,
    artifact_relative_path: str,
    derivative_content_sha256: str,
    source_hash: str,
) -> dict:
    return {
        "variant": variant_id,
        "audience": "senior practitioners",
        "tone": "executive",
        "source_public_url": PUBLIC_URL,
        "source_relative_path": SOURCE_RELATIVE,
        "campaign_id": CANONICAL_CAMPAIGN_ID,
        "source_content_sha256": source_hash,
        "derivative_content_sha256": derivative_content_sha256,
        "artifact_relative_path": artifact_relative_path,
        "idempotency_key": build_derivative_idempotency_key(
            campaign_id=CANONICAL_CAMPAIGN_ID,
            source_content_sha256=source_hash,
            variant=variant_id,
            flow=FLOW_A,
        ),
        "generated_at": "2026-07-06T12:00:00Z",
        "provider": "deepseek",
        "model": "deepseek-chat",
    }


def _derivatives_generated_campaign(base: Path) -> dict:
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
    for state, reason in (
        (STATE_VALIDATED, "validated"),
        (STATE_BLOG_PUBLISH_PENDING, "publish pending"),
        (STATE_BLOG_PUBLISHED, "published"),
    ):
        transition_state(campaign, state, reason=reason, actor=ACTOR_WORKER)
    campaign["source_public_url"] = PUBLIC_URL
    source_hash = campaign["source_content_sha256"]
    variant_ids = sorted(CANONICAL_VARIANT_IDS)
    variant_entries = []
    for variant_id in variant_ids:
        artifact_relative, derivative_hash = _write_artifact(base, variant_id)
        variant_entries.append(
            _variant_entry(
                variant_id,
                artifact_relative_path=artifact_relative,
                derivative_content_sha256=derivative_hash,
                source_hash=source_hash,
            )
        )
    campaign["variants"] = variant_entries
    campaign["linkedin_package"] = {
        "package_id": f"{CANONICAL_CAMPAIGN_ID}-pkg",
        "idempotency_key": build_package_idempotency_key(
            campaign_id=CANONICAL_CAMPAIGN_ID,
            source_content_sha256=source_hash,
            variant_ids=variant_ids,
            flow=FLOW_A,
        ),
        "package_status": "generated",
        "generated_at": "2026-07-06T12:00:00Z",
        "source_public_url": PUBLIC_URL,
        "source_relative_path": SOURCE_RELATIVE,
        "source_content_sha256": source_hash,
        "variant_ids": variant_ids,
    }
    transition_state(
        campaign, STATE_DERIVATIVES_PENDING, reason="derivatives pending", actor=ACTOR_WORKER
    )
    transition_state(
        campaign,
        STATE_DERIVATIVES_GENERATED,
        reason="derivatives generated",
        actor=ACTOR_WORKER,
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
    return campaign


def _distribution_scheduled_history_count(campaign: dict) -> int:
    return sum(
        1
        for entry in campaign.get("state_history") or []
        if isinstance(entry, dict) and entry.get("to_state") == STATE_DISTRIBUTION_SCHEDULED
    )


def _real_publish_env(**overrides: str) -> dict[str, str]:
    env = {
        "SILVERMAN_LINKEDIN_ACCESS_TOKEN": ACCESS_TOKEN,
        "SILVERMAN_LINKEDIN_MEMBER_URN": MEMBER_URN,
        "SILVERMAN_LINKEDIN_PUBLICATION_ENABLED": "true",
        "SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES": "120",
    }
    env.update(overrides)
    return env


def _queue_variant(base: Path, *, variant: str = TARGET_VARIANT) -> None:
    result = queue_linkedin_publication(
        base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=variant,
        dry_run=False,
        now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert result.status == "completed", result.errors


def _enabled_comfy_config(*, dry_run: bool = False) -> ComfyUISettingsLoadResult:
    return ComfyUISettingsLoadResult(
        settings=ComfyUISettings(
            enabled=True,
            base_url="http://127.0.0.1:8188",
            api_prefix="",
            api_key=None,
            auth_header_name="Authorization",
            extra_data_api_key_field=None,
            workflow_path=LOCAL_WORKFLOW_PATH,
            timeout_seconds=30,
            image_width=1200,
            image_height=900,
            dry_run=dry_run,
        )
    )


def _validated_publish_campaign(base: Path, content: str) -> dict:
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
        reason="validated for US-035 restart fixtures",
        actor=ACTOR_WORKER,
    )
    write_campaign_metadata(base, CANONICAL_CAMPAIGN_ID, campaign)
    return campaign


def _claim_then_interrupt(base: Path, campaign_id: str = QUEUE_CAMPAIGN_ID) -> dict:
    """Simulate mid-flight crash: claim succeeds, progress clock freezes."""
    claim = claim_flow_a_execution(base, campaign_id=campaign_id)
    assert claim.status == "completed"
    campaign = read_campaign_metadata(base, campaign_id)
    assert campaign is not None
    assert campaign["source_file_status"]["execution_state"] == EXECUTION_STATE_PROCESSING
    return campaign


def _age_claim_past_stale_ttl(base: Path, campaign_id: str) -> None:
    campaign = read_campaign_metadata(base, campaign_id)
    assert campaign is not None
    campaign["source_file_status"]["last_progress_at"] = PAST_PROGRESS
    write_campaign_metadata(base, campaign_id, campaign)


# ---------------------------------------------------------------------------
# Evidence map (task 1.3) — interruption → durable markers → re-entry
# A claim-only | B image PNG | C blog handoff | D schedule | E LinkedIn URN/uncertain
# ---------------------------------------------------------------------------


def test_no_startup_auto_clear_of_non_stale_processing_claim(editorial_base: Path):
    """Process start must not clear non-stale processing claims (1.1 / Decision 2)."""
    _write_queue_ready(editorial_base)
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=QUEUE_READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    claimed = _claim_then_interrupt(editorial_base)
    attempt_id = claimed["source_file_status"]["execution_attempt_id"]

    # create_app has no lifespan reclaim hook; constructing the app is the
    # process-boundary stand-in for worker restart.
    create_app_source = inspect.getsource(create_app)
    assert "detect_stale_flow_a_execution" not in create_app_source
    assert "claim_flow_a_execution" not in create_app_source
    assert "clear_stale_execution_claim" not in create_app_source
    create_app(make_settings(editorial_base))

    after = read_campaign_metadata(editorial_base, QUEUE_CAMPAIGN_ID)
    assert after is not None
    status = after["source_file_status"]
    assert status["execution_state"] == EXECUTION_STATE_PROCESSING
    assert status["execution_attempt_id"] == attempt_id

    blocked = claim_flow_a_execution(editorial_base, campaign_id=QUEUE_CAMPAIGN_ID)
    assert blocked.status == "failed"
    assert FLOW_A_EXECUTION_ALREADY_CLAIMED in blocked.errors
    assert blocked.already_claimed is True
    assert blocked.recovery_classification == RECOVERY_MANUAL_INTERVENTION_REQUIRED


def test_claim_only_interruption_pre_ttl_blocked_and_resume_blocked(
    editorial_base: Path,
):
    _write_queue_ready(editorial_base)
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=QUEUE_READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    first = _claim_then_interrupt(editorial_base)
    attempt_id = first["source_file_status"]["execution_attempt_id"]

    duplicate = claim_flow_a_execution(editorial_base, campaign_id=QUEUE_CAMPAIGN_ID)
    assert duplicate.status == "failed"
    assert FLOW_A_EXECUTION_ALREADY_CLAIMED in duplicate.errors
    assert duplicate.recovery_classification == RECOVERY_MANUAL_INTERVENTION_REQUIRED
    payload = str(duplicate.to_dict())
    assert ACCESS_TOKEN not in payload
    assert QUEUE_MARKDOWN not in payload

    blocked_resume = resume_incomplete_campaign_recovery(
        editorial_base, campaign_id=QUEUE_CAMPAIGN_ID
    )
    assert blocked_resume.outcome == "blocked"
    assert blocked_resume.reason_code == REASON_ACTIVE_CLAIM
    assert (
        blocked_resume.recovery_classification
        == RECOVERY_MANUAL_INTERVENTION_REQUIRED
    )

    campaign = read_campaign_metadata(editorial_base, QUEUE_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["source_file_status"]["execution_attempt_id"] == attempt_id
    assert campaign["state"] != STATE_BLOG_PUBLISHED
    assert not campaign.get("linkedin_post_urn")
    assert campaign.get("linkedin_distribution") in (None, {})


def test_claim_only_interruption_post_ttl_reclaim_does_not_invent_success(
    editorial_base: Path,
):
    _write_queue_ready(editorial_base)
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=QUEUE_READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    first = claim_flow_a_execution(editorial_base, campaign_id=QUEUE_CAMPAIGN_ID)
    assert first.status == "completed"
    _age_claim_past_stale_ttl(editorial_base, QUEUE_CAMPAIGN_ID)

    with patch.dict("os.environ", {"SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS": STALE_SECONDS}):
        stale = detect_stale_flow_a_execution(
            editorial_base, campaign_id=QUEUE_CAMPAIGN_ID
        )
    assert stale.status == "completed"
    assert stale.execution_state == EXECUTION_STATE_STALE
    assert stale.recovery_classification == RECOVERY_RETRYABLE

    reclaimed = claim_flow_a_execution(editorial_base, campaign_id=QUEUE_CAMPAIGN_ID)
    assert reclaimed.status == "completed"
    assert reclaimed.reclaimed_from_stale is True
    assert reclaimed.execution_attempt_id != first.execution_attempt_id

    campaign = read_campaign_metadata(editorial_base, QUEUE_CAMPAIGN_ID)
    assert campaign is not None
    # Claim-only interrupt: reclaim must not invent publish/schedule/URN success.
    blog_publish = campaign.get("blog_publish") or {}
    assert blog_publish.get("status") != "already_published"
    assert blog_publish.get("status") != "published"
    assert not blog_publish.get("published_at")
    assert campaign.get("linkedin_distribution") in (None, {})
    assert campaign["state"] not in {
        STATE_BLOG_PUBLISHED,
        STATE_DISTRIBUTION_SCHEDULED,
    }


def test_image_interruption_reuses_public_png_after_reclaim(
    editorial_base: Path, public_repo: Path
):
    _write_post(editorial_base, with_png=False)
    public_png = public_repo / "assets" / "images" / f"{PUBLIC_SLUG}.png"
    public_png.write_bytes(b"\x89PNG\r\n\x1a\nrestart-reuse")

    _write_queue_ready(editorial_base)
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=QUEUE_READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    claim_flow_a_execution(editorial_base, campaign_id=QUEUE_CAMPAIGN_ID)
    _age_claim_past_stale_ttl(editorial_base, QUEUE_CAMPAIGN_ID)
    with patch.dict("os.environ", {"SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS": STALE_SECONDS}):
        detect_stale_flow_a_execution(editorial_base, campaign_id=QUEUE_CAMPAIGN_ID)
    reclaimed = claim_flow_a_execution(editorial_base, campaign_id=QUEUE_CAMPAIGN_ID)
    assert reclaimed.reclaimed_from_stale is True

    fake = FakeComfyUIClient()
    result = ensure_blog_image(
        editorial_base,
        SOURCE_RELATIVE,
        config=_enabled_comfy_config(),
        client=fake,
        github_pages_repo_path=public_repo,
        environ={
            "SILVERMAN_GITHUB_PAGES_REPO_PATH": str(public_repo),
            "SILVERMAN_SITE_URL": SITE_URL,
        },
    )
    assert result.status == "skipped"
    assert result.skip_reason == SKIP_REASON_PUBLIC_ASSET_REUSE
    assert fake.calls == []
    assert public_png.read_bytes() == b"\x89PNG\r\n\x1a\nrestart-reuse"


def test_blog_interruption_already_published_and_unproven_target_fail_closed(
    editorial_base: Path, public_repo: Path
):
    content = _write_post(editorial_base).read_text(encoding="utf-8")
    _validated_publish_campaign(editorial_base, content)

    first = publish_blog_post(
        editorial_base,
        SOURCE_RELATIVE,
        site_url=SITE_URL,
        github_pages_repo_path=public_repo,
        environ={
            "SILVERMAN_GITHUB_PAGES_REPO_PATH": str(public_repo),
            "SILVERMAN_SITE_URL": SITE_URL,
            "SILVERMAN_COMFYUI_ENABLED": "false",
        },
    )
    assert first.status == "completed"
    post_path = public_repo / "_posts" / f"{PUBLICATION_DATE}-{PUBLIC_SLUG}.md"
    mtime = post_path.stat().st_mtime
    first_key = (first.blog_publish or {}).get("idempotency_key")

    # Simulate reclaim after interrupt with matching blog evidence present.
    _write_queue_ready(editorial_base)
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=QUEUE_READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    claim_flow_a_execution(editorial_base, campaign_id=QUEUE_CAMPAIGN_ID)
    queue_campaign = read_campaign_metadata(editorial_base, QUEUE_CAMPAIGN_ID)
    assert queue_campaign is not None
    queue_campaign["source_file_status"]["execution_state"] = EXECUTION_STATE_STALE
    queue_campaign["source_file_status"]["recovery_classification"] = RECOVERY_RETRYABLE
    write_campaign_metadata(editorial_base, QUEUE_CAMPAIGN_ID, queue_campaign)
    reclaimed = claim_flow_a_execution(editorial_base, campaign_id=QUEUE_CAMPAIGN_ID)
    assert reclaimed.reclaimed_from_stale is True

    second = publish_blog_post(
        editorial_base,
        SOURCE_RELATIVE,
        site_url=SITE_URL,
        github_pages_repo_path=public_repo,
        environ={
            "SILVERMAN_GITHUB_PAGES_REPO_PATH": str(public_repo),
            "SILVERMAN_SITE_URL": SITE_URL,
            "SILVERMAN_COMFYUI_ENABLED": "false",
        },
    )
    assert second.status == "completed"
    assert second.blog_publish["status"] == "already_published"
    assert post_path.stat().st_mtime == mtime
    stored = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert stored is not None
    assert stored["state"] == STATE_BLOG_PUBLISHED
    assert stored.get("blog_publish", {}).get("idempotency_key") == first_key

    # Separate unproven-target fixture: public targets exist without matching proof.
    collision_base = editorial_base
    collision_repo = public_repo
    collision_content = _write_post(collision_base).read_text(encoding="utf-8")
    # Reset campaign to validated without matching blog_publish proof, with
    # foreign public targets already present (US-033 target_exists pattern).
    campaign = build_initial_campaign_metadata(
        flow=FLOW_A,
        source_slug=SOURCE_SLUG,
        public_slug=PUBLIC_SLUG,
        source_relative_path=SOURCE_RELATIVE,
        image_relative_path=IMAGE_RELATIVE,
        source_content=collision_content,
        publication_date=PUBLICATION_DATE,
    )
    transition_state(
        campaign, STATE_VALIDATED, reason="validated collision", actor=ACTOR_WORKER
    )
    write_campaign_metadata(collision_base, CANONICAL_CAMPAIGN_ID, campaign)
    image_path = collision_repo / "assets" / "images" / f"{PUBLIC_SLUG}.png"
    post_path.write_text("foreign post body\n", encoding="utf-8")
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nforeign")

    collision = publish_blog_post(
        collision_base,
        SOURCE_RELATIVE,
        site_url=SITE_URL,
        github_pages_repo_path=collision_repo,
        environ={
            "SILVERMAN_GITHUB_PAGES_REPO_PATH": str(collision_repo),
            "SILVERMAN_SITE_URL": SITE_URL,
            "SILVERMAN_COMFYUI_ENABLED": "false",
        },
    )
    assert collision.status == "failed"
    assert BLOG_PUBLISH_TARGET_EXISTS in collision.errors
    assert post_path.read_text(encoding="utf-8") == "foreign post body\n"
    assert image_path.read_bytes() == b"\x89PNG\r\n\x1a\nforeign"


def test_schedule_interruption_at_most_one_set_and_mismatch(
    editorial_base: Path,
):
    _derivatives_generated_campaign(editorial_base)
    first = schedule_linkedin_distribution(
        editorial_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        start_at_utc=ANCHOR_UTC,
    )
    assert first.status == "completed"
    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    schedule_key = campaign["linkedin_distribution"]["idempotency_key"]
    anchors = {
        entry["variant"]: entry["scheduled_at_utc"] for entry in campaign["variants"]
    }
    history_before = _distribution_scheduled_history_count(campaign)

    # Mid-flight interrupt stand-in on a separate queue claim, then reclaim.
    _write_queue_ready(editorial_base)
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=QUEUE_READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    claim_flow_a_execution(editorial_base, campaign_id=QUEUE_CAMPAIGN_ID)
    queue_campaign = read_campaign_metadata(editorial_base, QUEUE_CAMPAIGN_ID)
    assert queue_campaign is not None
    queue_campaign["source_file_status"]["execution_state"] = EXECUTION_STATE_STALE
    queue_campaign["source_file_status"]["recovery_classification"] = RECOVERY_RETRYABLE
    write_campaign_metadata(editorial_base, QUEUE_CAMPAIGN_ID, queue_campaign)
    reclaimed = claim_flow_a_execution(editorial_base, campaign_id=QUEUE_CAMPAIGN_ID)
    assert reclaimed.reclaimed_from_stale is True

    again = schedule_linkedin_distribution(
        editorial_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        start_at_utc=ANCHOR_UTC,
    )
    assert again.status == "completed"
    assert again.metadata_written is False

    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["linkedin_distribution"]["idempotency_key"] == schedule_key
    assert campaign["linkedin_distribution"]["anchor_utc"] == ANCHOR_UTC
    assert _distribution_scheduled_history_count(campaign) == history_before
    assert {
        entry["variant"]: entry["scheduled_at_utc"] for entry in campaign["variants"]
    } == anchors

    mismatch = schedule_linkedin_distribution(
        editorial_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        start_at_utc="2026-07-14T14:00:00Z",
    )
    assert mismatch.status == "failed"
    assert LINKEDIN_SCHEDULE_METADATA_MISMATCH in mismatch.errors


def test_linkedin_urn_survives_restart_reclaim_already_published(
    editorial_base: Path,
):
    _distribution_scheduled_campaign(editorial_base)
    _queue_variant(editorial_base)
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.headers = {"x-restli-id": "urn:li:share:restart-urn"}
    mock_client.post.return_value = mock_response

    first = publish_linkedin_due_variants(
        editorial_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        publish_now=True,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 13, 0, 0, tzinfo=timezone.utc),
    )
    assert first.status == "completed"
    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    urn = entry["linkedin_post_urn"]
    published_at = entry["published_at"]

    _write_queue_ready(editorial_base)
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=QUEUE_READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    claim_flow_a_execution(editorial_base, campaign_id=QUEUE_CAMPAIGN_ID)
    queue_campaign = read_campaign_metadata(editorial_base, QUEUE_CAMPAIGN_ID)
    assert queue_campaign is not None
    queue_campaign["source_file_status"]["execution_state"] = EXECUTION_STATE_STALE
    queue_campaign["source_file_status"]["recovery_classification"] = RECOVERY_RETRYABLE
    write_campaign_metadata(editorial_base, QUEUE_CAMPAIGN_ID, queue_campaign)
    reclaimed = claim_flow_a_execution(editorial_base, campaign_id=QUEUE_CAMPAIGN_ID)
    assert reclaimed.reclaimed_from_stale is True

    second = publish_linkedin_due_variants(
        editorial_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        publish_now=True,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 14, 0, 0, tzinfo=timezone.utc),
    )
    assert second.status == "completed"
    assert second.results[0].warnings == ["linkedin_publish_already_published"]
    mock_client.post.assert_called_once()
    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["linkedin_post_urn"] == urn
    assert entry["published_at"] == published_at
    assert entry["publish_state"] == PUBLISH_STATE_PUBLISHED


def test_linkedin_mid_api_without_urn_stays_bl008_uncertain_no_flow_a_auto_publish(
    editorial_base: Path,
):
    """Mid-API crash without durable URN → BL-008 uncertain; no Flow A auto-republish."""
    _distribution_scheduled_campaign(editorial_base)
    _queue_variant(editorial_base)

    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    working = deepcopy(campaign)
    failed_at = "2026-07-07T13:05:00Z"
    for entry in working["variants"]:
        if entry.get("variant") == TARGET_VARIANT:
            content_hash = entry["derivative_content_sha256"]
            entry["publish_state"] = PUBLISH_STATE_FAILED
            entry.pop("linkedin_post_urn", None)
            entry.pop("published_at", None)
            entry["linkedin_publication"] = {
                "last_error_code": LINKEDIN_PUBLISH_API_ERROR,
                "last_failed_at": failed_at,
                "retryable": True,
                "http_status": None,
            }
            entry["linkedin_publication_attempts"] = [
                {
                    "attempt_number": 1,
                    "attempted_at": failed_at,
                    "outcome": "failed",
                    "derivative_content_sha256": content_hash,
                    "last_error_code": LINKEDIN_PUBLISH_API_ERROR,
                    "last_failed_at": failed_at,
                    "retryable": True,
                    "http_status": None,
                }
            ]
    write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, working)

    assert (
        classify_linkedin_recovery(LINKEDIN_PUBLISH_API_ERROR, None)
        == RECOVERY_CLASS_UNCERTAIN
    )

    # Flow A reclaim must not call LinkedIn publish as a success path.
    _write_queue_ready(editorial_base)
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=QUEUE_READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    claim_flow_a_execution(editorial_base, campaign_id=QUEUE_CAMPAIGN_ID)
    _age_claim_past_stale_ttl(editorial_base, QUEUE_CAMPAIGN_ID)
    with patch.dict("os.environ", {"SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS": STALE_SECONDS}):
        detect_stale_flow_a_execution(editorial_base, campaign_id=QUEUE_CAMPAIGN_ID)
    reclaimed = claim_flow_a_execution(editorial_base, campaign_id=QUEUE_CAMPAIGN_ID)
    assert reclaimed.reclaimed_from_stale is True

    with patch(
        "silverman_blog_linkedin.linkedin_publication_flow.create_member_text_post"
    ) as create_post:
        # Incomplete-campaign resume never imports LinkedIn publish; reclaim alone
        # also must not invoke it.
        resume = resume_incomplete_campaign_recovery(
            editorial_base,
            campaign_id=QUEUE_CAMPAIGN_ID,
            dry_run=True,
        )
        assert resume.outcome in {"ok", "blocked", "noop"}
        create_post.assert_not_called()

    # Blind re-queue of uncertain class stays BL-008 confirmation-gated.
    blind = queue_linkedin_publication(
        editorial_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        now=datetime(2026, 7, 7, 14, 0, 0, tzinfo=timezone.utc),
    )
    assert blind.status == "failed"
    assert LINKEDIN_PUBLISH_RECOVERY_CONFIRMATION_REQUIRED in blind.errors
    assert blind.metadata_written is False
    assert ACCESS_TOKEN not in str(blind.to_dict())

    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_FAILED
    assert not entry.get("linkedin_post_urn")


def test_concurrent_retrigger_immediately_after_restart_loses_to_non_stale_claim(
    editorial_base: Path,
):
    ready = editorial_base / "blog-posts" / "ready"
    ready.mkdir(parents=True, exist_ok=True)
    (ready / "post.md").write_text("# Sample\n", encoding="utf-8")
    connector_campaign = "flow-a-2026-07-06-restart-retrigger"
    connector_ready = "blog-posts/ready/post.md"

    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=connector_ready,
        calendar_item={
            "campaign_id": connector_campaign,
            "due_at_utc": "2026-07-01T14:00:00Z",
        },
    )
    holder = claim_flow_a_execution(editorial_base, campaign_id=connector_campaign)
    assert holder.status == "completed"
    # Process-boundary stand-in: claim remains processing (no auto-clear).
    create_app(make_settings(editorial_base))

    (ready / "post.md").write_text("# Sample\n", encoding="utf-8")
    from tests.conftest import write_and_seed_calendar

    write_and_seed_calendar(
        editorial_base,
        {
            "schema_version": "1",
            "updated_at_utc": "2026-07-09T20:00:00Z",
            "items": [
                {
                    "item_id": "due-flow-a",
                    "title": "Flow A sample",
                    "status": "scheduled",
                    "due_at_utc": "2026-07-01T14:00:00Z",
                    "source_folder": "blog-posts/ready",
                    "source_relative_path": connector_ready,
                    "flow_type": "flow_a_ready_blog_post",
                    "content_mode": "user_provided_approved_blog",
                    "target_audience": "executive-recruiter",
                    "topic_theme": "architecture",
                    "campaign_id": connector_campaign,
                }
            ],
        },
    )

    barrier = threading.Barrier(2)
    results: list = []
    lock = threading.Lock()

    # Patch once in the parent thread. Concurrent patch()/unpatch() of the same
    # targets from two threads can leave MagicMock installed on the modules and
    # contaminate later tests in the full suite.
    with (
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post"
        ) as publish_mock,
        patch(
            "silverman_blog_linkedin.blog_image_generation.ComfyUIHttpClient"
        ) as comfy_cls,
    ):

        def _retrigger() -> None:
            barrier.wait()
            outcome = execute_due_editorial_calendar_flow_a(
                editorial_base,
                now_utc="2026-07-09T20:00:00Z",
                dry_run=False,
            )
            publish_mock.assert_not_called()
            comfy_cls.assert_not_called()
            with lock:
                results.append(outcome)

        threads = [threading.Thread(target=_retrigger) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    assert len(results) == 2
    for outcome in results:
        assert outcome.items
        item = outcome.items[0]
        assert item.execution_status == EXECUTION_STATUS_FAILED
        assert FLOW_A_EXECUTION_ALREADY_CLAIMED in item.errors

    campaign = read_campaign_metadata(editorial_base, connector_campaign)
    assert campaign is not None
    assert (
        campaign["source_file_status"]["execution_state"] == EXECUTION_STATE_PROCESSING
    )
    assert (
        campaign["source_file_status"]["execution_attempt_id"]
        == holder.execution_attempt_id
    )


def test_us035_regression_pointers_to_prior_suites():
    """US-035 coexists with US-033 / US-034 / BL-012 / BL-008 modules."""
    import tests.test_flow_a_concurrency_us033 as us033
    import tests.test_flow_a_concurrency_us034 as us034
    import silverman_blog_linkedin.flow_a_incomplete_campaign_recovery as bl012
    import silverman_blog_linkedin.linkedin_publication_flow as bl008

    assert hasattr(us033, "test_overlapping_claims_one_winner_one_already_claimed")
    assert hasattr(us034, "test_reclaim_from_stale_operator_visible_and_non_stale_blocked")
    assert hasattr(bl012, "resume_incomplete_campaign_recovery")
    assert bl012.REASON_ACTIVE_CLAIM == "flow_a_recovery_active_non_stale_claim"
    assert hasattr(bl008, "classify_linkedin_recovery")
    assert hasattr(bl008, "queue_linkedin_publication")
    assert PUBLISH_STATE_QUEUED == "queued"
    assert PUBLISH_STATE_PENDING == "pending"
