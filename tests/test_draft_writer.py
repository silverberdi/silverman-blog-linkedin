"""Tests for LinkedIn draft path validation and file writing."""

import hashlib
from pathlib import Path
from unittest.mock import patch

from silverman_blog_linkedin.draft_writer import (
    REVIEW_RELATIVE,
    check_review_dir_ready,
    generate_draft_relative_path,
    sanitize_filename_segment,
    validate_source_path_shape,
    write_draft_file,
)
from silverman_blog_linkedin.file_reader import READY_RELATIVE


def _review_dir(base: Path) -> Path:
    path = base / REVIEW_RELATIVE
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ready_dir(base: Path) -> Path:
    path = base / READY_RELATIVE
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_sanitize_filename_segment():
    assert sanitize_filename_segment("my-post") == "my-post"
    assert sanitize_filename_segment("  Executive Variant!  ") == "Executive-Variant"
    assert sanitize_filename_segment("---") == "draft"
    assert sanitize_filename_segment("") == "draft"


@patch("silverman_blog_linkedin.draft_writer._utc_timestamp", return_value="20260705T150045Z")
def test_generate_draft_relative_path_default(_mock_ts):
    path = generate_draft_relative_path(
        source_relative_path="blog-posts/ready/my-post.md",
        slug_hint=None,
        run_id="run-20260705T150045Z-a1b2",
    )
    assert path == "linkedin-posts/review/20260705T150045Z-my-post.md"


@patch("silverman_blog_linkedin.draft_writer._utc_timestamp", return_value="20260705T150045Z")
def test_generate_draft_relative_path_with_slug_hint(_mock_ts):
    path = generate_draft_relative_path(
        source_relative_path="blog-posts/ready/my-post.md",
        slug_hint="executive",
        run_id="run-20260705T150045Z-a1b2",
    )
    assert path == "linkedin-posts/review/20260705T150045Z-my-post-executive.md"


@patch("silverman_blog_linkedin.draft_writer._utc_timestamp", return_value="20260705T150045Z")
def test_generate_draft_relative_path_collision_suffixes(_mock_ts):
    base = generate_draft_relative_path(
        source_relative_path="blog-posts/ready/my-post.md",
        slug_hint=None,
        run_id="run-20260705T150045Z-a1b2",
        collision_attempt=0,
    )
    retry_short = generate_draft_relative_path(
        source_relative_path="blog-posts/ready/my-post.md",
        slug_hint=None,
        run_id="run-20260705T150045Z-a1b2",
        collision_attempt=1,
    )
    retry_full = generate_draft_relative_path(
        source_relative_path="blog-posts/ready/my-post.md",
        slug_hint=None,
        run_id="run-20260705T150045Z-a1b2",
        collision_attempt=2,
    )
    assert base == "linkedin-posts/review/20260705T150045Z-my-post.md"
    assert retry_short == "linkedin-posts/review/20260705T150045Z-my-post-a1b2.md"
    assert (
        retry_full
        == "linkedin-posts/review/20260705T150045Z-my-post-run-20260705T150045Z-a1b2.md"
    )


def test_validate_source_path_shape_valid(tmp_path):
    _ready_dir(tmp_path)
    errors = validate_source_path_shape(tmp_path, "blog-posts/ready/my-post.md")
    assert errors == []


def test_validate_source_path_shape_absolute(tmp_path):
    _ready_dir(tmp_path)
    errors = validate_source_path_shape(tmp_path, "/etc/passwd")
    assert errors == ["absolute_path"]


def test_validate_source_path_shape_traversal(tmp_path):
    _ready_dir(tmp_path)
    errors = validate_source_path_shape(
        tmp_path, "blog-posts/ready/../processed/secret.md"
    )
    assert errors == ["path_traversal"]


def test_validate_source_path_shape_outside_ready(tmp_path):
    _ready_dir(tmp_path)
    errors = validate_source_path_shape(tmp_path, "blog-posts/processed/post.md")
    assert errors == ["path_outside_ready"]


def test_validate_source_path_shape_subdirectory(tmp_path):
    _ready_dir(tmp_path)
    errors = validate_source_path_shape(
        tmp_path, "blog-posts/ready/subdir/post.md"
    )
    assert errors == ["path_not_direct_child"]


