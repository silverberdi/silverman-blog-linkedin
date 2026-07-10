"""Tests for Flow A blog publish orchestration and HTTP endpoint."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.blog_publish_flow import (
    BLOG_PUBLISH_CONTENT_HASH_CHANGED,
    BLOG_PUBLISH_INVALID_CAMPAIGN_STATE,
    BLOG_PUBLISH_METADATA_WRITE_FAILED,
    BLOG_PUBLISH_PUBLIC_REPO_NOT_CONFIGURED,
    BLOG_PUBLISH_TARGET_EXISTS,
    BLOG_PUBLISH_VALIDATION_FAILED,
    RECONCILIATION_SKIPPED_PUBLIC_CONTENT_MISMATCH,
    RECONCILIATION_SKIPPED_SOURCE_MISMATCH,
    RECONCILED_FROM_ERROR_WARNING,
    publish_blog_post,
)
from silverman_blog_linkedin.github_pages_publish import (
    BLOG_IMAGE_PUBLIC_ASSET_HANDOFF_FAILED,
    EDITORIAL_TZ,
    render_expected_public_post,
    run_publish,
)
from silverman_blog_linkedin.blog_image_generation import (
    BLOG_IMAGE_GENERATION_DISABLED,
    BLOG_IMAGE_GENERATION_FAILED,
    WARNING_READY_SIBLING_BACKFILL_FAILED,
)
from silverman_blog_linkedin.campaign_lifecycle import (
    ACTOR_WORKER,
    FLOW_A,
    FLOW_B,
    METADATA_CAMPAIGNS_RELATIVE,
    STATE_BLOG_PUBLISH_PENDING,
    STATE_BLOG_PUBLISHED,
    STATE_DERIVATIVES_PENDING,
    STATE_ERROR,
    STATE_READY,
    STATE_VALIDATED,
    STATE_VALIDATION_FAILED,
    build_blog_publish_idempotency_key,
    build_initial_campaign_metadata,
    compute_source_content_sha256,
    read_campaign_metadata,
    transition_state,
    write_campaign_metadata,
)
from silverman_blog_linkedin.comfyui_client import (
    BLOG_IMAGE_GENERATION_COMFYUI_FAILED,
    FakeComfyUIClient,
)
from silverman_blog_linkedin.main import create_app
from silverman_blog_linkedin.ready_post_validation import (
    CONTENT_CONTAINS_TODO,
    FRONTMATTER_REQUIRED_FIELD_MISSING,
    READY_POST_IMAGE_MISSING,
)
from tests.conftest import auth_header, create_full_layout, make_settings

SOURCE_SLUG = "01-why-i-did-not-start-with-the-database"
PUBLIC_SLUG = "why-i-did-not-start-with-the-database"
PUBLICATION_DATE = "2026-07-06"
SOURCE_RELATIVE = f"blog-posts/ready/{SOURCE_SLUG}.md"
IMAGE_RELATIVE = f"blog-posts/ready/{SOURCE_SLUG}.png"
CANONICAL_CAMPAIGN_ID = f"flow-a-{PUBLICATION_DATE}-{PUBLIC_SLUG}"
SITE_URL = "https://silverman.pro"
TITLE = "Why I Did Not Start With the Database"


def _canonical_frontmatter(*, include_image: bool = True) -> str:
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
        "  - databases",
        "description: A senior practitioner's take on starting with the domain.",
    ]
    if include_image:
        lines.append(f"image: /assets/images/{PUBLIC_SLUG}.png")
    lines.append("---")
    return "\n".join(lines) + "\n"


def _canonical_body(*, extra: str = "") -> str:
    return (
        f"# {TITLE}\n\n"
        "The real problem is not persistence. The real problem is naming the business too late.\n"
        f"{extra}"
    )


def _write_post(
    base: Path,
    *,
    slug: str = SOURCE_SLUG,
    body: str | None = None,
    frontmatter: str | None = None,
    with_png: bool = True,
) -> Path:
    ready = base / "blog-posts" / "ready"
    ready.mkdir(parents=True, exist_ok=True)
    md_path = ready / f"{slug}.md"
    fm = frontmatter if frontmatter is not None else _canonical_frontmatter()
    content = fm + (body if body is not None else _canonical_body())
    md_path.write_text(content, encoding="utf-8")
    if with_png:
        (ready / f"{slug}.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    return md_path


def _setup_metadata_campaigns(base: Path) -> Path:
    metadata_dir = base / METADATA_CAMPAIGNS_RELATIVE
    metadata_dir.mkdir(parents=True, exist_ok=True)
    return metadata_dir


def _setup_public_repo(repo_path: Path) -> None:
    (repo_path / "_posts").mkdir(parents=True)
    (repo_path / "assets/images").mkdir(parents=True)


def _publish_env(editorial_base: Path, repo_path: Path) -> dict[str, str]:
    return {
        "SILVERMAN_BLOG_LINKEDIN_BASE_PATH": str(editorial_base),
        "SILVERMAN_GITHUB_PAGES_REPO_PATH": str(repo_path),
        "SILVERMAN_SITE_URL": SITE_URL,
    }


def _comfy_enabled_env(editorial_base: Path, repo_path: Path) -> dict[str, str]:
    env = _publish_env(editorial_base, repo_path)
    env["SILVERMAN_COMFYUI_IMAGE_ENABLED"] = "true"
    env["SILVERMAN_COMFYUI_BASE_URL"] = "http://127.0.0.1:8188"
    return env


def _publish(
    editorial_base: Path,
    repo_path: Path,
    *,
    relative: str = SOURCE_RELATIVE,
    environ: dict[str, str] | None = None,
    comfyui_client=None,
    execution_time: datetime | None = None,
):
    return publish_blog_post(
        editorial_base,
        relative,
        site_url=SITE_URL,
        github_pages_repo_path=str(repo_path),
        environ=environ or _publish_env(editorial_base, repo_path),
        comfyui_client=comfyui_client,
        execution_time=execution_time,
    )


def _validated_campaign(editorial_base: Path) -> dict:
    content = (_write_post(editorial_base)).read_text(encoding="utf-8")
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
    write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, campaign)
    return campaign


def _error_campaign(
    editorial_base: Path,
    *,
    error_code: str = BLOG_PUBLISH_INVALID_CAMPAIGN_STATE,
    extra_errors: list[str] | None = None,
    source_relative_path: str = SOURCE_RELATIVE,
) -> dict:
    campaign = _validated_campaign(editorial_base)
    if source_relative_path != SOURCE_RELATIVE:
        campaign["source_relative_path"] = source_relative_path
        write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, campaign)
    transition_state(
        campaign,
        STATE_ERROR,
        reason="Prior publish attempt failed",
        actor=ACTOR_WORKER,
        error_code=error_code,
    )
    if extra_errors:
        campaign.setdefault("errors", []).extend(extra_errors)
        write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, campaign)
    return campaign


def _write_matching_public_artifacts(
    editorial_base: Path,
    public_repo: Path,
    *,
    post_body: str | None = None,
    image_bytes: bytes | None = None,
) -> tuple[Path, Path]:
    md_path = editorial_base / SOURCE_RELATIVE
    png_path = editorial_base / IMAGE_RELATIVE
    if post_body is None:
        post_body = render_expected_public_post(
            md_path,
            PUBLIC_SLUG,
            date.fromisoformat(PUBLICATION_DATE),
        )
    if image_bytes is None:
        image_bytes = png_path.read_bytes()

    post_path = public_repo / "_posts" / f"{PUBLICATION_DATE}-{PUBLIC_SLUG}.md"
    image_path = public_repo / "assets/images" / f"{PUBLIC_SLUG}.png"
    post_path.write_text(post_body, encoding="utf-8")
    image_path.write_bytes(image_bytes)
    return post_path, image_path


@pytest.fixture
def editorial_base(tmp_path: Path) -> Path:
    _setup_metadata_campaigns(tmp_path)
    return tmp_path


@pytest.fixture
def public_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "public-repo"
    _setup_public_repo(repo)
    return repo


def test_validation_failure_prevents_publish(editorial_base: Path, public_repo: Path):
    _write_post(editorial_base, body=_canonical_body(extra="\nTODO: fix this\n"))

    result = _publish(editorial_base, public_repo)

    assert result.status == "failed"
    assert BLOG_PUBLISH_VALIDATION_FAILED in result.errors
    assert CONTENT_CONTAINS_TODO in result.errors
    assert result.validation.get("ok") is False
    assert not list((public_repo / "_posts").glob("*.md"))

    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    if campaign is not None:
        assert campaign["state"] in (STATE_READY, STATE_VALIDATION_FAILED, STATE_VALIDATED)
        assert campaign["state"] != STATE_BLOG_PUBLISHED


def test_successful_publish_transitions_to_blog_published(
    editorial_base: Path, public_repo: Path
):
    _validated_campaign(editorial_base)
    _write_post(editorial_base)

    result = _publish(editorial_base, public_repo)

    assert result.status == "completed"
    assert result.state == STATE_BLOG_PUBLISHED
    assert result.blog_publish["status"] == "published"
    assert result.metadata_written is True

    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["state"] == STATE_BLOG_PUBLISHED

    post_path = public_repo / "_posts" / f"{PUBLICATION_DATE}-{PUBLIC_SLUG}.md"
    image_path = public_repo / "assets/images" / f"{PUBLIC_SLUG}.png"
    assert post_path.is_file()
    assert image_path.is_file()


def test_response_includes_source_public_url(editorial_base: Path, public_repo: Path):
    _validated_campaign(editorial_base)
    _write_post(editorial_base)

    result = _publish(editorial_base, public_repo)

    expected_url = f"{SITE_URL}/2026/07/06/{PUBLIC_SLUG}/"
    assert result.source_public_url == expected_url
    assert result.blog_publish["source_public_url"] == expected_url


def test_idempotent_rerun_already_published_without_validation(
    editorial_base: Path, public_repo: Path
):
    _validated_campaign(editorial_base)
    _write_post(editorial_base)

    first = _publish(editorial_base, public_repo)
    assert first.status == "completed"

    post_path = public_repo / "_posts" / f"{PUBLICATION_DATE}-{PUBLIC_SLUG}.md"
    post_mtime = post_path.stat().st_mtime

    with patch(
        "silverman_blog_linkedin.blog_publish_flow.validate_ready_post"
    ) as mock_validate:
        second = _publish(editorial_base, public_repo)

    mock_validate.assert_not_called()
    assert second.status == "completed"
    assert second.blog_publish["status"] == "already_published"
    assert second.source_public_url == first.source_public_url
    assert post_path.stat().st_mtime == post_mtime


def test_ready_campaign_validated_then_published(editorial_base: Path, public_repo: Path):
    _write_post(editorial_base)

    result = _publish(editorial_base, public_repo)

    assert result.status == "completed"
    assert result.state == STATE_BLOG_PUBLISHED
    assert BLOG_PUBLISH_INVALID_CAMPAIGN_STATE not in result.errors

    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["state"] == STATE_BLOG_PUBLISHED


def test_target_exists_without_matching_metadata_fails(
    editorial_base: Path, public_repo: Path
):
    _validated_campaign(editorial_base)
    _write_post(editorial_base)

    post_path = public_repo / "_posts" / f"{PUBLICATION_DATE}-{PUBLIC_SLUG}.md"
    post_path.write_text("pre-existing post", encoding="utf-8")

    result = _publish(editorial_base, public_repo)

    assert result.status == "failed"
    assert BLOG_PUBLISH_TARGET_EXISTS in result.errors


def test_reconcile_validated_campaign_when_public_targets_exist(
    editorial_base: Path, public_repo: Path
):
    _validated_campaign(editorial_base)
    _write_post(editorial_base)
    _write_matching_public_artifacts(editorial_base, public_repo)

    result = _publish(editorial_base, public_repo)

    assert result.status == "completed"
    assert result.state == STATE_BLOG_PUBLISHED
    assert result.blog_publish["status"] == "reconciled"
    assert result.source_public_url == f"{SITE_URL}/2026/07/06/{PUBLIC_SLUG}/"

    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["state"] == STATE_BLOG_PUBLISHED
    assert campaign["blog_publish"]["public_repo_path"].startswith("_posts/")


def test_reconcile_error_campaign_when_public_targets_match(
    editorial_base: Path, public_repo: Path
):
    _error_campaign(
        editorial_base,
        error_code=BLOG_PUBLISH_INVALID_CAMPAIGN_STATE,
        extra_errors=[BLOG_PUBLISH_TARGET_EXISTS, "package_generation_failed"],
    )
    _write_post(editorial_base)
    _write_matching_public_artifacts(editorial_base, public_repo)

    result = _publish(editorial_base, public_repo)

    assert result.status == "completed"
    assert result.state == STATE_BLOG_PUBLISHED
    assert result.blog_publish["status"] == "reconciled"
    assert result.blog_publish.get("reconciled_from_error_state") is True
    assert RECONCILED_FROM_ERROR_WARNING in result.warnings

    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["state"] == STATE_BLOG_PUBLISHED
    assert campaign["source_public_url"] == f"{SITE_URL}/2026/07/06/{PUBLIC_SLUG}/"
    assert campaign["blog_publish"]["public_repo_path"].startswith("_posts/")
    assert campaign["blog_publish"]["public_repo_image_path"].startswith("assets/images/")
    assert BLOG_PUBLISH_INVALID_CAMPAIGN_STATE not in campaign.get("errors", [])
    assert BLOG_PUBLISH_TARGET_EXISTS not in campaign.get("errors", [])
    assert "package_generation_failed" in campaign.get("errors", [])


def test_error_reconcile_fails_on_content_hash_mismatch(
    editorial_base: Path, public_repo: Path
):
    _error_campaign(editorial_base)
    _write_post(editorial_base, body=_canonical_body(extra="\nChanged after campaign.\n"))
    _write_matching_public_artifacts(editorial_base, public_repo)

    result = _publish(editorial_base, public_repo)

    assert result.status == "failed"
    assert BLOG_PUBLISH_CONTENT_HASH_CHANGED in result.errors


def test_reconcile_error_campaign_exact_server_state(
    editorial_base: Path, public_repo: Path
):
    """Regression: error + target_exists + source_public_url + public files, no paths."""
    campaign = _validated_campaign(editorial_base)
    campaign["source_public_url"] = f"{SITE_URL}/2026/07/06/{PUBLIC_SLUG}/"
    transition_state(
        campaign,
        STATE_ERROR,
        reason="Prior publish attempt failed",
        actor=ACTOR_WORKER,
        error_code=BLOG_PUBLISH_TARGET_EXISTS,
    )
    campaign["errors"] = [BLOG_PUBLISH_TARGET_EXISTS]
    campaign["blog_publish"] = {
        "status": "failed",
        "error_code": BLOG_PUBLISH_TARGET_EXISTS,
    }
    write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, campaign)
    _write_post(editorial_base)
    _write_matching_public_artifacts(editorial_base, public_repo)

    result = _publish(editorial_base, public_repo)

    assert result.status == "completed"
    assert result.state == STATE_BLOG_PUBLISHED
    assert result.source_public_url == f"{SITE_URL}/2026/07/06/{PUBLIC_SLUG}/"
    assert result.blog_publish["status"] == "reconciled"
    assert result.blog_publish["public_repo_path"].startswith("_posts/")
    assert result.blog_publish["public_repo_image_path"].startswith("assets/images/")
    assert BLOG_PUBLISH_TARGET_EXISTS not in result.errors

    campaign_after = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign_after is not None
    assert campaign_after["state"] == STATE_BLOG_PUBLISHED
    assert campaign_after["source_public_url"] == f"{SITE_URL}/2026/07/06/{PUBLIC_SLUG}/"
    assert BLOG_PUBLISH_TARGET_EXISTS not in campaign_after.get("errors", [])


def test_reconcile_attempted_before_target_exists_guard(
    editorial_base: Path, public_repo: Path
):
    """Reconciliation runs before run_publish when pending and public files exist."""
    campaign = _validated_campaign(editorial_base)
    transition_state(
        campaign,
        STATE_BLOG_PUBLISH_PENDING,
        reason="Blog publish started",
        actor=ACTOR_WORKER,
    )
    campaign["blog_publish"] = {
        "status": "pending",
        "idempotency_key": build_blog_publish_idempotency_key(
            source_slug=SOURCE_SLUG,
            public_slug=PUBLIC_SLUG,
            publication_date=PUBLICATION_DATE,
            source_content_sha256=campaign["source_content_sha256"],
        ),
    }
    write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, campaign)
    _write_post(editorial_base)
    _write_matching_public_artifacts(editorial_base, public_repo)

    with patch(
        "silverman_blog_linkedin.blog_publish_flow.run_publish",
    ) as mock_run_publish:
        result = _publish(editorial_base, public_repo)

    mock_run_publish.assert_not_called()
    assert result.status == "completed"
    assert result.state == STATE_BLOG_PUBLISHED
    assert result.blog_publish["status"] == "reconciled"


def test_run_publish_overwrite_retries_reconciliation(
    editorial_base: Path, public_repo: Path
):
    """When run_publish refuses overwrite, reconciliation is retried before failing."""
    campaign = _validated_campaign(editorial_base)
    transition_state(
        campaign,
        STATE_BLOG_PUBLISH_PENDING,
        reason="Blog publish started",
        actor=ACTOR_WORKER,
    )
    campaign["blog_publish"] = {
        "status": "pending",
        "idempotency_key": build_blog_publish_idempotency_key(
            source_slug=SOURCE_SLUG,
            public_slug=PUBLIC_SLUG,
            publication_date=PUBLICATION_DATE,
            source_content_sha256=campaign["source_content_sha256"],
        ),
    }
    write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, campaign)
    _write_post(editorial_base)
    _write_matching_public_artifacts(editorial_base, public_repo)

    call_count = {"n": 0}
    original_attempt = None

    def reconcile_side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return None
        return original_attempt(*args, **kwargs)

    import silverman_blog_linkedin.blog_publish_flow as bpf

    original_attempt = bpf._attempt_blog_publish_reconciliation
    with patch.object(
        bpf,
        "_attempt_blog_publish_reconciliation",
        side_effect=reconcile_side_effect,
    ), patch(
        "silverman_blog_linkedin.blog_publish_flow.run_publish",
    ) as mock_run_publish:
        from silverman_blog_linkedin.github_pages_publish import PublishError

        mock_run_publish.side_effect = PublishError(
            "refusing to overwrite existing target(s): stale"
        )
        result = _publish(editorial_base, public_repo)

    assert call_count["n"] == 2
    assert result.status == "completed"
    assert result.blog_publish["status"] == "reconciled"


def test_unsafe_mismatch_returns_target_exists_with_skip_reason(
    editorial_base: Path, public_repo: Path
):
    _error_campaign(editorial_base)
    _write_post(editorial_base)

    post_path = public_repo / "_posts" / f"{PUBLICATION_DATE}-{PUBLIC_SLUG}.md"
    image_path = public_repo / "assets/images" / f"{PUBLIC_SLUG}.png"
    post_path.write_text("stale public content", encoding="utf-8")
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")

    result = _publish(editorial_base, public_repo)

    assert result.status == "failed"
    assert BLOG_PUBLISH_TARGET_EXISTS in result.errors
    assert (
        result.blog_publish.get("reconciliation_skip_reason")
        == RECONCILIATION_SKIPPED_PUBLIC_CONTENT_MISMATCH
    )
    assert result.source_public_url == f"{SITE_URL}/2026/07/06/{PUBLIC_SLUG}/"
    assert result.blog_publish.get("reconciliation_expected_post_relative_path")
    assert result.blog_publish.get("reconciliation_actual_post_relative_path")
    assert result.blog_publish.get("reconciliation_expected_post_sha256")
    assert result.blog_publish.get("reconciliation_actual_post_sha256")
    assert (
        result.blog_publish["reconciliation_expected_post_sha256"]
        != result.blog_publish["reconciliation_actual_post_sha256"]
    )


def test_reconcile_error_campaign_with_run_publish_canonical_output(
    editorial_base: Path, public_repo: Path
):
    """Public post from run_publish must reconcile even when raw ready markdown differs."""
    subtitle_frontmatter = (
        "---\n"
        f"title: {TITLE}\n"
        "status: draft\n"
        "subtitle: A senior practitioner's take on starting with the domain.\n"
        "audience: architects\n"
        "type: blog-post\n"
        "language: en\n"
        f"date: {PUBLICATION_DATE}\n"
        "categories:\n"
        "  - architecture\n"
        "tags:\n"
        "  - databases\n"
        f"image: /assets/images/{PUBLIC_SLUG}.png\n"
        "---\n"
    )
    body = _canonical_body()
    md_path = _write_post(editorial_base, frontmatter=subtitle_frontmatter, body=body)
    content = md_path.read_text(encoding="utf-8")

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
    campaign["source_public_url"] = f"{SITE_URL}/2026/07/06/{PUBLIC_SLUG}/"
    transition_state(
        campaign,
        STATE_ERROR,
        reason="Prior publish attempt failed",
        actor=ACTOR_WORKER,
        error_code=BLOG_PUBLISH_TARGET_EXISTS,
    )
    campaign["errors"] = [BLOG_PUBLISH_TARGET_EXISTS]
    campaign["blog_publish"] = {
        "status": "failed",
        "error_code": BLOG_PUBLISH_TARGET_EXISTS,
    }
    write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, campaign)

    env = _publish_env(editorial_base, public_repo)
    run_publish(
        SOURCE_SLUG,
        publication_date=date.fromisoformat(PUBLICATION_DATE),
        apply=True,
        environ=env,
        json_output=False,
    )

    raw_ready = (editorial_base / SOURCE_RELATIVE).read_text(encoding="utf-8")
    public_post = (
        public_repo / "_posts" / f"{PUBLICATION_DATE}-{PUBLIC_SLUG}.md"
    ).read_text(encoding="utf-8")
    assert raw_ready != public_post

    result = _publish(editorial_base, public_repo)

    assert result.status == "completed"
    assert result.state == STATE_BLOG_PUBLISHED
    assert result.blog_publish["status"] == "reconciled"
    assert BLOG_PUBLISH_TARGET_EXISTS not in result.errors


def test_reconcile_adopts_existing_public_image_when_post_canonical(
    editorial_base: Path, public_repo: Path
):
    """Regression: error + target_exists + canonical post + differing official public image."""
    campaign = _validated_campaign(editorial_base)
    campaign["source_public_url"] = f"{SITE_URL}/2026/07/06/{PUBLIC_SLUG}/"
    transition_state(
        campaign,
        STATE_ERROR,
        reason="Prior publish attempt failed",
        actor=ACTOR_WORKER,
        error_code=BLOG_PUBLISH_TARGET_EXISTS,
    )
    campaign["errors"] = [BLOG_PUBLISH_TARGET_EXISTS]
    campaign["blog_publish"] = {
        "status": "failed",
        "error_code": BLOG_PUBLISH_TARGET_EXISTS,
    }
    write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, campaign)
    _write_post(editorial_base)

    official_image = b"\x89PNG\r\n\x1a\nofficial-corrected-image"
    post_path, image_path = _write_matching_public_artifacts(
        editorial_base,
        public_repo,
        image_bytes=official_image,
    )
    ready_image = (editorial_base / IMAGE_RELATIVE).read_bytes()
    assert ready_image != official_image

    result = _publish(editorial_base, public_repo)

    assert result.status == "completed"
    assert result.state == STATE_BLOG_PUBLISHED
    assert result.blog_publish["status"] == "reconciled"
    assert result.blog_publish.get("public_repo_image_path") == (
        f"assets/images/{PUBLIC_SLUG}.png"
    )
    assert result.blog_publish.get("public_image_adopted") is True
    assert result.blog_publish.get("public_image_source") == "existing_public_asset"
    assert result.blog_publish.get("ready_image_sha256")
    assert result.blog_publish.get("published_image_sha256")
    assert (
        result.blog_publish["ready_image_sha256"]
        != result.blog_publish["published_image_sha256"]
    )
    assert (
        result.blog_publish.get("reconciliation_note")
        == "public_image_differs_from_ready_image_adopted"
    )
    assert BLOG_PUBLISH_TARGET_EXISTS not in result.errors
    assert image_path.read_bytes() == official_image
    assert post_path.read_text(encoding="utf-8") == render_expected_public_post(
        editorial_base / SOURCE_RELATIVE,
        PUBLIC_SLUG,
        date.fromisoformat(PUBLICATION_DATE),
    )

    campaign_after = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign_after is not None
    assert campaign_after["state"] == STATE_BLOG_PUBLISHED
    assert campaign_after.get("published_post_relative_path", "").startswith("_posts/")
    assert campaign_after.get("published_image_relative_path", "").startswith(
        "assets/images/"
    )
    assert BLOG_PUBLISH_TARGET_EXISTS not in campaign_after.get("errors", [])


def test_public_post_mismatch_does_not_adopt_image(
    editorial_base: Path, public_repo: Path
):
    _error_campaign(editorial_base)
    _write_post(editorial_base)

    post_path = public_repo / "_posts" / f"{PUBLICATION_DATE}-{PUBLIC_SLUG}.md"
    image_path = public_repo / "assets/images" / f"{PUBLIC_SLUG}.png"
    post_path.write_text("stale public content", encoding="utf-8")
    official_image = b"\x89PNG\r\n\x1a\nofficial-corrected-image"
    image_path.write_bytes(official_image)

    result = _publish(editorial_base, public_repo)

    assert result.status == "failed"
    assert BLOG_PUBLISH_TARGET_EXISTS in result.errors
    assert (
        result.blog_publish.get("reconciliation_skip_reason")
        == RECONCILIATION_SKIPPED_PUBLIC_CONTENT_MISMATCH
    )
    assert result.blog_publish.get("public_image_adopted") is None
    assert image_path.read_bytes() == official_image


def test_missing_public_image_handoff_completes_publish(
    editorial_base: Path, public_repo: Path
):
    """Pre-handoff fills missing public image when canonical post already exists."""
    _error_campaign(editorial_base)
    _write_post(editorial_base)

    post_path = public_repo / "_posts" / f"{PUBLICATION_DATE}-{PUBLIC_SLUG}.md"
    post_path.write_text(
        render_expected_public_post(
            editorial_base / SOURCE_RELATIVE,
            PUBLIC_SLUG,
            date.fromisoformat(PUBLICATION_DATE),
        ),
        encoding="utf-8",
    )

    result = _publish(editorial_base, public_repo)

    assert result.status == "completed"
    assert (public_repo / "assets/images" / f"{PUBLIC_SLUG}.png").is_file()
    assert result.blog_image_generation.get("public_asset_handoff_status") == "copied"


def test_campaign_beyond_blog_publish_does_not_adopt_image(
    editorial_base: Path, public_repo: Path
):
    _validated_campaign(editorial_base)
    _write_post(editorial_base)

    official_image = b"\x89PNG\r\n\x1a\nofficial-corrected-image"
    image_path = _write_matching_public_artifacts(
        editorial_base,
        public_repo,
        image_bytes=official_image,
    )[1]

    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
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
    transition_state(
        campaign,
        STATE_DERIVATIVES_PENDING,
        reason="Derivatives started",
        actor=ACTOR_WORKER,
    )
    write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, campaign)

    result = _publish(editorial_base, public_repo)

    assert result.status == "failed"
    assert BLOG_PUBLISH_INVALID_CAMPAIGN_STATE in result.errors
    assert result.blog_publish.get("public_image_adopted") is None
    assert image_path.read_bytes() == official_image


def test_target_exists_failure_includes_source_public_url(
    editorial_base: Path, public_repo: Path
):
    _error_campaign(
        editorial_base,
        source_relative_path="blog-posts/ready/other-post.md",
    )
    _write_post(editorial_base)
    _write_matching_public_artifacts(editorial_base, public_repo)

    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    campaign["source_public_url"] = f"{SITE_URL}/2026/07/06/{PUBLIC_SLUG}/"
    write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, campaign)

    result = _publish(editorial_base, public_repo)

    assert result.status == "failed"
    assert BLOG_PUBLISH_TARGET_EXISTS in result.errors
    assert result.source_public_url == f"{SITE_URL}/2026/07/06/{PUBLIC_SLUG}/"
    assert (
        result.blog_publish.get("reconciliation_skip_reason")
        == RECONCILIATION_SKIPPED_SOURCE_MISMATCH
    )


def test_error_reconcile_fails_on_wrong_source_path(
    editorial_base: Path, public_repo: Path
):
    _error_campaign(
        editorial_base,
        source_relative_path="blog-posts/ready/other-post.md",
    )
    _write_post(editorial_base)
    _write_matching_public_artifacts(editorial_base, public_repo)

    result = _publish(editorial_base, public_repo)

    assert result.status == "failed"
    assert BLOG_PUBLISH_TARGET_EXISTS in result.errors
    assert (
        result.blog_publish.get("reconciliation_skip_reason")
        == RECONCILIATION_SKIPPED_SOURCE_MISMATCH
    )


def test_invalid_campaign_state_fails(editorial_base: Path, public_repo: Path):
    _validated_campaign(editorial_base)
    _write_post(editorial_base)

    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
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
    transition_state(
        campaign,
        STATE_DERIVATIVES_PENDING,
        reason="Derivatives started",
        actor=ACTOR_WORKER,
    )
    write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, campaign)

    result = _publish(editorial_base, public_repo)

    assert result.status == "failed"
    assert BLOG_PUBLISH_INVALID_CAMPAIGN_STATE in result.errors


def test_changed_content_hash_fails(editorial_base: Path, public_repo: Path):
    _validated_campaign(editorial_base)
    _write_post(editorial_base, body=_canonical_body(extra="\nExtra paragraph.\n"))

    result = _publish(editorial_base, public_repo)

    assert result.status == "failed"
    assert BLOG_PUBLISH_CONTENT_HASH_CHANGED in result.errors


def test_campaign_metadata_excludes_markdown_body(
    editorial_base: Path, public_repo: Path
):
    _validated_campaign(editorial_base)
    _write_post(editorial_base)

    result = _publish(editorial_base, public_repo)
    assert result.status == "completed"

    metadata_path = editorial_base / METADATA_CAMPAIGNS_RELATIVE / f"{CANONICAL_CAMPAIGN_ID}.json"
    raw = metadata_path.read_text(encoding="utf-8")
    assert "markdown_content" not in raw
    assert "generated_draft_content" not in raw
    assert TITLE not in raw


def test_public_repo_not_configured(editorial_base: Path):
    _validated_campaign(editorial_base)
    _write_post(editorial_base)

    result = publish_blog_post(
        editorial_base,
        SOURCE_RELATIVE,
        site_url=SITE_URL,
        github_pages_repo_path=None,
        environ={"SILVERMAN_BLOG_LINKEDIN_BASE_PATH": str(editorial_base)},
    )

    assert result.status == "failed"
    assert BLOG_IMAGE_PUBLIC_ASSET_HANDOFF_FAILED in result.errors


def test_source_file_not_moved_after_publish(editorial_base: Path, public_repo: Path):
    md_path = _write_post(editorial_base)
    _validated_campaign(editorial_base)

    result = _publish(editorial_base, public_repo)
    assert result.status == "completed"
    assert md_path.is_file()
    assert md_path.parent.name == "ready"


def test_http_endpoint_requires_auth(editorial_base: Path, public_repo: Path, monkeypatch):
    create_full_layout(editorial_base)
    _write_post(editorial_base)
    monkeypatch.setenv("SILVERMAN_GITHUB_PAGES_REPO_PATH", str(public_repo))

    client = TestClient(create_app(make_settings(editorial_base)))

    unauth = client.post(
        "/publish-blog-post",
        json={"source_relative_path": SOURCE_RELATIVE},
    )
    assert unauth.status_code == 401

    bad_key = client.post(
        "/publish-blog-post",
        headers={"Authorization": "Bearer wrong-key"},
        json={"source_relative_path": SOURCE_RELATIVE},
    )
    assert bad_key.status_code == 401


def test_http_endpoint_successful_publish(
    editorial_base: Path, public_repo: Path, monkeypatch
):
    create_full_layout(editorial_base)
    _validated_campaign(editorial_base)
    _write_post(editorial_base)
    monkeypatch.setenv("SILVERMAN_GITHUB_PAGES_REPO_PATH", str(public_repo))

    client = TestClient(create_app(make_settings(editorial_base)))
    response = client.post(
        "/publish-blog-post",
        headers=auth_header(),
        json={"source_relative_path": SOURCE_RELATIVE, "site_url": SITE_URL},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["campaign_id"] == CANONICAL_CAMPAIGN_ID
    assert body["state"] == STATE_BLOG_PUBLISHED
    assert body["source_public_url"] == f"{SITE_URL}/2026/07/06/{PUBLIC_SLUG}/"
    assert body["blog_publish"]["status"] == "published"
    assert "validation" in body
    assert "metadata_written" in body


def test_flow_b_campaign_rejected(editorial_base: Path, public_repo: Path):
    _validated_campaign(editorial_base)
    _write_post(editorial_base)

    flow_b_campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert flow_b_campaign is not None
    flow_b_campaign = dict(flow_b_campaign)
    flow_b_campaign["flow"] = FLOW_B

    original_read = read_campaign_metadata
    validation_completed = {"done": False}

    def patched_read(base_path: Path, campaign_id: str):
        if (
            validation_completed["done"]
            and campaign_id == CANONICAL_CAMPAIGN_ID
        ):
            return flow_b_campaign
        return original_read(base_path, campaign_id)

    def mark_validation_done(*args, **kwargs):
        validation_completed["done"] = True
        from silverman_blog_linkedin.ready_post_validation import (
            validate_ready_post as real_validate,
        )

        return real_validate(*args, **kwargs)

    with (
        patch(
            "silverman_blog_linkedin.blog_publish_flow.read_campaign_metadata",
            side_effect=patched_read,
        ),
        patch(
            "silverman_blog_linkedin.blog_publish_flow.validate_ready_post",
            side_effect=mark_validation_done,
        ),
    ):
        result = _publish(editorial_base, public_repo)

    assert result.status == "failed"
    assert "blog_publish_flow_b_not_allowed" in result.errors


def test_no_linkedin_drafts_generated(editorial_base: Path, public_repo: Path):
    _validated_campaign(editorial_base)
    _write_post(editorial_base)

    _publish(editorial_base, public_repo)

    review_dir = editorial_base / "linkedin-posts" / "review"
    if review_dir.is_dir():
        assert list(review_dir.glob("*.md")) == []


def test_metadata_write_failure_surfaces_error_code(
    editorial_base: Path, public_repo: Path
):
    _validated_campaign(editorial_base)
    _write_post(editorial_base)

    with patch(
        "silverman_blog_linkedin.blog_publish_flow._persist_campaign",
        return_value=(False, "campaign_metadata_write_failed"),
    ):
        result = _publish(editorial_base, public_repo)

    assert result.status == "failed"
    assert result.metadata_written is False
    assert result.metadata_error_code == "campaign_metadata_write_failed"
    assert BLOG_PUBLISH_METADATA_WRITE_FAILED in result.errors
    assert not list((public_repo / "_posts").glob("*.md"))

    metadata_path = (
        editorial_base / METADATA_CAMPAIGNS_RELATIVE / f"{CANONICAL_CAMPAIGN_ID}.json"
    )
    if metadata_path.is_file():
        raw = metadata_path.read_text(encoding="utf-8")
        assert "markdown_content" not in raw
        assert "generated_draft_content" not in raw
        assert TITLE not in raw


def test_published_campaign_metadata_has_idempotency_key(
    editorial_base: Path, public_repo: Path
):
    _validated_campaign(editorial_base)
    content = _write_post(editorial_base).read_text(encoding="utf-8")
    content_hash = compute_source_content_sha256(content)
    expected_key = build_blog_publish_idempotency_key(
        source_slug=SOURCE_SLUG,
        public_slug=PUBLIC_SLUG,
        publication_date=PUBLICATION_DATE,
        source_content_sha256=content_hash,
    )

    result = _publish(editorial_base, public_repo)
    assert result.status == "completed"
    assert result.blog_publish["idempotency_key"] == expected_key

    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["blog_publish"]["idempotency_key"] == expected_key


def test_disabled_generation_fails_with_specific_image_error(
    editorial_base: Path, public_repo: Path
):
    _write_post(
        editorial_base,
        frontmatter=_canonical_frontmatter(include_image=False),
        with_png=False,
    )

    result = _publish(editorial_base, public_repo)

    assert result.status == "failed"
    assert BLOG_IMAGE_GENERATION_DISABLED in result.errors
    assert result.blog_image_generation.get("error_code") == BLOG_IMAGE_GENERATION_DISABLED
    assert not list((public_repo / "_posts").glob("*.md"))


def test_publish_surfaces_specific_comfyui_timeout_error(
    editorial_base: Path, public_repo: Path
):
    from silverman_blog_linkedin.comfyui_client import BLOG_IMAGE_GENERATION_TIMEOUT

    _write_post(
        editorial_base,
        frontmatter=_canonical_frontmatter(include_image=False),
        with_png=False,
    )

    result = _publish(
        editorial_base,
        public_repo,
        environ=_comfy_enabled_env(editorial_base, public_repo),
        comfyui_client=FakeComfyUIClient(error_code=BLOG_IMAGE_GENERATION_TIMEOUT),
    )

    assert result.status == "failed"
    assert BLOG_IMAGE_GENERATION_TIMEOUT in result.errors
    assert result.errors.count(BLOG_IMAGE_GENERATION_FAILED) == 0
    assert result.blog_image_generation.get("error_code") == BLOG_IMAGE_GENERATION_TIMEOUT


def test_enabled_generation_then_publish_success(
    editorial_base: Path, public_repo: Path
):
    _write_post(
        editorial_base,
        frontmatter=_canonical_frontmatter(include_image=False),
        with_png=False,
    )

    result = _publish(
        editorial_base,
        public_repo,
        environ=_comfy_enabled_env(editorial_base, public_repo),
        comfyui_client=FakeComfyUIClient(),
    )

    assert result.status == "completed"
    assert result.state == STATE_BLOG_PUBLISHED
    assert result.blog_image_generation.get("status") == "generated"
    assert (editorial_base / IMAGE_RELATIVE).is_file()
    assert (public_repo / "assets/images" / f"{PUBLIC_SLUG}.png").is_file()


def test_generation_failure_blocks_publish_before_public_writes(
    editorial_base: Path, public_repo: Path
):
    _write_post(
        editorial_base,
        frontmatter=_canonical_frontmatter(include_image=False),
        with_png=False,
    )

    result = _publish(
        editorial_base,
        public_repo,
        environ=_comfy_enabled_env(editorial_base, public_repo),
        comfyui_client=FakeComfyUIClient(
            error_code=BLOG_IMAGE_GENERATION_COMFYUI_FAILED
        ),
    )

    assert result.status == "failed"
    assert BLOG_IMAGE_GENERATION_COMFYUI_FAILED in result.errors
    assert result.blog_image_generation.get("status") == "failed"
    assert not list((public_repo / "_posts").glob("*.md"))
    assert not list((public_repo / "assets/images").glob("*.png"))


def test_existing_valid_image_publish_unchanged_when_generation_disabled(
    editorial_base: Path, public_repo: Path
):
    _validated_campaign(editorial_base)
    _write_post(editorial_base)
    (public_repo / "assets/images" / f"{PUBLIC_SLUG}.png").write_bytes(
        (editorial_base / IMAGE_RELATIVE).read_bytes()
    )

    result = _publish(editorial_base, public_repo)

    assert result.status == "completed"
    assert result.blog_image_generation.get("skip_reason") == "already_valid"


def test_publish_adopts_ready_sibling_before_validation(
    editorial_base: Path, public_repo: Path
):
    _validated_campaign(editorial_base)
    _write_post(editorial_base)

    result = _publish(
        editorial_base,
        public_repo,
        environ=_comfy_enabled_env(editorial_base, public_repo),
        comfyui_client=FakeComfyUIClient(),
    )

    assert result.status == "completed"
    assert result.blog_image_generation.get("public_asset_handoff_status") == "copied"
    assert (public_repo / "assets/images" / f"{PUBLIC_SLUG}.png").is_file()


def test_publish_handoff_failure_blocks_validation_and_bridge(
    editorial_base: Path, public_repo: Path,
):
    _validated_campaign(editorial_base)
    _write_post(editorial_base)
    images_dir = public_repo / "assets/images"
    images_dir.chmod(0o555)

    try:
        result = _publish(
            editorial_base,
            public_repo,
            environ=_comfy_enabled_env(editorial_base, public_repo),
            comfyui_client=FakeComfyUIClient(),
        )
    finally:
        images_dir.chmod(0o755)

    assert result.status == "failed"
    assert BLOG_IMAGE_PUBLIC_ASSET_HANDOFF_FAILED in result.errors
    assert result.blog_image_generation.get("status") == "failed"
    assert not list((public_repo / "_posts").glob("*.md"))


def test_publish_public_asset_backfill_warning_allows_image_step(
    editorial_base: Path, public_repo: Path,
):
    content = _write_post(
        editorial_base,
        with_png=False,
    ).read_text(encoding="utf-8")
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
    write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, campaign)

    assert f"image: /assets/images/{PUBLIC_SLUG}.png" in content
    (public_repo / "assets/images" / f"{PUBLIC_SLUG}.png").write_bytes(
        b"\x89PNG\r\n\x1a\npublic-only"
    )
    ready_dir = editorial_base / "blog-posts" / "ready"
    ready_dir.chmod(0o555)

    try:
        result = _publish(
            editorial_base,
            public_repo,
            environ=_comfy_enabled_env(editorial_base, public_repo),
            comfyui_client=FakeComfyUIClient(),
        )
    finally:
        ready_dir.chmod(0o755)

    assert BLOG_IMAGE_PUBLIC_ASSET_HANDOFF_FAILED not in result.errors
    assert WARNING_READY_SIBLING_BACKFILL_FAILED in (
        result.blog_image_generation.get("warnings") or []
    )
    assert result.blog_image_generation.get("skip_reason") == "public_asset_reuse"
    assert result.blog_image_generation.get("ready_sibling_backfill_status") == "failed"
    assert result.status == "failed"
    assert (
        BLOG_PUBLISH_VALIDATION_FAILED in result.errors
        or BLOG_PUBLISH_TARGET_EXISTS in result.errors
    )


def test_bridge_apply_succeeds_when_public_image_pre_handoff(
    editorial_base: Path, public_repo: Path
):
    _validated_campaign(editorial_base)
    _write_post(editorial_base)
    sibling_bytes = (editorial_base / IMAGE_RELATIVE).read_bytes()
    (public_repo / "assets/images" / f"{PUBLIC_SLUG}.png").write_bytes(sibling_bytes)

    result = _publish(editorial_base, public_repo)

    assert result.status == "completed"
    assert (public_repo / "assets/images" / f"{PUBLIC_SLUG}.png").read_bytes() == (
        sibling_bytes
    )
    assert (public_repo / "_posts" / f"{PUBLICATION_DATE}-{PUBLIC_SLUG}.md").is_file()


POST_02_SOURCE_SLUG = "02-deferring-is-not-avoiding-it-can-be-architecture"
POST_02_PUBLIC_SLUG = "deferring-is-not-avoiding-it-can-be-architecture"
POST_02_PUBLICATION_DATE = "2026-07-10"
POST_02_EXECUTION_TIME = datetime(2026, 7, 9, 21, 8, 0, tzinfo=EDITORIAL_TZ)
POST_02_SOURCE_RELATIVE = f"blog-posts/ready/{POST_02_SOURCE_SLUG}.md"
POST_02_CAMPAIGN_ID = f"flow-a-{POST_02_PUBLICATION_DATE}-{POST_02_PUBLIC_SLUG}"


def _write_post_02(editorial_base: Path) -> Path:
    ready = editorial_base / "blog-posts" / "ready"
    ready.mkdir(parents=True, exist_ok=True)
    md_path = ready / f"{POST_02_SOURCE_SLUG}.md"
    md_path.write_text(
        "---\n"
        "title: Deferring Is Not Avoiding — It Can Be Architecture\n"
        "audience: architects\n"
        "type: blog-post\n"
        "language: en\n"
        "layout: post\n"
        f"date: {POST_02_PUBLICATION_DATE}\n"
        "categories:\n"
        "  - architecture\n"
        "tags:\n"
        "  - leadership\n"
        "description: On intentional deferral as an architectural choice.\n"
        f"image: /assets/images/{POST_02_PUBLIC_SLUG}.png\n"
        "---\n"
        "# Deferring Is Not Avoiding\n\n"
        "Editorial body for post 02 regression.\n",
        encoding="utf-8",
    )
    (ready / f"{POST_02_SOURCE_SLUG}.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    return md_path


def _validated_post_02_campaign(editorial_base: Path) -> dict:
    content = _write_post_02(editorial_base).read_text(encoding="utf-8")
    campaign = build_initial_campaign_metadata(
        flow=FLOW_A,
        source_slug=POST_02_SOURCE_SLUG,
        public_slug=POST_02_PUBLIC_SLUG,
        source_relative_path=POST_02_SOURCE_RELATIVE,
        image_relative_path=f"blog-posts/ready/{POST_02_SOURCE_SLUG}.png",
        source_content=content,
        publication_date=POST_02_PUBLICATION_DATE,
    )
    transition_state(
        campaign,
        STATE_VALIDATED,
        reason="Editorial validation passed",
        actor=ACTOR_WORKER,
    )
    write_campaign_metadata(editorial_base, POST_02_CAMPAIGN_ID, campaign)
    return campaign


def test_publish_adjusted_date_preserves_intended_source_public_url(
    editorial_base: Path, public_repo: Path
):
    _validated_post_02_campaign(editorial_base)

    result = _publish(
        editorial_base,
        public_repo,
        relative=POST_02_SOURCE_RELATIVE,
        execution_time=POST_02_EXECUTION_TIME,
    )

    expected_url = (
        f"{SITE_URL}/2026/07/10/{POST_02_PUBLIC_SLUG}/"
    )
    assert result.status == "completed"
    assert result.source_public_url == expected_url
    assert result.blog_publish["source_public_url"] == expected_url
    assert result.blog_publish.get("date_adjusted") is True
    assert result.blog_publish.get("permalink") == (
        f"/2026/07/10/{POST_02_PUBLIC_SLUG}/"
    )

    post_path = (
        public_repo
        / "_posts"
        / f"{POST_02_PUBLICATION_DATE}-{POST_02_PUBLIC_SLUG}.md"
    )
    assert post_path.is_file()
    post_body = post_path.read_text(encoding="utf-8")
    assert "date: 2026-07-09 21:08:00 -0500" in post_body
    assert (
        f"permalink: /2026/07/10/{POST_02_PUBLIC_SLUG}/" in post_body
        or f'permalink: "/2026/07/10/{POST_02_PUBLIC_SLUG}/"' in post_body
    )


def test_reconcile_adjusted_date_public_post_matches_canonical_output(
    editorial_base: Path, public_repo: Path
):
    _validated_post_02_campaign(editorial_base)
    md_path = editorial_base / POST_02_SOURCE_RELATIVE
    post_body = render_expected_public_post(
        md_path,
        POST_02_PUBLIC_SLUG,
        date.fromisoformat(POST_02_PUBLICATION_DATE),
        execution_time=POST_02_EXECUTION_TIME,
    )
    post_path = (
        public_repo
        / "_posts"
        / f"{POST_02_PUBLICATION_DATE}-{POST_02_PUBLIC_SLUG}.md"
    )
    image_path = public_repo / "assets/images" / f"{POST_02_PUBLIC_SLUG}.png"
    post_path.write_text(post_body, encoding="utf-8")
    image_path.write_bytes((editorial_base / f"blog-posts/ready/{POST_02_SOURCE_SLUG}.png").read_bytes())

    result = _publish(
        editorial_base,
        public_repo,
        relative=POST_02_SOURCE_RELATIVE,
        execution_time=POST_02_EXECUTION_TIME,
    )

    assert result.status == "completed"
    assert result.blog_publish["status"] == "reconciled"
    assert result.source_public_url == (
        f"{SITE_URL}/2026/07/10/{POST_02_PUBLIC_SLUG}/"
    )
