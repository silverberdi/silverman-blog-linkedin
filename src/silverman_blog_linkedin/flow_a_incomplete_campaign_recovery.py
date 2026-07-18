"""Flow A incomplete-campaign recovery: inspect, resume, and allowlisted repair."""

from __future__ import annotations

import hashlib
import json
import shutil
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from silverman_blog_linkedin.blog_publish_flow import publish_blog_post
from silverman_blog_linkedin.campaign_lifecycle import (
    CANONICAL_VARIANT_IDS,
    CampaignLifecycleError,
    EXECUTION_STATE_IDLE,
    EXECUTION_STATE_PROCESSING,
    EXECUTION_STATE_STALE,
    FLOW_A,
    PHYSICAL_MOVE_STATE_COMPLETED,
    PHYSICAL_MOVE_STATE_PARTIAL,
    RECOVERY_CLASSIFICATIONS,
    RECOVERY_MANUAL_INTERVENTION_REQUIRED,
    RECOVERY_NO_ACTION,
    RECOVERY_REPAIR_REQUIRED,
    RECOVERY_REQUEUE_REQUIRED,
    RECOVERY_RETRYABLE,
    SOURCE_LOCATION_ERROR,
    SOURCE_LOCATION_PROCESSED,
    SOURCE_LOCATION_QUEUED,
    SOURCE_LOCATION_READY,
    STATE_BLOG_PUBLISHED,
    STATE_DERIVATIVES_GENERATED,
    STATE_DISTRIBUTION_SCHEDULED,
    STATE_FLOW_A_COMPLETE,
    STATE_READY,
    STATE_VALIDATED,
    STATE_VALIDATION_FAILED,
    normalize_source_file_status,
    read_campaign_metadata,
    resolve_campaign_source_paths,
    validate_campaign_id,
    write_campaign_metadata,
)
from silverman_blog_linkedin.run_metadata import utc_now_iso
from silverman_blog_linkedin.file_reader import normalize_relative_path
from silverman_blog_linkedin.flow_a_operational_queue import (
    claim_flow_a_execution,
    detect_stale_flow_a_execution,
    is_execution_stale,
    record_flow_a_progress,
    release_flow_a_execution,
)
from silverman_blog_linkedin.flow_a_source_lifecycle import complete_flow_a_source_lifecycle
from silverman_blog_linkedin.linkedin_distribution_schedule import (
    schedule_linkedin_distribution,
)
from silverman_blog_linkedin.linkedin_package_flow import generate_linkedin_package

# --- Reason codes ---

REASON_CAMPAIGN_NOT_FOUND = "flow_a_recovery_campaign_not_found"
REASON_NOT_FLOW_A = "flow_a_recovery_not_flow_a"
REASON_INVALID_CAMPAIGN_ID = "flow_a_recovery_invalid_campaign_id"
REASON_MALFORMED_CAMPAIGN = "flow_a_recovery_malformed_campaign"
REASON_EVIDENCE_AMBIGUOUS = "flow_a_recovery_evidence_ambiguous"
REASON_ACTIVE_CLAIM = "flow_a_recovery_active_non_stale_claim"
REASON_REQUEUE_REQUIRED = "flow_a_recovery_requeue_required"
REASON_ALREADY_COMPLETE = "flow_a_recovery_already_complete"
REASON_REPAIR_REFUSED = "flow_a_recovery_repair_refused"
REASON_REPAIR_AMBIGUOUS_LOCATION = "flow_a_recovery_repair_ambiguous_location"
REASON_REPAIR_NO_MISMATCH = "flow_a_recovery_repair_no_location_mismatch"
REASON_REPAIR_INVENT_SUCCESS = "flow_a_recovery_repair_invent_success_refused"
REASON_REPAIR_UNSAFE_COMPLETE = "flow_a_recovery_repair_unsafe_flow_a_complete"
REASON_REPAIR_NOT_STALE = "flow_a_recovery_repair_not_stale"
REASON_REPAIR_NOT_PARTIAL = "flow_a_recovery_repair_not_partial"
REASON_REPAIR_PARTIAL_UNSAFE = "flow_a_recovery_repair_partial_unsafe"
REASON_STAGE_FAILED = "flow_a_recovery_stage_failed"
REASON_CLAIM_FAILED = "flow_a_recovery_claim_failed"
REASON_OK = "flow_a_recovery_ok"
REASON_NOOP = "flow_a_recovery_noop"
REASON_PARTIAL = "flow_a_recovery_partial"
REASON_DRY_RUN = "flow_a_recovery_dry_run"

# Durable milestones for last_valid_stage (pipeline order).
DURABLE_MILESTONES: tuple[str, ...] = (
    STATE_READY,
    STATE_VALIDATED,
    STATE_BLOG_PUBLISHED,
    STATE_DERIVATIVES_GENERATED,
    STATE_DISTRIBUTION_SCHEDULED,
    STATE_FLOW_A_COMPLETE,
)

MILESTONE_RANK = {name: index for index, name in enumerate(DURABLE_MILESTONES)}

BLOG_PUBLISH_SUCCESS_STATUSES = frozenset(
    {"published", "already_published", "reconciled", "completed"}
)

REPAIR_ACTIONS = frozenset(
    {
        "sync_location_from_filesystem",
        "clear_stale_execution_claim",
        "complete_partial_source_move",
    }
)

WORKER_STAGES: tuple[str, ...] = (
    "publish",
    "package",
    "schedule",
    "source_lifecycle",
)

STAGE_TO_MILESTONE = {
    "publish": STATE_BLOG_PUBLISHED,
    "package": STATE_DERIVATIVES_GENERATED,
    "schedule": STATE_DISTRIBUTION_SCHEDULED,
    "source_lifecycle": STATE_FLOW_A_COMPLETE,
}

MILESTONE_TO_NEXT_STAGE = {
    STATE_READY: "publish",
    STATE_VALIDATED: "publish",
    STATE_BLOG_PUBLISHED: "package",
    STATE_DERIVATIVES_GENERATED: "schedule",
    STATE_DISTRIBUTION_SCHEDULED: "source_lifecycle",
    STATE_FLOW_A_COMPLETE: None,
}

STOP_AFTER_STAGE_VALUES = frozenset(DURABLE_MILESTONES)

_CLASSIFICATION_SEVERITY = {
    RECOVERY_NO_ACTION: 0,
    RECOVERY_RETRYABLE: 1,
    RECOVERY_REPAIR_REQUIRED: 2,
    RECOVERY_REQUEUE_REQUIRED: 3,
    RECOVERY_MANUAL_INTERVENTION_REQUIRED: 4,
}

Outcome = Literal["ok", "blocked", "failed", "noop", "partial"]


@dataclass
class StagePlanOrResult:
    stage: str
    intent: str
    status: str | None = None
    reason_code: str | None = None
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return {key: value for key, value in payload.items() if value is not None}


