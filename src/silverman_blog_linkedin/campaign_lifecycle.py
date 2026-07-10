"""Campaign lifecycle metadata, state machine, and idempotency key helpers."""

from __future__ import annotations

import hashlib
import json
import os
import re
from copy import deepcopy
from silverman_blog_linkedin.file_reader import normalize_relative_path
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.run_metadata import utc_now_iso

METADATA_CAMPAIGNS_RELATIVE = "metadata/campaigns"

FLOW_A = "flow_a"
FLOW_B = "flow_b"

STATE_READY = "ready"
STATE_VALIDATION_FAILED = "validation_failed"
STATE_VALIDATED = "validated"
STATE_BLOG_PUBLISH_PENDING = "blog_publish_pending"
STATE_BLOG_PUBLISHED = "blog_published"
STATE_DERIVATIVES_PENDING = "derivatives_pending"
STATE_DERIVATIVES_GENERATED = "derivatives_generated"
STATE_DISTRIBUTION_SCHEDULED = "distribution_scheduled"
STATE_DISTRIBUTION_COMPLETE = "distribution_complete"
STATE_FLOW_A_COMPLETE = "flow_a_complete"
STATE_ERROR = "error"

LIFECYCLE_STATES = frozenset(
    {
        STATE_READY,
        STATE_VALIDATION_FAILED,
        STATE_VALIDATED,
        STATE_BLOG_PUBLISH_PENDING,
        STATE_BLOG_PUBLISHED,
        STATE_DERIVATIVES_PENDING,
        STATE_DERIVATIVES_GENERATED,
        STATE_DISTRIBUTION_SCHEDULED,
        STATE_DISTRIBUTION_COMPLETE,
        STATE_FLOW_A_COMPLETE,
        STATE_ERROR,
    }
)

CANONICAL_VARIANT_IDS = frozenset(
    {
        "executive-recruiter",
        "technical-architect",
        "engineering-leadership",
        "short-provocative",
    }
)

FORBIDDEN_METADATA_FIELDS = frozenset(
    {
        "markdown_content",
        "generated_draft_content",
        "draft_content",
        "api_key",
    }
)

SOURCE_LOCATION_READY = "ready"
SOURCE_LOCATION_PROCESSED = "processed"
SOURCE_LOCATION_ERROR = "error"

READY_SOURCE_PREFIX = "blog-posts/ready/"
PROCESSED_SOURCE_PREFIX = "blog-posts/processed/"

PHYSICAL_MOVE_STATE_NONE = "none"
PHYSICAL_MOVE_STATE_COMPLETED = "completed"
PHYSICAL_MOVE_STATE_PARTIAL = "partial"
PHYSICAL_MOVE_STATE_FAILED = "failed"

POST_SCHEDULE_SOURCE_RESOLUTION_STATES = frozenset(
    {
        STATE_DISTRIBUTION_SCHEDULED,
        STATE_DISTRIBUTION_COMPLETE,
        STATE_FLOW_A_COMPLETE,
    }
)

ACTOR_WORKER = "worker"
ACTOR_N8N = "n8n"
ACTOR_MANUAL = "manual"
VALID_ACTORS = frozenset({ACTOR_WORKER, ACTOR_N8N, ACTOR_MANUAL})

FLOW_PREFIXES = {
    FLOW_A: "flow-a",
    FLOW_B: "flow-b",
}

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
UTC_ISO_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
CAMPAIGN_ID_PATTERN = re.compile(
    r"^(flow-a|flow-b)-(\d{4}-\d{2}-\d{2})-([a-z0-9]+(?:-[a-z0-9]+)*)$"
)

