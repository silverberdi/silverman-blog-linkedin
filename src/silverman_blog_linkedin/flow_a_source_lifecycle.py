"""Flow A physical source lifecycle completion after distribution scheduling."""

from __future__ import annotations

import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.campaign_lifecycle import (
    ACTOR_WORKER,
    EXECUTION_STATE_IDLE,
    PHYSICAL_MOVE_STATE_COMPLETED,
    PHYSICAL_MOVE_STATE_FAILED,
    PHYSICAL_MOVE_STATE_PARTIAL,
    PROCESSED_SOURCE_PREFIX,
    QUEUED_SOURCE_PREFIX,
    READY_SOURCE_PREFIX,
    SOURCE_LOCATION_PROCESSED,
    SOURCE_LOCATION_QUEUED,
    normalize_source_file_status,
    STATE_DISTRIBUTION_COMPLETE,
    STATE_DISTRIBUTION_SCHEDULED,
    STATE_FLOW_A_COMPLETE,
    compute_source_content_sha256,
    read_campaign_metadata,
    resolve_campaign_source_paths,
    transition_state,
    write_campaign_metadata,
)
from silverman_blog_linkedin.file_reader import normalize_relative_path
from silverman_blog_linkedin.run_metadata import utc_now_iso

FLOW_A_SOURCE_MOVE_FAILED = "flow_a_source_move_failed"
FLOW_A_SOURCE_MOVE_PARTIAL = "flow_a_source_move_partial"
FLOW_A_SOURCE_LIFECYCLE_PREMATURE = "flow_a_source_lifecycle_premature"
FLOW_A_SOURCE_MOVE_COLLISION_EXHAUSTED = "flow_a_source_move_collision_exhausted"
FLOW_A_SOURCE_CAMPAIGN_NOT_FOUND = "flow_a_source_campaign_not_found"
FLOW_A_SOURCE_READY_MISSING = "flow_a_source_ready_missing"
FLOW_A_SOURCE_QUEUED_MISSING = "flow_a_source_queued_missing"

LIFECYCLE_COMPLETION_ELIGIBLE_STATES = frozenset(
    {
        STATE_DISTRIBUTION_SCHEDULED,
        STATE_DISTRIBUTION_COMPLETE,
    }
)

MAX_COLLISION_SUFFIX = 99

REPAIR_MOVE_FAILED_WARNING = (
    "flow_a_source_move_failed: scheduling succeeded; repair source files under "
    "blog-posts/processed/ or blog-posts/ready/ and retry lifecycle completion "
    "by campaign_id"
)
REPAIR_MOVE_PARTIAL_WARNING = (
    "flow_a_source_move_partial: Markdown moved but companion image move failed; "
    "repair image placement and retry lifecycle completion by campaign_id"
)


@dataclass
class FlowASourceLifecycleResult:
    status: str
    campaign_id: str | None = None
    original_source_relative_path: str | None = None
    processed_source_relative_path: str | None = None
    original_image_relative_path: str | None = None
    processed_image_relative_path: str | None = None
    source_file_status: dict[str, Any] = field(default_factory=dict)
    already_processed: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata_written: bool = False
    metadata_error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _failed_result(
    *,
    campaign: dict[str, Any] | None,
    errors: list[str],
    warnings: list[str] | None = None,
    metadata_written: bool = False,
    metadata_error_code: str | None = None,
) -> FlowASourceLifecycleResult:
    source_status = dict((campaign or {}).get("source_file_status") or {})
    md_path, image_path = (
        resolve_campaign_source_paths(campaign) if campaign else (None, None)
    )
    return FlowASourceLifecycleResult(
        status="failed",
        campaign_id=campaign.get("campaign_id") if campaign else None,
        original_source_relative_path=(
            campaign.get("original_source_relative_path") if campaign else None
        ),
        processed_source_relative_path=(
            campaign.get("processed_source_relative_path") if campaign else md_path
        ),
        original_image_relative_path=(
            campaign.get("original_image_relative_path") if campaign else None
        ),
        processed_image_relative_path=(
            campaign.get("processed_image_relative_path") if campaign else image_path
        ),
        source_file_status=source_status,
        errors=errors,
        warnings=warnings or [],
        metadata_written=metadata_written,
        metadata_error_code=metadata_error_code,
    )