@dataclass
class IncompleteCampaignRecoveryResult:
    campaign_id: str
    outcome: Outcome
    reason_code: str
    summary: str
    recovery_classification: str
    last_valid_stage: str | None = None
    next_stage: str | None = None
    dry_run: bool = False
    block_reason: str | None = None
    stages: list[StagePlanOrResult] = field(default_factory=list)
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    repair_action: str | None = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "campaign_id": self.campaign_id,
            "outcome": self.outcome,
            "reason_code": self.reason_code,
            "summary": self.summary,
            "recovery_classification": self.recovery_classification,
            "last_valid_stage": self.last_valid_stage,
            "next_stage": self.next_stage,
        }
        if self.dry_run:
            payload["dry_run"] = True
        if self.block_reason is not None:
            payload["block_reason"] = self.block_reason
        if self.stages:
            payload["stages"] = [item.to_dict() for item in self.stages]
        if self.before is not None:
            payload["before"] = self.before
        if self.after is not None:
            payload["after"] = self.after
        if self.repair_action is not None:
            payload["repair_action"] = self.repair_action
        if self.errors:
            payload["errors"] = list(self.errors)
        return payload


def _more_severe_classification(current: str, proposed: str) -> str:
    current_rank = _CLASSIFICATION_SEVERITY.get(current, 0)
    proposed_rank = _CLASSIFICATION_SEVERITY.get(proposed, 0)
    return proposed if proposed_rank >= current_rank else current


def _safe_source_status_summary(campaign: dict[str, Any]) -> dict[str, Any]:
    status = normalize_source_file_status(campaign.get("source_file_status"))
    return {
        "location": status.get("location"),
        "execution_state": status.get("execution_state"),
        "recovery_classification": status.get("recovery_classification"),
        "physical_move_state": status.get("physical_move_state"),
        "last_progress_at": status.get("last_progress_at"),
    }


def _effective_classification(campaign: dict[str, Any]) -> str:
    status = normalize_source_file_status(campaign.get("source_file_status"))
    value = status.get("recovery_classification")
    if isinstance(value, str) and value in RECOVERY_CLASSIFICATIONS:
        return value
    return RECOVERY_NO_ACTION


class CampaignLoadError(Exception):
    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.message = message


def load_flow_a_campaign_for_recovery(
    base_path: Path, campaign_id: str
) -> dict[str, Any]:
    """Load a confined Flow A campaign document or raise CampaignLoadError."""
    stripped = (campaign_id or "").strip()
    if not stripped:
        raise CampaignLoadError(REASON_INVALID_CAMPAIGN_ID, "campaign_id must not be empty")
    try:
        validate_campaign_id(stripped)
    except CampaignLifecycleError as exc:
        raise CampaignLoadError(REASON_INVALID_CAMPAIGN_ID, str(exc)) from exc

    relative = f"metadata/campaigns/{stripped}.json"
    if ".." in relative or relative.startswith("/"):
        raise CampaignLoadError(REASON_INVALID_CAMPAIGN_ID, "campaign_id path escape")

    metadata_path = (base_path / relative).resolve()
    campaigns_root = (base_path / "metadata" / "campaigns").resolve()
    try:
        metadata_path.relative_to(campaigns_root)
    except ValueError as exc:
        raise CampaignLoadError(REASON_INVALID_CAMPAIGN_ID, "campaign_id path escape") from exc

    if not metadata_path.is_file():
        raise CampaignLoadError(
            REASON_CAMPAIGN_NOT_FOUND,
            f"campaign {stripped!r} not found",
        )

    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CampaignLoadError(
            REASON_MALFORMED_CAMPAIGN,
            f"campaign {stripped!r} is malformed",
        ) from exc

    if not isinstance(payload, dict):
        raise CampaignLoadError(
            REASON_MALFORMED_CAMPAIGN,
            f"campaign {stripped!r} is malformed",
        )

    if payload.get("campaign_id") not in (None, stripped):
        raise CampaignLoadError(
            REASON_MALFORMED_CAMPAIGN,
            "campaign_id does not match filename",
        )

    flow = payload.get("flow")
    if flow != FLOW_A:
        raise CampaignLoadError(
            REASON_NOT_FLOW_A,
            f"campaign flow {flow!r} is not flow_a",
        )

    return payload


@dataclass(frozen=True)
class LastValidStageDerivation:
    last_valid_stage: str | None
    ambiguous: bool
    ambiguity_detail: str | None = None
    confirmed_milestones: tuple[str, ...] = ()


def _history_durable_states(campaign: dict[str, Any]) -> set[str]:
    history = campaign.get("state_history")
    if not isinstance(history, list):
        return set()
    found: set[str] = set()
    for entry in history:
        if not isinstance(entry, dict):
            continue
        to_state = entry.get("to_state")
        if isinstance(to_state, str) and to_state in MILESTONE_RANK:
            found.add(to_state)
    return found


def _blog_publish_confirmed(campaign: dict[str, Any]) -> bool:
    blog_publish = campaign.get("blog_publish")
    if not isinstance(blog_publish, dict):
        return False
    status = blog_publish.get("status")
    if status not in BLOG_PUBLISH_SUCCESS_STATUSES:
        return False
    if not blog_publish.get("idempotency_key"):
        return False
    if not campaign.get("source_public_url"):
        return False
    return True


def _derivatives_confirmed(campaign: dict[str, Any]) -> bool:
    package = campaign.get("linkedin_package")
    if not isinstance(package, dict):
        return False
    if not package.get("idempotency_key"):
        return False
    variant_ids = package.get("variant_ids")
    if not isinstance(variant_ids, list) or not variant_ids:
        return False
    variants = campaign.get("variants")
    if not isinstance(variants, list) or not variants:
        return False
    by_id = {
        entry.get("variant"): entry
        for entry in variants
        if isinstance(entry, dict) and entry.get("variant")
    }
    for variant_id in variant_ids:
        if variant_id not in CANONICAL_VARIANT_IDS:
            return False
        entry = by_id.get(variant_id)
        if not isinstance(entry, dict):
            return False
        if not entry.get("artifact_relative_path"):
            return False
        if not entry.get("derivative_content_sha256"):
            return False
    return True


def _distribution_scheduled_confirmed(campaign: dict[str, Any]) -> bool:
    distribution = campaign.get("linkedin_distribution")
    if not isinstance(distribution, dict):
        return False
    if not distribution.get("idempotency_key"):
        return False
    if not distribution.get("anchor_utc"):
        return False
    package = campaign.get("linkedin_package") or {}
    variant_ids = package.get("variant_ids") if isinstance(package, dict) else None
    if not isinstance(variant_ids, list) or not variant_ids:
        variant_ids = distribution.get("variant_ids")
    if not isinstance(variant_ids, list) or not variant_ids:
        return False
    variants = campaign.get("variants")
    if not isinstance(variants, list):
        return False
    by_id = {
        entry.get("variant"): entry
        for entry in variants
        if isinstance(entry, dict) and entry.get("variant")
    }
    for variant_id in variant_ids:
        entry = by_id.get(variant_id)
        if not isinstance(entry, dict):
            return False
        if not entry.get("scheduled_at_utc"):
            return False
        if not entry.get("schedule_idempotency_key"):
            return False
    return True


