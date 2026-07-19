"""Ready-path Flow A completion: lifecycle + optional calendar upsert over HTTP."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.campaign_lifecycle import (
    read_campaign_metadata,
)
from silverman_blog_linkedin.editorial_calendar_flow_a_execute import (
    EXECUTION_STATUS_EXECUTED,
    SOURCE_LIFECYCLE_COMPLETED,
    SOURCE_LIFECYCLE_FAILED,
    SOURCE_LIFECYCLE_SKIPPED,
    _build_completion_facts_from_campaign,
)
from silverman_blog_linkedin.editorial_calendar_plan import (
    CALENDAR_COMPLETION_WRITE_FAILED,
    CALENDAR_RELATIVE_PATH,
    CALENDAR_SCHEMA_INVALID,
    calendar_fingerprint,
    complete_flow_a_calendar_item,
    load_calendar,
    save_calendar_atomic,
)
from silverman_blog_linkedin.file_reader import normalize_relative_path
from silverman_blog_linkedin.flow_a_source_lifecycle import (
    complete_flow_a_source_lifecycle,
)
from silverman_blog_linkedin.run_metadata import utc_now_iso

CALENDAR_UPDATE_COMPLETED = "completed"
CALENDAR_UPDATE_SKIPPED_ALREADY_COMPLETED = "skipped_already_completed"
CALENDAR_UPDATE_SKIPPED_ABSENT = "skipped_calendar_absent"
CALENDAR_UPDATE_SKIPPED_NOT_REQUESTED = "skipped_not_requested"
CALENDAR_UPDATE_FAILED = "failed"

STATUS_COMPLETED = "completed"
STATUS_PARTIAL = "partial"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"

DEFAULT_TARGET_AUDIENCE = "executive-recruiter"
DEFAULT_TOPIC_THEME = "architecture"
DEFAULT_FLOW_TYPE = "flow_a_ready_blog_post"
DEFAULT_CONTENT_MODE = "user_provided_approved_blog"
DEFAULT_SOURCE_FOLDER = "blog-posts/ready"


@dataclass
class FlowAReadyPathCompletionResult:
    status: str
    campaign_id: str | None = None
    source_lifecycle_status: str | None = None
    calendar_update_status: str | None = None
    processed_source_relative_path: str | None = None
    already_processed: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    lifecycle: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _campaign_identity_paths(campaign: dict[str, Any]) -> set[str]:
    paths: set[str] = set()
    for key in (
        "source_relative_path",
        "original_source_relative_path",
        "queued_source_relative_path",
        "processed_source_relative_path",
    ):
        value = campaign.get(key)
        if isinstance(value, str) and value.strip():
            paths.add(normalize_relative_path(value))
    return paths


def _item_matches_campaign(item: dict[str, Any], campaign: dict[str, Any]) -> bool:
    campaign_id = campaign.get("campaign_id")
    item_campaign_id = item.get("campaign_id")
    if (
        isinstance(campaign_id, str)
        and campaign_id.strip()
        and isinstance(item_campaign_id, str)
        and item_campaign_id.strip()
        and item_campaign_id.strip() == campaign_id.strip()
    ):
        return True

    identity_paths = _campaign_identity_paths(campaign)
    if not identity_paths:
        return False

    for key in ("source_relative_path", "processed_source_relative_path"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            if normalize_relative_path(value) in identity_paths:
                return True
    return False


def _resolve_matching_item_id(
    calendar: dict[str, Any],
    campaign: dict[str, Any],
) -> str | None:
    items = calendar.get("items")
    if not isinstance(items, list):
        return None
    matches: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if not _item_matches_campaign(item, campaign):
            continue
        item_id = item.get("item_id")
        if isinstance(item_id, str) and item_id.strip():
            matches.append(item_id.strip())
    if len(matches) == 1:
        return matches[0]
    return None


def _ready_source_path_for_calendar(campaign: dict[str, Any]) -> str | None:
    for key in (
        "original_source_relative_path",
        "source_relative_path",
        "queued_source_relative_path",
    ):
        value = campaign.get(key)
        if isinstance(value, str) and value.strip():
            normalized = normalize_relative_path(value)
            if normalized.startswith("blog-posts/"):
                return normalized
    processed = campaign.get("processed_source_relative_path")
    if isinstance(processed, str) and processed.strip():
        name = Path(processed).name
        if name.endswith(".md"):
            return f"blog-posts/ready/{name}"
    return None


def _build_new_calendar_item(
    campaign: dict[str, Any],
    *,
    completion_facts: dict[str, Any],
) -> dict[str, Any]:
    campaign_id = str(campaign.get("campaign_id") or "").strip()
    public_slug = campaign.get("public_slug")
    title = (
        str(public_slug).strip()
        if isinstance(public_slug, str) and public_slug.strip()
        else campaign_id
    )
    completed_at = completion_facts.get("completed_at_utc") or utc_now_iso()
    source_relative = _ready_source_path_for_calendar(campaign)
    item: dict[str, Any] = {
        "item_id": campaign_id,
        "title": title,
        "status": "completed",
        "due_at_utc": completed_at,
        "completed_at_utc": completed_at,
        "source_folder": DEFAULT_SOURCE_FOLDER,
        "flow_type": DEFAULT_FLOW_TYPE,
        "content_mode": DEFAULT_CONTENT_MODE,
        "target_audience": DEFAULT_TARGET_AUDIENCE,
        "topic_theme": (
            str(campaign["topic_theme"]).strip()
            if isinstance(campaign.get("topic_theme"), str)
            and str(campaign.get("topic_theme")).strip()
            else DEFAULT_TOPIC_THEME
        ),
        "campaign_id": campaign_id,
    }
    if source_relative:
        item["source_relative_path"] = source_relative
    else:
        item["source_selection_mode"] = "single_markdown_in_folder"
    if isinstance(public_slug, str) and public_slug.strip():
        item["public_slug"] = public_slug.strip()
    site_url = campaign.get("site_url")
    if isinstance(site_url, str) and site_url.strip():
        item["site_url"] = site_url.strip().rstrip("/")
    processed_path = completion_facts.get("processed_source_relative_path")
    if isinstance(processed_path, str) and processed_path.strip():
        item["processed_source_relative_path"] = normalize_relative_path(processed_path)
    flow_a_completion = completion_facts.get("flow_a_completion")
    if isinstance(flow_a_completion, dict):
        item["flow_a_completion"] = deepcopy(flow_a_completion)
    return item


def _persist_matched_item_completion(
    base_path: Path,
    *,
    calendar: dict[str, Any],
    item_id: str,
    completion_facts: dict[str, Any],
) -> tuple[str, list[str]]:
    completion = complete_flow_a_calendar_item(
        calendar,
        item_id=item_id,
        completion_facts=completion_facts,
    )
    if completion.error_code is not None:
        return CALENDAR_UPDATE_FAILED, [completion.error_code]
    if completion.skipped_already_completed or not completion.requires_persist:
        return CALENDAR_UPDATE_SKIPPED_ALREADY_COMPLETED, []

    expected_fingerprint = calendar_fingerprint(base_path)
    write_errors = save_calendar_atomic(
        base_path,
        completion.calendar,
        expected_fingerprint=expected_fingerprint,
    )
    if write_errors:
        codes = list(write_errors) or [CALENDAR_COMPLETION_WRITE_FAILED]
        return CALENDAR_UPDATE_FAILED, codes
    return CALENDAR_UPDATE_COMPLETED, []


def _update_calendar_from_campaign(
    base_path: Path,
    campaign: dict[str, Any],
    *,
    source_lifecycle_status: str,
) -> tuple[str, list[str]]:
    from silverman_blog_linkedin.editorial_calendar_store import (
        CALENDAR_STORE_NOT_CONFIGURED,
        CALENDAR_STORE_UNAVAILABLE,
    )

    calendar, load_errors = load_calendar(base_path)
    if calendar is None:
        if CALENDAR_STORE_NOT_CONFIGURED in load_errors or CALENDAR_STORE_UNAVAILABLE in load_errors:
            return CALENDAR_UPDATE_SKIPPED_ABSENT, []
        return CALENDAR_UPDATE_FAILED, list(load_errors) or [CALENDAR_SCHEMA_INVALID]

    completion_facts = _build_completion_facts_from_campaign(
        campaign,
        execution_status=EXECUTION_STATUS_EXECUTED,
        source_lifecycle_status=source_lifecycle_status,
    )

    item_id = _resolve_matching_item_id(calendar, campaign)
    if item_id is None:
        new_item = _build_new_calendar_item(campaign, completion_facts=completion_facts)
        existing_ids = {
            str(item.get("item_id"))
            for item in calendar.get("items", [])
            if isinstance(item, dict)
        }
        if new_item["item_id"] in existing_ids:
            return CALENDAR_UPDATE_FAILED, [CALENDAR_SCHEMA_INVALID]
        updated = deepcopy(calendar)
        items = updated.get("items")
        if not isinstance(items, list):
            return CALENDAR_UPDATE_FAILED, [CALENDAR_SCHEMA_INVALID]
        items.append(new_item)
        expected_fingerprint = calendar_fingerprint(base_path)
        write_errors = save_calendar_atomic(
            base_path,
            updated,
            expected_fingerprint=expected_fingerprint,
        )
        if write_errors:
            return CALENDAR_UPDATE_FAILED, list(write_errors)
        return CALENDAR_UPDATE_COMPLETED, []

    return _persist_matched_item_completion(
        base_path,
        calendar=calendar,
        item_id=item_id,
        completion_facts=completion_facts,
    )


def _map_lifecycle_status(lifecycle_status: str, *, already_processed: bool) -> str:
    if lifecycle_status == "failed":
        return SOURCE_LIFECYCLE_FAILED
    if lifecycle_status == "skipped" or already_processed:
        return SOURCE_LIFECYCLE_SKIPPED
    return SOURCE_LIFECYCLE_COMPLETED


def complete_flow_a_ready_path(
    base_path: Path,
    *,
    campaign_id: str,
    source_relative_path: str | None = None,
    update_calendar: bool = True,
) -> FlowAReadyPathCompletionResult:
    """Complete ready-path Flow A: source lifecycle then optional calendar upsert."""
    lifecycle = complete_flow_a_source_lifecycle(
        base_path,
        campaign_id=campaign_id,
        source_relative_path=source_relative_path,
    )
    lifecycle_status = _map_lifecycle_status(
        lifecycle.status,
        already_processed=lifecycle.already_processed,
    )
    errors = list(lifecycle.errors)
    warnings = list(lifecycle.warnings)

    if lifecycle.status == "failed":
        return FlowAReadyPathCompletionResult(
            status=STATUS_FAILED,
            campaign_id=campaign_id,
            source_lifecycle_status=lifecycle_status,
            calendar_update_status=(
                CALENDAR_UPDATE_SKIPPED_NOT_REQUESTED
                if not update_calendar
                else None
            ),
            processed_source_relative_path=lifecycle.processed_source_relative_path,
            already_processed=lifecycle.already_processed,
            errors=errors,
            warnings=warnings,
            lifecycle=lifecycle.to_dict(),
        )

    lifecycle_ok = lifecycle.status in {"completed", "skipped"}
    lifecycle_skipped_complete = (
        lifecycle.status == "skipped" or lifecycle.already_processed
    )

    if not update_calendar:
        calendar_update_status: str | None = CALENDAR_UPDATE_SKIPPED_NOT_REQUESTED
    else:
        campaign = read_campaign_metadata(base_path, campaign_id)
        if campaign is None:
            calendar_update_status = CALENDAR_UPDATE_FAILED
            errors.append("flow_a_source_campaign_not_found")
        else:
            cal_status, cal_errors = _update_calendar_from_campaign(
                base_path,
                campaign,
                # Idempotent lifecycle skip still means lifecycle is complete for calendar facts.
                source_lifecycle_status=SOURCE_LIFECYCLE_COMPLETED,
            )
            calendar_update_status = cal_status
            errors.extend(cal_errors)

    # Spec: skipped when already fully complete and no calendar mutation required.
    if lifecycle_skipped_complete and calendar_update_status in {
        CALENDAR_UPDATE_SKIPPED_ALREADY_COMPLETED,
        CALENDAR_UPDATE_SKIPPED_ABSENT,
        CALENDAR_UPDATE_SKIPPED_NOT_REQUESTED,
    }:
        overall = STATUS_SKIPPED
    elif not lifecycle_ok:
        overall = STATUS_FAILED
    elif calendar_update_status == CALENDAR_UPDATE_FAILED:
        overall = STATUS_PARTIAL
    else:
        overall = STATUS_COMPLETED

    return FlowAReadyPathCompletionResult(
        status=overall,
        campaign_id=campaign_id,
        source_lifecycle_status=lifecycle_status,
        calendar_update_status=calendar_update_status,
        processed_source_relative_path=lifecycle.processed_source_relative_path,
        already_processed=lifecycle.already_processed,
        errors=errors,
        warnings=warnings,
        lifecycle=lifecycle.to_dict(),
    )


__all__ = [
    "CALENDAR_UPDATE_COMPLETED",
    "CALENDAR_UPDATE_FAILED",
    "CALENDAR_UPDATE_SKIPPED_ABSENT",
    "CALENDAR_UPDATE_SKIPPED_ALREADY_COMPLETED",
    "CALENDAR_UPDATE_SKIPPED_NOT_REQUESTED",
    "FlowAReadyPathCompletionResult",
    "STATUS_COMPLETED",
    "STATUS_FAILED",
    "STATUS_PARTIAL",
    "STATUS_SKIPPED",
    "complete_flow_a_ready_path",
]