def _skipped_result(campaign: dict[str, Any]) -> FlowASourceLifecycleResult:
    source_status = dict(campaign.get("source_file_status") or {})
    return FlowASourceLifecycleResult(
        status="skipped",
        campaign_id=campaign["campaign_id"],
        original_source_relative_path=campaign.get("original_source_relative_path"),
        processed_source_relative_path=campaign.get("processed_source_relative_path"),
        original_image_relative_path=campaign.get("original_image_relative_path"),
        processed_image_relative_path=campaign.get("processed_image_relative_path"),
        source_file_status=source_status,
        already_processed=True,
        warnings=list(campaign.get("warnings") or []),
    )


def _completed_result(
    campaign: dict[str, Any],
    *,
    metadata_written: bool,
    metadata_error_code: str | None = None,
) -> FlowASourceLifecycleResult:
    source_status = dict(campaign.get("source_file_status") or {})
    return FlowASourceLifecycleResult(
        status="completed",
        campaign_id=campaign["campaign_id"],
        original_source_relative_path=campaign.get("original_source_relative_path"),
        processed_source_relative_path=campaign.get("processed_source_relative_path"),
        original_image_relative_path=campaign.get("original_image_relative_path"),
        processed_image_relative_path=campaign.get("processed_image_relative_path"),
        source_file_status=source_status,
        warnings=list(campaign.get("warnings") or []),
        metadata_written=metadata_written,
        metadata_error_code=metadata_error_code,
    )


def _same_file(path_a: Path, path_b: Path) -> bool:
    if not path_a.is_file() or not path_b.is_file():
        return False
    try:
        return path_a.samefile(path_b)
    except OSError:
        pass
    try:
        return compute_source_content_sha256(path_a.read_bytes()) == (
            compute_source_content_sha256(path_b.read_bytes())
        )
    except OSError:
        return False


def _allocate_processed_target(
    source_path: Path,
    processed_dir: Path,
) -> tuple[Path | None, str | None, str | None]:
    """Pick a processed target path with deterministic collision suffixes."""
    stem = source_path.stem
    suffix = source_path.suffix
    candidate_names = [source_path.name] + [
        f"{stem}-processed-{index}{suffix}" for index in range(1, MAX_COLLISION_SUFFIX + 1)
    ]
    for name in candidate_names:
        target = processed_dir / name
        relative = f"{PROCESSED_SOURCE_PREFIX}{name}"
        if not target.exists():
            return target, relative, None
        if _same_file(source_path, target):
            return target, relative, None
    return None, None, FLOW_A_SOURCE_MOVE_COLLISION_EXHAUSTED


