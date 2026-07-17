"""Flow A LinkedIn publication queue, publish-due, and cancel orchestration."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.campaign_lifecycle import (
    CampaignLifecycleError,
    FLOW_A,
    FLOW_B,
    METADATA_CAMPAIGNS_RELATIVE,
    STATE_DISTRIBUTION_COMPLETE,
    STATE_DISTRIBUTION_SCHEDULED,
    STATE_FLOW_A_COMPLETE,
    normalize_scheduled_at_utc,
    read_campaign_metadata,
    write_campaign_metadata,
)
from silverman_blog_linkedin.linkedin_client import (
    HttpClientProtocol,
    build_commentary,
    create_member_text_post,
)
from silverman_blog_linkedin.linkedin_config import (
    LinkedInPublicationSettings,
    load_linkedin_publication_settings,
)
from silverman_blog_linkedin.linkedin_distribution_schedule import AUDIENCE_SEQUENCE
from silverman_blog_linkedin.linkedin_token_provider import resolve_linkedin_access_token
from silverman_blog_linkedin.run_metadata import utc_now_iso

PUBLISH_STATE_PENDING = "pending"
PUBLISH_STATE_QUEUED = "queued"
PUBLISH_STATE_PUBLISHED = "published"
PUBLISH_STATE_FAILED = "failed"
PUBLISH_STATE_CANCELLED = "cancelled"

PUBLICATION_MODE_SAFETY_DELAY = "safety_delay"

LINKEDIN_PUBLISH_CAMPAIGN_NOT_FOUND = "linkedin_publish_campaign_not_found"
LINKEDIN_PUBLISH_FLOW_NOT_ALLOWED = "linkedin_publish_flow_not_allowed"
LINKEDIN_PUBLISH_INVALID_CAMPAIGN_STATE = "linkedin_publish_invalid_campaign_state"
LINKEDIN_PUBLISH_VARIANT_NOT_FOUND = "linkedin_publish_variant_not_found"
LINKEDIN_PUBLISH_VARIANT_NOT_PENDING = "linkedin_publish_variant_not_pending"
LINKEDIN_PUBLISH_VARIANT_NOT_QUEUED = "linkedin_publish_variant_not_queued"
LINKEDIN_PUBLISH_VARIANT_NOT_DUE = "linkedin_publish_variant_not_due"
LINKEDIN_PUBLISH_ARTIFACT_MISSING = "linkedin_publish_artifact_missing"
LINKEDIN_PUBLISH_ARTIFACT_HASH_CHANGED = "linkedin_publish_artifact_hash_changed"
LINKEDIN_PUBLISH_MISSING_SOURCE_PUBLIC_URL = "linkedin_publish_missing_source_public_url"
LINKEDIN_PUBLISH_TOKEN_MISSING = "linkedin_publish_token_missing"
LINKEDIN_PUBLISH_MEMBER_URN_MISSING = "linkedin_publish_member_urn_missing"
LINKEDIN_PUBLISH_TOKEN_INVALID = "linkedin_publish_token_invalid"
LINKEDIN_PUBLISH_TOKEN_EXPIRED = "linkedin_publish_token_expired"
LINKEDIN_PUBLISH_INSUFFICIENT_PERMISSION = "linkedin_publish_insufficient_permission"
LINKEDIN_PUBLISH_NOT_ENABLED = "linkedin_publish_not_enabled"
LINKEDIN_PUBLISH_API_ERROR = "linkedin_publish_api_error"
LINKEDIN_PUBLISH_CONTENT_INVALID = "linkedin_publish_content_invalid"
LINKEDIN_PUBLISH_METADATA_WRITE_FAILED = "linkedin_publish_metadata_write_failed"
LINKEDIN_PUBLISH_CANCEL_NOT_ALLOWED = "linkedin_publish_cancel_not_allowed"
LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_NOT_DUE = (
    "linkedin_publish_auto_queue_skipped_not_due"
)
LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_SUPERVISION = (
    "linkedin_publish_auto_queue_skipped_supervision"
)
LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_STATE = (
    "linkedin_publish_auto_queue_skipped_state"
)
LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_SEQUENCE = (
    "linkedin_publish_auto_queue_skipped_sequence"
)
LINKEDIN_PUBLISH_BLOCKED_SEQUENCE = "linkedin_publish_blocked_sequence"
LINKEDIN_PUBLISH_BLOCKED_CADENCE = "linkedin_publish_blocked_cadence"
LINKEDIN_PUBLISH_BLOCKED_EVIDENCE_INVALID = (
    "linkedin_publish_blocked_evidence_invalid"
)
LINKEDIN_SUPERVISION_ACTION_NOT_ALLOWED = "linkedin_supervision_action_not_allowed"
LINKEDIN_OAUTH_TOKEN_MISSING = "linkedin_oauth_token_missing"
LINKEDIN_OAUTH_REFRESH_FAILED = "linkedin_oauth_refresh_failed"
LINKEDIN_OAUTH_REAUTHORIZATION_REQUIRED = "linkedin_oauth_reauthorization_required"

# US-022 stable recovery error codes.
LINKEDIN_PUBLISH_RETRY_LIMIT_EXHAUSTED = "linkedin_publish_retry_limit_exhausted"
LINKEDIN_PUBLISH_RECOVERY_CONFIRMATION_REQUIRED = (
    "linkedin_publish_recovery_confirmation_required"
)
LINKEDIN_PUBLISH_RECOVERY_CONFIRMATION_INVALID = (
    "linkedin_publish_recovery_confirmation_invalid"
)
LINKEDIN_PUBLISH_CONTENT_CORRECTION_REQUIRED = (
    "linkedin_publish_content_correction_required"
)
LINKEDIN_PUBLISH_RECOVERY_EVIDENCE_INVALID = (
    "linkedin_publish_recovery_evidence_invalid"
)

# US-022 retry budget: one initial real LinkedIn API attempt plus at most two
# manually authorized retries per variant. Only real API calls count.
MAX_MANUAL_RETRIES = 2
MAX_REAL_ATTEMPTS = MAX_MANUAL_RETRIES + 1

# US-021 recovery classes (stable machine tokens; canonical table lives in the
# linkedin-retry-recovery-classification capability and operator policy).
RECOVERY_CLASS_TRANSIENT = "recoverable_transient"
RECOVERY_CLASS_REMEDIATION = "recoverable_after_remediation"
RECOVERY_CLASS_CONTENT_INVALID = "non_recoverable_as_is"
RECOVERY_CLASS_UNCERTAIN = "uncertain"

# US-022 class-specific operator confirmations (queue request enum values).
RECOVERY_CONFIRMATION_REMEDIATION_COMPLETED = "remediation_completed"
RECOVERY_CONFIRMATION_POST_ABSENCE_VERIFIED = "linkedin_post_absence_verified"

# US-022 recovery-history actions.
RECOVERY_ACTION_MANUAL_REQUEUE = "manual_requeue"
RECOVERY_ACTION_CONTENT_CORRECTED = "content_corrected"
RECOVERY_ACTION_RECOVERY_CANCELLED = "recovery_cancelled"

ATTEMPT_OUTCOME_FAILED = "failed"
ATTEMPT_OUTCOME_PUBLISHED = "published"

QUEUE_ELIGIBLE_PUBLISH_STATES = frozenset({PUBLISH_STATE_PENDING, PUBLISH_STATE_FAILED})

# US-020 publish-time guard: earlier variants in these states block later ones.
AWAITING_PUBLICATION_STATES = frozenset({PUBLISH_STATE_PENDING, PUBLISH_STATE_QUEUED})

# US-020 cadence rule: real minimum interval between successful publications
# within one campaign, anchored to stored `published_at` evidence (US-019).
CADENCE_MINIMUM_INTERVAL = timedelta(hours=72)

PUBLICATION_ELIGIBLE_CAMPAIGN_STATES = frozenset(
    {
        STATE_DISTRIBUTION_SCHEDULED,
        STATE_DISTRIBUTION_COMPLETE,
        STATE_FLOW_A_COMPLETE,
    }
)

SUPPORTED_RECOVERY_CONFIRMATIONS = frozenset(
    {
        RECOVERY_CONFIRMATION_REMEDIATION_COMPLETED,
        RECOVERY_CONFIRMATION_POST_ABSENCE_VERIFIED,
    }
)


def classify_linkedin_recovery(
    last_error_code: str | None,
    http_status: int | None,
) -> str:
    """Shared US-021 classifier over stored US-019 failure evidence.

    Single internal source of the canonical classification table in
    `linkedin-retry-recovery-classification`. Unlisted code/status
    combinations fail safe to uncertain (duplicate risk). `retryable`
    is descriptive evidence only and is never consulted here.
    """
    status_is_numeric = isinstance(http_status, int) and not isinstance(
        http_status, bool
    )
    if last_error_code == LINKEDIN_PUBLISH_API_ERROR:
        if status_is_numeric and (http_status == 429 or http_status >= 500):
            return RECOVERY_CLASS_TRANSIENT
        # null (transport), 201 (success without URN), and unlisted 4xx.
        return RECOVERY_CLASS_UNCERTAIN
    if last_error_code == LINKEDIN_PUBLISH_TOKEN_INVALID and http_status == 401:
        return RECOVERY_CLASS_REMEDIATION
    if last_error_code == LINKEDIN_PUBLISH_TOKEN_EXPIRED:
        return RECOVERY_CLASS_REMEDIATION
    if (
        last_error_code == LINKEDIN_PUBLISH_INSUFFICIENT_PERMISSION
        and http_status == 403
    ):
        return RECOVERY_CLASS_REMEDIATION
    if last_error_code == LINKEDIN_PUBLISH_CONTENT_INVALID and http_status in (
        400,
        422,
    ):
        return RECOVERY_CLASS_CONTENT_INVALID
    return RECOVERY_CLASS_UNCERTAIN


def _retry_counters(attempt_count: int) -> tuple[int, int, int]:
    """Derive (attempt_count, manual_retries_used, manual_retries_remaining)."""
    used = min(max(attempt_count - 1, 0), MAX_MANUAL_RETRIES)
    remaining = max(MAX_MANUAL_RETRIES - used, 0)
    return attempt_count, used, remaining


def _validated_attempt_history(
    entry: dict[str, Any],
) -> tuple[list[dict[str, Any]] | None, str | None]:
    """Return validated append-only attempt history or a fail-closed error."""
    raw = entry.get("linkedin_publication_attempts")
    if raw is None:
        return [], None
    if not isinstance(raw, list):
        return None, LINKEDIN_PUBLISH_RECOVERY_EVIDENCE_INVALID
    attempts: list[dict[str, Any]] = []
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict) or item.get("attempt_number") != index:
            return None, LINKEDIN_PUBLISH_RECOVERY_EVIDENCE_INVALID
        attempts.append(item)
    return attempts, None


def _validated_failure_evidence(
    entry: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    """Validate mandatory US-019 failure fields on the latest evidence object."""
    evidence = entry.get("linkedin_publication")
    if not isinstance(evidence, dict):
        return None, LINKEDIN_PUBLISH_RECOVERY_EVIDENCE_INVALID
    last_error_code = evidence.get("last_error_code")
    last_failed_at = evidence.get("last_failed_at")
    retryable = evidence.get("retryable")
    if not isinstance(last_error_code, str) or not last_error_code.strip():
        return None, LINKEDIN_PUBLISH_RECOVERY_EVIDENCE_INVALID
    if not isinstance(last_failed_at, str) or not last_failed_at.strip():
        return None, LINKEDIN_PUBLISH_RECOVERY_EVIDENCE_INVALID
    try:
        _parse_utc(last_failed_at)
    except (CampaignLifecycleError, TypeError, ValueError):
        return None, LINKEDIN_PUBLISH_RECOVERY_EVIDENCE_INVALID
    if not isinstance(retryable, bool):
        return None, LINKEDIN_PUBLISH_RECOVERY_EVIDENCE_INVALID
    if "http_status" not in evidence:
        return None, LINKEDIN_PUBLISH_RECOVERY_EVIDENCE_INVALID
    http_status = evidence.get("http_status")
    if http_status is not None and (
        not isinstance(http_status, int) or isinstance(http_status, bool)
    ):
        return None, LINKEDIN_PUBLISH_RECOVERY_EVIDENCE_INVALID
    return evidence, None


def _build_failed_attempt_entry(
    *,
    attempt_number: int,
    attempted_at: str,
    derivative_content_sha256: str | None,
    last_error_code: str,
    last_failed_at: str,
    retryable: bool,
    http_status: int | None,
) -> dict[str, Any]:
    return {
        "attempt_number": attempt_number,
        "attempted_at": attempted_at,
        "outcome": ATTEMPT_OUTCOME_FAILED,
        "derivative_content_sha256": derivative_content_sha256,
        "last_error_code": last_error_code,
        "last_failed_at": last_failed_at,
        "retryable": retryable,
        "http_status": http_status,
    }


def _build_published_attempt_entry(
    *,
    attempt_number: int,
    attempted_at: str,
    derivative_content_sha256: str | None,
    provider: str,
    post_urn: str,
    published_at: str,
    http_status: int | None,
) -> dict[str, Any]:
    return {
        "attempt_number": attempt_number,
        "attempted_at": attempted_at,
        "outcome": ATTEMPT_OUTCOME_PUBLISHED,
        "derivative_content_sha256": derivative_content_sha256,
        "provider": provider,
        "post_urn": post_urn,
        "published_at": published_at,
        "http_status": http_status,
    }


def _normalized_failed_attempt_history(
    entry: dict[str, Any],
) -> tuple[list[dict[str, Any]] | None, str | None]:
    """Attempt history for a failed variant, synthesizing legacy attempt 1.

    Legacy failed variants (valid US-019 evidence, no history) normalize to a
    single failed attempt using `last_failed_at` as `attempted_at` and the
    current verified content hash. Missing or invalid mandatory evidence
    fails closed; nothing is invented. The returned list is a plan — callers
    persist it only on a real mutating recovery action.
    """
    attempts, history_error = _validated_attempt_history(entry)
    if history_error:
        return None, history_error
    assert attempts is not None
    if attempts:
        return attempts, None
    evidence, evidence_error = _validated_failure_evidence(entry)
    if evidence_error:
        return None, evidence_error
    assert evidence is not None
    content_hash = entry.get("derivative_content_sha256")
    if not isinstance(content_hash, str) or not content_hash:
        return None, LINKEDIN_PUBLISH_RECOVERY_EVIDENCE_INVALID
    return (
        [
            _build_failed_attempt_entry(
                attempt_number=1,
                attempted_at=evidence["last_failed_at"],
                derivative_content_sha256=content_hash,
                last_error_code=evidence["last_error_code"],
                last_failed_at=evidence["last_failed_at"],
                retryable=evidence["retryable"],
                http_status=evidence["http_status"],
            )
        ],
        None,
    )


def _recovery_history(entry: dict[str, Any]) -> list[dict[str, Any]]:
    raw = entry.get("linkedin_recovery_history")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _build_recovery_event(
    *,
    event_number: int,
    action: str,
    recorded_at: str,
    attempt_number: int,
    classification: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "event_number": event_number,
        "action": action,
        "recorded_at": recorded_at,
        "attempt_number": attempt_number,
        "classification": classification,
    }
    if details:
        for key, value in details.items():
            if value is not None:
                event[key] = value
    return event


def _append_recovery_event(
    entry: dict[str, Any],
    *,
    action: str,
    recorded_at: str,
    attempt_number: int,
    classification: str,
    details: dict[str, Any] | None = None,
) -> None:
    history = _recovery_history(entry)
    history.append(
        _build_recovery_event(
            event_number=len(history) + 1,
            action=action,
            recorded_at=recorded_at,
            attempt_number=attempt_number,
            classification=classification,
            details=details,
        )
    )
    entry["linkedin_recovery_history"] = history


def _latest_content_correction_matches(
    entry: dict[str, Any],
    *,
    latest_attempt_number: int,
    current_content_sha256: str | None,
) -> bool:
    """True when the latest correction is tied to the latest failed attempt."""
    corrections = [
        event
        for event in _recovery_history(entry)
        if event.get("action") == RECOVERY_ACTION_CONTENT_CORRECTED
        and event.get("attempt_number") == latest_attempt_number
    ]
    if not corrections:
        return False
    return corrections[-1].get("new_content_sha256") == current_content_sha256


def _attempts_for_append(entry: dict[str, Any]) -> list[dict[str, Any]]:
    """Existing attempt entries as a list safe to append the next attempt to."""
    raw = entry.get("linkedin_publication_attempts")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _entry_attempt_counters(
    entry: dict[str, Any],
) -> tuple[int | None, int | None, int | None]:
    """Counters from validated stored attempt history; None triple if invalid."""
    attempts, error = _validated_attempt_history(entry)
    if error or attempts is None:
        return None, None, None
    return _retry_counters(len(attempts))


@dataclass
class LinkedInPublicationVariantResult:
    campaign_id: str
    variant: str
    publish_state: str
    publish_after_utc: str | None = None
    published_at: str | None = None
    linkedin_post_urn: str | None = None
    status: str = "completed"
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str | None = None
    publication_attempt_count: int | None = None
    manual_retries_used: int | None = None
    manual_retries_remaining: int | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        # US-022 counters are additive: omitted when no validated attempt
        # evidence exists so pre-US-022 response shapes stay byte-identical.
        for key in (
            "publication_attempt_count",
            "manual_retries_used",
            "manual_retries_remaining",
        ):
            if payload[key] is None:
                payload.pop(key)
        return payload


@dataclass
class LinkedInQueuePublicationResult:
    status: str
    campaign_id: str | None = None
    variant: str | None = None
    state: str | None = None
    publish_state: str | None = None
    dry_run: bool = True
    publish_after_utc: str | None = None
    publication_queued_at: str | None = None
    publication_mode: str | None = None
    publication_safety_delay_minutes: int | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata_written: bool = False
    publication_attempt_count: int | None = None
    manual_retries_used: int | None = None
    manual_retries_remaining: int | None = None
    recovery_classification: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LinkedInAutoQueueVariantResult:
    campaign_id: str
    variant: str
    publish_state: str
    publish_after_utc: str | None = None
    linkedin_post_urn: str | None = None
    published_at: str | None = None
    status: str = "completed"
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str | None = None
    metadata_written: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LinkedInPublishDueResult:
    status: str
    dry_run: bool = True
    publish_now: bool = False
    results: list[LinkedInPublicationVariantResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    auto_queue_pending: bool = False
    auto_queue_results: list[LinkedInAutoQueueVariantResult] = field(
        default_factory=list
    )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "status": self.status,
            "dry_run": self.dry_run,
            "publish_now": self.publish_now,
            "results": [item.to_dict() for item in self.results],
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }
        if self.auto_queue_pending:
            payload["auto_queue_pending"] = True
            payload["auto_queue_results"] = [
                item.to_dict() for item in self.auto_queue_results
            ]
        return payload


@dataclass
class LinkedInCancelPublicationResult:
    status: str
    campaign_id: str | None = None
    variant: str | None = None
    state: str | None = None
    publish_state: str | None = None
    dry_run: bool = True
    phase: str | None = None
    operator_supervision: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata_written: bool = False
    publication_attempt_count: int | None = None
    manual_retries_used: int | None = None
    manual_retries_remaining: int | None = None
    recovery_classification: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _get_variant_metadata_map(campaign: dict[str, Any]) -> dict[str, dict[str, Any]]:
    variants = campaign.get("variants") or []
    return {
        entry["variant"]: entry
        for entry in variants
        if isinstance(entry, dict) and entry.get("variant")
    }


def _find_variant_entry(
    campaign: dict[str, Any], variant: str
) -> dict[str, Any] | None:
    return _get_variant_metadata_map(campaign).get(variant)


def _read_artifact_text(base_path: Path, artifact_relative_path: str) -> str | None:
    artifact_path = base_path / artifact_relative_path
    if not artifact_path.is_file():
        return None
    return artifact_path.read_text(encoding="utf-8")


def _verify_artifact(
    base_path: Path, entry: dict[str, Any]
) -> tuple[str | None, str | None]:
    artifact_relative = entry.get("artifact_relative_path")
    stored_hash = entry.get("derivative_content_sha256")
    if not artifact_relative or not stored_hash:
        return None, LINKEDIN_PUBLISH_ARTIFACT_MISSING
    artifact_path = base_path / artifact_relative
    if not artifact_path.is_file():
        return None, LINKEDIN_PUBLISH_ARTIFACT_MISSING
    on_disk_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    if on_disk_hash != stored_hash:
        return None, LINKEDIN_PUBLISH_ARTIFACT_HASH_CHANGED
    return artifact_path.read_text(encoding="utf-8"), None


def _validate_campaign_eligibility(
    campaign: dict[str, Any] | None,
) -> list[str]:
    if campaign is None:
        return [LINKEDIN_PUBLISH_CAMPAIGN_NOT_FOUND]
    if campaign.get("flow") == FLOW_B:
        return [LINKEDIN_PUBLISH_FLOW_NOT_ALLOWED]
    if campaign.get("state") not in PUBLICATION_ELIGIBLE_CAMPAIGN_STATES:
        return [LINKEDIN_PUBLISH_INVALID_CAMPAIGN_STATE]
    return []


def _resolve_source_public_url(campaign: dict[str, Any]) -> str | None:
    url = campaign.get("source_public_url")
    if isinstance(url, str) and url.strip():
        return url.strip()
    package = campaign.get("linkedin_package") or {}
    package_url = package.get("source_public_url")
    if isinstance(package_url, str) and package_url.strip():
        return package_url.strip()
    return None


def _parse_utc(value: str) -> datetime:
    normalized = normalize_scheduled_at_utc(value)
    return datetime.strptime(normalized, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _campaign_variants_in_sequence(campaign: dict[str, Any]) -> list[dict[str, Any]]:
    """Campaign variants ordered by the canonical audience sequence.

    Non-canonical variant ids order deterministically after canonical ones by
    ascending `scheduled_at_utc`, then variant id.
    """
    entries = [
        entry
        for entry in campaign.get("variants") or []
        if isinstance(entry, dict) and entry.get("variant")
    ]
    order_index = {
        variant_id: index for index, variant_id in enumerate(AUDIENCE_SEQUENCE)
    }

    def sort_key(entry: dict[str, Any]) -> tuple[int, int, str, str]:
        variant_id = str(entry["variant"])
        if variant_id in order_index:
            return (0, order_index[variant_id], "", "")
        return (1, 0, str(entry.get("scheduled_at_utc") or ""), variant_id)

    return sorted(entries, key=sort_key)


def _earlier_variant_awaiting_publication(
    campaign: dict[str, Any], variant: str
) -> bool:
    for entry in _campaign_variants_in_sequence(campaign):
        if entry.get("variant") == variant:
            return False
        if entry.get("publish_state") in AWAITING_PUBLICATION_STATES:
            return True
    return False


def _publish_guard_block_reason(
    campaign: dict[str, Any],
    variant: str,
    *,
    now: datetime,
) -> str | None:
    """US-020 per-campaign publish-time guard: sequence -> evidence -> cadence.

    Returns a stable block reason, or None when the variant may proceed to the
    existing publish rules. Read-only: never mutates sibling or supervision
    metadata.
    """
    if _earlier_variant_awaiting_publication(campaign, variant):
        return LINKEDIN_PUBLISH_BLOCKED_SEQUENCE

    published_at_values: list[datetime] = []
    for entry in _campaign_variants_in_sequence(campaign):
        if entry.get("variant") == variant:
            continue
        if entry.get("publish_state") != PUBLISH_STATE_PUBLISHED:
            continue
        published_at = entry.get("published_at")
        if not isinstance(published_at, str) or not published_at.strip():
            return LINKEDIN_PUBLISH_BLOCKED_EVIDENCE_INVALID
        try:
            published_at_values.append(_parse_utc(published_at))
        except (CampaignLifecycleError, TypeError, ValueError):
            return LINKEDIN_PUBLISH_BLOCKED_EVIDENCE_INVALID

    for published_dt in published_at_values:
        if published_dt + CADENCE_MINIMUM_INTERVAL > now:
            return LINKEDIN_PUBLISH_BLOCKED_CADENCE
    return None


def _compute_publish_after_utc(
    *,
    now: datetime,
    safety_delay_minutes: int,
    publish_after_utc: str | None,
) -> str:
    if publish_after_utc is not None:
        return normalize_scheduled_at_utc(publish_after_utc)
    due = now + timedelta(minutes=safety_delay_minutes)
    return due.strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_real_publish_config(
    settings: LinkedInPublicationSettings,
) -> list[str]:
    if not settings.publication_enabled:
        return [LINKEDIN_PUBLISH_NOT_ENABLED]
    return []


def _list_campaign_ids(base_path: Path) -> list[str]:
    campaigns_dir = base_path / METADATA_CAMPAIGNS_RELATIVE
    if not campaigns_dir.is_dir():
        return []
    return sorted(path.stem for path in campaigns_dir.glob("*.json"))


def _failed_queue_recovery_validation(
    entry: dict[str, Any],
    *,
    recovery_confirmation: str | None,
) -> tuple[
    list[dict[str, Any]] | None,
    str | None,
    tuple[int | None, int | None, int | None],
    list[str],
]:
    """US-022 failed-state re-queue validation.

    Returns (normalized_attempts, classification, counters, errors). Attempts
    include synthesized legacy attempt 1 when applicable; callers persist them
    only on a real mutation.
    """
    evidence, evidence_error = _validated_failure_evidence(entry)
    if evidence_error:
        return None, None, (None, None, None), [evidence_error]
    assert evidence is not None

    attempts, history_error = _normalized_failed_attempt_history(entry)
    if history_error:
        return None, None, (None, None, None), [history_error]
    assert attempts is not None

    classification = classify_linkedin_recovery(
        evidence["last_error_code"], evidence["http_status"]
    )
    counters = _retry_counters(len(attempts))

    if len(attempts) >= MAX_REAL_ATTEMPTS:
        return (
            attempts,
            classification,
            counters,
            [LINKEDIN_PUBLISH_RETRY_LIMIT_EXHAUSTED],
        )

    if classification == RECOVERY_CLASS_TRANSIENT:
        if recovery_confirmation is not None:
            return (
                attempts,
                classification,
                counters,
                [LINKEDIN_PUBLISH_RECOVERY_CONFIRMATION_INVALID],
            )
    elif classification == RECOVERY_CLASS_REMEDIATION:
        if recovery_confirmation is None:
            return (
                attempts,
                classification,
                counters,
                [LINKEDIN_PUBLISH_RECOVERY_CONFIRMATION_REQUIRED],
            )
        if recovery_confirmation != RECOVERY_CONFIRMATION_REMEDIATION_COMPLETED:
            return (
                attempts,
                classification,
                counters,
                [LINKEDIN_PUBLISH_RECOVERY_CONFIRMATION_INVALID],
            )
    elif classification == RECOVERY_CLASS_UNCERTAIN:
        if recovery_confirmation is None:
            return (
                attempts,
                classification,
                counters,
                [LINKEDIN_PUBLISH_RECOVERY_CONFIRMATION_REQUIRED],
            )
        if recovery_confirmation != RECOVERY_CONFIRMATION_POST_ABSENCE_VERIFIED:
            return (
                attempts,
                classification,
                counters,
                [LINKEDIN_PUBLISH_RECOVERY_CONFIRMATION_INVALID],
            )
    else:  # RECOVERY_CLASS_CONTENT_INVALID
        if recovery_confirmation is not None:
            # A confirmation can never replace mechanical content correction.
            return (
                attempts,
                classification,
                counters,
                [LINKEDIN_PUBLISH_RECOVERY_CONFIRMATION_INVALID],
            )
        if not _latest_content_correction_matches(
            entry,
            latest_attempt_number=len(attempts),
            current_content_sha256=entry.get("derivative_content_sha256"),
        ):
            return (
                attempts,
                classification,
                counters,
                [LINKEDIN_PUBLISH_CONTENT_CORRECTION_REQUIRED],
            )

    return attempts, classification, counters, []


def queue_linkedin_publication(
    base_path: Path,
    *,
    campaign_id: str,
    variant: str,
    dry_run: bool = True,
    safety_delay_minutes: int | None = None,
    publish_after_utc: str | None = None,
    recovery_confirmation: str | None = None,
    environ: dict[str, str] | None = None,
    now: datetime | None = None,
) -> LinkedInQueuePublicationResult:
    """Authorize a variant for LinkedIn publication with safety delay metadata."""
    settings_load = load_linkedin_publication_settings(environ)
    if settings_load.config_invalid:
        return LinkedInQueuePublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            dry_run=dry_run,
            errors=["linkedin_publish_config_invalid"],
        )

    settings = settings_load.settings
    resolved_delay = (
        safety_delay_minutes
        if safety_delay_minutes is not None
        else settings.default_safety_delay_minutes
    )

    campaign = read_campaign_metadata(base_path, campaign_id)
    eligibility_errors = _validate_campaign_eligibility(campaign)
    if eligibility_errors:
        return LinkedInQueuePublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state") if campaign else None,
            dry_run=dry_run,
            errors=eligibility_errors,
        )
    assert campaign is not None

    entry = _find_variant_entry(campaign, variant)
    if entry is None:
        return LinkedInQueuePublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            dry_run=dry_run,
            errors=[LINKEDIN_PUBLISH_VARIANT_NOT_FOUND],
        )

    publish_state = entry.get("publish_state")
    if publish_state not in QUEUE_ELIGIBLE_PUBLISH_STATES:
        return LinkedInQueuePublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=dry_run,
            errors=[LINKEDIN_PUBLISH_VARIANT_NOT_PENDING],
        )

    is_failed_requeue = publish_state == PUBLISH_STATE_FAILED
    if not is_failed_requeue and recovery_confirmation is not None:
        # Recovery confirmations only apply to failed-state re-queue.
        return LinkedInQueuePublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=dry_run,
            errors=[LINKEDIN_PUBLISH_RECOVERY_CONFIRMATION_INVALID],
        )

    _, artifact_error = _verify_artifact(base_path, entry)
    if artifact_error:
        return LinkedInQueuePublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=dry_run,
            errors=[artifact_error],
        )

    if _resolve_source_public_url(campaign) is None:
        return LinkedInQueuePublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=dry_run,
            errors=[LINKEDIN_PUBLISH_MISSING_SOURCE_PUBLIC_URL],
        )

    normalized_attempts: list[dict[str, Any]] | None = None
    recovery_classification: str | None = None
    attempt_count: int | None = None
    retries_used: int | None = None
    retries_remaining: int | None = None
    if is_failed_requeue:
        (
            normalized_attempts,
            recovery_classification,
            (attempt_count, retries_used, retries_remaining),
            recovery_errors,
        ) = _failed_queue_recovery_validation(
            entry, recovery_confirmation=recovery_confirmation
        )
        if recovery_errors:
            return LinkedInQueuePublicationResult(
                status="failed",
                campaign_id=campaign_id,
                variant=variant,
                state=campaign.get("state"),
                publish_state=publish_state,
                dry_run=dry_run,
                errors=recovery_errors,
                publication_attempt_count=attempt_count,
                manual_retries_used=retries_used,
                manual_retries_remaining=retries_remaining,
                recovery_classification=recovery_classification,
            )
        assert normalized_attempts is not None
    else:
        attempt_count, retries_used, retries_remaining = _entry_attempt_counters(
            entry
        )

    current = now or datetime.now(timezone.utc)
    planned_publish_after = _compute_publish_after_utc(
        now=current,
        safety_delay_minutes=resolved_delay,
        publish_after_utc=publish_after_utc,
    )

    if dry_run:
        return LinkedInQueuePublicationResult(
            status="completed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=True,
            publish_after_utc=planned_publish_after,
            publication_mode=PUBLICATION_MODE_SAFETY_DELAY,
            publication_safety_delay_minutes=resolved_delay,
            metadata_written=False,
            publication_attempt_count=attempt_count,
            manual_retries_used=retries_used,
            manual_retries_remaining=retries_remaining,
            recovery_classification=recovery_classification,
        )

    working = deepcopy(campaign)
    metadata_map = _get_variant_metadata_map(working)
    updated_entry = dict(metadata_map[variant])
    queued_at = utc_now_iso()
    updated_entry["publish_state"] = PUBLISH_STATE_QUEUED
    updated_entry["publish_after_utc"] = planned_publish_after
    updated_entry["publication_queued_at"] = queued_at
    updated_entry["publication_mode"] = PUBLICATION_MODE_SAFETY_DELAY
    updated_entry["publication_safety_delay_minutes"] = resolved_delay
    if is_failed_requeue:
        # US-022: re-queue preserves latest `linkedin_publication` evidence,
        # persists (possibly legacy-normalized) attempt history, and records
        # the manual re-queue as an append-only recovery event.
        assert normalized_attempts is not None
        assert recovery_classification is not None
        updated_entry["linkedin_publication_attempts"] = normalized_attempts
        _append_recovery_event(
            updated_entry,
            action=RECOVERY_ACTION_MANUAL_REQUEUE,
            recorded_at=queued_at,
            attempt_number=len(normalized_attempts),
            classification=recovery_classification,
            details={"recovery_confirmation": recovery_confirmation},
        )
    metadata_map[variant] = updated_entry
    working["variants"] = list(metadata_map.values())

    write_result = write_campaign_metadata(base_path, campaign_id, working)
    if not write_result.written:
        return LinkedInQueuePublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=working.get("state"),
            publish_state=publish_state,
            dry_run=False,
            publish_after_utc=planned_publish_after,
            publication_mode=PUBLICATION_MODE_SAFETY_DELAY,
            publication_safety_delay_minutes=resolved_delay,
            errors=[LINKEDIN_PUBLISH_METADATA_WRITE_FAILED],
            metadata_written=False,
            publication_attempt_count=attempt_count,
            manual_retries_used=retries_used,
            manual_retries_remaining=retries_remaining,
            recovery_classification=recovery_classification,
        )

    return LinkedInQueuePublicationResult(
        status="completed",
        campaign_id=campaign_id,
        variant=variant,
        state=working.get("state"),
        publish_state=PUBLISH_STATE_QUEUED,
        dry_run=False,
        publish_after_utc=planned_publish_after,
        publication_queued_at=queued_at,
        publication_mode=PUBLICATION_MODE_SAFETY_DELAY,
        publication_safety_delay_minutes=resolved_delay,
        metadata_written=True,
        publication_attempt_count=attempt_count,
        manual_retries_used=retries_used,
        manual_retries_remaining=retries_remaining,
        recovery_classification=recovery_classification,
    )


def _publish_single_variant(
    base_path: Path,
    *,
    campaign_id: str,
    variant: str,
    dry_run: bool,
    publish_now: bool,
    settings: LinkedInPublicationSettings,
    environ: dict[str, str] | None,
    http_client: HttpClientProtocol | None,
    now: datetime,
) -> LinkedInPublicationVariantResult:
    campaign = read_campaign_metadata(base_path, campaign_id)
    eligibility_errors = _validate_campaign_eligibility(campaign)
    if eligibility_errors:
        return LinkedInPublicationVariantResult(
            campaign_id=campaign_id,
            variant=variant,
            publish_state="unknown",
            status="failed",
            errors=eligibility_errors,
        )
    assert campaign is not None

    entry = _find_variant_entry(campaign, variant)
    if entry is None:
        return LinkedInPublicationVariantResult(
            campaign_id=campaign_id,
            variant=variant,
            publish_state="unknown",
            status="failed",
            errors=[LINKEDIN_PUBLISH_VARIANT_NOT_FOUND],
        )

    publish_state = entry.get("publish_state")
    # US-022 counters from stored attempt evidence; blocked/no-call paths
    # below report these unchanged and never append an attempt entry.
    attempt_count, retries_used, retries_remaining = _entry_attempt_counters(entry)
    if publish_state == PUBLISH_STATE_PUBLISHED:
        return LinkedInPublicationVariantResult(
            campaign_id=campaign_id,
            variant=variant,
            publish_state=PUBLISH_STATE_PUBLISHED,
            published_at=entry.get("published_at"),
            linkedin_post_urn=entry.get("linkedin_post_urn"),
            status="completed",
            warnings=["linkedin_publish_already_published"],
            publication_attempt_count=attempt_count,
            manual_retries_used=retries_used,
            manual_retries_remaining=retries_remaining,
        )

    if publish_state != PUBLISH_STATE_QUEUED:
        return LinkedInPublicationVariantResult(
            campaign_id=campaign_id,
            variant=variant,
            publish_state=publish_state or "unknown",
            status="failed",
            errors=[LINKEDIN_PUBLISH_VARIANT_NOT_QUEUED],
        )

    publish_after = entry.get("publish_after_utc")
    if not publish_now and publish_after:
        due_at = _parse_utc(publish_after)
        if due_at > now:
            return LinkedInPublicationVariantResult(
                campaign_id=campaign_id,
                variant=variant,
                publish_state=PUBLISH_STATE_QUEUED,
                publish_after_utc=publish_after,
                status="completed",
                skipped=True,
                skip_reason=LINKEDIN_PUBLISH_VARIANT_NOT_DUE,
                publication_attempt_count=attempt_count,
                manual_retries_used=retries_used,
                manual_retries_remaining=retries_remaining,
            )

    # US-020 publish-time guard: evaluated in every invocation mode, after the
    # existing state and publish_after_utc handling and before dry-run
    # reporting, config validation, token resolution, or any LinkedIn call.
    # `publish_now` bypasses only the timing gates above, never this guard.
    guard_reason = _publish_guard_block_reason(campaign, variant, now=now)
    if guard_reason is not None:
        return LinkedInPublicationVariantResult(
            campaign_id=campaign_id,
            variant=variant,
            publish_state=PUBLISH_STATE_QUEUED,
            publish_after_utc=publish_after,
            status="completed",
            skipped=True,
            skip_reason=guard_reason,
            publication_attempt_count=attempt_count,
            manual_retries_used=retries_used,
            manual_retries_remaining=retries_remaining,
        )

    artifact_text, artifact_error = _verify_artifact(base_path, entry)
    if artifact_error:
        return LinkedInPublicationVariantResult(
            campaign_id=campaign_id,
            variant=variant,
            publish_state=PUBLISH_STATE_QUEUED,
            status="failed",
            errors=[artifact_error],
            publication_attempt_count=attempt_count,
            manual_retries_used=retries_used,
            manual_retries_remaining=retries_remaining,
        )
    assert artifact_text is not None

    blog_url = _resolve_source_public_url(campaign)
    if blog_url is None:
        return LinkedInPublicationVariantResult(
            campaign_id=campaign_id,
            variant=variant,
            publish_state=PUBLISH_STATE_QUEUED,
            status="failed",
            errors=[LINKEDIN_PUBLISH_MISSING_SOURCE_PUBLIC_URL],
            publication_attempt_count=attempt_count,
            manual_retries_used=retries_used,
            manual_retries_remaining=retries_remaining,
        )

    if dry_run:
        return LinkedInPublicationVariantResult(
            campaign_id=campaign_id,
            variant=variant,
            publish_state=PUBLISH_STATE_QUEUED,
            publish_after_utc=publish_after,
            status="completed",
            warnings=["linkedin_publish_dry_run"],
            publication_attempt_count=attempt_count,
            manual_retries_used=retries_used,
            manual_retries_remaining=retries_remaining,
        )

    config_errors = _validate_real_publish_config(settings)
    if config_errors:
        return LinkedInPublicationVariantResult(
            campaign_id=campaign_id,
            variant=variant,
            publish_state=PUBLISH_STATE_QUEUED,
            publish_after_utc=publish_after,
            status="failed",
            errors=config_errors,
            publication_attempt_count=attempt_count,
            manual_retries_used=retries_used,
            manual_retries_remaining=retries_remaining,
        )

    token_result = resolve_linkedin_access_token(environ, http_client=http_client, now=now)
    if token_result.status == "action_required":
        return LinkedInPublicationVariantResult(
            campaign_id=campaign_id,
            variant=variant,
            publish_state=PUBLISH_STATE_QUEUED,
            publish_after_utc=publish_after,
            status="failed",
            errors=[token_result.error_code or LINKEDIN_OAUTH_TOKEN_MISSING],
            publication_attempt_count=attempt_count,
            manual_retries_used=retries_used,
            manual_retries_remaining=retries_remaining,
        )

    publish_settings = LinkedInPublicationSettings(
        access_token=token_result.access_token or "",
        member_urn=token_result.member_urn or "",
        publication_enabled=settings.publication_enabled,
        default_safety_delay_minutes=settings.default_safety_delay_minutes,
        api_version=settings.api_version,
    )

    commentary = build_commentary(variant_text=artifact_text, blog_url=blog_url)
    api_result = create_member_text_post(
        publish_settings,
        commentary=commentary,
        client=http_client,
    )

    working = deepcopy(campaign)
    metadata_map = _get_variant_metadata_map(working)
    updated_entry = dict(metadata_map[variant])

    # US-022: exactly one immutable attempt entry per real LinkedIn API call,
    # appended before replacing the latest `linkedin_publication` view.
    attempts = _attempts_for_append(updated_entry)
    attempt_number = len(attempts) + 1
    real_count, real_used, real_remaining = _retry_counters(attempt_number)
    content_hash = updated_entry.get("derivative_content_sha256")

    if api_result.error_code:
        failed_at = utc_now_iso()
        updated_entry["publish_state"] = PUBLISH_STATE_FAILED
        updated_entry["linkedin_publication"] = {
            "last_error_code": api_result.error_code,
            "last_failed_at": failed_at,
            "retryable": api_result.retryable,
            "http_status": api_result.http_status,
        }
        attempts.append(
            _build_failed_attempt_entry(
                attempt_number=attempt_number,
                attempted_at=failed_at,
                derivative_content_sha256=content_hash,
                last_error_code=api_result.error_code,
                last_failed_at=failed_at,
                retryable=api_result.retryable,
                http_status=api_result.http_status,
            )
        )
        updated_entry["linkedin_publication_attempts"] = attempts
        metadata_map[variant] = updated_entry
        working["variants"] = list(metadata_map.values())
        write_result = write_campaign_metadata(base_path, campaign_id, working)
        return LinkedInPublicationVariantResult(
            campaign_id=campaign_id,
            variant=variant,
            publish_state=PUBLISH_STATE_FAILED if write_result.written else PUBLISH_STATE_QUEUED,
            status="failed",
            errors=[api_result.error_code]
            + (
                [LINKEDIN_PUBLISH_METADATA_WRITE_FAILED]
                if not write_result.written
                else []
            ),
            publication_attempt_count=real_count,
            manual_retries_used=real_used,
            manual_retries_remaining=real_remaining,
        )

    published_at = utc_now_iso()
    updated_entry["publish_state"] = PUBLISH_STATE_PUBLISHED
    updated_entry["published_at"] = published_at
    updated_entry["linkedin_post_urn"] = api_result.post_urn
    updated_entry["linkedin_publication"] = {
        "provider": "linkedin_rest_posts",
        "post_urn": api_result.post_urn,
        "published_at": published_at,
        "http_status": api_result.http_status,
    }
    assert api_result.post_urn is not None
    attempts.append(
        _build_published_attempt_entry(
            attempt_number=attempt_number,
            attempted_at=published_at,
            derivative_content_sha256=content_hash,
            provider="linkedin_rest_posts",
            post_urn=api_result.post_urn,
            published_at=published_at,
            http_status=api_result.http_status,
        )
    )
    updated_entry["linkedin_publication_attempts"] = attempts
    metadata_map[variant] = updated_entry
    working["variants"] = list(metadata_map.values())

    write_result = write_campaign_metadata(base_path, campaign_id, working)
    if not write_result.written:
        return LinkedInPublicationVariantResult(
            campaign_id=campaign_id,
            variant=variant,
            publish_state=PUBLISH_STATE_QUEUED,
            status="failed",
            errors=[LINKEDIN_PUBLISH_METADATA_WRITE_FAILED],
            publication_attempt_count=real_count,
            manual_retries_used=real_used,
            manual_retries_remaining=real_remaining,
        )

    return LinkedInPublicationVariantResult(
        campaign_id=campaign_id,
        variant=variant,
        publish_state=PUBLISH_STATE_PUBLISHED,
        published_at=published_at,
        linkedin_post_urn=api_result.post_urn,
        status="completed",
        publication_attempt_count=real_count,
        manual_retries_used=real_used,
        manual_retries_remaining=real_remaining,
    )


def _collect_queued_targets(
    base_path: Path,
    *,
    campaign_id: str | None,
    variant: str | None,
) -> list[tuple[str, str]]:
    if campaign_id and variant:
        return [(campaign_id, variant)]
    if campaign_id and not variant:
        campaign = read_campaign_metadata(base_path, campaign_id)
        if campaign is None:
            return []
        return [
            (campaign_id, entry["variant"])
            for entry in campaign.get("variants") or []
            if isinstance(entry, dict)
            and entry.get("variant")
            and entry.get("publish_state") == PUBLISH_STATE_QUEUED
        ]
    targets: list[tuple[str, str]] = []
    for cid in _list_campaign_ids(base_path):
        campaign = read_campaign_metadata(base_path, cid)
        if campaign is None:
            continue
        if campaign.get("flow") != FLOW_A:
            continue
        if campaign.get("state") not in PUBLICATION_ELIGIBLE_CAMPAIGN_STATES:
            continue
        for entry in campaign.get("variants") or []:
            if not isinstance(entry, dict):
                continue
            if entry.get("publish_state") != PUBLISH_STATE_QUEUED:
                continue
            variant_id = entry.get("variant")
            if variant_id:
                targets.append((cid, variant_id))
    return targets


def _collect_pending_targets(
    base_path: Path,
    *,
    campaign_id: str | None,
    variant: str | None,
) -> list[tuple[str, str, dict[str, Any], dict[str, Any]]]:
    campaign_ids = [campaign_id] if campaign_id else _list_campaign_ids(base_path)
    targets: list[tuple[str, str, dict[str, Any], dict[str, Any]]] = []
    for cid in campaign_ids:
        campaign = read_campaign_metadata(base_path, cid)
        if campaign is None:
            continue
        if campaign.get("flow") != FLOW_A:
            continue
        if campaign.get("state") != STATE_DISTRIBUTION_SCHEDULED:
            continue
        for entry in campaign.get("variants") or []:
            if not isinstance(entry, dict):
                continue
            variant_id = entry.get("variant")
            if not isinstance(variant_id, str) or not variant_id:
                continue
            if variant is not None and variant_id != variant:
                continue
            targets.append((cid, variant_id, entry, campaign))
    return targets


def _auto_queue_skip_reason(
    entry: dict[str, Any],
    *,
    publish_now: bool,
    now: datetime,
    sequence_blocked: bool = False,
) -> str | None:
    publish_state = entry.get("publish_state")
    if publish_state == PUBLISH_STATE_CANCELLED:
        return LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_SUPERVISION
    if publish_state != PUBLISH_STATE_PENDING:
        return LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_STATE

    supervision = entry.get("operator_supervision")
    if not isinstance(supervision, dict):
        supervision = {}
    last_action = supervision.get("last_action")
    auto_queue_eligible = supervision.get("auto_queue_eligible")

    scheduled_at = entry.get("scheduled_at_utc")
    schedule_valid = False
    try:
        if isinstance(scheduled_at, str):
            scheduled_due = _parse_utc(scheduled_at) <= now
            schedule_valid = True
        else:
            scheduled_due = False
    except (CampaignLifecycleError, TypeError, ValueError):
        scheduled_due = False

    if last_action == "defer":
        if not scheduled_due:
            return LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_SUPERVISION
    else:
        if auto_queue_eligible is False:
            return LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_SUPERVISION
        if not schedule_valid:
            return LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_NOT_DUE
        if not scheduled_due and not publish_now:
            return LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_NOT_DUE

    # US-020 sequence pre-filter: evaluated last so pre-existing skip reasons
    # (state -> supervision -> not-due) are reported exactly as before.
    if sequence_blocked:
        return LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_SEQUENCE
    return None


def _auto_queue_pending_variants(
    base_path: Path,
    *,
    campaign_id: str | None,
    variant: str | None,
    dry_run: bool,
    publish_now: bool,
    environ: dict[str, str] | None,
    now: datetime,
) -> tuple[list[LinkedInAutoQueueVariantResult], list[tuple[str, str, str | None]]]:
    outcomes: list[LinkedInAutoQueueVariantResult] = []
    planned_targets: list[tuple[str, str, str | None]] = []
    targets = _collect_pending_targets(
        base_path, campaign_id=campaign_id, variant=variant
    )

    for target_campaign_id, target_variant, entry, campaign_document in targets:
        publish_state = str(entry.get("publish_state") or "unknown")
        # An earlier variant queued earlier in this same request was `pending`
        # in the snapshot, so it still counts as awaiting publication here.
        sequence_blocked = _earlier_variant_awaiting_publication(
            campaign_document, target_variant
        )
        skip_reason = _auto_queue_skip_reason(
            entry,
            publish_now=publish_now,
            now=now,
            sequence_blocked=sequence_blocked,
        )
        if skip_reason is not None:
            linkedin_post_urn: str | None = None
            published_at: str | None = None
            if publish_state == PUBLISH_STATE_PUBLISHED:
                stored_urn = entry.get("linkedin_post_urn")
                stored_published_at = entry.get("published_at")
                linkedin_post_urn = (
                    stored_urn if isinstance(stored_urn, str) else None
                )
                published_at = (
                    stored_published_at
                    if isinstance(stored_published_at, str)
                    else None
                )
            outcomes.append(
                LinkedInAutoQueueVariantResult(
                    campaign_id=target_campaign_id,
                    variant=target_variant,
                    publish_state=publish_state,
                    linkedin_post_urn=linkedin_post_urn,
                    published_at=published_at,
                    skipped=True,
                    skip_reason=skip_reason,
                    warnings=[skip_reason],
                )
            )
            continue

        queue_result = queue_linkedin_publication(
            base_path,
            campaign_id=target_campaign_id,
            variant=target_variant,
            dry_run=dry_run,
            environ=environ,
            now=now,
        )
        planned_state = (
            PUBLISH_STATE_QUEUED
            if queue_result.status == "completed"
            else publish_state
        )
        outcomes.append(
            LinkedInAutoQueueVariantResult(
                campaign_id=target_campaign_id,
                variant=target_variant,
                publish_state=planned_state,
                publish_after_utc=queue_result.publish_after_utc,
                status=queue_result.status,
                errors=list(queue_result.errors),
                warnings=list(queue_result.warnings),
                metadata_written=queue_result.metadata_written,
            )
        )
        if queue_result.status == "completed":
            planned_targets.append(
                (
                    target_campaign_id,
                    target_variant,
                    queue_result.publish_after_utc,
                )
            )

    return outcomes, planned_targets


def _planned_dry_run_publish_result(
    *,
    campaign_id: str,
    variant: str,
    publish_after_utc: str | None,
    publish_now: bool,
    now: datetime,
    guard_reason: str | None = None,
) -> LinkedInPublicationVariantResult:
    if not publish_now and publish_after_utc:
        try:
            if _parse_utc(publish_after_utc) > now:
                return LinkedInPublicationVariantResult(
                    campaign_id=campaign_id,
                    variant=variant,
                    publish_state=PUBLISH_STATE_QUEUED,
                    publish_after_utc=publish_after_utc,
                    skipped=True,
                    skip_reason=LINKEDIN_PUBLISH_VARIANT_NOT_DUE,
                )
        except (TypeError, ValueError):
            pass
    if guard_reason is not None:
        return LinkedInPublicationVariantResult(
            campaign_id=campaign_id,
            variant=variant,
            publish_state=PUBLISH_STATE_QUEUED,
            publish_after_utc=publish_after_utc,
            skipped=True,
            skip_reason=guard_reason,
        )
    return LinkedInPublicationVariantResult(
        campaign_id=campaign_id,
        variant=variant,
        publish_state=PUBLISH_STATE_QUEUED,
        publish_after_utc=publish_after_utc,
        warnings=["linkedin_publish_dry_run"],
    )


def publish_linkedin_due_variants(
    base_path: Path,
    *,
    campaign_id: str | None = None,
    variant: str | None = None,
    dry_run: bool = True,
    publish_now: bool = False,
    auto_queue_pending: bool = False,
    environ: dict[str, str] | None = None,
    http_client: HttpClientProtocol | None = None,
    now: datetime | None = None,
) -> LinkedInPublishDueResult:
    """Publish eligible queued variants to LinkedIn when due."""
    settings_load = load_linkedin_publication_settings(environ)
    if settings_load.config_invalid:
        return LinkedInPublishDueResult(
            status="failed",
            dry_run=dry_run,
            publish_now=publish_now,
            auto_queue_pending=auto_queue_pending,
            errors=["linkedin_publish_config_invalid"],
        )

    settings = settings_load.settings
    current = now or datetime.now(timezone.utc)
    auto_queue_results: list[LinkedInAutoQueueVariantResult] = []
    planned_auto_queue_targets: list[tuple[str, str, str | None]] = []

    if auto_queue_pending:
        auto_queue_results, planned_auto_queue_targets = _auto_queue_pending_variants(
            base_path,
            campaign_id=campaign_id,
            variant=variant,
            dry_run=dry_run,
            publish_now=publish_now,
            environ=environ,
            now=current,
        )

    if campaign_id and not variant:
        campaign = read_campaign_metadata(base_path, campaign_id)
        if campaign is None:
            return LinkedInPublishDueResult(
                status="failed",
                dry_run=dry_run,
                publish_now=publish_now,
                auto_queue_pending=auto_queue_pending,
                auto_queue_results=auto_queue_results,
                errors=[LINKEDIN_PUBLISH_CAMPAIGN_NOT_FOUND],
            )

    if auto_queue_pending and campaign_id and variant:
        campaign = read_campaign_metadata(base_path, campaign_id)
        entry = _find_variant_entry(campaign, variant) if campaign else None
        targets = (
            [(campaign_id, variant)]
            if entry
            and entry.get("publish_state")
            in {PUBLISH_STATE_QUEUED, PUBLISH_STATE_PUBLISHED}
            else []
        )
    else:
        targets = _collect_queued_targets(
            base_path, campaign_id=campaign_id, variant=variant
        )
    if campaign_id and variant and not targets:
        campaign = read_campaign_metadata(base_path, campaign_id)
        if campaign is None:
            return LinkedInPublishDueResult(
                status="failed",
                dry_run=dry_run,
                publish_now=publish_now,
                auto_queue_pending=auto_queue_pending,
                auto_queue_results=auto_queue_results,
                errors=[LINKEDIN_PUBLISH_CAMPAIGN_NOT_FOUND],
            )

    if not targets and not (dry_run and planned_auto_queue_targets):
        return LinkedInPublishDueResult(
            status="completed",
            dry_run=dry_run,
            publish_now=publish_now,
            results=[],
            warnings=["linkedin_publish_no_queued_variants"],
            auto_queue_pending=auto_queue_pending,
            auto_queue_results=auto_queue_results,
        )

    results: list[LinkedInPublicationVariantResult] = []
    top_level_errors: list[str] = []

    if dry_run:
        queued_target_keys = set(targets)
        for target_campaign_id, target_variant, publish_after_utc in (
            planned_auto_queue_targets
        ):
            if (target_campaign_id, target_variant) in queued_target_keys:
                continue
            guard_campaign = read_campaign_metadata(base_path, target_campaign_id)
            guard_reason = (
                _publish_guard_block_reason(
                    guard_campaign, target_variant, now=current
                )
                if guard_campaign is not None
                else None
            )
            results.append(
                _planned_dry_run_publish_result(
                    campaign_id=target_campaign_id,
                    variant=target_variant,
                    publish_after_utc=publish_after_utc,
                    publish_now=publish_now,
                    now=current,
                    guard_reason=guard_reason,
                )
            )

    for target_campaign_id, target_variant in targets:
        result = _publish_single_variant(
            base_path,
            campaign_id=target_campaign_id,
            variant=target_variant,
            dry_run=dry_run,
            publish_now=publish_now,
            settings=settings,
            environ=environ,
            http_client=http_client,
            now=current,
        )
        results.append(result)
        if result.status == "failed" and result.errors:
            for code in result.errors:
                if code not in top_level_errors:
                    top_level_errors.append(code)

    publish_evidence = {
        (item.campaign_id, item.variant): item
        for item in results
        if item.publish_state == PUBLISH_STATE_PUBLISHED
        and item.linkedin_post_urn
    }
    for auto_queue_result in auto_queue_results:
        match = publish_evidence.get(
            (auto_queue_result.campaign_id, auto_queue_result.variant)
        )
        if match is None:
            continue
        auto_queue_result.linkedin_post_urn = match.linkedin_post_urn
        auto_queue_result.published_at = match.published_at

    for auto_queue_result in auto_queue_results:
        if auto_queue_result.status != "failed":
            continue
        for code in auto_queue_result.errors:
            if code not in top_level_errors:
                top_level_errors.append(code)

    overall_status = "completed"
    if any(item.status == "failed" for item in results) or any(
        item.status == "failed" for item in auto_queue_results
    ):
        overall_status = "failed"
    elif not results:
        overall_status = "completed"

    return LinkedInPublishDueResult(
        status=overall_status,
        dry_run=dry_run,
        publish_now=publish_now,
        results=results,
        errors=top_level_errors,
        auto_queue_pending=auto_queue_pending,
        auto_queue_results=auto_queue_results,
    )


def cancel_linkedin_publication(
    base_path: Path,
    *,
    campaign_id: str,
    variant: str,
    dry_run: bool = True,
    reason: str | None = None,
    idempotency_key: str | None = None,
) -> LinkedInCancelPublicationResult:
    """Cancel a pending, queued, or failed variant without calling LinkedIn."""
    from silverman_blog_linkedin.linkedin_supervision_flow import (
        SUPERVISION_PHASE_POST_QUEUE,
        SUPERVISION_PHASE_PRE_QUEUE,
        SUPERVISION_PHASE_RECOVERY,
        apply_supervision_cancellation,
    )

    campaign = read_campaign_metadata(base_path, campaign_id)
    eligibility_errors = _validate_campaign_eligibility(campaign)
    if eligibility_errors:
        return LinkedInCancelPublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state") if campaign else None,
            dry_run=dry_run,
            errors=eligibility_errors,
        )
    assert campaign is not None

    entry = _find_variant_entry(campaign, variant)
    if entry is None:
        return LinkedInCancelPublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            dry_run=dry_run,
            errors=[LINKEDIN_PUBLISH_VARIANT_NOT_FOUND],
        )

    publish_state = entry.get("publish_state")
    if publish_state == PUBLISH_STATE_PUBLISHED:
        return LinkedInCancelPublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=dry_run,
            errors=[LINKEDIN_PUBLISH_CANCEL_NOT_ALLOWED],
        )

    if publish_state == PUBLISH_STATE_PENDING:
        cancel_phase = SUPERVISION_PHASE_PRE_QUEUE
    elif publish_state == PUBLISH_STATE_QUEUED:
        cancel_phase = SUPERVISION_PHASE_POST_QUEUE
    elif publish_state == PUBLISH_STATE_FAILED:
        cancel_phase = SUPERVISION_PHASE_RECOVERY
    else:
        return LinkedInCancelPublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=dry_run,
            errors=[LINKEDIN_SUPERVISION_ACTION_NOT_ALLOWED],
        )

    # US-022 failed-state cancellation: validate and lazily normalize legacy
    # evidence before any mutation; fail closed when mandatory US-019
    # evidence is missing or invalid.
    normalized_attempts: list[dict[str, Any]] | None = None
    recovery_classification: str | None = None
    attempt_count: int | None = None
    retries_used: int | None = None
    retries_remaining: int | None = None
    if cancel_phase == SUPERVISION_PHASE_RECOVERY:
        evidence, evidence_error = _validated_failure_evidence(entry)
        attempts, history_error = _normalized_failed_attempt_history(entry)
        if evidence_error or history_error:
            return LinkedInCancelPublicationResult(
                status="failed",
                campaign_id=campaign_id,
                variant=variant,
                state=campaign.get("state"),
                publish_state=publish_state,
                dry_run=dry_run,
                errors=[LINKEDIN_PUBLISH_RECOVERY_EVIDENCE_INVALID],
            )
        assert evidence is not None and attempts is not None
        normalized_attempts = attempts
        recovery_classification = classify_linkedin_recovery(
            evidence["last_error_code"], evidence["http_status"]
        )
        attempt_count, retries_used, retries_remaining = _retry_counters(
            len(attempts)
        )

    if dry_run:
        return LinkedInCancelPublicationResult(
            status="completed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=True,
            phase=cancel_phase,
            metadata_written=False,
            publication_attempt_count=attempt_count,
            manual_retries_used=retries_used,
            manual_retries_remaining=retries_remaining,
            recovery_classification=recovery_classification,
        )

    working = deepcopy(campaign)
    metadata_map = _get_variant_metadata_map(working)
    updated_entry = dict(metadata_map[variant])
    cancelled_at = utc_now_iso()
    existing_supervision = updated_entry.get("operator_supervision")
    if isinstance(existing_supervision, dict):
        existing_supervision = deepcopy(existing_supervision)
    else:
        existing_supervision = None

    updated_entry, cancel_error = apply_supervision_cancellation(
        updated_entry,
        phase=cancel_phase,
        cancelled_at=cancelled_at,
        reason=reason,
        idempotency_key=idempotency_key,
        existing_supervision=existing_supervision,
    )
    if cancel_error and cancel_error != "replay":
        return LinkedInCancelPublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=False,
            errors=[cancel_error],
        )

    is_replay = cancel_error == "replay"
    if not is_replay:
        updated_entry["publish_state"] = PUBLISH_STATE_CANCELLED
        if cancel_phase == SUPERVISION_PHASE_POST_QUEUE:
            linkedin_publication = updated_entry.get("linkedin_publication")
            if not isinstance(linkedin_publication, dict):
                linkedin_publication = {}
            else:
                linkedin_publication = dict(linkedin_publication)
            linkedin_publication["cancelled_at"] = cancelled_at
            updated_entry["linkedin_publication"] = linkedin_publication
        if cancel_phase == SUPERVISION_PHASE_RECOVERY:
            # Preserve latest failure evidence and attempt history untouched;
            # persist normalized legacy history and the cancellation event.
            assert normalized_attempts is not None
            assert recovery_classification is not None
            updated_entry["linkedin_publication_attempts"] = normalized_attempts
            _append_recovery_event(
                updated_entry,
                action=RECOVERY_ACTION_RECOVERY_CANCELLED,
                recorded_at=cancelled_at,
                attempt_number=len(normalized_attempts),
                classification=recovery_classification,
                details={"reason": reason},
            )

    metadata_map[variant] = updated_entry
    working["variants"] = list(metadata_map.values())

    if is_replay:
        return LinkedInCancelPublicationResult(
            status="completed",
            campaign_id=campaign_id,
            variant=variant,
            state=working.get("state"),
            publish_state=updated_entry.get("publish_state"),
            dry_run=False,
            phase=cancel_phase,
            operator_supervision=updated_entry.get("operator_supervision"),
            metadata_written=False,
            publication_attempt_count=attempt_count,
            manual_retries_used=retries_used,
            manual_retries_remaining=retries_remaining,
            recovery_classification=recovery_classification,
        )

    write_result = write_campaign_metadata(base_path, campaign_id, working)
    if not write_result.written:
        return LinkedInCancelPublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=working.get("state"),
            publish_state=publish_state,
            dry_run=False,
            errors=[LINKEDIN_PUBLISH_METADATA_WRITE_FAILED],
            metadata_written=False,
            publication_attempt_count=attempt_count,
            manual_retries_used=retries_used,
            manual_retries_remaining=retries_remaining,
            recovery_classification=recovery_classification,
        )

    return LinkedInCancelPublicationResult(
        status="completed",
        campaign_id=campaign_id,
        variant=variant,
        state=working.get("state"),
        publish_state=PUBLISH_STATE_CANCELLED,
        dry_run=False,
        phase=cancel_phase,
        operator_supervision=updated_entry.get("operator_supervision"),
        metadata_written=True,
        publication_attempt_count=attempt_count,
        manual_retries_used=retries_used,
        manual_retries_remaining=retries_remaining,
        recovery_classification=recovery_classification,
    )
