"""Read-only aggregation of pending Flow A LinkedIn variants for supervision (US-038)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
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
    load_calendar,
)
from silverman_blog_linkedin.linkedin_config import load_linkedin_publication_settings
from silverman_blog_linkedin.run_metadata import utc_now_iso

CAMPAIGNS_SOURCE = "campaigns"
CALENDAR_SOURCE = "calendar"

CAMPAIGNS_DIRECTORY_NOT_FOUND = "campaigns_directory_not_found"
CAMPAIGNS_DIRECTORY_INVALID = "campaigns_directory_invalid"
CAMPAIGN_FILE_PATH_OUTSIDE_SOURCE = "campaign_file_path_outside_source"
CAMPAIGN_FILE_INVALID = "campaign_file_invalid"
CAMPAIGN_ID_INVALID = "campaign_id_invalid"
CAMPAIGN_ID_FILENAME_MISMATCH = "campaign_id_filename_mismatch"
LINKEDIN_VARIANTS_INVALID = "linkedin_variants_invalid"
LINKEDIN_VARIANT_INVALID = "linkedin_variant_invalid"
LINKEDIN_PUBLISH_STATE_INVALID = "linkedin_publish_state_invalid"
CALENDAR_CAMPAIGN_AMBIGUOUS = "calendar_campaign_ambiguous"

PUBLISH_STATE_PENDING = "pending"
KNOWN_PUBLISH_STATES = frozenset(
    {"pending", "queued", "published", "failed", "cancelled"}
)

STATUS_OK = "ok"
STATUS_PARTIAL = "partial"


@dataclass(frozen=True)
class SupervisionIssue:
    source: str
    identifier: str | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PendingSupervisionVariant:
    campaign_id: str
    variant_id: str
    audience: str | None
    scheduled_at_utc: str | None
    publish_state: str
    calendar_item_id: str | None = None
    calendar_title: str | None = None
    calendar_due_at_utc: str | None = None
    calendar_status: str | None = None
    operator_supervision_last_action: str | None = None
    auto_queue_eligible: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PendingSupervisionResult:
    status: str
    observed_at_utc: str
    read_only: bool
    linkedin_publication_enabled: bool
    variants: list[PendingSupervisionVariant] = field(default_factory=list)
    issues: list[SupervisionIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "observed_at_utc": self.observed_at_utc,
            "read_only": self.read_only,
            "linkedin_publication_enabled": self.linkedin_publication_enabled,
            "variants": [item.to_dict() for item in self.variants],
            "issues": [item.to_dict() for item in self.issues],
        }


def _safe_artifact_identifier(path: Path) -> str:
    return path.name


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


def _calendar_index(
    base_path: Path, issues: list[SupervisionIssue]
) -> dict[str, dict[str, Any]]:
    """Map campaign_id -> first calendar item (by item_id); flag ambiguity."""
    calendar_path = base_path / CALENDAR_RELATIVE_PATH
    if not calendar_path.exists():
        issues.append(
            SupervisionIssue(CALENDAR_SOURCE, "calendar.json", CALENDAR_FILE_NOT_FOUND)
        )
        return {}

    calendar, errors = load_calendar(base_path)
    if calendar is None:
        reason = errors[0] if errors else CALENDAR_SCHEMA_INVALID
        issues.append(SupervisionIssue(CALENDAR_SOURCE, "calendar.json", reason))
        return {}

    items = calendar.get("items", [])
    if not isinstance(items, list):
        issues.append(
            SupervisionIssue(CALENDAR_SOURCE, "calendar.json", CALENDAR_SCHEMA_INVALID)
        )
        return {}

    by_campaign: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        campaign_id = item.get("campaign_id")
        if not isinstance(campaign_id, str) or not campaign_id.strip():
            continue
        by_campaign.setdefault(campaign_id, []).append(item)

    selected: dict[str, dict[str, Any]] = {}
    for campaign_id, matches in by_campaign.items():
        ordered = sorted(
            matches,
            key=lambda item: str(item.get("item_id") or ""),
        )
        selected[campaign_id] = ordered[0]
        if len(ordered) > 1:
            issues.append(
                SupervisionIssue(
                    CALENDAR_SOURCE,
                    campaign_id,
                    CALENDAR_CAMPAIGN_AMBIGUOUS,
                )
            )
    return selected


def _optional_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _supervision_context(
    entry: dict[str, Any],
) -> tuple[str | None, bool | None]:
    supervision = entry.get("operator_supervision")
    if not isinstance(supervision, dict):
        return None, None
    last_action = _optional_str(supervision.get("last_action"))
    eligible = supervision.get("auto_queue_eligible")
    if isinstance(eligible, bool):
        return last_action, eligible
    return last_action, None


def _pending_rows_from_campaign(
    campaign: dict[str, Any],
    *,
    campaign_id: str,
    calendar_item: dict[str, Any] | None,
    issues: list[SupervisionIssue],
) -> list[PendingSupervisionVariant]:
    variants_raw = campaign.get("variants")
    if variants_raw is None:
        return []
    if not isinstance(variants_raw, list):
        issues.append(
            SupervisionIssue(CAMPAIGNS_SOURCE, campaign_id, LINKEDIN_VARIANTS_INVALID)
        )
        return []

    rows: list[PendingSupervisionVariant] = []
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
        if publish_state != PUBLISH_STATE_PENDING:
            continue

        last_action, auto_queue_eligible = _supervision_context(entry)
        rows.append(
            PendingSupervisionVariant(
                campaign_id=campaign_id,
                variant_id=variant_id,
                audience=_optional_str(entry.get("audience")),
                scheduled_at_utc=_optional_str(entry.get("scheduled_at_utc")),
                publish_state=PUBLISH_STATE_PENDING,
                calendar_item_id=(
                    _optional_str(calendar_item.get("item_id"))
                    if calendar_item
                    else None
                ),
                calendar_title=(
                    _optional_str(calendar_item.get("title")) if calendar_item else None
                ),
                calendar_due_at_utc=(
                    _optional_str(calendar_item.get("due_at_utc"))
                    if calendar_item
                    else None
                ),
                calendar_status=(
                    _optional_str(calendar_item.get("status")) if calendar_item else None
                ),
                operator_supervision_last_action=last_action,
                auto_queue_eligible=auto_queue_eligible,
            )
        )
    return rows


def _load_pending_variants(
    base_path: Path,
    *,
    calendar_by_campaign: dict[str, dict[str, Any]],
    issues: list[SupervisionIssue],
) -> list[PendingSupervisionVariant]:
    directory = _resolved_campaigns_directory(base_path, issues)
    if directory is None:
        return []

    rows: list[PendingSupervisionVariant] = []
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

        # Detect unreadable JSON without mutating: try parse, then use helper.
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
            _pending_rows_from_campaign(
                campaign,
                campaign_id=persisted_id,
                calendar_item=calendar_by_campaign.get(persisted_id),
                issues=issues,
            )
        )

    rows.sort(
        key=lambda item: (
            item.scheduled_at_utc or "",
            item.campaign_id,
            item.variant_id,
        )
    )
    return rows


def get_pending_linkedin_variant_supervision(
    base_path: Path,
    *,
    environ: dict[str, str] | None = None,
) -> PendingSupervisionResult:
    """Aggregate pending LinkedIn variants without mutation or external calls."""
    issues: list[SupervisionIssue] = []
    calendar_by_campaign = _calendar_index(base_path, issues)
    variants = _load_pending_variants(
        base_path,
        calendar_by_campaign=calendar_by_campaign,
        issues=issues,
    )
    publication = load_linkedin_publication_settings(environ=environ)
    issues = sorted(
        set(issues),
        key=lambda item: (item.source, item.identifier or "", item.reason),
    )
    return PendingSupervisionResult(
        status=STATUS_PARTIAL if issues else STATUS_OK,
        observed_at_utc=utc_now_iso(),
        read_only=True,
        linkedin_publication_enabled=publication.settings.publication_enabled,
        variants=variants,
        issues=issues,
    )


def console_html_path() -> Path:
    """Return the committed static console HTML path."""
    return Path(__file__).resolve().parent / "static" / (
        "linkedin_variant_supervision_console.html"
    )


def load_console_html() -> str:
    """Load Story 1 static console HTML from the package static asset."""
    path = console_html_path()
    return path.read_text(encoding="utf-8")