def test_validate_source_path_shape_non_md(tmp_path):
    _ready_dir(tmp_path)
    errors = validate_source_path_shape(tmp_path, "blog-posts/ready/post.txt")
    assert errors == ["extension_not_md"]


def test_check_review_dir_ready_when_writable(tmp_path):
    _review_dir(tmp_path)
    readiness = check_review_dir_ready(tmp_path)
    assert readiness.ready is True
    assert readiness.error_code is None


def test_check_review_dir_missing(tmp_path):
    readiness = check_review_dir_ready(tmp_path)
    assert readiness.ready is False
    assert readiness.error_code == "review_dir_not_ready"


def test_check_review_dir_not_writable(tmp_path):
    review = _review_dir(tmp_path)
    review.chmod(0o555)
    try:
        readiness = check_review_dir_ready(tmp_path)
        assert readiness.ready is False
        assert readiness.error_code == "review_dir_not_writable"
    finally:
        review.chmod(0o755)


@patch("silverman_blog_linkedin.draft_writer._utc_timestamp", return_value="20260705T150045Z")
def test_write_draft_file_success(_mock_ts, tmp_path):
    _review_dir(tmp_path)
    content = "LinkedIn draft body."
    result = write_draft_file(
        tmp_path,
        draft_content=content,
        source_relative_path="blog-posts/ready/my-post.md",
        slug_hint=None,
        run_id="run-20260705T150045Z-a1b2",
    )
    assert result.errors == []
    assert result.draft_relative_path == "linkedin-posts/review/20260705T150045Z-my-post.md"
    written = (tmp_path / result.draft_relative_path).read_bytes()
    expected = (content + "\n").encode("utf-8")
    assert written == expected
    assert result.size_bytes == len(expected)
    assert result.draft_content_sha256 == hashlib.sha256(expected).hexdigest()


@patch("silverman_blog_linkedin.draft_writer._utc_timestamp", return_value="20260705T150045Z")
def test_write_draft_file_preserves_trailing_newline(_mock_ts, tmp_path):
    _review_dir(tmp_path)
    content = "Already ends with newline.\n"
    result = write_draft_file(
        tmp_path,
        draft_content=content,
        source_relative_path="blog-posts/ready/my-post.md",
        slug_hint=None,
        run_id="run-20260705T150045Z-a1b2",
    )
    written = (tmp_path / result.draft_relative_path).read_text(encoding="utf-8")
    assert written == content


@patch("silverman_blog_linkedin.draft_writer._utc_timestamp", return_value="20260705T150045Z")
def test_write_draft_file_collision_retry(_mock_ts, tmp_path):
    review = _review_dir(tmp_path)
    existing = review / "20260705T150045Z-my-post.md"
    existing.write_text("existing\n", encoding="utf-8")

    result = write_draft_file(
        tmp_path,
        draft_content="New draft.",
        source_relative_path="blog-posts/ready/my-post.md",
        slug_hint=None,
        run_id="run-20260705T150045Z-a1b2",
    )

    assert result.errors == []
    assert result.draft_relative_path == "linkedin-posts/review/20260705T150045Z-my-post-a1b2.md"
    assert existing.read_text(encoding="utf-8") == "existing\n"


@patch("silverman_blog_linkedin.draft_writer._utc_timestamp", return_value="20260705T150045Z")
def test_write_draft_file_collision_exhausted(_mock_ts, tmp_path):
    review = _review_dir(tmp_path)
    run_id = "run-20260705T150045Z-a1b2"
    paths = [
        "20260705T150045Z-my-post.md",
        "20260705T150045Z-my-post-a1b2.md",
        "20260705T150045Z-my-post-run-20260705T150045Z-a1b2.md",
    ]
    for name in paths:
        (review / name).write_text("occupied\n", encoding="utf-8")

    result = write_draft_file(
        tmp_path,
        draft_content="New draft.",
        source_relative_path="blog-posts/ready/my-post.md",
        slug_hint=None,
        run_id=run_id,
    )

    assert result.errors == ["draft_path_collision"]
    assert result.draft_relative_path is None
    assert result.draft_content_sha256 is None
    assert result.size_bytes is None
