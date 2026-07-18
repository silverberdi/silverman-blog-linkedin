"""US-034 concurrency: schedule, LinkedIn once-only publish, stale detect + reclaim."""

from __future__ import annotations

import hashlib
import threading
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from silverman_blog_linkedin.campaign_lifecycle import (
    ACTOR_WORKER,
    CANONICAL_VARIANT_IDS,
    EXECUTION_STATE_PROCESSING,
    EXECUTION_STATE_STALE,
    FLOW_A,
    METADATA_CAMPAIGNS_RELATIVE,
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
from silverman_blog_linkedin.flow_a_operational_queue import (
    FLOW_A_EXECUTION_ALREADY_CLAIMED,
    accept_flow_a_source_for_queue,
    claim_flow_a_execution,
    detect_stale_flow_a_execution,
)
from silverman_blog_linkedin.linkedin_client import LinkedInPostResult
from silverman_blog_linkedin.linkedin_distribution_schedule import (
    LINKEDIN_SCHEDULE_METADATA_MISMATCH,
    schedule_linkedin_distribution,
)
from silverman_blog_linkedin.linkedin_package_flow import (
    GENERATED_RELATIVE,
    build_package_idempotency_key,
)
from silverman_blog_linkedin.linkedin_publication_flow import (
    PUBLISH_STATE_PENDING,
    PUBLISH_STATE_PUBLISHED,
    PUBLISH_STATE_QUEUED,
    publish_linkedin_due_variants,
    queue_linkedin_publication,
)
from silverman_blog_linkedin.linkedin_token_provider import TokenResolutionResult
from tests.conftest import create_full_layout

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

QUEUE_SOURCE_SLUG = "02-example-post"
QUEUE_PUBLIC_SLUG = "example-post"
QUEUE_READY_RELATIVE = f"blog-posts/ready/{QUEUE_SOURCE_SLUG}.md"
QUEUE_CAMPAIGN_ID = f"flow-a-{PUBLICATION_DATE}-{QUEUE_PUBLIC_SLUG}"
QUEUE_MARKDOWN = "# Example\n\nBody content.\n"


@pytest.fixture
def editorial_base(tmp_path: Path) -> Path:
    base = tmp_path / "editorial"
    create_full_layout(base)
    return base


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


def _calendar_item(campaign_id: str = QUEUE_CAMPAIGN_ID) -> dict:
    return {"campaign_id": campaign_id, "due_at_utc": "2026-07-06T14:00:00Z"}


def _write_queue_ready(base: Path) -> None:
    ready = base / "blog-posts" / "ready"
    ready.mkdir(parents=True, exist_ok=True)
    (ready / f"{QUEUE_SOURCE_SLUG}.md").write_text(QUEUE_MARKDOWN, encoding="utf-8")


def _distribution_scheduled_history_count(campaign: dict) -> int:
    return sum(
        1
        for entry in campaign.get("state_history") or []
        if isinstance(entry, dict) and entry.get("to_state") == STATE_DISTRIBUTION_SCHEDULED
    )


def test_overlapping_first_time_schedule_one_durable_write(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)
    barrier = threading.Barrier(2)
    results: list = []
    lock = threading.Lock()

    def _schedule() -> None:
        barrier.wait()
        outcome = schedule_linkedin_distribution(
            editorial_base,
            campaign_id=CANONICAL_CAMPAIGN_ID,
            start_at_utc=ANCHOR_UTC,
        )
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=_schedule) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(results) == 2
    assert all(r.status == "completed" for r in results)
    winners = [r for r in results if r.metadata_written]
    losers = [r for r in results if not r.metadata_written]
    assert len(winners) == 1
    assert len(losers) == 1

    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["state"] == STATE_DISTRIBUTION_SCHEDULED
    assert _distribution_scheduled_history_count(campaign) == 1
    assert campaign["linkedin_distribution"]["anchor_utc"] == ANCHOR_UTC
    assert campaign["linkedin_distribution"]["idempotency_key"] == winners[0].distribution[
        "idempotency_key"
    ]
    for entry in campaign["variants"]:
        assert entry["scheduled_at_utc"]
        assert entry["publish_state"] == PUBLISH_STATE_PENDING