def _flow_a_complete_confirmed(campaign: dict[str, Any]) -> bool:
    if campaign.get("state") != STATE_FLOW_A_COMPLETE:
        return False
    status = normalize_source_file_status(campaign.get("source_file_status"))
    if status.get("location") != SOURCE_LOCATION_PROCESSED:
        return False
    processed = campaign.get("processed_source_relative_path")
    if not isinstance(processed, str) or not processed.strip():
        return False
    return True


def _validated_confirmed(campaign: dict[str, Any]) -> bool:
    state = campaign.get("state")
    if state == STATE_VALIDATION_FAILED:
        return False
    if state in MILESTONE_RANK and MILESTONE_RANK[state] >= MILESTONE_RANK[STATE_VALIDATED]:
        return True
    history = _history_durable_states(campaign)
    if STATE_VALIDATED in history:
        return True
    validation = campaign.get("validation")
    if isinstance(validation, dict) and validation.get("status") in {
        "passed",
        "completed",
        "ok",
    }:
        return True
    # Publish success implies validation already succeeded.
    if _blog_publish_confirmed(campaign):
        return True
    return False


def _ready_confirmed(campaign: dict[str, Any]) -> bool:
    return isinstance(campaign.get("campaign_id"), str) and bool(campaign.get("campaign_id"))


def _evidence_confirmer(milestone: str):
    return {
        STATE_READY: _ready_confirmed,
        STATE_VALIDATED: _validated_confirmed,
        STATE_BLOG_PUBLISHED: _blog_publish_confirmed,
        STATE_DERIVATIVES_GENERATED: _derivatives_confirmed,
        STATE_DISTRIBUTION_SCHEDULED: _distribution_scheduled_confirmed,
        STATE_FLOW_A_COMPLETE: _flow_a_complete_confirmed,
    }[milestone]


def derive_last_valid_stage(campaign: dict[str, Any]) -> LastValidStageDerivation:
    """Derive highest confirmed durable milestone; fail closed on ambiguity."""
    candidates: set[str] = {STATE_READY}
    state = campaign.get("state")
    if isinstance(state, str) and state in MILESTONE_RANK:
        candidates.add(state)
    candidates.update(_history_durable_states(campaign))

    # Stage evidence may confirm milestones even when state lagged.
    if _blog_publish_confirmed(campaign):
        candidates.add(STATE_BLOG_PUBLISHED)
        candidates.add(STATE_VALIDATED)
    if _derivatives_confirmed(campaign):
        candidates.add(STATE_DERIVATIVES_GENERATED)
    if _distribution_scheduled_confirmed(campaign):
        candidates.add(STATE_DISTRIBUTION_SCHEDULED)
    if _flow_a_complete_confirmed(campaign):
        candidates.add(STATE_FLOW_A_COMPLETE)

    confirmed: list[str] = []
    for milestone in DURABLE_MILESTONES:
        if milestone not in candidates:
            continue
        if _evidence_confirmer(milestone)(campaign):
            confirmed.append(milestone)

    # Ambiguity: state/history claims a durable milestone that evidence does not confirm.
    claimed: set[str] = set()
    if isinstance(state, str) and state in MILESTONE_RANK:
        claimed.add(state)
    claimed.update(_history_durable_states(campaign))
    for milestone in claimed:
        if milestone == STATE_READY:
            continue
        if milestone not in confirmed and not _evidence_confirmer(milestone)(campaign):
            # flow_a_complete claimed without processed evidence is ambiguous.
            # blog_published claimed without blog_publish success is ambiguous.
            return LastValidStageDerivation(
                last_valid_stage=confirmed[-1] if confirmed else STATE_READY,
                ambiguous=True,
                ambiguity_detail=(
                    f"state or history claims {milestone!r} without confirming durable evidence"
                ),
                confirmed_milestones=tuple(confirmed),
            )

    if not confirmed:
        return LastValidStageDerivation(
            last_valid_stage=STATE_READY,
            ambiguous=False,
            confirmed_milestones=(),
        )

    # Contiguous confirmation from ready upward; gaps are ambiguity.
    highest = confirmed[-1]
    expected_prefix = [
        name
        for name in DURABLE_MILESTONES
        if MILESTONE_RANK[name] <= MILESTONE_RANK[highest]
    ]
    for expected in expected_prefix:
        if expected == STATE_READY:
            continue
        if expected not in confirmed:
            # Higher milestone confirmed without prerequisite is ambiguous unless
            # later evidence implies earlier (handled by confirmer cascade).
            if not _evidence_confirmer(expected)(campaign):
                return LastValidStageDerivation(
                    last_valid_stage=None,
                    ambiguous=True,
                    ambiguity_detail=(
                        f"missing prerequisite milestone {expected!r} before {highest!r}"
                    ),
                    confirmed_milestones=tuple(confirmed),
                )

    return LastValidStageDerivation(
        last_valid_stage=highest,
        ambiguous=False,
        confirmed_milestones=tuple(confirmed),
    )


def _next_stage_for(last_valid_stage: str | None) -> str | None:
    if last_valid_stage is None:
        return None
    return MILESTONE_TO_NEXT_STAGE.get(last_valid_stage)


def _load_error_result(
    campaign_id: str, error: CampaignLoadError
) -> IncompleteCampaignRecoveryResult:
    outcome: Outcome = "failed"
    if error.reason_code == REASON_CAMPAIGN_NOT_FOUND:
        outcome = "failed"
    return IncompleteCampaignRecoveryResult(
        campaign_id=campaign_id,
        outcome=outcome,
        reason_code=error.reason_code,
        summary=error.message,
        recovery_classification=RECOVERY_NO_ACTION,
        errors=[error.reason_code],
    )


def inspect_incomplete_campaign_recovery(
    base_path: Path, campaign_id: str
) -> IncompleteCampaignRecoveryResult:
    """Read-only recovery status for one Flow A campaign."""
    try:
        campaign = load_flow_a_campaign_for_recovery(base_path, campaign_id)
    except CampaignLoadError as exc:
        return _load_error_result(campaign_id, exc)

    classification = _effective_classification(campaign)
    derivation = derive_last_valid_stage(campaign)
    if derivation.ambiguous:
        classification = _more_severe_classification(
            classification, RECOVERY_REPAIR_REQUIRED
        )
        return IncompleteCampaignRecoveryResult(
            campaign_id=campaign_id,
            outcome="blocked",
            reason_code=REASON_EVIDENCE_AMBIGUOUS,
            summary=(
                derivation.ambiguity_detail
                or "Campaign evidence is ambiguous; repair or manual fix required"
            ),
            recovery_classification=classification,
            last_valid_stage=derivation.last_valid_stage,
            next_stage=None,
            block_reason=REASON_EVIDENCE_AMBIGUOUS,
        )

    last_valid = derivation.last_valid_stage or STATE_READY
    next_stage = _next_stage_for(last_valid)
    if last_valid == STATE_FLOW_A_COMPLETE:
        return IncompleteCampaignRecoveryResult(
            campaign_id=campaign_id,
            outcome="noop",
            reason_code=REASON_ALREADY_COMPLETE,
            summary="Campaign lifecycle completion is already consistent",
            recovery_classification=classification,
            last_valid_stage=last_valid,
            next_stage=None,
        )

    return IncompleteCampaignRecoveryResult(
        campaign_id=campaign_id,
        outcome="ok",
        reason_code=REASON_OK,
        summary=(
            f"Last valid stage is {last_valid}; "
            f"next unfinished worker stage is {next_stage}"
        ),
        recovery_classification=classification,
        last_valid_stage=last_valid,
        next_stage=next_stage,
    )