FLOW_A_VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    STATE_READY: frozenset(
        {STATE_VALIDATION_FAILED, STATE_VALIDATED, STATE_ERROR}
    ),
    STATE_VALIDATION_FAILED: frozenset({STATE_ERROR}),
    STATE_VALIDATED: frozenset({STATE_BLOG_PUBLISH_PENDING, STATE_ERROR}),
    STATE_BLOG_PUBLISH_PENDING: frozenset({STATE_BLOG_PUBLISHED, STATE_ERROR}),
    STATE_BLOG_PUBLISHED: frozenset({STATE_DERIVATIVES_PENDING, STATE_ERROR}),
    STATE_DERIVATIVES_PENDING: frozenset({STATE_DERIVATIVES_GENERATED, STATE_ERROR}),
    STATE_DERIVATIVES_GENERATED: frozenset(
        {STATE_DISTRIBUTION_SCHEDULED, STATE_ERROR}
    ),
    STATE_DISTRIBUTION_SCHEDULED: frozenset(
        {STATE_DISTRIBUTION_COMPLETE, STATE_FLOW_A_COMPLETE, STATE_ERROR}
    ),
    STATE_DISTRIBUTION_COMPLETE: frozenset({STATE_FLOW_A_COMPLETE, STATE_ERROR}),
    STATE_FLOW_A_COMPLETE: frozenset(),
    STATE_ERROR: frozenset(),
}

FAILURE_STATES = frozenset({STATE_VALIDATION_FAILED, STATE_ERROR})


class CampaignLifecycleError(Exception):
    """Validation or lifecycle rule violation with a machine-readable error code."""

    def __init__(self, message: str, error_code: str) -> None:
        super().__init__(message)
        self.error_code = error_code


