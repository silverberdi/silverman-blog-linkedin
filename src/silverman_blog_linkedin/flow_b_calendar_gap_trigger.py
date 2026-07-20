"""US-082: Flow B calendar gap trigger orchestration.

Composes US-076 settings → window/enablement gates → US-077 detect →
US-078 discover → US-079 generate into ``blog-posts/pending-approval/``.

MUST NOT write ``blog-posts/ready/``, invoke Flow A publish/package/schedule,
approve/promote drafts, call LinkedIn API publish, or re-implement US-076–US-081.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from silverman_blog_linkedin.blog_draft_generation_provider import (
    BlogDraftGenerationProvider,
)
from silverman_blog_linkedin.comfyui_client import ComfyUIClientProtocol
from silverman_blog_linkedin.flow_b_blog_draft_generation import (
    STATUS_DRAFTS_GENERATED,
    STATUS_DRAFTS_PARTIAL,
    generate_flow_b_blog_drafts,
)
from silverman_blog_linkedin.flow_b_calendar_gap_detect import (
    STATUS_BLOCKED as DETECT_STATUS_BLOCKED,
    STATUS_NO_GAP,
    detect_next_week_calendar_gaps,
)
from silverman_blog_linkedin.flow_b_gap_operator_settings import (
    SETTINGS_KEY_GAP_TRIGGER_ENABLED,
    SETTINGS_KEY_MAX_DRAFTS_PER_WEEKLY_RUN,
    SETTINGS_KEY_OPERATOR_TIMEZONE,
    SETTINGS_KEY_WEEKLY_RUN_LOCAL_DAY,
    SETTINGS_KEY_WEEKLY_RUN_LOCAL_TIME,
    GapOperatorSettingsSnapshot,
    load_gap_operator_settings,
)
from silverman_blog_linkedin.flow_b_gap_operator_settings_store import (
    GapOperatorSettingsStore,
)
from silverman_blog_linkedin.flow_b_gap_trigger_batch_store import (
    GAP_TRIGGER_BATCH_STORE_NOT_CONFIGURED,
    GAP_TRIGGER_BATCH_STORE_UNAVAILABLE,
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    GapTriggerBatchStore,
    _is_stale_in_progress,
    build_gap_trigger_idempotency_key,
    get_gap_trigger_batch_store,
)
from silverman_blog_linkedin.flow_b_topic_discovery import (
    STATUS_TOPICS_DISCOVERED,
    discover_flow_b_topics,
)
from silverman_blog_linkedin.run_metadata import utc_now_iso
from silverman_blog_linkedin.topic_discovery_provider import TopicDiscoveryProvider

STATUS_TRIGGERED: Literal["triggered"] = "triggered"
STATUS_NOOP_DISABLED: Literal["noop_disabled"] = "noop_disabled"
STATUS_NOOP_OUTSIDE_WINDOW: Literal["noop_outside_window"] = "noop_outside_window"
STATUS_NOOP_NO_GAP: Literal["noop_no_gap"] = "noop_no_gap"
STATUS_NOOP_IDEMPOTENT: Literal["noop_idempotent"] = "noop_idempotent"
STATUS_BLOCKED: Literal["blocked"] = "blocked"
STATUS_FAILED: Literal["failed"] = "failed"
STATUS_WOULD_TRIGGER: Literal["would_trigger"] = "would_trigger"

ERROR_SETTINGS_UNAVAILABLE = "gap_operator_settings_unavailable"
ERROR_TIMEZONE_INVALID = "gap_trigger_timezone_invalid"
ERROR_WINDOW_TIME_INVALID = "gap_trigger_window_time_invalid"
ERROR_DETECT_BLOCKED = "gap_detect_blocked"
ERROR_DISCOVERY_FAILED = "gap_trigger_discovery_failed"
ERROR_DRAFT_GENERATION_FAILED = "gap_trigger_draft_generation_failed"
ERROR_BATCH_STORE_UNAVAILABLE = GAP_TRIGGER_BATCH_STORE_UNAVAILABLE
ERROR_BATCH_STORE_NOT_CONFIGURED = GAP_TRIGGER_BATCH_STORE_NOT_CONFIGURED

@dataclass(frozen=True)
class GapTriggerResult:
    """Orchestration-suitable gap-trigger response (secret-safe)."""

    status: Literal[
        "triggered",
        "would_trigger",
        "noop_disabled",
        "noop_outside_window",
        "noop_no_gap",
        "noop_idempotent",
        "blocked",
        "failed",
    ]
    operator_timezone: str | None = None
    settings_source: Literal["defaults", "database"] | None = None
    gap_trigger_enabled: bool | None = None
    target_week: str | None = None
    empty_days: list[str] = field(default_factory=list)
    gaps: list[dict[str, Any]] = field(default_factory=list)
    idempotency_key: str | None = None
    batch_status: str | None = None
    max_drafts_per_weekly_run: int | None = None
    drafts: list[dict[str, Any]] = field(default_factory=list)
    dry_run: bool = False
    force_window: bool = False
    observed_at_utc: str = ""
    error_code: str | None = None
    error: str | None = None
    local_weekday: str | None = None
    local_time: str | None = None
    weekly_run_local_day: str | None = None
    weekly_run_local_time: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status,
            "operator_timezone": self.operator_timezone,
            "settings_source": self.settings_source,
            "gap_trigger_enabled": self.gap_trigger_enabled,
            "target_week": self.target_week,
            "empty_days": list(self.empty_days),
            "gaps": list(self.gaps),
            "idempotency_key": self.idempotency_key,
            "batch_status": self.batch_status,
            "max_drafts_per_weekly_run": self.max_drafts_per_weekly_run,
            "drafts": list(self.drafts),
            "observed_at_utc": self.observed_at_utc or utc_now_iso(),
        }
        if self.dry_run:
            payload["dry_run"] = True
        if self.force_window:
            payload["force_window"] = True
        if self.local_weekday is not None:
            payload["local_weekday"] = self.local_weekday
        if self.local_time is not None:
            payload["local_time"] = self.local_time
        if self.weekly_run_local_day is not None:
            payload["weekly_run_local_day"] = self.weekly_run_local_day
        if self.weekly_run_local_time is not None:
            payload["weekly_run_local_time"] = self.weekly_run_local_time
        if self.error_code is not None:
            payload["error_code"] = self.error_code
        if self.error is not None:
            payload["error"] = self.error
        return payload


def _parse_now_utc(now_utc: datetime | str | None) -> datetime:
    if now_utc is None:
        return datetime.now(timezone.utc)
    if isinstance(now_utc, datetime):
        if now_utc.tzinfo is None:
            return now_utc.replace(tzinfo=timezone.utc)
        return now_utc.astimezone(timezone.utc)
    raw = now_utc.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_hh_mm(value: str) -> time | None:
    parts = value.strip().split(":")
    if len(parts) != 2:
        return None
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return time(hour=hour, minute=minute)


def operator_local_in_weekly_window(
    *,
    now_utc: datetime,
    operator_timezone: str,
    weekly_run_local_day: str,
    weekly_run_local_time: str,
) -> tuple[bool, str | None, str | None, str | None]:
    """Return (inside_window, local_weekday, local_hhmm, error_code).

    Window: local weekday matches ``weekly_run_local_day`` and local clock is
    ≥ ``weekly_run_local_time`` through end of that local calendar day.
    """
    try:
        tz = ZoneInfo(operator_timezone)
    except (ZoneInfoNotFoundError, ValueError, TypeError, KeyError):
        return False, None, None, ERROR_TIMEZONE_INVALID

    local_dt = now_utc.astimezone(tz)
    weekday_name = local_dt.strftime("%A").lower()
    local_hhmm = local_dt.strftime("%H:%M")
    run_time = _parse_hh_mm(weekly_run_local_time)
    if run_time is None:
        return False, weekday_name, local_hhmm, ERROR_WINDOW_TIME_INVALID

    expected_day = weekly_run_local_day.strip().lower()
    if weekday_name != expected_day:
        return False, weekday_name, local_hhmm, None

    local_clock = local_dt.timetz().replace(tzinfo=None)
    if local_clock < run_time:
        return False, weekday_name, local_hhmm, None
    # Through end of local day (inclusive of any time after run_time).
    return True, weekday_name, local_hhmm, None


def _base_fields(
    snapshot: GapOperatorSettingsSnapshot | None,
    *,
    observed: str,
    dry_run: bool,
    force_window: bool,
) -> dict[str, Any]:
    settings = snapshot.settings if snapshot is not None else {}
    return {
        "operator_timezone": settings.get(SETTINGS_KEY_OPERATOR_TIMEZONE),
        "settings_source": snapshot.source if snapshot is not None else None,
        "gap_trigger_enabled": (
            bool(settings.get(SETTINGS_KEY_GAP_TRIGGER_ENABLED))
            if snapshot is not None
            else None
        ),
        "max_drafts_per_weekly_run": (
            int(settings.get(SETTINGS_KEY_MAX_DRAFTS_PER_WEEKLY_RUN) or 2)
            if snapshot is not None
            else None
        ),
        "weekly_run_local_day": settings.get(SETTINGS_KEY_WEEKLY_RUN_LOCAL_DAY),
        "weekly_run_local_time": settings.get(SETTINGS_KEY_WEEKLY_RUN_LOCAL_TIME),
        "observed_at_utc": observed,
        "dry_run": dry_run,
        "force_window": force_window,
    }


def run_flow_b_gap_trigger(
    base_path: Path,
    *,
    now_utc: datetime | str | None = None,
    dry_run: bool = False,
    force_window: bool = False,
    settings_store: GapOperatorSettingsStore | None = None,
    batch_store: GapTriggerBatchStore | None = None,
    environ: dict[str, str] | None = None,
    settings_snapshot: GapOperatorSettingsSnapshot | None = None,
    discovery_provider: TopicDiscoveryProvider | None = None,
    draft_provider: BlogDraftGenerationProvider | None = None,
    comfyui_client: ComfyUIClientProtocol | None = None,
    canon_path: Path | None = None,
) -> GapTriggerResult:
    """Run weekly gap-trigger orchestration (compose existing Flow B services)."""
    observed = utc_now_iso()
    env = os.environ if environ is None else environ
    clock = _parse_now_utc(now_utc)

    try:
        snapshot = settings_snapshot or load_gap_operator_settings(
            store=settings_store,
            environ=env,
        )
    except RuntimeError:
        return GapTriggerResult(
            status=STATUS_BLOCKED,
            observed_at_utc=observed,
            dry_run=dry_run,
            force_window=force_window,
            error_code=ERROR_SETTINGS_UNAVAILABLE,
            error="Gap operator settings store is unavailable",
        )

    base = _base_fields(
        snapshot, observed=observed, dry_run=dry_run, force_window=force_window
    )
    settings = snapshot.settings
    enabled = bool(settings.get(SETTINGS_KEY_GAP_TRIGGER_ENABLED))
    operator_tz = str(settings.get(SETTINGS_KEY_OPERATOR_TIMEZONE) or "UTC")
    weekly_day = str(settings.get(SETTINGS_KEY_WEEKLY_RUN_LOCAL_DAY) or "friday")
    weekly_time = str(settings.get(SETTINGS_KEY_WEEKLY_RUN_LOCAL_TIME) or "15:00")
    max_drafts = int(settings.get(SETTINGS_KEY_MAX_DRAFTS_PER_WEEKLY_RUN) or 2)

    if not enabled:
        return GapTriggerResult(
            status=STATUS_NOOP_DISABLED,
            **base,
        )

    inside, local_weekday, local_hhmm, window_error = operator_local_in_weekly_window(
        now_utc=clock,
        operator_timezone=operator_tz,
        weekly_run_local_day=weekly_day,
        weekly_run_local_time=weekly_time,
    )
    if window_error is not None:
        return GapTriggerResult(
            status=STATUS_BLOCKED,
            local_weekday=local_weekday,
            local_time=local_hhmm,
            error_code=window_error,
            error="Invalid operator timezone or weekly run time",
            **base,
        )
    if not force_window and not inside:
        return GapTriggerResult(
            status=STATUS_NOOP_OUTSIDE_WINDOW,
            local_weekday=local_weekday,
            local_time=local_hhmm,
            **base,
        )

    detect = detect_next_week_calendar_gaps(
        base_path,
        now_utc=clock,
        store=settings_store,
        environ=env,
        settings_snapshot=snapshot,
    )
    if detect.status == DETECT_STATUS_BLOCKED:
        return GapTriggerResult(
            status=STATUS_BLOCKED,
            local_weekday=local_weekday,
            local_time=local_hhmm,
            error_code=ERROR_DETECT_BLOCKED,
            error="Gap detect is blocked",
            **base,
        )

    target_week_meta = detect.target_week or {}
    iso_week = target_week_meta.get("iso_week")
    gaps_payload = [g.to_dict() for g in detect.gaps]
    empty_days = [g.local_date for g in detect.gaps]

    if detect.status == STATUS_NO_GAP or not empty_days:
        return GapTriggerResult(
            status=STATUS_NOOP_NO_GAP,
            target_week=iso_week,
            empty_days=[],
            gaps=[],
            local_weekday=local_weekday,
            local_time=local_hhmm,
            **base,
        )

    if not iso_week:
        return GapTriggerResult(
            status=STATUS_BLOCKED,
            local_weekday=local_weekday,
            local_time=local_hhmm,
            error_code=ERROR_DETECT_BLOCKED,
            error="Detect returned gaps without a target ISO week",
            **base,
        )

    idempotency_key = build_gap_trigger_idempotency_key(operator_tz, iso_week)

    try:
        store = batch_store or get_gap_trigger_batch_store()
    except RuntimeError:
        return GapTriggerResult(
            status=STATUS_BLOCKED,
            target_week=iso_week,
            empty_days=empty_days,
            gaps=gaps_payload,
            idempotency_key=idempotency_key,
            local_weekday=local_weekday,
            local_time=local_hhmm,
            error_code=ERROR_BATCH_STORE_NOT_CONFIGURED,
            error="Gap trigger batch store is not configured",
            **base,
        )

    existing, get_errors = store.get(idempotency_key)
    if get_errors:
        return GapTriggerResult(
            status=STATUS_BLOCKED,
            target_week=iso_week,
            empty_days=empty_days,
            gaps=gaps_payload,
            idempotency_key=idempotency_key,
            local_weekday=local_weekday,
            local_time=local_hhmm,
            error_code=ERROR_BATCH_STORE_UNAVAILABLE,
            error="Gap trigger batch store is unavailable",
            **base,
        )
    if existing is not None:
        existing_status = str(existing.get("status") or "")
        if existing_status == STATUS_COMPLETED or (
            existing_status == STATUS_IN_PROGRESS
            and not _is_stale_in_progress(existing, now_utc=clock)
        ):
            return GapTriggerResult(
                status=STATUS_NOOP_IDEMPOTENT,
                target_week=iso_week,
                empty_days=empty_days,
                gaps=gaps_payload,
                idempotency_key=idempotency_key,
                batch_status=existing_status,
                local_weekday=local_weekday,
                local_time=local_hhmm,
                **base,
            )

    if dry_run:
        return GapTriggerResult(
            status=STATUS_WOULD_TRIGGER,
            target_week=iso_week,
            empty_days=empty_days,
            gaps=gaps_payload,
            idempotency_key=idempotency_key,
            local_weekday=local_weekday,
            local_time=local_hhmm,
            **base,
        )

    _claimed, denial, claim_errors = store.try_claim(
        idempotency_key=idempotency_key,
        operator_timezone=operator_tz,
        iso_week=iso_week,
        empty_days=empty_days,
        now_utc=clock,
    )
    if claim_errors:
        return GapTriggerResult(
            status=STATUS_BLOCKED,
            target_week=iso_week,
            empty_days=empty_days,
            gaps=gaps_payload,
            idempotency_key=idempotency_key,
            local_weekday=local_weekday,
            local_time=local_hhmm,
            error_code=ERROR_BATCH_STORE_UNAVAILABLE,
            error="Gap trigger batch store is unavailable",
            **base,
        )
    if denial is not None:
        return GapTriggerResult(
            status=STATUS_NOOP_IDEMPOTENT,
            target_week=iso_week,
            empty_days=empty_days,
            gaps=gaps_payload,
            idempotency_key=idempotency_key,
            batch_status=denial,
            local_weekday=local_weekday,
            local_time=local_hhmm,
            **base,
        )

    discovery = discover_flow_b_topics(
        base_path,
        count=max_drafts,
        target_week=iso_week,
        empty_days=empty_days,
        dry_run=False,
        store=settings_store,
        environ=env,
        settings_snapshot=snapshot,
        provider=discovery_provider,
        canon_path=canon_path,
    )
    if discovery.status != STATUS_TOPICS_DISCOVERED or not discovery.topics:
        error_code = discovery.error_code or ERROR_DISCOVERY_FAILED
        store.mark_failed(
            idempotency_key,
            error_code=error_code,
            result_summary={"discovery_status": discovery.status},
        )
        return GapTriggerResult(
            status=STATUS_FAILED,
            target_week=iso_week,
            empty_days=empty_days,
            gaps=gaps_payload,
            idempotency_key=idempotency_key,
            batch_status="failed",
            local_weekday=local_weekday,
            local_time=local_hhmm,
            error_code=error_code,
            error=discovery.error or "Topic discovery failed",
            **base,
        )

    topic_inputs = [topic.to_dict() for topic in discovery.topics]
    generation = generate_flow_b_blog_drafts(
        base_path,
        topics=topic_inputs,
        target_week=iso_week,
        empty_days=empty_days,
        dry_run=False,
        store=settings_store,
        environ=env,
        settings_snapshot=snapshot,
        provider=draft_provider,
        comfyui_client=comfyui_client,
        canon_path=canon_path,
    )
    draft_payloads = [item.to_dict() for item in generation.drafts]
    success_statuses = {STATUS_DRAFTS_GENERATED, STATUS_DRAFTS_PARTIAL}
    if generation.status not in success_statuses:
        error_code = generation.error_code or ERROR_DRAFT_GENERATION_FAILED
        store.mark_failed(
            idempotency_key,
            error_code=error_code,
            result_summary={
                "generation_status": generation.status,
                "drafts": draft_payloads,
            },
        )
        return GapTriggerResult(
            status=STATUS_FAILED,
            target_week=iso_week,
            empty_days=empty_days,
            gaps=gaps_payload,
            idempotency_key=idempotency_key,
            batch_status="failed",
            drafts=draft_payloads,
            local_weekday=local_weekday,
            local_time=local_hhmm,
            error_code=error_code,
            error=generation.error or "Blog draft generation failed",
            **base,
        )

    # Partial success still counts as a completed batch (drafts were written).
    store.mark_completed(
        idempotency_key,
        result_summary={
            "generation_status": generation.status,
            "discovery_status": discovery.status,
            "drafts": draft_payloads,
            "topic_ids": [t.topic_id for t in discovery.topics],
        },
        empty_days=empty_days,
    )
    return GapTriggerResult(
        status=STATUS_TRIGGERED,
        target_week=iso_week,
        empty_days=empty_days,
        gaps=gaps_payload,
        idempotency_key=idempotency_key,
        batch_status=STATUS_COMPLETED,
        drafts=draft_payloads,
        local_weekday=local_weekday,
        local_time=local_hhmm,
        **base,
    )
