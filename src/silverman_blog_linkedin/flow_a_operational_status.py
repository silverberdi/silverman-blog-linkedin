"""Read-only aggregation of persisted Flow A operational evidence."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.campaign_lifecycle import (
    EXECUTION_STATE_IDLE,
    EXECUTION_STATE_PROCESSING,
    EXECUTION_STATE_STALE,
    EXECUTION_STATES,
    FLOW_A,
    LIFECYCLE_STATES,
    RECOVERY_CLASSIFICATIONS,
    RECOVERY_MANUAL_INTERVENTION_REQUIRED,
    RECOVERY_REPAIR_REQUIRED,
    RECOVERY_REQUEUE_REQUIRED,
    SOURCE_LOCATION_ERROR,
    SOURCE_LOCATION_PROCESSED,
    SOURCE_LOCATIONS,
    STATE_ERROR,
    STATE_FLOW_A_COMPLETE,
    STATE_VALIDATION_FAILED,
    CampaignLifecycleError,
    normalize_source_file_status,
    read_campaign_metadata,
    validate_campaign_id,
)
from silverman_blog_linkedin.editorial_calendar_plan import (
    ALLOWED_STATUSES,
    CALENDAR_FILE_NOT_FOUND,
    CALENDAR_RELATIVE_PATH,
    CALENDAR_SCHEMA_INVALID,
    load_calendar,
    validate_canonical_utc_timestamp,
)
from silverman_blog_linkedin.flow_a_config import (
    load_flow_a_processing_stale_seconds,
)
from silverman_blog_linkedin.run_metadata import (
    METADATA_RUNS_RELATIVE,
    utc_now_iso,
)

RUNS_SOURCE = "runs"
CAMPAIGNS_SOURCE = "campaigns"
CALENDAR_SOURCE = "calendar"

RUNS_DIRECTORY_NOT_FOUND = "runs_directory_not_found"
RUNS_DIRECTORY_INVALID = "runs_directory_invalid"
RUN_FILE_PATH_OUTSIDE_SOURCE = "run_file_path_outside_source"
RUN_FILE_INVALID = "run_file_invalid"
RUN_DOCUMENT_INVALID = "run_document_invalid"
RUN_IDENTIFIER_INVALID = "run_identifier_invalid"
RUN_IDENTIFIER_MISMATCH = "run_identifier_mismatch"
RUN_STATUS_INVALID = "run_status_invalid"
RUN_TRIGGER_INVALID = "run_trigger_invalid"
RUN_TIMESTAMP_INVALID = "run_timestamp_invalid"
RUN_ERROR_CODE_INVALID = "run_error_code_invalid"
RUN_CLOCK_INVERTED = "run_clock_inverted"

CAMPAIGNS_DIRECTORY_NOT_FOUND = "campaigns_directory_not_found"
CAMPAIGNS_DIRECTORY_INVALID = "campaigns_directory_invalid"
CAMPAIGN_FILE_PATH_OUTSIDE_SOURCE = "campaign_file_path_outside_source"
CAMPAIGN_FILE_INVALID = "campaign_file_invalid"
CAMPAIGN_ID_INVALID = "campaign_id_invalid"
CAMPAIGN_ID_FILENAME_MISMATCH = "campaign_id_filename_mismatch"
CAMPAIGN_STATE_INVALID = "campaign_state_invalid"
CAMPAIGN_SOURCE_STATUS_INVALID = "campaign_source_status_invalid"
CAMPAIGN_TIMESTAMP_INVALID = "campaign_timestamp_invalid"
CAMPAIGN_ATTEMPT_EVIDENCE_INVALID = "campaign_attempt_evidence_invalid"
CAMPAIGN_ERROR_CODE_INVALID = "campaign_error_code_invalid"
CAMPAIGN_STAGE_HISTORY_INVALID = "campaign_stage_history_invalid"
CAMPAIGN_STAGE_CLOCK_INVERTED = "campaign_stage_clock_inverted"
CAMPAIGN_STAGE_HISTORY_STATE_INCONSISTENT = (
    "campaign_stage_history_state_inconsistent"
)
CAMPAIGN_ATTEMPT_CLOCK_INVERTED = "campaign_attempt_clock_inverted"

LINKEDIN_DISTRIBUTION_INVALID = "linkedin_distribution_invalid"
LINKEDIN_VARIANTS_INVALID = "linkedin_variants_invalid"
LINKEDIN_VARIANT_INVALID = "linkedin_variant_invalid"
LINKEDIN_PUBLISH_STATE_INVALID = "linkedin_publish_state_invalid"
LINKEDIN_TIMESTAMP_INVALID = "linkedin_timestamp_invalid"
LINKEDIN_ERROR_CODE_INVALID = "linkedin_error_code_invalid"

CALENDAR_PATH_OUTSIDE_SOURCE = "calendar_path_outside_source"
CALENDAR_ITEM_PAST_DUE = "calendar_item_past_due"

PUBLISH_STATES = ("pending", "queued", "published", "failed", "cancelled")

DEPENDENCY_COMFYUI = "comfyui"
DEPENDENCY_DEEPSEEK = "deepseek"
DEPENDENCY_LINKEDIN = "linkedin"
DEPENDENCY_GITHUB_PAGES_CHECKOUT = "github_pages_checkout"
DEPENDENCY_UNCLASSIFIED = "unclassified"
DEPENDENCY_BUCKETS = (
    DEPENDENCY_COMFYUI,
    DEPENDENCY_DEEPSEEK,
    DEPENDENCY_GITHUB_PAGES_CHECKOUT,
    DEPENDENCY_LINKEDIN,
    DEPENDENCY_UNCLASSIFIED,
)

# Checkout-named families take precedence over the general linkedin_* family.
_GITHUB_PAGES_CHECKOUT_PREFIXES = (
    "blog_publish_",
    "blog_git_publication_",
    "checkout_",
    "linkedin_preview_validation_checkout_",
)
_GITHUB_PAGES_CHECKOUT_EXACT = frozenset(
    {"linkedin_article_preview_public_repo_not_configured"}
)
_COMFYUI_PREFIXES = ("comfyui_", "blog_image_generation_")
_DEEPSEEK_PREFIXES = ("deepseek_",)
_LINKEDIN_PREFIXES = ("linkedin_",)
DELAY_ELIGIBLE_STATUSES = frozenset(
    {"planned", "scheduled", "due", "in_progress"}
)
TERMINAL_CALENDAR_STATUSES = frozenset({"completed", "skipped", "failed"})
BLOCKING_RECOVERY_CLASSIFICATIONS = frozenset(
    {
        RECOVERY_REPAIR_REQUIRED,
        RECOVERY_REQUEUE_REQUIRED,
        RECOVERY_MANUAL_INTERVENTION_REQUIRED,
    }
)

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")
_SAFE_ERROR_CODE = re.compile(r"^[a-z][a-z0-9_]{0,127}$")
_SAFE_TRIGGER = re.compile(r"^(?:GET|POST) /[a-z0-9][a-z0-9/-]*$")


@dataclass(frozen=True)
class DataIssue:
    source: str
    identifier: str | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExecutionSummary:
    run_id: str
    trigger: str | None
    status: str
    outcome: str
    started_at: str | None
    completed_at: str | None
    duration_seconds: int | None = None
    error_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StageDurationSummary:
    stage: str
    started_at: str
    ended_at: str | None
    duration_seconds: int | None
    open: bool
    from_state: str | None = None
    to_state: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CampaignDependencyFailureSummary:
    dependency: str
    error_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DependencyFailureEntry:
    dependency: str
    failure_count: int
    error_codes: list[str] = field(default_factory=list)
    campaign_ids: list[str] = field(default_factory=list)
    run_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LinkedInProgressSummary:
    publish_state_counts: dict[str, int]
    strategy: str | None = None
    anchor_utc: str | None = None
    earliest_pending_scheduled_at_utc: str | None = None
    earliest_queued_publish_after_utc: str | None = None
    latest_published_at: str | None = None
    elapsed_pending_scheduled_windows: int = 0
    elapsed_queued_publish_windows: int = 0
    failure_codes: list[str] = field(default_factory=list)
    elapsed_windows_are_descriptive_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CampaignSummary:
    campaign_id: str
    state: str
    updated_at: str | None
    location: str
    execution_state: str
    recovery_classification: str
    successful: bool
    failed: bool
    blocked: bool
    stale: bool
    in_progress: bool
    health_reasons: list[str]
    execution_attempt_id: str | None
    attempt_count: int | None
    processing_started_at: str | None
    last_progress_at: str | None
    processing_lease_expires_at: str | None
    last_transition_at: str | None
    last_error_code: str | None
    linkedin: LinkedInProgressSummary
    attempt_duration_seconds: int | None = None
    stage_durations: list[StageDurationSummary] = field(default_factory=list)
    dependency_failures: list[CampaignDependencyFailureSummary] = field(
        default_factory=list
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DelayedCalendarItemSummary:
    item_id: str
    title: str
    status: str
    due_at_utc: str
    flow_type: str
    campaign_id: str | None
    reason: str = CALENDAR_ITEM_PAST_DUE

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FlowAOperationalStatusResult:
    status: str
    observed_at_utc: str
    stale_after_seconds: int
    summary: dict[str, Any]
    executions: dict[str, list[ExecutionSummary]]
    campaigns: list[CampaignSummary]
    delayed_calendar_items: list[DelayedCalendarItemSummary]
    dependency_failures: list[DependencyFailureEntry]
    data_issues: list[DataIssue]
    read_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "observed_at_utc": self.observed_at_utc,
            "read_only": self.read_only,
            "stale_after_seconds": self.stale_after_seconds,
            "summary": self.summary,
            "executions": {
                outcome: [item.to_dict() for item in items]
                for outcome, items in self.executions.items()
            },
            "campaigns": [item.to_dict() for item in self.campaigns],
            "delayed_calendar_items": [
                item.to_dict() for item in self.delayed_calendar_items
            ],
            "dependency_failures": [
                item.to_dict() for item in self.dependency_failures
            ],
            "data_issues": [item.to_dict() for item in self.data_issues],
        }


def _parse_canonical_utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        canonical = validate_canonical_utc_timestamp(value)
        return datetime.strptime(canonical, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


def _validated_timestamp(
    value: Any,
    *,
    source: str,
    identifier: str | None,
    reason: str,
    issues: list[DataIssue],
) -> str | None:
    parsed = _parse_canonical_utc(value)
    if parsed is None:
        if value is not None:
            issues.append(DataIssue(source, identifier, reason))
        return None
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_identifier(value: Any) -> str | None:
    if isinstance(value, str) and _SAFE_IDENTIFIER.fullmatch(value):
        return value
    return None


def _safe_error_code(value: Any) -> str | None:
    if isinstance(value, str) and _SAFE_ERROR_CODE.fullmatch(value):
        return value
    return None


def _safe_artifact_identifier(path: Path) -> str | None:
    return path.name if _SAFE_IDENTIFIER.fullmatch(path.name) else None


def _whole_seconds_between(
    start: Any,
    end: Any,
    *,
    source: str,
    identifier: str | None,
    inverted_reason: str,
    issues: list[DataIssue],
) -> int | None:
    """Whole-second difference between canonical UTC clocks.

    Returns None without an issue when either clock is absent or unparsable
    (unparsable values are reported by the callers' timestamp validation).
    Inverted clocks are rejected with a stable data issue.
    """
    start_parsed = _parse_canonical_utc(start)
    end_parsed = _parse_canonical_utc(end)
    if start_parsed is None or end_parsed is None:
        return None
    if end_parsed < start_parsed:
        issues.append(DataIssue(source, identifier, inverted_reason))
        return None
    return int((end_parsed - start_parsed).total_seconds())


def _classify_dependency(error_code: str) -> str:
    if error_code in _GITHUB_PAGES_CHECKOUT_EXACT or error_code.startswith(
        _GITHUB_PAGES_CHECKOUT_PREFIXES
    ):
        return DEPENDENCY_GITHUB_PAGES_CHECKOUT
    if error_code.startswith(_COMFYUI_PREFIXES):
        return DEPENDENCY_COMFYUI
    if error_code.startswith(_DEEPSEEK_PREFIXES):
        return DEPENDENCY_DEEPSEEK
    if error_code.startswith(_LINKEDIN_PREFIXES):
        return DEPENDENCY_LINKEDIN
    return DEPENDENCY_UNCLASSIFIED


def _lifecycle_state_or_none(value: Any) -> str | None:
    if isinstance(value, str) and value in LIFECYCLE_STATES:
        return value
    return None


def _stage_durations(
    campaign: dict[str, Any],
    *,
    campaign_id: str,
    campaign_state: str,
    observed_at: datetime,
    issues: list[DataIssue],
) -> list[StageDurationSummary]:
    raw_history = campaign.get("state_history")
    if raw_history is None:
        return []
    if not isinstance(raw_history, list):
        issues.append(
            DataIssue(
                CAMPAIGNS_SOURCE,
                campaign_id,
                CAMPAIGN_STAGE_HISTORY_INVALID,
            )
        )
        return []

    valid_entries: list[tuple[str, str | None, str]] = []
    for entry in raw_history:
        if not isinstance(entry, dict):
            issues.append(
                DataIssue(
                    CAMPAIGNS_SOURCE,
                    campaign_id,
                    CAMPAIGN_STAGE_HISTORY_INVALID,
                )
            )
            continue
        at = _parse_canonical_utc(entry.get("at"))
        to_state = _lifecycle_state_or_none(entry.get("to_state"))
        from_state_raw = entry.get("from_state")
        from_state = _lifecycle_state_or_none(from_state_raw)
        if (
            at is None
            or to_state is None
            or (from_state_raw is not None and from_state is None)
        ):
            issues.append(
                DataIssue(
                    CAMPAIGNS_SOURCE,
                    campaign_id,
                    CAMPAIGN_STAGE_HISTORY_INVALID,
                )
            )
            continue
        valid_entries.append(
            (at.strftime("%Y-%m-%dT%H:%M:%SZ"), from_state, to_state)
        )

    if not valid_entries:
        return []

    intervals: list[StageDurationSummary] = []
    for earlier, later in zip(valid_entries, valid_entries[1:]):
        duration = _whole_seconds_between(
            earlier[0],
            later[0],
            source=CAMPAIGNS_SOURCE,
            identifier=campaign_id,
            inverted_reason=CAMPAIGN_STAGE_CLOCK_INVERTED,
            issues=issues,
        )
        if duration is None:
            continue
        intervals.append(
            StageDurationSummary(
                stage=earlier[2],
                started_at=earlier[0],
                ended_at=later[0],
                duration_seconds=duration,
                open=False,
                from_state=later[1],
                to_state=later[2],
            )
        )

    last_at, _, last_to_state = valid_entries[-1]
    open_stage = last_to_state
    if campaign_state != last_to_state:
        issues.append(
            DataIssue(
                CAMPAIGNS_SOURCE,
                campaign_id,
                CAMPAIGN_STAGE_HISTORY_STATE_INCONSISTENT,
            )
        )
    open_duration = _whole_seconds_between(
        last_at,
        observed_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        source=CAMPAIGNS_SOURCE,
        identifier=campaign_id,
        inverted_reason=CAMPAIGN_STAGE_CLOCK_INVERTED,
        issues=issues,
    )
    intervals.append(
        StageDurationSummary(
            stage=open_stage,
            started_at=last_at,
            ended_at=None,
            duration_seconds=open_duration,
            open=True,
        )
    )

    intervals.sort(key=lambda item: (item.started_at, item.stage))
    return intervals


def _campaign_dependency_failures(
    campaign: dict[str, Any],
    *,
    campaign_id: str,
    failed: bool,
    blocked: bool,
    last_error_code: str | None,
    linkedin_failure_codes: list[str],
    issues: list[DataIssue],
) -> list[CampaignDependencyFailureSummary]:
    codes: set[str] = set(linkedin_failure_codes)
    if failed or blocked:
        if last_error_code is not None:
            codes.add(last_error_code)
        raw_errors = campaign.get("errors")
        if isinstance(raw_errors, list):
            for raw_code in raw_errors:
                code = _safe_error_code(raw_code)
                if code is None:
                    issues.append(
                        DataIssue(
                            CAMPAIGNS_SOURCE,
                            campaign_id,
                            CAMPAIGN_ERROR_CODE_INVALID,
                        )
                    )
                else:
                    codes.add(code)
        elif raw_errors is not None:
            issues.append(
                DataIssue(
                    CAMPAIGNS_SOURCE,
                    campaign_id,
                    CAMPAIGN_ERROR_CODE_INVALID,
                )
            )
        history = campaign.get("state_history")
        if isinstance(history, list):
            for entry in history:
                if not isinstance(entry, dict):
                    continue  # Malformed entries already reported by stage derivation.
                raw_code = entry.get("error_code")
                if raw_code is None:
                    continue
                code = _safe_error_code(raw_code)
                if code is None:
                    issues.append(
                        DataIssue(
                            CAMPAIGNS_SOURCE,
                            campaign_id,
                            CAMPAIGN_ERROR_CODE_INVALID,
                        )
                    )
                else:
                    codes.add(code)

    buckets: dict[str, set[str]] = {}
    for code in codes:
        buckets.setdefault(_classify_dependency(code), set()).add(code)
    return [
        CampaignDependencyFailureSummary(
            dependency=dependency,
            error_codes=sorted(buckets[dependency]),
        )
        for dependency in sorted(buckets)
    ]


def _aggregate_dependency_failures(
    executions: list[ExecutionSummary],
    campaigns: list[CampaignSummary],
) -> list[DependencyFailureEntry]:
    attributions: dict[str, set[tuple[str, str]]] = {}
    campaign_ids: dict[str, set[str]] = {}
    run_ids: dict[str, set[str]] = {}

    for execution in executions:
        if execution.outcome != "failed":
            continue
        for code in execution.error_codes:
            dependency = _classify_dependency(code)
            attributions.setdefault(dependency, set()).add(
                (code, execution.run_id)
            )
            run_ids.setdefault(dependency, set()).add(execution.run_id)

    for campaign in campaigns:
        for entry in campaign.dependency_failures:
            for code in entry.error_codes:
                attributions.setdefault(entry.dependency, set()).add(
                    (code, campaign.campaign_id)
                )
                campaign_ids.setdefault(entry.dependency, set()).add(
                    campaign.campaign_id
                )

    return [
        DependencyFailureEntry(
            dependency=dependency,
            failure_count=len(attributions[dependency]),
            error_codes=sorted(
                {code for code, _ in attributions[dependency]}
            ),
            campaign_ids=sorted(campaign_ids.get(dependency, set())),
            run_ids=sorted(run_ids.get(dependency, set())),
        )
        for dependency in sorted(attributions)
    ]


def _resolved_source_directory(
    base_path: Path,
    relative: str,
    *,
    source: str,
    missing_reason: str,
    invalid_reason: str,
    issues: list[DataIssue],
) -> Path | None:
    try:
        base_resolved = base_path.resolve(strict=True)
        candidate = base_path / relative
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError:
        issues.append(DataIssue(source, None, missing_reason))
        return None
    except OSError:
        issues.append(DataIssue(source, None, invalid_reason))
        return None

    try:
        resolved.relative_to(base_resolved)
    except ValueError:
        issues.append(DataIssue(source, None, invalid_reason))
        return None
    if not resolved.is_dir():
        issues.append(DataIssue(source, None, invalid_reason))
        return None
    return resolved


def _direct_json_entries(
    directory: Path,
    *,
    source: str,
    path_reason: str,
    file_reason: str,
    issues: list[DataIssue],
) -> list[Path]:
    try:
        entries = sorted(directory.iterdir(), key=lambda path: path.name)
    except OSError:
        issues.append(DataIssue(source, None, file_reason))
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
            issues.append(DataIssue(source, identifier, path_reason))
            continue
        if not resolved.is_file():
            issues.append(DataIssue(source, identifier, file_reason))
            continue
        accepted.append(entry)
    return accepted


def _read_json_document(
    path: Path,
    *,
    source: str,
    invalid_reason: str,
    issues: list[DataIssue],
) -> dict[str, Any] | None:
    identifier = _safe_artifact_identifier(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        issues.append(DataIssue(source, identifier, invalid_reason))
        return None
    if not isinstance(payload, dict):
        issues.append(DataIssue(source, identifier, invalid_reason))
        return None
    return payload


def _load_executions(
    base_path: Path, issues: list[DataIssue]
) -> list[ExecutionSummary]:
    directory = _resolved_source_directory(
        base_path,
        METADATA_RUNS_RELATIVE,
        source=RUNS_SOURCE,
        missing_reason=RUNS_DIRECTORY_NOT_FOUND,
        invalid_reason=RUNS_DIRECTORY_INVALID,
        issues=issues,
    )
    if directory is None:
        return []

    executions: list[ExecutionSummary] = []
    for path in _direct_json_entries(
        directory,
        source=RUNS_SOURCE,
        path_reason=RUN_FILE_PATH_OUTSIDE_SOURCE,
        file_reason=RUN_FILE_INVALID,
        issues=issues,
    ):
        payload = _read_json_document(
            path,
            source=RUNS_SOURCE,
            invalid_reason=RUN_DOCUMENT_INVALID,
            issues=issues,
        )
        if payload is None:
            continue

        artifact_identifier = _safe_artifact_identifier(path)
        run_id = _safe_identifier(payload.get("run_id"))
        if run_id is None:
            issues.append(
                DataIssue(RUNS_SOURCE, artifact_identifier, RUN_IDENTIFIER_INVALID)
            )
            continue
        if path.stem != run_id:
            issues.append(
                DataIssue(RUNS_SOURCE, artifact_identifier, RUN_IDENTIFIER_MISMATCH)
            )
            continue

        status = payload.get("status")
        if status == "completed":
            outcome = "successful"
        elif status == "failed":
            outcome = "failed"
        else:
            issues.append(DataIssue(RUNS_SOURCE, run_id, RUN_STATUS_INVALID))
            continue

        trigger_raw = payload.get("trigger")
        trigger = (
            trigger_raw
            if isinstance(trigger_raw, str) and _SAFE_TRIGGER.fullmatch(trigger_raw)
            else None
        )
        if trigger_raw is not None and trigger is None:
            issues.append(DataIssue(RUNS_SOURCE, run_id, RUN_TRIGGER_INVALID))

        started_at = _validated_timestamp(
            payload.get("started_at"),
            source=RUNS_SOURCE,
            identifier=run_id,
            reason=RUN_TIMESTAMP_INVALID,
            issues=issues,
        )
        completed_at = _validated_timestamp(
            payload.get("completed_at"),
            source=RUNS_SOURCE,
            identifier=run_id,
            reason=RUN_TIMESTAMP_INVALID,
            issues=issues,
        )

        error_codes: list[str] = []
        raw_errors = payload.get("errors", [])
        if isinstance(raw_errors, list):
            for raw_error in raw_errors:
                code = _safe_error_code(raw_error)
                if code is None:
                    issues.append(
                        DataIssue(RUNS_SOURCE, run_id, RUN_ERROR_CODE_INVALID)
                    )
                elif code not in error_codes:
                    error_codes.append(code)
        elif raw_errors is not None:
            issues.append(DataIssue(RUNS_SOURCE, run_id, RUN_ERROR_CODE_INVALID))

        duration_seconds = _whole_seconds_between(
            started_at,
            completed_at,
            source=RUNS_SOURCE,
            identifier=run_id,
            inverted_reason=RUN_CLOCK_INVERTED,
            issues=issues,
        )

        executions.append(
            ExecutionSummary(
                run_id=run_id,
                trigger=trigger,
                status=status,
                outcome=outcome,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration_seconds,
                error_codes=sorted(error_codes),
            )
        )

    executions.sort(
        key=lambda item: (
            item.completed_at or item.started_at or "",
            item.run_id,
        ),
        reverse=True,
    )
    return executions


def _validate_source_status(
    raw_status: Any, *, campaign_id: str, issues: list[DataIssue]
) -> dict[str, Any] | None:
    if raw_status is not None and not isinstance(raw_status, dict):
        issues.append(
            DataIssue(
                CAMPAIGNS_SOURCE,
                campaign_id,
                CAMPAIGN_SOURCE_STATUS_INVALID,
            )
        )
        return None
    status = raw_status if isinstance(raw_status, dict) else {}
    if (
        ("location" in status and status.get("location") not in SOURCE_LOCATIONS)
        or (
            "execution_state" in status
            and status.get("execution_state") not in EXECUTION_STATES
        )
        or (
            "recovery_classification" in status
            and status.get("recovery_classification")
            not in RECOVERY_CLASSIFICATIONS
        )
    ):
        issues.append(
            DataIssue(
                CAMPAIGNS_SOURCE,
                campaign_id,
                CAMPAIGN_SOURCE_STATUS_INVALID,
            )
        )
        return None
    return normalize_source_file_status(status)


def _attempt_identifier(
    value: Any, *, campaign_id: str, issues: list[DataIssue]
) -> str | None:
    if value is None:
        return None
    safe = _safe_identifier(value)
    if safe is None:
        issues.append(
            DataIssue(
                CAMPAIGNS_SOURCE,
                campaign_id,
                CAMPAIGN_ATTEMPT_EVIDENCE_INVALID,
            )
        )
    return safe


def _attempt_count(
    value: Any, *, campaign_id: str, issues: list[DataIssue]
) -> int | None:
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    issues.append(
        DataIssue(
            CAMPAIGNS_SOURCE,
            campaign_id,
            CAMPAIGN_ATTEMPT_EVIDENCE_INVALID,
        )
    )
    return None


def _linkedin_progress(
    campaign: dict[str, Any],
    *,
    campaign_id: str,
    observed_at: datetime,
    issues: list[DataIssue],
) -> LinkedInProgressSummary:
    counts = {state: 0 for state in PUBLISH_STATES}
    distribution = campaign.get("linkedin_distribution")
    if distribution is None:
        distribution = {}
    elif not isinstance(distribution, dict):
        issues.append(
            DataIssue(
                CAMPAIGNS_SOURCE,
                campaign_id,
                LINKEDIN_DISTRIBUTION_INVALID,
            )
        )
        distribution = {}

    strategy = _safe_identifier(distribution.get("strategy"))
    if distribution.get("strategy") is not None and strategy is None:
        issues.append(
            DataIssue(
                CAMPAIGNS_SOURCE,
                campaign_id,
                LINKEDIN_DISTRIBUTION_INVALID,
            )
        )
    anchor_utc = _validated_timestamp(
        distribution.get("anchor_utc"),
        source=CAMPAIGNS_SOURCE,
        identifier=campaign_id,
        reason=LINKEDIN_TIMESTAMP_INVALID,
        issues=issues,
    )

    variants = campaign.get("variants", [])
    if not isinstance(variants, list):
        issues.append(
            DataIssue(CAMPAIGNS_SOURCE, campaign_id, LINKEDIN_VARIANTS_INVALID)
        )
        variants = []

    pending_times: list[str] = []
    queued_times: list[str] = []
    published_times: list[str] = []
    failure_codes: list[str] = []
    elapsed_pending = 0
    elapsed_queued = 0

    for variant in variants:
        if not isinstance(variant, dict):
            issues.append(
                DataIssue(CAMPAIGNS_SOURCE, campaign_id, LINKEDIN_VARIANT_INVALID)
            )
            continue
        publish_state = variant.get("publish_state")
        if publish_state not in counts:
            issues.append(
                DataIssue(
                    CAMPAIGNS_SOURCE,
                    campaign_id,
                    LINKEDIN_PUBLISH_STATE_INVALID,
                )
            )
            continue
        counts[publish_state] += 1

        if publish_state == "pending":
            scheduled = _validated_timestamp(
                variant.get("scheduled_at_utc"),
                source=CAMPAIGNS_SOURCE,
                identifier=campaign_id,
                reason=LINKEDIN_TIMESTAMP_INVALID,
                issues=issues,
            )
            if scheduled is not None:
                pending_times.append(scheduled)
                parsed = _parse_canonical_utc(scheduled)
                if parsed is not None and parsed <= observed_at:
                    elapsed_pending += 1
        elif publish_state == "queued":
            publish_after = _validated_timestamp(
                variant.get("publish_after_utc"),
                source=CAMPAIGNS_SOURCE,
                identifier=campaign_id,
                reason=LINKEDIN_TIMESTAMP_INVALID,
                issues=issues,
            )
            if publish_after is not None:
                queued_times.append(publish_after)
                parsed = _parse_canonical_utc(publish_after)
                if parsed is not None and parsed <= observed_at:
                    elapsed_queued += 1
        elif publish_state == "published":
            published = _validated_timestamp(
                variant.get("published_at"),
                source=CAMPAIGNS_SOURCE,
                identifier=campaign_id,
                reason=LINKEDIN_TIMESTAMP_INVALID,
                issues=issues,
            )
            if published is not None:
                published_times.append(published)
        elif publish_state == "failed":
            evidence = variant.get("linkedin_publication")
            raw_code = (
                evidence.get("last_error_code")
                if isinstance(evidence, dict)
                else None
            )
            if raw_code is not None:
                code = _safe_error_code(raw_code)
                if code is None:
                    issues.append(
                        DataIssue(
                            CAMPAIGNS_SOURCE,
                            campaign_id,
                            LINKEDIN_ERROR_CODE_INVALID,
                        )
                    )
                elif code not in failure_codes:
                    failure_codes.append(code)

    return LinkedInProgressSummary(
        publish_state_counts=counts,
        strategy=strategy,
        anchor_utc=anchor_utc,
        earliest_pending_scheduled_at_utc=min(pending_times, default=None),
        earliest_queued_publish_after_utc=min(queued_times, default=None),
        latest_published_at=max(published_times, default=None),
        elapsed_pending_scheduled_windows=elapsed_pending,
        elapsed_queued_publish_windows=elapsed_queued,
        failure_codes=sorted(failure_codes),
    )


def _campaign_health(
    *,
    state: str,
    source_status: dict[str, Any],
    observed_at: datetime,
    stale_after_seconds: int,
    campaign_id: str,
    issues: list[DataIssue],
) -> tuple[bool, bool, bool, bool, bool, list[str], str | None]:
    location = source_status["location"]
    execution_state = source_status["execution_state"]
    recovery = source_status["recovery_classification"]
    reasons: list[str] = []

    successful = (
        state == STATE_FLOW_A_COMPLETE
        and location == SOURCE_LOCATION_PROCESSED
        and execution_state == EXECUTION_STATE_IDLE
    )
    if successful:
        reasons.append("campaign_lifecycle_successful")

    failed = False
    if state == STATE_VALIDATION_FAILED:
        failed = True
        reasons.append("campaign_state_validation_failed")
    elif state == STATE_ERROR:
        failed = True
        reasons.append("campaign_state_error")
    if location == SOURCE_LOCATION_ERROR:
        failed = True
        reasons.append("source_location_error")

    blocked = failed
    if recovery in BLOCKING_RECOVERY_CLASSIFICATIONS:
        blocked = True
        reasons.append(f"recovery_{recovery}")

    last_progress_at: str | None = None
    stale = execution_state == EXECUTION_STATE_STALE
    if stale:
        reasons.append("execution_state_stale")
    elif execution_state == EXECUTION_STATE_PROCESSING:
        raw_progress = source_status.get("last_progress_at")
        if raw_progress is None:
            stale = True
            reasons.append("processing_last_progress_at_missing")
        else:
            progress = _parse_canonical_utc(raw_progress)
            if progress is None:
                stale = True
                reasons.append("processing_last_progress_at_invalid")
                issues.append(
                    DataIssue(
                        CAMPAIGNS_SOURCE,
                        campaign_id,
                        CAMPAIGN_TIMESTAMP_INVALID,
                    )
                )
            else:
                last_progress_at = progress.strftime("%Y-%m-%dT%H:%M:%SZ")
                if observed_at >= progress + timedelta(seconds=stale_after_seconds):
                    stale = True
                    reasons.append("processing_inactivity_threshold_reached")
    else:
        last_progress_at = _validated_timestamp(
            source_status.get("last_progress_at"),
            source=CAMPAIGNS_SOURCE,
            identifier=campaign_id,
            reason=CAMPAIGN_TIMESTAMP_INVALID,
            issues=issues,
        )

    in_progress = not successful and not failed
    return (
        successful,
        failed,
        blocked,
        stale,
        in_progress,
        sorted(set(reasons)),
        last_progress_at,
    )


def _last_error_code(
    source_status: dict[str, Any],
    *,
    campaign_id: str,
    issues: list[DataIssue],
) -> str | None:
    last_error = source_status.get("last_error")
    if last_error is None:
        return None
    if not isinstance(last_error, dict):
        issues.append(
            DataIssue(
                CAMPAIGNS_SOURCE,
                campaign_id,
                CAMPAIGN_ERROR_CODE_INVALID,
            )
        )
        return None
    code = _safe_error_code(last_error.get("error_code"))
    if code is None:
        issues.append(
            DataIssue(
                CAMPAIGNS_SOURCE,
                campaign_id,
                CAMPAIGN_ERROR_CODE_INVALID,
            )
        )
    return code


def _load_campaigns(
    base_path: Path,
    *,
    observed_at: datetime,
    stale_after_seconds: int,
    issues: list[DataIssue],
) -> list[CampaignSummary]:
    directory = _resolved_source_directory(
        base_path,
        "metadata/campaigns",
        source=CAMPAIGNS_SOURCE,
        missing_reason=CAMPAIGNS_DIRECTORY_NOT_FOUND,
        invalid_reason=CAMPAIGNS_DIRECTORY_INVALID,
        issues=issues,
    )
    if directory is None:
        return []

    campaigns: list[CampaignSummary] = []
    for path in _direct_json_entries(
        directory,
        source=CAMPAIGNS_SOURCE,
        path_reason=CAMPAIGN_FILE_PATH_OUTSIDE_SOURCE,
        file_reason=CAMPAIGN_FILE_INVALID,
        issues=issues,
    ):
        artifact_identifier = _safe_artifact_identifier(path)
        filename_id = path.stem
        try:
            validate_campaign_id(filename_id)
        except CampaignLifecycleError:
            issues.append(
                DataIssue(
                    CAMPAIGNS_SOURCE,
                    artifact_identifier,
                    CAMPAIGN_ID_INVALID,
                )
            )
            continue

        campaign = read_campaign_metadata(base_path, filename_id)
        if not isinstance(campaign, dict):
            issues.append(
                DataIssue(
                    CAMPAIGNS_SOURCE,
                    artifact_identifier,
                    CAMPAIGN_FILE_INVALID,
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
                DataIssue(
                    CAMPAIGNS_SOURCE,
                    artifact_identifier,
                    CAMPAIGN_ID_INVALID,
                )
            )
            continue
        if persisted_id != filename_id:
            issues.append(
                DataIssue(
                    CAMPAIGNS_SOURCE,
                    artifact_identifier,
                    CAMPAIGN_ID_FILENAME_MISMATCH,
                )
            )
            continue
        if campaign.get("flow") != FLOW_A:
            continue

        state = campaign.get("state")
        if state not in LIFECYCLE_STATES:
            issues.append(
                DataIssue(CAMPAIGNS_SOURCE, persisted_id, CAMPAIGN_STATE_INVALID)
            )
            continue
        source_status = _validate_source_status(
            campaign.get("source_file_status"),
            campaign_id=persisted_id,
            issues=issues,
        )
        if source_status is None:
            continue

        updated_at = _validated_timestamp(
            campaign.get("updated_at"),
            source=CAMPAIGNS_SOURCE,
            identifier=persisted_id,
            reason=CAMPAIGN_TIMESTAMP_INVALID,
            issues=issues,
        )
        (
            successful,
            failed,
            blocked,
            stale,
            in_progress,
            health_reasons,
            last_progress_at,
        ) = _campaign_health(
            state=state,
            source_status=source_status,
            observed_at=observed_at,
            stale_after_seconds=stale_after_seconds,
            campaign_id=persisted_id,
            issues=issues,
        )

        processing_started_at = _validated_timestamp(
            source_status.get("processing_started_at"),
            source=CAMPAIGNS_SOURCE,
            identifier=persisted_id,
            reason=CAMPAIGN_TIMESTAMP_INVALID,
            issues=issues,
        )
        processing_lease_expires_at = _validated_timestamp(
            source_status.get("processing_lease_expires_at"),
            source=CAMPAIGNS_SOURCE,
            identifier=persisted_id,
            reason=CAMPAIGN_TIMESTAMP_INVALID,
            issues=issues,
        )
        last_transition_at = _validated_timestamp(
            source_status.get("last_transition_at"),
            source=CAMPAIGNS_SOURCE,
            identifier=persisted_id,
            reason=CAMPAIGN_TIMESTAMP_INVALID,
            issues=issues,
        )

        last_error_code = _last_error_code(
            source_status,
            campaign_id=persisted_id,
            issues=issues,
        )
        linkedin = _linkedin_progress(
            campaign,
            campaign_id=persisted_id,
            observed_at=observed_at,
            issues=issues,
        )
        stage_durations = _stage_durations(
            campaign,
            campaign_id=persisted_id,
            campaign_state=state,
            observed_at=observed_at,
            issues=issues,
        )
        attempt_duration_seconds = _whole_seconds_between(
            source_status.get("processing_started_at"),
            source_status.get("last_progress_at"),
            source=CAMPAIGNS_SOURCE,
            identifier=persisted_id,
            inverted_reason=CAMPAIGN_ATTEMPT_CLOCK_INVERTED,
            issues=issues,
        )
        dependency_failures = _campaign_dependency_failures(
            campaign,
            campaign_id=persisted_id,
            failed=failed,
            blocked=blocked,
            last_error_code=last_error_code,
            linkedin_failure_codes=linkedin.failure_codes,
            issues=issues,
        )

        campaigns.append(
            CampaignSummary(
                campaign_id=persisted_id,
                state=state,
                updated_at=updated_at,
                location=source_status["location"],
                execution_state=source_status["execution_state"],
                recovery_classification=source_status[
                    "recovery_classification"
                ],
                successful=successful,
                failed=failed,
                blocked=blocked,
                stale=stale,
                in_progress=in_progress,
                health_reasons=health_reasons,
                execution_attempt_id=_attempt_identifier(
                    source_status.get("execution_attempt_id"),
                    campaign_id=persisted_id,
                    issues=issues,
                ),
                attempt_count=_attempt_count(
                    source_status.get("attempt_count"),
                    campaign_id=persisted_id,
                    issues=issues,
                ),
                processing_started_at=processing_started_at,
                last_progress_at=last_progress_at,
                processing_lease_expires_at=processing_lease_expires_at,
                last_transition_at=last_transition_at,
                last_error_code=last_error_code,
                linkedin=linkedin,
                attempt_duration_seconds=attempt_duration_seconds,
                stage_durations=stage_durations,
                dependency_failures=dependency_failures,
            )
        )

    campaigns.sort(
        key=lambda item: (item.updated_at or "", item.campaign_id),
        reverse=True,
    )
    return campaigns


def _calendar_store_ready(base_path: Path, issues: list[DataIssue]) -> bool:
    """Return True when the calendar database store loads successfully."""
    calendar, errors = load_calendar(base_path)
    if calendar is None:
        reason = errors[0] if errors else CALENDAR_SCHEMA_INVALID
        issues.append(DataIssue(CALENDAR_SOURCE, "calendar_store", reason))
        return False
    items = calendar.get("items", [])
    if not isinstance(items, list):
        issues.append(
            DataIssue(CALENDAR_SOURCE, "calendar_store", CALENDAR_SCHEMA_INVALID)
        )
        return False
    return True


def _load_delayed_calendar_items(
    base_path: Path,
    *,
    observed_at: datetime,
    issues: list[DataIssue],
) -> list[DelayedCalendarItemSummary]:
    if not _calendar_store_ready(base_path, issues):
        return []
    calendar, errors = load_calendar(base_path)
    if calendar is None:
        for reason in errors or [CALENDAR_SCHEMA_INVALID]:
            issues.append(DataIssue(CALENDAR_SOURCE, "calendar.json", reason))
        return []

    delayed: list[DelayedCalendarItemSummary] = []
    for item in calendar.get("items", []):
        status = item["status"]
        if status in TERMINAL_CALENDAR_STATUSES:
            continue
        if status not in ALLOWED_STATUSES or status not in DELAY_ELIGIBLE_STATUSES:
            continue
        due_at = _parse_canonical_utc(item.get("due_at_utc"))
        if due_at is None:
            issues.append(
                DataIssue(
                    CALENDAR_SOURCE,
                    _safe_identifier(item.get("item_id")),
                    CALENDAR_SCHEMA_INVALID,
                )
            )
            continue
        if due_at >= observed_at:
            continue

        campaign_id = item.get("campaign_id")
        safe_campaign_id: str | None = None
        if campaign_id is not None:
            try:
                if not isinstance(campaign_id, str):
                    raise CampaignLifecycleError("", error_code=CAMPAIGN_ID_INVALID)
                validate_campaign_id(campaign_id)
                safe_campaign_id = campaign_id
            except CampaignLifecycleError:
                issues.append(
                    DataIssue(
                        CALENDAR_SOURCE,
                        _safe_identifier(item.get("item_id")),
                        CAMPAIGN_ID_INVALID,
                    )
                )

        delayed.append(
            DelayedCalendarItemSummary(
                item_id=str(item["item_id"]),
                title=str(item["title"]),
                status=status,
                due_at_utc=due_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                flow_type=str(item["flow_type"]),
                campaign_id=safe_campaign_id,
            )
        )

    delayed.sort(key=lambda item: (item.due_at_utc, item.item_id))
    return delayed


def _build_summary(
    executions: list[ExecutionSummary],
    campaigns: list[CampaignSummary],
    delayed: list[DelayedCalendarItemSummary],
    dependency_failures: list[DependencyFailureEntry],
    issues: list[DataIssue],
) -> dict[str, Any]:
    linkedin_counts = {state: 0 for state in PUBLISH_STATES}
    for campaign in campaigns:
        for state, count in campaign.linkedin.publish_state_counts.items():
            linkedin_counts[state] += count
    dependency_counts = {bucket: 0 for bucket in DEPENDENCY_BUCKETS}
    for entry in dependency_failures:
        dependency_counts[entry.dependency] = entry.failure_count
    return {
        "successful_executions": sum(
            item.outcome == "successful" for item in executions
        ),
        "failed_executions": sum(item.outcome == "failed" for item in executions),
        "campaigns_total": len(campaigns),
        "successful_campaigns": sum(item.successful for item in campaigns),
        "failed_campaigns": sum(item.failed for item in campaigns),
        "blocked_campaigns": sum(item.blocked for item in campaigns),
        "stale_campaigns": sum(item.stale for item in campaigns),
        "in_progress_campaigns": sum(item.in_progress for item in campaigns),
        "delayed_calendar_items": len(delayed),
        "linkedin_variants_by_publish_state": linkedin_counts,
        "stage_durations": {
            "campaigns_with_stage_durations": sum(
                bool(item.stage_durations) for item in campaigns
            ),
            "executions_with_duration": sum(
                item.duration_seconds is not None for item in executions
            ),
            "stage_intervals_reported": sum(
                len(item.stage_durations) for item in campaigns
            ),
        },
        "dependency_failures": dependency_counts,
        "data_issues": len(issues),
    }


def get_flow_a_operational_status(
    base_path: Path, *, now_utc: str | None = None
) -> FlowAOperationalStatusResult:
    """Aggregate fixed on-disk sources without mutation or external calls."""
    observed_at_utc = (
        utc_now_iso()
        if now_utc is None
        else validate_canonical_utc_timestamp(now_utc)
    )
    observed_at = _parse_canonical_utc(observed_at_utc)
    if observed_at is None:  # Defensive; validation above guarantees this.
        raise ValueError("invalid canonical observation time")

    stale_after_seconds = load_flow_a_processing_stale_seconds()
    issues: list[DataIssue] = []
    executions = _load_executions(base_path, issues)
    campaigns = _load_campaigns(
        base_path,
        observed_at=observed_at,
        stale_after_seconds=stale_after_seconds,
        issues=issues,
    )
    delayed = _load_delayed_calendar_items(
        base_path,
        observed_at=observed_at,
        issues=issues,
    )
    dependency_failures = _aggregate_dependency_failures(executions, campaigns)
    issues = sorted(
        set(issues),
        key=lambda item: (item.source, item.identifier or "", item.reason),
    )

    partitioned = {
        "successful": [
            item for item in executions if item.outcome == "successful"
        ],
        "failed": [item for item in executions if item.outcome == "failed"],
    }
    return FlowAOperationalStatusResult(
        status="partial" if issues else "ok",
        observed_at_utc=observed_at_utc,
        stale_after_seconds=stale_after_seconds,
        summary=_build_summary(
            executions, campaigns, delayed, dependency_failures, issues
        ),
        executions=partitioned,
        campaigns=campaigns,
        delayed_calendar_items=delayed,
        dependency_failures=dependency_failures,
        data_issues=issues,
        read_only=True,
    )
