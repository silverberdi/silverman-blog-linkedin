"""Tests for GitHub Pages blog publishing helper."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

from silverman_blog_linkedin.github_pages_publish import (
    PublishError,
    apply_plan,
    build_plan,
    derive_public_slug,
    jekyll_date,
    load_config,
    main,
    prepare_frontmatter,
    public_url,
    render_markdown,
    resolve_public_slug,
    run_publish,
    target_paths,
    validate_slug,
)

FIXED_DATE = date(2026, 7, 6)
SLUG = "example-post"
SOURCE_SLUG_WITH_PREFIX = "01-why-i-did-not-start-with-the-database"
PUBLIC_SLUG_FROM_PREFIX = "why-i-did-not-start-with-the-database"


def _env(editorial_base: Path, repo_path: Path) -> dict[str, str]:
    return {
        "SILVERMAN_BLOG_LINKEDIN_BASE_PATH": str(editorial_base),
        "SILVERMAN_GITHUB_PAGES_REPO_PATH": str(repo_path),
        "SILVERMAN_SITE_URL": "https://silverman.pro",
    }


def _setup_editorial(editorial_base: Path, slug: str = SLUG) -> tuple[Path, Path]:
    ready = editorial_base / "blog-posts/ready"
    ready.mkdir(parents=True)
    md_path = ready / f"{slug}.md"
    png_path = ready / f"{slug}.png"
    md_path.write_text(
        "---\n"
        "title: Example Title\n"
        "categories:\n"
        "  - architecture\n"
        "tags:\n"
        "  - leadership\n"
        "description: A short description.\n"
        "---\n"
        "# Body\n\n"
        "Post content here.\n",
        encoding="utf-8",
    )
    png_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    return md_path, png_path


def _setup_repo(repo_path: Path) -> None:
    (repo_path / "_posts").mkdir(parents=True)
    (repo_path / "assets/images").mkdir(parents=True)


@pytest.mark.parametrize(
    "slug",
    [
        "example-post",
        "architect-solution-state-of-art",
        "post123",
    ],
)
def test_validate_slug_accepts_safe_slugs(slug: str) -> None:
    validate_slug(slug)


@pytest.mark.parametrize(
    "slug",
    [
        "",
        "Bad-Slug",
        "bad_slug",
        "../escape",
        "dot.slug",
        "trailing-",
        "-leading",
    ],
)
def test_validate_slug_rejects_unsafe_slugs(slug: str) -> None:
    with pytest.raises(PublishError):
        validate_slug(slug, label="source slug")


@pytest.mark.parametrize(
    ("source_slug", "expected_public_slug"),
    [
        (SOURCE_SLUG_WITH_PREFIX, PUBLIC_SLUG_FROM_PREFIX),
        ("02-another-post", "another-post"),
        ("example-post", "example-post"),
        ("123-post", "post"),
    ],
)
def test_derive_public_slug_strips_numeric_prefix(
    source_slug: str, expected_public_slug: str
) -> None:
    assert derive_public_slug(source_slug) == expected_public_slug


def test_resolve_public_slug_uses_override() -> None:
    assert (
        resolve_public_slug(SOURCE_SLUG_WITH_PREFIX, "custom-public-slug")
        == "custom-public-slug"
    )


def test_resolve_public_slug_rejects_unsafe_override() -> None:
    with pytest.raises(PublishError, match="unsafe public slug"):
        resolve_public_slug(SOURCE_SLUG_WITH_PREFIX, "Bad-Slug")


def test_numeric_prefix_source_uses_public_slug_for_targets(tmp_path: Path) -> None:
    editorial = tmp_path / "editorial"
    repo = tmp_path / "repo"
    _setup_editorial(editorial, slug=SOURCE_SLUG_WITH_PREFIX)
    _setup_repo(repo)

    plan = run_publish(
        SOURCE_SLUG_WITH_PREFIX,
        publication_date=FIXED_DATE,
        apply=False,
        environ=_env(editorial, repo),
    )

    assert plan.source_slug == SOURCE_SLUG_WITH_PREFIX
    assert plan.public_slug == PUBLIC_SLUG_FROM_PREFIX
    assert plan.post_relative == (
        f"_posts/2026-07-06-{PUBLIC_SLUG_FROM_PREFIX}.md"
    )
    assert plan.image_relative == f"assets/images/{PUBLIC_SLUG_FROM_PREFIX}.png"
    assert plan.public_url == (
        "https://silverman.pro/2026/07/06/"
        f"{PUBLIC_SLUG_FROM_PREFIX}/"
    )


def test_public_slug_override(tmp_path: Path) -> None:
    editorial = tmp_path / "editorial"
    repo = tmp_path / "repo"
    _setup_editorial(editorial, slug=SOURCE_SLUG_WITH_PREFIX)
    _setup_repo(repo)

    plan = run_publish(
        SOURCE_SLUG_WITH_PREFIX,
        publication_date=FIXED_DATE,
        apply=False,
        public_slug_override="custom-public-slug",
        environ=_env(editorial, repo),
    )

    assert plan.source_slug == SOURCE_SLUG_WITH_PREFIX
    assert plan.public_slug == "custom-public-slug"
    assert plan.post_relative == "_posts/2026-07-06-custom-public-slug.md"
    assert plan.image_relative == "assets/images/custom-public-slug.png"


def test_target_paths_with_explicit_date(tmp_path: Path) -> None:
    config = load_config(_env(tmp_path / "editorial", tmp_path / "repo"))
    post_target, image_target, post_relative, image_relative = target_paths(
        config, SLUG, FIXED_DATE
    )

    assert post_relative == "_posts/2026-07-06-example-post.md"
    assert image_relative == "assets/images/example-post.png"
    assert post_target.name == "2026-07-06-example-post.md"
    assert image_target.name == "example-post.png"


def test_public_url_generation() -> None:
    url = public_url("https://silverman.pro", FIXED_DATE, SLUG)
    assert url == "https://silverman.pro/2026/07/06/example-post/"


def test_frontmatter_image_path(tmp_path: Path) -> None:
    md_path = tmp_path / "source.md"
    md_path.write_text("---\ntitle: Keep Me\n---\nBody\n", encoding="utf-8")

    frontmatter, body = prepare_frontmatter(md_path, SLUG, FIXED_DATE)

    assert frontmatter["image"] == "/assets/images/example-post.png"
    assert frontmatter["layout"] == "post"
    assert frontmatter["title"] == "Keep Me"
    assert frontmatter["date"] == jekyll_date(FIXED_DATE)
    assert frontmatter["categories"] == []
    assert frontmatter["tags"] == []
    assert frontmatter["description"] == ""
    assert "status" not in frontmatter
    assert "subtitle" not in frontmatter
    assert body == "Body\n"


def test_status_draft_removed_from_published_frontmatter(tmp_path: Path) -> None:
    md_path = tmp_path / "source.md"
    md_path.write_text(
        "---\ntitle: Draft Post\nstatus: draft\n---\nBody\n",
        encoding="utf-8",
    )

    frontmatter, body = prepare_frontmatter(md_path, SLUG, FIXED_DATE)
    rendered = render_markdown(frontmatter, body)
    parsed = yaml.safe_load(rendered.split("---", 2)[1])

    assert "status" not in frontmatter
    assert "status" not in parsed
    assert parsed["title"] == "Draft Post"


def test_description_falls_back_to_subtitle(tmp_path: Path) -> None:
    md_path = tmp_path / "source.md"
    md_path.write_text(
        "---\ntitle: Post\nsubtitle: A concise editorial subtitle\n---\nBody\n",
        encoding="utf-8",
    )

    frontmatter, _ = prepare_frontmatter(md_path, SLUG, FIXED_DATE)

    assert frontmatter["description"] == "A concise editorial subtitle"
    assert "subtitle" not in frontmatter


def test_existing_description_not_replaced_by_subtitle(tmp_path: Path) -> None:
    md_path = tmp_path / "source.md"
    md_path.write_text(
        "---\ntitle: Post\ndescription: Keep this\nsubtitle: Ignore me\n---\nBody\n",
        encoding="utf-8",
    )

    frontmatter, _ = prepare_frontmatter(md_path, SLUG, FIXED_DATE)

    assert frontmatter["description"] == "Keep this"


def test_no_invented_description_without_subtitle(tmp_path: Path) -> None:
    md_path = tmp_path / "source.md"
    md_path.write_text(
        "---\ntitle: Post\n---\n"
        "Unsupported claims invented from body text should not appear.\n",
        encoding="utf-8",
    )

    frontmatter, _ = prepare_frontmatter(md_path, SLUG, FIXED_DATE)

    assert frontmatter["description"] == ""


def test_render_markdown_preserves_body() -> None:
    frontmatter = {
        "layout": "post",
        "title": "Example",
        "date": jekyll_date(FIXED_DATE),
        "categories": [],
        "tags": [],
        "description": "",
        "image": "/assets/images/example-post.png",
    }
    rendered = render_markdown(frontmatter, "Post content here.\n")
    assert "Post content here." in rendered
    parsed = yaml.safe_load(rendered.split("---", 2)[1])
    assert parsed["image"] == "/assets/images/example-post.png"


def test_dry_run_creates_no_files(tmp_path: Path) -> None:
    editorial = tmp_path / "editorial"
    repo = tmp_path / "repo"
    _setup_editorial(editorial)
    _setup_repo(repo)

    plan = run_publish(
        SLUG,
        publication_date=FIXED_DATE,
        apply=False,
        environ=_env(editorial, repo),
    )

    assert plan.mode == "dry-run"
    assert not (repo / plan.post_relative).exists()
    assert not (repo / plan.image_relative).exists()


def test_apply_writes_expected_outputs(tmp_path: Path) -> None:
    editorial = tmp_path / "editorial"
    repo = tmp_path / "repo"
    source_md, source_png = _setup_editorial(editorial)
    _setup_repo(repo)

    plan = run_publish(
        SLUG,
        publication_date=FIXED_DATE,
        apply=True,
        environ=_env(editorial, repo),
    )

    post_path = repo / plan.post_relative
    image_path = repo / plan.image_relative
    assert post_path.is_file()
    assert image_path.is_file()
    assert image_path.read_bytes() == source_png.read_bytes()

    parsed = yaml.safe_load(post_path.read_text(encoding="utf-8").split("---", 2)[1])
    assert parsed["image"] == "/assets/images/example-post.png"
    assert "Post content here." in post_path.read_text(encoding="utf-8")

    assert source_md.read_text(encoding="utf-8") == (
        "---\n"
        "title: Example Title\n"
        "categories:\n"
        "  - architecture\n"
        "tags:\n"
        "  - leadership\n"
        "description: A short description.\n"
        "---\n"
        "# Body\n\n"
        "Post content here.\n"
    )
    assert source_png.read_bytes() == b"\x89PNG\r\n\x1a\nfake"


def test_refuses_existing_post(tmp_path: Path) -> None:
    editorial = tmp_path / "editorial"
    repo = tmp_path / "repo"
    _setup_editorial(editorial)
    _setup_repo(repo)
    existing = repo / "_posts/2026-07-06-example-post.md"
    existing.write_text("existing", encoding="utf-8")

    with pytest.raises(PublishError, match="refusing to overwrite"):
        run_publish(
            SLUG,
            publication_date=FIXED_DATE,
            apply=True,
            environ=_env(editorial, repo),
        )

    assert existing.read_text(encoding="utf-8") == "existing"
    assert not (repo / "assets/images/example-post.png").exists()


def test_refuses_existing_image(tmp_path: Path) -> None:
    editorial = tmp_path / "editorial"
    repo = tmp_path / "repo"
    _setup_editorial(editorial)
    _setup_repo(repo)
    existing = repo / "assets/images/example-post.png"
    existing.write_bytes(b"existing")

    with pytest.raises(PublishError, match="refusing to overwrite"):
        run_publish(
            SLUG,
            publication_date=FIXED_DATE,
            apply=False,
            environ=_env(editorial, repo),
        )

    assert existing.read_bytes() == b"existing"
    assert not (repo / "_posts/2026-07-06-example-post.md").exists()


def test_missing_markdown_source(tmp_path: Path) -> None:
    editorial = tmp_path / "editorial"
    repo = tmp_path / "repo"
    ready = editorial / "blog-posts/ready"
    ready.mkdir(parents=True)
    (ready / f"{SLUG}.png").write_bytes(b"png")
    _setup_repo(repo)

    with pytest.raises(PublishError, match="missing markdown source"):
        build_plan(
            load_config(_env(editorial, repo)),
            SLUG,
            FIXED_DATE,
            apply=False,
        )


def test_missing_png_source(tmp_path: Path) -> None:
    editorial = tmp_path / "editorial"
    repo = tmp_path / "repo"
    ready = editorial / "blog-posts/ready"
    ready.mkdir(parents=True)
    (ready / f"{SLUG}.md").write_text("# only md\n", encoding="utf-8")
    _setup_repo(repo)

    with pytest.raises(PublishError, match="missing PNG source"):
        build_plan(
            load_config(_env(editorial, repo)),
            SLUG,
            FIXED_DATE,
            apply=False,
        )


def test_main_json_error_output(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["bad slug", "--json"])
    captured = capsys.readouterr()
    assert code == 1
    payload = json.loads(captured.err.strip())
    assert payload["status"] == "error"
    assert "unsafe source slug" in payload["reason"]


def test_main_missing_repo_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SILVERMAN_GITHUB_PAGES_REPO_PATH", raising=False)
    assert main([SLUG]) == 1


def test_cli_module_invocation(tmp_path: Path) -> None:
    editorial = tmp_path / "editorial"
    repo = tmp_path / "repo"
    _setup_editorial(editorial)
    _setup_repo(repo)
    env = _env(editorial, repo)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "silverman_blog_linkedin.github_pages_publish",
            SLUG,
            "--date",
            "2026-07-06",
        ],
        capture_output=True,
        text=True,
        env={**__import__("os").environ, **env},
        check=False,
    )

    assert result.returncode == 0
    assert "mode: dry-run" in result.stdout
    assert "source_slug: example-post" in result.stdout
    assert "public_slug: example-post" in result.stdout
    assert "public_url: https://silverman.pro/2026/07/06/example-post/" in result.stdout
    assert not (repo / "_posts/2026-07-06-example-post.md").exists()
