"""US-088: cadence-aware schedule-time feasibility and shift-forward.

Reuses US-020 / US-087 ``CADENCE_MINIMUM_INTERVAL`` / ``project_cadence_conflict_at``
(published-evidence only). Combines cadence with US-040K density and strategy
invariants. Does not call LinkedIn API publish or mutate enablement.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from silverman_blog_linkedin.local_day_density import (
    MAX_DENSITY_MEMBERS_PER_LOCAL_DAY,
    evaluate_local_day_density,
    local_day_key_for_utc,
    resolve_operator_timezone,
)
from silverman_blog_linkedin.linkedin_publication_flow import (
    CADENCE_MINIMUM_INTERVAL,
    project_cadence_conflict_at,
)

# Re-export so schedule callers share one cadence constant (no second engine).
__all__ = [
    "CADENCE_MINIMUM_INTERVAL",
    "LINKEDIN_SCHEDULE_NO_FEASIBLE_SLOT",
    "SHIFT_FORWARD_HORIZON_LOCAL_DAYS",
    "STAGGER_MIN_CALENDAR_DAYS",
    "SlotFeasibility",
    "compute_staggered_schedules_cadence_aware",
    "find_feasible_slot_forward",
    "is_cadence_conflicted_at",
    "iter_shift_forward_candidate_instants",
    "resolve_schedule_operator_timezone",
    "slot_has_density_capacity",
]

LINKEDIN_SCHEDULE_NO_FEASIBLE_SLOT = "linkedin_schedule_no_feasible_slot"

# US-052 default: original candidate local day = day 0; search days 0…28 inclusive.
SHIFT_FORWARD_HORIZON_LOCAL_DAYS = 28

# flow_a_staggered: minimum calendar days between consecutive accepted variants.
STAGGER_MIN_CALENDAR_DAYS = 3

# US-052 preferred local days (Tue–Thu) and window starts (America/Bogota).
PREFERRED_LOCAL_WEEKDAYS = frozenset({1, 2, 3})
PREFERRED_WINDOW_CLOCKS: tuple[tuple[int, int], ...] = ((8, 0), (16, 0))

# Placement default when operator TZ is unset (US-052 SoT).
DEFAULT_SCHEDULE_OPERATOR_TIMEZONE = "America/Bogota"


@dataclass(frozen=True)
class SlotFeasibility:
    """Outcome of a single candidate slot check."""

    feasible: bool
    cadence_conflict: bool
    density_ok: bool
    strategy_ok: bool


def resolve_schedule_operator_timezone(
    *,
    operator_timezone: str | None = None,
    environ: dict[str, str] | None = None,
) -> str:
    """Resolve operator TZ for schedule-time density / horizon.

    Prefer request/env (US-040K), then America/Bogota (US-052). Never invent a
    second timezone SoT for preferred windows.
    """
    resolved, _errors = resolve_operator_timezone(
        operator_timezone, environ=environ
    )
    if resolved:
        return resolved
    try:
        from silverman_blog_linkedin.flow_b_gap_operator_settings import (
            SETTINGS_KEY_OPERATOR_TIMEZONE,
            load_gap_operator_settings,
        )

        snapshot = load_gap_operator_settings()
        tz = snapshot.settings.get(SETTINGS_KEY_OPERATOR_TIMEZONE)
        if isinstance(tz, str) and tz.strip():
            ZoneInfo(tz.strip())
            return tz.strip()
    except Exception:
        pass
    return DEFAULT_SCHEDULE_OPERATOR_TIMEZONE


def is_cadence_conflicted_at(
    campaign: dict[str, Any],
    *,
    evaluation_at: datetime,
) -> bool:
    """True when US-020 / US-087 cadence gate would refuse at ``evaluation_at``."""
    if evaluation_at.tzinfo is None:
        evaluation_at = evaluation_at.replace(tzinfo=timezone.utc)
    else:
        evaluation_at = evaluation_at.astimezone(timezone.utc)
    projection = project_cadence_conflict_at(
        campaign, evaluation_at=evaluation_at
    )
    return bool(projection.cadence_conflict)


def slot_has_density_capacity(
    base_path: Path,
    *,
    candidate_utc: datetime,
    operator_timezone: str,
    campaign_id: str | None,
    planned_counts: dict[str, int],
    density_ceiling: int = MAX_DENSITY_MEMBERS_PER_LOCAL_DAY,
    environ: dict[str, str] | None = None,
) -> bool:
    """True when accepting ``candidate_utc`` stays under US-040K max 2 (+ batch)."""
    if candidate_utc.tzinfo is None:
        candidate_utc = candidate_utc.replace(tzinfo=timezone.utc)
    else:
        candidate_utc = candidate_utc.astimezone(timezone.utc)

    try:
        tz = ZoneInfo(operator_timezone)
    except (ZoneInfoNotFoundError, ValueError, TypeError, KeyError):
        return False

    day_key = local_day_key_for_utc(candidate_utc, tz)
    result = evaluate_local_day_density(
        base_path,
        target_utc=candidate_utc,
        operator_timezone=operator_timezone,
        exclude_campaign_id=campaign_id,
        exclude_variant=None,
        environ=environ,
    )
    if not result.ok:
        # Fail closed on TZ/density eval errors (treat as no capacity).
        if result.others_on_day >= density_ceiling:
            return False
        # ok=False with others < ceiling usually means TZ/config error.
        if result.errors:
            return False

    occupied = result.others_on_day + planned_counts.get(day_key, 0)
    return occupied < density_ceiling


def _local_date_for_utc(dt_utc: datetime, tz: ZoneInfo) -> date:
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    return dt_utc.astimezone(tz).date()


def stagger_spacing_ok(
    *,
    candidate_utc: datetime,
    previous_accepted_utc: datetime | None,
    operator_timezone: str,
    min_calendar_days: int = STAGGER_MIN_CALENDAR_DAYS,
) -> bool:
    """Require ≥ ``min_calendar_days`` between consecutive accepted local days."""
    if previous_accepted_utc is None:
        return True
    try:
        tz = ZoneInfo(operator_timezone)
    except (ZoneInfoNotFoundError, ValueError, TypeError, KeyError):
        return False
    prev_day = _local_date_for_utc(previous_accepted_utc, tz)
    cand_day = _local_date_for_utc(candidate_utc, tz)
    return (cand_day - prev_day).days >= min_calendar_days


def evaluate_slot_feasibility(
    base_path: Path,
    campaign: dict[str, Any],
    *,
    candidate_utc: datetime,
    operator_timezone: str,
    campaign_id: str | None,
    planned_counts: dict[str, int],
    previous_accepted_utc: datetime | None = None,
    enforce_stagger: bool = False,
    density_ceiling: int = MAX_DENSITY_MEMBERS_PER_LOCAL_DAY,
    environ: dict[str, str] | None = None,
) -> SlotFeasibility:
    """Combine cadence + density + optional stagger for one candidate instant."""
    cadence_conflict = is_cadence_conflicted_at(
        campaign, evaluation_at=candidate_utc
    )
    density_ok = slot_has_density_capacity(
        base_path,
        candidate_utc=candidate_utc,
        operator_timezone=operator_timezone,
        campaign_id=campaign_id,
        planned_counts=planned_counts,
        density_ceiling=density_ceiling,
        environ=environ,
    )
    strategy_ok = True
    if enforce_stagger:
        strategy_ok = stagger_spacing_ok(
            candidate_utc=candidate_utc,
            previous_accepted_utc=previous_accepted_utc,
            operator_timezone=operator_timezone,
        )
    feasible = (not cadence_conflict) and density_ok and strategy_ok
    return SlotFeasibility(
        feasible=feasible,
        cadence_conflict=cadence_conflict,
        density_ok=density_ok,
        strategy_ok=strategy_ok,
    )


def iter_shift_forward_candidate_instants(
    *,
    origin_utc: datetime,
    operator_timezone: str,
    default_hour: int,
    default_minute: int,
    horizon_local_days: int = SHIFT_FORWARD_HORIZON_LOCAL_DAYS,
) -> Iterator[datetime]:
    """Yield deterministic forward candidates within the US-052 horizon.

    Day 0 = origin's operator-local calendar day. Prefer US-052 windows on
    Tue–Thu (08:00 then 16:00); non-preferred days use one default clock.
    Never yields instants strictly before ``origin_utc``.
    """
    if origin_utc.tzinfo is None:
        origin_utc = origin_utc.replace(tzinfo=timezone.utc)
    else:
        origin_utc = origin_utc.astimezone(timezone.utc)

    tz = ZoneInfo(operator_timezone)
    origin_local = origin_utc.astimezone(tz)
    origin_day = origin_local.date()

    for day_offset in range(0, horizon_local_days + 1):
        day = origin_day + timedelta(days=day_offset)
        if day.weekday() in PREFERRED_LOCAL_WEEKDAYS:
            clocks = list(PREFERRED_WINDOW_CLOCKS)
            # Keep strategy default clock when it already sits in a preferred window.
            default_in_morning = 8 <= default_hour < 10
            default_in_afternoon = 16 <= default_hour < 18
            if (default_in_morning or default_in_afternoon) and (
                default_hour,
                default_minute,
            ) not in clocks:
                clocks.append((default_hour, default_minute))
                clocks.sort()
        else:
            clocks = [(default_hour, default_minute)]

        for hour, minute in clocks:
            local_dt = datetime(
                day.year, day.month, day.day, hour, minute, 0, tzinfo=tz
            )
            candidate = local_dt.astimezone(timezone.utc)
            if candidate < origin_utc:
                continue
            yield candidate


def find_feasible_slot_forward(
    base_path: Path,
    campaign: dict[str, Any],
    *,
    preferred_utc: datetime,
    operator_timezone: str,
    campaign_id: str | None,
    planned_counts: dict[str, int],
    previous_accepted_utc: datetime | None = None,
    enforce_stagger: bool = False,
    default_hour: int,
    default_minute: int,
    density_ceiling: int = MAX_DENSITY_MEMBERS_PER_LOCAL_DAY,
    environ: dict[str, str] | None = None,
    horizon_local_days: int = SHIFT_FORWARD_HORIZON_LOCAL_DAYS,
) -> datetime | None:
    """Return first feasible slot at/after preferred, or None if horizon exhausted.

    If ``preferred_utc`` itself is feasible, it is returned unchanged (no
    unnecessary shift). Otherwise scan forward preferring US-052 windows.
    """
    if preferred_utc.tzinfo is None:
        preferred_utc = preferred_utc.replace(tzinfo=timezone.utc)
    else:
        preferred_utc = preferred_utc.astimezone(timezone.utc)

    preferred_check = evaluate_slot_feasibility(
        base_path,
        campaign,
        candidate_utc=preferred_utc,
        operator_timezone=operator_timezone,
        campaign_id=campaign_id,
        planned_counts=planned_counts,
        previous_accepted_utc=previous_accepted_utc,
        enforce_stagger=enforce_stagger,
        density_ceiling=density_ceiling,
        environ=environ,
    )
    if preferred_check.feasible:
        return preferred_utc

    # Horizon day 0 = original preferred local day (US-052).
    for candidate in iter_shift_forward_candidate_instants(
        origin_utc=preferred_utc,
        operator_timezone=operator_timezone,
        default_hour=default_hour,
        default_minute=default_minute,
        horizon_local_days=horizon_local_days,
    ):
        if candidate == preferred_utc:
            continue
        check = evaluate_slot_feasibility(
            base_path,
            campaign,
            candidate_utc=candidate,
            operator_timezone=operator_timezone,
            campaign_id=campaign_id,
            planned_counts=planned_counts,
            previous_accepted_utc=previous_accepted_utc,
            enforce_stagger=enforce_stagger,
            density_ceiling=density_ceiling,
            environ=environ,
        )
        if check.feasible:
            return candidate
    return None


def compute_staggered_schedules_cadence_aware(
    base_path: Path,
    campaign: dict[str, Any],
    *,
    variant_ids: list[str],
    anchor_utc: str,
    variant_day_offsets: dict[str, int],
    ordered_variant_ids: list[str],
    campaign_id: str | None = None,
    operator_timezone: str | None = None,
    environ: dict[str, str] | None = None,
    density_ceiling: int = MAX_DENSITY_MEMBERS_PER_LOCAL_DAY,
) -> tuple[dict[str, str] | None, str | None]:
    """Place ``flow_a_staggered`` variants with cadence-aware shift-forward.

    Returns ``(schedules, error_code)``. On horizon exhaustion returns
    ``linkedin_schedule_no_feasible_slot``.
    """
    tz_name = resolve_schedule_operator_timezone(
        operator_timezone=operator_timezone, environ=environ
    )
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError, TypeError, KeyError):
        return None, LINKEDIN_SCHEDULE_NO_FEASIBLE_SLOT

    try:
        anchor = datetime.strptime(anchor_utc, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None, LINKEDIN_SCHEDULE_NO_FEASIBLE_SLOT

    local_anchor = anchor.astimezone(tz)
    default_hour = local_anchor.hour
    default_minute = local_anchor.minute
    planned: dict[str, int] = {}
    schedules: dict[str, str] = {}
    previous_accepted: datetime | None = None

    for variant_id in ordered_variant_ids:
        day_offset = variant_day_offsets[variant_id]
        preferred = anchor + timedelta(days=day_offset)
        chosen = find_feasible_slot_forward(
            base_path,
            campaign,
            preferred_utc=preferred,
            operator_timezone=tz_name,
            campaign_id=campaign_id,
            planned_counts=planned,
            previous_accepted_utc=previous_accepted,
            enforce_stagger=True,
            default_hour=default_hour,
            default_minute=default_minute,
            density_ceiling=density_ceiling,
            environ=environ,
        )
        if chosen is None:
            return None, LINKEDIN_SCHEDULE_NO_FEASIBLE_SLOT
        schedules[variant_id] = chosen.strftime("%Y-%m-%dT%H:%M:%SZ")
        day_key = local_day_key_for_utc(chosen, tz)
        planned[day_key] = planned.get(day_key, 0) + 1
        previous_accepted = chosen

    # Only include requested variants (ordered list may be a subset).
    return {vid: schedules[vid] for vid in variant_ids if vid in schedules}, None
