"""Read-only Flow A schedule-visibility aggregation for console month view (US-040B).

Aggregates editorial-calendar blog items and Flow A LinkedIn variant schedules
for a requested UTC month. Does not mutate files or call LinkedIn/DeepSeek/ComfyUI/Git.
"""

from __future__ import annotations

import calendar
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.campaign_lifecycle import (
    FLOW_A,
    METADATA_CAMPAIGNS_RELATIVE,
    CampaignLifecycleError,
    read_campaign_metadata,
    validate_campaign_id,
)
from silverman_blog_linkedin.editorial_calendar_plan import (
    CALENDAR_FILE_NOT_FOUND,
    CALENDAR_RELATIVE_PATH,
    CALENDAR_SCHEMA_INVALID,
    calendar_fingerprint,
    load_calendar,
)
from silverman_blog_linkedin.editorial_calendar_schedule_update import (
    CALENDAR_SCHEDULE_UNSUPPORTED_STATE,
    EDITABLE_SCHEDULE_STATUSES,
    TERMINAL_SCHEDULE_STATUSES,
)
from silverman_blog_linkedin.linkedin_config import load_linkedin_publication_settings
from silverman_blog_linkedin.linkedin_supervision_flow import (
    cancellation_phase_for_entry,
    is_reopen_eligible_variant,
)
from silverman_blog_linkedin.linkedin_variant_pending_supervision import (
    CAMPAIGN_FILE_INVALID,
    CAMPAIGN_FILE_PATH_OUTSIDE_SOURCE,
    CAMPAIGN_ID_FILENAME_MISMATCH,
    CAMPAIGN_ID_INVALID,
    CAMPAIGNS_DIRECTORY_INVALID,
    CAMPAIGNS_DIRECTORY_NOT_FOUND,
    CAMPAIGNS_SOURCE,
    CALENDAR_SOURCE,
    KNOWN_PUBLISH_STATES,
    LINKEDIN_PUBLISH_STATE_INVALID,
    LINKEDIN_VARIANT_INVALID,
    LINKEDIN_VARIANTS_INVALID,
    PUBLISH_STATE_FAILED,
    PUBLISH_STATE_PENDING,
    STATUS_OK,
    STATUS_PARTIAL,
    SupervisionIssue,
    _optional_http_status,
    _optional_str,
    _safe_artifact_identifier,
    _supervision_context,
)
from silverman_blog_linkedin.run_metadata import utc_now_iso

CHANNEL_BLOG = "blog"
CHANNEL_LINKEDIN = "linkedin"

# Operator-facing display vocabulary (does not invent new LinkedIn publish_state values).
DISPLAY_PLANNED = "planned"
DISPLAY_PENDING = "pending"
DISPLAY_QUEUED = "queued"
DISPLAY_PUBLISHED = "published"
DISPLAY_COMPLETED = "completed"  # Blog channel: calendar completed / published on blog (not LinkedIn API).
DISPLAY_DEFERRED = "deferred"
DISPLAY_CANCELLED = "cancelled"
DISPLAY_BLOCKED = "blocked"
DISPLAY_FAILED = "failed"

DISPLAY_STATES = frozenset(
    {
        DISPLAY_PLANNED,
        DISPLAY_PENDING,
        DISPLAY_QUEUED,
        DISPLAY_PUBLISHED,
        DISPLAY_COMPLETED,
        DISPLAY_DEFERRED,
        DISPLAY_CANCELLED,
        DISPLAY_BLOCKED,
        DISPLAY_FAILED,
    }
)

BLOG_STATUS_PLANNED_LIKE = frozenset(
    {"planned", "scheduled", "due", "in_progress", "skipped"}
)
BLOG_STATUS_FAILED = "failed"
BLOG_STATUS_COMPLETED = "completed"

YEAR_MONTH_INVALID = "year_month_invalid"
SCHEDULE_EDIT_BLOCK_NOT_PENDING = "linkedin_supervision_variant_not_pending"


