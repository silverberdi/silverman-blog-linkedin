"""Tests for Flow A ready-post editorial validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from silverman_blog_linkedin.campaign_lifecycle import (
    ACTOR_WORKER,
    FLOW_A,
    METADATA_CAMPAIGNS_RELATIVE,
    STATE_BLOG_PUBLISH_PENDING,
    STATE_BLOG_PUBLISHED,
    STATE_READY,
    STATE_VALIDATED,
    STATE_VALIDATION_FAILED,
    compute_source_content_sha256,
    read_campaign_metadata,
    transition_state,
    write_campaign_metadata,
)
from silverman_blog_linkedin.ready_post_validation import (
    CAMPAIGN_CONTENT_HASH_CHANGED,
    CAMPAIGN_INVALID_EXISTING_STATE,
    CONTENT_CONTAINS_SECRET_MARKER,
    CONTENT_CONTAINS_TODO,
    CONTENT_EMBEDDED_LINKEDIN_DRAFT,
    CONTENT_MISSING_H1,
    CONTENT_NON_SILVERMAN_PUBLISH_TARGET,
    CONTENT_TITLE_MISMATCH,
    CONTENT_UNSUPPORTED_LOCAL_IMAGE,
    FRONTMATTER_INVALID,
    FRONTMATTER_INVALID_DATE,
    FRONTMATTER_INVALID_IMAGE,
    FRONTMATTER_MISSING,
    FRONTMATTER_REQUIRED_FIELD_MISSING,
    INVALID_PUBLIC_SLUG,
    READY_POST_EMPTY,
    READY_POST_IMAGE_INVALID_EXTENSION,
    READY_POST_IMAGE_MISSING,
    READY_POST_MISSING,
    READY_POST_NOT_MARKDOWN,
    READY_POST_NOT_UNDER_READY,
    WARNING_AI_OPENING,
    WARNING_GENERIC_ENDING,
    validate_ready_post,
)

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
    with_jpg: bool = False,
) -> Path:
    ready = base / "blog-posts" / "ready"
    ready.mkdir(parents=True, exist_ok=True)
    md_path = ready / f"{slug}.md"
    fm = frontmatter if frontmatter is not None else _canonical_frontmatter()
    content = fm + (body if body is not None else _canonical_body())
    md_path.write_text(content, encoding="utf-8")
    if with_png:
        (ready / f"{slug}.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    if with_jpg:
        (ready / f"{slug}.jpg").write_bytes(b"\xff\xd8\xff fake")
    return md_path


def _setup_metadata_campaigns(base: Path) -> Path:
    metadata_dir = base / METADATA_CAMPAIGNS_RELATIVE
    metadata_dir.mkdir(parents=True, exist_ok=True)
    return metadata_dir


def _validate(base: Path, relative: str = SOURCE_RELATIVE):
    return validate_ready_post(base, relative, site_url=SITE_URL)


@pytest.fixture
def editorial_base(tmp_path: Path) -> Path:
    _setup_metadata_campaigns(tmp_path)
    return tmp_path


def test_canonical_pass_path(editorial_base: Path):
    _write_post(editorial_base)

    result = _validate(editorial_base)

    assert result.ok is True
    assert result.errors == []
    assert result.source_slug == SOURCE_SLUG
    assert result.public_slug == PUBLIC_SLUG
    assert result.publication_date == PUBLICATION_DATE
    assert result.image_relative_path == IMAGE_RELATIVE
    assert result.campaign_id == CANONICAL_CAMPAIGN_ID
    assert result.state == STATE_VALIDATED
    assert result.metadata_written is True
    assert result.source_public_url == (
        f"{SITE_URL}/2026/07/06/{PUBLIC_SLUG}/"
    )

    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["state"] == STATE_VALIDATED
    assert campaign["source_public_url"] == result.source_public_url


@pytest.mark.parametrize(
    ("relative", "expected_error"),
    [
        ("blog-posts/processed/post.md", READY_POST_NOT_UNDER_READY),
        ("blog-posts/ready/post.txt", READY_POST_NOT_MARKDOWN),
    ],
)
def test_path_and_extension_failures(
    editorial_base: Path, relative: str, expected_error: str
):
    ready = editorial_base / "blog-posts" / "ready"
    ready.mkdir(parents=True, exist_ok=True)
    target = editorial_base / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("content", encoding="utf-8")

    result = _validate(editorial_base, relative)

    assert result.ok is False
    assert expected_error in result.errors
    assert result.metadata_written is False


def test_missing_source_file(editorial_base: Path):
    result = _validate(editorial_base)

    assert result.ok is False
    assert READY_POST_MISSING in result.errors


def test_path_traversal_outside_ready_dir_rejected(editorial_base: Path):
    processed = editorial_base / "blog-posts" / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    (processed / "post.md").write_text("outside ready", encoding="utf-8")

    traversal_path = "blog-posts/ready/../processed/post.md"
    result = _validate(editorial_base, traversal_path)

    assert result.ok is False
    assert READY_POST_NOT_UNDER_READY in result.errors
    assert result.metadata_written is False


def test_invalid_public_slug(editorial_base: Path):
    _write_post(editorial_base, slug="01-Bad-Slug")

    result = _validate(
        editorial_base, "blog-posts/ready/01-Bad-Slug.md"
    )

    assert result.ok is False
    assert INVALID_PUBLIC_SLUG in result.errors


def test_image_missing(editorial_base: Path):
    _write_post(editorial_base, with_png=False)

    result = _validate(editorial_base)

    assert result.ok is False
    assert READY_POST_IMAGE_MISSING in result.errors
    assert READY_POST_IMAGE_INVALID_EXTENSION not in result.errors
    assert result.state == STATE_VALIDATION_FAILED
    assert result.metadata_written is True


def test_image_invalid_extension(editorial_base: Path):
    _write_post(editorial_base, with_png=False, with_jpg=True)

    result = _validate(editorial_base)

    assert result.ok is False
    assert READY_POST_IMAGE_INVALID_EXTENSION in result.errors
    assert READY_POST_IMAGE_MISSING not in result.errors


def test_frontmatter_missing(editorial_base: Path):
    _write_post(editorial_base, frontmatter="", body="# Title\n\nBody.\n")

    result = _validate(editorial_base)

    assert result.ok is False
    assert FRONTMATTER_MISSING in result.errors


def test_frontmatter_invalid_yaml(editorial_base: Path):
    _write_post(
        editorial_base,
        frontmatter="---\ntitle: [unclosed\n---\n",
    )

    result = _validate(editorial_base)

    assert result.ok is False
    assert FRONTMATTER_INVALID in result.errors


def test_frontmatter_required_field_missing(editorial_base: Path):
    frontmatter = _canonical_frontmatter().replace("audience: architects\n", "")
    _write_post(editorial_base, frontmatter=frontmatter)

    result = _validate(editorial_base)

    assert result.ok is False
    assert FRONTMATTER_REQUIRED_FIELD_MISSING in result.errors


def test_frontmatter_invalid_date(editorial_base: Path):
    frontmatter = _canonical_frontmatter().replace(
        f"date: {PUBLICATION_DATE}\n", "date: not-a-date\n"
    )
    _write_post(editorial_base, frontmatter=frontmatter)

    result = _validate(editorial_base)

    assert result.ok is False
    assert FRONTMATTER_INVALID_DATE in result.errors


def test_frontmatter_invalid_image(editorial_base: Path):
    frontmatter = _canonical_frontmatter().replace(
        f"image: /assets/images/{PUBLIC_SLUG}.png\n",
        "image: /assets/images/wrong.png\n",
    )
    _write_post(editorial_base, frontmatter=frontmatter)

    result = _validate(editorial_base)

    assert result.ok is False
    assert FRONTMATTER_INVALID_IMAGE in result.errors


def test_empty_body_blocks(editorial_base: Path):
    _write_post(editorial_base, body="")

    result = _validate(editorial_base)

    assert result.ok is False
    assert READY_POST_EMPTY in result.errors


def test_missing_h1_blocks(editorial_base: Path):
    _write_post(editorial_base, body="Body without a heading.\n")

    result = _validate(editorial_base)

    assert result.ok is False
    assert CONTENT_MISSING_H1 in result.errors


def test_title_mismatch_blocks(editorial_base: Path):
    _write_post(
        editorial_base,
        body="# Completely Different Heading\n\nBody text.\n",
    )

    result = _validate(editorial_base)

    assert result.ok is False
    assert CONTENT_TITLE_MISMATCH in result.errors


def test_todo_marker_blocks(editorial_base: Path):
    _write_post(
        editorial_base,
        body=_canonical_body(extra="\nTODO: finish this section.\n"),
    )

    result = _validate(editorial_base)

    assert result.ok is False
    assert CONTENT_CONTAINS_TODO in result.errors


def test_secret_marker_blocks(editorial_base: Path):
    _write_post(
        editorial_base,
        body=_canonical_body(extra="\napi_key: super-secret-value\n"),
    )

    result = _validate(editorial_base)

    assert result.ok is False
    assert CONTENT_CONTAINS_SECRET_MARKER in result.errors


def test_unsupported_local_image_blocks(editorial_base: Path):
    _write_post(
        editorial_base,
        body=_canonical_body(extra="\n![diagram](../private/diagram.png)\n"),
    )

    result = _validate(editorial_base)

    assert result.ok is False
    assert CONTENT_UNSUPPORTED_LOCAL_IMAGE in result.errors


def test_non_silverman_publish_target_blocks(editorial_base: Path):
    _write_post(
        editorial_base,
        body=_canonical_body(extra="\nAlso publish to Medium for reach.\n"),
    )

    result = _validate(editorial_base)

    assert result.ok is False
    assert CONTENT_NON_SILVERMAN_PUBLISH_TARGET in result.errors


def test_embedded_linkedin_draft_blocks(editorial_base: Path):
    _write_post(
        editorial_base,
        body=_canonical_body(
            extra="\n## LinkedIn draft\n\nExecutive variant text here.\n"
        ),
    )

    result = _validate(editorial_base)

    assert result.ok is False
    assert CONTENT_EMBEDDED_LINKEDIN_DRAFT in result.errors


def test_anti_ai_opening_warning_only(editorial_base: Path):
    _write_post(
        editorial_base,
        body=(
            "# Why I Did Not Start With the Database\n\n"
            "In today's fast-paced world, teams reach for databases first.\n"
            "The trade-off is naming the business too late.\n"
        ),
    )

    result = _validate(editorial_base)

    assert result.ok is True
    assert WARNING_AI_OPENING in result.warnings
    assert result.state == STATE_VALIDATED

    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    assert WARNING_AI_OPENING in campaign["warnings"]


def test_generic_ending_warning_only(editorial_base: Path):
    _write_post(
        editorial_base,
        body=(
            "# Why I Did Not Start With the Database\n\n"
            "The real problem is not persistence. The real problem is naming "
            "the business too late.\n\n"
            "What are your thoughts?\n"
        ),
    )

    result = _validate(editorial_base)

    assert result.ok is True
    assert WARNING_GENERIC_ENDING in result.warnings
    assert result.state == STATE_VALIDATED


def test_idempotent_revalidation_same_hash(editorial_base: Path):
    _write_post(editorial_base)
    first = _validate(editorial_base)
    assert first.ok is True
    assert first.metadata_written is True

    campaign_before = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    history_len = len(campaign_before["state_history"])

    second = _validate(editorial_base)

    assert second.ok is True
    assert second.metadata_written is False
    assert second.state == STATE_VALIDATED

    campaign_after = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert len(campaign_after["state_history"]) == history_len


def test_campaign_content_hash_changed(editorial_base: Path):
    _write_post(editorial_base)
    first = _validate(editorial_base)
    assert first.ok is True

    md_path = editorial_base / SOURCE_RELATIVE
    md_path.write_text(
        md_path.read_text(encoding="utf-8") + "\nExtra paragraph.\n",
        encoding="utf-8",
    )

    second = _validate(editorial_base)

    assert second.ok is False
    assert CAMPAIGN_CONTENT_HASH_CHANGED in second.errors
    assert second.metadata_written is False


def test_campaign_invalid_existing_state(editorial_base: Path):
    _write_post(editorial_base)
    first = _validate(editorial_base)
    assert first.ok is True

    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    for to_state, reason in (
        (STATE_BLOG_PUBLISH_PENDING, "Blog publish requested"),
        (STATE_BLOG_PUBLISHED, "Already published"),
    ):
        transition_state(
            campaign,
            to_state,
            reason=reason,
            actor=ACTOR_WORKER,
        )
    write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, campaign)

    second = _validate(editorial_base)

    assert second.ok is False
    assert CAMPAIGN_INVALID_EXISTING_STATE in second.errors
    assert second.metadata_written is False


def test_metadata_write_failure_surfaces_error_code(editorial_base: Path):
    _write_post(editorial_base)
    metadata_dir = editorial_base / METADATA_CAMPAIGNS_RELATIVE
    metadata_dir.chmod(0o555)

    try:
        result = _validate(editorial_base)
    finally:
        metadata_dir.chmod(0o755)

    assert result.ok is False
    assert result.metadata_written is False
    assert result.metadata_error_code == "metadata_campaigns_not_writable"


def test_campaign_metadata_created_in_ready_then_validated(editorial_base: Path):
    _write_post(editorial_base)

    result = _validate(editorial_base)

    assert result.ok is True
    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["state"] == STATE_VALIDATED
    assert campaign["flow"] == FLOW_A
    assert campaign["source_slug"] == SOURCE_SLUG
    assert campaign["public_slug"] == PUBLIC_SLUG
    assert campaign["source_content_sha256"] == compute_source_content_sha256(
        (editorial_base / SOURCE_RELATIVE).read_text(encoding="utf-8")
    )
    states = [entry["to_state"] for entry in campaign["state_history"]]
    assert states == [STATE_READY, STATE_VALIDATED]
