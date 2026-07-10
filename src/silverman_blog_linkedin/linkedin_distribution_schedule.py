"""Flow A LinkedIn distribution scheduling orchestration."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.campaign_lifecycle import (
    ACTOR_WORKER,
    CampaignLifecycleError,
    FLOW_A,
    FLOW_B,
    STATE_DERIVATIVES_GENERATED,
    STATE_DISTRIBUTION_COMPLETE,
    STATE_DISTRIBUTION_SCHEDULED,
    STATE_FLOW_A_COMPLETE,
    find_campaign_by_source_path,
    normalize_scheduled_at_utc,
    read_campaign_metadata,
    transition_state,
    write_campaign_metadata,
)

DEFAULT_STAGGER_STRATEGY = "flow_a_staggered"
DEFAULT_PUBLISH_HOUR_UTC = 14
PREFERRED_WEEKDAYS = frozenset({1, 2, 3})  # Tuesday, Wednesday, Thursday

AUDIENCE_SEQUENCE: tuple[str, ...] = (
    "executive-recruiter",
    "engineering-leadership",
    "technical-architect",
    "short-provocative",
)

VARIANT_DAY_OFFSETS: dict[str, int] = {
    "executive-recruiter": 0,
    "engineering-leadership": 3,
    "technical-architect": 6,
    "short-provocative": 9,
}

LINKEDIN_SCHEDULE_CAMPAIGN_NOT_FOUND = "linkedin_schedule_campaign_not_found"
LINKEDIN_SCHEDULE_FLOW_NOT_ALLOWED = "linkedin_schedule_flow_not_allowed"
LINKEDIN_SCHEDULE_INVALID_CAMPAIGN_STATE = "linkedin_schedule_invalid_campaign_state"
LINKEDIN_SCHEDULE_PACKAGE_MISSING = "linkedin_schedule_package_missing"
LINKEDIN_SCHEDULE_VARIANT_METADATA_MISSING = "linkedin_schedule_variant_metadata_missing"
LINKEDIN_SCHEDULE_ARTIFACT_MISSING = "linkedin_schedule_artifact_missing"
LINKEDIN_SCHEDULE_ARTIFACT_HASH_CHANGED = "linkedin_schedule_artifact_hash_changed"
LINKEDIN_SCHEDULE_METADATA_MISMATCH = "linkedin_schedule_metadata_mismatch"
LINKEDIN_SCHEDULE_NO_VARIANTS = "linkedin_schedule_no_variants"
LINKEDIN_SCHEDULE_INVALID_STRATEGY = "linkedin_schedule_invalid_strategy"
LINKEDIN_SCHEDULE_INVALID_ANCHOR = "linkedin_schedule_invalid_anchor"
LINKEDIN_SCHEDULE_METADATA_WRITE_FAILED = "linkedin_schedule_metadata_write_failed"

SCHEDULE_ELIGIBLE_STATES = frozenset(
    {STATE_DERIVATIVES_GENERATED, STATE_DISTRIBUTION_SCHEDULED}
)

SCHEDULE_INVALID_STATES = frozenset(
    {STATE_DISTRIBUTION_COMPLETE, STATE_FLOW_A_COMPLETE}
)

PUBLISH_STATE_PENDING = "pending"


@dataclass
class LinkedInDistributionScheduleResult:
    status: str
    campaign_id: str | None = None
    state: str | None = None
    strategy: str | None = None
    anchor_utc: str | None = None
    distribution_id: str | None = None
    variant_schedules: list[dict[str, Any]] = field(default_factory=list)
    distribution: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata_written: bool = False
    metadata_error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_schedule_idempotency_key(
    *,
    campaign_id: str,
    source_content_sha256: str,
    package_idempotency_key: str,
    variant_ids: list[str],
    strategy: str,
    anchor_utc: str,
    flow: str,
) -> str:
    """Build schedule-level idempotency key with sorted variant list."""
    sorted_variants = ",".join(sorted(variant_ids))
    return (
        f"schedule:{campaign_id}:{source_content_sha256}:"
        f"{package_idempotency_key}:{sorted_variants}:{strategy}:{anchor_utc}:{flow}"
    )


def build_variant_schedule_idempotency_key(
    *,
    campaign_id: str,
    variant: str,
    derivative_content_sha256: str,
    scheduled_at_utc: str,
    flow: str,
) -> str:
    """Build per-variant schedule idempotency key."""
    normalized_at = normalize_scheduled_at_utc(scheduled_at_utc)
    return (
        f"schedule-variant:{campaign_id}:{variant}:"
        f"{derivative_content_sha256}:{normalized_at}:{flow}"
    )


def _distribution_id(campaign_id: str) -> str:
    return f"{campaign_id}-dist"


def _resolve_campaign(
    base_path: Path,
    *,
    campaign_id: str | None,
    source_relative_path: str | None,
) -> dict[str, Any] | None:
    if campaign_id:
        return read_campaign_metadata(base_path, campaign_id)
    if source_relative_path:
        return find_campaign_by_source_path(base_path, source_relative_path)
    return None


def _get_variant_metadata_map(campaign: dict[str, Any]) -> dict[str, dict[str, Any]]:
    variants = campaign.get("variants") or []
    return {
        entry["variant"]: entry
        for entry in variants
        if isinstance(entry, dict) and entry.get("variant")
    }


def _failed_result(
    *,
    campaign: dict[str, Any] | None,
    errors: list[str],
    warnings: list[str] | None = None,
    strategy: str | None = None,
    anchor_utc: str | None = None,
    metadata_written: bool = False,
    metadata_error_code: str | None = None,
    variant_schedules: list[dict[str, Any]] | None = None,
    distribution: dict[str, Any] | None = None,
) -> LinkedInDistributionScheduleResult:
    distribution_obj = distribution
    if distribution_obj is None and campaign:
        distribution_obj = campaign.get("linkedin_distribution")
    return LinkedInDistributionScheduleResult(
        status="failed",
        campaign_id=campaign.get("campaign_id") if campaign else None,
        state=campaign.get("state") if campaign else None,
        strategy=strategy,
        anchor_utc=anchor_utc,
        distribution_id=(
            (distribution_obj or {}).get("distribution_id")
            if distribution_obj
            else (
                _distribution_id(campaign["campaign_id"])
                if campaign and campaign.get("campaign_id")
                else None
            )
        ),
        variant_schedules=variant_schedules or [],
        distribution=distribution_obj,
        errors=errors,
        warnings=warnings or list(campaign.get("warnings") or []) if campaign else [],
        metadata_written=metadata_written,
        metadata_error_code=metadata_error_code,
    )


def _completed_result(
    campaign: dict[str, Any],
    *,
    strategy: str,
    anchor_utc: str,
    variant_schedules: list[dict[str, Any]],
    metadata_written: bool,
    metadata_error_code: str | None = None,
) -> LinkedInDistributionScheduleResult:
    distribution = dict(campaign.get("linkedin_distribution") or {})
    return LinkedInDistributionScheduleResult(
        status="completed",
        campaign_id=campaign["campaign_id"],
        state=campaign["state"],
        strategy=strategy,
        anchor_utc=anchor_utc,
        distribution_id=distribution.get("distribution_id"),
        variant_schedules=variant_schedules,
        distribution=distribution,
        errors=[],
        warnings=list(campaign.get("warnings") or []),
        metadata_written=metadata_written,
        metadata_error_code=metadata_error_code,
    )


def _variant_schedule_summary(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "variant": entry["variant"],
        "artifact_relative_path": entry["artifact_relative_path"],
        "derivative_content_sha256": entry["derivative_content_sha256"],
        "scheduled_at_utc": entry["scheduled_at_utc"],
        "publish_state": entry["publish_state"],
        "schedule_idempotency_key": entry["schedule_idempotency_key"],
    }


def _ordered_variant_ids(variant_ids: list[str]) -> list[str]:
    order_index = {variant_id: index for index, variant_id in enumerate(AUDIENCE_SEQUENCE)}
    return sorted(variant_ids, key=lambda variant_id: order_index.get(variant_id, 999))


def _default_anchor_utc(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    if current.weekday() in PREFERRED_WEEKDAYS:
        candidate = current.replace(hour=DEFAULT_PUBLISH_HOUR_UTC, minute=0, second=0, microsecond=0)
        if current < candidate:
            return candidate.strftime("%Y-%m-%dT%H:%M:%SZ")

    for day_offset in range(1, 8):
        candidate_day = current + timedelta(days=day_offset)
        if candidate_day.weekday() in PREFERRED_WEEKDAYS:
            anchor = candidate_day.replace(
                hour=DEFAULT_PUBLISH_HOUR_UTC, minute=0, second=0, microsecond=0
            )
            return anchor.strftime("%Y-%m-%dT%H:%M:%SZ")

    raise RuntimeError("unable to resolve default schedule anchor")


def _resolve_anchor_utc(start_at_utc: str | None) -> tuple[str | None, str | None]:
    if start_at_utc is None:
        return _default_anchor_utc(), None
    try:
        return normalize_scheduled_at_utc(start_at_utc), None
    except CampaignLifecycleError:
        return None, LINKEDIN_SCHEDULE_INVALID_ANCHOR


def _compute_staggered_schedules(
    variant_ids: list[str], anchor_utc: str
) -> dict[str, str]:
    anchor = datetime.strptime(anchor_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    schedules: dict[str, str] = {}
    for variant_id in _ordered_variant_ids(variant_ids):
        day_offset = VARIANT_DAY_OFFSETS[variant_id]
        scheduled = anchor + timedelta(days=day_offset)
        schedules[variant_id] = scheduled.strftime("%Y-%m-%dT%H:%M:%SZ")
    return schedules


def _verify_artifacts(
    base_path: Path,
    campaign: dict[str, Any],
    *,
    variant_ids: list[str],
) -> tuple[dict[str, dict[str, Any]], str | None]:
    metadata_map = _get_variant_metadata_map(campaign)
    verified: dict[str, dict[str, Any]] = {}
    for variant_id in variant_ids:
        entry = metadata_map.get(variant_id)
        if entry is None:
            return {}, LINKEDIN_SCHEDULE_VARIANT_METADATA_MISSING
        artifact_relative = entry.get("artifact_relative_path")
        stored_hash = entry.get("derivative_content_sha256")
        if not artifact_relative or not stored_hash:
            return {}, LINKEDIN_SCHEDULE_VARIANT_METADATA_MISSING
        artifact_path = base_path / artifact_relative
        if not artifact_path.is_file():
            return {}, LINKEDIN_SCHEDULE_ARTIFACT_MISSING
        on_disk_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        if on_disk_hash != stored_hash:
            return {}, LINKEDIN_SCHEDULE_ARTIFACT_HASH_CHANGED
        verified[variant_id] = entry
    return verified, None


def _check_idempotent_completed(
    campaign: dict[str, Any],
    *,
    expected_schedule_key: str,
    anchor_utc: str,
    variant_ids: list[str],
) -> bool:
    if campaign.get("state") != STATE_DISTRIBUTION_SCHEDULED:
        return False
    distribution = campaign.get("linkedin_distribution") or {}
    if distribution.get("idempotency_key") != expected_schedule_key:
        return False
    if distribution.get("anchor_utc") != anchor_utc:
        return False
    metadata_map = _get_variant_metadata_map(campaign)
    for variant_id in variant_ids:
        entry = metadata_map.get(variant_id)
        if entry is None:
            return False
        if not entry.get("scheduled_at_utc"):
            return False
        if entry.get("publish_state") != PUBLISH_STATE_PENDING:
            return False
        if not entry.get("schedule_idempotency_key"):
            return False
    return True


def schedule_linkedin_distribution(
    base_path: Path,
    *,
    campaign_id: str | None = None,
    source_relative_path: str | None = None,
    strategy: str | None = None,
    start_at_utc: str | None = None,
    timezone: str | None = None,
) -> LinkedInDistributionScheduleResult:
    """Schedule Flow A LinkedIn distribution for one campaign."""
    del timezone  # reserved for documentation/future use

    resolved_strategy = strategy or DEFAULT_STAGGER_STRATEGY
    if resolved_strategy != DEFAULT_STAGGER_STRATEGY:
        return LinkedInDistributionScheduleResult(
            status="failed",
            strategy=resolved_strategy,
            errors=[LINKEDIN_SCHEDULE_INVALID_STRATEGY],
        )

    campaign = _resolve_campaign(
        base_path,
        campaign_id=campaign_id,
        source_relative_path=source_relative_path,
    )
    if campaign is None:
        return LinkedInDistributionScheduleResult(
            status="failed",
            strategy=resolved_strategy,
            errors=[LINKEDIN_SCHEDULE_CAMPAIGN_NOT_FOUND],
        )

    if campaign.get("flow") == FLOW_B:
        return _failed_result(
            campaign=campaign,
            errors=[LINKEDIN_SCHEDULE_FLOW_NOT_ALLOWED],
            strategy=resolved_strategy,
        )

    state = campaign.get("state")
    if state in SCHEDULE_INVALID_STATES:
        distribution = campaign.get("linkedin_distribution") or {}
        if distribution.get("idempotency_key") and distribution.get("anchor_utc"):
            metadata_map = _get_variant_metadata_map(campaign)
            variant_ids_existing = sorted(distribution.get("variant_ids") or [])
            if variant_ids_existing and all(
                metadata_map.get(variant_id, {}).get("scheduled_at_utc")
                for variant_id in variant_ids_existing
            ):
                variant_schedules = [
                    _variant_schedule_summary(metadata_map[variant_id])
                    for variant_id in _ordered_variant_ids(variant_ids_existing)
                ]
                return _completed_result(
                    campaign,
                    strategy=distribution.get("strategy") or resolved_strategy,
                    anchor_utc=distribution["anchor_utc"],
                    variant_schedules=variant_schedules,
                    metadata_written=False,
                )
        return _failed_result(
            campaign=campaign,
            errors=[LINKEDIN_SCHEDULE_INVALID_CAMPAIGN_STATE],
            strategy=resolved_strategy,
        )

    if state not in SCHEDULE_ELIGIBLE_STATES:
        return _failed_result(
            campaign=campaign,
            errors=[LINKEDIN_SCHEDULE_INVALID_CAMPAIGN_STATE],
            strategy=resolved_strategy,
        )

    package = campaign.get("linkedin_package")
    if not package or not package.get("idempotency_key") or not package.get("variant_ids"):
        return _failed_result(
            campaign=campaign,
            errors=[LINKEDIN_SCHEDULE_PACKAGE_MISSING],
            strategy=resolved_strategy,
        )

    variant_ids = sorted(package["variant_ids"])
    if not variant_ids:
        return _failed_result(
            campaign=campaign,
            errors=[LINKEDIN_SCHEDULE_NO_VARIANTS],
            strategy=resolved_strategy,
        )

    metadata_map = _get_variant_metadata_map(campaign)
    for variant_id in variant_ids:
        if variant_id not in metadata_map:
            return _failed_result(
                campaign=campaign,
                errors=[LINKEDIN_SCHEDULE_VARIANT_METADATA_MISSING],
                strategy=resolved_strategy,
            )

    anchor_utc, anchor_error = _resolve_anchor_utc(start_at_utc)
    if anchor_error:
        return _failed_result(
            campaign=campaign,
            errors=[anchor_error],
            strategy=resolved_strategy,
            anchor_utc=start_at_utc,
        )
    assert anchor_utc is not None

    source_content_sha256 = campaign.get("source_content_sha256")
    if not source_content_sha256:
        return _failed_result(
            campaign=campaign,
            errors=[LINKEDIN_SCHEDULE_PACKAGE_MISSING],
            strategy=resolved_strategy,
            anchor_utc=anchor_utc,
        )

    schedule_idempotency_key = build_schedule_idempotency_key(
        campaign_id=campaign["campaign_id"],
        source_content_sha256=source_content_sha256,
        package_idempotency_key=package["idempotency_key"],
        variant_ids=variant_ids,
        strategy=resolved_strategy,
        anchor_utc=anchor_utc,
        flow=FLOW_A,
    )

    if state == STATE_DISTRIBUTION_SCHEDULED:
        if _check_idempotent_completed(
            campaign,
            expected_schedule_key=schedule_idempotency_key,
            anchor_utc=anchor_utc,
            variant_ids=variant_ids,
        ):
            metadata_map = _get_variant_metadata_map(campaign)
            variant_schedules = [
                _variant_schedule_summary(metadata_map[variant_id])
                for variant_id in _ordered_variant_ids(variant_ids)
            ]
            return _completed_result(
                campaign,
                strategy=resolved_strategy,
                anchor_utc=anchor_utc,
                variant_schedules=variant_schedules,
                metadata_written=False,
            )
        return _failed_result(
            campaign=campaign,
            errors=[LINKEDIN_SCHEDULE_METADATA_MISMATCH],
            strategy=resolved_strategy,
            anchor_utc=anchor_utc,
        )

    verified_entries, verify_error = _verify_artifacts(
        base_path, campaign, variant_ids=variant_ids
    )
    if verify_error:
        return _failed_result(
            campaign=campaign,
            errors=[verify_error],
            strategy=resolved_strategy,
            anchor_utc=anchor_utc,
        )

    schedule_times = _compute_staggered_schedules(variant_ids, anchor_utc)
    working_campaign = deepcopy(campaign)
    working_metadata_map = _get_variant_metadata_map(working_campaign)
    updated_entries: list[dict[str, Any]] = []

    for variant_id in _ordered_variant_ids(variant_ids):
        entry = dict(working_metadata_map[variant_id])
        scheduled_at = schedule_times[variant_id]
        derivative_hash = entry["derivative_content_sha256"]
        entry["scheduled_at_utc"] = scheduled_at
        entry["publish_state"] = PUBLISH_STATE_PENDING
        entry["schedule_idempotency_key"] = build_variant_schedule_idempotency_key(
            campaign_id=working_campaign["campaign_id"],
            variant=variant_id,
            derivative_content_sha256=derivative_hash,
            scheduled_at_utc=scheduled_at,
            flow=FLOW_A,
        )
        working_metadata_map[variant_id] = entry
        updated_entries.append(entry)

    working_campaign["variants"] = list(working_metadata_map.values())
    working_campaign["linkedin_distribution"] = {
        "distribution_id": _distribution_id(working_campaign["campaign_id"]),
        "idempotency_key": schedule_idempotency_key,
        "strategy": resolved_strategy,
        "anchor_utc": anchor_utc,
        "variant_ids": variant_ids,
    }

    history_len_before = len(working_campaign.get("state_history") or [])
    try:
        transition_state(
            working_campaign,
            STATE_DISTRIBUTION_SCHEDULED,
            reason="LinkedIn distribution scheduled",
            actor=ACTOR_WORKER,
        )
    except Exception:
        return _failed_result(
            campaign=working_campaign,
            errors=[LINKEDIN_SCHEDULE_INVALID_CAMPAIGN_STATE],
            strategy=resolved_strategy,
            anchor_utc=anchor_utc,
            variant_schedules=[_variant_schedule_summary(entry) for entry in updated_entries],
            distribution=working_campaign.get("linkedin_distribution"),
        )

    if len(working_campaign.get("state_history") or []) <= history_len_before:
        return _failed_result(
            campaign=working_campaign,
            errors=[LINKEDIN_SCHEDULE_INVALID_CAMPAIGN_STATE],
            strategy=resolved_strategy,
            anchor_utc=anchor_utc,
            variant_schedules=[_variant_schedule_summary(entry) for entry in updated_entries],
            distribution=working_campaign.get("linkedin_distribution"),
        )

    write_result = write_campaign_metadata(
        base_path, working_campaign["campaign_id"], working_campaign
    )
    if not write_result.written:
        return _failed_result(
            campaign=working_campaign,
            errors=[LINKEDIN_SCHEDULE_METADATA_WRITE_FAILED],
            strategy=resolved_strategy,
            anchor_utc=anchor_utc,
            variant_schedules=[_variant_schedule_summary(entry) for entry in updated_entries],
            distribution=working_campaign.get("linkedin_distribution"),
            metadata_written=False,
            metadata_error_code=write_result.error_code
            or LINKEDIN_SCHEDULE_METADATA_WRITE_FAILED,
        )

    return _completed_result(
        working_campaign,
        strategy=resolved_strategy,
        anchor_utc=anchor_utc,
        variant_schedules=[_variant_schedule_summary(entry) for entry in updated_entries],
        metadata_written=True,
    )