@dataclass(frozen=True)
class ScheduleVisibilityItem:
    item_id: str
    channel: str
    campaign_id: str | None
    variant_id: str | None
    title: str | None
    audience: str | None
    scheduled_at_utc: str | None
    publication_state: str
    source_state: str | None
    blocked: bool
    critical: bool
    linkedin_api_published: bool
    calendar_item_id: str | None = None
    schedule_editable: bool = False
    schedule_edit_block_reason: str | None = None
    # US-040J additive cancellation context (LinkedIn cancelled items; nullable).
    cancelled_at_utc: str | None = None
    cancellation_phase: str | None = None
    cancellation_reason: str | None = None
    reopen_eligible: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScheduleVisibilityResult:
    status: str
    observed_at_utc: str
    read_only: bool
    year: int
    month: int
    from_utc: str
    to_utc: str
    linkedin_publication_enabled: bool
    items: list[ScheduleVisibilityItem] = field(default_factory=list)
    issues: list[SupervisionIssue] = field(default_factory=list)
    calendar_fingerprint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "observed_at_utc": self.observed_at_utc,
            "read_only": self.read_only,
            "year": self.year,
            "month": self.month,
            "from_utc": self.from_utc,
            "to_utc": self.to_utc,
            "linkedin_publication_enabled": self.linkedin_publication_enabled,
            "calendar_fingerprint": self.calendar_fingerprint,
            "items": [item.to_dict() for item in self.items],
            "issues": [item.to_dict() for item in self.issues],
        }


