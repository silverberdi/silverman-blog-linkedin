"""Flow A execution connector for due editorial calendar items."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.blog_image_generation import (
    BLOG_IMAGE_GENERATION_BACKFILL_FAILED,
    BLOG_IMAGE_GENERATION_DISABLED,
    BLOG_IMAGE_GENERATION_FRONTMATTER_UPDATE_FAILED,
    BLOG_IMAGE_GENERATION_WRITE_FAILED,
)
from silverman_blog_linkedin.blog_publish_flow import (
    BLOG_PUBLISH_CONTENT_HASH_CHANGED,
    BLOG_PUBLISH_HASH_RECONCILIATION_FAILED,
    BLOG_PUBLISH_VALIDATION_FAILED,
    DEFAULT_SITE_URL,
    BlogPublishResult,
    publish_blog_post,
)
from silverman_blog_linkedin.comfyui_client import (
    BLOG_IMAGE_GENERATION_COMFYUI_FAILED,
    BLOG_IMAGE_GENERATION_NOT_CONFIGURED,
    BLOG_IMAGE_GENERATION_TIMEOUT,
)
from silverman_blog_linkedin.github_pages_publish import BLOG_IMAGE_PUBLIC_ASSET_HANDOFF_FAILED
from silverman_blog_linkedin.campaign_lifecycle import (
    EXECUTION_STATE_PROCESSING,
    METADATA_CAMPAIGNS_RELATIVE,
    RECOVERY_REPAIR_REQUIRED,
    RECOVERY_RETRYABLE,
    SOURCE_LOCATION_PROCESSED,
    SOURCE_LOCATION_QUEUED,
    STATE_BLOG_PUBLISHED,
    STATE_DISTRIBUTION_COMPLETE,
    STATE_DISTRIBUTION_SCHEDULED,
    STATE_FLOW_A_COMPLETE,
    normalize_source_file_status,
    read_campaign_metadata,
)
from silverman_blog_linkedin.flow_a_operational_queue import (
    CAMPAIGN_METADATA_WRITE_FAILED,
    QUEUE_ACCEPTANCE_COMPLETED,
    QUEUE_ACCEPTANCE_FAILED,
    QUEUE_ACCEPTANCE_PARTIAL,
    QUEUE_ACCEPTANCE_REPAIR_REQUIRED,
    QUEUE_ACCEPTANCE_SKIPPED_ALREADY_QUEUED,
    accept_flow_a_source_for_queue,
    claim_flow_a_execution,
    error_move_closed_processing_claim,
    move_queued_source_to_error,
    record_flow_a_progress,
    release_flow_a_execution,
)
from silverman_blog_linkedin.editorial_calendar_plan import (
    CALENDAR_COMPLETION_CAMPAIGN_UNRESOLVED,
    CALENDAR_COMPLETION_CONCURRENT_UPDATE,
    CALENDAR_COMPLETION_FACTS_CONFLICT,
    CALENDAR_COMPLETION_WRITE_FAILED,
    CALENDAR_ITEM_NOT_FOUND,
    FLOW_A_READY_BLOG_POST,
    USER_PROVIDED_APPROVED_BLOG,
    EditorialCalendarItemPlan,
    calendar_fingerprint,
    complete_flow_a_calendar_item,
    load_calendar,
    plan_editorial_calendar_due,
    save_calendar_atomic,
)
from silverman_blog_linkedin.file_reader import normalize_relative_path
from silverman_blog_linkedin.run_metadata import utc_now_iso
from silverman_blog_linkedin.flow_a_source_lifecycle import complete_flow_a_source_lifecycle
from silverman_blog_linkedin.linkedin_distribution_schedule import (
    LinkedInDistributionScheduleResult,
    schedule_linkedin_distribution,
)
from silverman_blog_linkedin.linkedin_package_flow import (
    LinkedInPackageResult,
    generate_linkedin_package,
)

EXECUTION_STATUS_EXECUTED = "executed"
EXECUTION_STATUS_RECONCILED = "reconciled"
EXECUTION_STATUS_SKIPPED_EXISTING_CAMPAIGN = "skipped_existing_campaign"
EXECUTION_STATUS_SKIPPED_NOT_FLOW_A = "skipped_not_flow_a"
EXECUTION_STATUS_SKIPPED_REVIEW_REQUIRED = "skipped_review_required"
EXECUTION_STATUS_FAILED = "failed"
EXECUTION_STATUS_WOULD_EXECUTE = "would_execute"

CALENDAR_UPDATE_COMPLETED = "completed"
CALENDAR_UPDATE_RECONCILED = "reconciled"
CALENDAR_UPDATE_SKIPPED_ALREADY_COMPLETED = "skipped_already_completed"
CALENDAR_UPDATE_FAILED = "failed"
CALENDAR_UPDATE_NOT_APPLICABLE = "not_applicable"

FAILED_STEP_QUEUE_ACCEPTANCE = "queue_acceptance"
FAILED_STEP_PUBLISH_BLOG = "publish_blog"
FAILED_STEP_GENERATE_LINKEDIN_PACKAGE = "generate_linkedin_package"
FAILED_STEP_SCHEDULE_LINKEDIN_DISTRIBUTION = "schedule_linkedin_distribution"
FAILED_STEP_COMPLETE_SOURCE_LIFECYCLE = "complete_source_lifecycle"

SOURCE_LIFECYCLE_COMPLETED = "completed"
SOURCE_LIFECYCLE_SKIPPED = "skipped"
SOURCE_LIFECYCLE_FAILED = "failed"

CALENDAR_CAMPAIGN_ID_CONFLICT = "calendar_campaign_id_conflict"

SKIP_EXISTING_CAMPAIGN_STATES = frozenset(
    {
        STATE_DISTRIBUTION_SCHEDULED,
        STATE_DISTRIBUTION_COMPLETE,
    }
)

COUNT_KEYS: tuple[str, ...] = (
    EXECUTION_STATUS_EXECUTED,
    EXECUTION_STATUS_RECONCILED,
    EXECUTION_STATUS_SKIPPED_EXISTING_CAMPAIGN,
    EXECUTION_STATUS_SKIPPED_NOT_FLOW_A,
    EXECUTION_STATUS_SKIPPED_REVIEW_REQUIRED,
    EXECUTION_STATUS_FAILED,
    EXECUTION_STATUS_WOULD_EXECUTE,
)


@dataclass
class EditorialCalendarFlowAItemResult:
    item_id: str
    execution_status: str
    source_relative_path: str | None = None
    review_required: bool = False
    planned_flow_steps: list[str] = field(default_factory=list)
    failed_step: str | None = None
    queue_acceptance_status: str | None = None
    would_queue_accept: bool = False
    source_lifecycle_status: str | None = None
    calendar_update_status: str | None = None
    publish_status: str | None = None
    blog_git_publication: dict[str, Any] | None = None
    blog_live_site_publication: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EditorialCalendarFlowAExecutionResult:
    status: str
    dry_run: bool
    now_utc: str
    calendar_path: str
    calendar_version: str | None = None
    items: list[EditorialCalendarFlowAItemResult] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    read_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _empty_counts() -> dict[str, int]:
    return {key: 0 for key in COUNT_KEYS}


def _increment_count(counts: dict[str, int], execution_status: str) -> None:
    if execution_status in counts:
        counts[execution_status] += 1


def _is_flow_a_eligible(plan_item: EditorialCalendarItemPlan) -> bool:
    return (
        plan_item.flow_type == FLOW_A_READY_BLOG_POST
        and plan_item.content_mode == USER_PROVIDED_APPROVED_BLOG
    )


def _should_skip_in_progress_campaign(
    base_path: Path, calendar_item: dict[str, Any]
) -> bool:
    campaign_id = calendar_item.get("campaign_id")
    if not isinstance(campaign_id, str) or not campaign_id.strip():
        return False
    campaign = read_campaign_metadata(base_path, campaign_id.strip())
    if campaign is None:
        return False
    return campaign.get("state") in SKIP_EXISTING_CAMPAIGN_STATES


@dataclass
class _CompletedCampaignResolution:
    campaign: dict[str, Any] | None = None
    error_code: str | None = None


def _is_flow_a_calendar_item_dict(calendar_item: dict[str, Any]) -> bool:
    return (
        str(calendar_item.get("flow_type", "")) == FLOW_A_READY_BLOG_POST
        and str(calendar_item.get("content_mode", "")) == USER_PROVIDED_APPROVED_BLOG
    )


def _calendar_ready_source_path(calendar_item: dict[str, Any]) -> str | None:
    value = calendar_item.get("source_relative_path")
    if isinstance(value, str) and value.strip():
        return normalize_relative_path(value)
    return None


def _campaign_has_processed_lifecycle_evidence(campaign: dict[str, Any]) -> bool:
    if campaign.get("state") != STATE_FLOW_A_COMPLETE:
        return False
    source_status = normalize_source_file_status(campaign.get("source_file_status"))
    return source_status.get("location") == SOURCE_LOCATION_PROCESSED


def _campaign_identity_consistent_with_calendar(
    calendar_item: dict[str, Any],
    campaign: dict[str, Any],
) -> bool:
    calendar_campaign_id = _calendar_campaign_id(calendar_item)
    campaign_id = campaign.get("campaign_id")
    if calendar_campaign_id and campaign_id and calendar_campaign_id != campaign_id:
        return False

    calendar_public_slug = _optional_calendar_str(calendar_item, "public_slug")
    campaign_public_slug = campaign.get("public_slug")
    if (
        calendar_public_slug
        and isinstance(campaign_public_slug, str)
        and campaign_public_slug.strip()
        and calendar_public_slug != campaign_public_slug.strip()
    ):
        return False

    if (
        calendar_campaign_id
        and campaign_id
        and calendar_campaign_id == campaign_id
        and campaign.get("state") == STATE_FLOW_A_COMPLETE
    ):
        return True

    calendar_ready = _calendar_ready_source_path(calendar_item)
    campaign_ready = campaign.get("source_relative_path")
    if calendar_ready and isinstance(campaign_ready, str) and campaign_ready.strip():
        normalized_campaign_ready = normalize_relative_path(campaign_ready)
        if calendar_ready == normalized_campaign_ready:
            return True
        calendar_name = Path(calendar_ready).name
        for candidate_key in (
            "source_relative_path",
            "queued_source_relative_path",
            "processed_source_relative_path",
        ):
            candidate = campaign.get(candidate_key)
            if isinstance(candidate, str) and candidate.strip():
                if Path(normalize_relative_path(candidate)).name == calendar_name:
                    return True
        return False

    return True


def _processed_source_relative_path_from_campaign(campaign: dict[str, Any]) -> str | None:
    processed = campaign.get("processed_source_relative_path")
    if isinstance(processed, str) and processed.strip():
        return normalize_relative_path(processed)
    source_status = normalize_source_file_status(campaign.get("source_file_status"))
    if source_status.get("location") == SOURCE_LOCATION_PROCESSED:
        fallback = campaign.get("source_relative_path")
        if isinstance(fallback, str) and fallback.strip():
            return normalize_relative_path(fallback)
    return None


def _build_completion_facts_from_campaign(
    campaign: dict[str, Any],
    *,
    execution_status: str,
    source_lifecycle_status: str,
    completed_at_utc: str | None = None,
) -> dict[str, Any]:
    blog_publish = campaign.get("blog_publish") if isinstance(campaign.get("blog_publish"), dict) else {}
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
    processed_path = _processed_source_relative_path_from_campaign(campaign)
    return {
        "campaign_id": campaign.get("campaign_id"),
        "completed_at_utc": completed_at_utc or utc_now_iso(),
        "processed_source_relative_path": processed_path,
        "flow_a_completion": {
            "campaign_state": campaign.get("state"),
            "execution_status": execution_status,
            "source_lifecycle_status": source_lifecycle_status,
            "blog_publish_status": blog_publish.get("status"),
            "public_url": campaign.get("source_public_url"),
            "linkedin_package_status": linkedin_package.get("status"),
            "linkedin_distribution_status": linkedin_distribution.get("status"),
        },
    }


def _list_flow_a_complete_campaigns(base_path: Path) -> list[dict[str, Any]]:
    campaigns_dir = base_path / METADATA_CAMPAIGNS_RELATIVE
    if not campaigns_dir.is_dir():
        return []
    campaigns: list[dict[str, Any]] = []
    for metadata_path in sorted(campaigns_dir.glob("*.json")):
        try:
            campaign = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(campaign, dict):
            continue
        if campaign.get("state") != STATE_FLOW_A_COMPLETE:
            continue
        if not _campaign_has_processed_lifecycle_evidence(campaign):
            continue
        campaigns.append(campaign)
    return campaigns


def _resolve_completed_campaign_for_reconciliation(
    base_path: Path,
    calendar_item: dict[str, Any],
) -> _CompletedCampaignResolution:
    campaign_id = _calendar_campaign_id(calendar_item)
    if campaign_id:
        campaign = read_campaign_metadata(base_path, campaign_id)
        if campaign is None or not _campaign_has_processed_lifecycle_evidence(campaign):
            return _CompletedCampaignResolution()
        if not _campaign_identity_consistent_with_calendar(calendar_item, campaign):
            return _CompletedCampaignResolution()
        return _CompletedCampaignResolution(campaign=campaign)

    calendar_ready = _calendar_ready_source_path(calendar_item)
    if calendar_ready is None:
        return _CompletedCampaignResolution()

    matches: list[dict[str, Any]] = []
    for campaign in _list_flow_a_complete_campaigns(base_path):
        campaign_ready = campaign.get("source_relative_path")
        if not isinstance(campaign_ready, str) or not campaign_ready.strip():
            continue
        if normalize_relative_path(campaign_ready) != calendar_ready:
            continue
        if not _campaign_identity_consistent_with_calendar(calendar_item, campaign):
            continue
        matches.append(campaign)

    if len(matches) == 1:
        return _CompletedCampaignResolution(campaign=matches[0])
    if len(matches) != 1:
        return _CompletedCampaignResolution(
            error_code=CALENDAR_COMPLETION_CAMPAIGN_UNRESOLVED
        )
    return _CompletedCampaignResolution()


def _persist_calendar_item_completion(
    base_path: Path,
    *,
    calendar: dict[str, Any],
    item_id: str,
    completion_facts: dict[str, Any],
    calendar_update_status_on_success: str,
) -> tuple[dict[str, Any], str, list[str], bool]:
    completion = complete_flow_a_calendar_item(
        calendar,
        item_id=item_id,
        completion_facts=completion_facts,
    )
    if completion.error_code == CALENDAR_COMPLETION_FACTS_CONFLICT:
        return calendar, CALENDAR_UPDATE_FAILED, [CALENDAR_COMPLETION_FACTS_CONFLICT], False
    if completion.error_code == CALENDAR_ITEM_NOT_FOUND:
        return calendar, CALENDAR_UPDATE_FAILED, [CALENDAR_ITEM_NOT_FOUND], False
    if completion.error_code is not None:
        return calendar, CALENDAR_UPDATE_FAILED, [completion.error_code], False

    if completion.skipped_already_completed:
        return calendar, CALENDAR_UPDATE_SKIPPED_ALREADY_COMPLETED, [], False

    if not completion.requires_persist:
        return calendar, CALENDAR_UPDATE_SKIPPED_ALREADY_COMPLETED, [], False

    expected_fingerprint = calendar_fingerprint(base_path)
    write_errors = save_calendar_atomic(
        base_path,
        completion.calendar,
        expected_fingerprint=expected_fingerprint,
    )
    if write_errors:
        if CALENDAR_COMPLETION_CONCURRENT_UPDATE in write_errors:
            return (
                calendar,
                CALENDAR_UPDATE_FAILED,
                [CALENDAR_COMPLETION_CONCURRENT_UPDATE],
                False,
            )
        return calendar, CALENDAR_UPDATE_FAILED, [CALENDAR_COMPLETION_WRITE_FAILED], False
    return completion.calendar, calendar_update_status_on_success, [], True


def _try_reconcile_flow_a_calendar_item(
    base_path: Path,
    *,
    calendar: dict[str, Any],
    calendar_item: dict[str, Any],
    plan_item: EditorialCalendarItemPlan,
    dry_run: bool,
) -> tuple[EditorialCalendarFlowAItemResult | None, bool]:
    if not _is_flow_a_calendar_item_dict(calendar_item):
        return None, False

    resolution = _resolve_completed_campaign_for_reconciliation(base_path, calendar_item)
    if resolution.error_code == CALENDAR_COMPLETION_CAMPAIGN_UNRESOLVED:
        return (
            _item_result_from_plan(
                plan_item,
                EXECUTION_STATUS_FAILED,
                calendar_update_status=CALENDAR_UPDATE_FAILED,
                errors=[CALENDAR_COMPLETION_CAMPAIGN_UNRESOLVED],
            ),
            False,
        )
    if resolution.campaign is None:
        return None, False

    campaign = resolution.campaign
    completion_facts = _build_completion_facts_from_campaign(
        campaign,
        execution_status=EXECUTION_STATUS_RECONCILED,
        source_lifecycle_status=SOURCE_LIFECYCLE_COMPLETED,
    )

    if dry_run:
        preview = complete_flow_a_calendar_item(
            calendar,
            item_id=plan_item.item_id,
            completion_facts=completion_facts,
        )
        if preview.error_code == CALENDAR_COMPLETION_FACTS_CONFLICT:
            return (
                _item_result_from_plan(
                    plan_item,
                    EXECUTION_STATUS_FAILED,
                    calendar_update_status=CALENDAR_UPDATE_FAILED,
                    errors=[CALENDAR_COMPLETION_FACTS_CONFLICT],
                ),
                False,
            )
        calendar_update_status = (
            CALENDAR_UPDATE_SKIPPED_ALREADY_COMPLETED
            if preview.skipped_already_completed
            else CALENDAR_UPDATE_RECONCILED
        )
        return (
            _item_result_from_plan(
                plan_item,
                EXECUTION_STATUS_RECONCILED,
                source_relative_path=_calendar_ready_source_path(calendar_item)
                or plan_item.source_relative_path,
                source_lifecycle_status=SOURCE_LIFECYCLE_COMPLETED,
                calendar_update_status=calendar_update_status,
                errors=[],
                warnings=plan_item.warnings,
            ),
            False,
        )

    updated_calendar, calendar_update_status, calendar_errors, persisted = (
        _persist_calendar_item_completion(
            base_path,
            calendar=calendar,
            item_id=plan_item.item_id,
            completion_facts=completion_facts,
            calendar_update_status_on_success=CALENDAR_UPDATE_RECONCILED,
        )
    )
    if calendar_errors:
        return (
            _item_result_from_plan(
                plan_item,
                EXECUTION_STATUS_FAILED,
                calendar_update_status=CALENDAR_UPDATE_FAILED,
                errors=calendar_errors,
            ),
            False,
        )

    calendar.clear()
    calendar.update(updated_calendar)
    return (
        _item_result_from_plan(
            plan_item,
            EXECUTION_STATUS_RECONCILED,
            source_relative_path=_calendar_ready_source_path(calendar_item)
            or plan_item.source_relative_path,
            source_lifecycle_status=SOURCE_LIFECYCLE_COMPLETED,
            calendar_update_status=calendar_update_status,
            errors=[],
            warnings=plan_item.warnings,
        ),
        persisted,
    )


def _apply_post_execution_calendar_completion(
    base_path: Path,
    *,
    calendar: dict[str, Any],
    plan_item: EditorialCalendarItemPlan,
    calendar_item: dict[str, Any] | None,
    item_result: EditorialCalendarFlowAItemResult,
    resolved_campaign_id: str | None = None,
) -> tuple[EditorialCalendarFlowAItemResult, bool]:
    if item_result.execution_status != EXECUTION_STATUS_EXECUTED:
        return _with_calendar_not_applicable(item_result), False
    if item_result.source_lifecycle_status not in (
        SOURCE_LIFECYCLE_COMPLETED,
        SOURCE_LIFECYCLE_SKIPPED,
    ):
        return _with_calendar_not_applicable(item_result), False
    if item_result.failed_step == FAILED_STEP_COMPLETE_SOURCE_LIFECYCLE:
        return _with_calendar_not_applicable(item_result), False

    campaign_id = resolved_campaign_id or _calendar_campaign_id(calendar_item)
    if not campaign_id:
        return _with_calendar_not_applicable(item_result), False

    campaign = read_campaign_metadata(base_path, campaign_id)
    if campaign is None or not _campaign_has_processed_lifecycle_evidence(campaign):
        return _with_calendar_not_applicable(item_result), False
    if calendar_item and not _campaign_identity_consistent_with_calendar(
        calendar_item, campaign
    ):
        return _with_calendar_not_applicable(item_result), False

    completion_facts = _build_completion_facts_from_campaign(
        campaign,
        execution_status=EXECUTION_STATUS_EXECUTED,
        source_lifecycle_status=item_result.source_lifecycle_status or SOURCE_LIFECYCLE_COMPLETED,
    )
    updated_calendar, calendar_update_status, calendar_errors, persisted = (
        _persist_calendar_item_completion(
            base_path,
            calendar=calendar,
            item_id=plan_item.item_id,
            completion_facts=completion_facts,
            calendar_update_status_on_success=CALENDAR_UPDATE_COMPLETED,
        )
    )
    if calendar_errors:
        return (
            EditorialCalendarFlowAItemResult(
                item_id=item_result.item_id,
                execution_status=item_result.execution_status,
                source_relative_path=item_result.source_relative_path,
                review_required=item_result.review_required,
                planned_flow_steps=item_result.planned_flow_steps,
                failed_step=item_result.failed_step,
                queue_acceptance_status=item_result.queue_acceptance_status,
                would_queue_accept=item_result.would_queue_accept,
                source_lifecycle_status=item_result.source_lifecycle_status,
                calendar_update_status=CALENDAR_UPDATE_FAILED,
                publish_status=item_result.publish_status,
                blog_git_publication=item_result.blog_git_publication,
                blog_live_site_publication=item_result.blog_live_site_publication,
                errors=list(dict.fromkeys([*item_result.errors, *calendar_errors])),
                warnings=item_result.warnings,
            ),
            False,
        )

    calendar.clear()
    calendar.update(updated_calendar)
    return (
        EditorialCalendarFlowAItemResult(
            item_id=item_result.item_id,
            execution_status=item_result.execution_status,
            source_relative_path=item_result.source_relative_path,
            review_required=item_result.review_required,
            planned_flow_steps=item_result.planned_flow_steps,
            failed_step=item_result.failed_step,
            queue_acceptance_status=item_result.queue_acceptance_status,
            would_queue_accept=item_result.would_queue_accept,
            source_lifecycle_status=item_result.source_lifecycle_status,
            calendar_update_status=calendar_update_status,
            publish_status=item_result.publish_status,
            blog_git_publication=item_result.blog_git_publication,
            blog_live_site_publication=item_result.blog_live_site_publication,
            errors=item_result.errors,
            warnings=item_result.warnings,
        ),
        persisted,
    )


def _with_calendar_not_applicable(
    item_result: EditorialCalendarFlowAItemResult,
) -> EditorialCalendarFlowAItemResult:
    if item_result.calendar_update_status is not None:
        return item_result
    return EditorialCalendarFlowAItemResult(
        item_id=item_result.item_id,
        execution_status=item_result.execution_status,
        source_relative_path=item_result.source_relative_path,
        review_required=item_result.review_required,
        planned_flow_steps=item_result.planned_flow_steps,
        failed_step=item_result.failed_step,
        queue_acceptance_status=item_result.queue_acceptance_status,
        would_queue_accept=item_result.would_queue_accept,
        source_lifecycle_status=item_result.source_lifecycle_status,
        calendar_update_status=CALENDAR_UPDATE_NOT_APPLICABLE,
        publish_status=item_result.publish_status,
        blog_git_publication=item_result.blog_git_publication,
        blog_live_site_publication=item_result.blog_live_site_publication,
        errors=item_result.errors,
        warnings=item_result.warnings,
    )


def _calendar_item_lookup(calendar: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for item in calendar.get("items", []):
        if isinstance(item, dict) and item.get("item_id"):
            lookup[str(item["item_id"])] = item
    return lookup


def _evaluate_execution_status(
    plan_item: EditorialCalendarItemPlan,
    *,
    base_path: Path,
    calendar_item: dict[str, Any] | None,
) -> str | None:
    """Return skip execution status, or None when the item may execute."""
    if plan_item.selection_status != "selected":
        return EXECUTION_STATUS_SKIPPED_NOT_FLOW_A
    if plan_item.review_required:
        return EXECUTION_STATUS_SKIPPED_REVIEW_REQUIRED
    if not _is_flow_a_eligible(plan_item):
        return EXECUTION_STATUS_SKIPPED_NOT_FLOW_A
    if calendar_item and _should_skip_in_progress_campaign(base_path, calendar_item):
        return EXECUTION_STATUS_SKIPPED_EXISTING_CAMPAIGN
    return None


def _item_result_from_plan(
    plan_item: EditorialCalendarItemPlan,
    execution_status: str,
    *,
    failed_step: str | None = None,
    queue_acceptance_status: str | None = None,
    would_queue_accept: bool = False,
    source_lifecycle_status: str | None = None,
    calendar_update_status: str | None = None,
    source_relative_path: str | None = None,
    publish_status: str | None = None,
    blog_git_publication: dict[str, Any] | None = None,
    blog_live_site_publication: dict[str, Any] | None = None,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
) -> EditorialCalendarFlowAItemResult:
    return EditorialCalendarFlowAItemResult(
        item_id=plan_item.item_id,
        execution_status=execution_status,
        source_relative_path=source_relative_path
        if source_relative_path is not None
        else plan_item.source_relative_path,
        review_required=plan_item.review_required,
        planned_flow_steps=list(plan_item.planned_flow_steps),
        failed_step=failed_step,
        queue_acceptance_status=queue_acceptance_status,
        would_queue_accept=would_queue_accept,
        source_lifecycle_status=source_lifecycle_status,
        calendar_update_status=calendar_update_status,
        publish_status=publish_status,
        blog_git_publication=blog_git_publication,
        blog_live_site_publication=blog_live_site_publication,
        errors=list(errors if errors is not None else plan_item.errors),
        warnings=list(warnings or plan_item.warnings),
    )


def _step_succeeded(status: str) -> bool:
    return status in {"completed", "partial"}


def _campaign_id_conflict(
    calendar_campaign_id: str | None,
    resolved_campaign_id: str | None,
) -> bool:
    if not calendar_campaign_id or not resolved_campaign_id:
        return False
    return calendar_campaign_id != resolved_campaign_id


def _calendar_campaign_id(calendar_item: dict[str, Any] | None) -> str | None:
    if calendar_item is None:
        return None
    value = calendar_item.get("campaign_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _optional_calendar_str(calendar_item: dict[str, Any] | None, key: str) -> str | None:
    if calendar_item is None:
        return None
    value = calendar_item.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _failed_item_from_step(
    plan_item: EditorialCalendarItemPlan,
    *,
    failed_step: str,
    errors: list[str],
    warnings: list[str] | None = None,
) -> EditorialCalendarFlowAItemResult:
    return _item_result_from_plan(
        plan_item,
        EXECUTION_STATUS_FAILED,
        failed_step=failed_step,
        errors=errors,
        warnings=warnings,
    )


def _queue_acceptance_succeeded(status: str, *, metadata_written: bool = True) -> bool:
    if not metadata_written:
        return False
    return status in (
        QUEUE_ACCEPTANCE_COMPLETED,
        QUEUE_ACCEPTANCE_SKIPPED_ALREADY_QUEUED,
    )


def _metadata_persistence_failed(
    *,
    metadata_written: bool,
    metadata_error_code: str | None,
) -> list[str]:
    if metadata_written:
        return []
    return [metadata_error_code or CAMPAIGN_METADATA_WRITE_FAILED]


def _progress_persistence_failed(progress_result) -> list[str]:
    if progress_result is None or progress_result.status != "failed":
        return []
    if progress_result.errors:
        return list(progress_result.errors)
    return [progress_result.metadata_error_code or CAMPAIGN_METADATA_WRITE_FAILED]


def _recovery_after_failure(campaign_id: str | None, base_path: Path) -> str:
    if not campaign_id:
        return RECOVERY_RETRYABLE
    campaign = read_campaign_metadata(base_path, campaign_id)
    if campaign is None:
        return RECOVERY_RETRYABLE
    state = campaign.get("state")
    if state in (STATE_BLOG_PUBLISHED, STATE_DISTRIBUTION_SCHEDULED, STATE_DISTRIBUTION_COMPLETE):
        return RECOVERY_REPAIR_REQUIRED
    return RECOVERY_RETRYABLE


_COMFYUI_TRANSIENT_ERRORS = frozenset(
    {
        BLOG_IMAGE_GENERATION_COMFYUI_FAILED,
        BLOG_IMAGE_GENERATION_TIMEOUT,
        BLOG_IMAGE_GENERATION_NOT_CONFIGURED,
    }
)

_EDITORIAL_IMAGE_REPAIR_ERRORS = frozenset(
    {
        BLOG_IMAGE_GENERATION_BACKFILL_FAILED,
        BLOG_IMAGE_GENERATION_FRONTMATTER_UPDATE_FAILED,
        BLOG_IMAGE_GENERATION_WRITE_FAILED,
    }
)

_IMAGE_REPAIR_ERRORS = frozenset(
    {
        *_EDITORIAL_IMAGE_REPAIR_ERRORS,
        BLOG_IMAGE_PUBLIC_ASSET_HANDOFF_FAILED,
        BLOG_PUBLISH_HASH_RECONCILIATION_FAILED,
        CAMPAIGN_METADATA_WRITE_FAILED,
    }
)


def _publish_failure_is_comfyui_transient(publish_result: BlogPublishResult) -> bool:
    return any(code in _COMFYUI_TRANSIENT_ERRORS for code in publish_result.errors)


def _publish_failure_is_image_repair(publish_result: BlogPublishResult) -> bool:
    return any(code in _IMAGE_REPAIR_ERRORS for code in publish_result.errors)


def _publish_failure_is_deterministic_validation(
    publish_result: BlogPublishResult,
) -> bool:
    validation_errors = set(publish_result.validation.get("errors", []))
    if BLOG_PUBLISH_VALIDATION_FAILED in publish_result.errors:
        return True
    if validation_errors.intersection(
        {
            BLOG_PUBLISH_VALIDATION_FAILED,
            BLOG_PUBLISH_CONTENT_HASH_CHANGED,
        }
    ):
        return True
    return any(
        code.startswith("ready_post_")
        or code.startswith("frontmatter_")
        or code.startswith("content_")
        for code in publish_result.errors
    )


def _publish_failure_last_error(publish_result: BlogPublishResult) -> dict[str, Any]:
    primary = publish_result.errors[0] if publish_result.errors else "publish_failed"
    if primary in _COMFYUI_TRANSIENT_ERRORS:
        category = "image_generation"
    elif primary == BLOG_IMAGE_PUBLIC_ASSET_HANDOFF_FAILED:
        category = "public_asset_handoff"
    elif (
        primary == BLOG_PUBLISH_HASH_RECONCILIATION_FAILED
        or BLOG_PUBLISH_HASH_RECONCILIATION_FAILED in publish_result.errors
    ):
        category = "source_hash_reconciliation"
    elif primary in _EDITORIAL_IMAGE_REPAIR_ERRORS:
        category = "editorial_image_repair"
    elif _publish_failure_is_deterministic_validation(publish_result):
        category = "editorial_validation"
    else:
        category = "transient_runtime"
    return {
        "category": category,
        "error_code": primary,
        "reason": "publish_blog_post failed",
        "at": None,
        "last_successful_stage": "queue_acceptance",
        "attempt_id": None,
    }


def _handle_publish_blog_post_failure(
    base_path: Path,
    *,
    campaign_id: str | None,
    publish_result: BlogPublishResult,
) -> tuple[list[str], list[str], bool]:
    """Apply post-acceptance publish failure policy; return errors, warnings, released."""
    item_errors = list(publish_result.errors)
    item_warnings = list(publish_result.warnings)
    released = False

    if campaign_id and _publish_failure_is_deterministic_validation(publish_result):
        move_result = move_queued_source_to_error(
            base_path,
            campaign_id=campaign_id,
            error_code=(
                publish_result.errors[0]
                if publish_result.errors
                else "editorial_validation_failed"
            ),
            category="editorial_validation",
        )
        item_errors.extend(move_result.errors)
        item_warnings.extend(move_result.warnings)
        item_errors.extend(
            _metadata_persistence_failed(
                metadata_written=move_result.metadata_written,
                metadata_error_code=move_result.metadata_error_code,
            )
        )
        if not error_move_closed_processing_claim(move_result):
            campaign_after = read_campaign_metadata(base_path, campaign_id)
            if campaign_after is not None:
                after_status = normalize_source_file_status(
                    campaign_after.get("source_file_status")
                )
                if after_status.get("execution_state") == EXECUTION_STATE_PROCESSING:
                    release_result = release_flow_a_execution(
                        base_path,
                        campaign_id=campaign_id,
                        recovery_classification=RECOVERY_REPAIR_REQUIRED,
                    )
                    item_errors.extend(release_result.errors)
                    item_errors.extend(
                        _metadata_persistence_failed(
                            metadata_written=release_result.metadata_written,
                            metadata_error_code=release_result.metadata_error_code,
                        )
                    )
                    released = True
        return list(dict.fromkeys(item_errors)), list(dict.fromkeys(item_warnings)), released

    resolved_campaign = publish_result.campaign_id or campaign_id
    if resolved_campaign:
        if _publish_failure_is_comfyui_transient(publish_result):
            recovery = RECOVERY_RETRYABLE
        elif _publish_failure_is_image_repair(publish_result):
            recovery = RECOVERY_REPAIR_REQUIRED
        else:
            recovery = _recovery_after_failure(resolved_campaign, base_path)
        release_result = release_flow_a_execution(
            base_path,
            campaign_id=resolved_campaign,
            recovery_classification=recovery,
            last_error=_publish_failure_last_error(publish_result),
        )
        item_errors.extend(release_result.errors)
        item_errors.extend(
            _metadata_persistence_failed(
                metadata_written=release_result.metadata_written,
                metadata_error_code=release_result.metadata_error_code,
            )
        )
        released = True
    return list(dict.fromkeys(item_errors)), list(dict.fromkeys(item_warnings)), released


def _execute_flow_a_item(
    base_path: Path,
    plan_item: EditorialCalendarItemPlan,
    calendar_item: dict[str, Any] | None,
    *,
    git_publication: bool = False,
    live_site_confirmation: bool = False,
) -> tuple[EditorialCalendarFlowAItemResult, str | None]:
    assert plan_item.source_relative_path is not None

    calendar_campaign = _calendar_campaign_id(calendar_item)
    site_url = _optional_calendar_str(calendar_item, "site_url") or DEFAULT_SITE_URL
    public_slug = _optional_calendar_str(calendar_item, "public_slug")
    topic_theme = _optional_calendar_str(calendar_item, "topic_theme")
    strategy = _optional_calendar_str(calendar_item, "strategy")

    queue_result = accept_flow_a_source_for_queue(
        base_path,
        source_relative_path=plan_item.source_relative_path,
        calendar_item=calendar_item,
        dry_run=False,
    )
    queue_status = queue_result.queue_acceptance_status
    if not _queue_acceptance_succeeded(
        queue_result.status,
        metadata_written=queue_result.metadata_written,
    ):
        queue_errors = list(queue_result.errors)
        queue_errors.extend(
            _metadata_persistence_failed(
                metadata_written=queue_result.metadata_written,
                metadata_error_code=queue_result.metadata_error_code,
            )
        )
        return (
            _item_result_from_plan(
                plan_item,
                EXECUTION_STATUS_FAILED,
                failed_step=FAILED_STEP_QUEUE_ACCEPTANCE,
                queue_acceptance_status=queue_status,
                errors=list(dict.fromkeys(queue_errors)),
                warnings=list(queue_result.warnings),
            ),
            None,
        )

    active_source = queue_result.queued_source_relative_path or plan_item.source_relative_path
    campaign_id = queue_result.campaign_id

    claim_result = claim_flow_a_execution(base_path, campaign_id=campaign_id) if campaign_id else None
    if claim_result and (
        claim_result.status == "failed" or not claim_result.metadata_written
    ):
        claim_errors = list(claim_result.errors)
        claim_errors.extend(
            _metadata_persistence_failed(
                metadata_written=claim_result.metadata_written,
                metadata_error_code=claim_result.metadata_error_code,
            )
        )
        return (
            _item_result_from_plan(
                plan_item,
                EXECUTION_STATUS_FAILED,
                failed_step=FAILED_STEP_QUEUE_ACCEPTANCE,
                queue_acceptance_status=queue_status,
                errors=list(dict.fromkeys(claim_errors)),
            ),
            None,
        )

    if campaign_id:
        progress_result = record_flow_a_progress(base_path, campaign_id=campaign_id)
        progress_errors = _progress_persistence_failed(progress_result)
        if progress_errors:
            release_flow_a_execution(
                base_path,
                campaign_id=campaign_id,
                recovery_classification=RECOVERY_RETRYABLE,
            )
            return (
                _failed_item_from_step(
                    plan_item,
                    failed_step=FAILED_STEP_PUBLISH_BLOG,
                    errors=progress_errors,
                ),
                None,
            )

    publish_result = publish_blog_post(
        base_path,
        active_source,
        site_url=site_url,
        public_slug_override=public_slug,
        git_publication=git_publication,
        live_site_confirmation=live_site_confirmation,
    )
    publish_status = publish_result.status
    publish_git_meta = (
        dict(publish_result.blog_git_publication)
        if publish_result.blog_git_publication
        else None
    )
    publish_live_meta = (
        dict(publish_result.blog_live_site_publication)
        if publish_result.blog_live_site_publication
        else None
    )
    publish_partial_errors = (
        list(publish_result.errors) if publish_result.status == "partial" else []
    )
    if not _step_succeeded(publish_result.status):
        item_errors, item_warnings, _released = _handle_publish_blog_post_failure(
            base_path,
            campaign_id=campaign_id,
            publish_result=publish_result,
        )
        return (
            _item_result_from_plan(
                plan_item,
                EXECUTION_STATUS_FAILED,
                failed_step=FAILED_STEP_PUBLISH_BLOG,
                queue_acceptance_status=queue_status,
                errors=item_errors,
                warnings=item_warnings,
            ),
            None,
        )

    if _campaign_id_conflict(calendar_campaign, publish_result.campaign_id):
        if campaign_id:
            release_flow_a_execution(
                base_path,
                campaign_id=campaign_id,
                recovery_classification=RECOVERY_REPAIR_REQUIRED,
            )
        return (
            _failed_item_from_step(
                plan_item,
                failed_step=FAILED_STEP_PUBLISH_BLOG,
                errors=[CALENDAR_CAMPAIGN_ID_CONFLICT],
                warnings=list(publish_result.warnings),
            ),
            None,
        )

    resolved_campaign = publish_result.campaign_id or campaign_id
    if resolved_campaign:
        progress_result = record_flow_a_progress(base_path, campaign_id=resolved_campaign)
        progress_errors = _progress_persistence_failed(progress_result)
        if progress_errors:
            release_flow_a_execution(
                base_path,
                campaign_id=resolved_campaign,
                recovery_classification=_recovery_after_failure(resolved_campaign, base_path),
            )
            return (
                _failed_item_from_step(
                    plan_item,
                    failed_step=FAILED_STEP_PUBLISH_BLOG,
                    errors=progress_errors,
                    warnings=_merge_warnings(publish_result),
                ),
                None,
            )

    package_result = generate_linkedin_package(
        base_path,
        campaign_id=publish_result.campaign_id,
        source_relative_path=(
            publish_result.source_relative_path
            if not publish_result.campaign_id
            else None
        ),
        site_url=site_url,
        topic_theme=topic_theme,
    )
    if not _step_succeeded(package_result.status):
        if resolved_campaign:
            release_flow_a_execution(
                base_path,
                campaign_id=resolved_campaign,
                recovery_classification=_recovery_after_failure(resolved_campaign, base_path),
            )
        return (
            _failed_item_from_step(
                plan_item,
                failed_step=FAILED_STEP_GENERATE_LINKEDIN_PACKAGE,
                errors=list(package_result.errors),
                warnings=_merge_warnings(publish_result, package_result),
            ),
            None,
        )

    if _campaign_id_conflict(calendar_campaign, package_result.campaign_id):
        if resolved_campaign:
            release_flow_a_execution(
                base_path,
                campaign_id=campaign_id or resolved_campaign,
                recovery_classification=RECOVERY_REPAIR_REQUIRED,
            )
        return (
            _failed_item_from_step(
                plan_item,
                failed_step=FAILED_STEP_GENERATE_LINKEDIN_PACKAGE,
                errors=[CALENDAR_CAMPAIGN_ID_CONFLICT],
                warnings=_merge_warnings(publish_result, package_result),
            ),
            None,
        )

    if resolved_campaign:
        progress_result = record_flow_a_progress(base_path, campaign_id=resolved_campaign)
        progress_errors = _progress_persistence_failed(progress_result)
        if progress_errors:
            release_flow_a_execution(
                base_path,
                campaign_id=resolved_campaign,
                recovery_classification=_recovery_after_failure(resolved_campaign, base_path),
            )
            return (
                _failed_item_from_step(
                    plan_item,
                    failed_step=FAILED_STEP_GENERATE_LINKEDIN_PACKAGE,
                    errors=progress_errors,
                    warnings=_merge_warnings(publish_result, package_result),
                ),
                None,
            )

    schedule_result = schedule_linkedin_distribution(
        base_path,
        campaign_id=package_result.campaign_id,
        source_relative_path=(
            package_result.source_relative_path
            if not package_result.campaign_id
            else None
        ),
        strategy=strategy,
    )
    if not _step_succeeded(schedule_result.status):
        if resolved_campaign:
            release_flow_a_execution(
                base_path,
                campaign_id=resolved_campaign,
                recovery_classification=RECOVERY_REPAIR_REQUIRED,
            )
        return (
            _failed_item_from_step(
                plan_item,
                failed_step=FAILED_STEP_SCHEDULE_LINKEDIN_DISTRIBUTION,
                errors=list(schedule_result.errors),
                warnings=_merge_warnings(publish_result, package_result, schedule_result),
            ),
            None,
        )

    if resolved_campaign:
        progress_result = record_flow_a_progress(base_path, campaign_id=resolved_campaign)
        progress_errors = _progress_persistence_failed(progress_result)
        if progress_errors:
            release_flow_a_execution(
                base_path,
                campaign_id=resolved_campaign,
                recovery_classification=RECOVERY_REPAIR_REQUIRED,
            )
            return (
                _failed_item_from_step(
                    plan_item,
                    failed_step=FAILED_STEP_SCHEDULE_LINKEDIN_DISTRIBUTION,
                    errors=progress_errors,
                    warnings=_merge_warnings(publish_result, package_result, schedule_result),
                ),
                None,
            )

    lifecycle_campaign_id = (
        schedule_result.campaign_id
        or package_result.campaign_id
        or publish_result.campaign_id
        or campaign_id
    )
    if not lifecycle_campaign_id:
        return (
            _item_result_from_plan(
                plan_item,
                EXECUTION_STATUS_EXECUTED,
                queue_acceptance_status=queue_status,
                source_lifecycle_status=SOURCE_LIFECYCLE_FAILED,
                errors=["flow_a_source_campaign_not_found"],
                warnings=_merge_warnings(publish_result, package_result, schedule_result),
            ),
            None,
        )

    lifecycle_result = complete_flow_a_source_lifecycle(
        base_path,
        campaign_id=lifecycle_campaign_id,
        source_relative_path=active_source,
    )
    lifecycle_warnings = _merge_warnings(publish_result, package_result, schedule_result)
    lifecycle_warnings = list(
        dict.fromkeys([*lifecycle_warnings, *lifecycle_result.warnings])
    )
    lifecycle_errors = list(lifecycle_result.errors)

    if lifecycle_result.status == SOURCE_LIFECYCLE_FAILED:
        if lifecycle_campaign_id:
            release_flow_a_execution(
                base_path,
                campaign_id=lifecycle_campaign_id,
                recovery_classification=RECOVERY_REPAIR_REQUIRED,
            )
        lifecycle_warnings = list(dict.fromkeys([*lifecycle_warnings, *lifecycle_errors]))
        return (
            _item_result_from_plan(
                plan_item,
                EXECUTION_STATUS_EXECUTED,
                failed_step=FAILED_STEP_COMPLETE_SOURCE_LIFECYCLE,
                queue_acceptance_status=queue_status,
                source_lifecycle_status=SOURCE_LIFECYCLE_FAILED,
                errors=lifecycle_errors,
                warnings=lifecycle_warnings,
            ),
            lifecycle_campaign_id,
        )

    if lifecycle_campaign_id:
        record_flow_a_progress(base_path, campaign_id=lifecycle_campaign_id)
        release_flow_a_execution(base_path, campaign_id=lifecycle_campaign_id)

    source_lifecycle_status = (
        SOURCE_LIFECYCLE_SKIPPED
        if lifecycle_result.status == SOURCE_LIFECYCLE_SKIPPED
        else SOURCE_LIFECYCLE_COMPLETED
    )
    return (
        _item_result_from_plan(
            plan_item,
            EXECUTION_STATUS_EXECUTED,
            queue_acceptance_status=queue_status,
            source_lifecycle_status=source_lifecycle_status,
            publish_status=publish_status,
            blog_git_publication=publish_git_meta,
            blog_live_site_publication=publish_live_meta,
            errors=publish_partial_errors,
            warnings=lifecycle_warnings,
        ),
        lifecycle_campaign_id,
    )


def _merge_warnings(*results: BlogPublishResult | LinkedInPackageResult | LinkedInDistributionScheduleResult) -> list[str]:
    merged: list[str] = []
    for result in results:
        merged.extend(result.warnings)
    return list(dict.fromkeys(merged))


def _aggregate_execution_status(
    planner_status: str,
    item_results: list[EditorialCalendarFlowAItemResult],
) -> str:
    if planner_status in ("calendar_missing", "calendar_invalid", "no_due_items"):
        return planner_status
    if not item_results:
        return planner_status

    if any(
        item.execution_status == EXECUTION_STATUS_EXECUTED
        and item.calendar_update_status == CALENDAR_UPDATE_FAILED
        for item in item_results
    ):
        return "partial"

    statuses = {item.execution_status for item in item_results}
    if EXECUTION_STATUS_FAILED in statuses:
        return "partial"

    actionable = {
        EXECUTION_STATUS_EXECUTED,
        EXECUTION_STATUS_RECONCILED,
        EXECUTION_STATUS_WOULD_EXECUTE,
    }
    skips = {
        EXECUTION_STATUS_SKIPPED_EXISTING_CAMPAIGN,
        EXECUTION_STATUS_SKIPPED_NOT_FLOW_A,
        EXECUTION_STATUS_SKIPPED_REVIEW_REQUIRED,
    }
    if (statuses & actionable) and (statuses & skips):
        return "partial"
    return "completed"


def execute_due_editorial_calendar_flow_a(
    base_path: Path,
    *,
    now_utc: str | None = None,
    dry_run: bool = True,
    limit: int | None = None,
    git_publication: bool = False,
    live_site_confirmation: bool = False,
) -> EditorialCalendarFlowAExecutionResult:
    """Plan due calendar items and simulate or execute Flow A for eligible entries."""
    plan = plan_editorial_calendar_due(base_path, now_utc=now_utc)

    if plan.status in ("calendar_missing", "calendar_invalid", "no_due_items"):
        return EditorialCalendarFlowAExecutionResult(
            status=plan.status,
            dry_run=dry_run,
            now_utc=plan.now_utc,
            calendar_path=plan.calendar_path,
            calendar_version=plan.calendar_version,
            items=[],
            counts=_empty_counts(),
            errors=list(plan.errors),
            warnings=list(plan.warnings),
            read_only=True,
        )

    calendar, _ = load_calendar(base_path)
    if calendar is None:
        calendar = {"schema_version": "1", "updated_at_utc": plan.now_utc, "items": []}
    calendar_lookup = _calendar_item_lookup(calendar)

    counts = _empty_counts()
    item_results: list[EditorialCalendarFlowAItemResult] = []
    eligible_processed = 0
    calendar_written = False

    for plan_item in plan.due_items:
        calendar_item = calendar_lookup.get(plan_item.item_id)

        if calendar_item is not None:
            reconcile_result, calendar_persisted = _try_reconcile_flow_a_calendar_item(
                base_path,
                calendar=calendar,
                calendar_item=calendar_item,
                plan_item=plan_item,
                dry_run=dry_run,
            )
            if reconcile_result is not None:
                item_results.append(reconcile_result)
                _increment_count(counts, reconcile_result.execution_status)
                calendar_written = calendar_written or calendar_persisted
                continue

        skip_status = _evaluate_execution_status(
            plan_item,
            base_path=base_path,
            calendar_item=calendar_item,
        )
        if skip_status is not None:
            result = _with_calendar_not_applicable(
                _item_result_from_plan(plan_item, skip_status)
            )
            item_results.append(result)
            _increment_count(counts, skip_status)
            continue

        if limit is not None and eligible_processed >= limit:
            continue

        eligible_processed += 1

        if dry_run:
            would_accept = False
            queue_status = None
            if plan_item.source_relative_path:
                preview = accept_flow_a_source_for_queue(
                    base_path,
                    source_relative_path=plan_item.source_relative_path,
                    calendar_item=calendar_item,
                    dry_run=True,
                )
                would_accept = preview.would_queue_accept
                queue_status = preview.queue_acceptance_status
            result = _with_calendar_not_applicable(
                _item_result_from_plan(
                    plan_item,
                    EXECUTION_STATUS_WOULD_EXECUTE,
                    queue_acceptance_status=queue_status,
                    would_queue_accept=would_accept,
                )
            )
            item_results.append(result)
            _increment_count(counts, EXECUTION_STATUS_WOULD_EXECUTE)
            continue

        item_result, resolved_campaign_id = _execute_flow_a_item(
            base_path,
            plan_item,
            calendar_item,
            git_publication=git_publication,
            live_site_confirmation=live_site_confirmation,
        )
        item_result, calendar_persisted = _apply_post_execution_calendar_completion(
            base_path,
            calendar=calendar,
            plan_item=plan_item,
            calendar_item=calendar_item,
            item_result=item_result,
            resolved_campaign_id=resolved_campaign_id,
        )
        calendar_written = calendar_written or calendar_persisted
        item_results.append(item_result)
        _increment_count(counts, item_result.execution_status)

    return EditorialCalendarFlowAExecutionResult(
        status=_aggregate_execution_status(plan.status, item_results),
        dry_run=dry_run,
        now_utc=plan.now_utc,
        calendar_path=plan.calendar_path,
        calendar_version=plan.calendar_version,
        items=item_results,
        counts=counts,
        errors=list(plan.errors),
        warnings=list(plan.warnings),
        read_only=not calendar_written,
    )
