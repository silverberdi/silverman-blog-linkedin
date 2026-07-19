"""US-040K: max-2 density members per operator-local calendar day.

Shared evaluator for defer / reopen / blog schedule-update. Additive to interim
duplicate-slot and UTC-day/72h (LinkedIn) and blog max-1/UTC-day checks.
BL-021 MAY later supersede this interim product rule via an approved change.

Does not call LinkedIn, DeepSeek, ComfyUI, or Git.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from silverman_blog_linkedin.linkedin_config import load_linkedin_publication_settings
from silverman_blog_linkedin.linkedin_variant_pending_supervision import (
    PUBLISH_STATE_PENDING,
)

# Stable codes — distinct from interim *_saturation / duplicate-slot families.
LINKEDIN_SUPERVISION_LOCAL_DAY_DENSITY = "linkedin_supervision_local_day_density"
CALENDAR_SCHEDULE_LOCAL_DAY_DENSITY = "calendar_schedule_local_day_density"
OPERATOR_TIMEZONE_REQUIRED = "operator_timezone_required"
OPERATOR_TIMEZONE_INVALID = "operator_timezone_invalid"

ENV_OPERATOR_TIMEZONE = "SILVERMAN_OPERATOR_TIMEZONE"

MAX_DENSITY_MEMBERS_PER_LOCAL_DAY = 2

# LinkedIn publish_state values that occupy a density slot (D1).
_LINKEDIN_DENSITY_PUBLISH_STATES = frozenset(
    {PUBLISH_STATE_PENDING, "queued", "published"}
)

CHANNEL_BLOG = "blog"
CHANNEL_LINKEDIN = "linkedin"


@dataclass(frozen=True)
class LocalDayDensityResult:
    ok: bool
    others_on_day: int = 0
    target_local_day: str | None = None
    resolved_timezone: str | None = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "others_on_day": self.others_on_day,
            "target_local_day": self.target_local_day,
            "resolved_timezone": self.resolved_timezone,
            "errors": list(self.errors),
        }


def resolve_operator_timezone(
    request_timezone: str | None,
    *,
    environ: dict[str, str] | None = None,
) -> tuple[str | None, list[str]]:
    """Resolve IANA timezone from request or SILVERMAN_OPERATOR_TIMEZONE.

    Fail closed when neither is valid — do not silently use UTC for US-040K.
    """
    env = os.environ if environ is None else environ
    candidates: list[tuple[str, str]] = []
    if isinstance(request_timezone, str) and request_timezone.strip():
        candidates.append(("request", request_timezone.strip()))
    env_raw = env.get(ENV_OPERATOR_TIMEZONE)
    if isinstance(env_raw, str) and env_raw.strip():
        candidates.append(("env", env_raw.strip()))

    if not candidates:
        return None, [OPERATOR_TIMEZONE_REQUIRED]

    last_invalid = OPERATOR_TIMEZONE_INVALID
    for _source, name in candidates:
        try:
            ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError, TypeError, KeyError):
            last_invalid = OPERATOR_TIMEZONE_INVALID
            continue
        return name, []
    return None, [last_invalid]


def local_day_key_for_utc(dt_utc: datetime, tz: ZoneInfo) -> str:
    """Return YYYY-MM-DD for ``dt_utc`` in the operator timezone."""
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    local = dt_utc.astimezone(tz)
    return local.strftime("%Y-%m-%d")


def _is_density_member(item: Any) -> bool:
    channel = getattr(item, "channel", None)
    source = getattr(item, "source_state", None)
    if channel == CHANNEL_LINKEDIN:
        return isinstance(source, str) and source in _LINKEDIN_DENSITY_PUBLISH_STATES
    if channel == CHANNEL_BLOG:
        # Blog items returned by schedule-visibility count (D1).
        return True
    return False


def _is_excluded(
    item: Any,
    *,
    exclude_campaign_id: str | None,
    exclude_variant: str | None,
    exclude_calendar_item_id: str | None,
) -> bool:
    channel = getattr(item, "channel", None)
    if (
        exclude_campaign_id
        and exclude_variant
        and channel == CHANNEL_LINKEDIN
        and getattr(item, "campaign_id", None) == exclude_campaign_id
        and getattr(item, "variant_id", None) == exclude_variant
    ):
        return True
    if (
        exclude_calendar_item_id
        and channel == CHANNEL_BLOG
        and getattr(item, "calendar_item_id", None) == exclude_calendar_item_id
    ):
        return True
    return False


def evaluate_local_day_density(
    base_path: Path,
    *,
    target_utc: datetime,
    operator_timezone: str | None = None,
    exclude_campaign_id: str | None = None,
    exclude_variant: str | None = None,
    exclude_calendar_item_id: str | None = None,
    density_error_code: str = LINKEDIN_SUPERVISION_LOCAL_DAY_DENSITY,
    environ: dict[str, str] | None = None,
) -> LocalDayDensityResult:
    """Count density members on the target operator-local day; refuse when ≥ 2 others.

    Placing would yield ``others_on_day + 1``. Refuse when that would be > 2
    (i.e. ``others_on_day >= MAX_DENSITY_MEMBERS_PER_LOCAL_DAY``).
    """
    # Lazy import avoids circular dependency with schedule-visibility / supervision.
    from silverman_blog_linkedin.flow_a_schedule_visibility import (
        _load_blog_items,
        _load_linkedin_items,
        _parse_utc,
    )

    resolved_name, tz_errors = resolve_operator_timezone(
        operator_timezone, environ=environ
    )
    if tz_errors or not resolved_name:
        return LocalDayDensityResult(
            ok=False,
            errors=tz_errors or [OPERATOR_TIMEZONE_REQUIRED],
        )

    try:
        tz = ZoneInfo(resolved_name)
    except (ZoneInfoNotFoundError, ValueError, TypeError, KeyError):
        return LocalDayDensityResult(
            ok=False,
            errors=[OPERATOR_TIMEZONE_INVALID],
        )

    if target_utc.tzinfo is None:
        target_utc = target_utc.replace(tzinfo=timezone.utc)
    else:
        target_utc = target_utc.astimezone(timezone.utc)

    target_day = local_day_key_for_utc(target_utc, tz)

    # Load window: target local day ±1 day (DST / TZ edge safety per design).
    day_start_local = datetime.fromisoformat(f"{target_day}T00:00:00").replace(
        tzinfo=tz
    )
    day_end_local = day_start_local + timedelta(days=1)
    load_start = (day_start_local - timedelta(days=1)).astimezone(timezone.utc)
    load_end = (day_end_local + timedelta(days=1)).astimezone(timezone.utc)

    issues: list[Any] = []
    publication = load_linkedin_publication_settings(
        environ=environ if environ is not None else os.environ
    )
    publication_enabled = publication.settings.publication_enabled

    blog_items = _load_blog_items(
        base_path, start=load_start, end=load_end, issues=issues
    )
    linkedin_items = _load_linkedin_items(
        base_path,
        start=load_start,
        end=load_end,
        publication_enabled=publication_enabled,
        issues=issues,
    )

    others = 0
    for item in (*blog_items, *linkedin_items):
        if not _is_density_member(item):
            continue
        if _is_excluded(
            item,
            exclude_campaign_id=exclude_campaign_id,
            exclude_variant=exclude_variant,
            exclude_calendar_item_id=exclude_calendar_item_id,
        ):
            continue
        parsed = _parse_utc(item.scheduled_at_utc)
        if parsed is None:
            continue
        if local_day_key_for_utc(parsed, tz) != target_day:
            continue
        others += 1

    if others >= MAX_DENSITY_MEMBERS_PER_LOCAL_DAY:
        return LocalDayDensityResult(
            ok=False,
            others_on_day=others,
            target_local_day=target_day,
            resolved_timezone=resolved_name,
            errors=[density_error_code],
        )

    return LocalDayDensityResult(
        ok=True,
        others_on_day=others,
        target_local_day=target_day,
        resolved_timezone=resolved_name,
        errors=[],
    )
