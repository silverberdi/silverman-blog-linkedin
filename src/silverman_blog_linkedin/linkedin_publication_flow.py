"""Flow A LinkedIn publication queue, publish-due, and cancel orchestration."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.campaign_lifecycle import (
    CampaignLifecycleError,
    FLOW_A,
    FLOW_B,
    METADATA_CAMPAIGNS_RELATIVE,
    STATE_DISTRIBUTION_COMPLETE,
    STATE_DISTRIBUTION_SCHEDULED,
    STATE_FLOW_A_COMPLETE,
    normalize_scheduled_at_utc,
    read_campaign_metadata,
    write_campaign_metadata,
)
from silverman_blog_linkedin.linkedin_client import (
    HttpClientProtocol,
    build_commentary,
    create_member_text_post,
)
from silverman_blog_linkedin.linkedin_config import (
    LinkedInPublicationSettings,
    load_linkedin_publication_settings,
)
from silverman_blog_linkedin.linkedin_token_provider import resolve_linkedin_access_token
from silverman_blog_linkedin.run_metadata import utc_now_iso

PUBLISH_STATE_PENDING = "pending"
PUBLISH_STATE_QUEUED = "queued"
PUBLISH_STATE_PUBLISHED = "published"
PUBLISH_STATE_FAILED = "failed"
PUBLISH_STATE_CANCELLED = "cancelled"

PUBLICATION_MODE_SAFETY_DELAY = "safety_delay"

LINKEDIN_PUBLISH_CAMPAIGN_NOT_FOUND = "linkedin_publish_campaign_not_found"
LINKEDIN_PUBLISH_FLOW_NOT_ALLOWED = "linkedin_publish_flow_not_allowed"
LINKEDIN_PUBLISH_INVALID_CAMPAIGN_STATE = "linkedin_publish_invalid_campaign_state"
LINKEDIN_PUBLISH_VARIANT_NOT_FOUND = "linkedin_publish_variant_not_found"
LINKEDIN_PUBLISH_VARIANT_NOT_PENDING = "linkedin_publish_variant_not_pending"
LINKEDIN_PUBLISH_VARIANT_NOT_QUEUED = "linkedin_publish_variant_not_queued"
LINKEDIN_PUBLISH_VARIANT_NOT_DUE = "linkedin_publish_variant_not_due"
LINKEDIN_PUBLISH_ARTIFACT_MISSING = "linkedin_publish_artifact_missing"
LINKEDIN_PUBLISH_ARTIFACT_HASH_CHANGED = "linkedin_publish_artifact_hash_changed"
LINKEDIN_PUBLISH_MISSING_SOURCE_PUBLIC_URL = "linkedin_publish_missing_source_public_url"
LINKEDIN_PUBLISH_TOKEN_MISSING = "linkedin_publish_token_missing"
LINKEDIN_PUBLISH_MEMBER_URN_MISSING = "linkedin_publish_member_urn_missing"
LINKEDIN_PUBLISH_TOKEN_INVALID = "linkedin_publish_token_invalid"
LINKEDIN_PUBLISH_TOKEN_EXPIRED = "linkedin_publish_token_expired"
LINKEDIN_PUBLISH_INSUFFICIENT_PERMISSION = "linkedin_publish_insufficient_permission"
LINKEDIN_PUBLISH_NOT_ENABLED = "linkedin_publish_not_enabled"
LINKEDIN_PUBLISH_API_ERROR = "linkedin_publish_api_error"
LINKEDIN_PUBLISH_CONTENT_INVALID = "linkedin_publish_content_invalid"
LINKEDIN_PUBLISH_METADATA_WRITE_FAILED = "linkedin_publish_metadata_write_failed"
LINKEDIN_PUBLISH_CANCEL_NOT_ALLOWED = "linkedin_publish_cancel_not_allowed"
LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_NOT_DUE = (
    "linkedin_publish_auto_queue_skipped_not_due"
)
LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_SUPERVISION = (
    "linkedin_publish_auto_queue_skipped_supervision"
)
LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_STATE = (
    "linkedin_publish_auto_queue_skipped_state"
)
LINKEDIN_SUPERVISION_ACTION_NOT_ALLOWED = "linkedin_supervision_action_not_allowed"
LINKEDIN_OAUTH_TOKEN_MISSING = "linkedin_oauth_token_missing"
LINKEDIN_OAUTH_REFRESH_FAILED = "linkedin_oauth_refresh_failed"
LINKEDIN_OAUTH_REAUTHORIZATION_REQUIRED = "linkedin_oauth_reauthorization_required"

QUEUE_ELIGIBLE_PUBLISH_STATES = frozenset({PUBLISH_STATE_PENDING, PUBLISH_STATE_FAILED})

PUBLICATION_ELIGIBLE_CAMPAIGN_STATES = frozenset(
    {
        STATE_DISTRIBUTION_SCHEDULED,
        STATE_DISTRIBUTION_COMPLETE,
        STATE_FLOW_A_COMPLETE,
    }
)


@dataclass
class LinkedInPublicationVariantResult:
    campaign_id: str
    variant: str
    publish_state: str
    publish_after_utc: str | None = None
    published_at: str | None = None
    linkedin_post_urn: str | None = None
    status: str = "completed"
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LinkedInQueuePublicationResult:
    status: str
    campaign_id: str | None = None
    variant: str | None = None
    state: str | None = None
    publish_state: str | None = None
    dry_run: bool = True
    publish_after_utc: str | None = None
    publication_queued_at: str | None = None
    publication_mode: str | None = None
    publication_safety_delay_minutes: int | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata_written: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LinkedInAutoQueueVariantResult:
    campaign_id: str
    variant: str
    publish_state: str
    publish_after_utc: str | None = None
    linkedin_post_urn: str | None = None
    published_at: str | None = None
    status: str = "completed"
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str | None = None
    metadata_written: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LinkedInPublishDueResult:
    status: str
    dry_run: bool = True
    publish_now: bool = False
    results: list[LinkedInPublicationVariantResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    auto_queue_pending: bool = False
    auto_queue_results: list[LinkedInAutoQueueVariantResult] = field(
        default_factory=list
    )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "status": self.status,
            "dry_run": self.dry_run,
            "publish_now": self.publish_now,
            "results": [item.to_dict() for item in self.results],
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }
        if self.auto_queue_pending:
            payload["auto_queue_pending"] = True
            payload["auto_queue_results"] = [
                item.to_dict() for item in self.auto_queue_results
            ]
        return payload


@dataclass
class LinkedInCancelPublicationResult:
    status: str
    campaign_id: str | None = None
    variant: str | None = None
    state: str | None = None
    publish_state: str | None = None
    dry_run: bool = True
    phase: str | None = None
    operator_supervision: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata_written: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _get_variant_metadata_map(campaign: dict[str, Any]) -> dict[str, dict[str, Any]]:
    variants = campaign.get("variants") or []
    return {
        entry["variant"]: entry
        for entry in variants
        if isinstance(entry, dict) and entry.get("variant")
    }


def _find_variant_entry(
    campaign: dict[str, Any], variant: str
) -> dict[str, Any] | None:
    return _get_variant_metadata_map(campaign).get(variant)


def _read_artifact_text(base_path: Path, artifact_relative_path: str) -> str | None:
    artifact_path = base_path / artifact_relative_path
    if not artifact_path.is_file():
        return None
    return artifact_path.read_text(encoding="utf-8")


def _verify_artifact(
    base_path: Path, entry: dict[str, Any]
) -> tuple[str | None, str | None]:
    artifact_relative = entry.get("artifact_relative_path")
    stored_hash = entry.get("derivative_content_sha256")
    if not artifact_relative or not stored_hash:
        return None, LINKEDIN_PUBLISH_ARTIFACT_MISSING
    artifact_path = base_path / artifact_relative
    if not artifact_path.is_file():
        return None, LINKEDIN_PUBLISH_ARTIFACT_MISSING
    on_disk_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    if on_disk_hash != stored_hash:
        return None, LINKEDIN_PUBLISH_ARTIFACT_HASH_CHANGED
    return artifact_path.read_text(encoding="utf-8"), None


def _validate_campaign_eligibility(
    campaign: dict[str, Any] | None,
) -> list[str]:
    if campaign is None:
        return [LINKEDIN_PUBLISH_CAMPAIGN_NOT_FOUND]
    if campaign.get("flow") == FLOW_B:
        return [LINKEDIN_PUBLISH_FLOW_NOT_ALLOWED]
    if campaign.get("state") not in PUBLICATION_ELIGIBLE_CAMPAIGN_STATES:
        return [LINKEDIN_PUBLISH_INVALID_CAMPAIGN_STATE]
    return []


def _resolve_source_public_url(campaign: dict[str, Any]) -> str | None:
    url = campaign.get("source_public_url")
    if isinstance(url, str) and url.strip():
        return url.strip()
    package = campaign.get("linkedin_package") or {}
    package_url = package.get("source_public_url")
    if isinstance(package_url, str) and package_url.strip():
        return package_url.strip()
    return None


def _parse_utc(value: str) -> datetime:
    normalized = normalize_scheduled_at_utc(value)
    return datetime.strptime(normalized, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _compute_publish_after_utc(
    *,
    now: datetime,
    safety_delay_minutes: int,
    publish_after_utc: str | None,
) -> str:
    if publish_after_utc is not None:
        return normalize_scheduled_at_utc(publish_after_utc)
    due = now + timedelta(minutes=safety_delay_minutes)
    return due.strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_real_publish_config(
    settings: LinkedInPublicationSettings,
) -> list[str]:
    if not settings.publication_enabled:
        return [LINKEDIN_PUBLISH_NOT_ENABLED]
    return []


def _list_campaign_ids(base_path: Path) -> list[str]:
    campaigns_dir = base_path / METADATA_CAMPAIGNS_RELATIVE
    if not campaigns_dir.is_dir():
        return []
    return sorted(path.stem for path in campaigns_dir.glob("*.json"))


def queue_linkedin_publication(
    base_path: Path,
    *,
    campaign_id: str,
    variant: str,
    dry_run: bool = True,
    safety_delay_minutes: int | None = None,
    publish_after_utc: str | None = None,
    environ: dict[str, str] | None = None,
    now: datetime | None = None,
) -> LinkedInQueuePublicationResult:
    """Authorize a variant for LinkedIn publication with safety delay metadata."""
    settings_load = load_linkedin_publication_settings(environ)
    if settings_load.config_invalid:
        return LinkedInQueuePublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            dry_run=dry_run,
            errors=["linkedin_publish_config_invalid"],
        )

    settings = settings_load.settings
    resolved_delay = (
        safety_delay_minutes
        if safety_delay_minutes is not None
        else settings.default_safety_delay_minutes
    )

    campaign = read_campaign_metadata(base_path, campaign_id)
    eligibility_errors = _validate_campaign_eligibility(campaign)
    if eligibility_errors:
        return LinkedInQueuePublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state") if campaign else None,
            dry_run=dry_run,
            errors=eligibility_errors,
        )
    assert campaign is not None

    entry = _find_variant_entry(campaign, variant)
    if entry is None:
        return LinkedInQueuePublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            dry_run=dry_run,
            errors=[LINKEDIN_PUBLISH_VARIANT_NOT_FOUND],
        )

    publish_state = entry.get("publish_state")
    if publish_state not in QUEUE_ELIGIBLE_PUBLISH_STATES:
        return LinkedInQueuePublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=dry_run,
            errors=[LINKEDIN_PUBLISH_VARIANT_NOT_PENDING],
        )

    _, artifact_error = _verify_artifact(base_path, entry)
    if artifact_error:
        return LinkedInQueuePublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=dry_run,
            errors=[artifact_error],
        )

    if _resolve_source_public_url(campaign) is None:
        return LinkedInQueuePublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=dry_run,
            errors=[LINKEDIN_PUBLISH_MISSING_SOURCE_PUBLIC_URL],
        )

    current = now or datetime.now(timezone.utc)
    planned_publish_after = _compute_publish_after_utc(
        now=current,
        safety_delay_minutes=resolved_delay,
        publish_after_utc=publish_after_utc,
    )

    if dry_run:
        return LinkedInQueuePublicationResult(
            status="completed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=True,
            publish_after_utc=planned_publish_after,
            publication_mode=PUBLICATION_MODE_SAFETY_DELAY,
            publication_safety_delay_minutes=resolved_delay,
            metadata_written=False,
        )

    working = deepcopy(campaign)
    metadata_map = _get_variant_metadata_map(working)
    updated_entry = dict(metadata_map[variant])
    queued_at = utc_now_iso()
    updated_entry["publish_state"] = PUBLISH_STATE_QUEUED
    updated_entry["publish_after_utc"] = planned_publish_after
    updated_entry["publication_queued_at"] = queued_at
    updated_entry["publication_mode"] = PUBLICATION_MODE_SAFETY_DELAY
    updated_entry["publication_safety_delay_minutes"] = resolved_delay
    updated_entry.pop("linkedin_publication", None)
    metadata_map[variant] = updated_entry
    working["variants"] = list(metadata_map.values())

    write_result = write_campaign_metadata(base_path, campaign_id, working)
    if not write_result.written:
        return LinkedInQueuePublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=working.get("state"),
            publish_state=publish_state,
            dry_run=False,
            publish_after_utc=planned_publish_after,
            publication_mode=PUBLICATION_MODE_SAFETY_DELAY,
            publication_safety_delay_minutes=resolved_delay,
            errors=[LINKEDIN_PUBLISH_METADATA_WRITE_FAILED],
            metadata_written=False,
        )

    return LinkedInQueuePublicationResult(
        status="completed",
        campaign_id=campaign_id,
        variant=variant,
        state=working.get("state"),
        publish_state=PUBLISH_STATE_QUEUED,
        dry_run=False,
        publish_after_utc=planned_publish_after,
        publication_queued_at=queued_at,
        publication_mode=PUBLICATION_MODE_SAFETY_DELAY,
        publication_safety_delay_minutes=resolved_delay,
        metadata_written=True,
    )


def _publish_single_variant(
    base_path: Path,
    *,
    campaign_id: str,
    variant: str,
    dry_run: bool,
    publish_now: bool,
    settings: LinkedInPublicationSettings,
    environ: dict[str, str] | None,
    http_client: HttpClientProtocol | None,
    now: datetime,
) -> LinkedInPublicationVariantResult:
    campaign = read_campaign_metadata(base_path, campaign_id)
    eligibility_errors = _validate_campaign_eligibility(campaign)
    if eligibility_errors:
        return LinkedInPublicationVariantResult(
            campaign_id=campaign_id,
            variant=variant,
            publish_state="unknown",
            status="failed",
            errors=eligibility_errors,
        )
    assert campaign is not None

    entry = _find_variant_entry(campaign, variant)
    if entry is None:
        return LinkedInPublicationVariantResult(
            campaign_id=campaign_id,
            variant=variant,
            publish_state="unknown",
            status="failed",
            errors=[LINKEDIN_PUBLISH_VARIANT_NOT_FOUND],
        )

    publish_state = entry.get("publish_state")
    if publish_state == PUBLISH_STATE_PUBLISHED:
        return LinkedInPublicationVariantResult(
            campaign_id=campaign_id,
            variant=variant,
            publish_state=PUBLISH_STATE_PUBLISHED,
            published_at=entry.get("published_at"),
            linkedin_post_urn=entry.get("linkedin_post_urn"),
            status="completed",
            warnings=["linkedin_publish_already_published"],
        )

    if publish_state != PUBLISH_STATE_QUEUED:
        return LinkedInPublicationVariantResult(
            campaign_id=campaign_id,
            variant=variant,
            publish_state=publish_state or "unknown",
            status="failed",
            errors=[LINKEDIN_PUBLISH_VARIANT_NOT_QUEUED],
        )

    publish_after = entry.get("publish_after_utc")
    if not publish_now and publish_after:
        due_at = _parse_utc(publish_after)
        if due_at > now:
            return LinkedInPublicationVariantResult(
                campaign_id=campaign_id,
                variant=variant,
                publish_state=PUBLISH_STATE_QUEUED,
                publish_after_utc=publish_after,
                status="completed",
                skipped=True,
                skip_reason=LINKEDIN_PUBLISH_VARIANT_NOT_DUE,
            )

    artifact_text, artifact_error = _verify_artifact(base_path, entry)
    if artifact_error:
        return LinkedInPublicationVariantResult(
            campaign_id=campaign_id,
            variant=variant,
            publish_state=PUBLISH_STATE_QUEUED,
            status="failed",
            errors=[artifact_error],
        )
    assert artifact_text is not None

    blog_url = _resolve_source_public_url(campaign)
    if blog_url is None:
        return LinkedInPublicationVariantResult(
            campaign_id=campaign_id,
            variant=variant,
            publish_state=PUBLISH_STATE_QUEUED,
            status="failed",
            errors=[LINKEDIN_PUBLISH_MISSING_SOURCE_PUBLIC_URL],
        )

    if dry_run:
        return LinkedInPublicationVariantResult(
            campaign_id=campaign_id,
            variant=variant,
            publish_state=PUBLISH_STATE_QUEUED,
            publish_after_utc=publish_after,
            status="completed",
            warnings=["linkedin_publish_dry_run"],
        )

    config_errors = _validate_real_publish_config(settings)
    if config_errors:
        return LinkedInPublicationVariantResult(
            campaign_id=campaign_id,
            variant=variant,
            publish_state=PUBLISH_STATE_QUEUED,
            publish_after_utc=publish_after,
            status="failed",
            errors=config_errors,
        )

    token_result = resolve_linkedin_access_token(environ, http_client=http_client, now=now)
    if token_result.status == "action_required":
        return LinkedInPublicationVariantResult(
            campaign_id=campaign_id,
            variant=variant,
            publish_state=PUBLISH_STATE_QUEUED,
            publish_after_utc=publish_after,
            status="failed",
            errors=[token_result.error_code or LINKEDIN_OAUTH_TOKEN_MISSING],
        )

    publish_settings = LinkedInPublicationSettings(
        access_token=token_result.access_token or "",
        member_urn=token_result.member_urn or "",
        publication_enabled=settings.publication_enabled,
        default_safety_delay_minutes=settings.default_safety_delay_minutes,
        api_version=settings.api_version,
    )

    commentary = build_commentary(variant_text=artifact_text, blog_url=blog_url)
    api_result = create_member_text_post(
        publish_settings,
        commentary=commentary,
        client=http_client,
    )

    working = deepcopy(campaign)
    metadata_map = _get_variant_metadata_map(working)
    updated_entry = dict(metadata_map[variant])

    if api_result.error_code:
        failed_at = utc_now_iso()
        updated_entry["publish_state"] = PUBLISH_STATE_FAILED
        updated_entry["linkedin_publication"] = {
            "last_error_code": api_result.error_code,
            "last_failed_at": failed_at,
            "retryable": api_result.retryable,
            "http_status": api_result.http_status,
        }
        metadata_map[variant] = updated_entry
        working["variants"] = list(metadata_map.values())
        write_result = write_campaign_metadata(base_path, campaign_id, working)
        return LinkedInPublicationVariantResult(
            campaign_id=campaign_id,
            variant=variant,
            publish_state=PUBLISH_STATE_FAILED if write_result.written else PUBLISH_STATE_QUEUED,
            status="failed",
            errors=[api_result.error_code]
            + (
                [LINKEDIN_PUBLISH_METADATA_WRITE_FAILED]
                if not write_result.written
                else []
            ),
        )

    published_at = utc_now_iso()
    updated_entry["publish_state"] = PUBLISH_STATE_PUBLISHED
    updated_entry["published_at"] = published_at
    updated_entry["linkedin_post_urn"] = api_result.post_urn
    updated_entry["linkedin_publication"] = {
        "provider": "linkedin_rest_posts",
        "post_urn": api_result.post_urn,
        "published_at": published_at,
        "http_status": api_result.http_status,
    }
    metadata_map[variant] = updated_entry
    working["variants"] = list(metadata_map.values())

    write_result = write_campaign_metadata(base_path, campaign_id, working)
    if not write_result.written:
        return LinkedInPublicationVariantResult(
            campaign_id=campaign_id,
            variant=variant,
            publish_state=PUBLISH_STATE_QUEUED,
            status="failed",
            errors=[LINKEDIN_PUBLISH_METADATA_WRITE_FAILED],
        )

    return LinkedInPublicationVariantResult(
        campaign_id=campaign_id,
        variant=variant,
        publish_state=PUBLISH_STATE_PUBLISHED,
        published_at=published_at,
        linkedin_post_urn=api_result.post_urn,
        status="completed",
    )


def _collect_queued_targets(
    base_path: Path,
    *,
    campaign_id: str | None,
    variant: str | None,
) -> list[tuple[str, str]]:
    if campaign_id and variant:
        return [(campaign_id, variant)]
    if campaign_id and not variant:
        campaign = read_campaign_metadata(base_path, campaign_id)
        if campaign is None:
            return []
        return [
            (campaign_id, entry["variant"])
            for entry in campaign.get("variants") or []
            if isinstance(entry, dict)
            and entry.get("variant")
            and entry.get("publish_state") == PUBLISH_STATE_QUEUED
        ]
    targets: list[tuple[str, str]] = []
    for cid in _list_campaign_ids(base_path):
        campaign = read_campaign_metadata(base_path, cid)
        if campaign is None:
            continue
        if campaign.get("flow") != FLOW_A:
            continue
        if campaign.get("state") not in PUBLICATION_ELIGIBLE_CAMPAIGN_STATES:
            continue
        for entry in campaign.get("variants") or []:
            if not isinstance(entry, dict):
                continue
            if entry.get("publish_state") != PUBLISH_STATE_QUEUED:
                continue
            variant_id = entry.get("variant")
            if variant_id:
                targets.append((cid, variant_id))
    return targets


def _collect_pending_targets(
    base_path: Path,
    *,
    campaign_id: str | None,
    variant: str | None,
) -> list[tuple[str, str, dict[str, Any]]]:
    campaign_ids = [campaign_id] if campaign_id else _list_campaign_ids(base_path)
    targets: list[tuple[str, str, dict[str, Any]]] = []
    for cid in campaign_ids:
        campaign = read_campaign_metadata(base_path, cid)
        if campaign is None:
            continue
        if campaign.get("flow") != FLOW_A:
            continue
        if campaign.get("state") != STATE_DISTRIBUTION_SCHEDULED:
            continue
        for entry in campaign.get("variants") or []:
            if not isinstance(entry, dict):
                continue
            variant_id = entry.get("variant")
            if not isinstance(variant_id, str) or not variant_id:
                continue
            if variant is not None and variant_id != variant:
                continue
            targets.append((cid, variant_id, entry))
    return targets


def _auto_queue_skip_reason(
    entry: dict[str, Any],
    *,
    publish_now: bool,
    now: datetime,
) -> str | None:
    publish_state = entry.get("publish_state")
    if publish_state == PUBLISH_STATE_CANCELLED:
        return LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_SUPERVISION
    if publish_state != PUBLISH_STATE_PENDING:
        return LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_STATE

    supervision = entry.get("operator_supervision")
    if not isinstance(supervision, dict):
        supervision = {}
    last_action = supervision.get("last_action")
    auto_queue_eligible = supervision.get("auto_queue_eligible")

    scheduled_at = entry.get("scheduled_at_utc")
    schedule_valid = False
    try:
        if isinstance(scheduled_at, str):
            scheduled_due = _parse_utc(scheduled_at) <= now
            schedule_valid = True
        else:
            scheduled_due = False
    except (CampaignLifecycleError, TypeError, ValueError):
        scheduled_due = False

    if last_action == "defer":
        if not scheduled_due:
            return LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_SUPERVISION
        return None
    if auto_queue_eligible is False:
        return LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_SUPERVISION
    if not schedule_valid:
        return LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_NOT_DUE
    if not scheduled_due and not publish_now:
        return LINKEDIN_PUBLISH_AUTO_QUEUE_SKIPPED_NOT_DUE
    return None


def _auto_queue_pending_variants(
    base_path: Path,
    *,
    campaign_id: str | None,
    variant: str | None,
    dry_run: bool,
    publish_now: bool,
    environ: dict[str, str] | None,
    now: datetime,
) -> tuple[list[LinkedInAutoQueueVariantResult], list[tuple[str, str, str | None]]]:
    outcomes: list[LinkedInAutoQueueVariantResult] = []
    planned_targets: list[tuple[str, str, str | None]] = []
    targets = _collect_pending_targets(
        base_path, campaign_id=campaign_id, variant=variant
    )

    for target_campaign_id, target_variant, entry in targets:
        publish_state = str(entry.get("publish_state") or "unknown")
        skip_reason = _auto_queue_skip_reason(
            entry, publish_now=publish_now, now=now
        )
        if skip_reason is not None:
            linkedin_post_urn: str | None = None
            published_at: str | None = None
            if publish_state == PUBLISH_STATE_PUBLISHED:
                stored_urn = entry.get("linkedin_post_urn")
                stored_published_at = entry.get("published_at")
                linkedin_post_urn = (
                    stored_urn if isinstance(stored_urn, str) else None
                )
                published_at = (
                    stored_published_at
                    if isinstance(stored_published_at, str)
                    else None
                )
            outcomes.append(
                LinkedInAutoQueueVariantResult(
                    campaign_id=target_campaign_id,
                    variant=target_variant,
                    publish_state=publish_state,
                    linkedin_post_urn=linkedin_post_urn,
                    published_at=published_at,
                    skipped=True,
                    skip_reason=skip_reason,
                    warnings=[skip_reason],
                )
            )
            continue

        queue_result = queue_linkedin_publication(
            base_path,
            campaign_id=target_campaign_id,
            variant=target_variant,
            dry_run=dry_run,
            environ=environ,
            now=now,
        )
        planned_state = (
            PUBLISH_STATE_QUEUED
            if queue_result.status == "completed"
            else publish_state
        )
        outcomes.append(
            LinkedInAutoQueueVariantResult(
                campaign_id=target_campaign_id,
                variant=target_variant,
                publish_state=planned_state,
                publish_after_utc=queue_result.publish_after_utc,
                status=queue_result.status,
                errors=list(queue_result.errors),
                warnings=list(queue_result.warnings),
                metadata_written=queue_result.metadata_written,
            )
        )
        if queue_result.status == "completed":
            planned_targets.append(
                (
                    target_campaign_id,
                    target_variant,
                    queue_result.publish_after_utc,
                )
            )

    return outcomes, planned_targets


def _planned_dry_run_publish_result(
    *,
    campaign_id: str,
    variant: str,
    publish_after_utc: str | None,
    publish_now: bool,
    now: datetime,
) -> LinkedInPublicationVariantResult:
    if not publish_now and publish_after_utc:
        try:
            if _parse_utc(publish_after_utc) > now:
                return LinkedInPublicationVariantResult(
                    campaign_id=campaign_id,
                    variant=variant,
                    publish_state=PUBLISH_STATE_QUEUED,
                    publish_after_utc=publish_after_utc,
                    skipped=True,
                    skip_reason=LINKEDIN_PUBLISH_VARIANT_NOT_DUE,
                )
        except (TypeError, ValueError):
            pass
    return LinkedInPublicationVariantResult(
        campaign_id=campaign_id,
        variant=variant,
        publish_state=PUBLISH_STATE_QUEUED,
        publish_after_utc=publish_after_utc,
        warnings=["linkedin_publish_dry_run"],
    )


def publish_linkedin_due_variants(
    base_path: Path,
    *,
    campaign_id: str | None = None,
    variant: str | None = None,
    dry_run: bool = True,
    publish_now: bool = False,
    auto_queue_pending: bool = False,
    environ: dict[str, str] | None = None,
    http_client: HttpClientProtocol | None = None,
    now: datetime | None = None,
) -> LinkedInPublishDueResult:
    """Publish eligible queued variants to LinkedIn when due."""
    settings_load = load_linkedin_publication_settings(environ)
    if settings_load.config_invalid:
        return LinkedInPublishDueResult(
            status="failed",
            dry_run=dry_run,
            publish_now=publish_now,
            auto_queue_pending=auto_queue_pending,
            errors=["linkedin_publish_config_invalid"],
        )

    settings = settings_load.settings
    current = now or datetime.now(timezone.utc)
    auto_queue_results: list[LinkedInAutoQueueVariantResult] = []
    planned_auto_queue_targets: list[tuple[str, str, str | None]] = []

    if auto_queue_pending:
        auto_queue_results, planned_auto_queue_targets = _auto_queue_pending_variants(
            base_path,
            campaign_id=campaign_id,
            variant=variant,
            dry_run=dry_run,
            publish_now=publish_now,
            environ=environ,
            now=current,
        )

    if campaign_id and not variant:
        campaign = read_campaign_metadata(base_path, campaign_id)
        if campaign is None:
            return LinkedInPublishDueResult(
                status="failed",
                dry_run=dry_run,
                publish_now=publish_now,
                auto_queue_pending=auto_queue_pending,
                auto_queue_results=auto_queue_results,
                errors=[LINKEDIN_PUBLISH_CAMPAIGN_NOT_FOUND],
            )

    if auto_queue_pending and campaign_id and variant:
        campaign = read_campaign_metadata(base_path, campaign_id)
        entry = _find_variant_entry(campaign, variant) if campaign else None
        targets = (
            [(campaign_id, variant)]
            if entry
            and entry.get("publish_state")
            in {PUBLISH_STATE_QUEUED, PUBLISH_STATE_PUBLISHED}
            else []
        )
    else:
        targets = _collect_queued_targets(
            base_path, campaign_id=campaign_id, variant=variant
        )
    if campaign_id and variant and not targets:
        campaign = read_campaign_metadata(base_path, campaign_id)
        if campaign is None:
            return LinkedInPublishDueResult(
                status="failed",
                dry_run=dry_run,
                publish_now=publish_now,
                auto_queue_pending=auto_queue_pending,
                auto_queue_results=auto_queue_results,
                errors=[LINKEDIN_PUBLISH_CAMPAIGN_NOT_FOUND],
            )

    if not targets and not (dry_run and planned_auto_queue_targets):
        return LinkedInPublishDueResult(
            status="completed",
            dry_run=dry_run,
            publish_now=publish_now,
            results=[],
            warnings=["linkedin_publish_no_queued_variants"],
            auto_queue_pending=auto_queue_pending,
            auto_queue_results=auto_queue_results,
        )

    results: list[LinkedInPublicationVariantResult] = []
    top_level_errors: list[str] = []

    if dry_run:
        queued_target_keys = set(targets)
        for target_campaign_id, target_variant, publish_after_utc in (
            planned_auto_queue_targets
        ):
            if (target_campaign_id, target_variant) in queued_target_keys:
                continue
            results.append(
                _planned_dry_run_publish_result(
                    campaign_id=target_campaign_id,
                    variant=target_variant,
                    publish_after_utc=publish_after_utc,
                    publish_now=publish_now,
                    now=current,
                )
            )

    for target_campaign_id, target_variant in targets:
        result = _publish_single_variant(
            base_path,
            campaign_id=target_campaign_id,
            variant=target_variant,
            dry_run=dry_run,
            publish_now=publish_now,
            settings=settings,
            environ=environ,
            http_client=http_client,
            now=current,
        )
        results.append(result)
        if result.status == "failed" and result.errors:
            for code in result.errors:
                if code not in top_level_errors:
                    top_level_errors.append(code)

    publish_evidence = {
        (item.campaign_id, item.variant): item
        for item in results
        if item.publish_state == PUBLISH_STATE_PUBLISHED
        and item.linkedin_post_urn
    }
    for auto_queue_result in auto_queue_results:
        match = publish_evidence.get(
            (auto_queue_result.campaign_id, auto_queue_result.variant)
        )
        if match is None:
            continue
        auto_queue_result.linkedin_post_urn = match.linkedin_post_urn
        auto_queue_result.published_at = match.published_at

    for auto_queue_result in auto_queue_results:
        if auto_queue_result.status != "failed":
            continue
        for code in auto_queue_result.errors:
            if code not in top_level_errors:
                top_level_errors.append(code)

    overall_status = "completed"
    if any(item.status == "failed" for item in results) or any(
        item.status == "failed" for item in auto_queue_results
    ):
        overall_status = "failed"
    elif not results:
        overall_status = "completed"

    return LinkedInPublishDueResult(
        status=overall_status,
        dry_run=dry_run,
        publish_now=publish_now,
        results=results,
        errors=top_level_errors,
        auto_queue_pending=auto_queue_pending,
        auto_queue_results=auto_queue_results,
    )


def cancel_linkedin_publication(
    base_path: Path,
    *,
    campaign_id: str,
    variant: str,
    dry_run: bool = True,
    reason: str | None = None,
    idempotency_key: str | None = None,
) -> LinkedInCancelPublicationResult:
    """Cancel a pending or queued variant before real LinkedIn publication."""
    from silverman_blog_linkedin.linkedin_supervision_flow import (
        SUPERVISION_PHASE_POST_QUEUE,
        SUPERVISION_PHASE_PRE_QUEUE,
        apply_supervision_cancellation,
    )

    campaign = read_campaign_metadata(base_path, campaign_id)
    eligibility_errors = _validate_campaign_eligibility(campaign)
    if eligibility_errors:
        return LinkedInCancelPublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state") if campaign else None,
            dry_run=dry_run,
            errors=eligibility_errors,
        )
    assert campaign is not None

    entry = _find_variant_entry(campaign, variant)
    if entry is None:
        return LinkedInCancelPublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            dry_run=dry_run,
            errors=[LINKEDIN_PUBLISH_VARIANT_NOT_FOUND],
        )

    publish_state = entry.get("publish_state")
    if publish_state == PUBLISH_STATE_PUBLISHED:
        return LinkedInCancelPublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=dry_run,
            errors=[LINKEDIN_PUBLISH_CANCEL_NOT_ALLOWED],
        )

    if publish_state == PUBLISH_STATE_PENDING:
        cancel_phase = SUPERVISION_PHASE_PRE_QUEUE
    elif publish_state == PUBLISH_STATE_QUEUED:
        cancel_phase = SUPERVISION_PHASE_POST_QUEUE
    else:
        return LinkedInCancelPublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=dry_run,
            errors=[LINKEDIN_SUPERVISION_ACTION_NOT_ALLOWED],
        )

    if dry_run:
        return LinkedInCancelPublicationResult(
            status="completed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=True,
            phase=cancel_phase,
            metadata_written=False,
        )

    working = deepcopy(campaign)
    metadata_map = _get_variant_metadata_map(working)
    updated_entry = dict(metadata_map[variant])
    cancelled_at = utc_now_iso()
    existing_supervision = updated_entry.get("operator_supervision")
    if isinstance(existing_supervision, dict):
        existing_supervision = deepcopy(existing_supervision)
    else:
        existing_supervision = None

    updated_entry, cancel_error = apply_supervision_cancellation(
        updated_entry,
        phase=cancel_phase,
        cancelled_at=cancelled_at,
        reason=reason,
        idempotency_key=idempotency_key,
        existing_supervision=existing_supervision,
    )
    if cancel_error and cancel_error != "replay":
        return LinkedInCancelPublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=campaign.get("state"),
            publish_state=publish_state,
            dry_run=False,
            errors=[cancel_error],
        )

    is_replay = cancel_error == "replay"
    if not is_replay:
        updated_entry["publish_state"] = PUBLISH_STATE_CANCELLED
        if cancel_phase == SUPERVISION_PHASE_POST_QUEUE:
            linkedin_publication = updated_entry.get("linkedin_publication")
            if not isinstance(linkedin_publication, dict):
                linkedin_publication = {}
            else:
                linkedin_publication = dict(linkedin_publication)
            linkedin_publication["cancelled_at"] = cancelled_at
            updated_entry["linkedin_publication"] = linkedin_publication

    metadata_map[variant] = updated_entry
    working["variants"] = list(metadata_map.values())

    if is_replay:
        return LinkedInCancelPublicationResult(
            status="completed",
            campaign_id=campaign_id,
            variant=variant,
            state=working.get("state"),
            publish_state=updated_entry.get("publish_state"),
            dry_run=False,
            phase=cancel_phase,
            operator_supervision=updated_entry.get("operator_supervision"),
            metadata_written=False,
        )

    write_result = write_campaign_metadata(base_path, campaign_id, working)
    if not write_result.written:
        return LinkedInCancelPublicationResult(
            status="failed",
            campaign_id=campaign_id,
            variant=variant,
            state=working.get("state"),
            publish_state=publish_state,
            dry_run=False,
            errors=[LINKEDIN_PUBLISH_METADATA_WRITE_FAILED],
            metadata_written=False,
        )

    return LinkedInCancelPublicationResult(
        status="completed",
        campaign_id=campaign_id,
        variant=variant,
        state=working.get("state"),
        publish_state=PUBLISH_STATE_CANCELLED,
        dry_run=False,
        phase=cancel_phase,
        operator_supervision=updated_entry.get("operator_supervision"),
        metadata_written=True,
    )
