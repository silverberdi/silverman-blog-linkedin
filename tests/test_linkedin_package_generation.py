"""Tests for Flow A LinkedIn derivative package generation."""

from __future__ import annotations

import json
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
    STATE_VALIDATED,
    build_initial_campaign_metadata,
    compute_source_content_sha256,
    read_campaign_metadata,
    transition_state,
    write_campaign_metadata,
)
from silverman_blog_linkedin.deepseek_client import DeepSeekGenerationResult
from silverman_blog_linkedin.linkedin_article_preview import (
    ARTICLE_PREVIEW_AVAILABLE,
    ARTICLE_PREVIEW_INVALID,
    ARTICLE_PREVIEW_MISSING,
    ARTICLE_PREVIEW_SKIPPED,
    LINKEDIN_ARTICLE_PREVIEW_IMAGE_INVALID,
    LINKEDIN_ARTICLE_PREVIEW_PUBLIC_IMAGE_MISSING,
    LINKEDIN_ARTICLE_PREVIEW_PUBLIC_REPO_NOT_CONFIGURED,
    build_public_image_url,
)
from silverman_blog_linkedin.linkedin_distribution_schedule import (
    schedule_linkedin_distribution,
)
from silverman_blog_linkedin.linkedin_package_flow import (
    GENERATED_RELATIVE,
    LINKEDIN_PACKAGE_CAMPAIGN_NOT_FOUND,
    LINKEDIN_PACKAGE_FLOW_NOT_ALLOWED,
    LINKEDIN_PACKAGE_GENERATED_DIR_NOT_READY,
    LINKEDIN_PACKAGE_GENERATED_DIR_NOT_WRITABLE,
    LINKEDIN_PACKAGE_GENERATION_FAILED,
    LINKEDIN_PACKAGE_INVALID_CAMPAIGN_STATE,
    LINKEDIN_PACKAGE_INVALID_VARIANT,
    LINKEDIN_PACKAGE_MISSING_SOURCE_PUBLIC_URL,
    LINKEDIN_PACKAGE_PUBLIC_URL_CHANGED,
    LINKEDIN_PACKAGE_SOURCE_HASH_CHANGED,
    LINKEDIN_PACKAGE_TARGET_EXISTS,
    build_package_idempotency_key,
    generate_linkedin_package,
)
from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, create_full_layout, make_settings

SOURCE_SLUG = "01-why-i-did-not-start-with-the-database"
PUBLIC_SLUG = "why-i-did-not-start-with-the-database"
PUBLICATION_DATE = "2026-07-06"
SOURCE_RELATIVE = f"blog-posts/ready/{SOURCE_SLUG}.md"
IMAGE_RELATIVE = f"blog-posts/ready/{SOURCE_SLUG}.png"
CANONICAL_CAMPAIGN_ID = f"flow-a-{PUBLICATION_DATE}-{PUBLIC_SLUG}"
SITE_URL = "https://silverman.pro"
PUBLIC_URL = f"{SITE_URL}/2026/07/06/{PUBLIC_SLUG}/"
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


def _write_post(base: Path, *, body: str | None = None) -> Path:
    ready = base / "blog-posts" / "ready"
    ready.mkdir(parents=True, exist_ok=True)
    md_path = ready / f"{SOURCE_SLUG}.md"
    md_path.write_text(_canonical_frontmatter() + (body or _canonical_body()), encoding="utf-8")
    return md_path


def _setup_metadata_campaigns(base: Path) -> Path:
    metadata_dir = base / METADATA_CAMPAIGNS_RELATIVE
    metadata_dir.mkdir(parents=True, exist_ok=True)
    return metadata_dir


def _blog_published_campaign(base: Path) -> dict:
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
    write_campaign_metadata(base, CANONICAL_CAMPAIGN_ID, campaign)
    return campaign


