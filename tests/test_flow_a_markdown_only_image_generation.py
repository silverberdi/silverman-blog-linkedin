"""Integration tests for Markdown-only Flow A image generation path."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from silverman_blog_linkedin.blog_image_generation import (
    BLOG_IMAGE_GENERATION_BACKFILL_FAILED,
    BLOG_IMAGE_GENERATION_FRONTMATTER_UPDATE_FAILED,
    BLOG_IMAGE_GENERATION_WRITE_FAILED,
    handoff_public_blog_image,
)
from silverman_blog_linkedin.blog_publish_flow import (
    BLOG_PUBLISH_CONTENT_HASH_CHANGED,
    BLOG_PUBLISH_HASH_RECONCILIATION_FAILED,
    BLOG_PUBLISH_VALIDATION_FAILED,
    build_blog_publish_idempotency_key,
    publish_blog_post,
    reconcile_authorized_source_hash,
)
from silverman_blog_linkedin.campaign_lifecycle import (
    CampaignMetadataWriteResult,
    EXECUTION_STATE_IDLE,
    EXECUTION_STATE_PROCESSING,
    FLOW_A,
    METADATA_CAMPAIGNS_RELATIVE,
    RECOVERY_REPAIR_REQUIRED,
    RECOVERY_REQUEUE_REQUIRED,
    RECOVERY_RETRYABLE,
    SOURCE_LOCATION_ERROR,
    SOURCE_LOCATION_PROCESSED,
    SOURCE_LOCATION_QUEUED,
    STATE_BLOG_PUBLISHED,
    STATE_DISTRIBUTION_SCHEDULED,
    STATE_FLOW_A_COMPLETE,
    STATE_VALIDATED,
    build_initial_campaign_metadata,
    compute_source_content_sha256,
    read_campaign_metadata,
    transition_state,
    write_campaign_metadata,
)
from silverman_blog_linkedin.comfyui_client import (
    BLOG_IMAGE_GENERATION_TIMEOUT,
    FakeComfyUIClient,
)
from silverman_blog_linkedin.editorial_calendar_flow_a_execute import (
    EXECUTION_STATUS_EXECUTED,
    EXECUTION_STATUS_FAILED,
    FAILED_STEP_PUBLISH_BLOG,
    SOURCE_LIFECYCLE_COMPLETED,
    execute_due_editorial_calendar_flow_a,
)
from silverman_blog_linkedin.flow_a_operational_queue import (
    CAMPAIGN_METADATA_WRITE_FAILED,
    QUEUE_ACCEPTANCE_COMPLETED,
    accept_flow_a_source_for_queue,
    release_flow_a_execution,
)
from silverman_blog_linkedin.flow_a_source_lifecycle import complete_flow_a_source_lifecycle
from silverman_blog_linkedin.github_pages_publish import BLOG_IMAGE_PUBLIC_ASSET_HANDOFF_FAILED
from silverman_blog_linkedin.linkedin_distribution_schedule import (
    LinkedInDistributionScheduleResult,
    schedule_linkedin_distribution,
)
from silverman_blog_linkedin.linkedin_package_flow import (
    LinkedInPackageResult,
    generate_linkedin_package,
)
from silverman_blog_linkedin.ready_post_validation import (
    FRONTMATTER_INVALID_IMAGE,
    READY_POST_IMAGE_MISSING,
    validate_ready_post,
    validate_ready_post_pre_generation,
)
from tests.conftest import create_full_layout
from tests.test_linkedin_package_generation import _mock_generator_factory

SOURCE_SLUG = "01-flow-a-markdown-only"
PUBLIC_SLUG = "flow-a-markdown-only"
PUBLICATION_DATE = "2026-07-06"
READY_MD = f"blog-posts/ready/{SOURCE_SLUG}.md"
QUEUED_MD = f"blog-posts/queued/{SOURCE_SLUG}.md"
QUEUED_PNG = f"blog-posts/queued/{SOURCE_SLUG}.png"
PROCESSED_MD = f"blog-posts/processed/{SOURCE_SLUG}.md"
PROCESSED_PNG = f"blog-posts/processed/{SOURCE_SLUG}.png"
CAMPAIGN_ID = f"flow-a-{PUBLICATION_DATE}-{PUBLIC_SLUG}"
SITE_URL = "https://silverman.pro"
TITLE = "Flow A Markdown Only"
PAST_UTC = "2026-07-01T14:00:00Z"
NOW_UTC = "2026-07-09T20:00:00Z"


def _frontmatter(*, image: str | None = None) -> str:
    lines = [
        "---",
        f"title: {TITLE}",
        "audience: architects",
        "type: blog-post",
        "language: en",
        "layout: post",
        f"date: {PUBLICATION_DATE}",
        "categories:",
        "  - architecture",
        "tags:",
        "  - flow-a",
        "description: Markdown-only Flow A integration coverage.",
    ]
    if image is not None:
        lines.append(f"image: {image}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def _body() -> str:
    return f"# {TITLE}\n\nCanonical Markdown-only body for Flow A.\n"


def _write_ready(
    base: Path,
    *,
    image: str | None = None,
    with_png: bool = False,
    body: str | None = None,
) -> None:
    ready = base / "blog-posts" / "ready"
    ready.mkdir(parents=True, exist_ok=True)
    (ready / f"{SOURCE_SLUG}.md").write_text(
        _frontmatter(image=image) + (body or _body()),
        encoding="utf-8",
    )
    if with_png:
        (ready / f"{SOURCE_SLUG}.png").write_bytes(b"\x89PNG\r\n\x1a\nqueued")


def _setup_public_repo(repo: Path) -> None:
    (repo / "_posts").mkdir(parents=True)
    (repo / "assets/images").mkdir(parents=True)


def _write_calendar(base: Path, *, item_id: str = "markdown-only-flow-a") -> None:
    calendar_dir = base / "editorial-calendar"
    calendar_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1",
        "updated_at_utc": NOW_UTC,
        "items": [
            {
                "item_id": item_id,
                "title": TITLE,
                "status": "scheduled",
                "due_at_utc": PAST_UTC,
                "source_folder": "blog-posts/ready",
                "source_relative_path": READY_MD,
                "flow_type": "flow_a_ready_blog_post",
                "content_mode": "user_provided_approved_blog",
                "target_audience": "executive-recruiter",
                "topic_theme": "architecture",
                "campaign_id": CAMPAIGN_ID,
                "public_slug": PUBLIC_SLUG,
                "site_url": SITE_URL,
                "publication_date": PUBLICATION_DATE,
            }
        ],
    }
    (calendar_dir / "calendar.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


def _connector_package(*args, **kwargs) -> LinkedInPackageResult:
    kwargs.setdefault(
        "generate_content",
        _mock_generator_factory(url=f"{SITE_URL}/2026/07/06/{PUBLIC_SLUG}/"),
    )
    kwargs.setdefault("environ", {"DEEPSEEK_API_KEY": "test-key"})
    return generate_linkedin_package(*args, **kwargs)


def _connector_schedule(*args, **kwargs) -> LinkedInDistributionScheduleResult:
    return schedule_linkedin_distribution(*args, **kwargs)


@pytest.fixture
def editorial_base(tmp_path: Path) -> Path:
    base = tmp_path / "editorial"
    create_full_layout(base)
    (base / METADATA_CAMPAIGNS_RELATIVE).mkdir(parents=True, exist_ok=True)
    return base


@pytest.fixture
def public_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "public-repo"
    _setup_public_repo(repo)
    return repo


@pytest.fixture
def connector_env(
    monkeypatch: pytest.MonkeyPatch, editorial_base: Path, public_repo: Path
) -> None:
    monkeypatch.setenv("SILVERMAN_BLOG_LINKEDIN_BASE_PATH", str(editorial_base))
    monkeypatch.setenv("SILVERMAN_GITHUB_PAGES_REPO_PATH", str(public_repo))
    monkeypatch.setenv("SILVERMAN_SITE_URL", SITE_URL)
    monkeypatch.setenv("SILVERMAN_COMFYUI_IMAGE_ENABLED", "true")
    monkeypatch.setenv("SILVERMAN_COMFYUI_BASE_URL", "http://127.0.0.1:8188")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")


def _comfy_env(base: Path, repo: Path) -> dict[str, str]:
    return {
        "SILVERMAN_BLOG_LINKEDIN_BASE_PATH": str(base),
        "SILVERMAN_GITHUB_PAGES_REPO_PATH": str(repo),
        "SILVERMAN_SITE_URL": SITE_URL,
        "SILVERMAN_COMFYUI_IMAGE_ENABLED": "true",
        "SILVERMAN_COMFYUI_BASE_URL": "http://127.0.0.1:8188",
    }


def _queue_accept_markdown_only(base: Path) -> str:
    result = accept_flow_a_source_for_queue(
        base,
        source_relative_path=READY_MD,
        calendar_item={"campaign_id": CAMPAIGN_ID, "publication_date": PUBLICATION_DATE},
    )
    assert result.queue_acceptance_status == QUEUE_ACCEPTANCE_COMPLETED
    assert result.queued_source_relative_path == QUEUED_MD
    assert not (base / READY_MD).exists()
    return result.queued_source_relative_path or QUEUED_MD


def _fake_comfyui_boundary(fake: FakeComfyUIClient):
    return patch(
        "silverman_blog_linkedin.blog_image_generation.ComfyUIHttpClient",
        return_value=fake,
    )


def test_pre_generation_allows_missing_image_and_png_when_generation_enabled(
    editorial_base: Path, public_repo: Path
):
    _write_ready(editorial_base, image=None, with_png=False)
    queued = _queue_accept_markdown_only(editorial_base)
    pre = validate_ready_post_pre_generation(
        editorial_base,
        queued,
        site_url=SITE_URL,
        environ=_comfy_env(editorial_base, public_repo),
    )
    assert pre.ok is True
    assert READY_POST_IMAGE_MISSING not in pre.errors


def test_full_validation_requires_png_after_remediation(editorial_base: Path):
    _write_ready(editorial_base, image=None, with_png=False)
    queued = _queue_accept_markdown_only(editorial_base)
    full = validate_ready_post(editorial_base, queued, site_url=SITE_URL)
    assert full.ok is False
    assert READY_POST_IMAGE_MISSING in full.errors


def test_non_canonical_image_blocks_pre_generation(editorial_base: Path, public_repo: Path):
    _write_ready(editorial_base, image="/assets/images/wrong.png", with_png=False)
    queued = _queue_accept_markdown_only(editorial_base)
    pre = validate_ready_post_pre_generation(
        editorial_base,
        queued,
        site_url=SITE_URL,
        environ=_comfy_env(editorial_base, public_repo),
    )
    assert pre.ok is False
    assert FRONTMATTER_INVALID_IMAGE in pre.errors


def test_connector_markdown_only_happy_path_end_to_end(
    editorial_base: Path,
    public_repo: Path,
    connector_env: None,
):
    _write_ready(editorial_base, image=None, with_png=False)
    _write_calendar(editorial_base)
    fake = FakeComfyUIClient()

    with (
        _fake_comfyui_boundary(fake),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.generate_linkedin_package",
            side_effect=_connector_package,
        ) as package_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.schedule_linkedin_distribution",
            side_effect=_connector_schedule,
        ) as schedule_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    item = result.items[0]
    assert item.execution_status == EXECUTION_STATUS_EXECUTED
    assert item.source_lifecycle_status == SOURCE_LIFECYCLE_COMPLETED
    assert item.queue_acceptance_status == QUEUE_ACCEPTANCE_COMPLETED
    assert item.failed_step is None

    assert fake.calls and len(fake.calls) == 1
    assert (editorial_base / QUEUED_PNG).is_file() is False
    assert (editorial_base / PROCESSED_MD).is_file()
    assert (editorial_base / PROCESSED_PNG).is_file()
    assert not (editorial_base / READY_MD).exists()
    assert not (editorial_base / QUEUED_MD).exists()
    assert (public_repo / "assets/images" / f"{PUBLIC_SLUG}.png").is_file()
    assert list((public_repo / "_posts").glob("*.md"))

    package_mock.assert_called_once()
    package_kwargs = package_mock.call_args.kwargs
    assert package_kwargs["campaign_id"] == CAMPAIGN_ID
    assert package_kwargs["site_url"] == SITE_URL

    schedule_mock.assert_called_once()
    schedule_kwargs = schedule_mock.call_args.kwargs
    assert schedule_kwargs["campaign_id"] == CAMPAIGN_ID

    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    status = campaign.get("source_file_status") or {}
    assert status.get("location") == SOURCE_LOCATION_PROCESSED
    assert status.get("execution_state") == EXECUTION_STATE_IDLE
    assert campaign.get("state") == STATE_FLOW_A_COMPLETE
    assert campaign.get("queued_source_relative_path") == QUEUED_MD
    assert campaign.get("processed_source_relative_path") == PROCESSED_MD
    assert campaign.get("processed_image_relative_path") == PROCESSED_PNG
    assert campaign.get("source_public_url")


def test_publish_layer_markdown_only_publish_and_lifecycle(
    editorial_base: Path, public_repo: Path,
):
    _write_ready(editorial_base, image=None, with_png=False)
    fake = FakeComfyUIClient()
    queue_path = _queue_accept_markdown_only(editorial_base)
    result = publish_blog_post(
        editorial_base,
        queue_path,
        site_url=SITE_URL,
        github_pages_repo_path=str(public_repo),
        environ=_comfy_env(editorial_base, public_repo),
        comfyui_client=fake,
    )

    assert result.status == "completed"
    assert fake.calls and len(fake.calls) == 1
    assert (editorial_base / QUEUED_PNG).is_file()
    assert (public_repo / "assets/images" / f"{PUBLIC_SLUG}.png").is_file()

    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    campaign["state"] = STATE_DISTRIBUTION_SCHEDULED
    write_campaign_metadata(editorial_base, CAMPAIGN_ID, campaign)

    lifecycle = complete_flow_a_source_lifecycle(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        source_relative_path=queue_path,
    )
    assert lifecycle.status == "completed"
    assert not (editorial_base / QUEUED_MD).exists()
    assert not (editorial_base / QUEUED_PNG).exists()
    campaign_after = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign_after is not None
    assert campaign_after.get("source_file_status", {}).get("location") == SOURCE_LOCATION_PROCESSED


def test_publish_layer_comfyui_transient_failure_does_not_release_claim(
    editorial_base: Path, public_repo: Path,
):
    """Publish-layer coverage only; connector release behavior is tested separately."""
    _write_ready(editorial_base, image=None, with_png=False)
    queued = _queue_accept_markdown_only(editorial_base)
    with patch(
        "silverman_blog_linkedin.editorial_calendar_flow_a_execute.release_flow_a_execution",
        wraps=release_flow_a_execution,
    ) as release_mock:
        result = publish_blog_post(
            editorial_base,
            queued,
            site_url=SITE_URL,
            github_pages_repo_path=str(public_repo),
            environ=_comfy_env(editorial_base, public_repo),
            comfyui_client=FakeComfyUIClient(error_code=BLOG_IMAGE_GENERATION_TIMEOUT),
        )
        release_mock.assert_not_called()

    assert result.status == "failed"
    assert BLOG_IMAGE_GENERATION_TIMEOUT in result.errors
    assert READY_POST_IMAGE_MISSING not in result.errors


def test_connector_comfyui_transient_failure_releases_claim_once(
    editorial_base: Path,
    public_repo: Path,
    connector_env: None,
):
    _write_ready(editorial_base, image=None, with_png=False)
    _write_calendar(editorial_base)
    fake = FakeComfyUIClient(error_code=BLOG_IMAGE_GENERATION_TIMEOUT)

    with (
        _fake_comfyui_boundary(fake),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.release_flow_a_execution",
            wraps=release_flow_a_execution,
        ) as release_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.generate_linkedin_package"
        ) as package_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.schedule_linkedin_distribution"
        ) as schedule_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.complete_flow_a_source_lifecycle"
        ) as lifecycle_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    assert release_mock.call_count == 1
    item = result.items[0]
    assert item.execution_status == EXECUTION_STATUS_FAILED
    assert item.failed_step == FAILED_STEP_PUBLISH_BLOG
    assert BLOG_IMAGE_GENERATION_TIMEOUT in item.errors
    assert READY_POST_IMAGE_MISSING not in item.errors

    package_mock.assert_not_called()
    schedule_mock.assert_not_called()
    lifecycle_mock.assert_not_called()
    assert not list((public_repo / "_posts").glob("*.md"))
    assert not list((public_repo / "assets/images").glob("*.png"))

    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    status = campaign.get("source_file_status") or {}
    assert status.get("location") == SOURCE_LOCATION_QUEUED
    assert status.get("execution_state") == EXECUTION_STATE_IDLE
    assert status.get("recovery_classification") == RECOVERY_RETRYABLE
    last_error = status.get("last_error") or {}
    assert last_error.get("category") == "image_generation"
    assert last_error.get("error_code") == BLOG_IMAGE_GENERATION_TIMEOUT


def test_publish_layer_handoff_failure_blocks_publish_and_preserves_png(
    editorial_base: Path, public_repo: Path,
):
    _write_ready(editorial_base, image=None, with_png=False)
    queued = _queue_accept_markdown_only(editorial_base)
    fake = FakeComfyUIClient()

    def _fail_handoff(*args, **kwargs):
        from silverman_blog_linkedin.blog_image_generation import BlogImageGenerationResult

        return BlogImageGenerationResult(
            status="failed",
            source_relative_path=queued,
            error_code=BLOG_IMAGE_PUBLIC_ASSET_HANDOFF_FAILED,
            public_asset_handoff_status="failed",
        )

    with patch(
        "silverman_blog_linkedin.blog_publish_flow.handoff_public_blog_image",
        side_effect=_fail_handoff,
    ):
        blocked = publish_blog_post(
            editorial_base,
            queued,
            site_url=SITE_URL,
            github_pages_repo_path=str(public_repo),
            environ=_comfy_env(editorial_base, public_repo),
            comfyui_client=fake,
        )

    assert blocked.status == "failed"
    assert BLOG_IMAGE_PUBLIC_ASSET_HANDOFF_FAILED in blocked.errors
    assert (editorial_base / QUEUED_PNG).is_file()
    assert not list((public_repo / "_posts").glob("*.md"))


def test_connector_handoff_failure_releases_claim_once(
    editorial_base: Path,
    public_repo: Path,
    connector_env: None,
):
    _write_ready(editorial_base, image=None, with_png=False)
    _write_calendar(editorial_base)
    fake = FakeComfyUIClient()

    def _fail_handoff(*args, **kwargs):
        from silverman_blog_linkedin.blog_image_generation import BlogImageGenerationResult

        return BlogImageGenerationResult(
            status="failed",
            source_relative_path=QUEUED_MD,
            error_code=BLOG_IMAGE_PUBLIC_ASSET_HANDOFF_FAILED,
            public_asset_handoff_status="failed",
        )

    with (
        _fake_comfyui_boundary(fake),
        patch(
            "silverman_blog_linkedin.blog_publish_flow.handoff_public_blog_image",
            side_effect=_fail_handoff,
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.release_flow_a_execution",
            wraps=release_flow_a_execution,
        ) as release_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.generate_linkedin_package"
        ) as package_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.schedule_linkedin_distribution"
        ) as schedule_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.complete_flow_a_source_lifecycle"
        ) as lifecycle_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    assert release_mock.call_count == 1
    item = result.items[0]
    assert item.execution_status == EXECUTION_STATUS_FAILED
    assert item.failed_step == FAILED_STEP_PUBLISH_BLOG
    assert BLOG_IMAGE_PUBLIC_ASSET_HANDOFF_FAILED in item.errors

    package_mock.assert_not_called()
    schedule_mock.assert_not_called()
    lifecycle_mock.assert_not_called()
    assert (editorial_base / QUEUED_PNG).is_file()
    assert not list((public_repo / "_posts").glob("*.md"))

    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    status = campaign.get("source_file_status") or {}
    assert status.get("location") == SOURCE_LOCATION_QUEUED
    assert status.get("execution_state") == EXECUTION_STATE_IDLE
    assert status.get("recovery_classification") == RECOVERY_REPAIR_REQUIRED
    last_error = status.get("last_error") or {}
    assert last_error.get("category") == "public_asset_handoff"
    assert last_error.get("error_code") == BLOG_IMAGE_PUBLIC_ASSET_HANDOFF_FAILED


def test_connector_deterministic_validation_error_move_no_release(
    editorial_base: Path,
    public_repo: Path,
    connector_env: None,
):
    _write_ready(editorial_base, image="/assets/images/wrong.png", with_png=False)
    _write_calendar(editorial_base)

    with (
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.release_flow_a_execution",
            wraps=release_flow_a_execution,
        ) as release_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.generate_linkedin_package"
        ) as package_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.schedule_linkedin_distribution"
        ) as schedule_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.complete_flow_a_source_lifecycle"
        ) as lifecycle_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    assert release_mock.call_count == 0
    item = result.items[0]
    assert item.execution_status == EXECUTION_STATUS_FAILED
    assert item.failed_step == FAILED_STEP_PUBLISH_BLOG
    assert FRONTMATTER_INVALID_IMAGE in item.errors

    package_mock.assert_not_called()
    schedule_mock.assert_not_called()
    lifecycle_mock.assert_not_called()

    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    status = campaign.get("source_file_status") or {}
    assert status.get("location") == SOURCE_LOCATION_ERROR
    assert status.get("execution_state") == EXECUTION_STATE_IDLE
    assert status.get("recovery_classification") == RECOVERY_REQUEUE_REQUIRED
    last_error = status.get("last_error") or {}
    assert last_error.get("category") == "editorial_validation"


def test_connector_deterministic_validation_error_move_failure_releases_once(
    editorial_base: Path,
    public_repo: Path,
    connector_env: None,
):
    _write_ready(editorial_base, image="/assets/images/wrong.png", with_png=False)
    _write_calendar(editorial_base)
    real_write = write_campaign_metadata
    error_move_attempts = {"count": 0}

    def _write_side_effect(base_path, campaign_id, campaign):
        if campaign.get("source_file_status", {}).get("marked_error_at"):
            error_move_attempts["count"] += 1
            return CampaignMetadataWriteResult(
                written=False,
                error_code=CAMPAIGN_METADATA_WRITE_FAILED,
            )
        return real_write(base_path, campaign_id, campaign)

    with (
        patch(
            "silverman_blog_linkedin.flow_a_operational_queue.write_campaign_metadata",
            side_effect=_write_side_effect,
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.release_flow_a_execution",
            wraps=release_flow_a_execution,
        ) as release_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    assert error_move_attempts["count"] >= 1
    assert release_mock.call_count == 1
    item = result.items[0]
    assert item.execution_status == EXECUTION_STATUS_FAILED
    assert CAMPAIGN_METADATA_WRITE_FAILED in item.errors

    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    status = campaign.get("source_file_status") or {}
    assert status.get("location") == SOURCE_LOCATION_QUEUED
    assert status.get("execution_state") == EXECUTION_STATE_IDLE
    assert status.get("recovery_classification") == RECOVERY_REPAIR_REQUIRED


def test_connector_local_editorial_image_repair_failure_releases_once(
    editorial_base: Path,
    public_repo: Path,
    connector_env: None,
):
    _write_ready(editorial_base, image=None, with_png=False)
    _write_calendar(editorial_base)
    fake = FakeComfyUIClient()

    with (
        _fake_comfyui_boundary(fake),
        patch(
            "silverman_blog_linkedin.blog_image_generation._patch_frontmatter_image",
            side_effect=OSError("frontmatter patch failed"),
        ),
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.release_flow_a_execution",
            wraps=release_flow_a_execution,
        ) as release_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.generate_linkedin_package"
        ) as package_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.schedule_linkedin_distribution"
        ) as schedule_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.complete_flow_a_source_lifecycle"
        ) as lifecycle_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    assert release_mock.call_count == 1
    item = result.items[0]
    assert item.execution_status == EXECUTION_STATUS_FAILED
    assert BLOG_IMAGE_GENERATION_FRONTMATTER_UPDATE_FAILED in item.errors

    package_mock.assert_not_called()
    schedule_mock.assert_not_called()
    lifecycle_mock.assert_not_called()
    assert not list((public_repo / "_posts").glob("*.md"))

    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    status = campaign.get("source_file_status") or {}
    assert status.get("location") == SOURCE_LOCATION_QUEUED
    assert status.get("execution_state") == EXECUTION_STATE_IDLE
    assert status.get("recovery_classification") == RECOVERY_REPAIR_REQUIRED
    last_error = status.get("last_error") or {}
    assert last_error.get("category") == "editorial_image_repair"
    assert last_error.get("error_code") == BLOG_IMAGE_GENERATION_FRONTMATTER_UPDATE_FAILED


def test_connector_hash_reconciliation_failure_releases_once(
    editorial_base: Path,
    public_repo: Path,
    connector_env: None,
):
    _write_ready(editorial_base, image=None, with_png=False)
    _write_calendar(editorial_base)
    fake = FakeComfyUIClient()

    with (
        _fake_comfyui_boundary(fake),
        patch(
            "silverman_blog_linkedin.blog_publish_flow.reconcile_authorized_source_hash",
            return_value=(
                False,
                "updated-hash",
                "updated-key",
                CAMPAIGN_METADATA_WRITE_FAILED,
            ),
        ) as reconcile_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.release_flow_a_execution",
            wraps=release_flow_a_execution,
        ) as release_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.generate_linkedin_package"
        ) as package_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.schedule_linkedin_distribution"
        ) as schedule_mock,
        patch(
            "silverman_blog_linkedin.editorial_calendar_flow_a_execute.complete_flow_a_source_lifecycle"
        ) as lifecycle_mock,
    ):
        result = execute_due_editorial_calendar_flow_a(
            editorial_base,
            now_utc=NOW_UTC,
            dry_run=False,
        )

    reconcile_mock.assert_called_once()
    assert release_mock.call_count == 1
    item = result.items[0]
    assert item.execution_status == EXECUTION_STATUS_FAILED
    assert BLOG_PUBLISH_HASH_RECONCILIATION_FAILED in item.errors
    assert CAMPAIGN_METADATA_WRITE_FAILED in item.errors

    package_mock.assert_not_called()
    schedule_mock.assert_not_called()
    lifecycle_mock.assert_not_called()
    assert not list((public_repo / "_posts").glob("*.md"))
    assert not list((public_repo / "assets/images").glob("*.png"))

    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    status = campaign.get("source_file_status") or {}
    assert status.get("location") == SOURCE_LOCATION_QUEUED
    assert status.get("execution_state") == EXECUTION_STATE_IDLE
    assert status.get("recovery_classification") == RECOVERY_REPAIR_REQUIRED
    last_error = status.get("last_error") or {}
    assert last_error.get("category") == "source_hash_reconciliation"
    assert last_error.get("error_code") == BLOG_PUBLISH_HASH_RECONCILIATION_FAILED


def test_public_asset_reuse_backfills_without_comfyui(
    editorial_base: Path, public_repo: Path,
):
    _write_ready(
        editorial_base,
        image=f"/assets/images/{PUBLIC_SLUG}.png",
        with_png=False,
    )
    queued = _queue_accept_markdown_only(editorial_base)
    (public_repo / "assets/images" / f"{PUBLIC_SLUG}.png").write_bytes(
        b"\x89PNG\r\n\x1a\npublic"
    )
    fake = FakeComfyUIClient()
    result = publish_blog_post(
        editorial_base,
        queued,
        site_url=SITE_URL,
        github_pages_repo_path=str(public_repo),
        environ=_comfy_env(editorial_base, public_repo),
        comfyui_client=fake,
    )
    assert fake.calls == []
    assert result.status == "completed"
    assert (editorial_base / QUEUED_PNG).is_file()
    assert (editorial_base / QUEUED_PNG).read_bytes() == (
        public_repo / "assets/images" / f"{PUBLIC_SLUG}.png"
    ).read_bytes()


def test_authorized_hash_reconciliation_retains_campaign_id(
    editorial_base: Path, public_repo: Path,
):
    _write_ready(editorial_base, image=None, with_png=False)
    queued = _queue_accept_markdown_only(editorial_base)
    before = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert before is not None
    intake_hash = before.get("source_content_sha256")

    result = publish_blog_post(
        editorial_base,
        queued,
        site_url=SITE_URL,
        github_pages_repo_path=str(public_repo),
        environ=_comfy_env(editorial_base, public_repo),
        comfyui_client=FakeComfyUIClient(),
    )
    assert result.status == "completed"
    after = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert after is not None
    assert after["campaign_id"] == CAMPAIGN_ID
    assert after.get("intake_source_content_sha256") == intake_hash
    assert after.get("source_content_sha256") != intake_hash
    expected_key = build_blog_publish_idempotency_key(
        source_slug=SOURCE_SLUG,
        public_slug=PUBLIC_SLUG,
        publication_date=PUBLICATION_DATE,
        source_content_sha256=after["source_content_sha256"],
    )
    assert after.get("blog_publish", {}).get("idempotency_key") == expected_key


def test_unrelated_body_mutation_blocked(editorial_base: Path, public_repo: Path):
    _write_ready(editorial_base, image=None, with_png=False)
    queued = _queue_accept_markdown_only(editorial_base)
    queued_path = editorial_base / queued
    queued_path.write_text(
        queued_path.read_text(encoding="utf-8") + "\nUnauthorized body edit.\n",
        encoding="utf-8",
    )
    result = publish_blog_post(
        editorial_base,
        queued,
        site_url=SITE_URL,
        github_pages_repo_path=str(public_repo),
        environ=_comfy_env(editorial_base, public_repo),
        comfyui_client=FakeComfyUIClient(),
    )
    assert result.status == "failed"
    assert BLOG_PUBLISH_CONTENT_HASH_CHANGED in result.errors or (
        BLOG_PUBLISH_VALIDATION_FAILED in result.errors
    )


def test_full_validation_failure_writes_no_public_asset(
    editorial_base: Path, public_repo: Path,
):
    from silverman_blog_linkedin.ready_post_validation import ReadyPostValidationResult

    _write_ready(editorial_base, image=None, with_png=False)
    queued = _queue_accept_markdown_only(editorial_base)

    def _forced_full_failure(*_args, **_kwargs):
        return ReadyPostValidationResult(
            ok=False,
            source_relative_path=queued,
            errors=[READY_POST_IMAGE_MISSING],
        )

    with patch(
        "silverman_blog_linkedin.blog_publish_flow.validate_ready_post",
        side_effect=_forced_full_failure,
    ):
        result = publish_blog_post(
            editorial_base,
            queued,
            site_url=SITE_URL,
            github_pages_repo_path=str(public_repo),
            environ=_comfy_env(editorial_base, public_repo),
            comfyui_client=FakeComfyUIClient(),
        )
    assert result.status == "failed"
    assert not list((public_repo / "assets/images").glob("*.png"))


def test_existing_queued_png_skips_comfyui(editorial_base: Path, public_repo: Path):
    _write_ready(
        editorial_base,
        image=f"/assets/images/{PUBLIC_SLUG}.png",
        with_png=True,
    )
    queued = _queue_accept_markdown_only(editorial_base)
    fake = FakeComfyUIClient()
    result = publish_blog_post(
        editorial_base,
        queued,
        site_url=SITE_URL,
        github_pages_repo_path=str(public_repo),
        environ=_comfy_env(editorial_base, public_repo),
        comfyui_client=fake,
    )
    assert fake.calls == []
    assert result.status == "completed"
