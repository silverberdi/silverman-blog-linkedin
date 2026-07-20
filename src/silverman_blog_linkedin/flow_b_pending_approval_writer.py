"""Collision-safe writes under ``blog-posts/pending-approval/`` (US-079).

Pair rules match ``blog-posts/ready/``: direct-child ``<slug>.md`` + ``<slug>.png``.
Sidecar metadata: ``<slug>.flow-b.json``. Never writes under ``blog-posts/ready/``.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from silverman_blog_linkedin.draft_writer import sanitize_filename_segment

PENDING_APPROVAL_RELATIVE = "blog-posts/pending-approval"
PENDING_APPROVAL_PREFIX = f"{PENDING_APPROVAL_RELATIVE}/"
READY_RELATIVE = "blog-posts/ready"
READY_PREFIX = f"{READY_RELATIVE}/"

ERROR_PENDING_DIR_NOT_READY = "pending_approval_dir_not_ready"
ERROR_PENDING_DIR_NOT_WRITABLE = "pending_approval_dir_not_writable"
ERROR_PATH_COLLISION = "pending_approval_path_collision"
ERROR_WRITE_FAILED = "pending_approval_write_failed"
ERROR_READY_WRITE_FORBIDDEN = "pending_approval_ready_write_forbidden"

_WINDOWS_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:[/\\]")


@dataclass(frozen=True)
class PendingApprovalDirReadiness:
    ready: bool
    error_code: str | None = None


@dataclass(frozen=True)
class PendingApprovalWriteResult:
    blog_relative_path: str | None
    image_relative_path: str | None
    metadata_relative_path: str | None
    slug: str | None
    content_sha256: str | None
    errors: list[str]


def check_pending_approval_dir_ready(base_path: Path) -> PendingApprovalDirReadiness:
    """Ensure ``blog-posts/pending-approval/`` exists (create if missing) and is writable."""
    pending_dir = base_path / PENDING_APPROVAL_RELATIVE
    try:
        pending_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return PendingApprovalDirReadiness(
            ready=False,
            error_code=ERROR_PENDING_DIR_NOT_READY,
        )
    if not pending_dir.is_dir():
        return PendingApprovalDirReadiness(
            ready=False,
            error_code=ERROR_PENDING_DIR_NOT_READY,
        )
    if not os.access(pending_dir, os.W_OK):
        return PendingApprovalDirReadiness(
            ready=False,
            error_code=ERROR_PENDING_DIR_NOT_WRITABLE,
        )
    return PendingApprovalDirReadiness(ready=True)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _is_under_pending(relative_path: str) -> bool:
    normalized = relative_path.replace("\\", "/").lstrip("/")
    return normalized.startswith(PENDING_APPROVAL_PREFIX) and not normalized.startswith(
        READY_PREFIX
    )


def _verify_pending_confinement(base_path: Path, relative_path: str) -> bool:
    if not _is_under_pending(relative_path):
        return False
    pending_dir = (base_path / PENDING_APPROVAL_RELATIVE).resolve()
    candidate = (base_path / relative_path).resolve()
    try:
        return candidate.is_relative_to(pending_dir)
    except (OSError, ValueError):
        return False


def generate_pending_approval_slug(
    *,
    title_or_thesis: str,
    topic_id: str,
    collision_attempt: int = 0,
) -> str:
    """Build a filesystem-safe lowercase slug from title/thesis with collision suffixes.

    Lowercase is required so ComfyUI / public-slug helpers (``SLUG_PATTERN``) accept
    the stem when generating the hero image sibling.
    """
    stem = sanitize_filename_segment(title_or_thesis).lower()[:80]
    topic_suffix = sanitize_filename_segment(topic_id).lower()[:24]
    timestamp = _utc_timestamp().lower()
    base = f"{timestamp}-{stem}"
    if collision_attempt == 0:
        return base
    if collision_attempt == 1:
        return f"{base}-{topic_suffix}"
    return f"{base}-{topic_suffix}-{collision_attempt}"


def pending_paths_for_slug(slug: str) -> tuple[str, str, str]:
    """Return ``(md, png, sidecar)`` relative paths for a pending-approval slug."""
    safe = sanitize_filename_segment(slug).lower()
    md = f"{PENDING_APPROVAL_PREFIX}{safe}.md"
    png = f"{PENDING_APPROVAL_PREFIX}{safe}.png"
    meta = f"{PENDING_APPROVAL_PREFIX}{safe}.flow-b.json"
    return md, png, meta


def _prepare_markdown_bytes(content: str) -> bytes:
    text = content
    if text and not text.endswith("\n"):
        text = text + "\n"
    return text.encode("utf-8")


def write_pending_approval_markdown(
    base_path: Path,
    *,
    markdown: str,
    title_or_thesis: str,
    topic_id: str,
) -> PendingApprovalWriteResult:
    """Exclusively create Markdown under pending-approval; reserve sibling paths.

    Does not write the PNG (ComfyUI owns image bytes). Writes sidecar after Markdown
    succeeds when caller supplies metadata via ``write_pending_approval_sidecar``.
    """
    readiness = check_pending_approval_dir_ready(base_path)
    if not readiness.ready:
        return PendingApprovalWriteResult(
            blog_relative_path=None,
            image_relative_path=None,
            metadata_relative_path=None,
            slug=None,
            content_sha256=None,
            errors=[readiness.error_code or ERROR_PENDING_DIR_NOT_READY],
        )

    raw_bytes = _prepare_markdown_bytes(markdown)
    content_sha256 = hashlib.sha256(raw_bytes).hexdigest()

    for attempt in range(5):
        slug = generate_pending_approval_slug(
            title_or_thesis=title_or_thesis,
            topic_id=topic_id,
            collision_attempt=attempt,
        )
        md_rel, png_rel, meta_rel = pending_paths_for_slug(slug)
        for relative in (md_rel, png_rel, meta_rel):
            if not _verify_pending_confinement(base_path, relative):
                return PendingApprovalWriteResult(
                    blog_relative_path=None,
                    image_relative_path=None,
                    metadata_relative_path=None,
                    slug=None,
                    content_sha256=None,
                    errors=[ERROR_READY_WRITE_FORBIDDEN],
                )
            if (base_path / relative).exists():
                break
        else:
            md_path = base_path / md_rel
            try:
                with open(md_path, "xb") as handle:
                    handle.write(raw_bytes)
            except FileExistsError:
                continue
            except OSError:
                return PendingApprovalWriteResult(
                    blog_relative_path=None,
                    image_relative_path=None,
                    metadata_relative_path=None,
                    slug=None,
                    content_sha256=None,
                    errors=[ERROR_WRITE_FAILED],
                )
            return PendingApprovalWriteResult(
                blog_relative_path=md_rel,
                image_relative_path=png_rel,
                metadata_relative_path=meta_rel,
                slug=slug,
                content_sha256=content_sha256,
                errors=[],
            )

    return PendingApprovalWriteResult(
        blog_relative_path=None,
        image_relative_path=None,
        metadata_relative_path=None,
        slug=None,
        content_sha256=None,
        errors=[ERROR_PATH_COLLISION],
    )


def write_pending_approval_sidecar(
    base_path: Path,
    metadata_relative_path: str,
    payload: dict[str, Any],
) -> str | None:
    """Write durable ``.flow-b.json`` sidecar; return error_code or None on success."""
    if not _verify_pending_confinement(base_path, metadata_relative_path):
        return ERROR_READY_WRITE_FORBIDDEN
    if not metadata_relative_path.endswith(".flow-b.json"):
        return ERROR_WRITE_FAILED
    # Reject path traversal via PurePosixPath parts
    parts = PurePosixPath(metadata_relative_path.replace("\\", "/")).parts
    if ".." in parts:
        return ERROR_READY_WRITE_FORBIDDEN
    path = base_path / metadata_relative_path
    try:
        raw = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        with open(path, "xb") as handle:
            handle.write(raw)
    except FileExistsError:
        return ERROR_PATH_COLLISION
    except OSError:
        return ERROR_WRITE_FAILED
    return None


def remove_pending_approval_partial(
    base_path: Path,
    *,
    blog_relative_path: str | None = None,
    metadata_relative_path: str | None = None,
) -> None:
    """Best-effort cleanup of partial pending-approval artifacts (never touches ready/)."""
    for relative in (blog_relative_path, metadata_relative_path):
        if not relative or not _verify_pending_confinement(base_path, relative):
            continue
        path = base_path / relative
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            continue
