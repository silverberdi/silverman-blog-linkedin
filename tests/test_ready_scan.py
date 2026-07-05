"""Tests for blog-posts/ready scanning and validation."""

from pathlib import Path

from silverman_blog_linkedin.ready_scan import READY_RELATIVE, scan_ready_folder


def _ready_dir(base: Path) -> Path:
    path = base / READY_RELATIVE
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_valid_markdown_candidate(tmp_path):
    ready = _ready_dir(tmp_path)
    (ready / "post.md").write_text("# Hello\n", encoding="utf-8")

    result = scan_ready_folder(tmp_path)

    assert result.candidate_count == 1
    assert result.valid_count == 1
    assert result.invalid_count == 0
    assert result.valid_files[0]["filename"] == "post.md"
    assert result.valid_files[0]["relative_path"] == "blog-posts/ready/post.md"
    assert result.valid_files[0]["size_bytes"] > 0


def test_empty_markdown_is_invalid(tmp_path):
    ready = _ready_dir(tmp_path)
    (ready / "empty.md").write_bytes(b"")

    result = scan_ready_folder(tmp_path)

    assert result.candidate_count == 1
    assert result.valid_count == 0
    assert result.invalid_count == 1
    assert "not_empty" in result.invalid_files[0]["errors"]


def test_non_markdown_files_ignored(tmp_path):
    ready = _ready_dir(tmp_path)
    (ready / "notes.txt").write_text("plain", encoding="utf-8")
    (ready / "post.md").write_text("content", encoding="utf-8")

    result = scan_ready_folder(tmp_path)

    assert result.ignored_count == 1
    assert result.ignored_files[0]["reason"] == "non_markdown"
    assert result.valid_count == 1


def test_subdirectories_ignored(tmp_path):
    ready = _ready_dir(tmp_path)
    (ready / "nested").mkdir()
    (ready / "post.md").write_text("content", encoding="utf-8")

    result = scan_ready_folder(tmp_path)

    assert result.ignored_count == 1
    assert result.ignored_files[0]["reason"] == "subdirectory"


def test_case_insensitive_md_extension(tmp_path):
    ready = _ready_dir(tmp_path)
    (ready / "Post.MD").write_text("content", encoding="utf-8")

    result = scan_ready_folder(tmp_path)

    assert result.valid_count == 1


def test_missing_ready_dir_returns_empty(tmp_path):
    result = scan_ready_folder(tmp_path)

    assert result.candidate_count == 0
    assert result.valid_count == 0