def _parse_utc(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def month_window_utc(year: int, month: int) -> tuple[datetime, datetime]:
    """Return inclusive-start / exclusive-end UTC bounds for a calendar month."""
    if year < 1 or year > 9999 or month < 1 or month > 12:
        raise ValueError(YEAR_MONTH_INVALID)
    start = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    return start, end


def _in_month(scheduled_at_utc: str | None, start: datetime, end: datetime) -> bool:
    parsed = _parse_utc(scheduled_at_utc)
    if parsed is None:
        return False
    return start <= parsed < end


def _resolved_campaigns_directory(
    base_path: Path, issues: list[SupervisionIssue]
) -> Path | None:
    try:
        base_resolved = base_path.resolve(strict=True)
        candidate = base_path / METADATA_CAMPAIGNS_RELATIVE
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError:
        issues.append(
            SupervisionIssue(CAMPAIGNS_SOURCE, None, CAMPAIGNS_DIRECTORY_NOT_FOUND)
        )
        return None
    except OSError:
        issues.append(
            SupervisionIssue(CAMPAIGNS_SOURCE, None, CAMPAIGNS_DIRECTORY_INVALID)
        )
        return None

    try:
        resolved.relative_to(base_resolved)
    except ValueError:
        issues.append(
            SupervisionIssue(CAMPAIGNS_SOURCE, None, CAMPAIGNS_DIRECTORY_INVALID)
        )
        return None
    if not resolved.is_dir():
        issues.append(
            SupervisionIssue(CAMPAIGNS_SOURCE, None, CAMPAIGNS_DIRECTORY_INVALID)
        )
        return None
    return resolved


def _direct_json_entries(
    directory: Path, issues: list[SupervisionIssue]
) -> list[Path]:
    try:
        entries = sorted(directory.iterdir(), key=lambda path: path.name)
    except OSError:
        issues.append(
            SupervisionIssue(CAMPAIGNS_SOURCE, None, CAMPAIGN_FILE_INVALID)
        )
        return []

    accepted: list[Path] = []
    for entry in entries:
        if entry.suffix != ".json":
            continue
        identifier = _safe_artifact_identifier(entry)
        try:
            resolved = entry.resolve(strict=True)
            resolved.relative_to(directory)
        except (FileNotFoundError, OSError, ValueError):
            issues.append(
                SupervisionIssue(
                    CAMPAIGNS_SOURCE, identifier, CAMPAIGN_FILE_PATH_OUTSIDE_SOURCE
                )
            )
            continue
        if not resolved.is_file():
            issues.append(
                SupervisionIssue(CAMPAIGNS_SOURCE, identifier, CAMPAIGN_FILE_INVALID)
            )
            continue
        accepted.append(entry)
    return accepted


def _blog_schedule_editability(
    status: str | None,
) -> tuple[bool, str | None]:
    if status is None:
        return False, CALENDAR_SCHEDULE_UNSUPPORTED_STATE
    if status in TERMINAL_SCHEDULE_STATUSES:
        return False, CALENDAR_SCHEDULE_UNSUPPORTED_STATE
    if status in EDITABLE_SCHEDULE_STATUSES:
        return True, None
    return False, CALENDAR_SCHEDULE_UNSUPPORTED_STATE


def _linkedin_schedule_editability(publish_state: str) -> tuple[bool, str | None]:
    # US-084: Scheduled (pending) and Waiting to send (queued) are schedule-editable.
    if publish_state in (PUBLISH_STATE_PENDING, DISPLAY_QUEUED):
        return True, None
    return False, SCHEDULE_EDIT_BLOCK_NOT_PENDING


def _map_blog_display_state(status: str | None) -> tuple[str, bool, bool]:
    """Return (publication_state, blocked, critical) for a calendar item."""
    if status == BLOG_STATUS_FAILED:
        return DISPLAY_FAILED, False, True
    if status == BLOG_STATUS_COMPLETED:
        # Distinct from LinkedIn DISPLAY_PUBLISHED (API evidence); blog channel stays
        # linkedin_api_published=false at item construction.
        return DISPLAY_COMPLETED, False, False
    if status in BLOG_STATUS_PLANNED_LIKE or status is None:
        return DISPLAY_PLANNED, False, False
    return DISPLAY_PLANNED, False, False


def _map_linkedin_display_state(
    *,
    publish_state: str,
    last_action: str | None,
    auto_queue_eligible: bool | None,
    publication_enabled: bool,
) -> tuple[str, bool, bool, bool]:
    """Return (publication_state, blocked, critical, linkedin_api_published)."""
    if publish_state == "published":
        return DISPLAY_PUBLISHED, False, False, True
    if publish_state == "cancelled":
        return DISPLAY_CANCELLED, False, False, False
    if publish_state == PUBLISH_STATE_FAILED:
        return DISPLAY_FAILED, False, True, False
    if publish_state == "queued":
        blocked = not publication_enabled
        display = DISPLAY_BLOCKED if blocked else DISPLAY_QUEUED
        return display, blocked, blocked, False
    if publish_state == PUBLISH_STATE_PENDING:
        deferred = last_action == "defer" or auto_queue_eligible is False
        if deferred:
            return DISPLAY_DEFERRED, False, False, False
        blocked = not publication_enabled
        if blocked:
            return DISPLAY_BLOCKED, True, True, False
        return DISPLAY_PENDING, False, False, False
    return DISPLAY_PENDING, False, False, False


def _load_blog_items(
    base_path: Path,
    *,
    start: datetime,
    end: datetime,
    issues: list[SupervisionIssue],
) -> list[ScheduleVisibilityItem]:
    calendar_doc, errors = load_calendar(base_path)
    if calendar_doc is None:
        reason = errors[0] if errors else CALENDAR_SCHEMA_INVALID
        issues.append(SupervisionIssue(CALENDAR_SOURCE, "calendar_store", reason))
        return []

    raw_items = calendar_doc.get("items", [])
    if not isinstance(raw_items, list):
        issues.append(
            SupervisionIssue(CALENDAR_SOURCE, "calendar_store", CALENDAR_SCHEMA_INVALID)
        )
        return []

    items: list[ScheduleVisibilityItem] = []
    for entry in raw_items:
        if not isinstance(entry, dict):
            continue
        item_id = _optional_str(entry.get("item_id"))
        due_at = _optional_str(entry.get("due_at_utc"))
        if not item_id or not _in_month(due_at, start, end):
            continue
        status = _optional_str(entry.get("status"))
        publication_state, blocked, critical = _map_blog_display_state(status)
        title = _optional_str(entry.get("title"))
        schedule_editable, block_reason = _blog_schedule_editability(status)
        items.append(
            ScheduleVisibilityItem(
                item_id=f"blog:{item_id}",
                channel=CHANNEL_BLOG,
                campaign_id=_optional_str(entry.get("campaign_id")),
                variant_id=None,
                title=title,
                audience=_optional_str(entry.get("target_audience")),
                scheduled_at_utc=due_at,
                publication_state=publication_state,
                source_state=status,
                blocked=blocked,
                critical=critical,
                linkedin_api_published=False,
                calendar_item_id=item_id,
                schedule_editable=schedule_editable,
                schedule_edit_block_reason=block_reason,
            )
        )
    return items


def _linkedin_rows_from_campaign(
    campaign: dict[str, Any],
    *,
    campaign_id: str,
    start: datetime,
    end: datetime,
    publication_enabled: bool,
    issues: list[SupervisionIssue],
) -> list[ScheduleVisibilityItem]:
    variants_raw = campaign.get("variants")
    if variants_raw is None:
        return []
    if not isinstance(variants_raw, list):
        issues.append(
            SupervisionIssue(CAMPAIGNS_SOURCE, campaign_id, LINKEDIN_VARIANTS_INVALID)
        )
        return []

    rows: list[ScheduleVisibilityItem] = []
    for index, entry in enumerate(variants_raw):
        if not isinstance(entry, dict):
            issues.append(
                SupervisionIssue(
                    CAMPAIGNS_SOURCE,
                    f"{campaign_id}#{index}",
                    LINKEDIN_VARIANT_INVALID,
                )
            )
            continue

        variant_id = entry.get("variant")
        if not isinstance(variant_id, str) or not variant_id.strip():
            issues.append(
                SupervisionIssue(
                    CAMPAIGNS_SOURCE,
                    f"{campaign_id}#{index}",
                    LINKEDIN_VARIANT_INVALID,
                )
            )
            continue

        publish_state = entry.get("publish_state")
        if publish_state is None:
            continue
        if not isinstance(publish_state, str) or publish_state not in KNOWN_PUBLISH_STATES:
            issues.append(
                SupervisionIssue(
                    CAMPAIGNS_SOURCE,
                    f"{campaign_id}:{variant_id}",
                    LINKEDIN_PUBLISH_STATE_INVALID,
                )
            )
            continue

        scheduled_at = _optional_str(entry.get("scheduled_at_utc"))
        if not _in_month(scheduled_at, start, end):
            continue

        last_action, auto_queue_eligible, _reason = _supervision_context(entry)
        (
            publication_state,
            blocked,
            critical,
            linkedin_api_published,
        ) = _map_linkedin_display_state(
            publish_state=publish_state,
            last_action=last_action,
            auto_queue_eligible=auto_queue_eligible,
            publication_enabled=publication_enabled,
        )

        # Surface failed publish evidence as critical without inventing success.
        if publish_state == PUBLISH_STATE_FAILED:
            evidence = entry.get("linkedin_publication")
            if isinstance(evidence, dict):
                _ = _optional_http_status(evidence.get("http_status"))

        title = _optional_str(entry.get("audience")) or variant_id
        schedule_editable, block_reason = _linkedin_schedule_editability(publish_state)
        cancelled_at_utc: str | None = None
        cancellation_phase: str | None = None
        cancellation_reason: str | None = None
        reopen_eligible: bool | None = None
        if publish_state == "cancelled":
            cancellation_phase = cancellation_phase_for_entry(entry)
            supervision = entry.get("operator_supervision")
            if isinstance(supervision, dict):
                cancellation = supervision.get("cancellation")
                if isinstance(cancellation, dict):
                    cancelled_at_utc = _optional_str(cancellation.get("cancelled_at_utc"))
                    cancellation_reason = _optional_str(cancellation.get("reason"))
            reopen_eligible = is_reopen_eligible_variant(entry)
        rows.append(
            ScheduleVisibilityItem(
                item_id=f"linkedin:{campaign_id}:{variant_id}",
                channel=CHANNEL_LINKEDIN,
                campaign_id=campaign_id,
                variant_id=variant_id,
                title=title,
                audience=_optional_str(entry.get("audience")),
                scheduled_at_utc=scheduled_at,
                publication_state=publication_state,
                source_state=publish_state,
                blocked=blocked,
                critical=critical,
                linkedin_api_published=linkedin_api_published,
                calendar_item_id=None,
                schedule_editable=schedule_editable,
                schedule_edit_block_reason=block_reason,
                cancelled_at_utc=cancelled_at_utc,
                cancellation_phase=cancellation_phase,
                cancellation_reason=cancellation_reason,
                reopen_eligible=reopen_eligible,
            )
        )
    return rows


def _load_linkedin_items(
    base_path: Path,
    *,
    start: datetime,
    end: datetime,
    publication_enabled: bool,
    issues: list[SupervisionIssue],
) -> list[ScheduleVisibilityItem]:
    directory = _resolved_campaigns_directory(base_path, issues)
    if directory is None:
        return []

    rows: list[ScheduleVisibilityItem] = []
    for path in _direct_json_entries(directory, issues):
        artifact_identifier = _safe_artifact_identifier(path)
        filename_id = path.stem
        try:
            validate_campaign_id(filename_id)
        except CampaignLifecycleError:
            issues.append(
                SupervisionIssue(
                    CAMPAIGNS_SOURCE, artifact_identifier, CAMPAIGN_ID_INVALID
                )
            )
            continue

        try:
            raw = path.read_text(encoding="utf-8")
            parsed = json.loads(raw)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            issues.append(
                SupervisionIssue(
                    CAMPAIGNS_SOURCE, artifact_identifier, CAMPAIGN_FILE_INVALID
                )
            )
            continue
        if not isinstance(parsed, dict):
            issues.append(
                SupervisionIssue(
                    CAMPAIGNS_SOURCE, artifact_identifier, CAMPAIGN_FILE_INVALID
                )
            )
            continue

        campaign = read_campaign_metadata(base_path, filename_id)
        if not isinstance(campaign, dict):
            issues.append(
                SupervisionIssue(
                    CAMPAIGNS_SOURCE, artifact_identifier, CAMPAIGN_FILE_INVALID
                )
            )
            continue

        persisted_id = campaign.get("campaign_id")
        try:
            if not isinstance(persisted_id, str):
                raise CampaignLifecycleError("", error_code=CAMPAIGN_ID_INVALID)
            validate_campaign_id(persisted_id)
        except CampaignLifecycleError:
            issues.append(
                SupervisionIssue(
                    CAMPAIGNS_SOURCE, artifact_identifier, CAMPAIGN_ID_INVALID
                )
            )
            continue
        if persisted_id != filename_id:
            issues.append(
                SupervisionIssue(
                    CAMPAIGNS_SOURCE,
                    artifact_identifier,
                    CAMPAIGN_ID_FILENAME_MISMATCH,
                )
            )
            continue
        if campaign.get("flow") != FLOW_A:
            continue

        rows.extend(
            _linkedin_rows_from_campaign(
                campaign,
                campaign_id=persisted_id,
                start=start,
                end=end,
                publication_enabled=publication_enabled,
                issues=issues,
            )
        )
    return rows


def get_flow_a_schedule_visibility(
    base_path: Path,
    *,
    year: int | None = None,
    month: int | None = None,
    environ: dict[str, str] | None = None,
) -> ScheduleVisibilityResult:
    """Aggregate blog + LinkedIn schedule items for a UTC month (read-only)."""
    observed = utc_now_iso()
    now = _parse_utc(observed) or datetime.now(timezone.utc)
    resolved_year = int(year) if year is not None else now.year
    resolved_month = int(month) if month is not None else now.month

    issues: list[SupervisionIssue] = []
    try:
        start, end = month_window_utc(resolved_year, resolved_month)
    except ValueError:
        issues.append(
            SupervisionIssue(CALENDAR_SOURCE, None, YEAR_MONTH_INVALID)
        )
        # Fall back to current UTC month so the response remains usable.
        start, end = month_window_utc(now.year, now.month)
        resolved_year, resolved_month = now.year, now.month

    publication = load_linkedin_publication_settings(environ=environ)
    enabled = publication.settings.publication_enabled

    blog_items = _load_blog_items(
        base_path, start=start, end=end, issues=issues
    )
    linkedin_items = _load_linkedin_items(
        base_path,
        start=start,
        end=end,
        publication_enabled=enabled,
        issues=issues,
    )

    fingerprint: str | None = None
    calendar_path = base_path / CALENDAR_RELATIVE_PATH
    if calendar_path.is_file():
        # Only expose fingerprint when the calendar file is present and readable.
        # Missing/invalid calendars already surface issues via _load_blog_items.
        fingerprint = calendar_fingerprint(base_path)

    items = blog_items + linkedin_items
    items.sort(
        key=lambda item: (
            item.scheduled_at_utc or "",
            item.channel,
            item.campaign_id or "",
            item.variant_id or item.calendar_item_id or "",
        )
    )
    issues = sorted(
        set(issues),
        key=lambda item: (item.source, item.identifier or "", item.reason),
    )

    # last day of month for inclusive display metadata (window end is exclusive)
    last_day = calendar.monthrange(resolved_year, resolved_month)[1]
    to_inclusive = datetime(
        resolved_year, resolved_month, last_day, 23, 59, 59, tzinfo=timezone.utc
    )

    return ScheduleVisibilityResult(
        status=STATUS_PARTIAL if issues else STATUS_OK,
        observed_at_utc=observed,
        read_only=True,
        year=resolved_year,
        month=resolved_month,
        from_utc=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        to_utc=to_inclusive.strftime("%Y-%m-%dT%H:%M:%SZ"),
        linkedin_publication_enabled=enabled,
        items=items,
        issues=issues,
        calendar_fingerprint=fingerprint,
    )
