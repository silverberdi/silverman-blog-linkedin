"""Tests for blog image generation orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from silverman_blog_linkedin.blog_image_generation import (
    BLOG_IMAGE_GENERATION_COMFYUI_FAILED,
    BLOG_IMAGE_GENERATION_FAILED,
    SKIP_REASON_GENERATION_DISABLED,
    SKIP_REASON_NON_CANONICAL_IMAGE,
    SKIP_REASON_PUBLIC_ASSET_REUSE,
    WARNING_READY_SIBLING_BACKFILL_FAILED,
    ensure_blog_image,
)
from silverman_blog_linkedin.github_pages_publish import (
    BLOG_IMAGE_PUBLIC_ASSET_HANDOFF_FAILED,
    copy_public_blog_image,
)
from silverman_blog_linkedin.campaign_lifecycle import (
    METADATA_CAMPAIGNS_RELATIVE,
    write_campaign_metadata,
)
from silverman_blog_linkedin.comfyui_client import FakeComfyUIClient
from silverman_blog_linkedin.comfyui_config import (
    ComfyUISettings,
    ComfyUISettingsLoadResult,
    LOCAL_WORKFLOW_PATH,
    load_comfyui_settings,
)

SOURCE_SLUG = "01-why-i-did-not-start-with-the-database"
PUBLIC_SLUG = "why-i-did-not-start-with-the-database"
POST_02_SOURCE_SLUG = "02-deferring-is-not-avoiding-it-can-be-architecture"
POST_02_PUBLIC_SLUG = "deferring-is-not-avoiding-it-can-be-architecture"
PUBLICATION_DATE = "2026-07-06"
SOURCE_RELATIVE = f"blog-posts/ready/{SOURCE_SLUG}.md"
IMAGE_RELATIVE = f"blog-posts/ready/{SOURCE_SLUG}.png"
TITLE = "Why I Did Not Start With the Database"


def _frontmatter(*, image: str | None = "/assets/images/placeholder.png") -> str:
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
    if image is not None:
        lines.append(f"image: {image}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def _body() -> str:
    return (
        f"# {TITLE}\n\n"
        "The real problem is not persistence. The real problem is naming the business too late.\n"
    )


def _write_post(
    base: Path,
    *,
    image: str | None = None,
    with_png: bool = False,
) -> Path:
    ready = base / "blog-posts" / "ready"
    ready.mkdir(parents=True, exist_ok=True)
    md_path = ready / f"{SOURCE_SLUG}.md"
    if image is None:
        fm = _frontmatter(image=None)
    elif image == "canonical":
        fm = _frontmatter(image=f"/assets/images/{PUBLIC_SLUG}.png")
    else:
        fm = _frontmatter(image=image)
    md_path.write_text(fm + _body(), encoding="utf-8")
    if with_png:
        (ready / f"{SOURCE_SLUG}.png").write_bytes(b"\x89PNG\r\n\x1a\nexisting")
    return md_path


def _disabled_config() -> ComfyUISettingsLoadResult:
    return load_comfyui_settings({})


def _enabled_config(*, dry_run: bool = False) -> ComfyUISettingsLoadResult:
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


@pytest.fixture
def editorial_base(tmp_path: Path) -> Path:
    (tmp_path / "metadata" / "runs").mkdir(parents=True)
    (tmp_path / METADATA_CAMPAIGNS_RELATIVE).mkdir(parents=True)
    return tmp_path


@pytest.fixture
def public_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "public-repo"
    (repo / "_posts").mkdir(parents=True)
    (repo / "assets/images").mkdir(parents=True)
    return repo


def _publish_env(editorial_base: Path, repo_path: Path) -> dict[str, str]:
    return {
        "SILVERMAN_BLOG_LINKEDIN_BASE_PATH": str(editorial_base),
        "SILVERMAN_GITHUB_PAGES_REPO_PATH": str(repo_path),
    }


def test_missing_image_generates_png_and_patches_frontmatter(
    editorial_base: Path, public_repo: Path
):
    _write_post(editorial_base, image=None, with_png=False)
    fake = FakeComfyUIClient()

    result = ensure_blog_image(
        editorial_base,
        SOURCE_RELATIVE,
        config=_enabled_config(),
        client=fake,
        github_pages_repo_path=public_repo,
        environ=_publish_env(editorial_base, public_repo),
    )

    assert result.status == "generated"
    assert (editorial_base / IMAGE_RELATIVE).is_file()
    assert (public_repo / "assets/images" / f"{PUBLIC_SLUG}.png").is_file()
    content = (editorial_base / SOURCE_RELATIVE).read_text(encoding="utf-8")
    assert f"image: /assets/images/{PUBLIC_SLUG}.png" in content
    assert result.prompt_hash is not None
    assert result.public_asset_handoff_status == "copied"
    assert result.public_asset_source == "comfyui_generated"
    assert len(fake.calls) == 1


def test_existing_valid_image_and_png_skips(editorial_base: Path, public_repo: Path):
    _write_post(editorial_base, image="canonical", with_png=True)
    (public_repo / "assets/images" / f"{PUBLIC_SLUG}.png").write_bytes(
        b"\x89PNG\r\n\x1a\nexisting"
    )
    fake = FakeComfyUIClient()

    result = ensure_blog_image(
        editorial_base,
        SOURCE_RELATIVE,
        config=_enabled_config(),
        client=fake,
        github_pages_repo_path=public_repo,
        environ=_publish_env(editorial_base, public_repo),
    )

    assert result.status == "skipped"
    assert result.skip_reason == "already_valid"
    assert result.public_asset_handoff_status == "reused"
    assert fake.calls == []


def test_canonical_image_missing_png_generates_png_only(
    editorial_base: Path, public_repo: Path
):
    _write_post(editorial_base, image="canonical", with_png=False)
    fake = FakeComfyUIClient()

    result = ensure_blog_image(
        editorial_base,
        SOURCE_RELATIVE,
        config=_enabled_config(),
        client=fake,
        github_pages_repo_path=public_repo,
        environ=_publish_env(editorial_base, public_repo),
    )

    assert result.status == "generated"
    assert (editorial_base / IMAGE_RELATIVE).is_file()
    assert (public_repo / "assets/images" / f"{PUBLIC_SLUG}.png").is_file()
    assert len(fake.calls) == 1


def test_non_canonical_image_path_does_not_generate(editorial_base: Path):
    _write_post(editorial_base, image="/assets/images/wrong-slug.png", with_png=False)
    fake = FakeComfyUIClient()

    result = ensure_blog_image(
        editorial_base,
        SOURCE_RELATIVE,
        config=_enabled_config(),
        client=fake,
    )

    assert result.status == "skipped"
    assert result.skip_reason == SKIP_REASON_NON_CANONICAL_IMAGE
    assert not (editorial_base / IMAGE_RELATIVE).exists()
    assert fake.calls == []


def test_disabled_generation_preserves_old_behavior(editorial_base: Path):
    _write_post(editorial_base, image=None, with_png=False)

    result = ensure_blog_image(
        editorial_base,
        SOURCE_RELATIVE,
        config=_disabled_config(),
        environ={},
    )

    assert result.status == "skipped"
    assert result.skip_reason == SKIP_REASON_GENERATION_DISABLED
    assert not (editorial_base / IMAGE_RELATIVE).exists()


def test_disabled_generation_ignores_ambient_comfyui_env(
    editorial_base: Path, monkeypatch: pytest.MonkeyPatch
):
    """Explicit empty environ must not inherit operator Comfy Cloud exports."""
    monkeypatch.setenv("SILVERMAN_COMFYUI_IMAGE_ENABLED", "true")
    monkeypatch.setenv("SILVERMAN_COMFYUI_BASE_URL", "https://cloud.comfy.org")
    monkeypatch.setenv("SILVERMAN_COMFYUI_API_PREFIX", "/api")
    monkeypatch.setenv("SILVERMAN_COMFYUI_API_KEY", "ambient-secret-key")
    _write_post(editorial_base, image=None, with_png=False)

    result = ensure_blog_image(
        editorial_base,
        SOURCE_RELATIVE,
        config=_disabled_config(),
        environ={},
        client=FakeComfyUIClient(),
    )

    assert result.status == "skipped"
    assert result.skip_reason == SKIP_REASON_GENERATION_DISABLED
    assert not (editorial_base / IMAGE_RELATIVE).exists()


def test_comfyui_failure_returns_failed(editorial_base: Path, public_repo: Path):
    _write_post(editorial_base, image=None, with_png=False)
    fake = FakeComfyUIClient(error_code=BLOG_IMAGE_GENERATION_COMFYUI_FAILED)

    result = ensure_blog_image(
        editorial_base,
        SOURCE_RELATIVE,
        config=_enabled_config(),
        client=fake,
        github_pages_repo_path=public_repo,
        environ=_publish_env(editorial_base, public_repo),
    )

    assert result.status == "failed"
    assert result.error_code == BLOG_IMAGE_GENERATION_COMFYUI_FAILED
    assert not (editorial_base / IMAGE_RELATIVE).exists()


def test_dry_run_has_no_file_writes_or_http_calls(editorial_base: Path, public_repo: Path):
    _write_post(editorial_base, image=None, with_png=False)
    fake = FakeComfyUIClient()

    result = ensure_blog_image(
        editorial_base,
        SOURCE_RELATIVE,
        config=_enabled_config(dry_run=True),
        client=fake,
        dry_run=True,
        github_pages_repo_path=public_repo,
        environ=_publish_env(editorial_base, public_repo),
    )

    assert result.status == "dry_run"
    assert result.prompt_hash is not None
    assert result.public_repo_image_relative_path == f"assets/images/{PUBLIC_SLUG}.png"
    assert not (editorial_base / IMAGE_RELATIVE).exists()
    assert not (public_repo / "assets/images" / f"{PUBLIC_SLUG}.png").exists()
    assert fake.calls == []
    original = (editorial_base / SOURCE_RELATIVE).read_text(encoding="utf-8")
    assert "image:" not in original


def test_metadata_recorded_on_campaign(editorial_base: Path, public_repo: Path):
    _write_post(editorial_base, image=None, with_png=False)
    campaign_id = f"flow-a-{PUBLICATION_DATE}-{PUBLIC_SLUG}"
    write_campaign_metadata(
        editorial_base,
        campaign_id,
        {"campaign_id": campaign_id, "state": "ready"},
    )

    result = ensure_blog_image(
        editorial_base,
        SOURCE_RELATIVE,
        config=_enabled_config(),
        client=FakeComfyUIClient(),
        campaign_id=campaign_id,
        github_pages_repo_path=public_repo,
        environ=_publish_env(editorial_base, public_repo),
    )

    assert result.status == "generated"
    assert result.metadata_written is True
    from silverman_blog_linkedin.campaign_lifecycle import read_campaign_metadata

    campaign = read_campaign_metadata(editorial_base, campaign_id)
    assert campaign is not None
    assert campaign["blog_image_generation"]["status"] == "generated"
    assert campaign["blog_image_generation"]["prompt_hash"] == result.prompt_hash


def test_run_metadata_written_on_generation(editorial_base: Path, public_repo: Path):
    _write_post(editorial_base, image=None, with_png=False)

    result = ensure_blog_image(
        editorial_base,
        SOURCE_RELATIVE,
        config=_enabled_config(),
        client=FakeComfyUIClient(),
        github_pages_repo_path=public_repo,
        environ=_publish_env(editorial_base, public_repo),
    )

    assert result.run_id is not None
    run_path = editorial_base / "metadata" / "runs" / f"{result.run_id}.json"
    assert run_path.is_file()


def test_openai_workflow_metadata_without_dimension_bindings(
    editorial_base: Path,
):
    from silverman_blog_linkedin.comfyui_config import DEFAULT_WORKFLOW_PATH

    _write_post(editorial_base, image=None, with_png=False)
    config = ComfyUISettingsLoadResult(
        settings=ComfyUISettings(
            enabled=True,
            base_url="https://cloud.comfy.org",
            api_prefix="/api",
            api_key=None,
            auth_header_name="Authorization",
            extra_data_api_key_field=None,
            workflow_path=DEFAULT_WORKFLOW_PATH,
            timeout_seconds=30,
            image_width=1200,
            image_height=900,
            dry_run=True,
        )
    )

    result = ensure_blog_image(
        editorial_base,
        SOURCE_RELATIVE,
        config=config,
        client=FakeComfyUIClient(),
        dry_run=True,
    )

    assert result.status == "dry_run"
    assert result.width == 1200
    assert result.height == 900
    assert result.workflow_controls_dimensions is False


def test_local_workflow_metadata_has_dimension_bindings(editorial_base: Path):
    _write_post(editorial_base, image=None, with_png=False)

    result = ensure_blog_image(
        editorial_base,
        SOURCE_RELATIVE,
        config=_enabled_config(dry_run=True),
        client=FakeComfyUIClient(),
        dry_run=True,
    )

    assert result.workflow_controls_dimensions is True


def test_missing_source_returns_failed(editorial_base: Path, public_repo: Path):
    result = ensure_blog_image(
        editorial_base,
        "blog-posts/ready/does-not-exist.md",
        config=_enabled_config(),
        client=FakeComfyUIClient(),
        github_pages_repo_path=public_repo,
    )

    assert result.status == "failed"
    assert result.error_code == BLOG_IMAGE_GENERATION_FAILED


def test_public_asset_exists_backfill_succeeds_no_comfyui(
    editorial_base: Path, public_repo: Path
):
    _write_post(editorial_base, image="canonical", with_png=False)
    public_png = public_repo / "assets/images" / f"{PUBLIC_SLUG}.png"
    public_png.write_bytes(b"\x89PNG\r\n\x1a\npublic-asset")
    fake = FakeComfyUIClient()

    result = ensure_blog_image(
        editorial_base,
        SOURCE_RELATIVE,
        config=_enabled_config(),
        client=fake,
        github_pages_repo_path=public_repo,
        environ=_publish_env(editorial_base, public_repo),
    )

    assert result.status == "skipped"
    assert result.skip_reason == SKIP_REASON_PUBLIC_ASSET_REUSE
    assert result.ready_sibling_backfill_status == "copied"
    assert (editorial_base / IMAGE_RELATIVE).read_bytes() == public_png.read_bytes()
    assert fake.calls == []


def test_public_asset_exists_backfill_fails_warning_no_handoff_error(
    editorial_base: Path, public_repo: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_post(editorial_base, image="canonical", with_png=False)
    public_png = public_repo / "assets/images" / f"{PUBLIC_SLUG}.png"
    public_png.write_bytes(b"\x89PNG\r\n\x1a\npublic-asset")
    ready_dir = editorial_base / "blog-posts" / "ready"
    ready_dir.chmod(0o555)
    fake = FakeComfyUIClient()

    try:
        result = ensure_blog_image(
            editorial_base,
            SOURCE_RELATIVE,
            config=_enabled_config(),
            client=fake,
            github_pages_repo_path=public_repo,
            environ=_publish_env(editorial_base, public_repo),
        )
    finally:
        ready_dir.chmod(0o755)

    assert result.status == "skipped"
    assert result.error_code is None
    assert BLOG_IMAGE_PUBLIC_ASSET_HANDOFF_FAILED not in (result.error_code,)
    assert result.ready_sibling_backfill_status == "failed"
    assert WARNING_READY_SIBLING_BACKFILL_FAILED in result.warnings
    assert fake.calls == []


def test_ready_sibling_adopts_to_public_asset_no_comfyui(
    editorial_base: Path, public_repo: Path
):
    _write_post(editorial_base, image="canonical", with_png=True)
    fake = FakeComfyUIClient()

    result = ensure_blog_image(
        editorial_base,
        SOURCE_RELATIVE,
        config=_enabled_config(),
        client=fake,
        github_pages_repo_path=public_repo,
        environ=_publish_env(editorial_base, public_repo),
    )

    assert result.status == "generated"
    assert result.public_asset_handoff_status == "copied"
    assert result.public_asset_source == "ready_sibling_png"
    assert (public_repo / "assets/images" / f"{PUBLIC_SLUG}.png").is_file()
    assert fake.calls == []


def test_ready_sibling_handoff_failure_returns_stable_error(
    editorial_base: Path, public_repo: Path,
):
    _write_post(editorial_base, image="canonical", with_png=True)
    images_dir = public_repo / "assets/images"
    images_dir.chmod(0o555)
    fake = FakeComfyUIClient()

    try:
        result = ensure_blog_image(
            editorial_base,
            SOURCE_RELATIVE,
            config=_enabled_config(),
            client=fake,
            github_pages_repo_path=public_repo,
            environ=_publish_env(editorial_base, public_repo),
        )
    finally:
        images_dir.chmod(0o755)

    assert result.status == "failed"
    assert result.error_code == BLOG_IMAGE_PUBLIC_ASSET_HANDOFF_FAILED
    assert fake.calls == []


def test_retry_after_local_sibling_adopts_public_asset(
    editorial_base: Path, public_repo: Path
):
    _write_post(editorial_base, image="canonical", with_png=True)
    fake = FakeComfyUIClient()

    first = ensure_blog_image(
        editorial_base,
        SOURCE_RELATIVE,
        config=_enabled_config(),
        client=fake,
        github_pages_repo_path=public_repo,
        environ=_publish_env(editorial_base, public_repo),
    )
    second = ensure_blog_image(
        editorial_base,
        SOURCE_RELATIVE,
        config=_enabled_config(),
        client=fake,
        github_pages_repo_path=public_repo,
        environ=_publish_env(editorial_base, public_repo),
    )

    assert first.status == "generated"
    assert second.status == "skipped"
    assert second.skip_reason == "already_valid"
    assert fake.calls == []


def test_retry_after_public_asset_exists_skips_comfyui(
    editorial_base: Path, public_repo: Path
):
    _write_post(editorial_base, image="canonical", with_png=True)
    (public_repo / "assets/images" / f"{PUBLIC_SLUG}.png").write_bytes(
        b"\x89PNG\r\n\x1a\nexisting"
    )
    fake = FakeComfyUIClient()

    result = ensure_blog_image(
        editorial_base,
        SOURCE_RELATIVE,
        config=_enabled_config(),
        client=fake,
        github_pages_repo_path=public_repo,
        environ=_publish_env(editorial_base, public_repo),
    )

    assert result.status == "skipped"
    assert result.skip_reason == "already_valid"
    assert fake.calls == []


def _write_post_02(base: Path, *, with_png: bool = True) -> Path:
    ready = base / "blog-posts" / "ready"
    ready.mkdir(parents=True, exist_ok=True)
    md_path = ready / f"{POST_02_SOURCE_SLUG}.md"
    fm = _frontmatter(image=f"/assets/images/{POST_02_PUBLIC_SLUG}.png")
    md_path.write_text(fm + _body(), encoding="utf-8")
    if with_png:
        (ready / f"{POST_02_SOURCE_SLUG}.png").write_bytes(
            b"\x89PNG\r\n\x1a\npost-02-sibling"
        )
    return md_path


def test_post_02_regression_adopts_sibling_to_public_asset(
    editorial_base: Path, public_repo: Path
):
    _write_post_02(editorial_base, with_png=True)
    source_relative = f"blog-posts/ready/{POST_02_SOURCE_SLUG}.md"
    fake = FakeComfyUIClient()

    result = ensure_blog_image(
        editorial_base,
        source_relative,
        config=_enabled_config(),
        client=fake,
        github_pages_repo_path=public_repo,
        environ=_publish_env(editorial_base, public_repo),
    )

    assert result.status == "generated"
    assert result.public_asset_handoff_status == "copied"
    assert result.public_asset_source == "ready_sibling_png"
    public_path = public_repo / "assets/images" / f"{POST_02_PUBLIC_SLUG}.png"
    assert public_path.is_file()
    assert public_path.read_bytes() == (
        editorial_base / "blog-posts/ready" / f"{POST_02_SOURCE_SLUG}.png"
    ).read_bytes()
    assert fake.calls == []


def test_copy_public_blog_image_success_and_permissions(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "_posts").mkdir(parents=True)
    (repo / "assets/images").mkdir(parents=True)
    source = tmp_path / "source.png"
    source.write_bytes(b"\x89PNG\r\n\x1a\nhandoff")

    result = copy_public_blog_image(source, repo, PUBLIC_SLUG)

    assert result.status == "copied"
    target = repo / "assets/images" / f"{PUBLIC_SLUG}.png"
    assert target.is_file()
    assert target.read_bytes() == source.read_bytes()
    assert oct(target.stat().st_mode & 0o777) == oct(0o644)


def test_copy_public_blog_image_refuses_overwrite(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "_posts").mkdir(parents=True)
    (repo / "assets/images").mkdir(parents=True)
    existing = repo / "assets/images" / f"{PUBLIC_SLUG}.png"
    existing.write_bytes(b"existing")
    source = tmp_path / "source.png"
    source.write_bytes(b"\x89PNG\r\n\x1a\nnew")

    result = copy_public_blog_image(source, repo, PUBLIC_SLUG)

    assert result.status == "reused"
    assert existing.read_bytes() == b"existing"


def test_copy_public_blog_image_missing_layout_fails(tmp_path: Path):
    repo = tmp_path / "repo"
    source = tmp_path / "source.png"
    source.write_bytes(b"\x89PNG\r\n\x1a\nhandoff")

    result = copy_public_blog_image(source, repo, PUBLIC_SLUG)

    assert result.status == "failed"
    assert result.error_message is not None
