"""LinkedIn review draft path validation and UTF-8 draft file writing."""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath

from silverman_blog_linkedin.file_reader import (
    READY_PREFIX,
    READY_RELATIVE,
    derive_filename,
    normalize_relative_path,
)

REVIEW_RELATIVE = "linkedin-posts/review"
REVIEW_PREFIX = f"{REVIEW_RELATIVE}/"

_WINDOWS_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:[/\\]")
_INVALID_FILENAME_CHARS = re.compile(r"[^a-zA-Z0-9_-]+")


@dataclass(frozen=True)
class ReviewDirReadiness:
    ready: bool
    error_code: str | None = None


@dataclass(frozen=True)
class DraftWriteResult:
    draft_relative_path: str | None
    draft_content_sha256: str | None
    size_bytes: int | None
    errors: list[str]


def _is_absolute_path(relative_path: str) -> bool:
    if relative_path.startswith("/"):
        return True
    if PureWindowsPath(relative_path).is_absolute():
        return True
    return bool(_WINDOWS_DRIVE_PATTERN.match(relative_path))


def validate_source_path_shape(base_path: Path, relative_path: str) -> list[str]:
    """Validate source path shape under blog-posts/ready without reading the file."""
    normalized = normalize_relative_path(relative_path)
    errors: list[str] = []

    if _is_absolute_path(normalized):
        errors.append("absolute_path")
        return errors

    parts = PurePosixPath(normalized).parts
    if ".." in parts:
        errors.append("path_traversal")
        return errors

    if not normalized.startswith(READY_PREFIX):
        errors.append("path_outside_ready")
        return errors

    remainder = normalized[len(READY_PREFIX) :]
    if not remainder or "/" in remainder:
        errors.append("path_not_direct_child")
        return errors

    filename = derive_filename(normalized)
    if filename is None or not filename.lower().endswith(".md"):
        errors.append("extension_not_md")
        if errors:
            return errors

    ready_dir = (base_path / READY_RELATIVE).resolve()
    candidate = (base_path / normalized).resolve()
    if not candidate.is_relative_to(ready_dir):
        errors.append("path_outside_ready")

    return errors


def check_review_dir_ready(base_path: Path) -> ReviewDirReadiness:
    """Check whether linkedin-posts/review exists, is a directory, and is writable."""
    review_dir = base_path / REVIEW_RELATIVE
    if not review_dir.exists() or not review_dir.is_dir():
        return ReviewDirReadiness(ready=False, error_code="review_dir_not_ready")
    if not os.access(review_dir, os.W_OK):
        return ReviewDirReadiness(ready=False, error_code="review_dir_not_writable")
    return ReviewDirReadiness(ready=True)


def sanitize_filename_segment(segment: str) -> str:
    """Sanitize a filename segment to filesystem-safe [a-zA-Z0-9_-]+ style."""
    sanitized = _INVALID_FILENAME_CHARS.sub("-", segment.strip())
    sanitized = sanitized.strip("-_")
    return sanitized or "draft"


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _run_id_suffix(run_id: str) -> str:
    return run_id.rsplit("-", 1)[-1]


def generate_draft_relative_path(
    *,
    source_relative_path: str,
    slug_hint: str | None,
    run_id: str,
    collision_attempt: int = 0,
) -> str:
    """Generate a draft relative path under linkedin-posts/review/."""
    filename = derive_filename(source_relative_path)
    if filename is None:
        source_stem = "draft"
    else:
        source_stem = sanitize_filename_segment(Path(filename).stem)

    timestamp = _utc_timestamp()
    base_name = f"{timestamp}-{source_stem}"
    if slug_hint:
        base_name = f"{base_name}-{sanitize_filename_segment(slug_hint)}"

    if collision_attempt == 1:
        base_name = f"{base_name}-{_run_id_suffix(run_id)}"
    elif collision_attempt == 2:
        base_name = f"{base_name}-{run_id}"

    return f"{REVIEW_PREFIX}{base_name}.md"


def _verify_draft_path_confinement(base_path: Path, draft_relative_path: str) -> bool:
    review_dir = (base_path / REVIEW_RELATIVE).resolve()
    candidate = (base_path / draft_relative_path).resolve()
    return candidate.is_relative_to(review_dir)


def _prepare_draft_bytes(draft_content: str) -> bytes:
    text = draft_content
    if text and not text.endswith("\n"):
        text = text + "\n"
    return text.encode("utf-8")


def write_draft_file(
    base_path: Path,
    *,
    draft_content: str,
    source_relative_path: str,
    slug_hint: str | None,
    run_id: str,
) -> DraftWriteResult:
    """Write draft content with exclusive creation and collision retries."""
    raw_bytes = _prepare_draft_bytes(draft_content)
    content_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    size_bytes = len(raw_bytes)

    for attempt in range(3):
        draft_relative_path = generate_draft_relative_path(
            source_relative_path=source_relative_path,
            slug_hint=slug_hint,
            run_id=run_id,
            collision_attempt=attempt,
        )
        if not _verify_draft_path_confinement(base_path, draft_relative_path):
            return DraftWriteResult(
                draft_relative_path=None,
                draft_content_sha256=None,
                size_bytes=None,
                errors=["draft_path_collision"],
            )

        draft_path = base_path / draft_relative_path
        try:
            with open(draft_path, "xb") as handle:
                handle.write(raw_bytes)
        except FileExistsError:
            continue
        except OSError:
            return DraftWriteResult(
                draft_relative_path=None,
                draft_content_sha256=None,
                size_bytes=None,
                errors=["draft_path_collision"],
            )
        else:
            return DraftWriteResult(
                draft_relative_path=draft_relative_path,
                draft_content_sha256=content_sha256,
                size_bytes=size_bytes,
                errors=[],
            )

    return DraftWriteResult(
        draft_relative_path=None,
        draft_content_sha256=None,
        size_bytes=None,
        errors=["draft_path_collision"],
    )
