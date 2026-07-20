"""US-081: promote approved Flow B drafts from pending-approval/ to ready/.

Moves ``.md`` + ``.png`` + ``.flow-b.json`` after a US-080 approve decision.
MUST NOT invoke Flow A publish/package/schedule, Git publish, or LinkedIn API.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.flow_b_blog_draft_approval import (
    ERROR_DRAFT_ID_INVALID,
    ERROR_DRAFT_NOT_FOUND,
    ERROR_PATH_TRAVERSAL,
    ERROR_SIDECAR_INVALID,
    STATUS_APPROVED,
    STATUS_PENDING_APPROVAL,
    STATUS_PENDING_APPROVAL_IMAGE_FAILED,
    STATUS_REJECTED,
    _as_optional_str,
    _load_sidecar,
    _looks_like_traversal,
    validate_draft_id,
)
from silverman_blog_linkedin.flow_b_pending_approval_writer import (
    PENDING_APPROVAL_PREFIX,
    PENDING_APPROVAL_RELATIVE,
    READY_PREFIX,
    READY_RELATIVE,
    pending_paths_for_slug,
)
from silverman_blog_linkedin.run_metadata import utc_now_iso

STATUS_PROMOTED = "promoted"
ORIGIN_FLOW_B = "flow_b"

ERROR_DRAFT_NOT_APPROVED = "draft_not_approved"
ERROR_DRAFT_REJECTED = "draft_rejected"
ERROR_DRAFT_PAIR_INCOMPLETE = "draft_pair_incomplete"
ERROR_READY_COLLISION = "draft_ready_collision"
ERROR_PROMOTE_MOVE_FAILED = "draft_promote_move_failed"
ERROR_APPROVAL_METADATA_MISSING = "draft_approval_metadata_missing"
ERROR_SIDECAR_WRITE_FAILED = "draft_sidecar_write_failed"

DEFAULT_PROMOTED_BY = "operator"


@dataclass(frozen=True)
class DraftPromoteResult:
    """Promote outcome — Flow A eligibility only (no publish side effects)."""

    status: str
    draft_id: str
    promoted: bool = False
    promotion_pending: bool = False
    already_promoted: bool = False
    dry_run: bool = False
    blog_relative_path: str | None = None
    image_relative_path: str | None = None
    metadata_relative_path: str | None = None
    approved_at_utc: str | None = None
    approved_by: str | None = None
    promoted_at_utc: str | None = None
    promoted_by: str | None = None
    origin: str | None = None
    target_week: str | None = None
    empty_days: list[str] | None = None
    flow_a_eligible: bool = False
    operator_note: str | None = None
    error_code: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status,
            "draft_id": self.draft_id,
            "promoted": self.promoted,
            "promotion_pending": self.promotion_pending,
            "already_promoted": self.already_promoted,
            "dry_run": self.dry_run,
            "blog_relative_path": self.blog_relative_path,
            "image_relative_path": self.image_relative_path,
            "metadata_relative_path": self.metadata_relative_path,
            "flow_a_eligible": self.flow_a_eligible,
        }
        if self.approved_at_utc is not None:
            payload["approved_at_utc"] = self.approved_at_utc
        if self.approved_by is not None:
            payload["approved_by"] = self.approved_by
        if self.promoted_at_utc is not None:
            payload["promoted_at_utc"] = self.promoted_at_utc
        if self.promoted_by is not None:
            payload["promoted_by"] = self.promoted_by
        if self.origin is not None:
            payload["origin"] = self.origin
        if self.target_week is not None:
            payload["target_week"] = self.target_week
        if self.empty_days is not None:
            payload["empty_days"] = list(self.empty_days)
        if self.operator_note is not None:
            payload["operator_note"] = self.operator_note
        if self.error_code is not None:
            payload["error_code"] = self.error_code
        if self.error is not None:
            payload["error"] = self.error
        return payload


def ready_paths_for_slug(slug: str) -> tuple[str, str, str]:
    """Return ``(md, png, sidecar)`` relative paths under ``blog-posts/ready/``."""
    md_pending, png_pending, meta_pending = pending_paths_for_slug(slug)
    return (
        md_pending.replace(PENDING_APPROVAL_PREFIX, READY_PREFIX, 1),
        png_pending.replace(PENDING_APPROVAL_PREFIX, READY_PREFIX, 1),
        meta_pending.replace(PENDING_APPROVAL_PREFIX, READY_PREFIX, 1),
    )


def _pending_dir(base_path: Path) -> Path:
    return base_path / PENDING_APPROVAL_RELATIVE


def _ready_dir(base_path: Path) -> Path:
    return base_path / READY_RELATIVE


def _verify_under(base_path: Path, candidate: Path, folder: Path) -> bool:
    try:
        return candidate.resolve().is_relative_to(folder.resolve())
    except (OSError, ValueError):
        return False


def _failed(
    draft_id: str,
    code: str,
    *,
    dry_run: bool = False,
) -> DraftPromoteResult:
    return DraftPromoteResult(
        status="failed",
        draft_id=draft_id,
        promoted=False,
        promotion_pending=False,
        dry_run=dry_run,
        error_code=code,
        error=_operator_message(code),
    )


def _empty_days_from_sidecar(sidecar: dict[str, Any]) -> list[str] | None:
    raw = sidecar.get("empty_days")
    if not isinstance(raw, list):
        return None
    return [str(day) for day in raw]


def _resolve_pending_package(
    base_path: Path, draft_id: str
) -> tuple[Path, Path, Path, dict[str, Any]] | tuple[None, None, None, str]:
    normalized = validate_draft_id(draft_id)
    if normalized is None:
        return (
            None,
            None,
            None,
            ERROR_PATH_TRAVERSAL
            if _looks_like_traversal(draft_id)
            else ERROR_DRAFT_ID_INVALID,
        )

    md_rel, png_rel, meta_rel = pending_paths_for_slug(normalized)
    md_path = base_path / md_rel
    png_path = base_path / png_rel
    meta_path = base_path / meta_rel
    pending = _pending_dir(base_path)

    for candidate in (md_path, meta_path, png_path):
        if not _verify_under(base_path, candidate, pending):
            return None, None, None, ERROR_PATH_TRAVERSAL

    if not meta_path.is_file():
        return None, None, None, ERROR_DRAFT_NOT_FOUND

    sidecar = _load_sidecar(meta_path)
    if sidecar is None:
        return None, None, None, ERROR_SIDECAR_INVALID

    return md_path, png_path, meta_path, sidecar


def _resolve_ready_promoted(
    base_path: Path, draft_id: str
) -> tuple[Path, Path, Path, dict[str, Any]] | None:
    """Return ready package when already promoted with matching provenance."""
    normalized = validate_draft_id(draft_id)
    if normalized is None:
        return None
    md_rel, png_rel, meta_rel = ready_paths_for_slug(normalized)
    md_path = base_path / md_rel
    png_path = base_path / png_rel
    meta_path = base_path / meta_rel
    ready = _ready_dir(base_path)
    for candidate in (md_path, png_path, meta_path):
        if not _verify_under(base_path, candidate, ready):
            return None
    if not (md_path.is_file() and png_path.is_file() and meta_path.is_file()):
        return None
    sidecar = _load_sidecar(meta_path)
    if sidecar is None:
        return None
    status = str(sidecar.get("status") or "").strip()
    origin = _as_optional_str(sidecar.get("origin"))
    slug = _as_optional_str(sidecar.get("slug")) or normalized
    if status != STATUS_PROMOTED:
        return None
    if origin != ORIGIN_FLOW_B and _as_optional_str(sidecar.get("flow")) != ORIGIN_FLOW_B:
        return None
    if slug != normalized and draft_id != normalized:
        return None
    return md_path, png_path, meta_path, sidecar


def _atomic_replace(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    os.replace(src, dest)


def _write_ready_sidecar(base_path: Path, metadata_relative_path: str, payload: dict[str, Any]) -> str | None:
    """Atomically write/overwrite sidecar under ready/ only."""
    normalized = metadata_relative_path.replace("\\", "/").lstrip("/")
    if not normalized.startswith(READY_PREFIX) or not normalized.endswith(".flow-b.json"):
        return ERROR_SIDECAR_WRITE_FAILED
    if ".." in Path(normalized).parts:
        return ERROR_SIDECAR_WRITE_FAILED
    path = base_path / normalized
    ready = _ready_dir(base_path)
    if not _verify_under(base_path, path, ready):
        return ERROR_SIDECAR_WRITE_FAILED
    try:
        raw = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        temp_path = path.with_suffix(path.suffix + ".tmp")
        with open(temp_path, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except OSError:
        try:
            temp_path = path.with_suffix(path.suffix + ".tmp")
            if temp_path.is_file():
                temp_path.unlink()
        except OSError:
            pass
        return ERROR_SIDECAR_WRITE_FAILED
    return None


def _success_note(*, dry_run: bool, already: bool) -> str:
    if dry_run:
        return (
            "Dry-run: would promote Markdown + PNG + sidecar to blog-posts/ready/. "
            "Does not publish the blog or LinkedIn."
        )
    if already:
        return (
            "Already promoted — artifacts under blog-posts/ready/. "
            "Flow A eligible; promote does not publish."
        )
    return (
        "Promoted to blog-posts/ready/. Flow A eligible for publish/package/schedule; "
        "promote does not publish the blog or LinkedIn."
    )


def promote_pending_approval_draft(
    base_path: Path,
    draft_id: str,
    *,
    promoted_by: str | None = None,
    dry_run: bool = False,
) -> DraftPromoteResult:
    """Promote an approved pending-approval package to ``blog-posts/ready/``."""
    normalized = validate_draft_id(draft_id)
    if normalized is None:
        code = (
            ERROR_PATH_TRAVERSAL
            if _looks_like_traversal(draft_id)
            else ERROR_DRAFT_ID_INVALID
        )
        return _failed(draft_id, code, dry_run=dry_run)

    by_value = (promoted_by or "").strip() or DEFAULT_PROMOTED_BY

    # Idempotent path: already under ready/
    ready_pkg = _resolve_ready_promoted(base_path, normalized)
    if ready_pkg is not None:
        md_path, png_path, meta_path, sidecar = ready_pkg
        md_rel, png_rel, meta_rel = ready_paths_for_slug(normalized)
        return DraftPromoteResult(
            status=STATUS_PROMOTED,
            draft_id=normalized,
            promoted=True,
            promotion_pending=False,
            already_promoted=True,
            dry_run=dry_run,
            blog_relative_path=md_rel,
            image_relative_path=png_rel,
            metadata_relative_path=meta_rel,
            approved_at_utc=_as_optional_str(sidecar.get("approved_at_utc")),
            approved_by=_as_optional_str(sidecar.get("approved_by")),
            promoted_at_utc=_as_optional_str(sidecar.get("promoted_at_utc")),
            promoted_by=_as_optional_str(sidecar.get("promoted_by")),
            origin=ORIGIN_FLOW_B,
            target_week=_as_optional_str(sidecar.get("target_week")),
            empty_days=_empty_days_from_sidecar(sidecar),
            flow_a_eligible=True,
            operator_note=_success_note(dry_run=dry_run, already=True),
        )

    md_path, png_path, meta_path, sidecar_or_err = _resolve_pending_package(
        base_path, normalized
    )
    if md_path is None:
        return _failed(normalized, str(sidecar_or_err), dry_run=dry_run)
    assert png_path is not None and meta_path is not None
    sidecar = sidecar_or_err  # type: ignore[assignment]
    assert isinstance(sidecar, dict)

    current = str(sidecar.get("status") or "").strip()
    if current == STATUS_REJECTED:
        return _failed(normalized, ERROR_DRAFT_REJECTED, dry_run=dry_run)
    if current in {
        STATUS_PENDING_APPROVAL,
        STATUS_PENDING_APPROVAL_IMAGE_FAILED,
        "",
    }:
        return _failed(normalized, ERROR_DRAFT_NOT_APPROVED, dry_run=dry_run)
    if current == STATUS_PROMOTED:
        # Sidecar says promoted but ready package missing → fail closed
        return _failed(normalized, ERROR_DRAFT_NOT_FOUND, dry_run=dry_run)
    if current != STATUS_APPROVED:
        return _failed(normalized, ERROR_DRAFT_NOT_APPROVED, dry_run=dry_run)

    approved_at = _as_optional_str(sidecar.get("approved_at_utc"))
    approved_by = _as_optional_str(sidecar.get("approved_by"))
    if not approved_at:
        return _failed(normalized, ERROR_APPROVAL_METADATA_MISSING, dry_run=dry_run)

    if not md_path.is_file():
        return _failed(normalized, ERROR_DRAFT_NOT_FOUND, dry_run=dry_run)
    if not png_path.is_file():
        return _failed(normalized, ERROR_DRAFT_PAIR_INCOMPLETE, dry_run=dry_run)

    md_rel, png_rel, meta_rel = ready_paths_for_slug(normalized)
    ready_md = base_path / md_rel
    ready_png = base_path / png_rel
    ready_meta = base_path / meta_rel
    ready = _ready_dir(base_path)
    for dest in (ready_md, ready_png, ready_meta):
        if not _verify_under(base_path, dest, ready):
            return _failed(normalized, ERROR_PATH_TRAVERSAL, dry_run=dry_run)
        if dest.exists():
            return _failed(normalized, ERROR_READY_COLLISION, dry_run=dry_run)

    promoted_at = utc_now_iso()
    empty_days = _empty_days_from_sidecar(sidecar)
    target_week = _as_optional_str(sidecar.get("target_week"))

    if dry_run:
        return DraftPromoteResult(
            status=STATUS_PROMOTED,
            draft_id=normalized,
            promoted=True,
            promotion_pending=False,
            already_promoted=False,
            dry_run=True,
            blog_relative_path=md_rel,
            image_relative_path=png_rel,
            metadata_relative_path=meta_rel,
            approved_at_utc=approved_at,
            approved_by=approved_by,
            promoted_at_utc=promoted_at,
            promoted_by=by_value,
            origin=ORIGIN_FLOW_B,
            target_week=target_week,
            empty_days=empty_days,
            flow_a_eligible=True,
            operator_note=_success_note(dry_run=True, already=False),
        )

    # Move md + png first; write sidecar under ready; remove pending sidecar.
    try:
        _ready_dir(base_path).mkdir(parents=True, exist_ok=True)
        _atomic_replace(md_path, ready_md)
        _atomic_replace(png_path, ready_png)
    except OSError:
        # Best-effort rollback if png move failed after md moved
        try:
            if ready_md.is_file() and not md_path.exists():
                _atomic_replace(ready_md, md_path)
        except OSError:
            pass
        return _failed(normalized, ERROR_PROMOTE_MOVE_FAILED, dry_run=False)

    updated = dict(sidecar)
    updated["status"] = STATUS_PROMOTED
    updated["promoted_at_utc"] = promoted_at
    updated["promoted_by"] = by_value
    updated["approved_at_utc"] = approved_at
    if approved_by:
        updated["approved_by"] = approved_by
    updated["draft_id"] = normalized
    updated["slug"] = _as_optional_str(sidecar.get("slug")) or normalized
    updated["blog_relative_path"] = md_rel
    updated["image_relative_path"] = png_rel
    updated["metadata_relative_path"] = meta_rel
    updated["origin"] = ORIGIN_FLOW_B
    if target_week is not None:
        updated["target_week"] = target_week
    if empty_days is not None:
        updated["empty_days"] = empty_days

    write_err = _write_ready_sidecar(base_path, meta_rel, updated)
    if write_err:
        # Leave md/png in ready; operator can fix sidecar — still fail closed on promote
        return DraftPromoteResult(
            status="failed",
            draft_id=normalized,
            promoted=False,
            dry_run=False,
            blog_relative_path=md_rel,
            image_relative_path=png_rel,
            error_code=write_err,
            error=_operator_message(write_err),
        )

    # Remove pending sidecar (and any leftover pending files)
    try:
        if meta_path.is_file():
            meta_path.unlink()
    except OSError:
        pass

    return DraftPromoteResult(
        status=STATUS_PROMOTED,
        draft_id=normalized,
        promoted=True,
        promotion_pending=False,
        already_promoted=False,
        dry_run=False,
        blog_relative_path=md_rel,
        image_relative_path=png_rel,
        metadata_relative_path=meta_rel,
        approved_at_utc=approved_at,
        approved_by=approved_by,
        promoted_at_utc=promoted_at,
        promoted_by=by_value,
        origin=ORIGIN_FLOW_B,
        target_week=target_week,
        empty_days=empty_days,
        flow_a_eligible=True,
        operator_note=_success_note(dry_run=False, already=False),
    )


def _operator_message(code: str) -> str:
    messages = {
        ERROR_DRAFT_NOT_FOUND: "Draft not found under pending-approval/ (or ready/ for re-promote).",
        ERROR_DRAFT_ID_INVALID: "draft_id is invalid.",
        ERROR_PATH_TRAVERSAL: "draft_id path traversal is not allowed.",
        ERROR_SIDECAR_INVALID: "Draft sidecar metadata is invalid or unreadable.",
        ERROR_DRAFT_NOT_APPROVED: "Draft is not approved; promote requires a prior approve decision.",
        ERROR_DRAFT_REJECTED: "Rejected drafts cannot be promoted.",
        ERROR_DRAFT_PAIR_INCOMPLETE: "Promote requires a complete Markdown + PNG pair.",
        ERROR_READY_COLLISION: "A file with this basename already exists under blog-posts/ready/.",
        ERROR_PROMOTE_MOVE_FAILED: "Failed to move draft artifacts to blog-posts/ready/.",
        ERROR_APPROVAL_METADATA_MISSING: "Approved draft is missing durable approval metadata (approved_at_utc).",
        ERROR_SIDECAR_WRITE_FAILED: "Failed to write promoted sidecar under blog-posts/ready/.",
    }
    return messages.get(code, "Flow B draft promote action failed.")
