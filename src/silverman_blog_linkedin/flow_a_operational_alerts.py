"""Evaluate US-028/US-029/US-030 Flow A operational alerts."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import httpx

from silverman_blog_linkedin.campaign_lifecycle import (
    SOURCE_LOCATION_ERROR,
    CampaignLifecycleError,
    validate_campaign_id,
)
from silverman_blog_linkedin.editorial_calendar_plan import (
    validate_canonical_utc_timestamp,
)
from silverman_blog_linkedin.flow_a_operational_alerts_config import (
    FlowAOperationalAlertsSettings,
    load_flow_a_operational_alerts_settings,
)
from silverman_blog_linkedin.flow_a_operational_status import (
    CALENDAR_ITEM_PAST_DUE,
    DEPENDENCY_COMFYUI,
    DEPENDENCY_GITHUB_PAGES_CHECKOUT,
    DEPENDENCY_LINKEDIN,
    CampaignSummary,
    DataIssue,
    DelayedCalendarItemSummary,
    ExecutionSummary,
    FlowAOperationalStatusResult,
    get_flow_a_operational_status,
)
from silverman_blog_linkedin.linkedin_token_store import _atomic_write_json
from silverman_blog_linkedin.paths import validate_folders
from silverman_blog_linkedin.run_metadata import utc_now_iso

logger = logging.getLogger(__name__)

ALERT_ITEM_MOVED_TO_ERROR = "item_moved_to_error"
ALERT_IMAGE_GENERATION_FAILURE = "image_generation_failure"
ALERT_BLOG_PUBLICATION_FAILURE = "blog_publication_failure"
ALERT_PARTIAL_CALENDAR_EXECUTION = "partial_calendar_execution"
ALERT_LINKEDIN_TOKEN_OR_PUBLICATION_FAILURE = (
    "linkedin_token_or_publication_failure"
)
ALERT_STALE_CAMPAIGN = "stale_campaign"
ALERT_UNHEALTHY_WORKER = "unhealthy_worker"
ALERT_FAILED_N8N_WORKFLOW = "failed_n8n_workflow"
US028_ALERT_TYPES = (
    ALERT_ITEM_MOVED_TO_ERROR,
    ALERT_IMAGE_GENERATION_FAILURE,
    ALERT_BLOG_PUBLICATION_FAILURE,
)
US029_ALERT_TYPES = (
    ALERT_PARTIAL_CALENDAR_EXECUTION,
    ALERT_LINKEDIN_TOKEN_OR_PUBLICATION_FAILURE,
    ALERT_STALE_CAMPAIGN,
)
US030_ALERT_TYPES = (
    ALERT_UNHEALTHY_WORKER,
    ALERT_FAILED_N8N_WORKFLOW,
)
ALL_ALERT_TYPES = US028_ALERT_TYPES + US029_ALERT_TYPES + US030_ALERT_TYPES

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"

EMISSION_STATUS_NOT_REQUESTED = "not_requested"
EMISSION_STATUS_DISABLED = "disabled"
EMISSION_STATUS_MISCONFIGURED = "misconfigured"
EMISSION_STATUS_EMITTED = "emitted"
EMISSION_STATUS_ALREADY_EMITTED = "already_emitted"
EMISSION_STATUS_PARTIAL = "partial"
EMISSION_STATUS_FAILED = "failed"

LEDGER_RELATIVE_DIR = "metadata/operational-alerts"
LEDGER_FILENAME = "emissions.json"
LEDGER_VERSION = 1
ORCHESTRATION_FAILURES_FILENAME = "orchestration-failures.json"
ORCHESTRATION_FAILURES_VERSION = 1

ORCHESTRATION_REASON_N8N_WORKFLOW_FAILED = "n8n_workflow_failed"
ORCHESTRATION_REASON_N8N_HTTP_NODE_FAILED = "n8n_http_node_failed"
ORCHESTRATION_REASON_N8N_ERROR_TRIGGER = "n8n_error_trigger"
ORCHESTRATION_REASON_CODES = frozenset(
    {
        ORCHESTRATION_REASON_N8N_WORKFLOW_FAILED,
        ORCHESTRATION_REASON_N8N_HTTP_NODE_FAILED,
        ORCHESTRATION_REASON_N8N_ERROR_TRIGGER,
    }
)

_SAFE_OPAQUE_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")
_FOLDER_NOT_READY_PREFIX = "editorial_folder_not_ready:"

_BLOG_PUBLICATION_PREFIXES = ("blog_publish_", "blog_git_publication_")
_LINKEDIN_PREVIEW_CHECKOUT_PREFIXES = ("linkedin_preview_validation_checkout_",)
_LINKEDIN_PREVIEW_CHECKOUT_EXACT = frozenset(
    {"linkedin_article_preview_public_repo_not_configured"}
)
_STALE_HEALTH_REASONS = frozenset(
    {
        "execution_state_stale",
        "processing_last_progress_at_missing",
        "processing_last_progress_at_invalid",
        "processing_inactivity_threshold_reached",
    }
)
_WEBHOOK_TIMEOUT_SECONDS = 15.0


@dataclass(frozen=True)
class OperationalAlert:
    alert_type: str
    severity: str
    fingerprint: str
    observed_at_utc: str
    summary: str
    campaign_id: str | None = None
    run_id: str | None = None
    calendar_item_id: str | None = None
    workflow_id: str | None = None
    execution_id: str | None = None
    dependency: str | None = None
    error_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if not payload["error_codes"]:
            del payload["error_codes"]
        if payload["dependency"] is None:
            del payload["dependency"]
        if payload["campaign_id"] is None:
            del payload["campaign_id"]
        if payload["run_id"] is None:
            del payload["run_id"]
        if payload["calendar_item_id"] is None:
            del payload["calendar_item_id"]
        if payload["workflow_id"] is None:
            del payload["workflow_id"]
        if payload["execution_id"] is None:
            del payload["execution_id"]
        return payload

    def webhook_payload(self) -> dict[str, Any]:
        """Secret-safe payload posted to the generic webhook."""
        return self.to_dict()


@dataclass(frozen=True)
class OrchestrationFailureReportResult:
    status: str
    fingerprint: str
    workflow_id: str
    reason_code: str
    observed_at_utc: str
    created: bool
    execution_id: str | None = None
    node_name: str | None = None
    campaign_id: str | None = None
    run_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "status": self.status,
            "fingerprint": self.fingerprint,
            "workflow_id": self.workflow_id,
            "reason_code": self.reason_code,
            "observed_at_utc": self.observed_at_utc,
            "created": self.created,
        }
        if self.execution_id is not None:
            payload["execution_id"] = self.execution_id
        if self.node_name is not None:
            payload["node_name"] = self.node_name
        if self.campaign_id is not None:
            payload["campaign_id"] = self.campaign_id
        if self.run_id is not None:
            payload["run_id"] = self.run_id
        return payload


@dataclass(frozen=True)
class EmissionResult:
    requested: bool
    status: str
    emitted_fingerprints: list[str] = field(default_factory=list)
    already_emitted_fingerprints: list[str] = field(default_factory=list)
    failed_fingerprints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested": self.requested,
            "status": self.status,
            "emitted_fingerprints": list(self.emitted_fingerprints),
            "already_emitted_fingerprints": list(
                self.already_emitted_fingerprints
            ),
            "failed_fingerprints": list(self.failed_fingerprints),
        }


@dataclass(frozen=True)
class FlowAOperationalAlertsResult:
    status: str
    observed_at_utc: str
    alerts: list[OperationalAlert]
    summary: dict[str, Any]
    data_issues: list[DataIssue]
    emission: EmissionResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "observed_at_utc": self.observed_at_utc,
            "alerts": [alert.to_dict() for alert in self.alerts],
            "summary": self.summary,
            "data_issues": [issue.to_dict() for issue in self.data_issues],
            "emission": self.emission.to_dict(),
        }


def _primary_error_code(codes: list[str]) -> str:
    if not codes:
        return "none"
    return sorted(codes)[0]


def _build_fingerprint(
    alert_type: str,
    *,
    campaign_id: str | None,
    run_id: str | None,
    calendar_item_id: str | None,
    primary_error_code: str,
) -> str:
    artifact = campaign_id or run_id or calendar_item_id or "unknown"
    return f"{alert_type}:{artifact}:{primary_error_code}"


def _build_summary_text(
    alert_type: str,
    *,
    campaign_id: str | None,
    run_id: str | None,
    calendar_item_id: str | None,
    error_codes: list[str],
    dependency: str | None,
    workflow_id: str | None = None,
    execution_id: str | None = None,
) -> str:
    parts = [alert_type]
    if campaign_id:
        parts.append(f"campaign_id={campaign_id}")
    if run_id:
        parts.append(f"run_id={run_id}")
    if calendar_item_id:
        parts.append(f"calendar_item_id={calendar_item_id}")
    if workflow_id:
        parts.append(f"workflow_id={workflow_id}")
    if execution_id:
        parts.append(f"execution_id={execution_id}")
    if dependency:
        parts.append(f"dependency={dependency}")
    if error_codes:
        parts.append(f"codes={','.join(sorted(error_codes))}")
    return "; ".join(parts)


def _validate_opaque_token(value: str, *, field_name: str) -> str:
    stripped = value.strip()
    if not stripped or not _SAFE_OPAQUE_TOKEN.fullmatch(stripped):
        raise ValueError(f"{field_name} must be a non-empty safe opaque token")
    return stripped


def _validate_optional_opaque_token(
    value: str | None, *, field_name: str
) -> str | None:
    if value is None:
        return None
    return _validate_opaque_token(value, field_name=field_name)


def _validate_optional_campaign_id(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    try:
        validate_campaign_id(stripped)
    except CampaignLifecycleError as exc:
        raise ValueError(f"invalid campaign_id: {exc}") from exc
    return stripped


def _validate_orchestration_reason_code(value: str) -> str:
    stripped = value.strip()
    if stripped not in ORCHESTRATION_REASON_CODES:
        raise ValueError(
            "reason_code must be one of: "
            + ", ".join(sorted(ORCHESTRATION_REASON_CODES))
        )
    return stripped


def _orchestration_failure_fingerprint(
    *,
    workflow_id: str,
    reason_code: str,
    execution_id: str | None,
) -> str:
    execution_part = execution_id if execution_id else "none"
    return (
        f"{ALERT_FAILED_N8N_WORKFLOW}:{workflow_id}:{reason_code}:{execution_part}"
    )


def _orchestration_failures_path(base_path: Path) -> Path:
    return base_path / LEDGER_RELATIVE_DIR / ORCHESTRATION_FAILURES_FILENAME


def _empty_orchestration_failures() -> dict[str, Any]:
    return {"version": ORCHESTRATION_FAILURES_VERSION, "entries": {}}


def _load_orchestration_failures(base_path: Path) -> dict[str, Any]:
    path = _orchestration_failures_path(base_path)
    if not path.is_file():
        return _empty_orchestration_failures()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning(
            "operational-alerts orchestration-failures unreadable; treating as empty"
        )
        return _empty_orchestration_failures()
    if not isinstance(raw, dict):
        return _empty_orchestration_failures()
    entries = raw.get("entries")
    if not isinstance(entries, dict):
        entries = {}
    return {"version": ORCHESTRATION_FAILURES_VERSION, "entries": entries}


def _write_orchestration_failures(base_path: Path, store: dict[str, Any]) -> None:
    path = _orchestration_failures_path(base_path)
    _atomic_write_json(path, store)


def report_orchestration_failure(
    base_path: Path,
    *,
    workflow_id: str,
    reason_code: str,
    observed_at_utc: str | None = None,
    execution_id: str | None = None,
    node_name: str | None = None,
    campaign_id: str | None = None,
    run_id: str | None = None,
) -> OrchestrationFailureReportResult:
    """Persist a secret-safe n8n orchestration-failure report (idempotent)."""
    resolved_workflow_id = _validate_opaque_token(
        workflow_id, field_name="workflow_id"
    )
    resolved_reason = _validate_orchestration_reason_code(reason_code)
    resolved_execution_id = _validate_optional_opaque_token(
        execution_id, field_name="execution_id"
    )
    resolved_node_name = _validate_optional_opaque_token(
        node_name, field_name="node_name"
    )
    resolved_campaign_id = _validate_optional_campaign_id(campaign_id)
    resolved_run_id = _validate_optional_opaque_token(run_id, field_name="run_id")
    resolved_observed = (
        utc_now_iso()
        if observed_at_utc is None
        else validate_canonical_utc_timestamp(observed_at_utc)
    )
    fingerprint = _orchestration_failure_fingerprint(
        workflow_id=resolved_workflow_id,
        reason_code=resolved_reason,
        execution_id=resolved_execution_id,
    )
    store = _load_orchestration_failures(base_path)
    entries: dict[str, Any] = dict(store.get("entries") or {})
    existing = entries.get(fingerprint)
    if isinstance(existing, dict):
        return OrchestrationFailureReportResult(
            status="ok",
            fingerprint=fingerprint,
            workflow_id=resolved_workflow_id,
            reason_code=resolved_reason,
            observed_at_utc=str(existing.get("observed_at_utc") or resolved_observed),
            created=False,
            execution_id=resolved_execution_id,
            node_name=(
                str(existing["node_name"])
                if isinstance(existing.get("node_name"), str)
                else resolved_node_name
            ),
            campaign_id=(
                str(existing["campaign_id"])
                if isinstance(existing.get("campaign_id"), str)
                else resolved_campaign_id
            ),
            run_id=(
                str(existing["run_id"])
                if isinstance(existing.get("run_id"), str)
                else resolved_run_id
            ),
        )

    entry: dict[str, Any] = {
        "workflow_id": resolved_workflow_id,
        "reason_code": resolved_reason,
        "observed_at_utc": resolved_observed,
        "status": "open",
    }
    if resolved_execution_id is not None:
        entry["execution_id"] = resolved_execution_id
    if resolved_node_name is not None:
        entry["node_name"] = resolved_node_name
    if resolved_campaign_id is not None:
        entry["campaign_id"] = resolved_campaign_id
    if resolved_run_id is not None:
        entry["run_id"] = resolved_run_id
    entries[fingerprint] = entry
    _write_orchestration_failures(
        base_path,
        {"version": ORCHESTRATION_FAILURES_VERSION, "entries": entries},
    )
    return OrchestrationFailureReportResult(
        status="ok",
        fingerprint=fingerprint,
        workflow_id=resolved_workflow_id,
        reason_code=resolved_reason,
        observed_at_utc=resolved_observed,
        created=True,
        execution_id=resolved_execution_id,
        node_name=resolved_node_name,
        campaign_id=resolved_campaign_id,
        run_id=resolved_run_id,
    )


def _not_ready_folder_names(base_path: Path) -> list[str]:
    validation = validate_folders(base_path)
    return sorted(
        name
        for name, status in validation.folders.items()
        if not (status.exists and status.is_directory)
    )


def derive_unhealthy_worker_alert(
    base_path: Path, *, observed_at_utc: str
) -> OperationalAlert | None:
    """Derive unhealthy_worker from in-process folder readiness (health-equivalent)."""
    not_ready = _not_ready_folder_names(base_path)
    if not not_ready:
        return None
    error_codes = [f"{_FOLDER_NOT_READY_PREFIX}{name}" for name in not_ready]
    fingerprint = (
        f"{ALERT_UNHEALTHY_WORKER}:folders_not_ready:{','.join(not_ready)}"
    )
    return OperationalAlert(
        alert_type=ALERT_UNHEALTHY_WORKER,
        severity=SEVERITY_ERROR,
        fingerprint=fingerprint,
        observed_at_utc=observed_at_utc,
        summary=_build_summary_text(
            ALERT_UNHEALTHY_WORKER,
            campaign_id=None,
            run_id=None,
            calendar_item_id=None,
            error_codes=error_codes,
            dependency=None,
        ),
        error_codes=error_codes,
    )


def derive_failed_n8n_workflow_alerts(
    base_path: Path, *, observed_at_utc: str
) -> list[OperationalAlert]:
    """Derive failed_n8n_workflow alerts from the orchestration-failures store only."""
    store = _load_orchestration_failures(base_path)
    alerts: list[OperationalAlert] = []
    entries = store.get("entries") or {}
    if not isinstance(entries, dict):
        return []
    for fingerprint, raw_entry in entries.items():
        if not isinstance(fingerprint, str) or not isinstance(raw_entry, dict):
            continue
        if raw_entry.get("status", "open") != "open":
            continue
        workflow_id = raw_entry.get("workflow_id")
        reason_code = raw_entry.get("reason_code")
        if not isinstance(workflow_id, str) or not isinstance(reason_code, str):
            continue
        if reason_code not in ORCHESTRATION_REASON_CODES:
            continue
        execution_raw = raw_entry.get("execution_id")
        execution_id = execution_raw if isinstance(execution_raw, str) else None
        campaign_raw = raw_entry.get("campaign_id")
        campaign_id = campaign_raw if isinstance(campaign_raw, str) else None
        run_raw = raw_entry.get("run_id")
        run_id = run_raw if isinstance(run_raw, str) else None
        expected = _orchestration_failure_fingerprint(
            workflow_id=workflow_id,
            reason_code=reason_code,
            execution_id=execution_id,
        )
        if fingerprint != expected:
            continue
        alerts.append(
            OperationalAlert(
                alert_type=ALERT_FAILED_N8N_WORKFLOW,
                severity=SEVERITY_ERROR,
                fingerprint=fingerprint,
                observed_at_utc=observed_at_utc,
                summary=_build_summary_text(
                    ALERT_FAILED_N8N_WORKFLOW,
                    campaign_id=campaign_id,
                    run_id=run_id,
                    calendar_item_id=None,
                    error_codes=[reason_code],
                    dependency=None,
                    workflow_id=workflow_id,
                    execution_id=execution_id,
                ),
                campaign_id=campaign_id,
                run_id=run_id,
                workflow_id=workflow_id,
                execution_id=execution_id,
                error_codes=[reason_code],
            )
        )
    return alerts


def _is_blog_publication_code(code: str) -> bool:
    return code.startswith(_BLOG_PUBLICATION_PREFIXES)


def _filter_blog_publication_codes(codes: list[str]) -> list[str]:
    return sorted({code for code in codes if _is_blog_publication_code(code)})


def _is_linkedin_preview_checkout_code(code: str) -> bool:
    return (
        code in _LINKEDIN_PREVIEW_CHECKOUT_EXACT
        or code.startswith(_LINKEDIN_PREVIEW_CHECKOUT_PREFIXES)
    )


def _is_linkedin_alert_code(code: str) -> bool:
    """True for linkedin_* codes that are not github_pages_checkout preview codes."""
    if _is_linkedin_preview_checkout_code(code):
        return False
    return code.startswith("linkedin_")


def _filter_linkedin_alert_codes(codes: list[str]) -> list[str]:
    return sorted({code for code in codes if _is_linkedin_alert_code(code)})


def _alert_from_parts(
    alert_type: str,
    *,
    observed_at_utc: str,
    campaign_id: str | None = None,
    run_id: str | None = None,
    calendar_item_id: str | None = None,
    dependency: str | None = None,
    error_codes: list[str] | None = None,
    severity: str = SEVERITY_ERROR,
) -> OperationalAlert:
    codes = sorted(set(error_codes or []))
    primary = _primary_error_code(codes)
    fingerprint = _build_fingerprint(
        alert_type,
        campaign_id=campaign_id,
        run_id=run_id,
        calendar_item_id=calendar_item_id,
        primary_error_code=primary,
    )
    return OperationalAlert(
        alert_type=alert_type,
        severity=severity,
        fingerprint=fingerprint,
        observed_at_utc=observed_at_utc,
        summary=_build_summary_text(
            alert_type,
            campaign_id=campaign_id,
            run_id=run_id,
            calendar_item_id=calendar_item_id,
            error_codes=codes,
            dependency=dependency,
        ),
        campaign_id=campaign_id,
        run_id=run_id,
        calendar_item_id=calendar_item_id,
        dependency=dependency,
        error_codes=codes,
    )


def _item_moved_to_error_alert(
    campaign: CampaignSummary, *, observed_at_utc: str
) -> OperationalAlert | None:
    if not campaign.failed:
        return None
    error_location = campaign.location == SOURCE_LOCATION_ERROR
    error_reason = "source_location_error" in campaign.health_reasons
    if not (error_location or error_reason):
        return None
    codes = [campaign.last_error_code] if campaign.last_error_code else []
    return _alert_from_parts(
        ALERT_ITEM_MOVED_TO_ERROR,
        observed_at_utc=observed_at_utc,
        campaign_id=campaign.campaign_id,
        error_codes=codes,
    )


def _campaign_codes_for_dependency(
    campaign: CampaignSummary, dependency: str
) -> list[str]:
    for entry in campaign.dependency_failures:
        if entry.dependency == dependency:
            return list(entry.error_codes)
    return []


def _derive_campaign_dependency_alerts(
    campaign: CampaignSummary, *, observed_at_utc: str
) -> list[OperationalAlert]:
    alerts: list[OperationalAlert] = []
    comfyui_codes = _campaign_codes_for_dependency(campaign, DEPENDENCY_COMFYUI)
    if comfyui_codes:
        alerts.append(
            _alert_from_parts(
                ALERT_IMAGE_GENERATION_FAILURE,
                observed_at_utc=observed_at_utc,
                campaign_id=campaign.campaign_id,
                dependency=DEPENDENCY_COMFYUI,
                error_codes=comfyui_codes,
            )
        )
    checkout_codes = _campaign_codes_for_dependency(
        campaign, DEPENDENCY_GITHUB_PAGES_CHECKOUT
    )
    blog_codes = _filter_blog_publication_codes(checkout_codes)
    if blog_codes:
        alerts.append(
            _alert_from_parts(
                ALERT_BLOG_PUBLICATION_FAILURE,
                observed_at_utc=observed_at_utc,
                campaign_id=campaign.campaign_id,
                dependency=DEPENDENCY_GITHUB_PAGES_CHECKOUT,
                error_codes=blog_codes,
            )
        )
    return alerts


def _derive_run_dependency_alerts(
    execution: ExecutionSummary, *, observed_at_utc: str
) -> list[OperationalAlert]:
    if execution.outcome != "failed":
        return []
    alerts: list[OperationalAlert] = []
    comfyui_codes = sorted(
        {
            code
            for code in execution.error_codes
            if code.startswith(("comfyui_", "blog_image_generation_"))
        }
    )
    if comfyui_codes:
        alerts.append(
            _alert_from_parts(
                ALERT_IMAGE_GENERATION_FAILURE,
                observed_at_utc=observed_at_utc,
                run_id=execution.run_id,
                dependency=DEPENDENCY_COMFYUI,
                error_codes=comfyui_codes,
            )
        )
    blog_codes = _filter_blog_publication_codes(execution.error_codes)
    if blog_codes:
        alerts.append(
            _alert_from_parts(
                ALERT_BLOG_PUBLICATION_FAILURE,
                observed_at_utc=observed_at_utc,
                run_id=execution.run_id,
                dependency=DEPENDENCY_GITHUB_PAGES_CHECKOUT,
                error_codes=blog_codes,
            )
        )
    linkedin_codes = _filter_linkedin_alert_codes(execution.error_codes)
    if linkedin_codes:
        alerts.append(
            _alert_from_parts(
                ALERT_LINKEDIN_TOKEN_OR_PUBLICATION_FAILURE,
                observed_at_utc=observed_at_utc,
                run_id=execution.run_id,
                dependency=DEPENDENCY_LINKEDIN,
                error_codes=linkedin_codes,
            )
        )
    return alerts


def _partial_calendar_alert(
    item: DelayedCalendarItemSummary, *, observed_at_utc: str
) -> OperationalAlert:
    return _alert_from_parts(
        ALERT_PARTIAL_CALENDAR_EXECUTION,
        observed_at_utc=observed_at_utc,
        campaign_id=item.campaign_id,
        calendar_item_id=item.item_id,
        error_codes=[CALENDAR_ITEM_PAST_DUE],
        severity=SEVERITY_WARNING,
    )


def _linkedin_alert_for_campaign(
    campaign: CampaignSummary, *, observed_at_utc: str
) -> OperationalAlert | None:
    codes = set(
        _campaign_codes_for_dependency(campaign, DEPENDENCY_LINKEDIN)
    )
    codes.update(
        _filter_linkedin_alert_codes(list(campaign.linkedin.failure_codes))
    )
    if not codes:
        return None
    return _alert_from_parts(
        ALERT_LINKEDIN_TOKEN_OR_PUBLICATION_FAILURE,
        observed_at_utc=observed_at_utc,
        campaign_id=campaign.campaign_id,
        dependency=DEPENDENCY_LINKEDIN,
        error_codes=sorted(codes),
    )


def _stale_campaign_alert(
    campaign: CampaignSummary, *, observed_at_utc: str
) -> OperationalAlert | None:
    if not campaign.stale:
        return None
    stale_codes = sorted(
        reason
        for reason in campaign.health_reasons
        if reason in _STALE_HEALTH_REASONS
    )
    if not stale_codes:
        stale_codes = ["stale"]
    return _alert_from_parts(
        ALERT_STALE_CAMPAIGN,
        observed_at_utc=observed_at_utc,
        campaign_id=campaign.campaign_id,
        error_codes=stale_codes,
        severity=SEVERITY_WARNING,
    )


def derive_operational_alerts(
    status: FlowAOperationalStatusResult,
) -> list[OperationalAlert]:
    """Derive US-028/US-029 alert candidates from operational-status evidence only."""
    observed_at_utc = status.observed_at_utc
    by_fingerprint: dict[str, OperationalAlert] = {}

    for campaign in status.campaigns:
        item_alert = _item_moved_to_error_alert(
            campaign, observed_at_utc=observed_at_utc
        )
        if item_alert is not None:
            by_fingerprint[item_alert.fingerprint] = item_alert
        for alert in _derive_campaign_dependency_alerts(
            campaign, observed_at_utc=observed_at_utc
        ):
            by_fingerprint[alert.fingerprint] = alert
        linkedin_alert = _linkedin_alert_for_campaign(
            campaign, observed_at_utc=observed_at_utc
        )
        if linkedin_alert is not None:
            by_fingerprint[linkedin_alert.fingerprint] = linkedin_alert
        stale_alert = _stale_campaign_alert(
            campaign, observed_at_utc=observed_at_utc
        )
        if stale_alert is not None:
            by_fingerprint[stale_alert.fingerprint] = stale_alert

    for execution in status.executions.get("failed", []):
        for alert in _derive_run_dependency_alerts(
            execution, observed_at_utc=observed_at_utc
        ):
            by_fingerprint[alert.fingerprint] = alert

    for delayed in status.delayed_calendar_items:
        calendar_alert = _partial_calendar_alert(
            delayed, observed_at_utc=observed_at_utc
        )
        by_fingerprint[calendar_alert.fingerprint] = calendar_alert

    return sorted(
        by_fingerprint.values(),
        key=lambda alert: (alert.alert_type, alert.fingerprint),
    )


def _summary_counts(alerts: list[OperationalAlert]) -> dict[str, Any]:
    counts = {alert_type: 0 for alert_type in ALL_ALERT_TYPES}
    for alert in alerts:
        if alert.alert_type in counts:
            counts[alert.alert_type] += 1
    return {"counts": counts, "total": len(alerts)}


def _ledger_path(base_path: Path) -> Path:
    return base_path / LEDGER_RELATIVE_DIR / LEDGER_FILENAME


def _empty_ledger() -> dict[str, Any]:
    return {"version": LEDGER_VERSION, "entries": {}}


def _load_emission_ledger(base_path: Path) -> dict[str, Any]:
    path = _ledger_path(base_path)
    if not path.is_file():
        return _empty_ledger()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("operational-alerts ledger unreadable; treating as empty")
        return _empty_ledger()
    if not isinstance(raw, dict):
        return _empty_ledger()
    entries = raw.get("entries")
    if not isinstance(entries, dict):
        entries = {}
    return {"version": LEDGER_VERSION, "entries": entries}


def _write_emission_ledger(base_path: Path, ledger: dict[str, Any]) -> None:
    path = _ledger_path(base_path)
    _atomic_write_json(path, ledger)


def _post_webhook(
    webhook_url: str,
    payload: dict[str, Any],
    *,
    client: httpx.Client | None = None,
) -> bool:
    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=_WEBHOOK_TIMEOUT_SECONDS)
    assert client is not None
    try:
        response = client.post(webhook_url, json=payload)
        return 200 <= response.status_code < 300
    except httpx.HTTPError:
        logger.warning("operational-alerts webhook delivery failed")
        return False
    finally:
        if own_client:
            client.close()


def _emit_alerts(
    base_path: Path,
    alerts: list[OperationalAlert],
    *,
    settings: FlowAOperationalAlertsSettings,
    observed_at_utc: str,
    client: httpx.Client | None = None,
) -> EmissionResult:
    if not settings.enabled:
        return EmissionResult(
            requested=True,
            status=EMISSION_STATUS_DISABLED,
        )
    if not settings.webhook_configured:
        return EmissionResult(
            requested=True,
            status=EMISSION_STATUS_MISCONFIGURED,
        )

    ledger = _load_emission_ledger(base_path)
    entries: dict[str, Any] = dict(ledger.get("entries") or {})
    emitted: list[str] = []
    already: list[str] = []
    failed: list[str] = []
    ledger_changed = False

    for alert in alerts:
        fingerprint = alert.fingerprint
        if fingerprint in entries:
            already.append(fingerprint)
            continue
        ok = _post_webhook(
            settings.webhook_url,
            {
                "observed_at_utc": observed_at_utc,
                "alert": alert.webhook_payload(),
            },
            client=client,
        )
        if not ok:
            failed.append(fingerprint)
            continue
        entries[fingerprint] = {
            "alert_type": alert.alert_type,
            "first_emitted_at_utc": observed_at_utc,
            "last_emitted_at_utc": observed_at_utc,
            **(
                {"campaign_id": alert.campaign_id}
                if alert.campaign_id is not None
                else {}
            ),
            **({"run_id": alert.run_id} if alert.run_id is not None else {}),
            **(
                {"calendar_item_id": alert.calendar_item_id}
                if alert.calendar_item_id is not None
                else {}
            ),
            **(
                {"workflow_id": alert.workflow_id}
                if alert.workflow_id is not None
                else {}
            ),
            **(
                {"execution_id": alert.execution_id}
                if alert.execution_id is not None
                else {}
            ),
        }
        emitted.append(fingerprint)
        ledger_changed = True

    if ledger_changed:
        _write_emission_ledger(
            base_path,
            {"version": LEDGER_VERSION, "entries": entries},
        )

    if failed and not emitted:
        status = EMISSION_STATUS_FAILED
    elif failed and emitted:
        status = EMISSION_STATUS_PARTIAL
    elif emitted and already:
        status = EMISSION_STATUS_PARTIAL
    elif emitted:
        status = EMISSION_STATUS_EMITTED
    elif already:
        status = EMISSION_STATUS_ALREADY_EMITTED
    else:
        # No candidates to emit.
        status = EMISSION_STATUS_EMITTED

    return EmissionResult(
        requested=True,
        status=status,
        emitted_fingerprints=emitted,
        already_emitted_fingerprints=already,
        failed_fingerprints=failed,
    )


def evaluate_flow_a_operational_alerts(
    base_path: Path,
    *,
    now_utc: str | None = None,
    emit: bool = False,
    settings: FlowAOperationalAlertsSettings | None = None,
    http_client: httpx.Client | None = None,
) -> FlowAOperationalAlertsResult:
    """Evaluate US-028/US-029/US-030 alerts; optionally emit via fail-closed webhook."""
    status = get_flow_a_operational_status(base_path, now_utc=now_utc)
    by_fingerprint: dict[str, OperationalAlert] = {
        alert.fingerprint: alert for alert in derive_operational_alerts(status)
    }
    unhealthy = derive_unhealthy_worker_alert(
        base_path, observed_at_utc=status.observed_at_utc
    )
    if unhealthy is not None:
        by_fingerprint[unhealthy.fingerprint] = unhealthy
    for alert in derive_failed_n8n_workflow_alerts(
        base_path, observed_at_utc=status.observed_at_utc
    ):
        by_fingerprint[alert.fingerprint] = alert
    alerts = sorted(
        by_fingerprint.values(),
        key=lambda alert: (alert.alert_type, alert.fingerprint),
    )
    summary = _summary_counts(alerts)

    if not emit:
        emission = EmissionResult(
            requested=False,
            status=EMISSION_STATUS_NOT_REQUESTED,
        )
    else:
        resolved = settings or load_flow_a_operational_alerts_settings()
        emission = _emit_alerts(
            base_path,
            alerts,
            settings=resolved,
            observed_at_utc=status.observed_at_utc,
            client=http_client,
        )

    return FlowAOperationalAlertsResult(
        status=status.status,
        observed_at_utc=status.observed_at_utc,
        alerts=alerts,
        summary=summary,
        data_issues=list(status.data_issues),
        emission=emission,
    )


# Public API for alert evaluation / emission.
__all__ = [
    "ALERT_BLOG_PUBLICATION_FAILURE",
    "ALERT_FAILED_N8N_WORKFLOW",
    "ALERT_IMAGE_GENERATION_FAILURE",
    "ALERT_ITEM_MOVED_TO_ERROR",
    "ALERT_LINKEDIN_TOKEN_OR_PUBLICATION_FAILURE",
    "ALERT_PARTIAL_CALENDAR_EXECUTION",
    "ALERT_STALE_CAMPAIGN",
    "ALERT_UNHEALTHY_WORKER",
    "ALL_ALERT_TYPES",
    "EMISSION_STATUS_ALREADY_EMITTED",
    "EMISSION_STATUS_DISABLED",
    "EMISSION_STATUS_EMITTED",
    "EMISSION_STATUS_FAILED",
    "EMISSION_STATUS_MISCONFIGURED",
    "EMISSION_STATUS_NOT_REQUESTED",
    "EMISSION_STATUS_PARTIAL",
    "LEDGER_FILENAME",
    "LEDGER_RELATIVE_DIR",
    "ORCHESTRATION_FAILURES_FILENAME",
    "ORCHESTRATION_REASON_CODES",
    "ORCHESTRATION_REASON_N8N_ERROR_TRIGGER",
    "ORCHESTRATION_REASON_N8N_HTTP_NODE_FAILED",
    "ORCHESTRATION_REASON_N8N_WORKFLOW_FAILED",
    "SEVERITY_ERROR",
    "SEVERITY_WARNING",
    "US028_ALERT_TYPES",
    "US029_ALERT_TYPES",
    "US030_ALERT_TYPES",
    "EmissionResult",
    "FlowAOperationalAlertsResult",
    "OperationalAlert",
    "OrchestrationFailureReportResult",
    "derive_failed_n8n_workflow_alerts",
    "derive_operational_alerts",
    "derive_unhealthy_worker_alert",
    "evaluate_flow_a_operational_alerts",
    "report_orchestration_failure",
]
