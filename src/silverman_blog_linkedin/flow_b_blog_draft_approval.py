"""US-080: list / detail / approve / reject Flow B pending-approval drafts.

Reads Markdown + PNG + ``.flow-b.json`` packages under ``blog-posts/pending-approval/``.
Approve and reject update sidecar status only — MUST NOT promote to ``blog-posts/ready/``,
invoke Flow A publish/package/schedule, or call LinkedIn API publish.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from silverman_blog_linkedin.draft_writer import sanitize_filename_segment
from silverman_blog_linkedin.flow_b_pending_approval_writer import (
    PENDING_APPROVAL_PREFIX,
    PENDING_APPROVAL_RELATIVE,
    READY_PREFIX,
    overwrite_pending_approval_sidecar,
    pending_paths_for_slug,
)
from silverman_blog_linkedin.run_metadata import utc_now_iso

STATUS_PENDING_APPROVAL = "pending_approval"
STATUS_PENDING_APPROVAL_IMAGE_FAILED = "pending_approval_image_failed"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"

DEFAULT_LIST_STATUSES = frozenset(
    {
        STATUS_PENDING_APPROVAL,
        STATUS_PENDING_APPROVAL_IMAGE_FAILED,
        STATUS_APPROVED,
    }
)
APPROVABLE_STATUSES = frozenset(
    {STATUS_PENDING_APPROVAL, STATUS_PENDING_APPROVAL_IMAGE_FAILED, STATUS_APPROVED}
)
REJECTABLE_STATUSES = frozenset(
    {
        STATUS_PENDING_APPROVAL,
        STATUS_PENDING_APPROVAL_IMAGE_FAILED,
        STATUS_APPROVED,
        STATUS_REJECTED,
    }
)

ERROR_DRAFT_NOT_FOUND = "draft_not_found"
ERROR_DRAFT_ID_INVALID = "draft_id_invalid"
ERROR_DRAFT_ALREADY_REJECTED = "draft_already_rejected"
ERROR_DRAFT_NOT_APPROVABLE = "draft_not_approvable"
ERROR_DRAFT_NOT_REJECTABLE = "draft_not_rejectable"
ERROR_SIDECAR_INVALID = "draft_sidecar_invalid"
ERROR_SIDECAR_WRITE_FAILED = "draft_sidecar_write_failed"
ERROR_IMAGE_NOT_FOUND = "draft_image_not_found"
ERROR_PATH_TRAVERSAL = "draft_path_traversal"

_DRAFT_ID_SAFE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

IMAGE_URL_TEMPLATE = "/flow-b/pending-approval-drafts/{draft_id}/image"


@dataclass(frozen=True)
class PendingDraftSummary:
    """List-item DTO for a pending-approval package."""

    draft_id: str
    slug: str
    title: str
    topic_id: str | None
    thesis: str | None
    referent_positioning: str | None
    rationale: str | None
    status: str
    blog_relative_path: str | None
    image_relative_path: str | None
    metadata_relative_path: str | None
    image_url: str | None
    generated_at_utc: str | None
    target_week: str | None = None
    empty_days: list[str] | None = None
    image_status: str | None = None
    image_warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "draft_id": self.draft_id,
            "slug": self.slug,
            "title": self.title,
            "topic_id": self.topic_id,
            "thesis": self.thesis,
            "referent_positioning": self.referent_positioning,
            "rationale": self.rationale,
            "status": self.status,
            "blog_relative_path": self.blog_relative_path,
            "image_relative_path": self.image_relative_path,
            "metadata_relative_path": self.metadata_relative_path,
            "image_url": self.image_url,
            "generated_at_utc": self.generated_at_utc,
        }
        if self.target_week is not None:
            payload["target_week"] = self.target_week
        if self.empty_days is not None:
            payload["empty_days"] = list(self.empty_days)
        if self.image_status is not None:
            payload["image_status"] = self.image_status
        if self.image_warning is not None:
            payload["image_warning"] = self.image_warning
        return payload


@dataclass(frozen=True)
class PendingDraftDetail(PendingDraftSummary):
    """Detail DTO including Markdown body."""

    body_markdown: str = ""
    approved_at_utc: str | None = None
    approved_by: str | None = None
    rejected_at_utc: str | None = None
    rejection_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload["body_markdown"] = self.body_markdown
        if self.approved_at_utc is not None:
            payload["approved_at_utc"] = self.approved_at_utc
        if self.approved_by is not None:
            payload["approved_by"] = self.approved_by
        if self.rejected_at_utc is not None:
            payload["rejected_at_utc"] = self.rejected_at_utc
        if self.rejection_reason is not None:
            payload["rejection_reason"] = self.rejection_reason
        return payload


@dataclass(frozen=True)
class PendingDraftListResult:
    status: Literal["ok"]
    drafts: list[PendingDraftSummary] = field(default_factory=list)
    observed_at_utc: str = ""
    filter_status: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "drafts": [draft.to_dict() for draft in self.drafts],
            "observed_at_utc": self.observed_at_utc,
            "filter_status": self.filter_status,
            "count": len(self.drafts),
        }


@dataclass(frozen=True)
class DraftDecisionResult:
    """Approve or reject outcome (decision only — no promote)."""

    status: str
    draft_id: str
    promoted: bool = False
    promotion_pending: bool = True
    dry_run: bool = False
    blog_relative_path: str | None = None
    image_relative_path: str | None = None
    metadata_relative_path: str | None = None
    approved_at_utc: str | None = None
    approved_by: str | None = None
    rejected_at_utc: str | None = None
    rejection_reason: str | None = None
    image_warning: str | None = None
    operator_note: str | None = None
    error_code: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status,
            "draft_id": self.draft_id,
            "promoted": False,
            "promotion_pending": self.promotion_pending
            if self.status == STATUS_APPROVED
            else False,
            "dry_run": self.dry_run,
            "blog_relative_path": self.blog_relative_path,
            "image_relative_path": self.image_relative_path,
            "metadata_relative_path": self.metadata_relative_path,
        }
        if self.approved_at_utc is not None:
            payload["approved_at_utc"] = self.approved_at_utc
        if self.approved_by is not None:
            payload["approved_by"] = self.approved_by
        if self.rejected_at_utc is not None:
            payload["rejected_at_utc"] = self.rejected_at_utc
        if self.rejection_reason is not None:
            payload["rejection_reason"] = self.rejection_reason
        if self.image_warning is not None:
            payload["image_warning"] = self.image_warning
        if self.operator_note is not None:
            payload["operator_note"] = self.operator_note
        if self.error_code is not None:
            payload["error_code"] = self.error_code
        if self.error is not None:
            payload["error"] = self.error
        return payload


def validate_draft_id(draft_id: str) -> str | None:
    """Return normalized draft_id or None if invalid / traversal."""
    if not isinstance(draft_id, str):
        return None
    raw = draft_id.strip()
    if not raw or len(raw) > 200:
        return None
    if raw != sanitize_filename_segment(raw).lower():
        return None
    if ".." in raw or "/" in raw or "\\" in raw:
        return None
    parts = PurePosixPath(raw).parts
    if len(parts) != 1 or ".." in parts:
        return None
    if not _DRAFT_ID_SAFE.match(raw):
        return None
    return raw


def _pending_dir(base_path: Path) -> Path:
    return base_path / PENDING_APPROVAL_RELATIVE


def _verify_resolved_under_pending(base_path: Path, candidate: Path) -> bool:
    pending_dir = _pending_dir(base_path).resolve()
    try:
        resolved = candidate.resolve()
        return resolved.is_relative_to(pending_dir)
    except (OSError, ValueError):
        return False


def _relative_under_pending(base_path: Path, path: Path) -> str | None:
    if not _verify_resolved_under_pending(base_path, path):
        return None
    try:
        rel = path.resolve().relative_to(base_path.resolve())
    except (OSError, ValueError):
        return None
    normalized = rel.as_posix()
    if not normalized.startswith(PENDING_APPROVAL_PREFIX):
        return None
    if normalized.startswith(READY_PREFIX):
        return None
    return normalized


def _title_from_markdown(text: str, *, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            if title:
                return title
        if stripped.startswith("title:"):
            # YAML-ish front matter line without full parser
            value = stripped[6:].strip().strip("\"'")
            if value:
                return value
    return fallback


def _load_sidecar(path: Path) -> dict[str, Any] | None:
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _image_warning_for_status(status: str, image_status: str | None) -> str | None:
    if status == STATUS_PENDING_APPROVAL_IMAGE_FAILED or image_status == "failed":
        return (
            "Hero image is missing or failed; approve gates text only. "
            "US-081 promote may still require a complete Markdown + PNG pair."
        )
    return None


def _summary_from_package(
    base_path: Path,
    *,
    draft_id: str,
    md_path: Path,
    png_path: Path,
    meta_path: Path,
    sidecar: dict[str, Any],
) -> PendingDraftSummary | None:
    status = str(sidecar.get("status") or "").strip() or STATUS_PENDING_APPROVAL
    thesis = _as_optional_str(sidecar.get("thesis"))
    try:
        body = md_path.read_text(encoding="utf-8")
    except OSError:
        body = ""
    title = _title_from_markdown(
        body,
        fallback=thesis or draft_id.replace("-", " "),
    )
    blog_rel = _as_optional_str(sidecar.get("blog_relative_path")) or _relative_under_pending(
        base_path, md_path
    )
    image_rel = _as_optional_str(
        sidecar.get("image_relative_path")
    ) or _relative_under_pending(base_path, png_path)
    meta_rel = _as_optional_str(
        sidecar.get("metadata_relative_path")
    ) or _relative_under_pending(base_path, meta_path)
    if meta_rel is None:
        meta_rel = f"{PENDING_APPROVAL_PREFIX}{draft_id}.flow-b.json"

    image_status = _as_optional_str(sidecar.get("image_status"))
    empty_days_raw = sidecar.get("empty_days")
    empty_days: list[str] | None = None
    if isinstance(empty_days_raw, list):
        empty_days = [str(day) for day in empty_days_raw]

    image_url = None
    if png_path.is_file() and _verify_resolved_under_pending(base_path, png_path):
        image_url = IMAGE_URL_TEMPLATE.format(draft_id=draft_id)

    return PendingDraftSummary(
        draft_id=draft_id,
        slug=str(sidecar.get("slug") or draft_id),
        title=title,
        topic_id=_as_optional_str(sidecar.get("topic_id")),
        thesis=thesis,
        referent_positioning=_as_optional_str(sidecar.get("referent_positioning")),
        rationale=_as_optional_str(sidecar.get("rationale")),
        status=status,
        blog_relative_path=blog_rel,
        image_relative_path=image_rel,
        metadata_relative_path=meta_rel,
        image_url=image_url,
        generated_at_utc=_as_optional_str(sidecar.get("generated_at_utc")),
        target_week=_as_optional_str(sidecar.get("target_week")),
        empty_days=empty_days,
        image_status=image_status,
        image_warning=_image_warning_for_status(status, image_status),
    )


def _resolve_package(
    base_path: Path, draft_id: str
) -> tuple[Path, Path, Path, dict[str, Any]] | tuple[None, None, None, str]:
    """Return (md, png, meta, sidecar) or (None, None, None, error_code)."""
    normalized = validate_draft_id(draft_id)
    if normalized is None:
        return None, None, None, ERROR_PATH_TRAVERSAL if _looks_like_traversal(
            draft_id
        ) else ERROR_DRAFT_ID_INVALID

    md_rel, png_rel, meta_rel = pending_paths_for_slug(normalized)
    md_path = base_path / md_rel
    png_path = base_path / png_rel
    meta_path = base_path / meta_rel

    for candidate in (md_path, meta_path):
        if not _verify_resolved_under_pending(base_path, candidate):
            return None, None, None, ERROR_PATH_TRAVERSAL

    if not md_path.is_file() or not meta_path.is_file():
        return None, None, None, ERROR_DRAFT_NOT_FOUND

    sidecar = _load_sidecar(meta_path)
    if sidecar is None:
        return None, None, None, ERROR_SIDECAR_INVALID

    return md_path, png_path, meta_path, sidecar


def _looks_like_traversal(draft_id: str) -> bool:
    if not isinstance(draft_id, str):
        return False
    return ".." in draft_id or "/" in draft_id or "\\" in draft_id


def list_pending_approval_drafts(
    base_path: Path,
    *,
    status_filter: str | None = None,
) -> PendingDraftListResult:
    """Scan pending-approval for complete packages; empty folder → empty list."""
    pending = _pending_dir(base_path)
    drafts: list[PendingDraftSummary] = []
    if pending.is_dir():
        for meta_path in sorted(pending.glob("*.flow-b.json")):
            if not meta_path.is_file():
                continue
            draft_id = meta_path.name[: -len(".flow-b.json")]
            if validate_draft_id(draft_id) is None:
                continue
            if not _verify_resolved_under_pending(base_path, meta_path):
                continue
            md_path = pending / f"{draft_id}.md"
            png_path = pending / f"{draft_id}.png"
            if not md_path.is_file():
                continue
            sidecar = _load_sidecar(meta_path)
            if sidecar is None:
                continue
            summary = _summary_from_package(
                base_path,
                draft_id=draft_id,
                md_path=md_path,
                png_path=png_path,
                meta_path=meta_path,
                sidecar=sidecar,
            )
            if summary is None:
                continue
            if status_filter:
                if summary.status != status_filter:
                    continue
            elif summary.status not in DEFAULT_LIST_STATUSES:
                continue
            drafts.append(summary)

    return PendingDraftListResult(
        status="ok",
        drafts=drafts,
        observed_at_utc=utc_now_iso(),
        filter_status=status_filter,
    )


def get_pending_approval_draft(
    base_path: Path, draft_id: str
) -> PendingDraftDetail | DraftDecisionResult:
    """Return detail DTO or a failure-shaped DraftDecisionResult."""
    md_path, png_path, meta_path, sidecar_or_err = _resolve_package(base_path, draft_id)
    if md_path is None:
        code = str(sidecar_or_err)
        return DraftDecisionResult(
            status="failed",
            draft_id=draft_id,
            promotion_pending=False,
            error_code=code,
            error=_operator_message(code),
        )
    assert png_path is not None and meta_path is not None
    sidecar = sidecar_or_err  # type: ignore[assignment]
    assert isinstance(sidecar, dict)

    summary = _summary_from_package(
        base_path,
        draft_id=validate_draft_id(draft_id) or draft_id,
        md_path=md_path,
        png_path=png_path,
        meta_path=meta_path,
        sidecar=sidecar,
    )
    assert summary is not None
    try:
        body = md_path.read_text(encoding="utf-8")
    except OSError:
        body = ""

    return PendingDraftDetail(
        draft_id=summary.draft_id,
        slug=summary.slug,
        title=summary.title,
        topic_id=summary.topic_id,
        thesis=summary.thesis,
        referent_positioning=summary.referent_positioning,
        rationale=summary.rationale,
        status=summary.status,
        blog_relative_path=summary.blog_relative_path,
        image_relative_path=summary.image_relative_path,
        metadata_relative_path=summary.metadata_relative_path,
        image_url=summary.image_url,
        generated_at_utc=summary.generated_at_utc,
        target_week=summary.target_week,
        empty_days=summary.empty_days,
        image_status=summary.image_status,
        image_warning=summary.image_warning,
        body_markdown=body,
        approved_at_utc=_as_optional_str(sidecar.get("approved_at_utc")),
        approved_by=_as_optional_str(sidecar.get("approved_by")),
        rejected_at_utc=_as_optional_str(sidecar.get("rejected_at_utc")),
        rejection_reason=_as_optional_str(sidecar.get("rejection_reason")),
    )


def resolve_pending_approval_image_path(
    base_path: Path, draft_id: str
) -> tuple[Path | None, str | None]:
    """Return confined PNG path or (None, error_code)."""
    md_path, png_path, meta_path, sidecar_or_err = _resolve_package(base_path, draft_id)
    if md_path is None:
        return None, str(sidecar_or_err)
    assert png_path is not None
    if not png_path.is_file() or not _verify_resolved_under_pending(base_path, png_path):
        return None, ERROR_IMAGE_NOT_FOUND
    return png_path, None


def approve_pending_approval_draft(
    base_path: Path,
    draft_id: str,
    *,
    approved_by: str | None = None,
    dry_run: bool = False,
) -> DraftDecisionResult:
    """Record approve decision in sidecar; MUST NOT promote to ready/."""
    md_path, png_path, meta_path, sidecar_or_err = _resolve_package(base_path, draft_id)
    if md_path is None:
        code = str(sidecar_or_err)
        return DraftDecisionResult(
            status="failed",
            draft_id=draft_id,
            promotion_pending=False,
            dry_run=dry_run,
            error_code=code,
            error=_operator_message(code),
        )
    assert png_path is not None and meta_path is not None
    sidecar = sidecar_or_err  # type: ignore[assignment]
    assert isinstance(sidecar, dict)

    normalized = validate_draft_id(draft_id) or draft_id
    current = str(sidecar.get("status") or "").strip()
    if current == STATUS_REJECTED:
        return DraftDecisionResult(
            status="failed",
            draft_id=normalized,
            promotion_pending=False,
            dry_run=dry_run,
            blog_relative_path=_as_optional_str(sidecar.get("blog_relative_path")),
            image_relative_path=_as_optional_str(sidecar.get("image_relative_path")),
            metadata_relative_path=_relative_under_pending(base_path, meta_path),
            error_code=ERROR_DRAFT_ALREADY_REJECTED,
            error=_operator_message(ERROR_DRAFT_ALREADY_REJECTED),
        )
    if current not in APPROVABLE_STATUSES:
        return DraftDecisionResult(
            status="failed",
            draft_id=normalized,
            promotion_pending=False,
            dry_run=dry_run,
            error_code=ERROR_DRAFT_NOT_APPROVABLE,
            error=_operator_message(ERROR_DRAFT_NOT_APPROVABLE),
        )

    approved_at = _as_optional_str(sidecar.get("approved_at_utc")) or utc_now_iso()
    by_value = (approved_by or "").strip() or _as_optional_str(
        sidecar.get("approved_by")
    ) or "operator"
    image_status = _as_optional_str(sidecar.get("image_status"))
    warning = _image_warning_for_status(current, image_status)
    meta_rel = _relative_under_pending(base_path, meta_path)
    blog_rel = _as_optional_str(sidecar.get("blog_relative_path")) or _relative_under_pending(
        base_path, md_path
    )
    image_rel = _as_optional_str(
        sidecar.get("image_relative_path")
    ) or _relative_under_pending(base_path, png_path)

    operator_note = (
        "Approved decision recorded. Promotion to blog-posts/ready/ remains US-081; "
        "Flow A eligibility is not complete."
    )

    if dry_run:
        return DraftDecisionResult(
            status=STATUS_APPROVED,
            draft_id=normalized,
            promoted=False,
            promotion_pending=True,
            dry_run=True,
            blog_relative_path=blog_rel,
            image_relative_path=image_rel,
            metadata_relative_path=meta_rel,
            approved_at_utc=approved_at,
            approved_by=by_value,
            image_warning=warning,
            operator_note=operator_note,
        )

    updated = dict(sidecar)
    updated["status"] = STATUS_APPROVED
    updated["approved_at_utc"] = approved_at
    updated["approved_by"] = by_value
    # Clear reject fields if previously set (should not happen for rejected)
    updated.pop("rejected_at_utc", None)
    updated.pop("rejection_reason", None)

    write_err = overwrite_pending_approval_sidecar(
        base_path, meta_rel or f"{PENDING_APPROVAL_PREFIX}{normalized}.flow-b.json", updated
    )
    if write_err:
        return DraftDecisionResult(
            status="failed",
            draft_id=normalized,
            promotion_pending=False,
            dry_run=False,
            error_code=ERROR_SIDECAR_WRITE_FAILED,
            error=_operator_message(ERROR_SIDECAR_WRITE_FAILED),
        )

    return DraftDecisionResult(
        status=STATUS_APPROVED,
        draft_id=normalized,
        promoted=False,
        promotion_pending=True,
        dry_run=False,
        blog_relative_path=blog_rel,
        image_relative_path=image_rel,
        metadata_relative_path=meta_rel,
        approved_at_utc=approved_at,
        approved_by=by_value,
        image_warning=warning,
        operator_note=operator_note,
    )


def reject_pending_approval_draft(
    base_path: Path,
    draft_id: str,
    *,
    rejection_reason: str | None = None,
    dry_run: bool = False,
) -> DraftDecisionResult:
    """Record reject; MUST NOT promote to ready/. May supersede approved-but-not-promoted."""
    md_path, png_path, meta_path, sidecar_or_err = _resolve_package(base_path, draft_id)
    if md_path is None:
        code = str(sidecar_or_err)
        return DraftDecisionResult(
            status="failed",
            draft_id=draft_id,
            promotion_pending=False,
            dry_run=dry_run,
            error_code=code,
            error=_operator_message(code),
        )
    assert png_path is not None and meta_path is not None
    sidecar = sidecar_or_err  # type: ignore[assignment]
    assert isinstance(sidecar, dict)

    normalized = validate_draft_id(draft_id) or draft_id
    current = str(sidecar.get("status") or "").strip()
    if current not in REJECTABLE_STATUSES:
        return DraftDecisionResult(
            status="failed",
            draft_id=normalized,
            promotion_pending=False,
            dry_run=dry_run,
            error_code=ERROR_DRAFT_NOT_REJECTABLE,
            error=_operator_message(ERROR_DRAFT_NOT_REJECTABLE),
        )

    rejected_at = utc_now_iso()
    reason = (rejection_reason or "").strip() or None
    if reason and len(reason) > 2000:
        reason = reason[:2000]
    # Idempotent re-reject: preserve prior timestamp if already rejected and no new reason
    if current == STATUS_REJECTED:
        rejected_at = _as_optional_str(sidecar.get("rejected_at_utc")) or rejected_at
        if reason is None:
            reason = _as_optional_str(sidecar.get("rejection_reason"))

    meta_rel = _relative_under_pending(base_path, meta_path)
    blog_rel = _as_optional_str(sidecar.get("blog_relative_path")) or _relative_under_pending(
        base_path, md_path
    )
    image_rel = _as_optional_str(
        sidecar.get("image_relative_path")
    ) or _relative_under_pending(base_path, png_path)

    operator_note = (
        "Draft rejected/blocked. Remains under pending-approval/ and is not "
        "eligible for promotion to ready/."
    )

    if dry_run:
        return DraftDecisionResult(
            status=STATUS_REJECTED,
            draft_id=normalized,
            promoted=False,
            promotion_pending=False,
            dry_run=True,
            blog_relative_path=blog_rel,
            image_relative_path=image_rel,
            metadata_relative_path=meta_rel,
            rejected_at_utc=rejected_at,
            rejection_reason=reason,
            operator_note=operator_note,
        )

    updated = dict(sidecar)
    updated["status"] = STATUS_REJECTED
    updated["rejected_at_utc"] = rejected_at
    if reason is not None:
        updated["rejection_reason"] = reason
    # Clear approve fields when superseding approved-but-not-promoted
    updated.pop("approved_at_utc", None)
    updated.pop("approved_by", None)

    write_err = overwrite_pending_approval_sidecar(
        base_path, meta_rel or f"{PENDING_APPROVAL_PREFIX}{normalized}.flow-b.json", updated
    )
    if write_err:
        return DraftDecisionResult(
            status="failed",
            draft_id=normalized,
            promotion_pending=False,
            dry_run=False,
            error_code=ERROR_SIDECAR_WRITE_FAILED,
            error=_operator_message(ERROR_SIDECAR_WRITE_FAILED),
        )

    return DraftDecisionResult(
        status=STATUS_REJECTED,
        draft_id=normalized,
        promoted=False,
        promotion_pending=False,
        dry_run=False,
        blog_relative_path=blog_rel,
        image_relative_path=image_rel,
        metadata_relative_path=meta_rel,
        rejected_at_utc=rejected_at,
        rejection_reason=reason,
        operator_note=operator_note,
    )


def _as_optional_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _operator_message(code: str) -> str:
    messages = {
        ERROR_DRAFT_NOT_FOUND: "Draft not found under blog-posts/pending-approval/.",
        ERROR_DRAFT_ID_INVALID: "draft_id is invalid.",
        ERROR_PATH_TRAVERSAL: "draft_id path traversal is not allowed.",
        ERROR_DRAFT_ALREADY_REJECTED: "Draft is already rejected and cannot be approved.",
        ERROR_DRAFT_NOT_APPROVABLE: "Draft status is not approvable.",
        ERROR_DRAFT_NOT_REJECTABLE: "Draft status is not rejectable.",
        ERROR_SIDECAR_INVALID: "Draft sidecar metadata is invalid or unreadable.",
        ERROR_SIDECAR_WRITE_FAILED: "Failed to update draft sidecar metadata.",
        ERROR_IMAGE_NOT_FOUND: "Draft hero image was not found under pending-approval/.",
    }
    return messages.get(code, "Flow B draft approval action failed.")
