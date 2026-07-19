"""US-077: detect-only next-week LinkedIn calendar gap sensor.

Scans the next operator-local Mon–Sun week for days with LinkedIn coverage
count ≤ ``gap_posts_threshold`` (default 0 ⇒ empty days). Applies
``min_lead_days`` so only actionable empty days appear in ``gaps[]``.

Detect-only: does not mutate campaigns, calendar rows, or draft folders, and
does not call LinkedIn / DeepSeek / ComfyUI / Git. Detect MAY run when
``gap_trigger_enabled=false`` (flag is echoed; auto-trigger remains US-082).

Gap ≠ density: days with ≥1 covering posts are not gaps even under US-040K max-2.
Empty coverage is a proxy for needing upstream content — not a filesystem
inventory of ``blog-posts/ready/`` or ``blog-posts/pending-approval/``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from silverman_blog_linkedin.flow_b_gap_operator_settings import (
    GAP_SCAN_MODE_NEXT_WEEK,
    SETTINGS_KEY_GAP_POSTS_THRESHOLD,
    SETTINGS_KEY_GAP_SCAN_MODE,
    SETTINGS_KEY_GAP_TRIGGER_ENABLED,
    SETTINGS_KEY_MIN_LEAD_DAYS,
    SETTINGS_KEY_OPERATOR_TIMEZONE,
    GapOperatorSettingsSnapshot,
    load_gap_operator_settings,
)
from silverman_blog_linkedin.flow_b_gap_operator_settings_store import (
    GapOperatorSettingsStore,
)
from silverman_blog_linkedin.linkedin_config import load_linkedin_publication_settings
from silverman_blog_linkedin.linkedin_variant_pending_supervision import (
    PUBLISH_STATE_PENDING,
)
from silverman_blog_linkedin.local_day_density import local_day_key_for_utc
from silverman_blog_linkedin.run_metadata import utc_now_iso

# Same LinkedIn membership set as US-040K density for LinkedIn-only coverage
# (policy: pending / queued / published). Deferred / cancelled / failed do not cover.
GAP_COVERAGE_PUBLISH_STATES = frozenset(
    {PUBLISH_STATE_PENDING, "queued", "published"}
)

STATUS_GAPS_FOUND: Literal["gaps_found"] = "gaps_found"
STATUS_NO_GAP: Literal["no_gap"] = "no_gap"
STATUS_BLOCKED: Literal["blocked"] = "blocked"

WEEKDAY_NAMES = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


@dataclass(frozen=True)
class CalendarGapDay:
    """One actionable empty local day in the target week."""

    local_date: str
    weekday: str
    coverage_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "local_date": self.local_date,
            "weekday": self.weekday,
            "coverage_count": self.coverage_count,
        }


@dataclass(frozen=True)
class CalendarGapDetectResult:
    """Orchestration-suitable detect-only result (always read_only)."""

    status: Literal["gaps_found", "no_gap", "blocked"]
    operator_timezone: str | None
    settings_source: Literal["defaults", "database"] | None
    gap_trigger_enabled: bool | None
    target_week: dict[str, str] | None
    gaps: list[CalendarGapDay] = field(default_factory=list)
    min_lead_days: int | None = None
    gap_posts_threshold: int | None = None
    gap_scan_mode: str | None = None
    read_only: bool = True
    observed_at_utc: str = ""
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status,
            "operator_timezone": self.operator_timezone,
            "settings_source": self.settings_source,
            "gap_trigger_enabled": self.gap_trigger_enabled,
            "target_week": self.target_week,
            "gaps": [gap.to_dict() for gap in self.gaps],
            "min_lead_days": self.min_lead_days,
            "gap_posts_threshold": self.gap_posts_threshold,
            "gap_scan_mode": self.gap_scan_mode,
            "read_only": True,
            "observed_at_utc": self.observed_at_utc,
        }
        if self.errors:
            payload["errors"] = list(self.errors)
        return payload


def next_operator_local_week(
    now_utc: datetime,
    tz: ZoneInfo,
) -> tuple[date, date, str]:
    """Return (monday, sunday, ISO week id) for the **next** Mon–Sun week.

    Always looks ahead one full week from the Monday of the current local week
    (not “rest of this week”).
    """
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    else:
        now_utc = now_utc.astimezone(timezone.utc)
    today_local = now_utc.astimezone(tz).date()
    current_monday = today_local - timedelta(days=today_local.weekday())
    next_monday = current_monday + timedelta(days=7)
    next_sunday = next_monday + timedelta(days=6)
    iso = next_monday.isocalendar()
    iso_week = f"{iso.year}-W{iso.week:02d}"
    return next_monday, next_sunday, iso_week


def _parse_now_utc(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _lead_day_distance(*, today_local: date, gap_local: date) -> int:
    """Whole local calendar days from today to gap day (``gap - today``).

    Actionable when ``distance >= min_lead_days`` (design D4).
    """
    return (gap_local - today_local).days


def _count_linkedin_coverage_by_local_day(
    base_path: Path,
    *,
    week_monday: date,
    week_sunday: date,
    tz: ZoneInfo,
    environ: dict[str, str] | None,
) -> dict[str, int]:
    """Bucket LinkedIn pending/queued/published items by operator-local day."""
    # Lazy import avoids circular dependency with schedule-visibility.
    from silverman_blog_linkedin.flow_a_schedule_visibility import (
        _load_linkedin_items,
        _parse_utc,
    )

    monday_start = datetime(
        week_monday.year, week_monday.month, week_monday.day, 0, 0, 0, tzinfo=tz
    )
    sunday_end = datetime(
        week_sunday.year, week_sunday.month, week_sunday.day, 0, 0, 0, tzinfo=tz
    ) + timedelta(days=1)
    # ±1 day UTC window for DST / TZ edges (same safety as local_day_density).
    load_start = (monday_start - timedelta(days=1)).astimezone(timezone.utc)
    load_end = (sunday_end + timedelta(days=1)).astimezone(timezone.utc)

    publication = load_linkedin_publication_settings(
        environ=environ if environ is not None else os.environ
    )
    issues: list[Any] = []
    linkedin_items = _load_linkedin_items(
        base_path,
        start=load_start,
        end=load_end,
        publication_enabled=publication.settings.publication_enabled,
        issues=issues,
    )

    counts: dict[str, int] = {}
    for item in linkedin_items:
        source = getattr(item, "source_state", None)
        if not isinstance(source, str) or source not in GAP_COVERAGE_PUBLISH_STATES:
            continue
        parsed = _parse_utc(getattr(item, "scheduled_at_utc", None))
        if parsed is None:
            continue
        day_key = local_day_key_for_utc(parsed, tz)
        counts[day_key] = counts.get(day_key, 0) + 1
    return counts


def detect_next_week_calendar_gaps(
    base_path: Path,
    *,
    now_utc: datetime | str | None = None,
    store: GapOperatorSettingsStore | None = None,
    environ: dict[str, str] | None = None,
    settings_snapshot: GapOperatorSettingsSnapshot | None = None,
) -> CalendarGapDetectResult:
    """Detect actionable LinkedIn gaps for the next operator-local week.

    Read-only: never writes campaigns, calendar, or draft folders.
    Does not require ``gap_trigger_enabled=true``.
    """
    observed = utc_now_iso()
    try:
        snapshot = (
            settings_snapshot
            if settings_snapshot is not None
            else load_gap_operator_settings(store=store, environ=environ)
        )
    except RuntimeError as exc:
        return CalendarGapDetectResult(
            status=STATUS_BLOCKED,
            operator_timezone=None,
            settings_source=None,
            gap_trigger_enabled=None,
            target_week=None,
            observed_at_utc=observed,
            errors=[str(exc)],
        )

    settings = snapshot.settings
    tz_name = settings[SETTINGS_KEY_OPERATOR_TIMEZONE]
    min_lead_days = int(settings[SETTINGS_KEY_MIN_LEAD_DAYS])
    gap_posts_threshold = int(settings[SETTINGS_KEY_GAP_POSTS_THRESHOLD])
    gap_scan_mode = settings[SETTINGS_KEY_GAP_SCAN_MODE]
    gap_trigger_enabled = bool(settings[SETTINGS_KEY_GAP_TRIGGER_ENABLED])

    if gap_scan_mode != GAP_SCAN_MODE_NEXT_WEEK:
        return CalendarGapDetectResult(
            status=STATUS_BLOCKED,
            operator_timezone=tz_name if isinstance(tz_name, str) else None,
            settings_source=snapshot.source,
            gap_trigger_enabled=gap_trigger_enabled,
            target_week=None,
            min_lead_days=min_lead_days,
            gap_posts_threshold=gap_posts_threshold,
            gap_scan_mode=gap_scan_mode if isinstance(gap_scan_mode, str) else None,
            observed_at_utc=observed,
            errors=["gap_scan_mode_unsupported"],
        )

    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError, TypeError, KeyError):
        return CalendarGapDetectResult(
            status=STATUS_BLOCKED,
            operator_timezone=tz_name if isinstance(tz_name, str) else None,
            settings_source=snapshot.source,
            gap_trigger_enabled=gap_trigger_enabled,
            target_week=None,
            min_lead_days=min_lead_days,
            gap_posts_threshold=gap_posts_threshold,
            gap_scan_mode=GAP_SCAN_MODE_NEXT_WEEK,
            observed_at_utc=observed,
            errors=["operator_timezone_invalid"],
        )

    now = _parse_now_utc(now_utc)
    today_local = now.astimezone(tz).date()
    week_monday, week_sunday, iso_week = next_operator_local_week(now, tz)
    target_week = {
        "iso_week": iso_week,
        "monday_local": week_monday.isoformat(),
        "sunday_local": week_sunday.isoformat(),
    }

    coverage = _count_linkedin_coverage_by_local_day(
        base_path,
        week_monday=week_monday,
        week_sunday=week_sunday,
        tz=tz,
        environ=environ,
    )

    gaps: list[CalendarGapDay] = []
    cursor = week_monday
    while cursor <= week_sunday:
        day_key = cursor.isoformat()
        count = coverage.get(day_key, 0)
        # Gap iff coverage ≤ threshold (default 0 ⇒ exactly empty).
        # Days with ≥1 covering posts are never gaps (even when under max-2).
        if count <= gap_posts_threshold:
            lead = _lead_day_distance(today_local=today_local, gap_local=cursor)
            if lead >= min_lead_days:
                gaps.append(
                    CalendarGapDay(
                        local_date=day_key,
                        weekday=WEEKDAY_NAMES[cursor.weekday()],
                        coverage_count=count,
                    )
                )
        cursor += timedelta(days=1)

    status: Literal["gaps_found", "no_gap"] = (
        STATUS_GAPS_FOUND if gaps else STATUS_NO_GAP
    )
    return CalendarGapDetectResult(
        status=status,
        operator_timezone=tz_name,
        settings_source=snapshot.source,
        gap_trigger_enabled=gap_trigger_enabled,
        target_week=target_week,
        gaps=gaps,
        min_lead_days=min_lead_days,
        gap_posts_threshold=gap_posts_threshold,
        gap_scan_mode=GAP_SCAN_MODE_NEXT_WEEK,
        observed_at_utc=observed,
    )