class InvalidStateTransition(CampaignLifecycleError):
    """Raised when a state transition is not allowed."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="invalid_state_transition")


@dataclass(frozen=True)
class MetadataCampaignsReadiness:
    ready: bool
    error_code: str | None = None


@dataclass(frozen=True)
class CampaignMetadataWriteResult:
    written: bool
    error_code: str | None = None


def validate_variant_id(variant: str) -> None:
    """Reject non-canonical variant IDs (short names and snake_case aliases)."""
    if variant not in CANONICAL_VARIANT_IDS:
        raise CampaignLifecycleError(
            f"invalid variant id {variant!r}",
            error_code="invalid_variant_id",
        )


def _validate_public_slug(public_slug: str) -> None:
    if not public_slug or not SLUG_PATTERN.match(public_slug):
        raise CampaignLifecycleError(
            f"unsafe public_slug {public_slug!r}: must match ^[a-z0-9]+(?:-[a-z0-9]+)*$",
            error_code="unsafe_public_slug",
        )


def validate_campaign_id(campaign_id: str) -> None:
    """Validate persisted campaign ID format and path safety."""
    if (
        not campaign_id
        or "/" in campaign_id
        or "\\" in campaign_id
        or ".." in campaign_id
        or " " in campaign_id
        or campaign_id != campaign_id.lower()
    ):
        raise CampaignLifecycleError(
            f"invalid campaign_id {campaign_id!r}",
            error_code="invalid_campaign_id",
        )

    match = CAMPAIGN_ID_PATTERN.match(campaign_id)
    if not match:
        raise CampaignLifecycleError(
            f"invalid campaign_id {campaign_id!r}",
            error_code="invalid_campaign_id",
        )

    publication_date = match.group(2)
    public_slug = match.group(3)
    _validate_publication_date(publication_date)
    if not SLUG_PATTERN.match(public_slug):
        raise CampaignLifecycleError(
            f"invalid campaign_id {campaign_id!r}",
            error_code="invalid_campaign_id",
        )


def _validate_publication_date(publication_date: str) -> None:
    if not DATE_PATTERN.match(publication_date):
        raise CampaignLifecycleError(
            f"invalid publication_date {publication_date!r}: expected YYYY-MM-DD",
            error_code="invalid_publication_date",
        )
    try:
        datetime.strptime(publication_date, "%Y-%m-%d")
    except ValueError as exc:
        raise CampaignLifecycleError(
            f"invalid publication_date {publication_date!r}",
            error_code="invalid_publication_date",
        ) from exc


def generate_campaign_id(
    flow: str, publication_date: str, public_slug: str
) -> str:
    """Build a safe campaign ID: flow-a-YYYY-MM-DD-<public-slug>."""
    if flow not in FLOW_PREFIXES:
        raise CampaignLifecycleError(
            f"unsupported flow {flow!r}",
            error_code="invalid_flow",
        )
    _validate_publication_date(publication_date)
    _validate_public_slug(public_slug)
    prefix = FLOW_PREFIXES[flow]
    return f"{prefix}-{publication_date}-{public_slug}"


def compute_source_content_sha256(content: bytes | str) -> str:
    """Return hex SHA-256 digest of Markdown source content."""
    if isinstance(content, str):
        content_bytes = content.encode("utf-8")
    else:
        content_bytes = content
    return hashlib.sha256(content_bytes).hexdigest()


def build_blog_publish_idempotency_key(
    *,
    source_slug: str,
    public_slug: str,
    publication_date: str,
    source_content_sha256: str,
) -> str:
    """Namespaced blog publish intent key."""
    return (
        f"blog:{source_slug}:{public_slug}:{publication_date}:{source_content_sha256}"
    )


def build_derivative_idempotency_key(
    *,
    campaign_id: str,
    source_content_sha256: str,
    variant: str,
    flow: str,
) -> str:
    """Namespaced derivative generation key using canonical variant IDs."""
    validate_variant_id(variant)
    return f"derivative:{campaign_id}:{source_content_sha256}:{variant}:{flow}"


def normalize_scheduled_at_utc(scheduled_at: str) -> str:
    """Normalize schedule timestamp to YYYY-MM-DDTHH:MM:SSZ."""
    if UTC_ISO_PATTERN.match(scheduled_at):
        return scheduled_at
    normalized = scheduled_at.replace("+00:00", "Z")
    if normalized.endswith("Z") and UTC_ISO_PATTERN.match(normalized):
        return normalized
    try:
        if scheduled_at.endswith("Z"):
            parsed = datetime.strptime(scheduled_at, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
        else:
            parsed = datetime.fromisoformat(scheduled_at)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            else:
                parsed = parsed.astimezone(timezone.utc)
    except ValueError as exc:
        raise CampaignLifecycleError(
            f"invalid scheduled_at {scheduled_at!r}",
            error_code="invalid_scheduled_at",
        ) from exc
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_schedule_idempotency_key(
    *,
    campaign_id: str,
    variant: str,
    scheduled_at: str,
) -> str:
    """Namespaced LinkedIn schedule slot key."""
    validate_variant_id(variant)
    normalized_at = normalize_scheduled_at_utc(scheduled_at)
    return f"schedule:{campaign_id}:{variant}:{normalized_at}"


def _default_source_file_status() -> dict[str, Any]:
    return {
        "location": SOURCE_LOCATION_READY,
        "marked_processed_at": None,
        "marked_error_at": None,
        "physical_move_completed_at": None,
        "physical_move_state": PHYSICAL_MOVE_STATE_NONE,
    }


def build_initial_campaign_metadata(
    *,
    flow: str,
    source_slug: str,
    public_slug: str,
    source_relative_path: str,
    image_relative_path: str,
    source_content: bytes | str,
    publication_date: str,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Create a new Flow A campaign document without content bodies."""
    if flow not in (FLOW_A, FLOW_B):
        raise CampaignLifecycleError(
            f"unsupported flow {flow!r}",
            error_code="invalid_flow",
        )

    campaign_id = generate_campaign_id(flow, publication_date, public_slug)
    content_sha256 = compute_source_content_sha256(source_content)
    timestamp = created_at or utc_now_iso()
    blog_publish_key = build_blog_publish_idempotency_key(
        source_slug=source_slug,
        public_slug=public_slug,
        publication_date=publication_date,
        source_content_sha256=content_sha256,
    )

    return {
        "campaign_id": campaign_id,
        "flow": flow,
        "state": STATE_READY,
        "created_at": timestamp,
        "updated_at": timestamp,
        "source_slug": source_slug,
        "public_slug": public_slug,
        "source_relative_path": source_relative_path,
        "image_relative_path": image_relative_path,
        "source_content_sha256": content_sha256,
        "publication_date": publication_date,
        "source_public_url": None,
        "blog_publish": {
            "idempotency_key": blog_publish_key,
            "status": "pending",
            "published_at": None,
            "error_code": None,
        },
        "variants": [],
        "state_history": [
            {
                "at": timestamp,
                "from_state": None,
                "to_state": STATE_READY,
                "reason": "Campaign created",
                "actor": ACTOR_WORKER,
                "error_code": None,
            }
        ],
        "errors": [],
        "warnings": [],
        "source_file_status": _default_source_file_status(),
    }