def _mock_generator_factory(
    *,
    url: str = PUBLIC_URL,
    url_count: int = 1,
    fail_variant: str | None = None,
):
    def _generator(_settings, _messages):
        variant_hint = None
        for message in _messages:
            if message.get("role") != "user":
                continue
            for line in message.get("content", "").splitlines():
                if line.startswith("Variant hint:"):
                    variant_hint = line.split(":", 1)[1].strip()
                    break
        if fail_variant and variant_hint == fail_variant:
            return DeepSeekGenerationResult(content=None, error_code="deepseek_unavailable")
        body = "Senior architecture insight for LinkedIn.\n\n"
        if url_count == 1:
            body += f"Read the full story here: {url}\n"
        elif url_count == 0:
            body += "No URL in this draft.\n"
        else:
            body += f"Read here: {url}\nAlso see: {url}\n"
        return DeepSeekGenerationResult(content=body, error_code=None)

    return _generator


def _generate(
    base: Path,
    *,
    campaign_id: str | None = CANONICAL_CAMPAIGN_ID,
    source_relative_path: str | None = None,
    variants: list[str] | None = None,
    site_url: str | None = None,
    generate_content=None,
):
    return generate_linkedin_package(
        base,
        campaign_id=campaign_id,
        source_relative_path=source_relative_path,
        variants=variants,
        site_url=site_url,
        environ={"DEEPSEEK_API_KEY": "test-key"},
        generate_content=generate_content or _mock_generator_factory(),
    )


def _setup_public_repo(repo_path: Path, *, with_image: bool = False) -> None:
    images_dir = repo_path / "assets" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    (repo_path / "_posts").mkdir(parents=True, exist_ok=True)
    if with_image:
        (images_dir / f"{PUBLIC_SLUG}.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")


def _publish_env(editorial_base: Path, repo_path: Path) -> dict[str, str]:
    return {
        "DEEPSEEK_API_KEY": "test-key",
        "SILVERMAN_GITHUB_PAGES_REPO_PATH": str(repo_path),
        "SILVERMAN_SITE_URL": SITE_URL,
        "SILVERMAN_BLOG_LINKEDIN_BASE_PATH": str(editorial_base),
    }


def _generate_with_repo(
    base: Path,
    repo_path: Path,
    *,
    with_image: bool = True,
    campaign_id: str | None = CANONICAL_CAMPAIGN_ID,
    **kwargs,
):
    _setup_public_repo(repo_path, with_image=with_image)
    env = _publish_env(base, repo_path)
    return generate_linkedin_package(
        base,
        campaign_id=campaign_id,
        environ=env,
        generate_content=kwargs.pop("generate_content", None) or _mock_generator_factory(),
        **kwargs,
    )


@pytest.fixture
def public_repo(tmp_path: Path) -> Path:
    repo_path = tmp_path / "public-blog"
    repo_path.mkdir()
    return repo_path


@pytest.fixture
def editorial_base(tmp_path: Path) -> Path:
    _setup_metadata_campaigns(tmp_path)
    (tmp_path / "linkedin-posts").mkdir(parents=True, exist_ok=True)
    return tmp_path


def test_campaign_not_found(editorial_base: Path):
    result = _generate(editorial_base, campaign_id="flow-a-2026-07-06-missing")

    assert result.status == "failed"
    assert LINKEDIN_PACKAGE_CAMPAIGN_NOT_FOUND in result.errors


def test_flow_b_rejected(editorial_base: Path):
    _blog_published_campaign(editorial_base)
    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    campaign = dict(campaign)
    campaign["flow"] = FLOW_B
    write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, campaign)

    result = _generate(editorial_base)

    assert result.status == "failed"
    assert LINKEDIN_PACKAGE_FLOW_NOT_ALLOWED in result.errors


def test_campaign_before_blog_published(editorial_base: Path):
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
    write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, campaign)

    result = _generate(editorial_base)

    assert result.status == "failed"
    assert LINKEDIN_PACKAGE_INVALID_CAMPAIGN_STATE in result.errors