def _move_source_file(source_path: Path, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        source_path.rename(target_path)
    except OSError:
        shutil.move(str(source_path), str(target_path))


def _resolve_active_source_path(
    campaign: dict[str, Any],
    source_relative_path: str | None,
) -> str | None:
    """Resolve queued source path, with legacy ready/ fallback for pre-queue campaigns."""
    source_status = normalize_source_file_status(campaign.get("source_file_status"))
    location = source_status.get("location")

    if location == SOURCE_LOCATION_QUEUED or campaign.get("queued_source_relative_path"):
        queued = campaign.get("queued_source_relative_path")
        if isinstance(queued, str) and queued.strip():
            return normalize_relative_path(queued)
        active, _image = resolve_campaign_source_paths(campaign)
        if active and active.startswith(QUEUED_SOURCE_PREFIX):
            return active

    if source_relative_path:
        normalized = normalize_relative_path(source_relative_path)
        if normalized.startswith(QUEUED_SOURCE_PREFIX):
            return normalized
        if normalized.startswith(READY_SOURCE_PREFIX):
            return normalized

    original = campaign.get("original_source_relative_path")
    if isinstance(original, str) and original.strip():
        normalized = normalize_relative_path(original)
        if normalized.startswith(QUEUED_SOURCE_PREFIX) or normalized.startswith(
            READY_SOURCE_PREFIX
        ):
            return normalized

    active, _image = resolve_campaign_source_paths(campaign)
    if active and (
        active.startswith(QUEUED_SOURCE_PREFIX) or active.startswith(READY_SOURCE_PREFIX)
    ):
        return active

    source_relative = campaign.get("source_relative_path")
    if isinstance(source_relative, str) and source_relative.strip():
        normalized = normalize_relative_path(source_relative)
        if normalized.startswith(QUEUED_SOURCE_PREFIX) or normalized.startswith(
            READY_SOURCE_PREFIX
        ):
            return normalized
    return None


def _image_relative_path_for_source(source_relative: str, source_slug: str) -> str:
    if source_relative.startswith(QUEUED_SOURCE_PREFIX):
        return f"{QUEUED_SOURCE_PREFIX}{source_slug}.png"
    return f"{READY_SOURCE_PREFIX}{source_slug}.png"


def complete_flow_a_source_lifecycle(
    base_path: Path,
    *,
    campaign_id: str,
    source_relative_path: str | None = None,
) -> FlowASourceLifecycleResult:
    """Move Flow A source files from ready/ to processed/ after scheduling succeeds."""
    campaign = read_campaign_metadata(base_path, campaign_id)
    if campaign is None:
        return FlowASourceLifecycleResult(
            status="failed",
            campaign_id=campaign_id,
            errors=[FLOW_A_SOURCE_CAMPAIGN_NOT_FOUND],
        )

    state = campaign.get("state")
    source_status = campaign.setdefault("source_file_status", {})
    processed_md = campaign.get("processed_source_relative_path")
    if (
        source_status.get("location") == SOURCE_LOCATION_PROCESSED
        and isinstance(processed_md, str)
        and (base_path / processed_md).is_file()
    ):
        if state != STATE_FLOW_A_COMPLETE:
            try:
                if state == STATE_DISTRIBUTION_SCHEDULED:
                    transition_state(
                        campaign,
                        STATE_FLOW_A_COMPLETE,
                        reason="Flow A source lifecycle already processed on disk",
                        actor=ACTOR_WORKER,
                    )
                    write_result = write_campaign_metadata(
                        base_path, campaign_id, campaign
                    )
                    if not write_result.written:
                        return _failed_result(
                            campaign=campaign,
                            errors=[FLOW_A_SOURCE_MOVE_FAILED],
                            metadata_written=False,
                            metadata_error_code=write_result.error_code,
                        )
            except Exception:
                return _skipped_result(campaign)
        return _skipped_result(campaign)

    if state == STATE_FLOW_A_COMPLETE:
        return _skipped_result(campaign)

    if state not in LIFECYCLE_COMPLETION_ELIGIBLE_STATES:
        return _failed_result(
            campaign=campaign,
            errors=[FLOW_A_SOURCE_LIFECYCLE_PREMATURE],
        )

    ready_relative = _resolve_active_source_path(campaign, source_relative_path)
    if ready_relative is None:
        return _failed_result(
            campaign=campaign,
            errors=[FLOW_A_SOURCE_QUEUED_MISSING, FLOW_A_SOURCE_MOVE_FAILED],
            warnings=[REPAIR_MOVE_FAILED_WARNING],
        )

    ready_path = (base_path / ready_relative).resolve()
    if not ready_path.is_file():
        missing_code = (
            FLOW_A_SOURCE_QUEUED_MISSING
            if ready_relative.startswith(QUEUED_SOURCE_PREFIX)
            else FLOW_A_SOURCE_READY_MISSING
        )
        return _failed_result(
            campaign=campaign,
            errors=[missing_code, FLOW_A_SOURCE_MOVE_FAILED],
            warnings=[REPAIR_MOVE_FAILED_WARNING],
        )

    source_slug = ready_path.stem
    ready_image_relative = (
        campaign.get("queued_image_relative_path")
        or _image_relative_path_for_source(ready_relative, source_slug)
    )
    ready_image_path = base_path / ready_image_relative
    has_ready_image = ready_image_path.is_file()

    processed_dir = (base_path / "blog-posts" / "processed").resolve()
    md_target, processed_md_relative, collision_error = _allocate_processed_target(
        ready_path, processed_dir
    )
    if collision_error or md_target is None or processed_md_relative is None:
        source_status["physical_move_state"] = PHYSICAL_MOVE_STATE_FAILED
        write_campaign_metadata(base_path, campaign_id, campaign)
        return _failed_result(
            campaign=campaign,
            errors=[collision_error or FLOW_A_SOURCE_MOVE_COLLISION_EXHAUSTED],
            warnings=[REPAIR_MOVE_FAILED_WARNING],
        )

    original_source = campaign.get("original_source_relative_path") or ready_relative
    original_image = (
        campaign.get("original_image_relative_path")
        if campaign.get("original_image_relative_path")
        else (ready_image_relative if has_ready_image else None)
    )

    try:
        if not _same_file(ready_path, md_target):
            _move_source_file(ready_path, md_target)
    except OSError:
        source_status["physical_move_state"] = PHYSICAL_MOVE_STATE_FAILED
        write_campaign_metadata(base_path, campaign_id, campaign)
        return _failed_result(
            campaign=campaign,
            errors=[FLOW_A_SOURCE_MOVE_FAILED],
            warnings=[REPAIR_MOVE_FAILED_WARNING],
        )

    processed_image_relative: str | None = None
    if has_ready_image:
        image_target, processed_image_relative, image_collision = _allocate_processed_target(
            ready_image_path, processed_dir
        )
        if image_collision or image_target is None or processed_image_relative is None:
            source_status["physical_move_state"] = PHYSICAL_MOVE_STATE_PARTIAL
            campaign["processed_source_relative_path"] = processed_md_relative
            campaign["original_source_relative_path"] = original_source
            campaign["source_relative_path"] = processed_md_relative
            write_campaign_metadata(base_path, campaign_id, campaign)
            return _failed_result(
                campaign=campaign,
                errors=[
                    image_collision or FLOW_A_SOURCE_MOVE_COLLISION_EXHAUSTED,
                    FLOW_A_SOURCE_MOVE_PARTIAL,
                ],
                warnings=[REPAIR_MOVE_PARTIAL_WARNING],
            )
        try:
            if not _same_file(ready_image_path, image_target):
                _move_source_file(ready_image_path, image_target)
        except OSError:
            source_status["physical_move_state"] = PHYSICAL_MOVE_STATE_PARTIAL
            campaign["processed_source_relative_path"] = processed_md_relative
            campaign["original_source_relative_path"] = original_source
            campaign["source_relative_path"] = processed_md_relative
            if original_image:
                campaign["original_image_relative_path"] = original_image
            write_campaign_metadata(base_path, campaign_id, campaign)
            return _failed_result(
                campaign=campaign,
                errors=[FLOW_A_SOURCE_MOVE_PARTIAL],
                warnings=[REPAIR_MOVE_PARTIAL_WARNING],
            )

    now = utc_now_iso()
    campaign["original_source_relative_path"] = original_source
    campaign["processed_source_relative_path"] = processed_md_relative
    campaign["source_relative_path"] = processed_md_relative
    if original_image:
        campaign["original_image_relative_path"] = original_image
    if processed_image_relative:
        campaign["processed_image_relative_path"] = processed_image_relative
        campaign["image_relative_path"] = processed_image_relative
    if has_ready_image and ready_relative.startswith(QUEUED_SOURCE_PREFIX):
        campaign["queued_image_relative_path"] = ready_image_relative

    source_status["location"] = SOURCE_LOCATION_PROCESSED
    source_status["execution_state"] = EXECUTION_STATE_IDLE
    source_status["marked_processed_at"] = now
    source_status["physical_move_completed_at"] = now
    source_status["physical_move_state"] = PHYSICAL_MOVE_STATE_COMPLETED

    try:
        transition_state(
            campaign,
            STATE_FLOW_A_COMPLETE,
            reason="Flow A source lifecycle completed",
            actor=ACTOR_WORKER,
        )
    except Exception:
        source_status["physical_move_state"] = PHYSICAL_MOVE_STATE_FAILED
        write_campaign_metadata(base_path, campaign_id, campaign)
        return _failed_result(
            campaign=campaign,
            errors=[FLOW_A_SOURCE_MOVE_FAILED],
            warnings=[REPAIR_MOVE_FAILED_WARNING],
        )

    write_result = write_campaign_metadata(base_path, campaign_id, campaign)
    if not write_result.written:
        return _failed_result(
            campaign=campaign,
            errors=[FLOW_A_SOURCE_MOVE_FAILED],
            warnings=[REPAIR_MOVE_FAILED_WARNING],
            metadata_written=False,
            metadata_error_code=write_result.error_code,
        )

    return _completed_result(
        campaign,
        metadata_written=True,
    )


__all__ = [
    "FlowASourceLifecycleResult",
    "complete_flow_a_source_lifecycle",
    "FLOW_A_SOURCE_LIFECYCLE_PREMATURE",
    "FLOW_A_SOURCE_MOVE_COLLISION_EXHAUSTED",
    "FLOW_A_SOURCE_MOVE_FAILED",
    "FLOW_A_SOURCE_MOVE_PARTIAL",
]