def _append_state_history(
    campaign: dict[str, Any],
    *,
    from_state: str | None,
    to_state: str,
    reason: str,
    actor: str,
    error_code: str | None,
    at: str,
) -> None:
    campaign.setdefault("state_history", []).append(
        {
            "at": at,
            "from_state": from_state,
            "to_state": to_state,
            "reason": reason,
            "actor": actor,
            "error_code": error_code,
        }
    )


def _update_source_file_status_for_transition(
    campaign: dict[str, Any], to_state: str, at: str
) -> None:
    status = campaign.setdefault("source_file_status", _default_source_file_status())
    if to_state == STATE_FLOW_A_COMPLETE:
        status["location"] = SOURCE_LOCATION_PROCESSED
        status["marked_processed_at"] = at
    elif to_state in FAILURE_STATES:
        status["location"] = SOURCE_LOCATION_ERROR
        status["marked_error_at"] = at


def transition_state(
    campaign: dict[str, Any],
    to_state: str,
    *,
    reason: str,
    actor: str,
    error_code: str | None = None,
) -> dict[str, Any]:
    """Enforce Flow A transitions, append history, and refresh metadata timestamps."""
    if campaign.get("flow") == FLOW_B:
        raise CampaignLifecycleError(
            "Flow B campaigns are not eligible for Flow A automatic transitions",
            error_code="flow_b_not_eligible_for_flow_a",
        )
    if actor not in VALID_ACTORS:
        raise CampaignLifecycleError(
            f"invalid actor {actor!r}",
            error_code="invalid_actor",
        )
    if to_state not in LIFECYCLE_STATES:
        raise CampaignLifecycleError(
            f"unknown state {to_state!r}",
            error_code="invalid_state",
        )

    from_state = campaign.get("state")
    if from_state not in FLOW_A_VALID_TRANSITIONS:
        raise InvalidStateTransition(f"unknown current state {from_state!r}")

    allowed = FLOW_A_VALID_TRANSITIONS[from_state]
    if to_state not in allowed:
        raise InvalidStateTransition(
            f"cannot transition from {from_state!r} to {to_state!r}"
        )

    if to_state in FAILURE_STATES and not error_code:
        raise CampaignLifecycleError(
            f"error_code is required when transitioning to {to_state!r}",
            error_code="missing_error_code",
        )

    now = utc_now_iso()
    _append_state_history(
        campaign,
        from_state=from_state,
        to_state=to_state,
        reason=reason,
        actor=actor,
        error_code=error_code,
        at=now,
    )

    if to_state in FAILURE_STATES and error_code:
        campaign.setdefault("errors", []).append(error_code)

    campaign["state"] = to_state
    campaign["updated_at"] = now
    _update_source_file_status_for_transition(campaign, to_state, now)
    return campaign


def mark_source_processed(campaign: dict[str, Any]) -> dict[str, Any]:
    """Metadata-only mark of source file as processed."""
    now = utc_now_iso()
    status = campaign.setdefault("source_file_status", _default_source_file_status())
    status["location"] = SOURCE_LOCATION_PROCESSED
    status["marked_processed_at"] = now
    campaign["updated_at"] = now
    return campaign


def mark_source_error(campaign: dict[str, Any]) -> dict[str, Any]:
    """Metadata-only mark of source file as error."""
    now = utc_now_iso()
    status = campaign.setdefault("source_file_status", _default_source_file_status())
    status["location"] = SOURCE_LOCATION_ERROR
    status["marked_error_at"] = now
    campaign["updated_at"] = now
    return campaign


def _strip_forbidden_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_forbidden_fields(nested)
            for key, nested in value.items()
            if key not in FORBIDDEN_METADATA_FIELDS
        }
    if isinstance(value, list):
        return [_strip_forbidden_fields(item) for item in value]
    return value