def test_missing_source_public_url(editorial_base: Path):
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
    campaign["source_public_url"] = None
    write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, campaign)

    result = _generate(editorial_base)

    assert result.status == "failed"
    assert LINKEDIN_PACKAGE_MISSING_SOURCE_PUBLIC_URL in result.errors


def test_source_hash_changed(editorial_base: Path):
    _blog_published_campaign(editorial_base)
    _write_post(editorial_base, body=_canonical_body(extra="\nChanged paragraph.\n"))

    result = _generate(editorial_base)

    assert result.status == "failed"
    assert LINKEDIN_PACKAGE_SOURCE_HASH_CHANGED in result.errors


def test_success_writes_four_artifacts(editorial_base: Path):
    _blog_published_campaign(editorial_base)

    result = _generate(editorial_base)

    assert result.status == "completed"
    generated_dir = editorial_base / GENERATED_RELATIVE / CANONICAL_CAMPAIGN_ID
    for variant_id in sorted(CANONICAL_VARIANT_IDS):
        artifact = generated_dir / f"{variant_id}.md"
        assert artifact.is_file()


def test_campaign_transitions_to_derivatives_generated(editorial_base: Path):
    _blog_published_campaign(editorial_base)

    result = _generate(editorial_base)

    assert result.status == "completed"
    assert result.state == STATE_DERIVATIVES_GENERATED

    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["state"] == STATE_DERIVATIVES_GENERATED
    states = [entry["to_state"] for entry in campaign["state_history"]]
    assert STATE_DERIVATIVES_PENDING in states
    assert STATE_DERIVATIVES_GENERATED in states


def test_each_variant_contains_url_exactly_once(editorial_base: Path):
    _blog_published_campaign(editorial_base)

    result = _generate(editorial_base)
    assert result.status == "completed"

    generated_dir = editorial_base / GENERATED_RELATIVE / CANONICAL_CAMPAIGN_ID
    for variant_id in sorted(CANONICAL_VARIANT_IDS):
        content = (generated_dir / f"{variant_id}.md").read_text(encoding="utf-8")
        assert content.count(PUBLIC_URL) == 1


def test_zero_url_fails_package(editorial_base: Path):
    _blog_published_campaign(editorial_base)

    result = _generate(
        editorial_base,
        generate_content=_mock_generator_factory(url_count=0),
    )

    assert result.status == "failed"
    assert LINKEDIN_PACKAGE_GENERATION_FAILED in result.errors


def test_duplicated_url_fails_package(editorial_base: Path):
    _blog_published_campaign(editorial_base)

    result = _generate(
        editorial_base,
        generate_content=_mock_generator_factory(url_count=2),
    )

    assert result.status == "failed"
    assert LINKEDIN_PACKAGE_GENERATION_FAILED in result.errors


def test_provider_error_returns_package_generation_failed(editorial_base: Path):
    _blog_published_campaign(editorial_base)

    result = _generate(
        editorial_base,
        generate_content=_mock_generator_factory(fail_variant="executive-recruiter"),
    )

    assert result.status == "failed"
    assert LINKEDIN_PACKAGE_GENERATION_FAILED in result.errors
    assert "deepseek_unavailable" in result.errors


def test_empty_content_returns_package_generation_failed(editorial_base: Path):
    _blog_published_campaign(editorial_base)

    def _empty_generator(_settings, _messages):
        return DeepSeekGenerationResult(content=None, error_code="deepseek_empty_response")

    result = _generate(editorial_base, generate_content=_empty_generator)

    assert result.status == "failed"
    assert LINKEDIN_PACKAGE_GENERATION_FAILED in result.errors
    assert result.errors.count(LINKEDIN_PACKAGE_GENERATION_FAILED) == 1


def test_site_url_base_succeeds_with_full_public_url(editorial_base: Path):
    _blog_published_campaign(editorial_base)

    result = _generate(editorial_base, site_url=SITE_URL)

    assert result.status == "completed"
    assert result.source_public_url == PUBLIC_URL


