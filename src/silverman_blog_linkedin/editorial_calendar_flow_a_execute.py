"""Flow A execution connector for due editorial calendar items."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.blog_publish_flow import (
    DEFAULT_SITE_URL,
    BlogPublishResult,
    publish_blog_post,
)
from silverman_blog_linkedin.campaign_lifecycle import (
    STATE_DISTRIBUTION_COMPLETE,
    STATE_DISTRIBUTION_SCHEDULED,
    STATE_FLOW_A_COMPLETE,
    read_campaign_metadata,
)
from silverman_blog_linkedin.editorial_calendar_plan import (
    FLOW_A_READY_BLOG_POST,
    USER_PROVIDED_APPROVED_BLOG,
    EditorialCalendarItemPlan,
    load_calendar,
    plan_editorial_calendar_due,
)
from silverman_blog_linkedin.linkedin_distribution_schedule import (
    LinkedInDistributionScheduleResult,
    schedule_linkedin_distribution,
)
from silverman_blog_linkedin.linkedin_package_flow import (
    LinkedInPackageResult,
    generate_linkedin_package,
)

EXECUTION_STATUS_EXECUTED = "executed"
EXECUTION_STATUS_SKIPPED_EXISTING_CAMPAIGN = "skipped_existing_campaign"
EXECUTION_STATUS_SKIPPED_NOT_FLOW_A = "skipped_not_flow_a"
EXECUTION_STATUS_SKIPPED_REVIEW_REQUIRED = "skipped_review_required"
EXECUTION_STATUS_FAILED = "failed"
EXECUTION_STATUS_WOULD_EXECUTE = "would_execute"

FAILED_STEP_PUBLISH_BLOG = "publish_blog"
FAILED_STEP_GENERATE_LINKEDIN_PACKAGE = "generate_linkedin_package"
FAILED_STEP_SCHEDULE_LINKEDIN_DISTRIBUTION = "schedule_linkedin_distribution"

CALENDAR_CAMPAIGN_ID_CONFLICT = "calendar_campaign_id_conflict"

POST_DISTRIBUTION_SCHEDULED_STATES = frozenset(
    {
        STATE_DISTRIBUTION_SCHEDULED,
        STATE_DISTRIBUTION_COMPLETE,
        STATE_FLOW_A_COMPLETE,
    }
)

COUNT_KEYS: tuple[str, ...] = (
    EXECUTION_STATUS_EXECUTED,
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


def _should_skip_existing_campaign(
    base_path: Path, calendar_item: dict[str, Any]
) -> bool:
    campaign_id = calendar_item.get("campaign_id")
    if not isinstance(campaign_id, str) or not campaign_id.strip():
        return False
    campaign = read_campaign_metadata(base_path, campaign_id.strip())
    if campaign is None:
        return False
    return campaign.get("state") in POST_DISTRIBUTION_SCHEDULED_STATES


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
    if calendar_item and _should_skip_existing_campaign(base_path, calendar_item):
        return EXECUTION_STATUS_SKIPPED_EXISTING_CAMPAIGN
    return None


def _item_result_from_plan(
    plan_item: EditorialCalendarItemPlan,
    execution_status: str,
    *,
    failed_step: str | None = None,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
) -> EditorialCalendarFlowAItemResult:
    return EditorialCalendarFlowAItemResult(
        item_id=plan_item.item_id,
        execution_status=execution_status,
        source_relative_path=plan_item.source_relative_path,
        review_required=plan_item.review_required,
        planned_flow_steps=list(plan_item.planned_flow_steps),
        failed_step=failed_step,
        errors=list(errors or plan_item.errors),
        warnings=list(warnings or plan_item.warnings),
    )


def _step_succeeded(status: str) -> bool:
    return status == "completed"


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


def _execute_flow_a_item(
    base_path: Path,
    plan_item: EditorialCalendarItemPlan,
    calendar_item: dict[str, Any] | None,
) -> EditorialCalendarFlowAItemResult:
    assert plan_item.source_relative_path is not None

    calendar_campaign = _calendar_campaign_id(calendar_item)
    site_url = _optional_calendar_str(calendar_item, "site_url") or DEFAULT_SITE_URL
    public_slug = _optional_calendar_str(calendar_item, "public_slug")
    topic_theme = _optional_calendar_str(calendar_item, "topic_theme")
    strategy = _optional_calendar_str(calendar_item, "strategy")

    publish_result = publish_blog_post(
        base_path,
        plan_item.source_relative_path,
        site_url=site_url,
        public_slug_override=public_slug,
    )
    if not _step_succeeded(publish_result.status):
        return _failed_item_from_step(
            plan_item,
            failed_step=FAILED_STEP_PUBLISH_BLOG,
            errors=list(publish_result.errors),
            warnings=list(publish_result.warnings),
        )

    if _campaign_id_conflict(calendar_campaign, publish_result.campaign_id):
        return _failed_item_from_step(
            plan_item,
            failed_step=FAILED_STEP_PUBLISH_BLOG,
            errors=[CALENDAR_CAMPAIGN_ID_CONFLICT],
            warnings=list(publish_result.warnings),
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
        return _failed_item_from_step(
            plan_item,
            failed_step=FAILED_STEP_GENERATE_LINKEDIN_PACKAGE,
            errors=list(package_result.errors),
            warnings=_merge_warnings(publish_result, package_result),
        )

    if _campaign_id_conflict(calendar_campaign, package_result.campaign_id):
        return _failed_item_from_step(
            plan_item,
            failed_step=FAILED_STEP_GENERATE_LINKEDIN_PACKAGE,
            errors=[CALENDAR_CAMPAIGN_ID_CONFLICT],
            warnings=_merge_warnings(publish_result, package_result),
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
        return _failed_item_from_step(
            plan_item,
            failed_step=FAILED_STEP_SCHEDULE_LINKEDIN_DISTRIBUTION,
            errors=list(schedule_result.errors),
            warnings=_merge_warnings(publish_result, package_result, schedule_result),
        )

    return _item_result_from_plan(
        plan_item,
        EXECUTION_STATUS_EXECUTED,
        errors=[],
        warnings=_merge_warnings(publish_result, package_result, schedule_result),
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

    statuses = {item.execution_status for item in item_results}
    if EXECUTION_STATUS_FAILED in statuses:
        return "partial"

    actionable = {EXECUTION_STATUS_EXECUTED, EXECUTION_STATUS_WOULD_EXECUTE}
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
    calendar_lookup = _calendar_item_lookup(calendar or {})

    counts = _empty_counts()
    item_results: list[EditorialCalendarFlowAItemResult] = []
    eligible_processed = 0

    for plan_item in plan.due_items:
        calendar_item = calendar_lookup.get(plan_item.item_id)
        skip_status = _evaluate_execution_status(
            plan_item,
            base_path=base_path,
            calendar_item=calendar_item,
        )
        if skip_status is not None:
            result = _item_result_from_plan(plan_item, skip_status)
            item_results.append(result)
            _increment_count(counts, skip_status)
            continue

        if limit is not None and eligible_processed >= limit:
            continue

        eligible_processed += 1

        if dry_run:
            result = _item_result_from_plan(plan_item, EXECUTION_STATUS_WOULD_EXECUTE)
            item_results.append(result)
            _increment_count(counts, EXECUTION_STATUS_WOULD_EXECUTE)
            continue

        result = _execute_flow_a_item(base_path, plan_item, calendar_item)
        item_results.append(result)
        _increment_count(counts, result.execution_status)

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
        read_only=dry_run,
    )