def sanitize_campaign_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove forbidden content bodies and secrets before persistence."""
    return _strip_forbidden_fields(deepcopy(payload))


def campaign_metadata_relative_path(campaign_id: str) -> str:
    """Relative metadata file path from editorial base."""
    validate_campaign_id(campaign_id)
    return f"{METADATA_CAMPAIGNS_RELATIVE}/{campaign_id}.json"


def check_metadata_campaigns_ready(base_path: Path) -> MetadataCampaignsReadiness:
    """Check whether metadata/campaigns exists, is a directory, and is writable."""
    metadata_dir = base_path / METADATA_CAMPAIGNS_RELATIVE
    if not metadata_dir.exists() or not metadata_dir.is_dir():
        return MetadataCampaignsReadiness(
            ready=False, error_code="metadata_campaigns_not_ready"
        )
    if not os.access(metadata_dir, os.W_OK):
        return MetadataCampaignsReadiness(
            ready=False, error_code="metadata_campaigns_not_writable"
        )
    return MetadataCampaignsReadiness(ready=True)


def write_campaign_metadata(
    base_path: Path, campaign_id: str, payload: dict[str, Any]
) -> CampaignMetadataWriteResult:
    """Persist sanitized campaign metadata when metadata/campaigns is writable."""
    try:
        validate_campaign_id(campaign_id)
    except CampaignLifecycleError:
        return CampaignMetadataWriteResult(
            written=False, error_code="invalid_campaign_id"
        )

    readiness = check_metadata_campaigns_ready(base_path)
    if not readiness.ready:
        return CampaignMetadataWriteResult(
            written=False, error_code=readiness.error_code
        )

    metadata_path = base_path / campaign_metadata_relative_path(campaign_id)
    sanitized = sanitize_campaign_metadata(payload)
    try:
        metadata_path.write_text(
            json.dumps(sanitized, indent=2) + "\n", encoding="utf-8"
        )
    except OSError:
        return CampaignMetadataWriteResult(
            written=False, error_code="campaign_metadata_write_failed"
        )
    return CampaignMetadataWriteResult(written=True)


def _campaign_source_path_candidates(campaign: dict[str, Any]) -> list[str]:
    """Return normalized source path fields that may identify a campaign."""
    candidates: list[str] = []
    for key in (
        "source_relative_path",
        "original_source_relative_path",
        "processed_source_relative_path",
    ):
        value = campaign.get(key)
        if isinstance(value, str) and value.strip():
            normalized = normalize_relative_path(value)
            if normalized not in candidates:
                candidates.append(normalized)
    return candidates


def find_campaign_by_source_path(
    base_path: Path, source_relative_path: str
) -> dict[str, Any] | None:
    """Load campaign metadata matching active, original, or processed source paths."""
    campaigns_dir = base_path / METADATA_CAMPAIGNS_RELATIVE
    if not campaigns_dir.is_dir():
        return None
    normalized = normalize_relative_path(source_relative_path)
    for metadata_path in campaigns_dir.glob("*.json"):
        try:
            data = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if normalized in _campaign_source_path_candidates(data):
            return data
    return None


def resolve_campaign_source_paths(
    campaign: dict[str, Any],
) -> tuple[str | None, str | None]:
    """Resolve active Markdown and optional companion image paths for a campaign."""
    source_status = campaign.get("source_file_status") or _default_source_file_status()
    location = source_status.get("location", SOURCE_LOCATION_READY)
    state = campaign.get("state")

    use_processed = (
        location == SOURCE_LOCATION_PROCESSED
        or state in POST_SCHEDULE_SOURCE_RESOLUTION_STATES
    )
    if use_processed:
        md_path = campaign.get("processed_source_relative_path") or campaign.get(
            "source_relative_path"
        )
        image_path = campaign.get("processed_image_relative_path") or campaign.get(
            "image_relative_path"
        )
    else:
        md_path = campaign.get("source_relative_path")
        image_path = campaign.get("image_relative_path")

    if isinstance(md_path, str) and md_path.strip():
        md_normalized = normalize_relative_path(md_path)
    else:
        md_normalized = None

    if isinstance(image_path, str) and image_path.strip():
        image_normalized = normalize_relative_path(image_path)
    else:
        image_normalized = None

    return md_normalized, image_normalized


def read_campaign_metadata(
    base_path: Path, campaign_id: str
) -> dict[str, Any] | None:
    """Load campaign metadata JSON when present."""
    try:
        validate_campaign_id(campaign_id)
    except CampaignLifecycleError:
        return None

    metadata_path = base_path / campaign_metadata_relative_path(campaign_id)
    if not metadata_path.is_file():
        return None
    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