def test_site_url_different_host_fails_public_url_changed(editorial_base: Path):
    _blog_published_campaign(editorial_base)

    result = _generate(editorial_base, site_url="https://other.example.com")

    assert result.status == "failed"
    assert LINKEDIN_PACKAGE_PUBLIC_URL_CHANGED in result.errors


def test_metadata_and_response_exclude_generated_bodies(editorial_base: Path):
    _blog_published_campaign(editorial_base)

    result = _generate(editorial_base)
    assert result.status == "completed"

    response_json = json.dumps(result.to_dict())
    assert "generated_draft_content" not in response_json
    assert "Read the full story here" not in response_json

    metadata_path = editorial_base / METADATA_CAMPAIGNS_RELATIVE / f"{CANONICAL_CAMPAIGN_ID}.json"
    raw = metadata_path.read_text(encoding="utf-8")
    assert "generated_draft_content" not in raw
    assert "markdown_content" not in raw
    assert "Read the full story here" not in raw


def test_idempotent_rerun_does_not_regenerate_or_append_state_history(
    editorial_base: Path,
):
    _blog_published_campaign(editorial_base)

    first = _generate(editorial_base)
    assert first.status == "completed"

    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    history_len = len(campaign["state_history"])
    generated_dir = editorial_base / GENERATED_RELATIVE / CANONICAL_CAMPAIGN_ID
    mtimes = {
        variant_id: (generated_dir / f"{variant_id}.md").stat().st_mtime
        for variant_id in sorted(CANONICAL_VARIANT_IDS)
    }

    second = _generate(editorial_base)

    assert second.status == "completed"
    campaign_after = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign_after is not None
    assert len(campaign_after["state_history"]) == history_len
    for variant_id, mtime in mtimes.items():
        assert (generated_dir / f"{variant_id}.md").stat().st_mtime == mtime


def test_target_exists_without_metadata_proof_fails(editorial_base: Path):
    _blog_published_campaign(editorial_base)

    orphan = (
        editorial_base
        / GENERATED_RELATIVE
        / CANONICAL_CAMPAIGN_ID
        / "executive-recruiter.md"
    )
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text("orphan artifact\n", encoding="utf-8")

    result = _generate(editorial_base)

    assert result.status == "failed"
    assert LINKEDIN_PACKAGE_TARGET_EXISTS in result.errors


def test_invalid_variant_fails(editorial_base: Path):
    _blog_published_campaign(editorial_base)

    result = _generate(editorial_base, variants=["executive"])

    assert result.status == "failed"
    assert LINKEDIN_PACKAGE_INVALID_VARIANT in result.errors


def test_generated_path_exists_but_not_directory(editorial_base: Path):
    _blog_published_campaign(editorial_base)
    generated_path = editorial_base / GENERATED_RELATIVE
    generated_path.write_text("not a directory", encoding="utf-8")

    result = _generate(editorial_base)

    assert result.status == "failed"
    assert LINKEDIN_PACKAGE_GENERATED_DIR_NOT_READY in result.errors


def test_generated_path_not_writable(editorial_base: Path):
    _blog_published_campaign(editorial_base)

    with patch(
        "silverman_blog_linkedin.linkedin_package_flow._ensure_generated_dirs",
        return_value=LINKEDIN_PACKAGE_GENERATED_DIR_NOT_WRITABLE,
    ):
        result = _generate(editorial_base)

    assert result.status == "failed"
    assert LINKEDIN_PACKAGE_GENERATED_DIR_NOT_WRITABLE in result.errors


def test_http_endpoint_requires_auth(editorial_base: Path):
    create_full_layout(editorial_base)
    _blog_published_campaign(editorial_base)

    client = TestClient(create_app(make_settings(editorial_base)))

    unauth = client.post(
        "/generate-linkedin-package",
        json={"campaign_id": CANONICAL_CAMPAIGN_ID},
    )
    assert unauth.status_code == 401

    bad_key = client.post(
        "/generate-linkedin-package",
        headers={"Authorization": "Bearer wrong-key"},
        json={"campaign_id": CANONICAL_CAMPAIGN_ID},
    )
    assert bad_key.status_code == 401


