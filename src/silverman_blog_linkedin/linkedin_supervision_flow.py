"""Flow A LinkedIn variant operator supervision (edit, defer) during pending window."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.campaign_lifecycle import (
    normalize_scheduled_at_utc,
    read_campaign_metadata,
    write_campaign_metadata,
)
from silverman_blog_linkedin.linkedin_publication_flow import (
    LINKEDIN_PUBLISH_ARTIFACT_HASH_CHANGED,
    LINKEDIN_PUBLISH_ARTIFACT_MISSING,
    LINKEDIN_PUBLISH_CONTENT_INVALID,
    LINKEDIN_PUBLISH_METADATA_WRITE_FAILED,
    LINKEDIN_PUBLISH_RECOVERY_EVIDENCE_INVALID,
    LINKEDIN_PUBLISH_VARIANT_NOT_FOUND,
    PUBLISH_STATE_FAILED,
    PUBLISH_STATE_PENDING,
    RECOVERY_ACTION_CONTENT_CORRECTED,
    RECOVERY_CLASS_CONTENT_INVALID,
    _append_recovery_event,
    _find_variant_entry,
    _get_variant_metadata_map,
    _normalized_failed_attempt_history,
    _parse_utc,
    _validate_campaign_eligibility,
    _validated_failure_evidence,
    _verify_artifact,
    classify_linkedin_recovery,
)
from silverman_blog_linkedin.run_metadata import utc_now_iso

LINKEDIN_SUPERVISION_VARIANT_NOT_PENDING = "linkedin_supervision_variant_not_pending"
LINKEDIN_SUPERVISION_ACTION_NOT_ALLOWED = "linkedin_supervision_action_not_allowed"
LINKEDIN_SUPERVISION_DEFER_TIME_INVALID = "linkedin_supervision_defer_time_invalid"
LINKEDIN_SUPERVISION_EDIT_UNCHANGED = "linkedin_supervision_edit_unchanged"
LINKEDIN_SUPERVISION_IDEMPOTENCY_CONFLICT = "linkedin_supervision_idempotency_conflict"

SUPERVISION_ACTION_EDIT = "edit"
SUPERVISION_ACTION_DEFER = "defer"
SUPERVISION_ACTION_CANCEL = "cancel"
SUPERVISION_PHASE_PRE_QUEUE = "pre_queue"
SUPERVISION_PHASE_POST_QUEUE = "post_queue"
# US-022 failed-state recovery actions (correction/cancel on `failed`).
SUPERVISION_PHASE_RECOVERY = "recovery"
SUPERVISION_ACTOR_OPERATOR = "operator"


@dataclass
class LinkedInSupervisionResult:
    status: str
    campaign_id: str | None = None
    variant: str | None = None
    state: str | None = None
    publish_state: str | None = None
    dry_run: bool = True
    phase: str | None = None
    scheduled_at_utc: str | None = None
    derivative_content_sha256: str | None = None
    operator_supervision: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata_written: bool = False
    artifact_written: bool = False
    recovery_classification: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_draft_content(content: str) -> str:
    if not content or not content.strip():
        return ""
    normalized = content.replace("\r\n", "\n")
    if not normalized.endswith("\n"):
        normalized += "\n"
    return normalized


def _content_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        tmp_path.write_text(content, encoding="utf-8")
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def _get_or_init_operator_supervision(entry: dict[str, Any]) -> dict[str, Any]:
    supervision = entry.get("operator_supervision")
    if isinstance(supervision, dict):
        return deepcopy(supervision)
    return {}


def _payload_fingerprint(action: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps({"action": action, **payload}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _check_idempotency(
    supervision: dict[str, Any],
    *,
    action: str,
    idempotency_key: str | None,
    payload: dict[str, Any],
) -> tuple[str | None, list[str]]:
    """Return replay status: None (proceed), 'replay' (idempotent success), or errors."""
    if not idempotency_key:
        return None, []

    proofs = supervision.get("idempotency_proofs")
    if not isinstance(proofs, dict):
        proofs = {}

    fingerprint = _payload_fingerprint(action, payload)
    existing = proofs.get(idempotency_key)
    if existing is None:
        return None, []

    if not isinstance(existing, dict):
        return None, [LINKEDIN_SUPERVISION_IDEMPOTENCY_CONFLICT]

    if (
        existing.get("action") == action
        and existing.get("payload_fingerprint") == fingerprint
    ):
        return "replay", []

    return None, [LINKEDIN_SUPERVISION_IDEMPOTENCY_CONFLICT]


def _record_idempotency_proof(
    supervision: dict[str, Any],
    *,
    action: str,
    idempotency_key: str | None,
    payload: dict[str, Any],
    completed_at: str,
) -> None:
    if not idempotency_key:
        return
    proofs = supervision.get("idempotency_proofs")
    if not isinstance(proofs, dict):
        proofs = {}
    proofs[idempotency_key] = {
        "action": action,
        "payload_fingerprint": _payload_fingerprint(action, payload),
        "completed_at_utc": completed_at,
    }
    supervision["idempotency_proofs"] = proofs


def _validate_pending_supervision(
    entry: dict[str, Any],
) -> list[str]:
    publish_state = entry.get("publish_state")
    if publish_state != PUBLISH_STATE_PENDING:
        return [LINKEDIN_SUPERVISION_VARIANT_NOT_PENDING]
    return []


def _supervision_eligibility(
    base_path: Path,
    *,
    campaign_id: str,
    variant: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[str]]:
    campaign = read_campaign_metadata(base_path, campaign_id)
    eligibility_errors = _validate_campaign_eligibility(campaign)
    if eligibility_errors:
        return campaign, None, eligibility_errors
    assert campaign is not None

    entry = _find_variant_entry(campaign, variant)
    if entry is None:
        return campaign, None, [LINKEDIN_PUBLISH_VARIANT_NOT_FOUND]
    return campaign, entry, []


def correct_linkedin_variant(
    base_path: Path,
    *,
    campaign_id: str,
    variant: str,
    draft_content: str,
    dry_run: bool = True,
    reason: str | None = None,
    idempotency_key: str | None = None,
    auto_queue_eligible: bool | None = None,
) -> LinkedInSupervisionResult:
    """Atomically update a pending or content-rejected failed variant draft.

    Pending behavior is unchanged. A `failed` variant is eligible only when
    its latest US-019 evidence classifies as non-recoverable as-is with
    `last_error_code=linkedin_publish_content_invalid` (US-022); the variant
    stays `failed` and is never made auto-queue eligible.
    """
    campaign, entry, errors = _supervision_eligibility(
        base_path, campaign_id=campaign_id, variant=variant
    )
    if errors:
        return LinkedInSupervisionResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state") if campaign else None,
            dry_run=dry_run,
            errors=errors,
        )
    assert campaign is not None and entry is not None

    publish_state = entry.get("publish_state")
    is_failed_correction = publish_state == PUBLISH_STATE_FAILED
    normalized_attempts: list[dict[str, Any]] | None = None
    recovery_classification: str | None = None
    if is_failed_correction:
        evidence, evidence_error = _validated_failure_evidence(entry)
        attempts, history_error = _normalized_failed_attempt_history(entry)
        if evidence_error or history_error:
            return LinkedInSupervisionResult(
                status="failed",
                campaign_id=campaign_id,
                variant=variant,
                state=campaign.get("state"),
                publish_state=publish_state,
                dry_run=dry_run,
                errors=[LINKEDIN_PUBLISH_RECOVERY_EVIDENCE_INVALID],
            )
        assert evidence is not None and attempts is not None
        classification = classify_linkedin_recovery(
            evidence["last_error_code"], evidence["http_status"]
        )
        if (
            classification != RECOVERY_CLASS_CONTENT_INVALID
            or evidence["last_error_code"] != LINKEDIN_PUBLISH_CONTENT_INVALID
        ):
            return LinkedInSupervisionResult(
                status="failed",
                campaign_id=campaign_id,
                variant=variant,
                state=campaign.get("state"),
                publish_state=publish_state,
                dry_run=dry_run,
                errors=[LINKEDIN_SUPERVISION_ACTION_NOT_ALLOWED],
                recovery_classification=classification,
            )
        normalized_attempts = attempts
        recovery_classification = classification
    else:
        pending_errors = _validate_pending_supervision(entry)
        if pending_errors:
            return LinkedInSupervisionResult(
                status="failed",
                campaign_id=campaign_id,
                variant=variant,
                state=campaign.get("state"),
                publish_state=publish_state,
                dry_run=dry_run,
                errors=pending_errors,
            )

    supervision_phase = (
        SUPERVISION_PHASE_RECOVERY
        if is_failed_correction
        else SUPERVISION_PHASE_PRE_QUEUE
    )

    normalized_content = _normalize_draft_content(draft_content)
    if not normalized_content:
        return LinkedInSupervisionResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=dry_run,
            errors=[LINKEDIN_SUPERVISION_EDIT_UNCHANGED],
        )

    artifact_relative = entry.get("artifact_relative_path")
    stored_hash = entry.get("derivative_content_sha256")
    if not artifact_relative or not stored_hash:
        return LinkedInSupervisionResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=dry_run,
            errors=[LINKEDIN_PUBLISH_ARTIFACT_MISSING],
        )

    _, artifact_error = _verify_artifact(base_path, entry)
    if artifact_error:
        return LinkedInSupervisionResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=dry_run,
            errors=[artifact_error],
        )

    new_hash = _content_sha256(normalized_content)
    if new_hash == stored_hash:
        return LinkedInSupervisionResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=dry_run,
            errors=[LINKEDIN_SUPERVISION_EDIT_UNCHANGED],
        )

    payload = {"draft_content": normalized_content, "reason": reason}
    supervision = _get_or_init_operator_supervision(entry)
    replay_status, idempotency_errors = _check_idempotency(
        supervision,
        action=SUPERVISION_ACTION_EDIT,
        idempotency_key=idempotency_key,
        payload=payload,
    )
    if idempotency_errors:
        return LinkedInSupervisionResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=dry_run,
            errors=idempotency_errors,
        )
    if replay_status == "replay":
        return LinkedInSupervisionResult(
            status="completed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=False,
            phase=supervision_phase,
            derivative_content_sha256=new_hash,
            operator_supervision=supervision,
            metadata_written=False,
            artifact_written=False,
            recovery_classification=recovery_classification,
        )

    if dry_run:
        return LinkedInSupervisionResult(
            status="completed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=True,
            phase=supervision_phase,
            derivative_content_sha256=new_hash,
            metadata_written=False,
            artifact_written=False,
            recovery_classification=recovery_classification,
        )

    artifact_path = base_path / artifact_relative
    _atomic_write_text(artifact_path, normalized_content)
    on_disk_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    if on_disk_hash != new_hash:
        return LinkedInSupervisionResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=False,
            errors=[LINKEDIN_PUBLISH_ARTIFACT_HASH_CHANGED],
            artifact_written=False,
        )

    edited_at = utc_now_iso()
    edit_record = {
        "edited_at_utc": edited_at,
        "previous_content_sha256": stored_hash,
        "new_content_sha256": new_hash,
    }
    if reason:
        edit_record["reason"] = reason

    history = supervision.get("edit_history")
    if not isinstance(history, list):
        history = []
    history.append(edit_record)
    supervision["edit_history"] = history
    supervision["last_action"] = SUPERVISION_ACTION_EDIT
    supervision["last_action_at_utc"] = edited_at
    supervision["phase"] = supervision_phase
    supervision["actor"] = SUPERVISION_ACTOR_OPERATOR
    if reason:
        supervision["reason"] = reason
    if is_failed_correction:
        # A corrected failed variant is never auto-queue eligible; explicit
        # manual re-queue remains the only path to another attempt.
        supervision["auto_queue_eligible"] = False
    else:
        supervision["auto_queue_eligible"] = (
            auto_queue_eligible if auto_queue_eligible is not None else True
        )
    _record_idempotency_proof(
        supervision,
        action=SUPERVISION_ACTION_EDIT,
        idempotency_key=idempotency_key,
        payload=payload,
        completed_at=edited_at,
    )

    working = deepcopy(campaign)
    metadata_map = _get_variant_metadata_map(working)
    updated_entry = dict(metadata_map[variant])
    updated_entry["derivative_content_sha256"] = new_hash
    updated_entry["operator_supervision"] = supervision
    if is_failed_correction:
        assert normalized_attempts is not None
        assert recovery_classification is not None
        updated_entry["linkedin_publication_attempts"] = normalized_attempts
        _append_recovery_event(
            updated_entry,
            action=RECOVERY_ACTION_CONTENT_CORRECTED,
            recorded_at=edited_at,
            attempt_number=len(normalized_attempts),
            classification=recovery_classification,
            details={
                "previous_content_sha256": stored_hash,
                "new_content_sha256": new_hash,
            },
        )
    metadata_map[variant] = updated_entry
    working["variants"] = list(metadata_map.values())

    write_result = write_campaign_metadata(base_path, campaign_id, working)
    if not write_result.written:
        return LinkedInSupervisionResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=working.get("state"),
            publish_state=publish_state,
            dry_run=False,
            errors=[LINKEDIN_PUBLISH_METADATA_WRITE_FAILED],
            metadata_written=False,
            artifact_written=True,
            recovery_classification=recovery_classification,
        )

    return LinkedInSupervisionResult(
        status="completed",
        campaign_id=campaign_id,
        variant=variant,
        state=working.get("state"),
        publish_state=publish_state,
        dry_run=False,
        phase=supervision_phase,
        derivative_content_sha256=new_hash,
        operator_supervision=supervision,
        metadata_written=True,
        artifact_written=True,
        recovery_classification=recovery_classification,
    )


def defer_linkedin_variant(
    base_path: Path,
    *,
    campaign_id: str,
    variant: str,
    new_scheduled_at_utc: str,
    dry_run: bool = True,
    reason: str | None = None,
    idempotency_key: str | None = None,
    now: datetime | None = None,
) -> LinkedInSupervisionResult:
    """Reschedule a pending variant with deferral audit history."""
    campaign, entry, errors = _supervision_eligibility(
        base_path, campaign_id=campaign_id, variant=variant
    )
    if errors:
        return LinkedInSupervisionResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state") if campaign else None,
            dry_run=dry_run,
            errors=errors,
        )
    assert campaign is not None and entry is not None

    publish_state = entry.get("publish_state")
    pending_errors = _validate_pending_supervision(entry)
    if pending_errors:
        return LinkedInSupervisionResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=dry_run,
            errors=pending_errors,
        )

    try:
        normalized_new = normalize_scheduled_at_utc(new_scheduled_at_utc)
        new_dt = _parse_utc(normalized_new)
    except ValueError:
        return LinkedInSupervisionResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=dry_run,
            errors=[LINKEDIN_SUPERVISION_DEFER_TIME_INVALID],
        )

    current = now or datetime.now(timezone.utc)
    if new_dt <= current:
        return LinkedInSupervisionResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=dry_run,
            errors=[LINKEDIN_SUPERVISION_DEFER_TIME_INVALID],
        )

    previous_scheduled = entry.get("scheduled_at_utc")
    if not isinstance(previous_scheduled, str) or not previous_scheduled.strip():
        return LinkedInSupervisionResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=dry_run,
            errors=[LINKEDIN_SUPERVISION_ACTION_NOT_ALLOWED],
        )

    payload = {
        "new_scheduled_at_utc": normalized_new,
        "reason": reason,
    }
    supervision = _get_or_init_operator_supervision(entry)
    replay_status, idempotency_errors = _check_idempotency(
        supervision,
        action=SUPERVISION_ACTION_DEFER,
        idempotency_key=idempotency_key,
        payload=payload,
    )
    if idempotency_errors:
        return LinkedInSupervisionResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=dry_run,
            errors=idempotency_errors,
        )
    if replay_status == "replay":
        return LinkedInSupervisionResult(
            status="completed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=False,
            phase=SUPERVISION_PHASE_PRE_QUEUE,
            scheduled_at_utc=normalized_new,
            operator_supervision=supervision,
            metadata_written=False,
        )

    if dry_run:
        return LinkedInSupervisionResult(
            status="completed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=True,
            phase=SUPERVISION_PHASE_PRE_QUEUE,
            scheduled_at_utc=normalized_new,
            metadata_written=False,
        )

    deferred_at = utc_now_iso()
    defer_record = {
        "deferred_at_utc": deferred_at,
        "previous_scheduled_at_utc": normalize_scheduled_at_utc(previous_scheduled),
        "new_scheduled_at_utc": normalized_new,
    }
    if reason:
        defer_record["reason"] = reason

    history = supervision.get("deferral_history")
    if not isinstance(history, list):
        history = []
    history.append(defer_record)
    supervision["deferral_history"] = history
    supervision["last_action"] = SUPERVISION_ACTION_DEFER
    supervision["last_action_at_utc"] = deferred_at
    supervision["phase"] = SUPERVISION_PHASE_PRE_QUEUE
    supervision["actor"] = SUPERVISION_ACTOR_OPERATOR
    if reason:
        supervision["reason"] = reason
    supervision["auto_queue_eligible"] = False
    _record_idempotency_proof(
        supervision,
        action=SUPERVISION_ACTION_DEFER,
        idempotency_key=idempotency_key,
        payload=payload,
        completed_at=deferred_at,
    )

    working = deepcopy(campaign)
    metadata_map = _get_variant_metadata_map(working)
    updated_entry = dict(metadata_map[variant])
    updated_entry["scheduled_at_utc"] = normalized_new
    updated_entry["operator_supervision"] = supervision
    metadata_map[variant] = updated_entry
    working["variants"] = list(metadata_map.values())

    write_result = write_campaign_metadata(base_path, campaign_id, working)
    if not write_result.written:
        return LinkedInSupervisionResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=working.get("state"),
            publish_state=publish_state,
            dry_run=False,
            errors=[LINKEDIN_PUBLISH_METADATA_WRITE_FAILED],
            metadata_written=False,
        )

    return LinkedInSupervisionResult(
        status="completed",
        campaign_id=campaign_id,
        variant=variant,
        state=working.get("state"),
        publish_state=publish_state,
        dry_run=False,
        phase=SUPERVISION_PHASE_PRE_QUEUE,
        scheduled_at_utc=normalized_new,
        operator_supervision=supervision,
        metadata_written=True,
    )


def apply_supervision_cancellation(
    updated_entry: dict[str, Any],
    *,
    phase: str,
    cancelled_at: str,
    reason: str | None = None,
    idempotency_key: str | None = None,
    existing_supervision: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], str | None]:
    """Apply operator_supervision cancellation fields; return (entry, replay_or_error)."""
    supervision = (
        deepcopy(existing_supervision)
        if existing_supervision is not None
        else _get_or_init_operator_supervision(updated_entry)
    )

    payload = {"phase": phase, "reason": reason}
    replay_status, idempotency_errors = _check_idempotency(
        supervision,
        action=SUPERVISION_ACTION_CANCEL,
        idempotency_key=idempotency_key,
        payload=payload,
    )
    if idempotency_errors:
        return updated_entry, idempotency_errors[0]
    if replay_status == "replay":
        updated_entry["operator_supervision"] = supervision
        return updated_entry, "replay"

    cancellation = {
        "cancelled_at_utc": cancelled_at,
        "phase": phase,
    }
    if reason:
        cancellation["reason"] = reason

    supervision["cancellation"] = cancellation
    supervision["last_action"] = SUPERVISION_ACTION_CANCEL
    supervision["last_action_at_utc"] = cancelled_at
    supervision["phase"] = phase
    supervision["actor"] = SUPERVISION_ACTOR_OPERATOR
    if reason:
        supervision["reason"] = reason
    supervision["auto_queue_eligible"] = False
    _record_idempotency_proof(
        supervision,
        action=SUPERVISION_ACTION_CANCEL,
        idempotency_key=idempotency_key,
        payload=payload,
        completed_at=cancelled_at,
    )
    updated_entry["operator_supervision"] = supervision
    return updated_entry, None
