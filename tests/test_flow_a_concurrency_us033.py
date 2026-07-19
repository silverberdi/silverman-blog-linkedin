"""US-033 concurrency and duplicate-execution protection (post / image / blog)."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from silverman_blog_linkedin.blog_image_generation import (
    SKIP_REASON_PUBLIC_ASSET_REUSE,
    ensure_blog_image,
    ensure_editorial_blog_image,
)
from silverman_blog_linkedin.blog_publish_flow import (
    BLOG_PUBLISH_TARGET_EXISTS,
    publish_blog_post,
)
from silverman_blog_linkedin.campaign_lifecycle import (
    CAMPAIGN_METADATA_CONCURRENT_UPDATE,
    EXECUTION_STATE_PROCESSING,
    RECOVERY_MANUAL_INTERVENTION_REQUIRED,
    STATE_BLOG_PUBLISHED,
    STATE_VALIDATED,
    build_initial_campaign_metadata,
    campaign_metadata_content_fingerprint,
    read_campaign_metadata,
    transition_state,
    write_campaign_metadata,
    write_campaign_metadata_cas,
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
from silverman_blog_linkedin.flow_a_operational_queue import (
    FLOW_A_EXECUTION_ALREADY_CLAIMED,
    QUEUE_ACCEPTANCE_SKIPPED_ALREADY_QUEUED,
    accept_flow_a_source_for_queue,
    claim_flow_a_execution,
)
from silverman_blog_linkedin import linkedin_publication_flow as linkedin_publication_flow_mod
from tests.conftest import create_full_layout

SOURCE_SLUG = "02-example-post"
PUBLIC_SLUG = "example-post"
PUBLICATION_DATE = "2026-07-06"
READY_RELATIVE = f"blog-posts/ready/{SOURCE_SLUG}.md"
CAMPAIGN_ID = f"flow-a-{PUBLICATION_DATE}-{PUBLIC_SLUG}"
SOURCE_MARKDOWN = "# Example\n\nBody content.\n"
SITE_URL = "https://silverman.pro"
NOW_UTC = "2026-07-09T20:00:00Z"
PAST_UTC = "2026-07-01T14:00:00Z"

PUBLISH_SOURCE_SLUG = "01-why-i-did-not-start-with-the-database"
PUBLISH_PUBLIC_SLUG = "why-i-did-not-start-with-the-database"
PUBLISH_RELATIVE = f"blog-posts/ready/{PUBLISH_SOURCE_SLUG}.md"
PUBLISH_IMAGE = f"blog-posts/ready/{PUBLISH_SOURCE_SLUG}.png"
PUBLISH_CAMPAIGN_ID = f"flow-a-{PUBLICATION_DATE}-{PUBLISH_PUBLIC_SLUG}"
TITLE = "Why I Did Not Start With the Database"
CONNECTOR_CAMPAIGN_ID = "flow-a-2026-07-06-different-slug"
CONNECTOR_READY = "blog-posts/ready/post.md"


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


def _calendar_item(campaign_id: str = CAMPAIGN_ID) -> dict:
    return {"campaign_id": campaign_id, "due_at_utc": "2026-07-06T14:00:00Z"}


def _write_ready(base: Path, *, with_image: bool = False) -> None:
    ready = base / "blog-posts" / "ready"
    ready.mkdir(parents=True, exist_ok=True)
    (ready / f"{SOURCE_SLUG}.md").write_text(SOURCE_MARKDOWN, encoding="utf-8")
    if with_image:
        (ready / f"{SOURCE_SLUG}.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")


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


def _publish_frontmatter() -> str:
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
        f"image: /assets/images/{PUBLISH_PUBLIC_SLUG}.png\n"
        "---\n"
    )


def _publish_body() -> str:
    return (
        f"# {TITLE}\n\n"
        "The real problem is not persistence. The real problem is naming the business too late.\n"
    )


def _write_publish_post(base: Path, *, with_png: bool = True) -> str:
    ready = base / "blog-posts" / "ready"
    ready.mkdir(parents=True, exist_ok=True)
    content = _publish_frontmatter() + _publish_body()
    (ready / f"{PUBLISH_SOURCE_SLUG}.md").write_text(content, encoding="utf-8")
    if with_png:
        (ready / f"{PUBLISH_SOURCE_SLUG}.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    return content


def _validated_publish_campaign(base: Path, content: str) -> dict:
    campaign = build_initial_campaign_metadata(
        flow="flow_a",
        source_slug=PUBLISH_SOURCE_SLUG,
        public_slug=PUBLISH_PUBLIC_SLUG,
        source_relative_path=PUBLISH_RELATIVE,
        image_relative_path=PUBLISH_IMAGE,
        source_content=content,
        publication_date=PUBLICATION_DATE,
    )
    transition_state(
        campaign,
        STATE_VALIDATED,
        reason="validated for US-033 tests",
        actor="worker",
    )
    write_campaign_metadata(base, PUBLISH_CAMPAIGN_ID, campaign)
    return campaign


def _write_connector_calendar(base: Path, *, campaign_id: str) -> None:
    from tests.conftest import write_and_seed_calendar

    write_and_seed_calendar(
        base,
        {
            "schema_version": "1",
            "updated_at_utc": NOW_UTC,
            "items": [
                {
                    "item_id": "due-flow-a",
                    "title": "Flow A sample",
                    "status": "scheduled",
                    "due_at_utc": PAST_UTC,
                    "source_folder": "blog-posts/ready",
                    "source_relative_path": CONNECTOR_READY,
                    "flow_type": "flow_a_ready_blog_post",
                    "content_mode": "user_provided_approved_blog",
                    "target_audience": "executive-recruiter",
                    "topic_theme": "architecture",
                    "campaign_id": campaign_id,
                }
            ],
        },
    )


def test_campaign_metadata_fingerprint_and_cas_conflict(editorial_base: Path):
    _write_ready(editorial_base)
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    fp = campaign_metadata_content_fingerprint(editorial_base, CAMPAIGN_ID)
    assert fp is not None

    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    campaign["updated_at"] = "2099-01-01T00:00:00Z"
    write_campaign_metadata(editorial_base, CAMPAIGN_ID, campaign)

    stale_payload = dict(campaign)
    stale_payload["updated_at"] = "2000-01-01T00:00:00Z"
    cas = write_campaign_metadata_cas(
        editorial_base,
        CAMPAIGN_ID,
        stale_payload,
        expected_fingerprint=fp,
    )
    assert cas.written is False
    assert cas.error_code == CAMPAIGN_METADATA_CONCURRENT_UPDATE


def test_overlapping_claims_one_winner_one_already_claimed(editorial_base: Path):
    _write_ready(editorial_base)
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(),
    )

    barrier = threading.Barrier(2)
    results: list = []
    lock = threading.Lock()

    def _claim() -> None:
        barrier.wait()
        result = claim_flow_a_execution(editorial_base, campaign_id=CAMPAIGN_ID)
        with lock:
            results.append(result)

    threads = [threading.Thread(target=_claim) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    winners = [r for r in results if r.status == "completed"]
    losers = [r for r in results if r.status == "failed"]
    assert len(winners) == 1
    assert len(losers) == 1
    assert FLOW_A_EXECUTION_ALREADY_CLAIMED in losers[0].errors
    assert losers[0].already_claimed is True
    assert losers[0].recovery_classification == RECOVERY_MANUAL_INTERVENTION_REQUIRED

    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    status = campaign["source_file_status"]
    assert status["execution_state"] == EXECUTION_STATE_PROCESSING
    assert status["execution_attempt_id"] == winners[0].execution_attempt_id


def test_sequential_duplicate_claim_still_rejects_with_manual_intervention(
    editorial_base: Path,
):
    _write_ready(editorial_base)
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    first = claim_flow_a_execution(editorial_base, campaign_id=CAMPAIGN_ID)
    assert first.status == "completed"
    second = claim_flow_a_execution(editorial_base, campaign_id=CAMPAIGN_ID)
    assert second.status == "failed"
    assert FLOW_A_EXECUTION_ALREADY_CLAIMED in second.errors
    assert second.already_claimed is True
    assert second.recovery_classification == RECOVERY_MANUAL_INTERVENTION_REQUIRED
    assert second.metadata_written is False


def test_same_identity_queue_accept_does_not_duplicate_campaign(editorial_base: Path):
    _write_ready(editorial_base)
    first = accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    second = accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    assert second.queue_acceptance_status == QUEUE_ACCEPTANCE_SKIPPED_ALREADY_QUEUED
    campaigns = list((editorial_base / "metadata" / "campaigns").glob("*.json"))
    assert len(campaigns) == 1
    assert first.campaign_id == second.campaign_id == CAMPAIGN_ID


def test_connector_claim_loser_does_not_publish_or_comfyui(editorial_base: Path):
    ready = editorial_base / "blog-posts" / "ready"
    ready.mkdir(parents=True, exist_ok=True)
    (ready / "post.md").write_text("# Sample\n", encoding="utf-8")

    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=CONNECTOR_READY,
        calendar_item={
            "campaign_id": CONNECTOR_CAMPAIGN_ID,
            "due_at_utc": PAST_UTC,
        },
    )
    holder = claim_flow_a_execution(
        editorial_base, campaign_id=CONNECTOR_CAMPAIGN_ID
    )
    assert holder.status == "completed"

    # Planner resolves due items from ready/; keep a copy after queue move.
    (ready / "post.md").write_text("# Sample\n", encoding="utf-8")
    _write_connector_calendar(editorial_base, campaign_id=CONNECTOR_CAMPAIGN_ID)

    with (
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.publish_blog_post"
        ) as publish_mock,
        patch(
            "silverman_blog_linkedin.blog_image_generation.ComfyUIHttpClient"
        ) as comfy_cls,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    publish_mock.assert_not_called()
    comfy_cls.assert_not_called()
    assert result.items
    item = result.items[0]
    assert item.execution_status == EXECUTION_STATUS_FAILED
    assert FLOW_A_EXECUTION_ALREADY_CLAIMED in item.errors


def test_pre_comfyui_recheck_skips_when_public_asset_appears(
    editorial_base: Path, public_repo: Path
):
    ready = editorial_base / "blog-posts" / "ready"
    ready.mkdir(parents=True, exist_ok=True)
    content = (
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
        "description: desc\n"
        f"image: /assets/images/{PUBLISH_PUBLIC_SLUG}.png\n"
        "---\n"
        f"# {TITLE}\n\nBody.\n"
    )
    (ready / f"{PUBLISH_SOURCE_SLUG}.md").write_text(content, encoding="utf-8")
    public_png = public_repo / "assets" / "images" / f"{PUBLISH_PUBLIC_SLUG}.png"
    assert not public_png.exists()

    import silverman_blog_linkedin.blog_image_generation as image_mod

    calls = {"n": 0}
    real_detection = image_mod._detection_outcome

    def _detection_then_plant(**kwargs):
        calls["n"] += 1
        outcome = real_detection(**kwargs)
        if calls["n"] == 1:
            public_png.write_bytes(b"\x89PNG\r\n\x1a\npeer-public")
        return outcome

    fake = FakeComfyUIClient()
    with patch.object(image_mod, "_detection_outcome", side_effect=_detection_then_plant):
        result = ensure_editorial_blog_image(
            editorial_base,
            PUBLISH_RELATIVE,
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
    assert public_png.read_bytes() == b"\x89PNG\r\n\x1a\npeer-public"


def test_repeated_publish_with_existing_public_asset_skips_comfyui(
    editorial_base: Path, public_repo: Path
):
    _write_publish_post(editorial_base, with_png=False)
    public_png = public_repo / "assets" / "images" / f"{PUBLISH_PUBLIC_SLUG}.png"
    public_png.write_bytes(b"\x89PNG\r\n\x1a\nexisting")
    fake = FakeComfyUIClient()

    result = ensure_blog_image(
        editorial_base,
        PUBLISH_RELATIVE,
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


def test_already_published_repeated_publish_no_rewrite(
    editorial_base: Path, public_repo: Path
):
    content = _write_publish_post(editorial_base)
    _validated_publish_campaign(editorial_base, content)

    first = publish_blog_post(
        editorial_base,
        PUBLISH_RELATIVE,
        site_url=SITE_URL,
        github_pages_repo_path=public_repo,
        environ={
            "SILVERMAN_GITHUB_PAGES_REPO_PATH": str(public_repo),
            "SILVERMAN_SITE_URL": SITE_URL,
            "SILVERMAN_COMFYUI_ENABLED": "false",
        },
    )
    assert first.status == "completed"
    post_path = public_repo / "_posts" / f"{PUBLICATION_DATE}-{PUBLISH_PUBLIC_SLUG}.md"
    mtime = post_path.stat().st_mtime
    first_key = (first.blog_publish or {}).get("idempotency_key")

    second = publish_blog_post(
        editorial_base,
        PUBLISH_RELATIVE,
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

    stored = read_campaign_metadata(editorial_base, PUBLISH_CAMPAIGN_ID)
    assert stored is not None
    assert stored["state"] == STATE_BLOG_PUBLISHED
    assert stored.get("blog_publish", {}).get("idempotency_key") == first_key


def test_unproven_target_collision_fails_closed(
    editorial_base: Path, public_repo: Path
):
    content = _write_publish_post(editorial_base)
    _validated_publish_campaign(editorial_base, content)
    post_path = public_repo / "_posts" / f"{PUBLICATION_DATE}-{PUBLISH_PUBLIC_SLUG}.md"
    image_path = public_repo / "assets" / "images" / f"{PUBLISH_PUBLIC_SLUG}.png"
    post_path.write_text("foreign post body\n", encoding="utf-8")
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nforeign")

    result = publish_blog_post(
        editorial_base,
        PUBLISH_RELATIVE,
        site_url=SITE_URL,
        github_pages_repo_path=public_repo,
        environ={
            "SILVERMAN_GITHUB_PAGES_REPO_PATH": str(public_repo),
            "SILVERMAN_SITE_URL": SITE_URL,
            "SILVERMAN_COMFYUI_ENABLED": "false",
        },
    )
    assert result.status == "failed"
    assert BLOG_PUBLISH_TARGET_EXISTS in result.errors
    assert post_path.read_text(encoding="utf-8") == "foreign post body\n"
    assert image_path.read_bytes() == b"\x89PNG\r\n\x1a\nforeign"


def test_concurrent_first_publish_single_artifact_set(
    editorial_base: Path, public_repo: Path
):
    content = _write_publish_post(editorial_base)
    _validated_publish_campaign(editorial_base, content)

    barrier = threading.Barrier(2)
    results: list = []
    lock = threading.Lock()

    def _publish() -> None:
        barrier.wait()
        outcome = publish_blog_post(
            editorial_base,
            PUBLISH_RELATIVE,
            site_url=SITE_URL,
            github_pages_repo_path=public_repo,
            environ={
                "SILVERMAN_GITHUB_PAGES_REPO_PATH": str(public_repo),
                "SILVERMAN_SITE_URL": SITE_URL,
                "SILVERMAN_COMFYUI_ENABLED": "false",
            },
        )
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=_publish) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(results) == 2
    completed = [r for r in results if r.status == "completed"]
    assert len(completed) >= 1

    for result in results:
        if result.status == "completed":
            assert result.blog_publish.get("status") in {
                "already_published",
                "published",
                "reconciled",
            }
        else:
            # Loser fails closed without inventing a second artifact set.
            # Codes may be target_exists or a handoff race under true overlap.
            assert result.status == "failed"
            assert result.errors

    posts = list((public_repo / "_posts").glob(f"*-{PUBLISH_PUBLIC_SLUG}.md"))
    images = list((public_repo / "assets" / "images").glob(f"{PUBLISH_PUBLIC_SLUG}.png"))
    assert len(posts) == 1
    assert len(images) == 1

    stored = read_campaign_metadata(editorial_base, PUBLISH_CAMPAIGN_ID)
    assert stored is not None
    if any(r.blog_publish.get("status") == "published" for r in completed):
        assert stored["state"] == STATE_BLOG_PUBLISHED


def test_linkedin_publication_module_untouched_by_us033_import_surface():
    """Regression smoke: LinkedIn publication module still importable (BL-008)."""
    assert linkedin_publication_flow_mod is not None
    assert hasattr(linkedin_publication_flow_mod, "publish_linkedin_due_variants") or hasattr(
        linkedin_publication_flow_mod, "queue_linkedin_publication"
    )


def test_secret_safe_already_claimed_result_fields(editorial_base: Path):
    _write_ready(editorial_base)
    accept_flow_a_source_for_queue(
        editorial_base,
        source_relative_path=READY_RELATIVE,
        calendar_item=_calendar_item(),
    )
    claim_flow_a_execution(editorial_base, campaign_id=CAMPAIGN_ID)
    duplicate = claim_flow_a_execution(editorial_base, campaign_id=CAMPAIGN_ID)
    payload = duplicate.to_dict()
    serialized = str(payload)
    assert "api_key" not in serialized
    assert SOURCE_MARKDOWN not in serialized
    assert FLOW_A_EXECUTION_ALREADY_CLAIMED in duplicate.errors