def _stages_to_run(
    last_valid_stage: str,
    *,
    stop_after_stage: str | None,
) -> list[str]:
    start_index = {
        STATE_READY: 0,
        STATE_VALIDATED: 0,
        STATE_BLOG_PUBLISHED: 1,
        STATE_DERIVATIVES_GENERATED: 2,
        STATE_DISTRIBUTION_SCHEDULED: 3,
        STATE_FLOW_A_COMPLETE: 4,
    }[last_valid_stage]
    stages = list(WORKER_STAGES[start_index:])
    if stop_after_stage is None:
        return stages
    stop_milestone_rank = MILESTONE_RANK[stop_after_stage]
    filtered: list[str] = []
    for stage in stages:
        filtered.append(stage)
        if MILESTONE_RANK[STAGE_TO_MILESTONE[stage]] >= stop_milestone_rank:
            break
    return filtered


def _plan_dry_run_stages(
    last_valid_stage: str,
    *,
    stop_after_stage: str | None,
) -> list[StagePlanOrResult]:
    planned = _stages_to_run(last_valid_stage, stop_after_stage=stop_after_stage)
    results: list[StagePlanOrResult] = []
    for stage in WORKER_STAGES:
        milestone = STAGE_TO_MILESTONE[stage]
        if MILESTONE_RANK[milestone] <= MILESTONE_RANK[last_valid_stage]:
            if stage in ("publish", "package", "schedule") or (
                stage == "source_lifecycle" and last_valid_stage == STATE_FLOW_A_COMPLETE
            ):
                results.append(
                    StagePlanOrResult(
                        stage=stage,
                        intent="skip_already_complete",
                        status="skipped",
                    )
                )
                continue
        if stage in planned:
            results.append(
                StagePlanOrResult(stage=stage, intent="would_run", status="planned")
            )
        else:
            results.append(
                StagePlanOrResult(
                    stage=stage,
                    intent="skip_stop_after",
                    status="skipped",
                )
            )
    return results


def _step_succeeded(status: str | None) -> bool:
    return status in {"completed", "skipped", "already_published", "executed"}


