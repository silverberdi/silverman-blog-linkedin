"""Editorial calendar due-item planning and Flow A completion persistence."""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.campaign_lifecycle import (
    STATE_DERIVATIVES_GENERATED,
    STATE_DISTRIBUTION_COMPLETE,
    STATE_DISTRIBUTION_SCHEDULED,
    STATE_FLOW_A_COMPLETE,
)
from silverman_blog_linkedin.file_reader import normalize_relative_path
from silverman_blog_linkedin.run_metadata import utc_now_iso

CALENDAR_RELATIVE_PATH = "editorial-calendar/calendar.json"

FLOW_A_READY_BLOG_POST = "flow_a_ready_blog_post"
FLOW_B_SOURCE_MATERIAL = "flow_b_source_material"
USER_PROVIDED_APPROVED_BLOG = "user_provided_approved_blog"
SYSTEM_GENERATED_SOURCE_MATERIAL = "system_generated_source_material"

SOURCE_SELECTION_EXPLICIT_PATH = "explicit_path"
SOURCE_SELECTION_SINGLE_MARKDOWN = "single_markdown_in_folder"

CALENDAR_FILE_NOT_FOUND = "calendar_file_not_found"
CALENDAR_SCHEMA_INVALID = "calendar_schema_invalid"
CALENDAR_AMBIGUOUS_SOURCE_SELECTION = "calendar_ambiguous_source_selection"
CALENDAR_INVALID_FLOW_POLICY = "calendar_invalid_flow_policy"
CALENDAR_INVALID_SOURCE_SELECTION = "calendar_invalid_source_selection"
CALENDAR_ITEM_OVERDUE_BUT_PLANNED = "calendar_item_overdue_but_planned"
CALENDAR_SOURCE_FOLDER_NOT_ALLOWED = "calendar_source_folder_not_allowed"
CALENDAR_SOURCE_PATH_INVALID = "calendar_source_path_invalid"
CALENDAR_SOURCE_NOT_FOUND = "calendar_source_not_found"
CALENDAR_ITEM_NOT_FOUND = "calendar_item_not_found"
CALENDAR_COMPLETION_WRITE_FAILED = "calendar_completion_write_failed"
CALENDAR_COMPLETION_CONCURRENT_UPDATE = "calendar_completion_concurrent_update"
CALENDAR_COMPLETION_CAMPAIGN_UNRESOLVED = "calendar_completion_campaign_unresolved"
CALENDAR_COMPLETION_FACTS_CONFLICT = "calendar_completion_facts_conflict"

FLOW_A_COMPLETION_SUMMARY_KEYS: frozenset[str] = frozenset(
    {
        "campaign_state",
        "execution_status",
        "source_lifecycle_status",
        "blog_publish_status",
        "public_url",
        "linkedin_package_status",
        "linkedin_distribution_status",
    }
)

FLOW_A_LINKEDIN_SUMMARY_KEYS: frozenset[str] = frozenset(
    {
        "linkedin_package_status",
        "linkedin_distribution_status",
    }
)

_PACKAGE_COMPLETED_STATES: frozenset[str] = frozenset(
    {
        STATE_DERIVATIVES_GENERATED,
        STATE_DISTRIBUTION_SCHEDULED,
        STATE_DISTRIBUTION_COMPLETE,
        STATE_FLOW_A_COMPLETE,
    }
)

_DISTRIBUTION_COMPLETED_STATES: frozenset[str] = frozenset(
    {
        STATE_DISTRIBUTION_SCHEDULED,
        STATE_DISTRIBUTION_COMPLETE,
        STATE_FLOW_A_COMPLETE,
    }
)

FLOW_A_COMPLETION_PARENT_FIELD_KEYS: frozenset[str] = frozenset(
    {
        "campaign_id",
        "processed_source_relative_path",
        "completed_at_utc",
    }
)

ALLOWED_STATUSES: frozenset[str] = frozenset(
    {
        "planned",
        "scheduled",
        "due",
        "in_progress",
        "completed",
        "skipped",
        "failed",
    }
)

