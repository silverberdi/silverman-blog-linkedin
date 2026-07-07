"""Tests for Flow A blog publish orchestration and HTTP endpoint."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from datetime import date

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.blog_publish_flow import (
    BLOG_PUBLISH_CONTENT_HASH_CHANGED,
    BLOG_PUBLISH_INVALID_CAMPAIGN_STATE,
    BLOG_PUBLISH_METADATA_WRITE_FAILED,
    BLOG_PUBLISH_PUBLIC_REPO_NOT_CONFIGURED,
    BLOG_PUBLISH_TARGET_EXISTS,
    BLOG_PUBLISH_VALIDATION_FAILED,
    RECONCILED_FROM_ERROR_WARNING,
    publish_blog_post,
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
from silverman_blog_linkedin.github_pages_publish import (
    prepare_frontmatter,
    render_markdown,
)
from silverman_blog_linkedin.main import create_app
from silverman_blog_linkedin.ready_post_validation import CONTENT_CONTAINS_TODO
from tests.conftest import auth_header, create_full_layout, make_settings

SOURCE_SLUG = "01-why-i-did-not-start-with-the-database"
PUBLIC_SLUG = "why-i-did-not-start-with-the-database"
PUBLICATION_DATE = "2026-07-06"
SOURCE_RELATIVE = f"blog-posts/ready/{SOURCE_SLUG}.md"
IMAGE_RELATIVE = f"blog-posts/ready/{SOURCE_SLUG}.png"
CANONICAL_CAMPAIGN_ID = f"flow-a-{PUBLICATION_DATE}-{PUBLIC_SLUG}"
SITE_URL = "https://silverman.pro"
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


def _publish(
    editorial_base: Path,
    repo_path: Path,
    *,
    relative: str = SOURCE_RELATIVE,
):
    return publish_blog_post(
        editorial_base,
        relative,
        site_url=SITE_URL,
        github_pages_repo_path=str(repo_path),
        environ=_publish_env(editorial_base, repo_path),
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
        frontmatter, body = prepare_frontmatter(
            md_path,
            PUBLIC_SLUG,
            date.fromisoformat(PUBLICATION_DATE),
        )
        post_body = render_markdown(frontmatter, body)
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
    assert BLOG_PUBLISH_INVALID_CAMPAIGN_STATE in result.errors


def test_error_reconcile_fails_on_mismatched_public_content(
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
    assert BLOG_PUBLISH_PUBLIC_REPO_NOT_CONFIGURED in result.errors


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