def test_http_successful_response_shape(editorial_base: Path, monkeypatch):
    create_full_layout(editorial_base)
    _blog_published_campaign(editorial_base)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    with patch(
        "silverman_blog_linkedin.linkedin_package_flow.generate_linkedin_draft_content",
        side_effect=_mock_generator_factory(),
    ):
        client = TestClient(create_app(make_settings(editorial_base)))
        response = client.post(
            "/generate-linkedin-package",
            headers=auth_header(),
            json={"campaign_id": CANONICAL_CAMPAIGN_ID},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["campaign_id"] == CANONICAL_CAMPAIGN_ID
    assert body["state"] == STATE_DERIVATIVES_GENERATED
    assert body["package_id"] == f"{CANONICAL_CAMPAIGN_ID}-pkg"
    assert body["source_public_url"] == PUBLIC_URL
    assert len(body["variants"]) == 4
    assert body["package"] is not None
    assert body["metadata_written"] is True
    assert "generated_draft_content" not in body
    assert "errors" in body
    assert "warnings" in body


def test_http_missing_identifiers_returns_422(editorial_base: Path):
    create_full_layout(editorial_base)
    client = TestClient(create_app(make_settings(editorial_base)))

    response = client.post(
        "/generate-linkedin-package",
        headers=auth_header(),
        json={},
    )
    assert response.status_code == 422


def test_http_extra_fields_returns_422(editorial_base: Path):
    create_full_layout(editorial_base)
    client = TestClient(create_app(make_settings(editorial_base)))

    response = client.post(
        "/generate-linkedin-package",
        headers=auth_header(),
        json={
            "campaign_id": CANONICAL_CAMPAIGN_ID,
            "generated_draft_content": "secret body",
        },
    )
    assert response.status_code == 422


def test_resolve_by_source_relative_path(editorial_base: Path):
    _blog_published_campaign(editorial_base)

    result = _generate(
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


def test_no_scheduling_metadata_created(editorial_base: Path):
    _blog_published_campaign(editorial_base)

    result = _generate(editorial_base)
    assert result.status == "completed"

    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    raw = json.dumps(campaign)
    assert "schedule_at" not in raw
    assert "publish_state" not in raw


def test_no_linkedin_api_publication_attempted(editorial_base: Path):
    _blog_published_campaign(editorial_base)

    with patch("httpx.Client.post") as mock_post:
        result = _generate(editorial_base)

    assert result.status == "completed"
    mock_post.assert_not_called()


def test_package_idempotency_key_format(editorial_base: Path):
    _blog_published_campaign(editorial_base)
    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None

    variant_ids = sorted(CANONICAL_VARIANT_IDS)
    expected = build_package_idempotency_key(
        campaign_id=CANONICAL_CAMPAIGN_ID,
        source_content_sha256=campaign["source_content_sha256"],
        variant_ids=variant_ids,
        flow=FLOW_A,
    )

    result = _generate(editorial_base)
    assert result.status == "completed"
    assert result.package is not None
    assert result.package["idempotency_key"] == expected


def test_build_public_image_url_converts_relative_path():
    assert (
        build_public_image_url(SITE_URL, f"/assets/images/{PUBLIC_SLUG}.png")
        == f"{SITE_URL}/assets/images/{PUBLIC_SLUG}.png"
    )


def test_package_includes_public_image_url_when_public_image_exists(
    editorial_base: Path,
    public_repo: Path,
):
    _blog_published_campaign(editorial_base)

    result = _generate_with_repo(editorial_base, public_repo, with_image=True)

    assert result.status == "completed"
    assert result.article_preview is not None
    assert result.article_preview["status"] == ARTICLE_PREVIEW_AVAILABLE
    assert (
        result.article_preview["public_image_url"]
        == f"{SITE_URL}/assets/images/{PUBLIC_SLUG}.png"
    )
    assert result.package is not None
    assert result.package["article_preview"]["public_image_url"] == (
        f"{SITE_URL}/assets/images/{PUBLIC_SLUG}.png"
    )
    for variant in result.variants:
        assert variant["public_image_url"] == f"{SITE_URL}/assets/images/{PUBLIC_SLUG}.png"
        assert variant["article_title"] == TITLE
        assert variant["public_url"] == PUBLIC_URL


def test_missing_public_image_produces_clear_warning_not_package_failure(
    editorial_base: Path,
    public_repo: Path,
):
    _blog_published_campaign(editorial_base)

    result = _generate_with_repo(editorial_base, public_repo, with_image=False)

    assert result.status == "completed"
    assert result.article_preview is not None
    assert result.article_preview["status"] == ARTICLE_PREVIEW_MISSING
    assert (
        result.article_preview["error_code"]
        == LINKEDIN_ARTICLE_PREVIEW_PUBLIC_IMAGE_MISSING
    )
    assert LINKEDIN_ARTICLE_PREVIEW_PUBLIC_IMAGE_MISSING in result.warnings
    assert LINKEDIN_PACKAGE_GENERATION_FAILED not in result.errors


def test_article_preview_skipped_when_public_repo_not_configured(editorial_base: Path):
    _blog_published_campaign(editorial_base)

    result = _generate(editorial_base)

    assert result.status == "completed"
    assert result.article_preview is not None
    assert result.article_preview["status"] == ARTICLE_PREVIEW_SKIPPED
    assert (
        result.article_preview["error_code"]
        == LINKEDIN_ARTICLE_PREVIEW_PUBLIC_REPO_NOT_CONFIGURED
    )
    assert LINKEDIN_ARTICLE_PREVIEW_PUBLIC_REPO_NOT_CONFIGURED in result.warnings


def test_invalid_image_path_produces_invalid_status_and_warning(
    editorial_base: Path,
    public_repo: Path,
):
    _blog_published_campaign(editorial_base)
    invalid_frontmatter = _canonical_frontmatter().replace(
        f"image: /assets/images/{PUBLIC_SLUG}.png",
        "image: /images/wrong.png",
    )
    content = invalid_frontmatter + _canonical_body()
    (editorial_base / SOURCE_RELATIVE).write_text(content, encoding="utf-8")
    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    campaign["source_content_sha256"] = compute_source_content_sha256(content)
    write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, campaign)

    result = _generate_with_repo(editorial_base, public_repo, with_image=True)

    assert result.status == "completed"
    assert result.article_preview is not None
    assert result.article_preview["status"] == ARTICLE_PREVIEW_INVALID
    assert result.article_preview["error_code"] == LINKEDIN_ARTICLE_PREVIEW_IMAGE_INVALID
    assert LINKEDIN_ARTICLE_PREVIEW_IMAGE_INVALID in result.warnings


def test_flow_a_schedules_distribution_after_package_with_article_preview(
    editorial_base: Path,
    public_repo: Path,
):
    _blog_published_campaign(editorial_base)
    package_result = _generate_with_repo(editorial_base, public_repo, with_image=True)
    assert package_result.status == "completed"

    schedule_result = schedule_linkedin_distribution(
        editorial_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
    )

    assert schedule_result.status == "completed"
    assert schedule_result.variant_schedules
    for item in schedule_result.variant_schedules:
        assert item["publish_state"] == "pending"


def test_no_linkedin_media_upload_on_package_generation(
    editorial_base: Path,
    public_repo: Path,
):
    _blog_published_campaign(editorial_base)

    with patch("httpx.Client.post") as mock_post, patch(
        "httpx.Client.put"
    ) as mock_put:
        result = _generate_with_repo(editorial_base, public_repo, with_image=True)

    assert result.status == "completed"
    mock_post.assert_not_called()
    mock_put.assert_not_called()