def test_schedule_cas_loser_matching_peer_is_idempotent(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)
    first = schedule_linkedin_distribution(
        editorial_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        start_at_utc=ANCHOR_UTC,
    )
    assert first.status == "completed"
    assert first.metadata_written is True
    scheduled_before = {
        entry["variant"]: entry["scheduled_at_utc"]
        for entry in (read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID) or {})[
            "variants"
        ]
    }
    history_before = _distribution_scheduled_history_count(
        read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID) or {}
    )

    second = schedule_linkedin_distribution(
        editorial_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        start_at_utc=ANCHOR_UTC,
    )
    assert second.status == "completed"
    assert second.metadata_written is False
    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    assert _distribution_scheduled_history_count(campaign) == history_before
    scheduled_after = {
        entry["variant"]: entry["scheduled_at_utc"] for entry in campaign["variants"]
    }
    assert scheduled_after == scheduled_before


def test_schedule_mismatch_fails_closed(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)
    first = schedule_linkedin_distribution(
        editorial_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        start_at_utc=ANCHOR_UTC,
    )
    assert first.status == "completed"
    mismatch = schedule_linkedin_distribution(
        editorial_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        start_at_utc="2026-07-14T14:00:00Z",
    )
    assert mismatch.status == "failed"
    assert LINKEDIN_SCHEDULE_METADATA_MISMATCH in mismatch.errors
    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["linkedin_distribution"]["anchor_utc"] == ANCHOR_UTC


def test_pre_api_evidence_recheck_skips_linkedin_call(editorial_base: Path):
    _distribution_scheduled_campaign(editorial_base)
    _queue_variant(editorial_base)
    peer_urn = "urn:li:share:peer-pre-api"
    peer_published_at = "2026-07-07T12:30:00Z"
    api_called = {"value": False}

    def _token_then_peer_evidence(*_args, **_kwargs):
        campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
        assert campaign is not None
        working = deepcopy(campaign)
        for entry in working["variants"]:
            if entry.get("variant") == TARGET_VARIANT:
                entry["publish_state"] = PUBLISH_STATE_PUBLISHED
                entry["linkedin_post_urn"] = peer_urn
                entry["published_at"] = peer_published_at
        write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, working)
        return TokenResolutionResult(
            status="ok",
            access_token=ACCESS_TOKEN,
            member_urn=MEMBER_URN,
        )

    def _create_should_not_run(*_args, **_kwargs):
        api_called["value"] = True
        raise AssertionError("LinkedIn API must not be called after peer URN evidence")

    with (
        patch(
            "silverman_blog_linkedin.linkedin_publication_flow.resolve_linkedin_access_token",
            side_effect=_token_then_peer_evidence,
        ),
        patch(
            "silverman_blog_linkedin.linkedin_publication_flow.create_member_text_post",
            side_effect=_create_should_not_run,
        ),
    ):
        result = publish_linkedin_due_variants(
            editorial_base,
            campaign_id=CANONICAL_CAMPAIGN_ID,
            variant=TARGET_VARIANT,
            dry_run=False,
            publish_now=True,
            environ=_real_publish_env(),
            now=datetime(2026, 7, 7, 13, 0, 0, tzinfo=timezone.utc),
        )

    assert api_called["value"] is False
    assert result.status == "completed"
    assert result.results[0].warnings == ["linkedin_publish_already_published"]
    assert result.results[0].linkedin_post_urn == peer_urn
    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["linkedin_post_urn"] == peer_urn
    assert entry["published_at"] == peer_published_at