def resume_incomplete_campaign_recovery(
    base_path: Path,
    *,
    campaign_id: str,
    dry_run: bool = False,
    stop_after_stage: str | None = None,
) -> IncompleteCampaignRecoveryResult:
    """Resume unfinished Flow A worker stages for one campaign."""
    try:
        campaign = load_flow_a_campaign_for_recovery(base_path, campaign_id)
    except CampaignLoadError as exc:
        return _load_error_result(campaign_id, exc)

    classification = _effective_classification(campaign)
    derivation = derive_last_valid_stage(campaign)
    if derivation.ambiguous:
        classification = _more_severe_classification(
            classification, RECOVERY_REPAIR_REQUIRED
        )
        return IncompleteCampaignRecoveryResult(
            campaign_id=campaign_id,
            outcome="blocked",
            reason_code=REASON_EVIDENCE_AMBIGUOUS,
            summary=(
                derivation.ambiguity_detail
                or "Ambiguous evidence blocks resume; no stages executed"
            ),
            recovery_classification=classification,
            last_valid_stage=derivation.last_valid_stage,
            next_stage=None,
            dry_run=dry_run,
            block_reason=REASON_EVIDENCE_AMBIGUOUS,
        )

    last_valid = derivation.last_valid_stage or STATE_READY
    next_stage = _next_stage_for(last_valid)

    if last_valid == STATE_FLOW_A_COMPLETE:
        return IncompleteCampaignRecoveryResult(
            campaign_id=campaign_id,
            outcome="noop",
            reason_code=REASON_ALREADY_COMPLETE,
            summary="Campaign already at consistent flow_a_complete; resume is a no-op",
            recovery_classification=classification,
            last_valid_stage=last_valid,
            next_stage=None,
            dry_run=dry_run,
            stages=[
                StagePlanOrResult(
                    stage=stage,
                    intent="skip_already_complete",
                    status="skipped",
                )
                for stage in WORKER_STAGES
            ],
        )

    source_status = normalize_source_file_status(campaign.get("source_file_status"))
    location = source_status.get("location", SOURCE_LOCATION_READY)
    execution_state = source_status.get("execution_state", EXECUTION_STATE_IDLE)

    if location == SOURCE_LOCATION_ERROR:
        classification = _more_severe_classification(
            classification, RECOVERY_REQUEUE_REQUIRED
        )
        return IncompleteCampaignRecoveryResult(
            campaign_id=campaign_id,
            outcome="blocked",
            reason_code=REASON_REQUEUE_REQUIRED,
            summary=(
                "Source is in error/; explicit requeue is required before resume"
            ),
            recovery_classification=classification,
            last_valid_stage=last_valid,
            next_stage=next_stage,
            dry_run=dry_run,
            block_reason=REASON_REQUEUE_REQUIRED,
        )

    if execution_state == EXECUTION_STATE_PROCESSING and not is_execution_stale(
        source_status
    ):
        classification = _more_severe_classification(
            classification, RECOVERY_MANUAL_INTERVENTION_REQUIRED
        )
        return IncompleteCampaignRecoveryResult(
            campaign_id=campaign_id,
            outcome="blocked",
            reason_code=REASON_ACTIVE_CLAIM,
            summary="Active non-stale processing claim blocks resume",
            recovery_classification=classification,
            last_valid_stage=last_valid,
            next_stage=next_stage,
            dry_run=dry_run,
            block_reason=REASON_ACTIVE_CLAIM,
        )

    if dry_run:
        stages = _plan_dry_run_stages(last_valid, stop_after_stage=stop_after_stage)
        return IncompleteCampaignRecoveryResult(
            campaign_id=campaign_id,
            outcome="ok",
            reason_code=REASON_DRY_RUN,
            summary=(
                f"Dry-run resume from {last_valid}; "
                f"planned next stage is {next_stage}"
            ),
            recovery_classification=classification,
            last_valid_stage=last_valid,
            next_stage=next_stage,
            dry_run=True,
            stages=stages,
        )

    claimed = False
    if location == SOURCE_LOCATION_QUEUED:
        if execution_state == EXECUTION_STATE_PROCESSING and is_execution_stale(
            source_status
        ):
            detect_stale_flow_a_execution(base_path, campaign_id=campaign_id)
        elif execution_state == EXECUTION_STATE_STALE:
            detect_stale_flow_a_execution(base_path, campaign_id=campaign_id)

        claim_result = claim_flow_a_execution(base_path, campaign_id=campaign_id)
        if claim_result.status == "failed" or not claim_result.metadata_written:
            classification = _more_severe_classification(
                classification,
                claim_result.recovery_classification
                or RECOVERY_MANUAL_INTERVENTION_REQUIRED,
            )
            return IncompleteCampaignRecoveryResult(
                campaign_id=campaign_id,
                outcome="blocked",
                reason_code=REASON_CLAIM_FAILED,
                summary="Unable to claim campaign execution for resume",
                recovery_classification=classification,
                last_valid_stage=last_valid,
                next_stage=next_stage,
                block_reason=REASON_CLAIM_FAILED,
                errors=list(claim_result.errors),
            )
        claimed = True
        record_flow_a_progress(base_path, campaign_id=campaign_id)

    stages_to_execute = _stages_to_run(last_valid, stop_after_stage=stop_after_stage)
    stage_results: list[StagePlanOrResult] = []
    for stage in WORKER_STAGES:
        milestone = STAGE_TO_MILESTONE[stage]
        if MILESTONE_RANK[milestone] <= MILESTONE_RANK[last_valid] and stage != "source_lifecycle":
            stage_results.append(
                StagePlanOrResult(
                    stage=stage,
                    intent="skip_already_complete",
                    status="skipped",
                )
            )
        elif (
            stage == "source_lifecycle"
            and last_valid == STATE_FLOW_A_COMPLETE
        ):
            stage_results.append(
                StagePlanOrResult(
                    stage=stage,
                    intent="skip_already_complete",
                    status="skipped",
                )
            )
        elif stage not in stages_to_execute:
            stage_results.append(
                StagePlanOrResult(
                    stage=stage,
                    intent="skip_stop_after",
                    status="skipped",
                )
            )

    partial = False
    failed = False
    failure_code = REASON_STAGE_FAILED
    active_source, _ = resolve_campaign_source_paths(
        read_campaign_metadata(base_path, campaign_id) or campaign
    )

    for stage in stages_to_execute:
        if stage == "publish":
            if not active_source:
                stage_results.append(
                    StagePlanOrResult(
                        stage=stage,
                        intent="run",
                        status="failed",
                        reason_code=REASON_STAGE_FAILED,
                        detail="source path unresolved",
                    )
                )
                failed = True
                break
            publish_result = publish_blog_post(
                base_path,
                active_source,
                git_publication=False,
                live_site_confirmation=False,
            )
            ok = _step_succeeded(publish_result.status)
            stage_results.append(
                StagePlanOrResult(
                    stage=stage,
                    intent="run",
                    status=publish_result.status,
                    reason_code=None if ok else REASON_STAGE_FAILED,
                    detail=(
                        None
                        if ok
                        else (publish_result.errors[0] if publish_result.errors else None)
                    ),
                )
            )
            if not ok:
                failed = True
                if claimed:
                    release_flow_a_execution(
                        base_path,
                        campaign_id=campaign_id,
                        recovery_classification=RECOVERY_RETRYABLE,
                    )
                    claimed = False
                break
            if claimed:
                record_flow_a_progress(base_path, campaign_id=campaign_id)
            refreshed = read_campaign_metadata(base_path, campaign_id)
            if refreshed:
                active_source, _ = resolve_campaign_source_paths(refreshed)
            continue

        if stage == "package":
            package_result = generate_linkedin_package(
                base_path, campaign_id=campaign_id
            )
            ok = _step_succeeded(package_result.status)
            stage_results.append(
                StagePlanOrResult(
                    stage=stage,
                    intent="run",
                    status=package_result.status,
                    reason_code=None if ok else REASON_STAGE_FAILED,
                    detail=(
                        None
                        if ok
                        else (package_result.errors[0] if package_result.errors else None)
                    ),
                )
            )
            if not ok:
                failed = True
                if claimed:
                    release_flow_a_execution(
                        base_path,
                        campaign_id=campaign_id,
                        recovery_classification=RECOVERY_RETRYABLE,
                    )
                    claimed = False
                break
            if claimed:
                record_flow_a_progress(base_path, campaign_id=campaign_id)
            continue

        if stage == "schedule":
            schedule_result = schedule_linkedin_distribution(
                base_path, campaign_id=campaign_id
            )
            ok = _step_succeeded(schedule_result.status)
            stage_results.append(
                StagePlanOrResult(
                    stage=stage,
                    intent="run",
                    status=schedule_result.status,
                    reason_code=None if ok else REASON_STAGE_FAILED,
                    detail=(
                        None
                        if ok
                        else (
                            schedule_result.errors[0] if schedule_result.errors else None
                        )
                    ),
                )
            )
            if not ok:
                failed = True
                if claimed:
                    release_flow_a_execution(
                        base_path,
                        campaign_id=campaign_id,
                        recovery_classification=RECOVERY_REPAIR_REQUIRED,
                    )
                    claimed = False
                break
            if claimed:
                record_flow_a_progress(base_path, campaign_id=campaign_id)
            continue

        if stage == "source_lifecycle":
            lifecycle_result = complete_flow_a_source_lifecycle(
                base_path,
                campaign_id=campaign_id,
                source_relative_path=active_source,
            )
            ok = _step_succeeded(lifecycle_result.status)
            stage_results.append(
                StagePlanOrResult(
                    stage=stage,
                    intent="run",
                    status=lifecycle_result.status,
                    reason_code=None if ok else REASON_STAGE_FAILED,
                    detail=(
                        None
                        if ok
                        else (
                            lifecycle_result.errors[0]
                            if lifecycle_result.errors
                            else None
                        )
                    ),
                )
            )
            if not ok:
                failed = True
                if claimed:
                    release_flow_a_execution(
                        base_path,
                        campaign_id=campaign_id,
                        recovery_classification=RECOVERY_REPAIR_REQUIRED,
                    )
                    claimed = False
                break

    if claimed:
        final_campaign = read_campaign_metadata(base_path, campaign_id)
        final_classification = RECOVERY_NO_ACTION
        if final_campaign is not None:
            final_derivation = derive_last_valid_stage(final_campaign)
            if final_derivation.last_valid_stage != STATE_FLOW_A_COMPLETE:
                final_classification = RECOVERY_RETRYABLE
        release_flow_a_execution(
            base_path,
            campaign_id=campaign_id,
            recovery_classification=final_classification,
        )

    final = read_campaign_metadata(base_path, campaign_id) or campaign
    final_derivation = derive_last_valid_stage(final)
    final_last = final_derivation.last_valid_stage or last_valid
    final_next = _next_stage_for(final_last)
    final_classification = _effective_classification(final)

    ran = [item for item in stage_results if item.intent == "run"]
    if failed:
        if ran and any(_step_succeeded(item.status) for item in ran):
            partial = True
        outcome: Outcome = "partial" if partial else "failed"
        return IncompleteCampaignRecoveryResult(
            campaign_id=campaign_id,
            outcome=outcome,
            reason_code=REASON_PARTIAL if partial else failure_code,
            summary=(
                "Resume stopped after a stage failure; partial progress preserved"
                if partial
                else "Resume failed before durable stage progress"
            ),
            recovery_classification=final_classification,
            last_valid_stage=final_last,
            next_stage=final_next,
            stages=stage_results,
            errors=[failure_code],
        )

    if final_last == STATE_FLOW_A_COMPLETE:
        return IncompleteCampaignRecoveryResult(
            campaign_id=campaign_id,
            outcome="ok",
            reason_code=REASON_OK,
            summary="Resume completed remaining worker stages through lifecycle completion",
            recovery_classification=final_classification,
            last_valid_stage=final_last,
            next_stage=None,
            stages=stage_results,
        )

    return IncompleteCampaignRecoveryResult(
        campaign_id=campaign_id,
        outcome="ok",
        reason_code=REASON_OK,
        summary=(
            f"Resume advanced campaign to {final_last}; "
            f"next unfinished stage is {final_next}"
        ),
        recovery_classification=final_classification,
        last_valid_stage=final_last,
        next_stage=final_next,
        stages=stage_results,
    )


