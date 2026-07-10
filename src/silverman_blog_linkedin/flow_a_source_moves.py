"""Coordinated Markdown and companion image filesystem moves for Flow A."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.campaign_lifecycle import (
    ERROR_SOURCE_PREFIX,
    PHYSICAL_MOVE_STATE_COMPLETED,
    PHYSICAL_MOVE_STATE_FAILED,
    PHYSICAL_MOVE_STATE_PARTIAL,
    PROCESSED_SOURCE_PREFIX,
    QUEUED_SOURCE_PREFIX,
    compute_source_content_sha256,
)
from silverman_blog_linkedin.file_reader import normalize_relative_path

MAX_COLLISION_SUFFIX = 99
MOVE_ALREADY_AT_DESTINATION = "already_at_destination"
FLOW_A_QUEUE_DESTINATION_COLLISION = "flow_a_queue_destination_collision"
FLOW_A_SOURCE_MOVE_COLLISION_EXHAUSTED = "flow_a_source_move_collision_exhausted"


class DestinationFolder(str, Enum):
    QUEUED = "queued"
    PROCESSED = "processed"
    ERROR = "error"


_DESTINATION_PREFIX = {
    DestinationFolder.QUEUED: QUEUED_SOURCE_PREFIX,
    DestinationFolder.PROCESSED: PROCESSED_SOURCE_PREFIX,
    DestinationFolder.ERROR: ERROR_SOURCE_PREFIX,
}

_DESTINATION_SUFFIX = {
    DestinationFolder.PROCESSED: "processed",
    DestinationFolder.ERROR: "error",
}


@dataclass
class ComponentMoveResult:
    source_path: str
    destination_path: str | None
    status: str
    error_code: str | None = None


@dataclass
class CoordinatedMoveResult:
    status: str
    physical_move_state: str
    markdown: ComponentMoveResult | None = None
    image: ComponentMoveResult | None = None
    destination_markdown_relative: str | None = None
    destination_image_relative: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status,
            "physical_move_state": self.physical_move_state,
            "destination_markdown_relative": self.destination_markdown_relative,
            "destination_image_relative": self.destination_image_relative,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }
        if self.markdown:
            payload["markdown"] = {
                "source_path": self.markdown.source_path,
                "destination_path": self.markdown.destination_path,
                "status": self.markdown.status,
                "error_code": self.markdown.error_code,
            }
        if self.image:
            payload["image"] = {
                "source_path": self.image.source_path,
                "destination_path": self.image.destination_path,
                "status": self.image.status,
                "error_code": self.image.error_code,
            }
        return payload


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


def _move_file(source_path: Path, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        source_path.rename(target_path)
    except OSError:
        shutil.move(str(source_path), str(target_path))


def _confined_under(base_path: Path, relative: str, folder: DestinationFolder) -> Path:
    prefix = _DESTINATION_PREFIX[folder]
    normalized = normalize_relative_path(relative)
    if not normalized.startswith(prefix):
        raise ValueError(f"path not under {prefix}: {relative!r}")
    resolved = (base_path / normalized).resolve()
    dest_dir = (base_path / "blog-posts" / folder.value).resolve()
    if not resolved.is_relative_to(dest_dir):
        raise ValueError(f"path outside confinement: {relative!r}")
    return resolved


def _allocate_suffix_target(
    source_path: Path,
    dest_dir: Path,
    *,
    folder: DestinationFolder,
) -> tuple[Path | None, str | None, str | None]:
    """Pick a destination with deterministic collision suffixes for processed/error."""
    stem = source_path.stem
    suffix = source_path.suffix
    label = _DESTINATION_SUFFIX[folder]
    prefix = _DESTINATION_PREFIX[folder]
    candidate_names = [source_path.name] + [
        f"{stem}-{label}-{index}{suffix}" for index in range(1, MAX_COLLISION_SUFFIX + 1)
    ]
    for name in candidate_names:
        target = dest_dir / name
        relative = f"{prefix}{name}"
        if not target.exists():
            return target, relative, None
        if _same_file(source_path, target):
            return target, relative, None
    return None, None, FLOW_A_SOURCE_MOVE_COLLISION_EXHAUSTED


def _resolve_queued_target(
    source_path: Path,
    dest_dir: Path,
    *,
    campaign_id: str | None,
    source_content_sha256: str | None,
    existing_campaign_at_destination: dict[str, Any] | None,
) -> tuple[Path | None, str | None, str | None]:
    """Resolve queued destination preserving basename; reject conflicts."""
    target = dest_dir / source_path.name
    relative = f"{QUEUED_SOURCE_PREFIX}{source_path.name}"
    if not target.exists():
        return target, relative, None
    if _same_file(source_path, target):
        return target, relative, MOVE_ALREADY_AT_DESTINATION
    if existing_campaign_at_destination is not None:
        same_campaign = existing_campaign_at_destination.get("campaign_id") == campaign_id
        same_hash = (
            existing_campaign_at_destination.get("source_content_sha256")
            == source_content_sha256
        )
        if same_campaign and same_hash:
            return target, relative, MOVE_ALREADY_AT_DESTINATION
    return None, None, FLOW_A_QUEUE_DESTINATION_COLLISION


def _allocate_target(
    source_path: Path,
    dest_dir: Path,
    *,
    folder: DestinationFolder,
    campaign_id: str | None = None,
    source_content_sha256: str | None = None,
    existing_campaign_at_destination: dict[str, Any] | None = None,
) -> tuple[Path | None, str | None, str | None]:
    if folder == DestinationFolder.QUEUED:
        return _resolve_queued_target(
            source_path,
            dest_dir,
            campaign_id=campaign_id,
            source_content_sha256=source_content_sha256,
            existing_campaign_at_destination=existing_campaign_at_destination,
        )
    return _allocate_suffix_target(source_path, dest_dir, folder=folder)


def coordinated_source_move(
    base_path: Path,
    *,
    markdown_relative: str,
    image_relative: str | None,
    destination_folder: DestinationFolder,
    campaign_id: str | None = None,
    source_content_sha256: str | None = None,
    existing_campaign_at_destination: dict[str, Any] | None = None,
) -> CoordinatedMoveResult:
    """Move Markdown first, then optional companion image, recording partial state."""
    dest_dir = (base_path / "blog-posts" / destination_folder.value).resolve()
    md_source = (base_path / normalize_relative_path(markdown_relative)).resolve()
    ready_dir = (base_path / "blog-posts" / "ready").resolve()
    queued_dir = (base_path / "blog-posts" / "queued").resolve()
    error_dir = (base_path / "blog-posts" / "error").resolve()
    allowed_roots = {ready_dir, queued_dir, error_dir, dest_dir}
    if not any(md_source.is_relative_to(root) for root in allowed_roots if root.is_dir()):
        return CoordinatedMoveResult(
            status="failed",
            physical_move_state=PHYSICAL_MOVE_STATE_FAILED,
            errors=["path_outside_confinement"],
        )

    if not md_source.is_file():
        return CoordinatedMoveResult(
            status="failed",
            physical_move_state=PHYSICAL_MOVE_STATE_FAILED,
            errors=["source_missing"],
        )

    md_target, md_relative, md_error = _allocate_target(
        md_source,
        dest_dir,
        folder=destination_folder,
        campaign_id=campaign_id,
        source_content_sha256=source_content_sha256,
        existing_campaign_at_destination=existing_campaign_at_destination,
    )
    if md_error == FLOW_A_QUEUE_DESTINATION_COLLISION:
        return CoordinatedMoveResult(
            status="failed",
            physical_move_state=PHYSICAL_MOVE_STATE_FAILED,
            errors=[FLOW_A_QUEUE_DESTINATION_COLLISION],
        )
    if md_error or md_target is None or md_relative is None:
        return CoordinatedMoveResult(
            status="failed",
            physical_move_state=PHYSICAL_MOVE_STATE_FAILED,
            errors=[md_error or FLOW_A_SOURCE_MOVE_COLLISION_EXHAUSTED],
        )

    md_status = "skipped"
    if md_error != MOVE_ALREADY_AT_DESTINATION:
        try:
            if not _same_file(md_source, md_target):
                _move_file(md_source, md_target)
            md_status = "completed"
        except OSError:
            return CoordinatedMoveResult(
                status="failed",
                physical_move_state=PHYSICAL_MOVE_STATE_FAILED,
                markdown=ComponentMoveResult(
                    source_path=markdown_relative,
                    destination_path=md_relative,
                    status="failed",
                ),
                errors=["markdown_move_failed"],
            )
    else:
        md_status = "already_at_destination"

    markdown_result = ComponentMoveResult(
        source_path=markdown_relative,
        destination_path=md_relative,
        status=md_status,
    )

    image_result: ComponentMoveResult | None = None
    dest_image_relative: str | None = None
    if image_relative:
        image_source = (base_path / normalize_relative_path(image_relative)).resolve()
        if image_source.is_file():
            img_target, img_relative, img_error = _allocate_target(
                image_source,
                dest_dir,
                folder=destination_folder,
                campaign_id=campaign_id,
                source_content_sha256=source_content_sha256,
                existing_campaign_at_destination=existing_campaign_at_destination,
            )
            if img_error == FLOW_A_QUEUE_DESTINATION_COLLISION:
                return CoordinatedMoveResult(
                    status="partial",
                    physical_move_state=PHYSICAL_MOVE_STATE_PARTIAL,
                    markdown=markdown_result,
                    destination_markdown_relative=md_relative,
                    errors=[FLOW_A_QUEUE_DESTINATION_COLLISION],
                )
            if img_error and img_error != MOVE_ALREADY_AT_DESTINATION:
                return CoordinatedMoveResult(
                    status="partial",
                    physical_move_state=PHYSICAL_MOVE_STATE_PARTIAL,
                    markdown=markdown_result,
                    destination_markdown_relative=md_relative,
                    errors=[img_error],
                )
            if img_target is not None and img_relative is not None:
                img_status = "skipped"
                try:
                    if img_error != MOVE_ALREADY_AT_DESTINATION:
                        if not _same_file(image_source, img_target):
                            _move_file(image_source, img_target)
                        img_status = "completed"
                    else:
                        img_status = "already_at_destination"
                    dest_image_relative = img_relative
                    image_result = ComponentMoveResult(
                        source_path=image_relative,
                        destination_path=img_relative,
                        status=img_status,
                    )
                except OSError:
                    return CoordinatedMoveResult(
                        status="partial",
                        physical_move_state=PHYSICAL_MOVE_STATE_PARTIAL,
                        markdown=markdown_result,
                        image=ComponentMoveResult(
                            source_path=image_relative,
                            destination_path=img_relative,
                            status="failed",
                            error_code="image_move_failed",
                        ),
                        destination_markdown_relative=md_relative,
                        errors=["image_move_failed"],
                    )

    return CoordinatedMoveResult(
        status="completed",
        physical_move_state=PHYSICAL_MOVE_STATE_COMPLETED,
        markdown=markdown_result,
        image=image_result,
        destination_markdown_relative=md_relative,
        destination_image_relative=dest_image_relative,
    )