def test_concurrent_first_publish_retains_single_urn(editorial_base: Path):
    _distribution_scheduled_campaign(editorial_base)
    _queue_variant(editorial_base)
    barrier = threading.Barrier(2)
    call_counter = {"n": 0}
    counter_lock = threading.Lock()
    results: list = []
    results_lock = threading.Lock()

    def _create_post(*_args, **_kwargs):
        with counter_lock:
            call_counter["n"] += 1
            urn = f"urn:li:share:race-{call_counter['n']}"
        barrier.wait()
        return LinkedInPostResult(
            post_urn=urn,
            http_status=201,
            error_code=None,
            retryable=False,
        )

    def _publish() -> None:
        outcome = publish_linkedin_due_variants(
            editorial_base,
            campaign_id=CANONICAL_CAMPAIGN_ID,
            variant=TARGET_VARIANT,
            dry_run=False,
            publish_now=True,
            environ=_real_publish_env(),
            now=datetime(2026, 7, 7, 13, 0, 0, tzinfo=timezone.utc),
        )
        with results_lock:
            results.append(outcome)

    with patch(
        "silverman_blog_linkedin.linkedin_publication_flow.create_member_text_post",
        side_effect=_create_post,
    ):
        threads = [threading.Thread(target=_publish) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    assert len(results) == 2
    assert all(r.status == "completed" for r in results)
    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["publish_state"] == PUBLISH_STATE_PUBLISHED
    retained_urn = entry["linkedin_post_urn"]
    assert isinstance(retained_urn, str) and retained_urn.startswith("urn:li:share:race-")
    assert entry["published_at"]

    urns_from_results = {r.results[0].linkedin_post_urn for r in results}
    assert retained_urn in urns_from_results
    already_published = [
        r for r in results if "linkedin_publish_already_published" in (r.results[0].warnings or [])
    ]
    fresh_publish = [
        r
        for r in results
        if "linkedin_publish_already_published" not in (r.results[0].warnings or [])
    ]
    assert len(fresh_publish) == 1
    assert len(already_published) == 1
    assert already_published[0].results[0].linkedin_post_urn == retained_urn


def test_publish_now_does_not_bypass_already_published(editorial_base: Path):
    _distribution_scheduled_campaign(editorial_base)
    _queue_variant(editorial_base)
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.headers = {"x-restli-id": "urn:li:share:first-publish"}
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


def test_stale_detect_completed_and_skipped_operator_visible(editorial_base: Path):
    _write_queue_ready(editorial_base)
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=QUEUE_READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    claim_flow_a_execution(editorial_base, campaign_id=QUEUE_CAMPAIGN_ID)

    skipped = detect_stale_flow_a_execution(
        editorial_base, campaign_id=QUEUE_CAMPAIGN_ID
    )
    assert skipped.status == "skipped"
    assert skipped.execution_state == EXECUTION_STATE_PROCESSING
    assert skipped.recovery_classification == RECOVERY_MANUAL_INTERVENTION_REQUIRED
    campaign = read_campaign_metadata(editorial_base, QUEUE_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["source_file_status"]["location"] == "queued"
    queued_relative = campaign["queued_source_relative_path"]
    assert isinstance(queued_relative, str)
    assert (editorial_base / queued_relative).is_file()

    past = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    campaign["source_file_status"]["last_progress_at"] = past
    write_campaign_metadata(editorial_base, QUEUE_CAMPAIGN_ID, campaign)

    with patch.dict("os.environ", {"SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS": "60"}):
        completed = detect_stale_flow_a_execution(
            editorial_base, campaign_id=QUEUE_CAMPAIGN_ID
        )
    assert completed.status == "completed"
    assert completed.execution_state == EXECUTION_STATE_STALE
    assert completed.recovery_classification == RECOVERY_RETRYABLE
    campaign = read_campaign_metadata(editorial_base, QUEUE_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["source_file_status"]["execution_state"] == EXECUTION_STATE_STALE
    assert campaign["source_file_status"]["location"] == "queued"
    assert (editorial_base / queued_relative).is_file()


def test_reclaim_from_stale_operator_visible_and_non_stale_blocked(
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

    blocked = claim_flow_a_execution(editorial_base, campaign_id=QUEUE_CAMPAIGN_ID)
    assert blocked.status == "failed"
    assert FLOW_A_EXECUTION_ALREADY_CLAIMED in blocked.errors
    assert blocked.already_claimed is True
    assert blocked.recovery_classification == RECOVERY_MANUAL_INTERVENTION_REQUIRED

    campaign = read_campaign_metadata(editorial_base, QUEUE_CAMPAIGN_ID)
    assert campaign is not None
    campaign["source_file_status"]["execution_state"] = EXECUTION_STATE_STALE
    campaign["source_file_status"]["recovery_classification"] = RECOVERY_RETRYABLE
    write_campaign_metadata(editorial_base, QUEUE_CAMPAIGN_ID, campaign)

    reclaimed = claim_flow_a_execution(editorial_base, campaign_id=QUEUE_CAMPAIGN_ID)
    assert reclaimed.status == "completed"
    assert reclaimed.reclaimed_from_stale is True
    assert reclaimed.execution_state == EXECUTION_STATE_PROCESSING
    assert reclaimed.attempt_count == (first.attempt_count or 0) + 1
    assert reclaimed.execution_attempt_id != first.execution_attempt_id


def test_reclaim_does_not_duplicate_schedule_or_linkedin_evidence(editorial_base: Path):
    """After reclaim, matching schedule/LinkedIn evidence stays once-only."""
    _write_queue_ready(editorial_base)
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=QUEUE_READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    first = claim_flow_a_execution(editorial_base, campaign_id=QUEUE_CAMPAIGN_ID)
    assert first.status == "completed"

    _distribution_scheduled_campaign(editorial_base)
    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    schedule_key = campaign["linkedin_distribution"]["idempotency_key"]
    anchor = campaign["linkedin_distribution"]["anchor_utc"]
    history_count = _distribution_scheduled_history_count(campaign)

    queue_campaign = read_campaign_metadata(editorial_base, QUEUE_CAMPAIGN_ID)
    assert queue_campaign is not None
    queue_campaign["source_file_status"]["execution_state"] = EXECUTION_STATE_STALE
    queue_campaign["source_file_status"]["recovery_classification"] = RECOVERY_RETRYABLE
    write_campaign_metadata(editorial_base, QUEUE_CAMPAIGN_ID, queue_campaign)

    reclaimed = claim_flow_a_execution(editorial_base, campaign_id=QUEUE_CAMPAIGN_ID)
    assert reclaimed.status == "completed"
    assert reclaimed.reclaimed_from_stale is True

    schedule_again = schedule_linkedin_distribution(
        editorial_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        start_at_utc=ANCHOR_UTC,
    )
    assert schedule_again.status == "completed"
    assert schedule_again.metadata_written is False

    _queue_variant(editorial_base)
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.headers = {"x-restli-id": "urn:li:share:reclaim-safe"}
    mock_client.post.return_value = mock_response
    published = publish_linkedin_due_variants(
        editorial_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        publish_now=True,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 13, 0, 0, tzinfo=timezone.utc),
    )
    assert published.status == "completed"
    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    urn = entry["linkedin_post_urn"]
    published_at = entry["published_at"]

    publish_again = publish_linkedin_due_variants(
        editorial_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        publish_now=True,
        environ=_real_publish_env(),
        http_client=mock_client,
        now=datetime(2026, 7, 7, 14, 0, 0, tzinfo=timezone.utc),
    )
    assert publish_again.results[0].warnings == ["linkedin_publish_already_published"]
    mock_client.post.assert_called_once()

    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["linkedin_distribution"]["idempotency_key"] == schedule_key
    assert campaign["linkedin_distribution"]["anchor_utc"] == anchor
    assert _distribution_scheduled_history_count(campaign) == history_count
    entry = next(v for v in campaign["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["linkedin_post_urn"] == urn
    assert entry["published_at"] == published_at


def test_us034_regression_pointers_to_prior_suites():
    """US-034 regression suite coexists with US-033 / schedule / LinkedIn modules."""
    import tests.test_flow_a_concurrency_us033 as us033
    import tests.test_linkedin_distribution_scheduling as schedule_tests
    import tests.test_linkedin_publication as publish_tests

    assert hasattr(us033, "test_overlapping_claims_one_winner_one_already_claimed")
    assert hasattr(
        schedule_tests, "test_idempotent_rerun_does_not_rewrite_schedules_or_duplicate_state_history"
    )
    assert hasattr(
        publish_tests, "test_auto_queue_repeat_is_once_only_and_does_not_requeue"
    )
    assert METADATA_CAMPAIGNS_RELATIVE == "metadata/campaigns"