def _find_markdown_locations(
    base_path: Path, campaign: dict[str, Any]
) -> list[tuple[str, str]]:
    """Return (location, relative_path) matches for campaign Markdown identity."""
    source_slug = campaign.get("source_slug")
    source_hash = campaign.get("source_content_sha256")
    candidates: list[tuple[str, str]] = []
    for location in (
        SOURCE_LOCATION_READY,
        SOURCE_LOCATION_QUEUED,
        SOURCE_LOCATION_PROCESSED,
        SOURCE_LOCATION_ERROR,
    ):
        folder = base_path / "blog-posts" / location
        if not folder.is_dir():
            continue
        for path in folder.glob("*.md"):
            if path.name.startswith("."):
                continue
            relative = normalize_relative_path(
                f"blog-posts/{location}/{path.name}"
            )
            matched = False
            if isinstance(source_slug, str) and path.stem == source_slug:
                matched = True
            if isinstance(source_hash, str) and source_hash:
                try:
                    digest = hashlib.sha256(path.read_bytes()).hexdigest()
                except OSError:
                    digest = None
                if digest == source_hash:
                    matched = True
            # Also match known path fields.
            known_paths = {
                campaign.get("source_relative_path"),
                campaign.get("queued_source_relative_path"),
                campaign.get("processed_source_relative_path"),
                campaign.get("error_source_relative_path"),
                campaign.get("original_source_relative_path"),
            }
            if relative in known_paths:
                matched = True
            if matched:
                candidates.append((location, relative))
    # Deduplicate while preserving order.
    seen: set[tuple[str, str]] = set()
    unique: list[tuple[str, str]] = []
    for item in candidates:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def _location_path_fields(location: str, relative: str) -> dict[str, Any]:
    updates: dict[str, Any] = {"source_relative_path": relative}
    if location == SOURCE_LOCATION_QUEUED:
        updates["queued_source_relative_path"] = relative
    elif location == SOURCE_LOCATION_PROCESSED:
        updates["processed_source_relative_path"] = relative
    elif location == SOURCE_LOCATION_ERROR:
        updates["error_source_relative_path"] = relative
    return updates


