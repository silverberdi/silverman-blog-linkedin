"""US-081: spill algorithm A placement for Flow B–origin LinkedIn scheduling.

Order under US-040K local-day density max 2 (settings ``density_max_per_local_day``
default 2, never exceeding max 2):

1. target-week ``empty_days[]`` chronological with remaining capacity
2. other days in the target ISO week with remaining capacity
3. forward day-by-day after the week with remaining capacity

Does not call LinkedIn API publish.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from silverman_blog_linkedin.flow_b_gap_operator_settings import (
    SETTINGS_KEY_DENSITY_MAX_PER_LOCAL_DAY,
    SETTINGS_KEY_OPERATOR_TIMEZONE,
    load_gap_operator_settings,
)
from silverman_blog_linkedin.local_day_density import (
    MAX_DENSITY_MEMBERS_PER_LOCAL_DAY,
    evaluate_local_day_density,
    local_day_key_for_utc,
)

FLOW_B_SPILL_A_STRATEGY = "flow_b_spill_a"

LINKEDIN_SCHEDULE_SPILL_DENSITY_EXHAUSTED = "linkedin_schedule_spill_density_exhausted"
LINKEDIN_SCHEDULE_SPILL_CONTEXT_INVALID = "linkedin_schedule_spill_context_invalid"

_ISO_WEEK_RE = re.compile(r"^(\d{4})-W(\d{2})$")
_DAY_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


@dataclass(frozen=True)
class FlowBSpillProvenance:
    """Gap context from promoted sidecar or campaign metadata."""

    target_week: str | None
    empty_days: list[str]
    origin: str = "flow_b"
    source: str = "sidecar"  # sidecar | campaign

    @property
    def usable(self) -> bool:
        return bool(self.target_week) or bool(self.empty_days)


def _as_optional_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _parse_iso_week(target_week: str) -> tuple[int, int] | None:
    match = _ISO_WEEK_RE.match(target_week.strip())
    if not match:
        return None
    year = int(match.group(1))
    week = int(match.group(2))
    if week < 1 or week > 53:
        return None
    try:
        date.fromisocalendar(year, week, 1)
    except ValueError:
        return None
    return year, week


def _parse_day(value: str) -> date | None:
    match = _DAY_RE.match(value.strip())
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def _week_days(year: int, week: int) -> list[date]:
    return [date.fromisocalendar(year, week, dow) for dow in range(1, 8)]


def _load_sidecar_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def resolve_flow_b_spill_provenance(
    base_path: Path,
    campaign: dict[str, Any],
) -> FlowBSpillProvenance | None:
    """Resolve Flow B gap provenance from campaign metadata or ready sidecar."""
    # Explicit campaign stamp (optional)
    stamped = campaign.get("flow_b_origin")
    if isinstance(stamped, dict):
        target_week = _as_optional_str(stamped.get("target_week"))
        empty_raw = stamped.get("empty_days")
        empty_days = (
            [str(day) for day in empty_raw] if isinstance(empty_raw, list) else []
        )
        provenance = FlowBSpillProvenance(
            target_week=target_week,
            empty_days=empty_days,
            source="campaign",
        )
        if provenance.usable:
            return provenance

    source_rel = _as_optional_str(campaign.get("source_relative_path"))
    if not source_rel or not source_rel.endswith(".md"):
        return None
    if not source_rel.startswith("blog-posts/ready/"):
        return None
    meta_rel = source_rel[: -len(".md")] + ".flow-b.json"
    meta_path = base_path / meta_rel
    if not meta_path.is_file():
        return None
    sidecar = _load_sidecar_json(meta_path)
    if sidecar is None:
        return None
    origin = _as_optional_str(sidecar.get("origin")) or _as_optional_str(
        sidecar.get("flow")
    )
    if origin != "flow_b":
        return None
    target_week = _as_optional_str(sidecar.get("target_week"))
    empty_raw = sidecar.get("empty_days")
    empty_days = [str(day) for day in empty_raw] if isinstance(empty_raw, list) else []
    provenance = FlowBSpillProvenance(
        target_week=target_week,
        empty_days=empty_days,
        source="sidecar",
    )
    return provenance if provenance.usable else None


def _density_ceiling() -> int:
    try:
        snapshot = load_gap_operator_settings()
        raw = snapshot.settings.get(SETTINGS_KEY_DENSITY_MAX_PER_LOCAL_DAY)
        if isinstance(raw, int) and raw > 0:
            return min(raw, MAX_DENSITY_MEMBERS_PER_LOCAL_DAY)
    except Exception:
        pass
    return MAX_DENSITY_MEMBERS_PER_LOCAL_DAY


def _operator_timezone_name() -> str | None:
    try:
        snapshot = load_gap_operator_settings()
        tz = snapshot.settings.get(SETTINGS_KEY_OPERATOR_TIMEZONE)
        if isinstance(tz, str) and tz.strip():
            ZoneInfo(tz.strip())
            return tz.strip()
    except Exception:
        pass
    return None


def _occupancy_for_day(
    base_path: Path,
    *,
    day: date,
    hour: int,
    minute: int,
    operator_timezone: str,
    campaign_id: str | None,
    planned_counts: dict[str, int],
    environ: dict[str, str] | None,
) -> int:
    """Return how many density members already occupy ``day`` (disk + planned)."""
    tz = ZoneInfo(operator_timezone)
    local_noon = datetime(day.year, day.month, day.day, hour, minute, 0, tzinfo=tz)
    target_utc = local_noon.astimezone(timezone.utc)
    result = evaluate_local_day_density(
        base_path,
        target_utc=target_utc,
        operator_timezone=operator_timezone,
        exclude_campaign_id=campaign_id,
        exclude_variant=None,
        environ=environ,
    )
    day_key = day.isoformat()
    disk = result.others_on_day if result.ok else 0
    # If TZ/density eval failed, treat as full to fail closed
    if not result.ok:
        return MAX_DENSITY_MEMBERS_PER_LOCAL_DAY
    return disk + planned_counts.get(day_key, 0)


def build_spill_a_candidate_days(
    *,
    target_week: str | None,
    empty_days: list[str],
    forward_horizon_days: int = 90,
) -> list[date] | None:
    """Build ordered candidate local days for spill algorithm A.

    Returns None when context cannot produce any ordered candidates.
    """
    week_dates: list[date] = []
    week_end: date | None = None
    if target_week:
        parsed = _parse_iso_week(target_week)
        if parsed is None:
            return None
        year, week = parsed
        week_dates = _week_days(year, week)
        week_end = week_dates[-1]

    gap_days: list[date] = []
    for raw in empty_days:
        day = _parse_day(raw)
        if day is None:
            continue
        if week_dates and day not in week_dates:
            # Still allow chronological gap days outside week if week missing/mismatched
            gap_days.append(day)
        else:
            gap_days.append(day)
    gap_days = sorted(set(gap_days))

    other_in_week: list[date] = []
    if week_dates:
        gap_set = set(gap_days)
        other_in_week = [d for d in week_dates if d not in gap_set]

    if week_end is None:
        if not gap_days:
            return None
        week_end = max(gap_days)

    forward: list[date] = []
    cursor = week_end + timedelta(days=1)
    for _ in range(forward_horizon_days):
        forward.append(cursor)
        cursor = cursor + timedelta(days=1)

    ordered: list[date] = []
    seen: set[date] = set()
    for day in (*gap_days, *other_in_week, *forward):
        if day in seen:
            continue
        seen.add(day)
        ordered.append(day)
    return ordered or None


def _ordered_variant_ids(variant_ids: list[str]) -> list[str]:
    """Canonical audience order (matches Flow A schedule)."""
    # Local import avoided — keep AUDIENCE order inline to prevent circular imports.
    audience_sequence = (
        "executive-recruiter",
        "engineering-leadership",
        "technical-architect",
        "short-provocative",
    )
    order_index = {variant_id: index for index, variant_id in enumerate(audience_sequence)}
    return sorted(variant_ids, key=lambda variant_id: order_index.get(variant_id, 999))


def compute_spill_a_schedules(
    base_path: Path,
    *,
    variant_ids: list[str],
    target_week: str | None,
    empty_days: list[str],
    anchor_utc: str,
    campaign_id: str | None = None,
    operator_timezone: str | None = None,
    environ: dict[str, str] | None = None,
) -> tuple[dict[str, str] | None, str | None]:
    """Assign ``scheduled_at_utc`` per variant under spill A + density max 2.

    Returns ``(schedules, error_code)``.
    """
    candidates = build_spill_a_candidate_days(
        target_week=target_week,
        empty_days=empty_days,
    )
    if candidates is None:
        return None, LINKEDIN_SCHEDULE_SPILL_CONTEXT_INVALID

    tz_name = operator_timezone or _operator_timezone_name()
    if not tz_name:
        # Fall back to UTC only when settings/env unavailable — still fail closed
        # if ZoneInfo invalid.
        tz_name = "UTC"
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError, TypeError, KeyError):
        return None, LINKEDIN_SCHEDULE_SPILL_CONTEXT_INVALID

    try:
        anchor = datetime.strptime(anchor_utc, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None, LINKEDIN_SCHEDULE_SPILL_CONTEXT_INVALID

    local_anchor = anchor.astimezone(tz)
    hour = local_anchor.hour
    minute = local_anchor.minute
    ceiling = _density_ceiling()
    planned: dict[str, int] = {}
    schedules: dict[str, str] = {}

    for variant_id in _ordered_variant_ids(list(variant_ids)):
        placed = False
        for day in candidates:
            day_key = day.isoformat()
            occupied = _occupancy_for_day(
                base_path,
                day=day,
                hour=hour,
                minute=minute,
                operator_timezone=tz_name,
                campaign_id=campaign_id,
                planned_counts=planned,
                environ=environ,
            )
            if occupied >= ceiling:
                continue
            local_dt = datetime(
                day.year, day.month, day.day, hour, minute, 0, tzinfo=tz
            )
            scheduled = local_dt.astimezone(timezone.utc)
            schedules[variant_id] = scheduled.strftime("%Y-%m-%dT%H:%M:%SZ")
            planned[day_key] = planned.get(day_key, 0) + 1
            placed = True
            break
        if not placed:
            return None, LINKEDIN_SCHEDULE_SPILL_DENSITY_EXHAUSTED

    return schedules, None
