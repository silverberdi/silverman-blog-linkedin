"""Request path validation and UTF-8 blog post file reading."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

READY_RELATIVE = "blog-posts/ready"
READY_PREFIX = f"{READY_RELATIVE}/"

_WINDOWS_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:[/\\]")


@dataclass(frozen=True)
class FileReadResult:
    relative_path: str
    filename: str | None
    size_bytes: int | None
    content_sha256: str | None
    markdown_content: str | None
    errors: list[str]


def normalize_relative_path(relative_path: str) -> str:
    """Strip leading ./ and trailing slashes from a relative path."""
    normalized = relative_path.strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.rstrip("/")


def derive_filename(relative_path: str) -> str | None:
    """Return the final path component when safely derivable."""
    normalized = normalize_relative_path(relative_path)
    parts = PurePosixPath(normalized).parts
    if not parts:
        return None
    if normalized == READY_RELATIVE:
        return None
    if normalized.startswith(READY_PREFIX):
        remainder = normalized[len(READY_PREFIX) :]
        if not remainder or "/" in remainder:
            return None
        return remainder
    name = parts[-1]
    return name if name else None


def _is_absolute_path(relative_path: str) -> bool:
    if relative_path.startswith("/"):
        return True
    if PureWindowsPath(relative_path).is_absolute():
        return True
    return bool(_WINDOWS_DRIVE_PATTERN.match(relative_path))


def _validate_path_shape(relative_path: str) -> list[str]:
    errors: list[str] = []

    if _is_absolute_path(relative_path):
        errors.append("absolute_path")
        return errors

    parts = PurePosixPath(relative_path).parts
    if ".." in parts:
        errors.append("path_traversal")
        return errors

    if not relative_path.startswith(READY_PREFIX):
        errors.append("path_outside_ready")
        return errors

    remainder = relative_path[len(READY_PREFIX) :]
    if not remainder or "/" in remainder:
        errors.append("path_not_direct_child")
        return errors

    filename = derive_filename(relative_path)
    if filename is None or not filename.lower().endswith(".md"):
        errors.append("extension_not_md")

    return errors


def read_blog_post_file(base_path: Path, relative_path: str) -> FileReadResult:
    """Validate path under blog-posts/ready and read UTF-8 Markdown content."""
    normalized = normalize_relative_path(relative_path)
    filename = derive_filename(normalized)

    path_errors = _validate_path_shape(normalized)
    if path_errors:
        return FileReadResult(
            relative_path=normalized,
            filename=filename,
            size_bytes=None,
            content_sha256=None,
            markdown_content=None,
            errors=path_errors,
        )

    ready_dir = (base_path / READY_RELATIVE).resolve()
    candidate = (base_path / normalized).resolve()

    if not candidate.is_relative_to(ready_dir):
        return FileReadResult(
            relative_path=normalized,
            filename=filename,
            size_bytes=None,
            content_sha256=None,
            markdown_content=None,
            errors=["path_outside_ready"],
        )

    if not candidate.exists():
        return FileReadResult(
            relative_path=normalized,
            filename=filename,
            size_bytes=None,
            content_sha256=None,
            markdown_content=None,
            errors=["file_not_found"],
        )

    if candidate.is_dir():
        return FileReadResult(
            relative_path=normalized,
            filename=filename,
            size_bytes=None,
            content_sha256=None,
            markdown_content=None,
            errors=["is_directory"],
        )

    size_bytes: int | None = None
    try:
        size_bytes = candidate.stat().st_size
    except OSError:
        size_bytes = None

    if size_bytes == 0:
        return FileReadResult(
            relative_path=normalized,
            filename=filename,
            size_bytes=0,
            content_sha256=None,
            markdown_content=None,
            errors=["file_empty"],
        )

    try:
        raw_bytes = candidate.read_bytes()
    except OSError:
        return FileReadResult(
            relative_path=normalized,
            filename=filename,
            size_bytes=size_bytes,
            content_sha256=None,
            markdown_content=None,
            errors=["not_readable"],
        )

    if len(raw_bytes) == 0:
        return FileReadResult(
            relative_path=normalized,
            filename=filename,
            size_bytes=0,
            content_sha256=None,
            markdown_content=None,
            errors=["file_empty"],
        )

    content_sha256 = hashlib.sha256(raw_bytes).hexdigest()

    try:
        markdown_content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return FileReadResult(
            relative_path=normalized,
            filename=filename,
            size_bytes=len(raw_bytes),
            content_sha256=content_sha256,
            markdown_content=None,
            errors=["not_utf8"],
        )

    return FileReadResult(
        relative_path=normalized,
        filename=filename,
        size_bytes=len(raw_bytes),
        content_sha256=content_sha256,
        markdown_content=markdown_content,
        errors=[],
    )