def repair_incomplete_campaign_recovery(
    base_path: Path,
    *,
    campaign_id: str,
    repair_action: str,
    dry_run: bool = False,
) -> IncompleteCampaignRecoveryResult:
    """Apply an allowlisted metadata/filesystem repair for one campaign."""
    try:
        campaign = load_flow_a_campaign_for_recovery(base_path, campaign_id)
    except CampaignLoadError as exc:
        return _load_error_result(campaign_id, exc)

    if repair_action not in REPAIR_ACTIONS:
        # Caller/HTTP layer should 422; defensive service guard.
        return IncompleteCampaignRecoveryResult(
            campaign_id=campaign_id,
            outcome="failed",
            reason_code=REASON_REPAIR_REFUSED,
            summary=f"Unknown repair_action {repair_action!r}",
            recovery_classification=_effective_classification(campaign),
            dry_run=dry_run,
            repair_action=repair_action,
            errors=[REASON_REPAIR_REFUSED],
        )

    classification = _effective_classification(campaign)
    source_status = normalize_source_file_status(campaign.get("source_file_status"))
    execution_state = source_status.get("execution_state", EXECUTION_STATE_IDLE)

    if (
        execution_state == EXECUTION_STATE_PROCESSING
        and not is_execution_stale(source_status)
        and repair_action != "clear_stale_execution_claim"
    ):
        classification = _more_severe_classification(
            classification, RECOVERY_MANUAL_INTERVENTION_REQUIRED
        )
        return IncompleteCampaignRecoveryResult(
            campaign_id=campaign_id,
            outcome="blocked",
            reason_code=REASON_ACTIVE_CLAIM,
            summary="Active non-stale processing claim blocks repair",
            recovery_classification=classification,
            dry_run=dry_run,
            repair_action=repair_action,
            block_reason=REASON_ACTIVE_CLAIM,
            before=_safe_source_status_summary(campaign),
        )

    derivation = derive_last_valid_stage(campaign)
    last_valid = derivation.last_valid_stage

    if repair_action == "sync_location_from_filesystem":
        matches = _find_markdown_locations(base_path, campaign)
        if len(matches) > 1:
            return IncompleteCampaignRecoveryResult(
                campaign_id=campaign_id,
                outcome="blocked",
                reason_code=REASON_REPAIR_AMBIGUOUS_LOCATION,
                summary=(
                    "Multiple Markdown locations match campaign identity; "
                    "location sync refused"
                ),
                recovery_classification=_more_severe_classification(
                    classification, RECOVERY_REPAIR_REQUIRED
                ),
                last_valid_stage=last_valid,
                dry_run=dry_run,
                repair_action=repair_action,
                block_reason=REASON_REPAIR_AMBIGUOUS_LOCATION,
                before=_safe_source_status_summary(campaign),
            )
        if len(matches) == 0:
            return IncompleteCampaignRecoveryResult(
                campaign_id=campaign_id,
                outcome="blocked",
                reason_code=REASON_REPAIR_AMBIGUOUS_LOCATION,
                summary="No unique Markdown location found for location sync",
                recovery_classification=_more_severe_classification(
                    classification, RECOVERY_REPAIR_REQUIRED
                ),
                last_valid_stage=last_valid,
                dry_run=dry_run,
                repair_action=repair_action,
                block_reason=REASON_REPAIR_AMBIGUOUS_LOCATION,
                before=_safe_source_status_summary(campaign),
            )

        observed_location, observed_relative = matches[0]
        current_location = source_status.get("location")
        before = _safe_source_status_summary(campaign)
        if observed_location == current_location:
            return IncompleteCampaignRecoveryResult(
                campaign_id=campaign_id,
                outcome="noop",
                reason_code=REASON_REPAIR_NO_MISMATCH,
                summary="Metadata location already matches filesystem",
                recovery_classification=classification,
                last_valid_stage=last_valid,
                dry_run=dry_run,
                repair_action=repair_action,
                before=before,
                after=before,
            )

        after_status = deepcopy(source_status)
        after_status["location"] = observed_location
        if observed_location == SOURCE_LOCATION_PROCESSED:
            after_status["recovery_classification"] = RECOVERY_NO_ACTION
        elif observed_location == SOURCE_LOCATION_ERROR:
            after_status["recovery_classification"] = RECOVERY_REQUEUE_REQUIRED
        else:
            after_status["recovery_classification"] = RECOVERY_RETRYABLE

        after_campaign_view = {
            "location": observed_location,
            "execution_state": after_status.get("execution_state"),
            "recovery_classification": after_status.get("recovery_classification"),
            "physical_move_state": after_status.get("physical_move_state"),
            "source_relative_path": observed_relative,
        }

        if dry_run:
            return IncompleteCampaignRecoveryResult(
                campaign_id=campaign_id,
                outcome="ok",
                reason_code=REASON_DRY_RUN,
                summary=(
                    f"Dry-run would sync location {current_location!r} → "
                    f"{observed_location!r}"
                ),
                recovery_classification=after_status["recovery_classification"],
                last_valid_stage=last_valid,
                dry_run=True,
                repair_action=repair_action,
                before=before,
                after=after_campaign_view,
            )

        working = deepcopy(campaign)
        working_status = normalize_source_file_status(working.get("source_file_status"))
        working_status["location"] = observed_location
        working_status["recovery_classification"] = after_status[
            "recovery_classification"
        ]
        working_status["last_transition_at"] = utc_now_iso()
        working["source_file_status"] = working_status
        working.update(_location_path_fields(observed_location, observed_relative))
        working["updated_at"] = utc_now_iso()
        write_result = write_campaign_metadata(base_path, campaign_id, working)
        if not write_result.written:
            return IncompleteCampaignRecoveryResult(
                campaign_id=campaign_id,
                outcome="failed",
                reason_code=REASON_REPAIR_REFUSED,
                summary="Failed to persist location sync",
                recovery_classification=classification,
                last_valid_stage=last_valid,
                repair_action=repair_action,
                before=before,
                errors=[write_result.error_code or REASON_REPAIR_REFUSED],
            )
        refreshed = read_campaign_metadata(base_path, campaign_id) or working
        return IncompleteCampaignRecoveryResult(
            campaign_id=campaign_id,
            outcome="ok",
            reason_code=REASON_OK,
            summary=(
                f"Synced location {current_location!r} → {observed_location!r}"
            ),
            recovery_classification=_effective_classification(refreshed),
            last_valid_stage=derive_last_valid_stage(refreshed).last_valid_stage,
            repair_action=repair_action,
            before=before,
            after=_safe_source_status_summary(refreshed)
            | {"source_relative_path": observed_relative},
        )

    if repair_action == "clear_stale_execution_claim":
        before = _safe_source_status_summary(campaign)
        stale = execution_state == EXECUTION_STATE_STALE or (
            execution_state == EXECUTION_STATE_PROCESSING
            and is_execution_stale(source_status)
        )
        if not stale:
            return IncompleteCampaignRecoveryResult(
                campaign_id=campaign_id,
                outcome="blocked",
                reason_code=REASON_REPAIR_NOT_STALE,
                summary="Execution claim is not stale; clear refused",
                recovery_classification=classification,
                last_valid_stage=last_valid,
                dry_run=dry_run,
                repair_action=repair_action,
                block_reason=REASON_REPAIR_NOT_STALE,
                before=before,
            )

        after_view = {
            "location": before.get("location"),
            "execution_state": EXECUTION_STATE_IDLE,
            "recovery_classification": RECOVERY_RETRYABLE,
            "physical_move_state": before.get("physical_move_state"),
        }
        if dry_run:
            return IncompleteCampaignRecoveryResult(
                campaign_id=campaign_id,
                outcome="ok",
                reason_code=REASON_DRY_RUN,
                summary="Dry-run would clear stale execution claim to idle",
                recovery_classification=RECOVERY_RETRYABLE,
                last_valid_stage=last_valid,
                dry_run=True,
                repair_action=repair_action,
                before=before,
                after=after_view,
            )

        if execution_state == EXECUTION_STATE_PROCESSING:
            detect_stale_flow_a_execution(base_path, campaign_id=campaign_id)

        # Reclaim stale → processing, then release → idle without erasing stage evidence.
        claim_result = claim_flow_a_execution(base_path, campaign_id=campaign_id)
        if claim_result.status == "failed":
            # If not queued, clear directly while preserving stage evidence.
            working = read_campaign_metadata(base_path, campaign_id) or deepcopy(
                campaign
            )
            working_status = normalize_source_file_status(
                working.get("source_file_status")
            )
            if working_status.get("execution_state") not in {
                EXECUTION_STATE_STALE,
                EXECUTION_STATE_PROCESSING,
            }:
                return IncompleteCampaignRecoveryResult(
                    campaign_id=campaign_id,
                    outcome="failed",
                    reason_code=REASON_REPAIR_REFUSED,
                    summary="Unable to clear stale claim",
                    recovery_classification=classification,
                    last_valid_stage=last_valid,
                    repair_action=repair_action,
                    before=before,
                    errors=list(claim_result.errors),
                )
            working_status["execution_state"] = EXECUTION_STATE_IDLE
            working_status["recovery_classification"] = RECOVERY_RETRYABLE
            working_status["last_transition_at"] = utc_now_iso()
            working["source_file_status"] = working_status
            working["updated_at"] = utc_now_iso()
            write_campaign_metadata(base_path, campaign_id, working)
        else:
            release_flow_a_execution(
                base_path,
                campaign_id=campaign_id,
                recovery_classification=RECOVERY_RETRYABLE,
            )

        refreshed = read_campaign_metadata(base_path, campaign_id) or campaign
        return IncompleteCampaignRecoveryResult(
            campaign_id=campaign_id,
            outcome="ok",
            reason_code=REASON_OK,
            summary="Cleared stale execution claim to idle",
            recovery_classification=_effective_classification(refreshed),
            last_valid_stage=derive_last_valid_stage(refreshed).last_valid_stage,
            repair_action=repair_action,
            before=before,
            after=_safe_source_status_summary(refreshed),
        )

    # complete_partial_source_move
    before = _safe_source_status_summary(campaign)
    if source_status.get("physical_move_state") != PHYSICAL_MOVE_STATE_PARTIAL:
        return IncompleteCampaignRecoveryResult(
            campaign_id=campaign_id,
            outcome="blocked",
            reason_code=REASON_REPAIR_NOT_PARTIAL,
            summary="physical_move_state is not partial; complete move refused",
            recovery_classification=classification,
            last_valid_stage=last_valid,
            dry_run=dry_run,
            repair_action=repair_action,
            block_reason=REASON_REPAIR_NOT_PARTIAL,
            before=before,
        )

    location = source_status.get("location")
    if location not in {
        SOURCE_LOCATION_QUEUED,
        SOURCE_LOCATION_ERROR,
        SOURCE_LOCATION_PROCESSED,
    }:
        return IncompleteCampaignRecoveryResult(
            campaign_id=campaign_id,
            outcome="blocked",
            reason_code=REASON_REPAIR_PARTIAL_UNSAFE,
            summary="Partial move destination location is unsafe or unknown",
            recovery_classification=_more_severe_classification(
                classification, RECOVERY_REPAIR_REQUIRED
            ),
            last_valid_stage=last_valid,
            dry_run=dry_run,
            repair_action=repair_action,
            block_reason=REASON_REPAIR_PARTIAL_UNSAFE,
            before=before,
        )

    md_relative, image_relative = resolve_campaign_source_paths(campaign)
    if not md_relative or not (base_path / md_relative).is_file():
        return IncompleteCampaignRecoveryResult(
            campaign_id=campaign_id,
            outcome="blocked",
            reason_code=REASON_REPAIR_PARTIAL_UNSAFE,
            summary="Partial move Markdown destination is missing or ambiguous",
            recovery_classification=_more_severe_classification(
                classification, RECOVERY_REPAIR_REQUIRED
            ),
            last_valid_stage=last_valid,
            dry_run=dry_run,
            repair_action=repair_action,
            block_reason=REASON_REPAIR_PARTIAL_UNSAFE,
            before=before,
        )

    # Remaining sibling is the image still outside the destination folder.
    # Markdown is already at the destination for partial moves; move image only.
    remaining_image = None
    for candidate in (
        campaign.get("original_image_relative_path"),
        campaign.get("queued_image_relative_path"),
        campaign.get("image_relative_path"),
        image_relative,
    ):
        if not isinstance(candidate, str) or not candidate.strip():
            continue
        normalized = normalize_relative_path(candidate)
        path = base_path / normalized
        if path.is_file() and f"blog-posts/{location}/" not in normalized:
            remaining_image = normalized
            break

    if remaining_image is None:
        after_view = dict(before)
        after_view["physical_move_state"] = PHYSICAL_MOVE_STATE_COMPLETED
        if dry_run:
            return IncompleteCampaignRecoveryResult(
                campaign_id=campaign_id,
                outcome="ok",
                reason_code=REASON_DRY_RUN,
                summary="Dry-run would mark partial move completed (no remaining image)",
                recovery_classification=classification,
                last_valid_stage=last_valid,
                dry_run=True,
                repair_action=repair_action,
                before=before,
                after=after_view,
            )
        working = deepcopy(campaign)
        working_status = normalize_source_file_status(working.get("source_file_status"))
        working_status["physical_move_state"] = PHYSICAL_MOVE_STATE_COMPLETED
        working_status["last_transition_at"] = utc_now_iso()
        working["source_file_status"] = working_status
        working["updated_at"] = utc_now_iso()
        write_campaign_metadata(base_path, campaign_id, working)
        refreshed = read_campaign_metadata(base_path, campaign_id) or working
        return IncompleteCampaignRecoveryResult(
            campaign_id=campaign_id,
            outcome="ok",
            reason_code=REASON_OK,
            summary="Marked partial move completed; no remaining sibling image",
            recovery_classification=_effective_classification(refreshed),
            last_valid_stage=derive_last_valid_stage(refreshed).last_valid_stage,
            repair_action=repair_action,
            before=before,
            after=_safe_source_status_summary(refreshed),
        )

    image_name = Path(remaining_image).name
    dest_image_relative = normalize_relative_path(
        f"blog-posts/{location}/{image_name}"
    )
    dest_image_path = (base_path / dest_image_relative).resolve()
    location_root = (base_path / "blog-posts" / location).resolve()
    try:
        dest_image_path.relative_to(location_root)
    except ValueError:
        return IncompleteCampaignRecoveryResult(
            campaign_id=campaign_id,
            outcome="blocked",
            reason_code=REASON_REPAIR_PARTIAL_UNSAFE,
            summary="Partial image destination escapes editorial location confinement",
            recovery_classification=_more_severe_classification(
                classification, RECOVERY_REPAIR_REQUIRED
            ),
            last_valid_stage=last_valid,
            dry_run=dry_run,
            repair_action=repair_action,
            block_reason=REASON_REPAIR_PARTIAL_UNSAFE,
            before=before,
        )

    if dry_run:
        return IncompleteCampaignRecoveryResult(
            campaign_id=campaign_id,
            outcome="ok",
            reason_code=REASON_DRY_RUN,
            summary=f"Dry-run would complete partial image move into {location}/",
            recovery_classification=classification,
            last_valid_stage=last_valid,
            dry_run=True,
            repair_action=repair_action,
            before=before,
            after={
                **before,
                "physical_move_state": PHYSICAL_MOVE_STATE_COMPLETED,
                "remaining_image": remaining_image,
            },
        )

    source_image_path = (base_path / remaining_image).resolve()
    already_at_dest = dest_image_path.exists() and source_image_path.samefile(
        dest_image_path
    )
    if dest_image_path.exists() and not already_at_dest:
        return IncompleteCampaignRecoveryResult(
            campaign_id=campaign_id,
            outcome="blocked",
            reason_code=REASON_REPAIR_PARTIAL_UNSAFE,
            summary="Partial image destination already exists with a different file",
            recovery_classification=_more_severe_classification(
                classification, RECOVERY_REPAIR_REQUIRED
            ),
            last_valid_stage=last_valid,
            repair_action=repair_action,
            block_reason=REASON_REPAIR_PARTIAL_UNSAFE,
            before=before,
        )

    try:
        if not already_at_dest:
            shutil.move(str(source_image_path), str(dest_image_path))
    except OSError:
        return IncompleteCampaignRecoveryResult(
            campaign_id=campaign_id,
            outcome="failed",
            reason_code=REASON_REPAIR_PARTIAL_UNSAFE,
            summary="Failed to complete partial source move",
            recovery_classification=_more_severe_classification(
                classification, RECOVERY_REPAIR_REQUIRED
            ),
            last_valid_stage=last_valid,
            repair_action=repair_action,
            before=before,
            errors=["image_move_failed"],
        )

    working = read_campaign_metadata(base_path, campaign_id) or deepcopy(campaign)
    working_status = normalize_source_file_status(working.get("source_file_status"))
    working_status["physical_move_state"] = PHYSICAL_MOVE_STATE_COMPLETED
    if location == SOURCE_LOCATION_ERROR:
        working_status["recovery_classification"] = RECOVERY_REQUEUE_REQUIRED
    else:
        working_status["recovery_classification"] = RECOVERY_RETRYABLE
    working_status["last_transition_at"] = utc_now_iso()
    working["source_file_status"] = working_status
    if location == SOURCE_LOCATION_QUEUED:
        working["queued_image_relative_path"] = dest_image_relative
    elif location == SOURCE_LOCATION_ERROR:
        working["error_image_relative_path"] = dest_image_relative
    elif location == SOURCE_LOCATION_PROCESSED:
        working["processed_image_relative_path"] = dest_image_relative
    working["image_relative_path"] = dest_image_relative
    working["updated_at"] = utc_now_iso()
    write_campaign_metadata(base_path, campaign_id, working)
    refreshed = read_campaign_metadata(base_path, campaign_id) or working

    return IncompleteCampaignRecoveryResult(
        campaign_id=campaign_id,
        outcome="ok",
        reason_code=REASON_OK,
        summary="Completed partial source move",
        recovery_classification=_effective_classification(refreshed),
        last_valid_stage=derive_last_valid_stage(refreshed).last_valid_stage,
        repair_action=repair_action,
        before=before,
        after=_safe_source_status_summary(refreshed),
    )