DUE_STATUSES: frozenset[str] = frozenset({"scheduled", "due"})

ALLOWED_SOURCE_FOLDERS: frozenset[str] = frozenset(
    {
        "blog-posts/ready",
        "source-material",
    }
)

FLOW_A_PLANNED_STEPS: tuple[str, ...] = (
    "validate_ready",
    "publish_blog",
    "generate_linkedin_package",
    "schedule_linkedin_distribution",
)

FLOW_B_PLANNED_STEPS: tuple[str, ...] = ("queue_for_review",)

UTC_ISO_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

CALENDAR_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "schema_version",
    "updated_at_utc",
    "items",
)

CALENDAR_ITEM_REQUIRED_FIELDS: tuple[str, ...] = (
    "item_id",
    "title",
    "status",
    "due_at_utc",
    "source_folder",
    "flow_type",
    "content_mode",
    "target_audience",
    "topic_theme",
)


@dataclass
class EditorialCalendarItemPlan:
    item_id: str
    title: str
    due_at_utc: str
    flow_type: str
    content_mode: str
    source_relative_path: str | None
    selection_status: str
    review_required: bool
    planned_flow_steps: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class EditorialCalendarPlanResult:
    status: str
    calendar_path: str
    calendar_version: str | None = None
    now_utc: str = ""
    due_items: list[EditorialCalendarItemPlan] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    read_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FlowACalendarItemCompletionResult:
    calendar: dict[str, Any]
    requires_persist: bool
    error_code: str | None = None
    skipped_already_completed: bool = False


@dataclass
class EditorialCalendarStatusResult:
    status: str
    calendar_path: str
    calendar_present: bool
    schema_version: str | None = None
    item_counts_by_status: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    read_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _calendar_path(base_path: Path) -> Path:
    return base_path / CALENDAR_RELATIVE_PATH


def calendar_file_content_fingerprint(path: Path) -> str | None:
    """Return SHA-256 hex digest of raw on-disk calendar bytes, or None if absent."""
    if not path.is_file():
        return None
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def calendar_fingerprint(base_path: Path) -> str | None:
    """Return SHA-256 fingerprint of the current calendar.json, or None if absent."""
    return calendar_file_content_fingerprint(_calendar_path(base_path))


def _fsync_parent_directory(path: Path) -> None:
    try:
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(dir_fd)
    except OSError:
        pass
    finally:
        os.close(dir_fd)


