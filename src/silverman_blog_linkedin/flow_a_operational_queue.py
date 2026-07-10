"""Flow A operational queue acceptance, execution claims, and requeue."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.campaign_lifecycle import (
    ACTOR_WORKER,
    ERROR_SOURCE_PREFIX,
    FLOW_A,
    PHYSICAL_MOVE_STATE_COMPLETED,
    PHYSICAL_MOVE_STATE_PARTIAL,
    QUEUED_SOURCE_PREFIX,
    READY_SOURCE_PREFIX,
    RECOVERY_MANUAL_INTERVENTION_REQUIRED,
    RECOVERY_NO_ACTION,
    RECOVERY_REPAIR_REQUIRED,
    RECOVERY_RETRYABLE,
    RECOVERY_REQUEUE_REQUIRED,
    SOURCE_LOCATION_ERROR,
    SOURCE_LOCATION_PROCESSED,
    SOURCE_LOCATION_QUEUED,
    SOURCE_LOCATION_READY,
    EXECUTION_STATE_IDLE,
    EXECUTION_STATE_PROCESSING,
    EXECUTION_STATE_STALE,
    build_initial_campaign_metadata,
    compute_source_content_sha256,
    find_campaign_by_source_path,
    generate_campaign_id,
    normalize_source_file_status,
    read_campaign_metadata,
    validate_operational_transition,
    write_campaign_metadata,
)
from silverman_blog_linkedin.file_reader import normalize_relative_path
from silverman_blog_linkedin.flow_a_config import load_flow_a_processing_stale_seconds
from silverman_blog_linkedin.flow_a_hidden_artifacts import is_hidden_artifact_basename
from silverman_blog_linkedin.flow_a_source_moves import (
    FLOW_A_QUEUE_DESTINATION_COLLISION,
    DestinationFolder,
    coordinated_source_move,
)
from silverman_blog_linkedin.github_pages_publish import resolve_public_slug
from silverman_blog_linkedin.paths import validate_folders
from silverman_blog_linkedin.run_metadata import utc_now_iso

EDITORIAL_FOLDERS_NOT_READY = "editorial_folders_not_ready"
FLOW_A_QUEUE_SOURCE_MISSING = "flow_a_queue_source_missing"
FLOW_A_QUEUE_PATH_UNSAFE = "flow_a_queue_path_unsafe"
FLOW_A_QUEUE_INTAKE_FAILED = "flow_a_queue_intake_failed"
FLOW_A_QUEUE_CAMPAIGN_NOT_FOUND = "flow_a_queue_campaign_not_found"
FLOW_A_QUEUE_ALREADY_PROCESSING = "flow_a_queue_already_processing"
FLOW_A_EXECUTION_ALREADY_CLAIMED = "flow_a_execution_already_claimed"
FLOW_A_EXECUTION_ALREADY_RELEASED = "flow_a_execution_already_released"
FLOW_A_EXECUTION_NOT_CLAIMED = "flow_a_execution_not_claimed"
FLOW_A_EXECUTION_STALE_RELEASE_NOT_ALLOWED = "flow_a_execution_stale_release_not_allowed"
FLOW_A_REQUEUE_NOT_IN_ERROR = "flow_a_requeue_not_in_error"
CALENDAR_CAMPAIGN_ID_CONFLICT = "calendar_campaign_id_conflict"
CAMPAIGN_METADATA_WRITE_FAILED = "campaign_metadata_write_failed"

QUEUE_ACCEPTANCE_COMPLETED = "completed"
QUEUE_ACCEPTANCE_SKIPPED_ALREADY_QUEUED = "skipped_already_queued"
QUEUE_ACCEPTANCE_FAILED = "failed"
QUEUE_ACCEPTANCE_PARTIAL = "partial"
QUEUE_ACCEPTANCE_REPAIR_REQUIRED = "repair_required"


@dataclass
class QueueAcceptanceResult:
    status: str
    queue_acceptance_status: str
    campaign_id: str | None = None
    source_relative_path: str | None = None
    queued_source_relative_path: str | None = None
    queued_image_relative_path: str | None = None
    physical_move_state: str | None = None
    recovery_classification: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata_written: bool = False
    metadata_error_code: str | None = None
    would_queue_accept: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionClaimResult:
    status: str
    campaign_id: str | None = None
    execution_attempt_id: str | None = None
    attempt_count: int | None = None
    execution_state: str | None = None
    recovery_classification: str | None = None
    errors: list[str] = field(default_factory=list)
    already_claimed: bool = False
    reclaimed_from_stale: bool = False
    metadata_written: bool = False
    metadata_error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionReleaseResult:
    status: str
    campaign_id: str | None = None
    execution_state: str | None = None
    recovery_classification: str | None = None
    already_released: bool = False
    errors: list[str] = field(default_factory=list)
    metadata_written: bool = False
    metadata_error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RequeueResult:
    status: str
    campaign_id: str | None = None
    queued_source_relative_path: str | None = None
    errors: list[str] = field(default_factory=list)
    metadata_written: bool = False
    metadata_error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _metadata_write_succeeded(write_result: Any) -> bool:
    return bool(getattr(write_result, "written", False))


def _metadata_write_failure_fields(write_result: Any) -> dict[str, Any]:
    if _metadata_write_succeeded(write_result):
        return {}
    error_code = getattr(write_result, "error_code", None) or CAMPAIGN_METADATA_WRITE_FAILED
    return {
        "metadata_written": False,
        "metadata_error_code": error_code,
        "errors": [error_code],
    }


def _parse_utc_iso(value: str) -> datetime:
    if value.endswith("Z"):
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _derived_lease_expires_at(last_progress_at: str, stale_seconds: int) -> str:
    progress = _parse_utc_iso(last_progress_at)
    expires = progress + timedelta(seconds=stale_seconds)
    return expires.strftime("%Y-%m-%dT%H:%M:%SZ")


def is_execution_stale(
    source_status: dict[str, Any],
    *,
    now: datetime | None = None,
    stale_seconds: int | None = None,
) -> bool:
    """Return True when now >= last_progress_at + stale_seconds."""
    if source_status.get("execution_state") != EXECUTION_STATE_PROCESSING:
        return False
    last_progress = source_status.get("last_progress_at")
    if not isinstance(last_progress, str) or not last_progress.strip():
        return True
    seconds = stale_seconds if stale_seconds is not None else load_flow_a_processing_stale_seconds()
    current = now or datetime.now(timezone.utc)
    threshold = _parse_utc_iso(last_progress) + timedelta(seconds=seconds)
    return current >= threshold


def detect_stale_flow_a_execution(
    base_path: Path,
    *,
    campaign_id: str,
    now_utc: str | None = None,
) -> ExecutionClaimResult:
    """Mark a processing claim stale when inactivity threshold exceeded."""
    campaign = read_campaign_metadata(base_path, campaign_id)
    if campaign is None:
        return ExecutionClaimResult(
            status="failed",
            campaign_id=campaign_id,
            errors=[FLOW_A_QUEUE_CAMPAIGN_NOT_FOUND],
        )

    source_status = normalize_source_file_status(campaign.get("source_file_status"))
    if source_status.get("execution_state") != EXECUTION_STATE_PROCESSING:
        return ExecutionClaimResult(
            status="skipped",
            campaign_id=campaign_id,
            execution_state=source_status.get("execution_state"),
        )

    now = (
        _parse_utc_iso(now_utc)
        if now_utc
        else datetime.now(timezone.utc)
    )
    if not is_execution_stale(source_status, now=now):
        return ExecutionClaimResult(
            status="skipped",
            campaign_id=campaign_id,
            execution_state=EXECUTION_STATE_PROCESSING,
            recovery_classification=RECOVERY_MANUAL_INTERVENTION_REQUIRED,
        )

    validate_operational_transition(
        from_location=source_status.get("location", SOURCE_LOCATION_QUEUED),
        from_execution=EXECUTION_STATE_PROCESSING,
        to_location=source_status.get("location", SOURCE_LOCATION_QUEUED),
        to_execution=EXECUTION_STATE_STALE,
    )
    source_status["execution_state"] = EXECUTION_STATE_STALE
    source_status["recovery_classification"] = RECOVERY_RETRYABLE
    campaign["source_file_status"] = source_status
    campaign["updated_at"] = utc_now_iso()
    write_result = write_campaign_metadata(base_path, campaign_id, campaign)
    if not _metadata_write_succeeded(write_result):
        return ExecutionClaimResult(
            status="failed",
            campaign_id=campaign_id,
            execution_state=EXECUTION_STATE_PROCESSING,
            recovery_classification=RECOVERY_MANUAL_INTERVENTION_REQUIRED,
            metadata_written=False,
            metadata_error_code=write_result.error_code,
            errors=[write_result.error_code or CAMPAIGN_METADATA_WRITE_FAILED],
        )
    return ExecutionClaimResult(
        status="completed",
        campaign_id=campaign_id,
        execution_state=EXECUTION_STATE_STALE,
        recovery_classification=RECOVERY_RETRYABLE,
        metadata_written=True,
        metadata_error_code=None,
    )


def _canonical_utc_now(now_utc: str | None = None) -> tuple[datetime, str]:
    """Parse optional now_utc once; return (datetime, canonical Zulu string)."""
    if now_utc:
        current = _parse_utc_iso(now_utc)
    else:
        current = datetime.now(timezone.utc)
    return current, current.strftime("%Y-%m-%dT%H:%M:%SZ")


def _markdown_move_reached_error(
    base_path: Path,
    move_result: Any,
) -> bool:
    """True when Markdown physically resides under blog-posts/error/."""
    markdown = getattr(move_result, "markdown", None)
    if markdown is None or markdown.status not in ("completed", "already_at_destination"):
        return False
    destination = getattr(move_result, "destination_markdown_relative", None)
    if not isinstance(destination, str) or not destination.startswith(ERROR_SOURCE_PREFIX):
        return False
    return (base_path / destination).is_file()


def error_move_closed_processing_claim(move_result: QueueAcceptanceResult) -> bool:
    """Return True when error move persisted idle execution (no release needed)."""
    if not move_result.metadata_written:
        return False
    return move_result.status in (
        QUEUE_ACCEPTANCE_COMPLETED,
        QUEUE_ACCEPTANCE_PARTIAL,
    )


def claim_flow_a_execution(
    base_path: Path,
    *,
    campaign_id: str,
    now_utc: str | None = None,
) -> ExecutionClaimResult:
    """Claim Flow A execution for a queued campaign."""
    campaign = read_campaign_metadata(base_path, campaign_id)
    if campaign is None:
        return ExecutionClaimResult(
            status="failed",
            campaign_id=campaign_id,
            errors=[FLOW_A_QUEUE_CAMPAIGN_NOT_FOUND],
        )

    source_status = normalize_source_file_status(campaign.get("source_file_status"))
    location = source_status.get("location")
    if location not in (SOURCE_LOCATION_QUEUED,):
        return ExecutionClaimResult(
            status="failed",
            campaign_id=campaign_id,
            errors=[FLOW_A_QUEUE_INTAKE_FAILED],
        )

    execution_state = source_status.get("execution_state", EXECUTION_STATE_IDLE)
    current_dt, now = _canonical_utc_now(now_utc)
    stale_seconds = load_flow_a_processing_stale_seconds()
    reclaimed = execution_state == EXECUTION_STATE_STALE

    if execution_state == EXECUTION_STATE_PROCESSING:
        if is_execution_stale(
            source_status, now=current_dt, stale_seconds=stale_seconds
        ):
            detect_stale_flow_a_execution(
                base_path, campaign_id=campaign_id, now_utc=now
            )
            campaign = read_campaign_metadata(base_path, campaign_id) or campaign
            source_status = normalize_source_file_status(campaign.get("source_file_status"))
            execution_state = source_status.get("execution_state", EXECUTION_STATE_IDLE)
            reclaimed = True
        else:
            return ExecutionClaimResult(
                status="failed",
                campaign_id=campaign_id,
                errors=[FLOW_A_EXECUTION_ALREADY_CLAIMED],
                already_claimed=True,
                recovery_classification=RECOVERY_MANUAL_INTERVENTION_REQUIRED,
            )

    from_execution = execution_state
    if from_execution not in (EXECUTION_STATE_IDLE, EXECUTION_STATE_STALE):
        return ExecutionClaimResult(
            status="failed",
            campaign_id=campaign_id,
            errors=[FLOW_A_EXECUTION_ALREADY_CLAIMED],
        )

    validate_operational_transition(
        from_location=location,
        from_execution=from_execution,
        to_location=location,
        to_execution=EXECUTION_STATE_PROCESSING,
    )

    attempt_count = int(source_status.get("attempt_count") or 0) + 1
    attempt_id = str(uuid.uuid4())
    source_status["execution_state"] = EXECUTION_STATE_PROCESSING
    source_status["execution_attempt_id"] = attempt_id
    source_status["attempt_count"] = attempt_count
    source_status["processing_claimed_at"] = now
    source_status["processing_started_at"] = now
    source_status["last_progress_at"] = now
    source_status["processing_lease_expires_at"] = _derived_lease_expires_at(
        now, stale_seconds
    )
    source_status["recovery_classification"] = RECOVERY_NO_ACTION
    campaign["source_file_status"] = source_status
    campaign["updated_at"] = now

    write_result = write_campaign_metadata(base_path, campaign_id, campaign)
    if not _metadata_write_succeeded(write_result):
        return ExecutionClaimResult(
            status="failed",
            campaign_id=campaign_id,
            execution_attempt_id=attempt_id,
            attempt_count=attempt_count,
            execution_state=EXECUTION_STATE_PROCESSING,
            reclaimed_from_stale=reclaimed,
            metadata_written=False,
            metadata_error_code=write_result.error_code,
            errors=[write_result.error_code or CAMPAIGN_METADATA_WRITE_FAILED],
        )
    return ExecutionClaimResult(
        status="completed",
        campaign_id=campaign_id,
        execution_attempt_id=attempt_id,
        attempt_count=attempt_count,
        execution_state=EXECUTION_STATE_PROCESSING,
        reclaimed_from_stale=reclaimed,
        metadata_written=True,
        metadata_error_code=None,
    )


def record_flow_a_progress(
    base_path: Path,
    *,
    campaign_id: str,
    at: str | None = None,
) -> ExecutionClaimResult:
    """Refresh last_progress_at after a completed Flow A stage boundary."""
    campaign = read_campaign_metadata(base_path, campaign_id)
    if campaign is None:
        return ExecutionClaimResult(
            status="failed",
            campaign_id=campaign_id,
            errors=[FLOW_A_QUEUE_CAMPAIGN_NOT_FOUND],
        )

    source_status = normalize_source_file_status(campaign.get("source_file_status"))
    if source_status.get("execution_state") != EXECUTION_STATE_PROCESSING:
        return ExecutionClaimResult(
            status="skipped",
            campaign_id=campaign_id,
            execution_state=source_status.get("execution_state"),
        )

    now = at or utc_now_iso()
    stale_seconds = load_flow_a_processing_stale_seconds()
    source_status["last_progress_at"] = now
    source_status["processing_lease_expires_at"] = _derived_lease_expires_at(
        now, stale_seconds
    )
    campaign["source_file_status"] = source_status
    campaign["updated_at"] = now
    write_result = write_campaign_metadata(base_path, campaign_id, campaign)
    if not _metadata_write_succeeded(write_result):
        return ExecutionClaimResult(
            status="failed",
            campaign_id=campaign_id,
            execution_attempt_id=source_status.get("execution_attempt_id"),
            execution_state=EXECUTION_STATE_PROCESSING,
            metadata_written=False,
            metadata_error_code=write_result.error_code,
            errors=[write_result.error_code or CAMPAIGN_METADATA_WRITE_FAILED],
        )
    return ExecutionClaimResult(
        status="completed",
        campaign_id=campaign_id,
        execution_attempt_id=source_status.get("execution_attempt_id"),
        execution_state=EXECUTION_STATE_PROCESSING,
        metadata_written=True,
        metadata_error_code=None,
    )


def release_flow_a_execution(
    base_path: Path,
    *,
    campaign_id: str,
    recovery_classification: str = RECOVERY_RETRYABLE,
    last_error: dict[str, Any] | None = None,
) -> ExecutionReleaseResult:
    """Release a non-terminal processing claim."""
    campaign = read_campaign_metadata(base_path, campaign_id)
    if campaign is None:
        return ExecutionReleaseResult(
            status="failed",
            campaign_id=campaign_id,
            errors=[FLOW_A_QUEUE_CAMPAIGN_NOT_FOUND],
        )

    source_status = normalize_source_file_status(campaign.get("source_file_status"))
    location = source_status.get("location")
    execution_state = source_status.get("execution_state", EXECUTION_STATE_IDLE)

    if location == SOURCE_LOCATION_PROCESSED and execution_state == EXECUTION_STATE_IDLE:
        return ExecutionReleaseResult(
            status="skipped",
            campaign_id=campaign_id,
            execution_state=execution_state,
            already_released=True,
        )

    if execution_state == EXECUTION_STATE_STALE:
        return ExecutionReleaseResult(
            status="failed",
            campaign_id=campaign_id,
            execution_state=EXECUTION_STATE_STALE,
            recovery_classification=RECOVERY_RETRYABLE,
            errors=[FLOW_A_EXECUTION_STALE_RELEASE_NOT_ALLOWED],
        )

    if execution_state != EXECUTION_STATE_PROCESSING:
        return ExecutionReleaseResult(
            status="skipped",
            campaign_id=campaign_id,
            execution_state=execution_state,
            already_released=True,
            errors=[FLOW_A_EXECUTION_ALREADY_RELEASED],
        )

    validate_operational_transition(
        from_location=location,
        from_execution=execution_state,
        to_location=location,
        to_execution=EXECUTION_STATE_IDLE,
    )

    now = utc_now_iso()
    source_status["execution_state"] = EXECUTION_STATE_IDLE
    source_status["recovery_classification"] = recovery_classification
    source_status["last_transition_at"] = now
    if last_error:
        source_status["last_error"] = last_error
    campaign["source_file_status"] = source_status
    campaign["updated_at"] = now

    write_result = write_campaign_metadata(base_path, campaign_id, campaign)
    if not _metadata_write_succeeded(write_result):
        return ExecutionReleaseResult(
            status="failed",
            campaign_id=campaign_id,
            execution_state=EXECUTION_STATE_PROCESSING,
            recovery_classification=recovery_classification,
            metadata_written=False,
            metadata_error_code=write_result.error_code,
            errors=[write_result.error_code or CAMPAIGN_METADATA_WRITE_FAILED],
        )
    return ExecutionReleaseResult(
        status="completed",
        campaign_id=campaign_id,
        execution_state=EXECUTION_STATE_IDLE,
        recovery_classification=recovery_classification,
        metadata_written=True,
        metadata_error_code=None,
    )


def _intake_check_ready_source(
    base_path: Path,
    source_relative_path: str,
) -> tuple[list[str], Path | None, str | None, str | None]:
    """Minimum intake checks for queue acceptance."""
    errors: list[str] = []
    normalized = normalize_relative_path(source_relative_path)
    if not normalized.startswith(READY_SOURCE_PREFIX):
        errors.append(FLOW_A_QUEUE_PATH_UNSAFE)
        return errors, None, None, None

    filename = normalized[len(READY_SOURCE_PREFIX) :]
    if "/" in filename or is_hidden_artifact_basename(filename):
        errors.append(FLOW_A_QUEUE_PATH_UNSAFE)
        return errors, None, None, None

    if not filename.lower().endswith(".md"):
        errors.append(FLOW_A_QUEUE_INTAKE_FAILED)
        return errors, None, None, None

    ready_dir = (base_path / "blog-posts" / "ready").resolve()
    resolved = (base_path / normalized).resolve()
    try:
        resolved.relative_to(ready_dir)
    except ValueError:
        errors.append(FLOW_A_QUEUE_PATH_UNSAFE)
        return errors, None, None, None

    if not resolved.is_file():
        errors.append(FLOW_A_QUEUE_SOURCE_MISSING)
        return errors, None, None, None

    try:
        content = resolved.read_bytes()
    except OSError:
        errors.append(FLOW_A_QUEUE_INTAKE_FAILED)
        return errors, None, None, None

    if len(content) == 0:
        errors.append(FLOW_A_QUEUE_INTAKE_FAILED)
        return errors, None, None, None

    content_hash = compute_source_content_sha256(content)
    source_slug = resolved.stem
    try:
        public_slug = resolve_public_slug(source_slug, None)
    except Exception:
        errors.append(FLOW_A_QUEUE_INTAKE_FAILED)
        return errors, None, None, None

    return errors, resolved, source_slug, public_slug


def _image_relative_for_slug(source_slug: str, folder_prefix: str) -> str:
    return f"{folder_prefix}{source_slug}.png"


def _campaign_source_path_chain_compatible(
    campaign: dict[str, Any],
    source_relative_path: str,
) -> bool:
    normalized_incoming = normalize_relative_path(source_relative_path)
    chain: list[str] = []
    for key in (
        "original_source_relative_path",
        "queued_source_relative_path",
        "error_source_relative_path",
        "processed_source_relative_path",
        "source_relative_path",
    ):
        value = campaign.get(key)
        if isinstance(value, str) and value.strip():
            chain.append(normalize_relative_path(value))
    if not chain:
        return True
    return normalized_incoming in chain


def _campaign_source_identity_compatible(
    campaign: dict[str, Any],
    *,
    content_hash: str,
    source_slug: str,
    public_slug: str,
    source_relative_path: str,
) -> bool:
    if campaign.get("flow") != FLOW_A:
        return False
    existing_hash = campaign.get("source_content_sha256")
    if isinstance(existing_hash, str) and existing_hash and existing_hash != content_hash:
        return False
    existing_slug = campaign.get("source_slug")
    if isinstance(existing_slug, str) and existing_slug and existing_slug != source_slug:
        return False
    existing_public = campaign.get("public_slug")
    if isinstance(existing_public, str) and existing_public and existing_public != public_slug:
        return False
    return _campaign_source_path_chain_compatible(campaign, source_relative_path)


def _resolve_or_create_campaign(
    base_path: Path,
    *,
    source_relative_path: str,
    calendar_item: dict[str, Any] | None,
    source_slug: str,
    public_slug: str,
    content_hash: str,
    content: bytes,
) -> tuple[dict[str, Any] | None, str | None]:
    calendar_campaign_id = None
    if calendar_item:
        raw_id = calendar_item.get("campaign_id")
        if isinstance(raw_id, str) and raw_id.strip():
            calendar_campaign_id = raw_id.strip()

    existing_by_calendar_id = None
    if calendar_campaign_id:
        existing_by_calendar_id = read_campaign_metadata(base_path, calendar_campaign_id)

    existing_by_source = find_campaign_by_source_path(base_path, source_relative_path)
    if (
        calendar_campaign_id
        and existing_by_source is not None
        and existing_by_source.get("campaign_id") != calendar_campaign_id
    ):
        return None, CALENDAR_CAMPAIGN_ID_CONFLICT

    existing = existing_by_calendar_id or existing_by_source

    publication_date = None
    if calendar_item:
        raw_date = calendar_item.get("publication_date")
        if isinstance(raw_date, str) and raw_date.strip():
            publication_date = raw_date.strip()[:10]
        if publication_date is None:
            due_at = calendar_item.get("due_at_utc")
            if isinstance(due_at, str) and len(due_at) >= 10:
                publication_date = due_at[:10]

    if publication_date is None and existing:
        publication_date = existing.get("publication_date")

    if publication_date is None:
        return None, FLOW_A_QUEUE_INTAKE_FAILED

    if existing is not None:
        if not _campaign_source_identity_compatible(
            existing,
            content_hash=content_hash,
            source_slug=source_slug,
            public_slug=public_slug,
            source_relative_path=source_relative_path,
        ):
            return None, CALENDAR_CAMPAIGN_ID_CONFLICT
        return existing, None

    image_relative = _image_relative_for_slug(source_slug, READY_SOURCE_PREFIX)
    campaign = build_initial_campaign_metadata(
        flow=FLOW_A,
        source_slug=source_slug,
        public_slug=public_slug,
        source_relative_path=source_relative_path,
        image_relative_path=image_relative,
        source_content=content,
        publication_date=publication_date,
        campaign_id=calendar_campaign_id,
    )
    return campaign, None


def _already_queued_result(
    campaign: dict[str, Any],
    *,
    metadata_written: bool = True,
    metadata_error_code: str | None = None,
) -> QueueAcceptanceResult:
    queued_md, queued_image = campaign.get("queued_source_relative_path"), campaign.get(
        "queued_image_relative_path"
    )
    active_md = queued_md or campaign.get("source_relative_path")
    return QueueAcceptanceResult(
        status="completed",
        queue_acceptance_status=QUEUE_ACCEPTANCE_SKIPPED_ALREADY_QUEUED,
        campaign_id=campaign.get("campaign_id"),
        source_relative_path=campaign.get("original_source_relative_path")
        or campaign.get("source_relative_path"),
        queued_source_relative_path=active_md,
        queued_image_relative_path=queued_image,
        recovery_classification=RECOVERY_NO_ACTION,
        metadata_written=metadata_written,
        metadata_error_code=metadata_error_code,
    )


def _reconcile_metadata_queued_physical(
    base_path: Path,
    campaign: dict[str, Any],
    *,
    queued_md_relative: str,
    queued_image_relative: str | None,
    calendar_source_relative_path: str | None = None,
) -> QueueAcceptanceResult:
    """Repair metadata when Markdown is physically queued but metadata still says ready."""
    now = utc_now_iso()
    prior_source = campaign.get("source_relative_path")
    original_source = campaign.get("original_source_relative_path")
    if not isinstance(original_source, str) or not original_source.strip():
        if isinstance(prior_source, str) and prior_source.startswith(READY_SOURCE_PREFIX):
            original_source = prior_source
        elif calendar_source_relative_path:
            original_source = normalize_relative_path(calendar_source_relative_path)
    source_status = normalize_source_file_status(campaign.get("source_file_status"))
    source_status["location"] = SOURCE_LOCATION_QUEUED
    source_status["execution_state"] = EXECUTION_STATE_IDLE
    source_status["recovery_classification"] = RECOVERY_REPAIR_REQUIRED
    source_status["physical_move_state"] = PHYSICAL_MOVE_STATE_COMPLETED
    source_status["last_transition_at"] = now
    campaign["queued_source_relative_path"] = queued_md_relative
    campaign["queued_at"] = campaign.get("queued_at") or now
    campaign["source_relative_path"] = queued_md_relative
    if original_source:
        campaign["original_source_relative_path"] = original_source
    if queued_image_relative:
        campaign["queued_image_relative_path"] = queued_image_relative
        campaign["image_relative_path"] = queued_image_relative
    campaign["source_file_status"] = source_status
    campaign["updated_at"] = now
    write_result = write_campaign_metadata(base_path, campaign["campaign_id"], campaign)
    metadata_failure = _metadata_write_failure_fields(write_result)
    return QueueAcceptanceResult(
        status=QUEUE_ACCEPTANCE_REPAIR_REQUIRED,
        queue_acceptance_status=QUEUE_ACCEPTANCE_COMPLETED,
        campaign_id=campaign.get("campaign_id"),
        source_relative_path=original_source,
        queued_source_relative_path=queued_md_relative,
        queued_image_relative_path=queued_image_relative,
        physical_move_state=PHYSICAL_MOVE_STATE_COMPLETED,
        recovery_classification=RECOVERY_REPAIR_REQUIRED,
        metadata_written=_metadata_write_succeeded(write_result),
        metadata_error_code=metadata_failure.get("metadata_error_code"),
        errors=list(metadata_failure.get("errors", [])),
    )


def accept_flow_a_source_for_queue(
    base_path: Path,
    *,
    source_relative_path: str,
    calendar_item: dict[str, Any] | None = None,
    dry_run: bool = False,
) -> QueueAcceptanceResult:
    """Accept a calendar-selected ready source into blog-posts/queued/."""
    normalized = normalize_relative_path(source_relative_path)

    folder_result = validate_folders(base_path)
    if not folder_result.folders_ready:
        return QueueAcceptanceResult(
            status=QUEUE_ACCEPTANCE_FAILED,
            queue_acceptance_status=QUEUE_ACCEPTANCE_FAILED,
            source_relative_path=normalized,
            errors=[EDITORIAL_FOLDERS_NOT_READY],
        )

    calendar_campaign_id = None
    if calendar_item:
        raw = calendar_item.get("campaign_id")
        if isinstance(raw, str) and raw.strip():
            calendar_campaign_id = raw.strip()
            existing_by_id = read_campaign_metadata(base_path, calendar_campaign_id)
            if existing_by_id is not None:
                source_status = normalize_source_file_status(
                    existing_by_id.get("source_file_status")
                )
                if source_status.get("location") == SOURCE_LOCATION_QUEUED:
                    return _already_queued_result(existing_by_id)
                queued_md = existing_by_id.get("queued_source_relative_path")
                if queued_md and (base_path / queued_md).is_file():
                    return _reconcile_metadata_queued_physical(
                        base_path,
                        existing_by_id,
                        queued_md_relative=queued_md,
                        queued_image_relative=existing_by_id.get(
                            "queued_image_relative_path"
                        ),
                        calendar_source_relative_path=normalized,
                    )

    intake_errors, resolved, source_slug, public_slug = _intake_check_ready_source(
        base_path, normalized
    )
    if intake_errors:
        if FLOW_A_QUEUE_SOURCE_MISSING in intake_errors or FLOW_A_QUEUE_PATH_UNSAFE in intake_errors:
            return QueueAcceptanceResult(
                status=QUEUE_ACCEPTANCE_FAILED,
                queue_acceptance_status=QUEUE_ACCEPTANCE_FAILED,
                source_relative_path=normalized,
                errors=intake_errors,
            )
        return QueueAcceptanceResult(
            status=QUEUE_ACCEPTANCE_FAILED,
            queue_acceptance_status=QUEUE_ACCEPTANCE_FAILED,
            source_relative_path=normalized,
            errors=intake_errors,
        )

    assert resolved is not None and source_slug is not None and public_slug is not None
    content = resolved.read_bytes()
    content_hash = compute_source_content_sha256(content)

    campaign, campaign_error = _resolve_or_create_campaign(
        base_path,
        source_relative_path=normalized,
        calendar_item=calendar_item,
        source_slug=source_slug,
        public_slug=public_slug,
        content_hash=content_hash,
        content=content,
    )
    if campaign is None:
        return QueueAcceptanceResult(
            status=QUEUE_ACCEPTANCE_FAILED,
            queue_acceptance_status=QUEUE_ACCEPTANCE_FAILED,
            source_relative_path=normalized,
            errors=[campaign_error or FLOW_A_QUEUE_INTAKE_FAILED],
        )

    campaign_id = campaign["campaign_id"]
    source_status = normalize_source_file_status(campaign.get("source_file_status"))
    if source_status.get("location") == SOURCE_LOCATION_QUEUED:
        return _already_queued_result(campaign)

    queued_basename = resolved.name
    queued_md_relative = f"{QUEUED_SOURCE_PREFIX}{queued_basename}"
    queued_target = base_path / queued_md_relative
    if queued_target.is_file():
        existing_at_dest = find_campaign_by_source_path(base_path, queued_md_relative)
        if existing_at_dest is not None:
            same_campaign = existing_at_dest.get("campaign_id") == campaign_id
            same_hash = existing_at_dest.get("source_content_sha256") == content_hash
            if same_campaign and same_hash:
                return _already_queued_result(existing_at_dest)
        return QueueAcceptanceResult(
            status=QUEUE_ACCEPTANCE_FAILED,
            queue_acceptance_status=QUEUE_ACCEPTANCE_FAILED,
            campaign_id=campaign_id,
            source_relative_path=normalized,
            errors=[FLOW_A_QUEUE_DESTINATION_COLLISION],
            recovery_classification=RECOVERY_REPAIR_REQUIRED,
        )

    image_relative = _image_relative_for_slug(source_slug, READY_SOURCE_PREFIX)
    has_image = (base_path / image_relative).is_file()

    if dry_run:
        return QueueAcceptanceResult(
            status="would_accept",
            queue_acceptance_status="would_accept",
            campaign_id=campaign_id,
            source_relative_path=normalized,
            would_queue_accept=True,
        )

    existing_at_dest = find_campaign_by_source_path(base_path, queued_md_relative)
    move_result = coordinated_source_move(
        base_path,
        markdown_relative=normalized,
        image_relative=image_relative if has_image else None,
        destination_folder=DestinationFolder.QUEUED,
        campaign_id=campaign_id,
        source_content_sha256=content_hash,
        existing_campaign_at_destination=existing_at_dest,
    )

    if FLOW_A_QUEUE_DESTINATION_COLLISION in move_result.errors:
        return QueueAcceptanceResult(
            status=QUEUE_ACCEPTANCE_FAILED,
            queue_acceptance_status=QUEUE_ACCEPTANCE_FAILED,
            campaign_id=campaign_id,
            source_relative_path=normalized,
            errors=list(move_result.errors),
            recovery_classification=RECOVERY_REPAIR_REQUIRED,
        )

    if move_result.status == "failed":
        return QueueAcceptanceResult(
            status=QUEUE_ACCEPTANCE_FAILED,
            queue_acceptance_status=QUEUE_ACCEPTANCE_FAILED,
            campaign_id=campaign_id,
            source_relative_path=normalized,
            errors=list(move_result.errors),
            physical_move_state=move_result.physical_move_state,
        )

    now = utc_now_iso()
    queued_image_relative = move_result.destination_image_relative
    original_source = campaign.get("original_source_relative_path") or normalized
    original_image = campaign.get("original_image_relative_path")
    if has_image and original_image is None:
        original_image = image_relative

    source_status["location"] = SOURCE_LOCATION_QUEUED
    source_status["execution_state"] = EXECUTION_STATE_IDLE
    source_status["recovery_classification"] = (
        RECOVERY_REPAIR_REQUIRED
        if move_result.status == "partial"
        else RECOVERY_NO_ACTION
    )
    source_status["physical_move_state"] = move_result.physical_move_state
    source_status["last_transition_at"] = now
    campaign["queued_source_relative_path"] = move_result.destination_markdown_relative
    campaign["queued_at"] = now
    campaign["original_source_relative_path"] = original_source
    campaign["source_relative_path"] = move_result.destination_markdown_relative
    if queued_image_relative:
        campaign["queued_image_relative_path"] = queued_image_relative
        campaign["image_relative_path"] = queued_image_relative
    elif original_image:
        campaign["image_relative_path"] = original_image
    if original_image:
        campaign["original_image_relative_path"] = original_image
    campaign["source_slug"] = source_slug
    campaign["public_slug"] = public_slug
    campaign["source_content_sha256"] = content_hash
    if "intake_source_content_sha256" not in campaign:
        campaign["intake_source_content_sha256"] = content_hash
    campaign["source_file_status"] = source_status
    campaign["updated_at"] = now

    write_result = write_campaign_metadata(base_path, campaign_id, campaign)
    acceptance_status = (
        QUEUE_ACCEPTANCE_PARTIAL
        if move_result.status == "partial"
        else QUEUE_ACCEPTANCE_COMPLETED
    )
    if not _metadata_write_succeeded(write_result):
        metadata_failure = _metadata_write_failure_fields(write_result)
        return QueueAcceptanceResult(
            status=QUEUE_ACCEPTANCE_REPAIR_REQUIRED,
            queue_acceptance_status=acceptance_status,
            campaign_id=campaign_id,
            source_relative_path=original_source,
            queued_source_relative_path=move_result.destination_markdown_relative,
            queued_image_relative_path=queued_image_relative,
            physical_move_state=move_result.physical_move_state,
            recovery_classification=RECOVERY_REPAIR_REQUIRED,
            metadata_written=False,
            metadata_error_code=metadata_failure.get("metadata_error_code"),
            errors=list(move_result.errors) + list(metadata_failure.get("errors", [])),
        )
    overall_status = (
        QUEUE_ACCEPTANCE_REPAIR_REQUIRED
        if move_result.status == "partial"
        else QUEUE_ACCEPTANCE_COMPLETED
    )
    return QueueAcceptanceResult(
        status=overall_status,
        queue_acceptance_status=acceptance_status,
        campaign_id=campaign_id,
        source_relative_path=original_source,
        queued_source_relative_path=move_result.destination_markdown_relative,
        queued_image_relative_path=queued_image_relative,
        physical_move_state=move_result.physical_move_state,
        recovery_classification=source_status["recovery_classification"],
        metadata_written=True,
        metadata_error_code=None,
        errors=list(move_result.errors),
    )


def move_queued_source_to_error(
    base_path: Path,
    *,
    campaign_id: str,
    error_code: str,
    category: str,
    last_successful_stage: str | None = None,
) -> QueueAcceptanceResult:
    """Move a queued source to error/ after deterministic validation failure."""
    campaign = read_campaign_metadata(base_path, campaign_id)
    if campaign is None:
        return QueueAcceptanceResult(
            status=QUEUE_ACCEPTANCE_FAILED,
            queue_acceptance_status=QUEUE_ACCEPTANCE_FAILED,
            errors=[FLOW_A_QUEUE_CAMPAIGN_NOT_FOUND],
        )

    md_relative, image_relative = (
        campaign.get("queued_source_relative_path"),
        campaign.get("queued_image_relative_path"),
    )
    if not md_relative:
        return QueueAcceptanceResult(
            status=QUEUE_ACCEPTANCE_FAILED,
            queue_acceptance_status=QUEUE_ACCEPTANCE_FAILED,
            campaign_id=campaign_id,
            errors=[FLOW_A_QUEUE_SOURCE_MISSING],
        )

    prior_location = normalize_source_file_status(
        campaign.get("source_file_status")
    ).get("location", SOURCE_LOCATION_QUEUED)
    prior_md_relative = md_relative
    prior_image_relative = image_relative or campaign.get("original_image_relative_path")
    prior_execution_state = normalize_source_file_status(
        campaign.get("source_file_status")
    ).get("execution_state", EXECUTION_STATE_IDLE)

    move_result = coordinated_source_move(
        base_path,
        markdown_relative=md_relative,
        image_relative=image_relative,
        destination_folder=DestinationFolder.ERROR,
        campaign_id=campaign_id,
        source_content_sha256=campaign.get("source_content_sha256"),
    )
    now = utc_now_iso()
    source_status = normalize_source_file_status(campaign.get("source_file_status"))
    source_status["physical_move_state"] = move_result.physical_move_state
    source_status["marked_error_at"] = now
    source_status["last_transition_at"] = now
    source_status["last_error"] = {
        "category": category,
        "error_code": error_code,
        "reason": error_code,
        "at": now,
        "last_successful_stage": last_successful_stage,
        "attempt_id": source_status.get("execution_attempt_id"),
    }

    md_in_error = _markdown_move_reached_error(base_path, move_result)
    error_md_relative = move_result.destination_markdown_relative if md_in_error else None
    error_from_execution = (
        prior_execution_state
        if prior_execution_state
        in (EXECUTION_STATE_PROCESSING, EXECUTION_STATE_STALE)
        else EXECUTION_STATE_PROCESSING
    )

    if md_in_error and move_result.status == "completed":
        validate_operational_transition(
            from_location=prior_location,
            from_execution=error_from_execution,
            to_location=SOURCE_LOCATION_ERROR,
            to_execution=EXECUTION_STATE_IDLE,
        )
        source_status["location"] = SOURCE_LOCATION_ERROR
        source_status["execution_state"] = EXECUTION_STATE_IDLE
        source_status["recovery_classification"] = RECOVERY_REQUEUE_REQUIRED
        campaign["error_source_relative_path"] = error_md_relative
        campaign["source_relative_path"] = error_md_relative
        if move_result.destination_image_relative:
            campaign["error_image_relative_path"] = move_result.destination_image_relative
            campaign["image_relative_path"] = move_result.destination_image_relative
        result_status = QUEUE_ACCEPTANCE_COMPLETED
        recovery = RECOVERY_REQUEUE_REQUIRED
    elif md_in_error:
        validate_operational_transition(
            from_location=prior_location,
            from_execution=error_from_execution,
            to_location=SOURCE_LOCATION_ERROR,
            to_execution=EXECUTION_STATE_IDLE,
        )
        source_status["location"] = SOURCE_LOCATION_ERROR
        source_status["execution_state"] = EXECUTION_STATE_IDLE
        source_status["recovery_classification"] = RECOVERY_REPAIR_REQUIRED
        campaign["error_source_relative_path"] = error_md_relative
        campaign["source_relative_path"] = error_md_relative
        if move_result.destination_image_relative:
            campaign["error_image_relative_path"] = move_result.destination_image_relative
            campaign["image_relative_path"] = move_result.destination_image_relative
        elif prior_image_relative:
            campaign["image_relative_path"] = prior_image_relative
        result_status = QUEUE_ACCEPTANCE_PARTIAL
        recovery = RECOVERY_REPAIR_REQUIRED
    else:
        source_status["location"] = prior_location
        source_status["execution_state"] = EXECUTION_STATE_PROCESSING
        source_status["recovery_classification"] = RECOVERY_REPAIR_REQUIRED
        campaign["source_relative_path"] = prior_md_relative
        campaign.pop("error_source_relative_path", None)
        campaign.pop("error_image_relative_path", None)
        result_status = QUEUE_ACCEPTANCE_FAILED
        recovery = RECOVERY_REPAIR_REQUIRED

    campaign["source_file_status"] = source_status
    campaign["updated_at"] = now
    write_result = write_campaign_metadata(base_path, campaign_id, campaign)
    metadata_failure = _metadata_write_failure_fields(write_result)
    active_source = error_md_relative or prior_md_relative
    if metadata_failure:
        return QueueAcceptanceResult(
            status=QUEUE_ACCEPTANCE_REPAIR_REQUIRED,
            queue_acceptance_status=result_status,
            campaign_id=campaign_id,
            source_relative_path=active_source,
            queued_source_relative_path=prior_md_relative,
            queued_image_relative_path=prior_image_relative,
            recovery_classification=recovery,
            physical_move_state=move_result.physical_move_state,
            metadata_written=False,
            metadata_error_code=metadata_failure.get("metadata_error_code"),
            errors=list(move_result.errors) + list(metadata_failure.get("errors", [])),
            warnings=list(move_result.warnings),
        )
    return QueueAcceptanceResult(
        status=result_status,
        queue_acceptance_status=result_status,
        campaign_id=campaign_id,
        source_relative_path=active_source,
        queued_source_relative_path=prior_md_relative,
        queued_image_relative_path=prior_image_relative,
        recovery_classification=recovery,
        physical_move_state=move_result.physical_move_state,
        metadata_written=True,
        metadata_error_code=None,
        errors=list(move_result.errors),
        warnings=list(move_result.warnings),
    )


def requeue_flow_a_source_from_error(
    base_path: Path,
    *,
    campaign_id: str,
) -> RequeueResult:
    """Move a source from error/ back to queued/ preserving campaign identity."""
    campaign = read_campaign_metadata(base_path, campaign_id)
    if campaign is None:
        return RequeueResult(
            status="failed",
            campaign_id=campaign_id,
            errors=[FLOW_A_QUEUE_CAMPAIGN_NOT_FOUND],
        )

    source_status = normalize_source_file_status(campaign.get("source_file_status"))
    if source_status.get("location") != SOURCE_LOCATION_ERROR:
        return RequeueResult(
            status="failed",
            campaign_id=campaign_id,
            errors=[FLOW_A_REQUEUE_NOT_IN_ERROR],
        )

    md_relative = campaign.get("error_source_relative_path") or campaign.get(
        "source_relative_path"
    )
    image_relative = campaign.get("error_image_relative_path") or campaign.get(
        "image_relative_path"
    )
    if not md_relative:
        return RequeueResult(
            status="failed",
            campaign_id=campaign_id,
            errors=[FLOW_A_QUEUE_SOURCE_MISSING],
        )

    move_result = coordinated_source_move(
        base_path,
        markdown_relative=md_relative,
        image_relative=image_relative,
        destination_folder=DestinationFolder.QUEUED,
        campaign_id=campaign_id,
        source_content_sha256=campaign.get("source_content_sha256"),
    )
    if move_result.status == "failed":
        return RequeueResult(
            status="failed",
            campaign_id=campaign_id,
            errors=list(move_result.errors),
        )

    now = utc_now_iso()
    validate_operational_transition(
        from_location=SOURCE_LOCATION_ERROR,
        from_execution=EXECUTION_STATE_IDLE,
        to_location=SOURCE_LOCATION_QUEUED,
        to_execution=EXECUTION_STATE_IDLE,
    )
    source_status["location"] = SOURCE_LOCATION_QUEUED
    source_status["execution_state"] = EXECUTION_STATE_IDLE
    source_status["recovery_classification"] = (
        RECOVERY_REPAIR_REQUIRED
        if move_result.status == "partial"
        else RECOVERY_NO_ACTION
    )
    source_status["physical_move_state"] = move_result.physical_move_state
    source_status["last_transition_at"] = now
    source_status["last_error"] = None
    if move_result.destination_markdown_relative:
        campaign["queued_source_relative_path"] = move_result.destination_markdown_relative
        campaign["source_relative_path"] = move_result.destination_markdown_relative
    if move_result.destination_image_relative:
        campaign["queued_image_relative_path"] = move_result.destination_image_relative
        campaign["image_relative_path"] = move_result.destination_image_relative
    campaign.setdefault("state_history", []).append(
        {
            "at": now,
            "from_state": campaign.get("state"),
            "to_state": campaign.get("state"),
            "reason": "requeued_from_error",
            "actor": ACTOR_WORKER,
            "error_code": None,
        }
    )
    campaign["source_file_status"] = source_status
    campaign["updated_at"] = now
    write_result = write_campaign_metadata(base_path, campaign_id, campaign)
    metadata_failure = _metadata_write_failure_fields(write_result)
    if metadata_failure:
        return RequeueResult(
            status="failed",
            campaign_id=campaign_id,
            queued_source_relative_path=move_result.destination_markdown_relative,
            metadata_written=False,
            metadata_error_code=metadata_failure.get("metadata_error_code"),
            errors=list(move_result.errors) + list(metadata_failure.get("errors", [])),
        )
    return RequeueResult(
        status="completed" if move_result.status == "completed" else "partial",
        campaign_id=campaign_id,
        queued_source_relative_path=move_result.destination_markdown_relative,
        metadata_written=True,
        metadata_error_code=None,
        errors=list(move_result.errors),
    )
