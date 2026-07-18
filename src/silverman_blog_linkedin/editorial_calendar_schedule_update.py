"""Editorial calendar schedule update (US-040C).

Authenticated worker-only mutation of ``due_at_utc`` for future unpublished
calendar items. Does not call LinkedIn, DeepSeek, ComfyUI, Git, or blog publish.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.editorial_calendar_plan import (
    CALENDAR_COMPLETION_CONCURRENT_UPDATE,
    CALENDAR_FILE_NOT_FOUND,
    CALENDAR_ITEM_NOT_FOUND,
    CALENDAR_RELATIVE_PATH,
    calendar_fingerprint,
    load_calendar,
    save_calendar_atomic,
    validate_canonical_utc_timestamp,
)
from silverman_blog_linkedin.run_metadata import utc_now_iso

CALENDAR_SCHEDULE_TIME_INVALID = "calendar_schedule_time_invalid"
CALENDAR_SCHEDULE_DUPLICATE_SLOT = "calendar_schedule_duplicate_slot"
CALENDAR_SCHEDULE_SATURATION = "calendar_schedule_saturation"
CALENDAR_SCHEDULE_UNSUPPORTED_STATE = "calendar_schedule_unsupported_state"
CALENDAR_SCHEDULE_IDEMPOTENCY_CONFLICT = "calendar_schedule_idempotency_conflict"

RELATED_LINKEDIN_UNCHANGED = "unchanged_separate_overrides"

# Interim US-040C / BL-021 cadence rules until BL-021 closes.
INTERIM_MAX_BLOG_ITEMS_PER_UTC_DAY = 1
TERMINAL_SCHEDULE_STATUSES = frozenset({"completed", "skipped", "failed"})
EDITABLE_SCHEDULE_STATUSES = frozenset(
    {"planned", "scheduled", "due", "in_progress"}
)

SOURCE_CONSOLE = "linkedin_variant_supervision_console"
DEFAULT_ACTOR = "operator"


@dataclass
class EditorialCalendarScheduleUpdateResult:
    status: str
    dry_run: bool = True
    item_id: str | None = None
    previous_due_at_utc: str | None = None
    new_due_at_utc: str | None = None
    calendar_path: str = CALENDAR_RELATIVE_PATH
    calendar_written: bool = False
    idempotency_result: str | None = None
    related_linkedin_variants_outcome: str = RELATED_LINKEDIN_UNCHANGED
    audit: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _parse_utc_z(value: str) -> datetime:
    normalized = validate_canonical_utc_timestamp(value)
    return datetime.fromisoformat(normalized.replace("Z", "+00:00")).astimezone(
        timezone.utc
    )


def _utc_day_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _payload_fingerprint(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _find_item(
    calendar: dict[str, Any], item_id: str
) -> tuple[int | None, dict[str, Any] | None]:
    items = calendar.get("items")
    if not isinstance(items, list):
        return None, None
    for index, item in enumerate(items):
        if isinstance(item, dict) and str(item.get("item_id", "")) == item_id:
            return index, item
    return None, None


def _count_other_items_on_utc_day(
    calendar: dict[str, Any],
    *,
    item_id: str,
    target_day: str,
) -> int:
    items = calendar.get("items")
    if not isinstance(items, list):
        return 0
    count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("item_id", "")) == item_id:
            continue
        due = item.get("due_at_utc")
        if not isinstance(due, str) or not due.strip():
            continue
        try:
            day = _utc_day_key(_parse_utc_z(due.strip()))
        except ValueError:
            continue
        if day == target_day:
            count += 1
    return count


def _check_idempotency(
    item: dict[str, Any],
    *,
    idempotency_key: str | None,
    payload: dict[str, Any],
) -> tuple[str | None, list[str]]:
    if not idempotency_key:
        return None, []
    proofs = item.get("schedule_idempotency_proofs")
    if not isinstance(proofs, dict):
        return None, []
    existing = proofs.get(idempotency_key)
    if not isinstance(existing, dict):
        return None, []
    expected = _payload_fingerprint(payload)
    stored = existing.get("payload_fingerprint")
    if stored != expected:
        return None, [CALENDAR_SCHEDULE_IDEMPOTENCY_CONFLICT]
    return "replay", []


def _record_idempotency(
    item: dict[str, Any],
    *,
    idempotency_key: str | None,
    payload: dict[str, Any],
    completed_at: str,
) -> None:
    if not idempotency_key:
        return
    proofs = item.get("schedule_idempotency_proofs")
    if not isinstance(proofs, dict):
        proofs = {}
    proofs[idempotency_key] = {
        "payload_fingerprint": _payload_fingerprint(payload),
        "completed_at_utc": completed_at,
        "action": "update_item_schedule",
    }
    item["schedule_idempotency_proofs"] = proofs


def update_editorial_calendar_item_schedule(
    base_path: Path,
    *,
    item_id: str,
    new_due_at_utc: str,
    dry_run: bool = True,
    reason: str | None = None,
    idempotency_key: str | None = None,
    actor: str | None = None,
    source: str | None = None,
    expected_calendar_fingerprint: str | None = None,
    now: datetime | None = None,
) -> EditorialCalendarScheduleUpdateResult:
    """Update ``due_at_utc`` for an editable calendar item (dry-run default)."""
    calendar_path = CALENDAR_RELATIVE_PATH
    calendar, load_errors = load_calendar(base_path)
    if calendar is None:
        code = load_errors[0] if load_errors else CALENDAR_FILE_NOT_FOUND
        return EditorialCalendarScheduleUpdateResult(
            status="failed",
            dry_run=dry_run,
            item_id=item_id,
            calendar_path=calendar_path,
            errors=[code],
        )

    index, item = _find_item(calendar, item_id)
    if item is None or index is None:
        return EditorialCalendarScheduleUpdateResult(
            status="failed",
            dry_run=dry_run,
            item_id=item_id,
            calendar_path=calendar_path,
            errors=[CALENDAR_ITEM_NOT_FOUND],
        )

    status = str(item.get("status", ""))
    if status in TERMINAL_SCHEDULE_STATUSES or status not in EDITABLE_SCHEDULE_STATUSES:
        return EditorialCalendarScheduleUpdateResult(
            status="failed",
            dry_run=dry_run,
            item_id=item_id,
            calendar_path=calendar_path,
            previous_due_at_utc=(
                str(item["due_at_utc"])
                if isinstance(item.get("due_at_utc"), str)
                else None
            ),
            errors=[CALENDAR_SCHEDULE_UNSUPPORTED_STATE],
        )

    previous_due = item.get("due_at_utc")
    if not isinstance(previous_due, str) or not previous_due.strip():
        return EditorialCalendarScheduleUpdateResult(
            status="failed",
            dry_run=dry_run,
            item_id=item_id,
            calendar_path=calendar_path,
            errors=[CALENDAR_SCHEDULE_TIME_INVALID],
        )
    previous_due = previous_due.strip()

    try:
        normalized_new = validate_canonical_utc_timestamp(new_due_at_utc)
        new_dt = _parse_utc_z(normalized_new)
    except ValueError:
        return EditorialCalendarScheduleUpdateResult(
            status="failed",
            dry_run=dry_run,
            item_id=item_id,
            calendar_path=calendar_path,
            previous_due_at_utc=previous_due,
            errors=[CALENDAR_SCHEDULE_TIME_INVALID],
        )

    current = now or datetime.now(timezone.utc)
    if new_dt <= current:
        return EditorialCalendarScheduleUpdateResult(
            status="failed",
            dry_run=dry_run,
            item_id=item_id,
            calendar_path=calendar_path,
            previous_due_at_utc=previous_due,
            new_due_at_utc=normalized_new,
            errors=[CALENDAR_SCHEDULE_TIME_INVALID],
        )

    target_day = _utc_day_key(new_dt)
    others_on_day = _count_other_items_on_utc_day(
        calendar, item_id=item_id, target_day=target_day
    )
    if others_on_day >= INTERIM_MAX_BLOG_ITEMS_PER_UTC_DAY:
        # With max=1, another item on the day is both duplicate and saturation.
        code = (
            CALENDAR_SCHEDULE_DUPLICATE_SLOT
            if others_on_day == 1
            else CALENDAR_SCHEDULE_SATURATION
        )
        return EditorialCalendarScheduleUpdateResult(
            status="failed",
            dry_run=dry_run,
            item_id=item_id,
            calendar_path=calendar_path,
            previous_due_at_utc=previous_due,
            new_due_at_utc=normalized_new,
            errors=[code],
        )

    payload = {
        "item_id": item_id,
        "new_due_at_utc": normalized_new,
        "reason": reason,
    }
    replay_status, idempotency_errors = _check_idempotency(
        item, idempotency_key=idempotency_key, payload=payload
    )
    if idempotency_errors:
        return EditorialCalendarScheduleUpdateResult(
            status="failed",
            dry_run=dry_run,
            item_id=item_id,
            calendar_path=calendar_path,
            previous_due_at_utc=previous_due,
            new_due_at_utc=normalized_new,
            errors=idempotency_errors,
        )
    if replay_status == "replay":
        return EditorialCalendarScheduleUpdateResult(
            status="completed",
            dry_run=False,
            item_id=item_id,
            previous_due_at_utc=previous_due,
            new_due_at_utc=normalized_new,
            calendar_path=calendar_path,
            calendar_written=False,
            idempotency_result="replay",
            related_linkedin_variants_outcome=RELATED_LINKEDIN_UNCHANGED,
            audit={
                "idempotency_key": idempotency_key,
                "worker_result": "replay",
            },
        )

    if dry_run:
        return EditorialCalendarScheduleUpdateResult(
            status="completed",
            dry_run=True,
            item_id=item_id,
            previous_due_at_utc=previous_due,
            new_due_at_utc=normalized_new,
            calendar_path=calendar_path,
            calendar_written=False,
            related_linkedin_variants_outcome=RELATED_LINKEDIN_UNCHANGED,
        )

    resolved_actor = (
        actor.strip()
        if isinstance(actor, str) and actor.strip()
        else DEFAULT_ACTOR
    )
    resolved_source = (
        source.strip() if isinstance(source, str) and source.strip() else None
    )
    changed_at = utc_now_iso()
    audit_record: dict[str, Any] = {
        "changed_at_utc": changed_at,
        "previous_due_at_utc": previous_due,
        "new_due_at_utc": normalized_new,
        "actor": resolved_actor,
        "worker_result": "completed",
    }
    if reason:
        audit_record["reason"] = reason
    if resolved_source:
        audit_record["source"] = resolved_source
    if idempotency_key:
        audit_record["idempotency_key"] = idempotency_key

    working = deepcopy(calendar)
    items = working.get("items")
    assert isinstance(items, list)
    mutated = deepcopy(items[index])
    assert isinstance(mutated, dict)
    mutated["due_at_utc"] = normalized_new
    history = mutated.get("schedule_change_history")
    if not isinstance(history, list):
        history = []
    history.append(audit_record)
    mutated["schedule_change_history"] = history
    _record_idempotency(
        mutated,
        idempotency_key=idempotency_key,
        payload=payload,
        completed_at=changed_at,
    )
    items[index] = mutated

    fingerprint = expected_calendar_fingerprint
    if fingerprint is None:
        fingerprint = calendar_fingerprint(base_path)

    write_errors = save_calendar_atomic(
        base_path,
        working,
        expected_fingerprint=fingerprint,
    )
    if write_errors:
        # Prefer concurrent-update code when present.
        code = (
            CALENDAR_COMPLETION_CONCURRENT_UPDATE
            if CALENDAR_COMPLETION_CONCURRENT_UPDATE in write_errors
            else write_errors[0]
        )
        return EditorialCalendarScheduleUpdateResult(
            status="failed",
            dry_run=False,
            item_id=item_id,
            previous_due_at_utc=previous_due,
            new_due_at_utc=normalized_new,
            calendar_path=calendar_path,
            calendar_written=False,
            errors=[code],
        )

    return EditorialCalendarScheduleUpdateResult(
        status="completed",
        dry_run=False,
        item_id=item_id,
        previous_due_at_utc=previous_due,
        new_due_at_utc=normalized_new,
        calendar_path=calendar_path,
        calendar_written=True,
        idempotency_result="recorded" if idempotency_key else None,
        related_linkedin_variants_outcome=RELATED_LINKEDIN_UNCHANGED,
        audit=audit_record,
    )
