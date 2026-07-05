"""Tests for blog post path validation and file reading."""

from pathlib import Path

from silverman_blog_linkedin.file_reader import (
    READY_RELATIVE,
    derive_filename,
    normalize_relative_path,
    read_blog_post_file,
)


def _ready_dir(base: Path) -> Path:
    path = base / READY_RELATIVE
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_normalize_relative_path():
    assert normalize_relative_path("./blog-posts/ready/post.md/") == (
        "blog-posts/ready/post.md"
    )
    assert normalize_relative_path("blog-posts/ready/post.md") == (
        "blog-posts/ready/post.md"
    )


def test_derive_filename():
    assert derive_filename("blog-posts/ready/my-post.md") == "my-post.md"
    assert derive_filename("blog-posts/ready/") is None


def test_valid_read(tmp_path):
    ready = _ready_dir(tmp_path)
    content = "# Title\n\nBody text.\n"
    (ready / "post.md").write_text(content, encoding="utf-8")

    result = read_blog_post_file(tmp_path, "blog-posts/ready/post.md")

    assert result.errors == []
    assert result.relative_path == "blog-posts/ready/post.md"
    assert result.filename == "post.md"
    assert result.size_bytes == len(content.encode("utf-8"))
    assert result.content_sha256 is not None
    assert len(result.content_sha256) == 64
    assert result.markdown_content == content


def test_absolute_path_rejected(tmp_path):
    _ready_dir(tmp_path)

    result = read_blog_post_file(tmp_path, "/etc/passwd")

    assert result.errors == ["absolute_path"]
    assert result.size_bytes is None
    assert result.content_sha256 is None
    assert result.markdown_content is None


def test_path_traversal_rejected(tmp_path):
    _ready_dir(tmp_path)

    result = read_blog_post_file(
        tmp_path, "blog-posts/ready/../processed/secret.md"
    )

    assert result.errors == ["path_traversal"]
    assert result.content_sha256 is None
    assert result.markdown_content is None


def test_path_outside_ready_rejected(tmp_path):
    _ready_dir(tmp_path)

    result = read_blog_post_file(tmp_path, "blog-posts/processed/post.md")

    assert result.errors == ["path_outside_ready"]
    assert result.relative_path == "blog-posts/processed/post.md"
    assert result.filename == "post.md"
    assert result.size_bytes is None
    assert result.content_sha256 is None


def test_subdirectory_path_rejected(tmp_path):
    ready = _ready_dir(tmp_path)
    nested = ready / "subdir"
    nested.mkdir()
    (nested / "post.md").write_text("# Nested\n", encoding="utf-8")

    result = read_blog_post_file(tmp_path, "blog-posts/ready/subdir/post.md")

    assert result.errors == ["path_not_direct_child"]
    assert result.content_sha256 is None
    assert result.markdown_content is None


def test_non_md_extension_rejected(tmp_path):
    ready = _ready_dir(tmp_path)
    (ready / "notes.txt").write_text("plain", encoding="utf-8")

    result = read_blog_post_file(tmp_path, "blog-posts/ready/notes.txt")

    assert result.errors == ["extension_not_md"]
    assert result.content_sha256 is None


def test_missing_file(tmp_path):
    _ready_dir(tmp_path)

    result = read_blog_post_file(tmp_path, "blog-posts/ready/missing.md")

    assert result.errors == ["file_not_found"]
    assert result.filename == "missing.md"
    assert result.size_bytes is None
    assert result.content_sha256 is None
    assert result.markdown_content is None


def test_directory_target(tmp_path):
    ready = _ready_dir(tmp_path)
    (ready / "folder.md").mkdir()

    result = read_blog_post_file(tmp_path, "blog-posts/ready/folder.md")

    assert result.errors == ["is_directory"]
    assert result.content_sha256 is None
    assert result.markdown_content is None


def test_empty_file(tmp_path):
    ready = _ready_dir(tmp_path)
    (ready / "empty.md").write_bytes(b"")

    result = read_blog_post_file(tmp_path, "blog-posts/ready/empty.md")

    assert result.errors == ["file_empty"]
    assert result.size_bytes == 0
    assert result.content_sha256 is None
    assert result.markdown_content is None


def test_invalid_utf8(tmp_path):
    ready = _ready_dir(tmp_path)
    (ready / "bad.md").write_bytes(b"\xff\xfe")

    result = read_blog_post_file(tmp_path, "blog-posts/ready/bad.md")

    assert result.errors == ["not_utf8"]
    assert result.content_sha256 is not None
    assert result.markdown_content is None


def test_normalized_input(tmp_path):
    ready = _ready_dir(tmp_path)
    (ready / "post.md").write_text("# Hello\n", encoding="utf-8")

    result = read_blog_post_file(tmp_path, "./blog-posts/ready/post.md/")

    assert result.errors == []
    assert result.relative_path == "blog-posts/ready/post.md"
    assert result.markdown_content == "# Hello\n"