def _parse_utc_timestamp(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        parsed = datetime.strptime(normalized, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    else:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        else:
            parsed = parsed.astimezone(timezone.utc)
    return parsed


def _format_utc_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_canonical_utc_timestamp(value: str) -> str:
    """Validate a canonical UTC timestamp with Z suffix (for example 2026-07-09T20:00:00Z)."""
    stripped = value.strip()
    if not stripped:
        raise ValueError("timestamp must not be empty or whitespace-only")
    if not UTC_ISO_PATTERN.match(stripped):
        raise ValueError(
            "timestamp must be a canonical UTC instant ending with Z "
            "(for example 2026-07-09T20:00:00Z)"
        )
    try:
        _parse_utc_timestamp(stripped)
    except ValueError as exc:
        raise ValueError(
            "timestamp must be a canonical UTC instant ending with Z "
            "(for example 2026-07-09T20:00:00Z)"
        ) from exc
    return stripped


def _resolve_now_utc(now_utc: str | None) -> str:
    if now_utc is None:
        return utc_now_iso()
    parsed = _parse_utc_timestamp(now_utc)
    return _format_utc_timestamp(parsed)


def _is_absolute_or_traversal(path: str) -> bool:
    normalized = normalize_relative_path(path)
    if not normalized:
        return True
    if normalized.startswith("/"):
        return True
    parts = Path(normalized).parts
    return ".." in parts


def _is_under_folder(relative_path: str, folder: str) -> bool:
    normalized_path = normalize_relative_path(relative_path)
    normalized_folder = normalize_relative_path(folder)
    if normalized_path == normalized_folder:
        return False
    return normalized_path.startswith(f"{normalized_folder}/")


def _source_folder_allowed(source_folder: str) -> bool:
    normalized = normalize_relative_path(source_folder)
    if normalized in ALLOWED_SOURCE_FOLDERS:
        return True
    return normalized.startswith("source-material/")


def _validate_iso_utc_field(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return [CALENDAR_SCHEMA_INVALID]
    stripped = value.strip()
    if not UTC_ISO_PATTERN.match(stripped):
        return [CALENDAR_SCHEMA_INVALID]
    try:
        _parse_utc_timestamp(stripped)
    except ValueError:
        return [CALENDAR_SCHEMA_INVALID]
    return []


def _validate_calendar_item(item: Any, seen_ids: set[str]) -> list[str]:
    if not isinstance(item, dict):
        return [CALENDAR_SCHEMA_INVALID]

    errors: list[str] = []
    for field_name in CALENDAR_ITEM_REQUIRED_FIELDS:
        if field_name not in item or item[field_name] in (None, ""):
            errors.append(CALENDAR_SCHEMA_INVALID)

    if errors:
        return errors

    item_id = str(item["item_id"])
    if item_id in seen_ids:
        errors.append(CALENDAR_SCHEMA_INVALID)
    seen_ids.add(item_id)

    status = str(item["status"])
    if status not in ALLOWED_STATUSES:
        errors.append(CALENDAR_SCHEMA_INVALID)

    errors.extend(_validate_iso_utc_field(item.get("due_at_utc"), "due_at_utc"))

    source_folder = str(item.get("source_folder", ""))
    if _is_absolute_or_traversal(source_folder):
        errors.append(CALENDAR_SCHEMA_INVALID)

    source_relative_path = item.get("source_relative_path")
    source_selection_mode = item.get("source_selection_mode")

    has_path = isinstance(source_relative_path, str) and bool(
        source_relative_path.strip()
    )
    has_mode = isinstance(source_selection_mode, str) and bool(
        source_selection_mode.strip()
    )

    if has_path and has_mode:
        errors.append(CALENDAR_SCHEMA_INVALID)
    elif not has_path and not has_mode:
        errors.append(CALENDAR_SCHEMA_INVALID)
    elif has_mode:
        mode = str(source_selection_mode)
        if mode not in (
            SOURCE_SELECTION_EXPLICIT_PATH,
            SOURCE_SELECTION_SINGLE_MARKDOWN,
        ):
            errors.append(CALENDAR_SCHEMA_INVALID)
        if mode == SOURCE_SELECTION_EXPLICIT_PATH and not has_path:
            errors.append(CALENDAR_SCHEMA_INVALID)

    if has_path and _is_absolute_or_traversal(str(source_relative_path)):
        errors.append(CALENDAR_SCHEMA_INVALID)

    completed_at_utc = item.get("completed_at_utc")
    if completed_at_utc is not None:
        errors.extend(_validate_iso_utc_field(completed_at_utc, "completed_at_utc"))

    processed_source_relative_path = item.get("processed_source_relative_path")
    if processed_source_relative_path is not None:
        if not isinstance(processed_source_relative_path, str) or not processed_source_relative_path.strip():
            errors.append(CALENDAR_SCHEMA_INVALID)
        else:
            normalized_processed = normalize_relative_path(processed_source_relative_path)
            if (
                _is_absolute_or_traversal(normalized_processed)
                or not normalized_processed.endswith(".md")
            ):
                errors.append(CALENDAR_SCHEMA_INVALID)

    flow_a_completion = item.get("flow_a_completion")
    if flow_a_completion is not None:
        errors.extend(_validate_flow_a_completion_object(flow_a_completion))

    return errors


def _validate_flow_a_completion_object(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return [CALENDAR_SCHEMA_INVALID]
    errors: list[str] = []
    for forbidden_key in FLOW_A_COMPLETION_PARENT_FIELD_KEYS:
        if forbidden_key in value:
            errors.append(CALENDAR_SCHEMA_INVALID)
    for key in value:
        if key not in FLOW_A_COMPLETION_SUMMARY_KEYS:
            errors.append(CALENDAR_SCHEMA_INVALID)
    return errors


def validate_calendar_document(calendar: dict[str, Any]) -> list[str]:
    """Validate an in-memory calendar document using the same rules as load_calendar."""
    if not isinstance(calendar, dict):
        return [CALENDAR_SCHEMA_INVALID]

    errors: list[str] = []
    for field_name in CALENDAR_TOP_LEVEL_FIELDS:
        if field_name not in calendar:
            errors.append(CALENDAR_SCHEMA_INVALID)

    if errors:
        return errors

    errors.extend(
        _validate_iso_utc_field(calendar.get("updated_at_utc"), "updated_at_utc")
    )

    items = calendar.get("items")
    if not isinstance(items, list):
        return [CALENDAR_SCHEMA_INVALID]

    seen_ids: set[str] = set()
    for item in items:
        item_errors = _validate_calendar_item(item, seen_ids)
        if item_errors:
            errors.extend(item_errors)

    return list(dict.fromkeys(errors))


def derive_flow_a_linkedin_completion_statuses(
    campaign: dict[str, Any],
) -> tuple[str | None, str | None]:
    """Derive calendar LinkedIn summary statuses from canonical campaign metadata."""
    linkedin_package = (
        campaign.get("linkedin_package")
        if isinstance(campaign.get("linkedin_package"), dict)
        else {}
    )
    linkedin_distribution = (
        campaign.get("linkedin_distribution")
        if isinstance(campaign.get("linkedin_distribution"), dict)
        else {}
    )
    state = campaign.get("state")

    package_status: str | None = None
    package_meta_status = linkedin_package.get("package_status")
    if package_meta_status == "generated":
        package_status = "completed"
    elif package_meta_status == "failed":
        package_status = "failed"
    elif state in _PACKAGE_COMPLETED_STATES and linkedin_package.get("package_id"):
        package_status = "completed"

    distribution_status: str | None = None
    if state in _DISTRIBUTION_COMPLETED_STATES and linkedin_distribution.get(
        "distribution_id"
    ):
        distribution_status = "completed"
    elif _variants_show_scheduling_complete(campaign.get("variants")):
        distribution_status = "completed"

    return package_status, distribution_status


def _variants_show_scheduling_complete(variants: Any) -> bool:
    if not isinstance(variants, list) or not variants:
        return False
    for entry in variants:
        if not isinstance(entry, dict):
            return False
        scheduled_at = entry.get("scheduled_at_utc")
        if not isinstance(scheduled_at, str) or not scheduled_at.strip():
            return False
        if entry.get("publish_state") != "pending":
            return False
    return True


def _flow_a_completion_equivalent(
    left: dict[str, Any] | None,
    right: dict[str, Any] | None,
) -> bool:
    left_norm = {k: left.get(k) for k in sorted(FLOW_A_COMPLETION_SUMMARY_KEYS)} if isinstance(left, dict) else {}
    right_norm = {k: right.get(k) for k in sorted(FLOW_A_COMPLETION_SUMMARY_KEYS)} if isinstance(right, dict) else {}
    return left_norm == right_norm


def _flow_a_completion_non_linkedin_equivalent(
    left: dict[str, Any] | None,
    right: dict[str, Any] | None,
) -> bool:
    other_keys = FLOW_A_COMPLETION_SUMMARY_KEYS - FLOW_A_LINKEDIN_SUMMARY_KEYS
    left_norm = {k: left.get(k) for k in sorted(other_keys)} if isinstance(left, dict) else {}
    right_norm = {k: right.get(k) for k in sorted(other_keys)} if isinstance(right, dict) else {}
    return left_norm == right_norm


def _flow_a_completion_linkedin_summary_repair_only(
    left: dict[str, Any] | None,
    right: dict[str, Any] | None,
) -> bool:
    if not _flow_a_completion_non_linkedin_equivalent(left, right):
        return False
    left_norm = left if isinstance(left, dict) else {}
    right_norm = right if isinstance(right, dict) else {}
    needs_repair = False
    for key in FLOW_A_LINKEDIN_SUMMARY_KEYS:
        stored = left_norm.get(key)
        derived = right_norm.get(key)
        if stored is not None and stored != derived:
            return False
        if stored is None and derived is not None:
            needs_repair = True
    return needs_repair


def _canonical_completion_facts_linkedin_summary_repair(
    item: dict[str, Any],
    completion_facts: dict[str, Any],
) -> bool:
    if str(item.get("status", "")) != "completed":
        return False
    for key in ("campaign_id", "processed_source_relative_path"):
        expected = completion_facts.get(key)
        if expected is None:
            continue
        if str(item.get(key, "")) != str(expected):
            return False
    return _flow_a_completion_linkedin_summary_repair_only(
        item.get("flow_a_completion"),
        completion_facts.get("flow_a_completion"),
    )


def _canonical_completion_facts_equivalent(
    item: dict[str, Any],
    completion_facts: dict[str, Any],
) -> bool:
    if str(item.get("status", "")) != "completed":
        return False
    for key in ("campaign_id", "processed_source_relative_path"):
        expected = completion_facts.get(key)
        if expected is None:
            continue
        if str(item.get(key, "")) != str(expected):
            return False
    if not _flow_a_completion_equivalent(
        item.get("flow_a_completion"),
        completion_facts.get("flow_a_completion"),
    ):
        return False
    return True


def _canonical_completion_facts_conflict(
    item: dict[str, Any],
    completion_facts: dict[str, Any],
) -> bool:
    if str(item.get("status", "")) != "completed":
        return False
    if _canonical_completion_facts_equivalent(item, completion_facts):
        return False
    if _canonical_completion_facts_linkedin_summary_repair(item, completion_facts):
        return False
    for key in ("campaign_id", "processed_source_relative_path"):
        expected = completion_facts.get(key)
        if expected is None:
            continue
        if str(item.get(key, "")) != str(expected):
            return True
    if not _flow_a_completion_equivalent(
        item.get("flow_a_completion"),
        completion_facts.get("flow_a_completion"),
    ):
        return True
    return False


def complete_flow_a_calendar_item(
    calendar: dict[str, Any],
    *,
    item_id: str,
    completion_facts: dict[str, Any],
) -> FlowACalendarItemCompletionResult:
    """Return an updated calendar and whether persistence is required."""
    updated = deepcopy(calendar)
    items = updated.get("items")
    if not isinstance(items, list):
        return FlowACalendarItemCompletionResult(
            calendar=calendar,
            requires_persist=False,
            error_code=CALENDAR_SCHEMA_INVALID,
        )

    target_index: int | None = None
    for index, item in enumerate(items):
        if isinstance(item, dict) and str(item.get("item_id", "")) == item_id:
            target_index = index
            break

    if target_index is None:
        return FlowACalendarItemCompletionResult(
            calendar=calendar,
            requires_persist=False,
            error_code=CALENDAR_ITEM_NOT_FOUND,
        )

    target = items[target_index]
    if not isinstance(target, dict):
        return FlowACalendarItemCompletionResult(
            calendar=calendar,
            requires_persist=False,
            error_code=CALENDAR_SCHEMA_INVALID,
        )

    if _canonical_completion_facts_equivalent(target, completion_facts):
        return FlowACalendarItemCompletionResult(
            calendar=calendar,
            requires_persist=False,
            skipped_already_completed=True,
        )

    if _canonical_completion_facts_conflict(target, completion_facts):
        return FlowACalendarItemCompletionResult(
            calendar=calendar,
            requires_persist=False,
            error_code=CALENDAR_COMPLETION_FACTS_CONFLICT,
        )

    mutated = deepcopy(target)
    mutated["status"] = "completed"

    if "campaign_id" in completion_facts and completion_facts["campaign_id"] is not None:
        mutated["campaign_id"] = completion_facts["campaign_id"]

    if str(target.get("status", "")) != "completed":
        completed_at_utc = completion_facts.get("completed_at_utc")
        if isinstance(completed_at_utc, str) and completed_at_utc.strip():
            mutated["completed_at_utc"] = completed_at_utc.strip()
    elif isinstance(target.get("completed_at_utc"), str):
        mutated["completed_at_utc"] = target["completed_at_utc"]

    processed_path = completion_facts.get("processed_source_relative_path")
    if isinstance(processed_path, str) and processed_path.strip():
        mutated["processed_source_relative_path"] = normalize_relative_path(processed_path)

    flow_a_completion = completion_facts.get("flow_a_completion")
    if isinstance(flow_a_completion, dict):
        mutated["flow_a_completion"] = {
            key: flow_a_completion[key]
            for key in FLOW_A_COMPLETION_SUMMARY_KEYS
            if key in flow_a_completion
        }

    items[target_index] = mutated
    return FlowACalendarItemCompletionResult(
        calendar=updated,
        requires_persist=True,
    )


def save_calendar_atomic(
    base_path: Path,
    calendar: dict[str, Any],
    *,
    expected_fingerprint: str | None = None,
) -> list[str]:
    """Persist calendar.json with validate-then-temp-write-then-replace semantics."""
    validation_errors = validate_calendar_document(calendar)
    if validation_errors:
        return validation_errors

    path = _calendar_path(base_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = deepcopy(calendar)
    payload["updated_at_utc"] = utc_now_iso()

    if path.is_file():
        current_fingerprint = calendar_file_content_fingerprint(path)
        if expected_fingerprint is None:
            expected_fingerprint = current_fingerprint
        if (
            expected_fingerprint is None
            or current_fingerprint is None
            or current_fingerprint != expected_fingerprint
        ):
            return [CALENDAR_COMPLETION_CONCURRENT_UPDATE]

    original_mode: int | None = None
    if path.is_file():
        try:
            original_mode = path.stat().st_mode
        except OSError:
            original_mode = None

    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    replaced = False
    try:
        encoded = json.dumps(payload, indent=2) + "\n"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())

        if path.is_file() and expected_fingerprint is not None:
            pre_replace_fingerprint = calendar_file_content_fingerprint(path)
            if pre_replace_fingerprint != expected_fingerprint:
                return [CALENDAR_COMPLETION_CONCURRENT_UPDATE]

        os.replace(tmp_path, path)
        replaced = True

        if original_mode is not None:
            try:
                os.chmod(path, original_mode)
            except OSError:
                pass
        _fsync_parent_directory(path)
    except OSError:
        return [CALENDAR_COMPLETION_WRITE_FAILED]
    finally:
        if not replaced and tmp_path.is_file():
            try:
                tmp_path.unlink()
            except OSError:
                pass

    return []


def load_calendar(base_path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    """Load and validate calendar.json. Returns (calendar, errors)."""
    path = _calendar_path(base_path)
    if not path.is_file():
        return None, [CALENDAR_FILE_NOT_FOUND]

    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None, [CALENDAR_SCHEMA_INVALID]

    if not isinstance(data, dict):
        return None, [CALENDAR_SCHEMA_INVALID]

    errors = validate_calendar_document(data)
    if errors:
        return None, errors

    return data, []


def find_due_items(
    calendar: dict[str, Any], now_utc: str
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return due items and top-level warnings."""
    now = _parse_utc_timestamp(now_utc)
    due_items: list[dict[str, Any]] = []
    warnings: list[str] = []

    items = calendar.get("items", [])
    if not isinstance(items, list):
        return [], warnings

    for item in items:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", ""))
        due_at_raw = str(item.get("due_at_utc", ""))
        try:
            due_at = _parse_utc_timestamp(due_at_raw)
        except ValueError:
            continue

        if due_at > now:
            continue

        if status == "planned":
            warnings.append(CALENDAR_ITEM_OVERDUE_BUT_PLANNED)
            continue

        if status in DUE_STATUSES:
            due_items.append(item)

    return due_items, warnings


def resolve_source_document(
    base_path: Path, item: dict[str, Any]
) -> tuple[str | None, str, list[str]]:
    """Resolve source document for a calendar item."""
    source_folder = normalize_relative_path(str(item.get("source_folder", "")))
    errors: list[str] = []

    if not _source_folder_allowed(source_folder):
        return None, "rejected", [CALENDAR_SOURCE_FOLDER_NOT_ALLOWED]

    folder_path = base_path / source_folder
    if not folder_path.is_dir():
        return None, "rejected", [CALENDAR_SOURCE_NOT_FOUND]

    source_relative_path = item.get("source_relative_path")
    source_selection_mode = item.get("source_selection_mode")

    if isinstance(source_relative_path, str) and source_relative_path.strip():
        normalized = normalize_relative_path(source_relative_path)
        if _is_absolute_or_traversal(normalized):
            return None, "rejected", [CALENDAR_SOURCE_PATH_INVALID]
        if not _is_under_folder(normalized, source_folder):
            return None, "rejected", [CALENDAR_SOURCE_PATH_INVALID]
        if not normalized.endswith(".md"):
            return None, "rejected", [CALENDAR_SOURCE_PATH_INVALID]
        file_path = base_path / normalized
        if not file_path.is_file():
            return None, "rejected", [CALENDAR_SOURCE_NOT_FOUND]
        return normalized, "selected", []

    mode = str(source_selection_mode or "")
    if mode == SOURCE_SELECTION_EXPLICIT_PATH:
        return None, "rejected", [CALENDAR_INVALID_SOURCE_SELECTION]

    if mode == SOURCE_SELECTION_SINGLE_MARKDOWN:
        matches = sorted(
            p.name
            for p in folder_path.iterdir()
            if p.is_file() and p.suffix.lower() == ".md"
        )
        if len(matches) != 1:
            return None, "rejected", [CALENDAR_AMBIGUOUS_SOURCE_SELECTION]
        resolved = normalize_relative_path(f"{source_folder}/{matches[0]}")
        return resolved, "selected", []

    return None, "rejected", [CALENDAR_INVALID_SOURCE_SELECTION]


def build_item_plan(
    item: dict[str, Any],
    resolved_source: str | None,
    selection_status: str,
    selection_errors: list[str],
) -> EditorialCalendarItemPlan:
    """Build per-item execution plan labels without side effects."""
    flow_type = str(item.get("flow_type", ""))
    content_mode = str(item.get("content_mode", ""))
    errors = list(selection_errors)
    planned_steps: list[str] = []
    review_required = False

    if selection_status == "rejected" and not errors:
        errors = [CALENDAR_AMBIGUOUS_SOURCE_SELECTION]

    if selection_status == "selected":
        if content_mode == SYSTEM_GENERATED_SOURCE_MATERIAL:
            review_required = True
            planned_steps = list(FLOW_B_PLANNED_STEPS)
        elif (
            flow_type == FLOW_A_READY_BLOG_POST
            and content_mode == USER_PROVIDED_APPROVED_BLOG
        ):
            review_required = False
            planned_steps = list(FLOW_A_PLANNED_STEPS)
        else:
            selection_status = "rejected"
            errors.append(CALENDAR_INVALID_FLOW_POLICY)
            planned_steps = []
            resolved_source = None

    return EditorialCalendarItemPlan(
        item_id=str(item.get("item_id", "")),
        title=str(item.get("title", "")),
        due_at_utc=str(item.get("due_at_utc", "")),
        flow_type=flow_type,
        content_mode=content_mode,
        source_relative_path=resolved_source,
        selection_status=selection_status,
        review_required=review_required,
        planned_flow_steps=planned_steps,
        errors=errors,
        warnings=[],
    )


def _aggregate_plan_status(item_plans: list[EditorialCalendarItemPlan]) -> str:
    if not item_plans:
        return "no_due_items"
    selected = [plan for plan in item_plans if plan.selection_status == "selected"]
    rejected = [plan for plan in item_plans if plan.selection_status == "rejected"]
    if selected and rejected:
        return "partial"
    if rejected:
        return "partial"
    return "completed"


def plan_editorial_calendar_due(
    base_path: Path, *, now_utc: str | None = None
) -> EditorialCalendarPlanResult:
    """Read-only due-item planning entry point."""
    resolved_now = _resolve_now_utc(now_utc)
    calendar_file = _calendar_path(base_path)
    calendar_path_str = str(calendar_file)

    calendar, load_errors = load_calendar(base_path)
    if calendar is None:
        if CALENDAR_FILE_NOT_FOUND in load_errors:
            return EditorialCalendarPlanResult(
                status="calendar_missing",
                calendar_path=calendar_path_str,
                now_utc=resolved_now,
                errors=[CALENDAR_FILE_NOT_FOUND],
                read_only=True,
            )
        return EditorialCalendarPlanResult(
            status="calendar_invalid",
            calendar_path=calendar_path_str,
            now_utc=resolved_now,
            errors=load_errors or [CALENDAR_SCHEMA_INVALID],
            read_only=True,
        )

    due_raw, warnings = find_due_items(calendar, resolved_now)
    if not due_raw:
        return EditorialCalendarPlanResult(
            status="no_due_items",
            calendar_path=calendar_path_str,
            calendar_version=str(calendar.get("schema_version")),
            now_utc=resolved_now,
            due_items=[],
            errors=[],
            warnings=list(dict.fromkeys(warnings)),
            read_only=True,
        )

    item_plans: list[EditorialCalendarItemPlan] = []
    for item in due_raw:
        resolved_source, selection_status, selection_errors = resolve_source_document(
            base_path, item
        )
        item_plans.append(
            build_item_plan(item, resolved_source, selection_status, selection_errors)
        )

    return EditorialCalendarPlanResult(
        status=_aggregate_plan_status(item_plans),
        calendar_path=calendar_path_str,
        calendar_version=str(calendar.get("schema_version")),
        now_utc=resolved_now,
        due_items=item_plans,
        errors=[],
        warnings=list(dict.fromkeys(warnings)),
        read_only=True,
    )


def get_editorial_calendar_status(base_path: Path) -> EditorialCalendarStatusResult:
    """Return calendar presence and item counts without due-item planning."""
    calendar_file = _calendar_path(base_path)
    calendar_path_str = str(calendar_file)

    if not calendar_file.is_file():
        return EditorialCalendarStatusResult(
            status="calendar_missing",
            calendar_path=calendar_path_str,
            calendar_present=False,
            errors=[CALENDAR_FILE_NOT_FOUND],
            read_only=True,
        )

    calendar, load_errors = load_calendar(base_path)
    if calendar is None:
        return EditorialCalendarStatusResult(
            status="calendar_invalid",
            calendar_path=calendar_path_str,
            calendar_present=True,
            errors=load_errors or [CALENDAR_SCHEMA_INVALID],
            read_only=True,
        )

    counts: dict[str, int] = {status: 0 for status in sorted(ALLOWED_STATUSES)}
    for item in calendar.get("items", []):
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", ""))
        if status in counts:
            counts[status] += 1

    return EditorialCalendarStatusResult(
        status="ok",
        calendar_path=calendar_path_str,
        calendar_present=True,
        schema_version=str(calendar.get("schema_version")),
        item_counts_by_status=counts,
        errors=[],
        read_only=True,
    )


def plan_result_to_comparable_dict(result: EditorialCalendarPlanResult) -> dict[str, Any]:
    """Deep copy for idempotency comparisons in tests."""
    return deepcopy(result.to_dict())
