"""Tests for blog image generation orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from silverman_blog_linkedin.blog_image_generation import (
    BLOG_IMAGE_GENERATION_COMFYUI_FAILED,
    BLOG_IMAGE_GENERATION_FAILED,
    SKIP_REASON_GENERATION_DISABLED,
    SKIP_REASON_NON_CANONICAL_IMAGE,
    ensure_blog_image,
)
from silverman_blog_linkedin.campaign_lifecycle import (
    METADATA_CAMPAIGNS_RELATIVE,
    write_campaign_metadata,
)
from silverman_blog_linkedin.comfyui_client import FakeComfyUIClient
from silverman_blog_linkedin.comfyui_config import (
    ComfyUISettings,
    ComfyUISettingsLoadResult,
)

SOURCE_SLUG = "01-why-i-did-not-start-with-the-database"
PUBLIC_SLUG = "why-i-did-not-start-with-the-database"
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


def _enabled_config(*, dry_run: bool = False) -> ComfyUISettingsLoadResult:
    return ComfyUISettingsLoadResult(
        settings=ComfyUISettings(
            enabled=True,
            base_url="http://127.0.0.1:8188",
            api_prefix="",
            api_key=None,
            auth_header_name="Authorization",
            extra_data_api_key_field=None,
            workflow_path=Path(__file__).resolve().parents[1]
            / "prompts"
            / "comfyui"
            / "blog-image-workflow.json",
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


def test_missing_image_generates_png_and_patches_frontmatter(editorial_base: Path):
    _write_post(editorial_base, image=None, with_png=False)
    fake = FakeComfyUIClient()

    result = ensure_blog_image(
        editorial_base,
        SOURCE_RELATIVE,
        config=_enabled_config(),
        client=fake,
    )

    assert result.status == "generated"
    assert (editorial_base / IMAGE_RELATIVE).is_file()
    content = (editorial_base / SOURCE_RELATIVE).read_text(encoding="utf-8")
    assert f"image: /assets/images/{PUBLIC_SLUG}.png" in content
    assert result.prompt_hash is not None
    assert len(fake.calls) == 1


def test_existing_valid_image_and_png_skips(editorial_base: Path):
    _write_post(editorial_base, image="canonical", with_png=True)
    fake = FakeComfyUIClient()

    result = ensure_blog_image(
        editorial_base,
        SOURCE_RELATIVE,
        config=_enabled_config(),
        client=fake,
    )

    assert result.status == "skipped"
    assert result.skip_reason == "already_valid"
    assert fake.calls == []


def test_canonical_image_missing_png_generates_png_only(editorial_base: Path):
    _write_post(editorial_base, image="canonical", with_png=False)
    fake = FakeComfyUIClient()

    result = ensure_blog_image(
        editorial_base,
        SOURCE_RELATIVE,
        config=_enabled_config(),
        client=fake,
    )

    assert result.status == "generated"
    assert (editorial_base / IMAGE_RELATIVE).is_file()
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

    result = ensure_blog_image(editorial_base, SOURCE_RELATIVE)

    assert result.status == "skipped"
    assert result.skip_reason == SKIP_REASON_GENERATION_DISABLED
    assert not (editorial_base / IMAGE_RELATIVE).exists()


def test_comfyui_failure_returns_failed(editorial_base: Path):
    _write_post(editorial_base, image=None, with_png=False)
    fake = FakeComfyUIClient(error_code=BLOG_IMAGE_GENERATION_COMFYUI_FAILED)

    result = ensure_blog_image(
        editorial_base,
        SOURCE_RELATIVE,
        config=_enabled_config(),
        client=fake,
    )

    assert result.status == "failed"
    assert result.error_code == BLOG_IMAGE_GENERATION_COMFYUI_FAILED
    assert not (editorial_base / IMAGE_RELATIVE).exists()


def test_dry_run_has_no_file_writes_or_http_calls(editorial_base: Path):
    _write_post(editorial_base, image=None, with_png=False)
    fake = FakeComfyUIClient()

    result = ensure_blog_image(
        editorial_base,
        SOURCE_RELATIVE,
        config=_enabled_config(dry_run=True),
        client=fake,
        dry_run=True,
    )

    assert result.status == "dry_run"
    assert result.prompt_hash is not None
    assert not (editorial_base / IMAGE_RELATIVE).exists()
    assert fake.calls == []
    original = (editorial_base / SOURCE_RELATIVE).read_text(encoding="utf-8")
    assert "image:" not in original


def test_metadata_recorded_on_campaign(editorial_base: Path):
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
    )

    assert result.status == "generated"
    assert result.metadata_written is True
    from silverman_blog_linkedin.campaign_lifecycle import read_campaign_metadata

    campaign = read_campaign_metadata(editorial_base, campaign_id)
    assert campaign is not None
    assert campaign["blog_image_generation"]["status"] == "generated"
    assert campaign["blog_image_generation"]["prompt_hash"] == result.prompt_hash


def test_run_metadata_written_on_generation(editorial_base: Path):
    _write_post(editorial_base, image=None, with_png=False)

    result = ensure_blog_image(
        editorial_base,
        SOURCE_RELATIVE,
        config=_enabled_config(),
        client=FakeComfyUIClient(),
    )

    assert result.run_id is not None
    run_path = editorial_base / "metadata" / "runs" / f"{result.run_id}.json"
    assert run_path.is_file()


def test_missing_source_returns_failed(editorial_base: Path):
    result = ensure_blog_image(
        editorial_base,
        "blog-posts/ready/does-not-exist.md",
        config=_enabled_config(),
        client=FakeComfyUIClient(),
    )

    assert result.status == "failed"
    assert result.error_code == BLOG_IMAGE_GENERATION_FAILED
