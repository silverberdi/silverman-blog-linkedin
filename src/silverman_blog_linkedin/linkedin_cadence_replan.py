"""US-089: replan already-scheduled LinkedIn variants with cadence conflict.

Selects not-yet-Live ``pending`` / ``queued`` variants that are cadence-infeasible
at their current ``scheduled_at_utc`` (US-051 / US-087 meaning) and shifts them
forward via shared US-088 ``find_feasible_slot_forward``. Does not invent a
second 72h engine, call LinkedIn API publish, or mutate enablement.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from silverman_blog_linkedin.campaign_lifecycle import (
    CAMPAIGN_METADATA_CONCURRENT_UPDATE,
    METADATA_CAMPAIGNS_RELATIVE,
    campaign_metadata_content_fingerprint,
    normalize_scheduled_at_utc,
    read_campaign_metadata,
    write_campaign_metadata_cas,
)
from silverman_blog_linkedin.linkedin_publication_flow import (
    LINKEDIN_PUBLISH_METADATA_WRITE_FAILED,
    LINKEDIN_PUBLISH_VARIANT_NOT_FOUND,
    PUBLISH_STATE_PENDING,
    PUBLISH_STATE_QUEUED,
    _get_variant_metadata_map,
    _parse_utc,
)
from silverman_blog_linkedin.linkedin_schedule_feasibility import (
    LINKEDIN_SCHEDULE_NO_FEASIBLE_SLOT,
    find_feasible_slot_forward,
    is_cadence_conflicted_at,
    resolve_schedule_operator_timezone,
)
from silverman_blog_linkedin.linkedin_supervision_flow import (
    SUPERVISION_ACTOR_OPERATOR,
    SUPERVISION_PHASE_POST_QUEUE,
    SUPERVISION_PHASE_PRE_QUEUE,
    _get_or_init_operator_supervision,
)
from silverman_blog_linkedin.local_day_density import local_day_key_for_utc
from silverman_blog_linkedin.run_metadata import utc_now_iso

# Re-export for callers / tests (single cadence engine).
__all__ = [
    "LINKEDIN_SCHEDULE_NO_FEASIBLE_SLOT",
    "LINKEDIN_REPLAN_TARGET_INVALID",
    "SUPERVISION_ACTION_REPLAN_CADENCE",
    "LinkedInCadenceReplanResult",
    "ReplanTargetPlan",
    "replan_linkedin_cadence_conflicts",
]

LINKEDIN_REPLAN_TARGET_INVALID = "linkedin_replan_target_invalid"
SUPERVISION_ACTION_REPLAN_CADENCE = "replan_cadence"

_REPLAN_ELIGIBLE_STATES = frozenset({PUBLISH_STATE_PENDING, PUBLISH_STATE_QUEUED})

# Outcome labels for structured preview / apply rows.
OUTCOME_MOVED = "moved"
OUTCOME_UNCHANGED = "unchanged"
OUTCOME_SKIPPED_NOT_CONFLICTED = "skipped_not_conflicted"
OUTCOME_FAILED = "failed"


@dataclass
class ReplanTargetPlan:
    campaign_id: str
    variant_id: str
    publish_state: str | None = None
    previous_scheduled_at_utc: str | None = None
    proposed_scheduled_at_utc: str | None = None
    outcome: str = OUTCOME_FAILED
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LinkedInCadenceReplanResult:
    status: str
    dry_run: bool = True
    metadata_written: bool = False
    targets: list[ReplanTargetPlan] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    campaigns_written: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "dry_run": self.dry_run,
            "metadata_written": self.metadata_written,
            "targets": [t.to_dict() for t in self.targets],
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "campaigns_written": list(self.campaigns_written),
        }


@dataclass(frozen=True)
class _CandidateRef:
    campaign_id: str
    variant_id: str
    publish_state: str
    scheduled_at_utc: str
    scheduled_dt: datetime


def _list_campaign_ids(base_path: Path) -> list[str]:
    campaigns_dir = base_path / METADATA_CAMPAIGNS_RELATIVE
    if not campaigns_dir.is_dir():
        return []
    return sorted(path.stem for path in campaigns_dir.glob("*.json"))


def _variant_id(entry: dict[str, Any]) -> str | None:
    raw = entry.get("variant")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _parse_scheduled(entry: dict[str, Any]) -> tuple[str, datetime] | None:
    raw = entry.get("scheduled_at_utc")
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        normalized = normalize_scheduled_at_utc(raw)
        return normalized, _parse_utc(normalized)
    except (ValueError, TypeError):
        return None


def _is_cadence_conflict_target(
    campaign: dict[str, Any], scheduled_dt: datetime
) -> bool:
    """US-051 / US-087 selection gate — cadence only (not density/OAuth/enablement)."""
    return is_cadence_conflicted_at(campaign, evaluation_at=scheduled_dt)


def _collect_eligible_conflicts(
    base_path: Path,
    *,
    campaign_id: str | None,
    targets: list[tuple[str, str]] | None,
) -> tuple[list[_CandidateRef], list[ReplanTargetPlan], dict[str, dict[str, Any]]]:
    """Return ordered conflict candidates, skip rows, and loaded campaigns cache.

    Deterministic scan order when filters omitted: campaign id ascending, then
    variant order as stored. Processing order for placement is applied later
    (earliest scheduled_at_utc, campaign_id, variant_id).
    """
    campaigns_cache: dict[str, dict[str, Any]] = {}
    skip_rows: list[ReplanTargetPlan] = []
    candidates: list[_CandidateRef] = []

    if targets:
        # Explicit targets: evaluate each; non-conflicts become skip rows.
        seen: set[tuple[str, str]] = set()
        ordered_targets: list[tuple[str, str]] = []
        for cid, vid in targets:
            key = (cid, vid)
            if key in seen:
                continue
            seen.add(key)
            ordered_targets.append(key)

        for cid, vid in ordered_targets:
            if cid not in campaigns_cache:
                loaded = read_campaign_metadata(base_path, cid)
                if loaded is None:
                    skip_rows.append(
                        ReplanTargetPlan(
                            campaign_id=cid,
                            variant_id=vid,
                            outcome=OUTCOME_FAILED,
                            errors=[LINKEDIN_PUBLISH_VARIANT_NOT_FOUND],
                        )
                    )
                    continue
                campaigns_cache[cid] = loaded
            campaign = campaigns_cache[cid]
            metadata_map = _get_variant_metadata_map(campaign)
            entry = metadata_map.get(vid)
            if entry is None:
                skip_rows.append(
                    ReplanTargetPlan(
                        campaign_id=cid,
                        variant_id=vid,
                        outcome=OUTCOME_FAILED,
                        errors=[LINKEDIN_PUBLISH_VARIANT_NOT_FOUND],
                    )
                )
                continue
            publish_state = entry.get("publish_state")
            if publish_state not in _REPLAN_ELIGIBLE_STATES:
                skip_rows.append(
                    ReplanTargetPlan(
                        campaign_id=cid,
                        variant_id=vid,
                        publish_state=publish_state
                        if isinstance(publish_state, str)
                        else None,
                        outcome=OUTCOME_SKIPPED_NOT_CONFLICTED,
                        errors=[LINKEDIN_REPLAN_TARGET_INVALID],
                    )
                )
                continue
            parsed = _parse_scheduled(entry)
            if parsed is None:
                skip_rows.append(
                    ReplanTargetPlan(
                        campaign_id=cid,
                        variant_id=vid,
                        publish_state=str(publish_state),
                        outcome=OUTCOME_SKIPPED_NOT_CONFLICTED,
                        errors=[LINKEDIN_REPLAN_TARGET_INVALID],
                    )
                )
                continue
            normalized, scheduled_dt = parsed
            if not _is_cadence_conflict_target(campaign, scheduled_dt):
                skip_rows.append(
                    ReplanTargetPlan(
                        campaign_id=cid,
                        variant_id=vid,
                        publish_state=str(publish_state),
                        previous_scheduled_at_utc=normalized,
                        proposed_scheduled_at_utc=normalized,
                        outcome=OUTCOME_SKIPPED_NOT_CONFLICTED,
                    )
                )
                continue
            candidates.append(
                _CandidateRef(
                    campaign_id=cid,
                    variant_id=vid,
                    publish_state=str(publish_state),
                    scheduled_at_utc=normalized,
                    scheduled_dt=scheduled_dt,
                )
            )
        return candidates, skip_rows, campaigns_cache

    # Scan mode: optional campaign_id filter; only cadence-conflicted eligible.
    campaign_ids = (
        [campaign_id] if campaign_id else _list_campaign_ids(base_path)
    )
    for cid in campaign_ids:
        loaded = read_campaign_metadata(base_path, cid)
        if loaded is None:
            continue
        campaigns_cache[cid] = loaded
        for entry in loaded.get("variants") or []:
            if not isinstance(entry, dict):
                continue
            vid = _variant_id(entry)
            if vid is None:
                continue
            publish_state = entry.get("publish_state")
            if publish_state not in _REPLAN_ELIGIBLE_STATES:
                continue
            parsed = _parse_scheduled(entry)
            if parsed is None:
                continue
            normalized, scheduled_dt = parsed
            if not _is_cadence_conflict_target(loaded, scheduled_dt):
                continue
            candidates.append(
                _CandidateRef(
                    campaign_id=cid,
                    variant_id=vid,
                    publish_state=str(publish_state),
                    scheduled_at_utc=normalized,
                    scheduled_dt=scheduled_dt,
                )
            )

    return candidates, skip_rows, campaigns_cache


def _placement_sort_key(ref: _CandidateRef) -> tuple[datetime, str, str]:
    return (ref.scheduled_dt, ref.campaign_id, ref.variant_id)


def _default_clock_for_slot(
    scheduled_dt: datetime, operator_timezone: str
) -> tuple[int, int]:
    try:
        tz = ZoneInfo(operator_timezone)
    except (ZoneInfoNotFoundError, ValueError, TypeError, KeyError):
        return 8, 0
    local = scheduled_dt.astimezone(tz)
    return local.hour, local.minute


def _compute_plan(
    base_path: Path,
    candidates: list[_CandidateRef],
    campaigns_cache: dict[str, dict[str, Any]],
    *,
    operator_timezone: str,
    environ: dict[str, str] | None,
) -> tuple[list[ReplanTargetPlan], bool]:
    """Shift-forward each selected target; share density planned_counts across batch.

    Returns (plan rows for selected candidates, all_feasible).
    """
    planned_counts: dict[str, int] = {}
    plan_rows: list[ReplanTargetPlan] = []
    all_feasible = True

    try:
        tz = ZoneInfo(operator_timezone)
    except (ZoneInfoNotFoundError, ValueError, TypeError, KeyError):
        for ref in candidates:
            plan_rows.append(
                ReplanTargetPlan(
                    campaign_id=ref.campaign_id,
                    variant_id=ref.variant_id,
                    publish_state=ref.publish_state,
                    previous_scheduled_at_utc=ref.scheduled_at_utc,
                    outcome=OUTCOME_FAILED,
                    errors=[LINKEDIN_SCHEDULE_NO_FEASIBLE_SLOT],
                )
            )
        return plan_rows, False

    for ref in sorted(candidates, key=_placement_sort_key):
        campaign = campaigns_cache[ref.campaign_id]
        default_hour, default_minute = _default_clock_for_slot(
            ref.scheduled_dt, operator_timezone
        )
        chosen = find_feasible_slot_forward(
            base_path,
            campaign,
            preferred_utc=ref.scheduled_dt,
            operator_timezone=operator_timezone,
            campaign_id=ref.campaign_id,
            planned_counts=planned_counts,
            previous_accepted_utc=None,
            enforce_stagger=False,
            default_hour=default_hour,
            default_minute=default_minute,
            environ=environ,
        )
        if chosen is None:
            all_feasible = False
            plan_rows.append(
                ReplanTargetPlan(
                    campaign_id=ref.campaign_id,
                    variant_id=ref.variant_id,
                    publish_state=ref.publish_state,
                    previous_scheduled_at_utc=ref.scheduled_at_utc,
                    outcome=OUTCOME_FAILED,
                    errors=[LINKEDIN_SCHEDULE_NO_FEASIBLE_SLOT],
                )
            )
            continue

        proposed = chosen.strftime("%Y-%m-%dT%H:%M:%SZ")
        # Race: preferred became feasible → leave unchanged (do not invent a later move).
        if proposed == ref.scheduled_at_utc:
            plan_rows.append(
                ReplanTargetPlan(
                    campaign_id=ref.campaign_id,
                    variant_id=ref.variant_id,
                    publish_state=ref.publish_state,
                    previous_scheduled_at_utc=ref.scheduled_at_utc,
                    proposed_scheduled_at_utc=proposed,
                    outcome=OUTCOME_UNCHANGED,
                )
            )
            day_key = local_day_key_for_utc(chosen, tz)
            planned_counts[day_key] = planned_counts.get(day_key, 0) + 1
            continue

        # Occupy density for later targets in this batch.
        day_key = local_day_key_for_utc(chosen, tz)
        planned_counts[day_key] = planned_counts.get(day_key, 0) + 1
        plan_rows.append(
            ReplanTargetPlan(
                campaign_id=ref.campaign_id,
                variant_id=ref.variant_id,
                publish_state=ref.publish_state,
                previous_scheduled_at_utc=ref.scheduled_at_utc,
                proposed_scheduled_at_utc=proposed,
                outcome=OUTCOME_MOVED,
            )
        )

    return plan_rows, all_feasible


def _apply_entry_replan(
    entry: dict[str, Any],
    *,
    new_scheduled_at_utc: str,
    actor: str,
    source: str | None,
    reason: str | None,
    replanned_at: str,
) -> dict[str, Any]:
    """Mirror US-084 defer schedule-field semantics for pending vs queued."""
    publish_state = entry.get("publish_state")
    is_queued = publish_state == PUBLISH_STATE_QUEUED
    previous = entry.get("scheduled_at_utc")
    previous_normalized = (
        normalize_scheduled_at_utc(previous)
        if isinstance(previous, str) and previous.strip()
        else None
    )

    supervision = _get_or_init_operator_supervision(entry)
    history = supervision.get("deferral_history")
    if not isinstance(history, list):
        history = []
    record: dict[str, Any] = {
        "action": SUPERVISION_ACTION_REPLAN_CADENCE,
        "replanned_at_utc": replanned_at,
        "previous_scheduled_at_utc": previous_normalized,
        "new_scheduled_at_utc": new_scheduled_at_utc,
        "actor": actor,
    }
    if reason:
        record["reason"] = reason
    if isinstance(source, str) and source.strip():
        record["source"] = source.strip()
    history.append(record)
    supervision["deferral_history"] = history
    supervision["last_action"] = SUPERVISION_ACTION_REPLAN_CADENCE
    supervision["last_action_at_utc"] = replanned_at
    if is_queued:
        supervision["phase"] = SUPERVISION_PHASE_POST_QUEUE
    else:
        supervision["phase"] = SUPERVISION_PHASE_PRE_QUEUE
        supervision["auto_queue_eligible"] = False
    supervision["actor"] = actor
    if isinstance(source, str) and source.strip():
        supervision["source"] = source.strip()
    if reason:
        supervision["reason"] = reason

    updated = dict(entry)
    updated["scheduled_at_utc"] = new_scheduled_at_utc
    if is_queued:
        updated["publish_after_utc"] = new_scheduled_at_utc
        updated["publish_state"] = PUBLISH_STATE_QUEUED
    updated["operator_supervision"] = supervision
    return updated


def _apply_real_plan(
    base_path: Path,
    move_rows: list[ReplanTargetPlan],
    *,
    actor: str,
    source: str | None,
    reason: str | None,
) -> tuple[bool, list[str], list[str]]:
    """Apply all-or-nothing-validated moves per campaign with CAS.

    Plan must already be fully feasible. Returns (ok, errors, campaigns_written).
    """
    by_campaign: dict[str, list[ReplanTargetPlan]] = {}
    for row in move_rows:
        if row.outcome != OUTCOME_MOVED or not row.proposed_scheduled_at_utc:
            continue
        by_campaign.setdefault(row.campaign_id, []).append(row)

    if not by_campaign:
        return True, [], []

    campaigns_written: list[str] = []
    errors: list[str] = []
    replanned_at = utc_now_iso()

    for cid in sorted(by_campaign.keys()):
        rows = by_campaign[cid]
        expected_fp = campaign_metadata_content_fingerprint(base_path, cid)
        campaign = read_campaign_metadata(base_path, cid)
        if campaign is None:
            errors.append(LINKEDIN_PUBLISH_VARIANT_NOT_FOUND)
            break

        working = deepcopy(campaign)
        metadata_map = _get_variant_metadata_map(working)
        for row in rows:
            entry = metadata_map.get(row.variant_id)
            if entry is None:
                errors.append(LINKEDIN_PUBLISH_VARIANT_NOT_FOUND)
                break
            # Re-check cadence eligibility at apply (race / concurrent publish).
            parsed = _parse_scheduled(entry)
            if parsed is None:
                errors.append(LINKEDIN_REPLAN_TARGET_INVALID)
                break
            _normalized, scheduled_dt = parsed
            if not _is_cadence_conflict_target(working, scheduled_dt):
                # Race: no longer conflicted — leave unchanged for this target.
                continue
            assert row.proposed_scheduled_at_utc is not None
            metadata_map[row.variant_id] = _apply_entry_replan(
                entry,
                new_scheduled_at_utc=row.proposed_scheduled_at_utc,
                actor=actor,
                source=source,
                reason=reason,
                replanned_at=replanned_at,
            )
        else:
            working["variants"] = list(metadata_map.values())
            write_result = write_campaign_metadata_cas(
                base_path,
                cid,
                working,
                expected_fingerprint=expected_fp,
            )
            if not write_result.written:
                code = write_result.error_code or LINKEDIN_PUBLISH_METADATA_WRITE_FAILED
                if code == CAMPAIGN_METADATA_CONCURRENT_UPDATE:
                    errors.append(CAMPAIGN_METADATA_CONCURRENT_UPDATE)
                else:
                    errors.append(LINKEDIN_PUBLISH_METADATA_WRITE_FAILED)
                break
            campaigns_written.append(cid)
            continue
        break

    return (len(errors) == 0), errors, campaigns_written


def replan_linkedin_cadence_conflicts(
    base_path: Path,
    *,
    dry_run: bool = True,
    campaign_id: str | None = None,
    targets: list[dict[str, str]] | None = None,
    operator_timezone: str | None = None,
    actor: str | None = None,
    source: str | None = None,
    reason: str | None = None,
    environ: dict[str, str] | None = None,
) -> LinkedInCadenceReplanResult:
    """Select cadence-conflicted pending/queued variants and shift forward (US-089).

    ``dry_run`` defaults to True (preview; zero metadata mutation). Real apply
    requires ``dry_run=False`` and a fully feasible plan (all-or-nothing).
    """
    resolved_actor = (
        actor.strip()
        if isinstance(actor, str) and actor.strip()
        else SUPERVISION_ACTOR_OPERATOR
    )
    tz_name = resolve_schedule_operator_timezone(
        operator_timezone=operator_timezone, environ=environ
    )

    normalized_targets: list[tuple[str, str]] | None = None
    if targets is not None:
        normalized_targets = []
        for item in targets:
            if not isinstance(item, dict):
                return LinkedInCadenceReplanResult(
                    status="failed",
                    dry_run=dry_run,
                    errors=[LINKEDIN_REPLAN_TARGET_INVALID],
                )
            cid = item.get("campaign_id")
            vid = item.get("variant_id")
            if not isinstance(cid, str) or not cid.strip():
                return LinkedInCadenceReplanResult(
                    status="failed",
                    dry_run=dry_run,
                    errors=[LINKEDIN_REPLAN_TARGET_INVALID],
                )
            if not isinstance(vid, str) or not vid.strip():
                return LinkedInCadenceReplanResult(
                    status="failed",
                    dry_run=dry_run,
                    errors=[LINKEDIN_REPLAN_TARGET_INVALID],
                )
            normalized_targets.append((cid.strip(), vid.strip()))

    if campaign_id is not None:
        campaign_id = campaign_id.strip() or None

    candidates, skip_rows, campaigns_cache = _collect_eligible_conflicts(
        base_path,
        campaign_id=campaign_id,
        targets=normalized_targets,
    )

    # Explicit-target hard failures (not found) fail the request.
    hard_skips = [r for r in skip_rows if r.outcome == OUTCOME_FAILED]
    if hard_skips and normalized_targets is not None:
        return LinkedInCadenceReplanResult(
            status="failed",
            dry_run=dry_run,
            targets=skip_rows,
            errors=[err for r in hard_skips for err in r.errors],
        )

    plan_rows, all_feasible = _compute_plan(
        base_path,
        candidates,
        campaigns_cache,
        operator_timezone=tz_name,
        environ=environ,
    )
    all_targets = list(skip_rows) + plan_rows

    if candidates and not all_feasible:
        # Fail closed: preview still returns per-target errors; no mutation.
        top_errors = [LINKEDIN_SCHEDULE_NO_FEASIBLE_SLOT]
        return LinkedInCadenceReplanResult(
            status="failed",
            dry_run=dry_run,
            metadata_written=False,
            targets=all_targets,
            errors=top_errors,
        )

    if dry_run:
        return LinkedInCadenceReplanResult(
            status="completed",
            dry_run=True,
            metadata_written=False,
            targets=all_targets,
        )

    # Real apply: only persist moved rows; unchanged/skipped stay put.
    ok, apply_errors, campaigns_written = _apply_real_plan(
        base_path,
        plan_rows,
        actor=resolved_actor,
        source=source,
        reason=reason,
    )
    if not ok:
        return LinkedInCadenceReplanResult(
            status="failed",
            dry_run=False,
            metadata_written=bool(campaigns_written),
            targets=all_targets,
            errors=apply_errors,
            campaigns_written=campaigns_written,
        )

    return LinkedInCadenceReplanResult(
        status="completed",
        dry_run=False,
        metadata_written=bool(campaigns_written),
        targets=all_targets,
        campaigns_written=campaigns_written,
    )
