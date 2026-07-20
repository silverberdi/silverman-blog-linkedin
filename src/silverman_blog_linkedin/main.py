"""FastAPI application and HTTP routes."""

from __future__ import annotations

import hashlib
import html
import logging
import os
import re
from typing import Literal
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator, model_validator

from silverman_blog_linkedin import SERVICE_NAME, __version__
from silverman_blog_linkedin.auth import require_api_key
from silverman_blog_linkedin.blog_publish_flow import publish_blog_post
from silverman_blog_linkedin.campaign_lifecycle import (
    CampaignLifecycleError,
    validate_campaign_id,
)
from silverman_blog_linkedin.config import Settings, load_settings
from silverman_blog_linkedin.deepseek_client import generate_linkedin_draft_content
from silverman_blog_linkedin.deepseek_config import load_deepseek_settings
from silverman_blog_linkedin.draft_writer import (
    check_review_dir_ready,
    validate_source_path_shape,
    write_draft_file,
)
from silverman_blog_linkedin.editorial_calendar_flow_a_execute import (
    execute_due_editorial_calendar_flow_a,
)
from silverman_blog_linkedin.editorial_calendar_plan import (
    get_editorial_calendar_status,
    plan_editorial_calendar_due,
    validate_canonical_utc_timestamp,
)
from silverman_blog_linkedin.editorial_calendar_schedule_update import (
    update_editorial_calendar_item_schedule,
)
from silverman_blog_linkedin.flow_b_calendar_gap_detect import (
    detect_next_week_calendar_gaps,
)
from silverman_blog_linkedin.flow_b_calendar_gap_trigger import (
    run_flow_b_gap_trigger,
)
from silverman_blog_linkedin.flow_b_blog_draft_approval import (
    ERROR_DRAFT_ALREADY_REJECTED,
    ERROR_DRAFT_ID_INVALID,
    ERROR_DRAFT_NOT_APPROVABLE,
    ERROR_DRAFT_NOT_FOUND,
    ERROR_DRAFT_NOT_REJECTABLE,
    ERROR_IMAGE_NOT_FOUND,
    ERROR_PATH_TRAVERSAL,
    ERROR_SIDECAR_INVALID,
    ERROR_SIDECAR_WRITE_FAILED,
    STATUS_APPROVED,
    STATUS_REJECTED,
    DraftDecisionResult,
    PendingDraftDetail,
    approve_pending_approval_draft,
    get_pending_approval_draft,
    list_pending_approval_drafts,
    reject_pending_approval_draft,
    resolve_pending_approval_image_path,
)
from silverman_blog_linkedin.flow_b_blog_draft_promotion import (
    ERROR_APPROVAL_METADATA_MISSING,
    ERROR_DRAFT_NOT_APPROVED,
    ERROR_DRAFT_PAIR_INCOMPLETE,
    ERROR_DRAFT_REJECTED,
    ERROR_PROMOTE_MOVE_FAILED,
    ERROR_READY_COLLISION,
    ERROR_SIDECAR_WRITE_FAILED as ERROR_PROMOTE_SIDECAR_WRITE_FAILED,
    STATUS_PROMOTED,
    DraftPromoteResult,
    promote_pending_approval_draft,
)
from silverman_blog_linkedin.flow_b_blog_draft_generation import (
    ERROR_ANTI_AI_BLOCKED as DRAFT_ERROR_ANTI_AI_BLOCKED,
    ERROR_CANON_MISSING as DRAFT_ERROR_CANON_MISSING,
    ERROR_CANON_SECTION_MISSING as DRAFT_ERROR_CANON_SECTION_MISSING,
    ERROR_CONFIG_INVALID as DRAFT_ERROR_CONFIG_INVALID,
    ERROR_SETTINGS_UNAVAILABLE as DRAFT_ERROR_SETTINGS_UNAVAILABLE,
    ERROR_TOPIC_INVALID as DRAFT_ERROR_TOPIC_INVALID,
    ERROR_TOPICS_DUPLICATE as DRAFT_ERROR_TOPICS_DUPLICATE,
    ERROR_TOPICS_EMPTY as DRAFT_ERROR_TOPICS_EMPTY,
    STATUS_DRAFTS_GENERATED,
    STATUS_DRAFTS_PARTIAL,
    generate_flow_b_blog_drafts,
    validate_draft_request_fields,
)
from silverman_blog_linkedin.flow_b_topic_discovery import (
    ERROR_CANON_MISSING,
    ERROR_CANON_SECTION_MISSING,
    ERROR_CONFIG_INVALID,
    ERROR_DISCOVERY_FAILED,
    ERROR_NOT_OBJECTIVE_ALIGNED,
    ERROR_SETTINGS_UNAVAILABLE,
    STATUS_DISCOVERY_FAILED,
    STATUS_TOPICS_DISCOVERED,
    discover_flow_b_topics,
    validate_discovery_request_fields,
)
from silverman_blog_linkedin.flow_b_gap_operator_settings import (
    ALLOWED_GAP_SCAN_MODES,
    ALLOWED_WEEKDAYS,
    ERROR_SETTINGS_STORE_NOT_CONFIGURED,
    ERROR_SETTINGS_STORE_UNAVAILABLE,
    is_valid_hh_mm,
    is_valid_iana_timezone,
    load_gap_operator_settings,
    save_gap_operator_settings,
)
from silverman_blog_linkedin.flow_a_ready_path_completion import (
    complete_flow_a_ready_path,
)
from silverman_blog_linkedin.flow_a_incomplete_campaign_recovery import (
    REASON_CAMPAIGN_NOT_FOUND,
    REASON_INVALID_CAMPAIGN_ID,
    REASON_MALFORMED_CAMPAIGN,
    REASON_NOT_FLOW_A,
    STOP_AFTER_STAGE_VALUES,
    cancel_incomplete_campaign_recovery,
    inspect_incomplete_campaign_recovery,
    repair_incomplete_campaign_recovery,
    resume_incomplete_campaign_recovery,
)
from silverman_blog_linkedin.flow_a_operational_alerts import (
    ORCHESTRATION_REASON_CODES,
    evaluate_flow_a_operational_alerts,
    report_orchestration_failure,
)
from silverman_blog_linkedin.flow_a_operational_status import (
    get_flow_a_operational_status,
)
from silverman_blog_linkedin.flow_a_schedule_visibility import (
    get_flow_a_schedule_visibility,
)
from silverman_blog_linkedin.linkedin_variant_pending_supervision import (
    console_assets_dir,
    get_pending_linkedin_variant_supervision,
    load_console_html,
)
from silverman_blog_linkedin.file_reader import (
    derive_filename,
    normalize_relative_path,
    read_blog_post_file,
)
from silverman_blog_linkedin.github_pages_publish import DEFAULT_SITE_URL, ENV_REPO_PATH
from silverman_blog_linkedin.linkedin_distribution_schedule import (
    schedule_linkedin_distribution,
)
from silverman_blog_linkedin.linkedin_oauth_flow import (
    build_authorize_result,
    build_oauth_status,
    handle_oauth_callback,
)
from silverman_blog_linkedin.linkedin_publication_flow import (
    cancel_linkedin_publication,
    publish_linkedin_due_variants,
    queue_linkedin_publication,
)
from silverman_blog_linkedin.linkedin_supervision_flow import (
    correct_linkedin_variant,
    defer_linkedin_variant,
    reopen_linkedin_variant,
)
from silverman_blog_linkedin.linkedin_package_flow import generate_linkedin_package
from silverman_blog_linkedin.linkedin_preview_validation import (
    validate_linkedin_article_preview,
)
from silverman_blog_linkedin.linkedin_prompt import build_chat_messages
from silverman_blog_linkedin.paths import validate_folders
from silverman_blog_linkedin.ready_scan import ScanResult, scan_ready_folder
from silverman_blog_linkedin.run_metadata import (
    PROVIDER_DEEPSEEK,
    build_generate_linkedin_draft_metadata_payload,
    build_generate_linkedin_draft_response,
    build_process_file_metadata_payload,
    build_process_file_response,
    build_process_ready_response,
    build_run_metadata_payload,
    build_write_linkedin_draft_metadata_payload,
    build_write_linkedin_draft_response,
    check_metadata_runs_ready,
    generate_run_id,
    utc_now_iso,
    write_run_metadata,
)

logger = logging.getLogger(__name__)

_EMPTY_SCAN = ScanResult(
    valid_files=[],
    invalid_files=[],
    ignored_files=[],
    candidate_count=0,
    valid_count=0,
    invalid_count=0,
    ignored_count=0,
)


class ProcessFileRequest(BaseModel):
    relative_path: str

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        normalized = normalize_relative_path(value)
        if not normalized:
            raise ValueError("relative_path must not be empty")
        return normalized


class WriteLinkedinDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_relative_path: str
    draft_content: str
    source_content_sha256: str | None = None
    title: str | None = None
    slug_hint: str | None = None

    @field_validator("source_relative_path")
    @classmethod
    def validate_source_relative_path(cls, value: str) -> str:
        normalized = normalize_relative_path(value)
        if not normalized:
            raise ValueError("source_relative_path must not be empty")
        return normalized

    @field_validator("draft_content")
    @classmethod
    def validate_draft_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("draft_content must not be empty or whitespace-only")
        return value


class GenerateLinkedinDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_relative_path: str
    markdown_content: str
    source_content_sha256: str | None = None
    title: str | None = None
    slug_hint: str | None = None
    tone: str | None = None
    audience: str | None = None
    variant: str | None = None
    source_public_url: str | None = None
    topic_theme: str | None = None

    @field_validator("source_relative_path")
    @classmethod
    def validate_source_relative_path(cls, value: str) -> str:
        normalized = normalize_relative_path(value)
        if not normalized:
            raise ValueError("source_relative_path must not be empty")
        return normalized

    @field_validator("markdown_content")
    @classmethod
    def validate_markdown_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("markdown_content must not be empty or whitespace-only")
        return value

    @field_validator("source_public_url")
    @classmethod
    def validate_source_public_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("source_public_url must not be empty or whitespace-only")
        parsed = urlparse(stripped)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("source_public_url must use http or https scheme")
        if not parsed.netloc:
            raise ValueError("source_public_url must have a valid host")
        return stripped

    @field_validator("topic_theme")
    @classmethod
    def validate_topic_theme(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("topic_theme must not be empty or whitespace-only")
        return stripped


class GenerateLinkedInPackageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: str | None = None
    source_relative_path: str | None = None
    variants: list[str] | None = None
    topic_theme: str | None = None
    site_url: str | None = None

    @field_validator("source_relative_path")
    @classmethod
    def validate_source_relative_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_relative_path(value)
        if not normalized:
            raise ValueError("source_relative_path must not be empty")
        return normalized

    @field_validator("campaign_id")
    @classmethod
    def validate_campaign_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("campaign_id must not be empty")
        return stripped

    @field_validator("topic_theme")
    @classmethod
    def validate_topic_theme(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("topic_theme must not be empty or whitespace-only")
        return stripped

    @field_validator("site_url")
    @classmethod
    def validate_site_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip().rstrip("/")
        if not stripped:
            raise ValueError("site_url must not be empty or whitespace-only")
        parsed = urlparse(stripped)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("site_url must use http or https scheme")
        if not parsed.netloc:
            raise ValueError("site_url must have a valid host")
        return stripped

    @model_validator(mode="after")
    def validate_exactly_one_identifier(self) -> GenerateLinkedInPackageRequest:
        has_campaign = self.campaign_id is not None
        has_source = self.source_relative_path is not None
        if has_campaign == has_source:
            raise ValueError(
                "provide exactly one of campaign_id or source_relative_path"
            )
        return self


class ScheduleLinkedInDistributionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: str | None = None
    source_relative_path: str | None = None
    strategy: str | None = None
    start_at_utc: str | None = None
    timezone: str | None = None

    @field_validator("source_relative_path")
    @classmethod
    def validate_source_relative_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_relative_path(value)
        if not normalized:
            raise ValueError("source_relative_path must not be empty")
        return normalized

    @field_validator("campaign_id")
    @classmethod
    def validate_campaign_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("campaign_id must not be empty")
        return stripped

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("strategy must not be empty or whitespace-only")
        return stripped

    @field_validator("start_at_utc")
    @classmethod
    def validate_start_at_utc(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("start_at_utc must not be empty or whitespace-only")
        return stripped

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("timezone must not be empty or whitespace-only")
        return stripped

    @model_validator(mode="after")
    def validate_exactly_one_identifier(self) -> ScheduleLinkedInDistributionRequest:
        has_campaign = self.campaign_id is not None
        has_source = self.source_relative_path is not None
        if has_campaign == has_source:
            raise ValueError(
                "provide exactly one of campaign_id or source_relative_path"
            )
        return self


class QueueLinkedInPublicationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: str
    variant: str
    dry_run: bool = True
    safety_delay_minutes: int | None = None
    publish_after_utc: str | None = None
    # US-022 failed-state recovery only; any other value is rejected with 422.
    recovery_confirmation: (
        Literal["remediation_completed", "linkedin_post_absence_verified"] | None
    ) = None

    @field_validator("campaign_id")
    @classmethod
    def validate_campaign_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("campaign_id must not be empty")
        return stripped

    @field_validator("variant")
    @classmethod
    def validate_variant(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("variant must not be empty")
        return stripped

    @field_validator("publish_after_utc")
    @classmethod
    def validate_publish_after_utc(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("publish_after_utc must not be empty or whitespace-only")
        return stripped

    @field_validator("safety_delay_minutes")
    @classmethod
    def validate_safety_delay_minutes(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 0:
            raise ValueError("safety_delay_minutes must be >= 0")
        return value


class PublishLinkedInDueVariantsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: str | None = None
    variant: str | None = None
    dry_run: bool = True
    publish_now: bool = False
    auto_queue_pending: bool = False

    @field_validator("campaign_id")
    @classmethod
    def validate_campaign_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("campaign_id must not be empty")
        return stripped

    @field_validator("variant")
    @classmethod
    def validate_variant(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("variant must not be empty")
        return stripped

    @model_validator(mode="after")
    def validate_variant_requires_campaign(
        self,
    ) -> PublishLinkedInDueVariantsRequest:
        if self.variant is not None and self.campaign_id is None:
            raise ValueError("variant requires campaign_id")
        return self


class CancelLinkedInPublicationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: str
    variant: str
    dry_run: bool = True
    reason: str | None = None
    idempotency_key: str | None = None

    @field_validator("campaign_id")
    @classmethod
    def validate_campaign_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("campaign_id must not be empty")
        return stripped

    @field_validator("variant")
    @classmethod
    def validate_variant(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("variant must not be empty")
        return stripped

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("idempotency_key must not be empty or whitespace-only")
        return stripped


class CorrectLinkedInVariantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: str
    variant: str
    draft_content: str
    dry_run: bool = True
    reason: str | None = None
    idempotency_key: str | None = None
    auto_queue_eligible: bool | None = None

    @field_validator("campaign_id")
    @classmethod
    def validate_campaign_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("campaign_id must not be empty")
        return stripped

    @field_validator("variant")
    @classmethod
    def validate_variant(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("variant must not be empty")
        return stripped

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("idempotency_key must not be empty or whitespace-only")
        return stripped


class DeferLinkedInVariantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: str
    variant: str
    new_scheduled_at_utc: str
    dry_run: bool = True
    reason: str | None = None
    idempotency_key: str | None = None
    actor: str | None = None
    source: str | None = None
    operator_timezone: str | None = None

    @field_validator("campaign_id")
    @classmethod
    def validate_campaign_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("campaign_id must not be empty")
        return stripped

    @field_validator("variant")
    @classmethod
    def validate_variant(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("variant must not be empty")
        return stripped

    @field_validator("new_scheduled_at_utc")
    @classmethod
    def validate_new_scheduled_at_utc(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("new_scheduled_at_utc must not be empty or whitespace-only")
        return stripped

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("actor")
    @classmethod
    def validate_actor(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("idempotency_key must not be empty or whitespace-only")
        return stripped

    @field_validator("operator_timezone")
    @classmethod
    def validate_operator_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ReopenLinkedInVariantRequest(BaseModel):
    """US-040J: reopen eligible cancelled variant with a new future schedule."""

    model_config = ConfigDict(extra="forbid")

    campaign_id: str
    variant: str
    new_scheduled_at_utc: str
    dry_run: bool = True
    reason: str | None = None
    idempotency_key: str | None = None
    actor: str | None = None
    source: str | None = None
    operator_timezone: str | None = None

    @field_validator("campaign_id")
    @classmethod
    def validate_campaign_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("campaign_id must not be empty")
        return stripped

    @field_validator("variant")
    @classmethod
    def validate_variant(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("variant must not be empty")
        return stripped

    @field_validator("new_scheduled_at_utc")
    @classmethod
    def validate_new_scheduled_at_utc(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("new_scheduled_at_utc must not be empty or whitespace-only")
        return stripped

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("actor")
    @classmethod
    def validate_actor(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("idempotency_key must not be empty or whitespace-only")
        return stripped

    @field_validator("operator_timezone")
    @classmethod
    def validate_operator_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ValidateLinkedInArticlePreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: str
    dry_run: bool = True

    @field_validator("campaign_id")
    @classmethod
    def validate_campaign_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("campaign_id must not be empty")
        return stripped


class PublishBlogPostRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_relative_path: str
    site_url: str | None = None
    public_slug: str | None = None
    git_publication: bool = False
    live_site_confirmation: bool = False

    @field_validator("source_relative_path")
    @classmethod
    def validate_source_relative_path(cls, value: str) -> str:
        normalized = normalize_relative_path(value)
        if not normalized:
            raise ValueError("source_relative_path must not be empty")
        return normalized

    @field_validator("site_url")
    @classmethod
    def validate_site_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip().rstrip("/")
        if not stripped:
            raise ValueError("site_url must not be empty or whitespace-only")
        parsed = urlparse(stripped)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("site_url must use http or https scheme")
        if not parsed.netloc:
            raise ValueError("site_url must have a valid host")
        return stripped

    @field_validator("public_slug")
    @classmethod
    def validate_public_slug(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("public_slug must not be empty or whitespace-only")
        return stripped


class PlanEditorialCalendarDueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    now_utc: str | None = None

    @field_validator("now_utc")
    @classmethod
    def validate_now_utc(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_canonical_utc_timestamp(value)


class UpdateEditorialCalendarItemScheduleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    new_due_at_utc: str
    dry_run: bool = True
    reason: str | None = None
    idempotency_key: str | None = None
    actor: str | None = None
    source: str | None = None
    expected_calendar_fingerprint: str | None = None
    operator_timezone: str | None = None

    @field_validator("item_id")
    @classmethod
    def validate_item_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("item_id must not be empty")
        return stripped

    @field_validator("new_due_at_utc")
    @classmethod
    def validate_new_due_at_utc(cls, value: str) -> str:
        return validate_canonical_utc_timestamp(value)

    @field_validator("reason", "actor", "source", "operator_timezone")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("idempotency_key must not be empty or whitespace-only")
        return stripped

    @field_validator("expected_calendar_fingerprint")
    @classmethod
    def validate_fingerprint(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip().lower()
        if not stripped:
            raise ValueError(
                "expected_calendar_fingerprint must not be empty or whitespace-only"
            )
        if len(stripped) != 64 or any(c not in "0123456789abcdef" for c in stripped):
            raise ValueError(
                "expected_calendar_fingerprint must be a SHA-256 hex digest"
            )
        return stripped


class FlowBGapTriggerRequest(BaseModel):
    """POST body for Flow B calendar gap trigger (US-082)."""

    model_config = ConfigDict(extra="forbid")

    now_utc: str | None = None
    dry_run: bool = False
    force_window: bool = False

    @field_validator("now_utc")
    @classmethod
    def validate_gap_trigger_now_utc(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_canonical_utc_timestamp(value)


class FlowBDiscoverTopicsRequest(BaseModel):
    """POST body for Flow B AI topic discovery (US-078). Discovery-only."""

    model_config = ConfigDict(extra="forbid")

    count: int | None = None
    target_week: str | None = None
    empty_days: list[str] | None = None
    dry_run: bool = False


class FlowBGenerateBlogDraftsRequest(BaseModel):
    """POST body for Flow B blog draft + image generation (US-079)."""

    model_config = ConfigDict(extra="forbid")

    topics: list[dict]
    target_week: str | None = None
    empty_days: list[str] | None = None
    dry_run: bool = False


class FlowBApproveDraftRequest(BaseModel):
    """POST body for Flow B pending-approval approve (US-080). Decision only."""

    model_config = ConfigDict(extra="forbid")

    approved_by: str | None = None
    dry_run: bool = False


class FlowBRejectDraftRequest(BaseModel):
    """POST body for Flow B pending-approval reject (US-080)."""

    model_config = ConfigDict(extra="forbid")

    rejection_reason: str | None = None
    dry_run: bool = False


class FlowBPromoteDraftRequest(BaseModel):
    """POST body for Flow B pending-approval promote to ready/ (US-081)."""

    model_config = ConfigDict(extra="forbid")

    promoted_by: str | None = None
    dry_run: bool = False


class GapOperatorSettingsPutRequest(BaseModel):
    """Full-document PUT body for Flow B gap operator settings (US-076)."""

    model_config = ConfigDict(extra="forbid")

    operator_timezone: str
    gap_trigger_enabled: bool
    gap_scan_mode: str
    weekly_run_local_day: str
    weekly_run_local_time: str
    min_lead_days: int
    gap_posts_threshold: int
    max_drafts_per_weekly_run: int
    density_max_per_local_day: int
    expected_row_version: int | None = None

    @field_validator("operator_timezone")
    @classmethod
    def validate_operator_timezone(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped or not is_valid_iana_timezone(stripped):
            raise ValueError("operator_timezone must be a valid IANA timezone")
        return stripped

    @field_validator("gap_scan_mode")
    @classmethod
    def validate_gap_scan_mode(cls, value: str) -> str:
        stripped = value.strip()
        if stripped not in ALLOWED_GAP_SCAN_MODES:
            raise ValueError("gap_scan_mode must be one of: next_week")
        return stripped

    @field_validator("weekly_run_local_day")
    @classmethod
    def validate_weekly_run_local_day(cls, value: str) -> str:
        stripped = value.strip().lower()
        if stripped not in ALLOWED_WEEKDAYS:
            raise ValueError(
                "weekly_run_local_day must be a lowercase weekday (monday–sunday)"
            )
        return stripped

    @field_validator("weekly_run_local_time")
    @classmethod
    def validate_weekly_run_local_time(cls, value: str) -> str:
        stripped = value.strip()
        if not is_valid_hh_mm(stripped):
            raise ValueError("weekly_run_local_time must be HH:MM in 24-hour form")
        return stripped

    @field_validator(
        "min_lead_days",
        "gap_posts_threshold",
        "max_drafts_per_weekly_run",
        "density_max_per_local_day",
    )
    @classmethod
    def validate_non_negative_int(cls, value: int) -> int:
        if value < 0:
            raise ValueError("must be a non-negative integer")
        return value


class CompleteFlowAReadyPathRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: str
    source_relative_path: str | None = None
    update_calendar: bool = True

    @field_validator("campaign_id")
    @classmethod
    def validate_campaign_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("campaign_id must not be empty")
        return stripped

    @field_validator("source_relative_path")
    @classmethod
    def validate_source_relative_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_relative_path(value)
        if not normalized:
            raise ValueError("source_relative_path must not be empty")
        return normalized


class ExecuteEditorialCalendarFlowADueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    now_utc: str | None = None
    dry_run: bool = True
    limit: int | None = None
    git_publication: bool = False
    live_site_confirmation: bool = False

    @field_validator("now_utc")
    @classmethod
    def validate_now_utc(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_canonical_utc_timestamp(value)

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError("limit must be a positive integer")
        return value


class EvaluateFlowAOperationalAlertsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    now_utc: str | None = None
    emit: bool = False

    @field_validator("now_utc")
    @classmethod
    def validate_now_utc(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_canonical_utc_timestamp(value)


class ResumeIncompleteCampaignRecoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: str
    dry_run: bool = False
    stop_after_stage: str | None = None

    @field_validator("campaign_id")
    @classmethod
    def validate_campaign_id_field(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("campaign_id must not be empty")
        if stripped.startswith("/") or ".." in stripped or "\\" in stripped:
            raise ValueError("campaign_id must not be an absolute or escaping path")
        try:
            validate_campaign_id(stripped)
        except CampaignLifecycleError as exc:
            raise ValueError(str(exc)) from exc
        return stripped

    @field_validator("stop_after_stage")
    @classmethod
    def validate_stop_after_stage(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if stripped not in STOP_AFTER_STAGE_VALUES:
            raise ValueError(
                "stop_after_stage must be one of: "
                + ", ".join(sorted(STOP_AFTER_STAGE_VALUES))
            )
        return stripped


class RepairIncompleteCampaignRecoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: str
    repair_action: Literal[
        "sync_location_from_filesystem",
        "clear_stale_execution_claim",
        "complete_partial_source_move",
    ]
    dry_run: bool = False

    @field_validator("campaign_id")
    @classmethod
    def validate_campaign_id_field(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("campaign_id must not be empty")
        if stripped.startswith("/") or ".." in stripped or "\\" in stripped:
            raise ValueError("campaign_id must not be an absolute or escaping path")
        try:
            validate_campaign_id(stripped)
        except CampaignLifecycleError as exc:
            raise ValueError(str(exc)) from exc
        return stripped


class CancelIncompleteCampaignRecoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: str
    dry_run: bool = False
    reason_code: str | None = None
    summary: str | None = None

    @field_validator("campaign_id")
    @classmethod
    def validate_campaign_id_field(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("campaign_id must not be empty")
        if stripped.startswith("/") or ".." in stripped or "\\" in stripped:
            raise ValueError("campaign_id must not be an absolute or escaping path")
        try:
            validate_campaign_id(stripped)
        except CampaignLifecycleError as exc:
            raise ValueError(str(exc)) from exc
        return stripped

    @field_validator("reason_code")
    @classmethod
    def validate_reason_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        if len(stripped) > 64:
            raise ValueError("reason_code must be at most 64 characters")
        return stripped

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = " ".join(value.split())
        if not stripped:
            return None
        if len(stripped) > 200:
            raise ValueError("summary must be at most 200 characters")
        return stripped


_SAFE_ORCHESTRATION_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")


class ReportOrchestrationFailureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str
    reason_code: str
    observed_at_utc: str | None = None
    execution_id: str | None = None
    node_name: str | None = None
    campaign_id: str | None = None
    run_id: str | None = None

    @staticmethod
    def _require_safe_token(value: str, field_name: str) -> str:
        stripped = value.strip()
        if not stripped or not _SAFE_ORCHESTRATION_TOKEN.fullmatch(stripped):
            raise ValueError(f"{field_name} must be a non-empty safe opaque token")
        return stripped

    @field_validator("workflow_id")
    @classmethod
    def validate_workflow_id(cls, value: str) -> str:
        return cls._require_safe_token(value, "workflow_id")

    @field_validator("reason_code")
    @classmethod
    def validate_reason_code(cls, value: str) -> str:
        stripped = value.strip()
        if stripped not in ORCHESTRATION_REASON_CODES:
            raise ValueError(
                "reason_code must be one of: "
                + ", ".join(sorted(ORCHESTRATION_REASON_CODES))
            )
        return stripped

    @field_validator("observed_at_utc")
    @classmethod
    def validate_observed_at_utc(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_canonical_utc_timestamp(value)

    @field_validator("execution_id", "node_name", "run_id")
    @classmethod
    def validate_optional_tokens(
        cls, value: str | None, info: ValidationInfo
    ) -> str | None:
        if value is None:
            return None
        return cls._require_safe_token(value, info.field_name)

    @field_validator("campaign_id")
    @classmethod
    def validate_campaign_id_field(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        try:
            validate_campaign_id(stripped)
        except CampaignLifecycleError as exc:
            raise ValueError(f"invalid campaign_id: {exc}") from exc
        return stripped


def _generate_linkedin_draft_editorial_fields(
    body: GenerateLinkedinDraftRequest,
) -> dict[str, str | None]:
    """Editorial and public URL fields shared by generate-linkedin-draft builders."""
    return {
        "title": body.title,
        "slug_hint": body.slug_hint,
        "tone": body.tone,
        "audience": body.audience,
        "variant": body.variant,
        "source_public_url": body.source_public_url,
        "topic_theme": body.topic_theme,
    }


def _generate_linkedin_draft_public_fields(
    body: GenerateLinkedinDraftRequest,
) -> dict[str, str | None]:
    """Public blog URL fields echoed in generate-linkedin-draft HTTP responses."""
    return {
        "source_public_url": body.source_public_url,
        "topic_theme": body.topic_theme,
    }


def _resolve_source_content_sha256(
    markdown_content: str, provided: str | None
) -> str:
    if provided is not None:
        return provided
    return hashlib.sha256(markdown_content.encode("utf-8")).hexdigest()


def _effective_slug_hint(slug_hint: str | None, variant: str | None) -> str | None:
    if slug_hint is not None:
        return slug_hint
    if variant is not None:
        return variant
    return None


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if settings is None:
        settings = load_settings()

    app = FastAPI(title=SERVICE_NAME, version=__version__)
    app.state.settings = settings

    logger.info("API key configured: yes")
    logger.info("Base path: %s", settings.base_path)
    logger.info("Listening port: %s", settings.port)

    @app.get("/health")
    def health() -> dict:
        from silverman_blog_linkedin.editorial_calendar_store import calendar_store_ready

        validation = validate_folders(settings.base_path)
        status = "healthy" if validation.folders_ready else "degraded"
        store_info = calendar_store_ready()
        return {
            "status": status,
            "service": SERVICE_NAME,
            "version": __version__,
            "base_path": str(settings.base_path),
            "folders_ready": validation.folders_ready,
            "folders": {
                name: status.to_dict()
                for name, status in validation.folders.items()
            },
            **store_info,
        }

    @app.post("/process-ready")
    def process_ready(_auth: None = Depends(require_api_key)) -> dict:
        run_id = generate_run_id()
        started_at = utc_now_iso()

        metadata_readiness = check_metadata_runs_ready(settings.base_path)
        folder_validation = validate_folders(settings.base_path)
        folders_ready = folder_validation.folders_ready

        if not metadata_readiness.ready:
            errors = [metadata_readiness.error_code or "metadata_runs_not_ready"]
            logger.info(
                "process-ready run_id=%s status=failed metadata_written=false",
                run_id,
            )
            return build_process_ready_response(
                run_id=run_id,
                status="failed",
                metadata_written=False,
                folders_ready=False,
                scan=_EMPTY_SCAN,
                errors=errors,
            )

        if not folders_ready:
            completed_at = utc_now_iso()
            errors = ["editorial_folders_not_ready"]
            payload = build_run_metadata_payload(
                run_id=run_id,
                status="failed",
                base_path=settings.base_path,
                folders_ready=False,
                scan_valid_files=[],
                scan_invalid_files=[],
                scan_ignored_files=[],
                candidate_count=0,
                valid_count=0,
                invalid_count=0,
                ignored_count=0,
                errors=errors,
                started_at=started_at,
                completed_at=completed_at,
            )
            metadata_written = write_run_metadata(
                settings.base_path, run_id, payload
            )
            logger.info(
                "process-ready run_id=%s status=failed folders_ready=false "
                "metadata_written=%s",
                run_id,
                metadata_written,
            )
            return build_process_ready_response(
                run_id=run_id,
                status="failed",
                metadata_written=metadata_written,
                folders_ready=False,
                scan=_EMPTY_SCAN,
                errors=errors if metadata_written else errors + ["metadata_write_failed"],
            )

        scan = scan_ready_folder(settings.base_path)
        completed_at = utc_now_iso()
        errors: list[str] = []
        payload = build_run_metadata_payload(
            run_id=run_id,
            status="completed",
            base_path=settings.base_path,
            folders_ready=True,
            scan_valid_files=scan.valid_files,
            scan_invalid_files=scan.invalid_files,
            scan_ignored_files=scan.ignored_files,
            candidate_count=scan.candidate_count,
            valid_count=scan.valid_count,
            invalid_count=scan.invalid_count,
            ignored_count=scan.ignored_count,
            errors=errors,
            started_at=started_at,
            completed_at=completed_at,
        )
        metadata_written = write_run_metadata(settings.base_path, run_id, payload)
        status = "completed" if metadata_written else "failed"
        if not metadata_written:
            errors = ["metadata_write_failed"]

        logger.info(
            "process-ready run_id=%s status=%s valid=%s invalid=%s ignored=%s",
            run_id,
            status,
            scan.valid_count,
            scan.invalid_count,
            scan.ignored_count,
        )
        return build_process_ready_response(
            run_id=run_id,
            status=status,
            metadata_written=metadata_written,
            folders_ready=True,
            scan=scan,
            errors=errors,
        )

    @app.post("/process-file")
    def process_file(
        body: ProcessFileRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        run_id = generate_run_id()
        started_at = utc_now_iso()
        relative_path = body.relative_path
        filename = derive_filename(relative_path)

        metadata_readiness = check_metadata_runs_ready(settings.base_path)
        if not metadata_readiness.ready:
            errors = [metadata_readiness.error_code or "metadata_runs_not_ready"]
            logger.info(
                "process-file run_id=%s status=failed metadata_written=false "
                "relative_path=%s",
                run_id,
                relative_path,
            )
            return build_process_file_response(
                run_id=run_id,
                status="failed",
                metadata_written=False,
                folders_ready=False,
                relative_path=relative_path,
                filename=filename,
                size_bytes=None,
                content_sha256=None,
                markdown_content=None,
                errors=errors,
            )

        folder_validation = validate_folders(settings.base_path)
        folders_ready = folder_validation.folders_ready

        if not folders_ready:
            completed_at = utc_now_iso()
            errors = ["editorial_folders_not_ready"]
            payload = build_process_file_metadata_payload(
                run_id=run_id,
                status="failed",
                base_path=settings.base_path,
                folders_ready=False,
                relative_path=relative_path,
                filename=filename,
                size_bytes=None,
                content_sha256=None,
                errors=errors,
                started_at=started_at,
                completed_at=completed_at,
            )
            metadata_written = write_run_metadata(
                settings.base_path, run_id, payload
            )
            logger.info(
                "process-file run_id=%s status=failed folders_ready=false "
                "metadata_written=%s relative_path=%s",
                run_id,
                metadata_written,
                relative_path,
            )
            return build_process_file_response(
                run_id=run_id,
                status="failed",
                metadata_written=metadata_written,
                folders_ready=False,
                relative_path=relative_path,
                filename=filename,
                size_bytes=None,
                content_sha256=None,
                markdown_content=None,
                errors=errors if metadata_written else errors + ["metadata_write_failed"],
            )

        read_result = read_blog_post_file(settings.base_path, relative_path)
        completed_at = utc_now_iso()
        status = "completed" if not read_result.errors else "failed"
        payload = build_process_file_metadata_payload(
            run_id=run_id,
            status=status,
            base_path=settings.base_path,
            folders_ready=True,
            relative_path=read_result.relative_path,
            filename=read_result.filename,
            size_bytes=read_result.size_bytes,
            content_sha256=read_result.content_sha256,
            errors=read_result.errors,
            started_at=started_at,
            completed_at=completed_at,
        )
        metadata_written = write_run_metadata(settings.base_path, run_id, payload)
        errors = list(read_result.errors)
        if not metadata_written:
            status = "failed"
            errors = errors + ["metadata_write_failed"]

        logger.info(
            "process-file run_id=%s status=%s relative_path=%s size_bytes=%s",
            run_id,
            status,
            read_result.relative_path,
            read_result.size_bytes,
        )
        if read_result.content_sha256:
            logger.debug(
                "process-file run_id=%s content_sha256=%s",
                run_id,
                read_result.content_sha256,
            )

        return build_process_file_response(
            run_id=run_id,
            status=status,
            metadata_written=metadata_written,
            folders_ready=True,
            relative_path=read_result.relative_path,
            filename=read_result.filename,
            size_bytes=read_result.size_bytes,
            content_sha256=read_result.content_sha256,
            markdown_content=read_result.markdown_content,
            errors=errors,
        )

    @app.post("/write-linkedin-draft")
    def write_linkedin_draft(
        body: WriteLinkedinDraftRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        run_id = generate_run_id()
        started_at = utc_now_iso()
        source_relative_path = body.source_relative_path
        source_content_sha256 = body.source_content_sha256

        metadata_readiness = check_metadata_runs_ready(settings.base_path)
        if not metadata_readiness.ready:
            errors = [metadata_readiness.error_code or "metadata_runs_not_ready"]
            logger.info(
                "write-linkedin-draft run_id=%s status=failed metadata_written=false "
                "source_relative_path=%s",
                run_id,
                source_relative_path,
            )
            return build_write_linkedin_draft_response(
                run_id=run_id,
                status="failed",
                metadata_written=False,
                source_relative_path=source_relative_path,
                source_content_sha256=source_content_sha256,
                draft_written=False,
                draft_relative_path=None,
                draft_content_sha256=None,
                size_bytes=None,
                errors=errors,
            )

        review_readiness = check_review_dir_ready(settings.base_path)
        path_errors = validate_source_path_shape(
            settings.base_path, source_relative_path
        )

        if not review_readiness.ready:
            completed_at = utc_now_iso()
            errors = [review_readiness.error_code or "review_dir_not_ready"]
            payload = build_write_linkedin_draft_metadata_payload(
                run_id=run_id,
                status="failed",
                base_path=settings.base_path,
                source_relative_path=source_relative_path,
                draft_relative_path=None,
                source_content_sha256=source_content_sha256,
                draft_content_sha256=None,
                size_bytes=None,
                draft_written=False,
                title=body.title,
                slug_hint=body.slug_hint,
                errors=errors,
                started_at=started_at,
                completed_at=completed_at,
            )
            metadata_written = write_run_metadata(
                settings.base_path, run_id, payload
            )
            logger.info(
                "write-linkedin-draft run_id=%s status=failed draft_written=false "
                "metadata_written=%s source_relative_path=%s",
                run_id,
                metadata_written,
                source_relative_path,
            )
            return build_write_linkedin_draft_response(
                run_id=run_id,
                status="failed",
                metadata_written=metadata_written,
                source_relative_path=source_relative_path,
                source_content_sha256=source_content_sha256,
                draft_written=False,
                draft_relative_path=None,
                draft_content_sha256=None,
                size_bytes=None,
                errors=errors if metadata_written else errors + ["metadata_write_failed"],
            )

        if path_errors:
            completed_at = utc_now_iso()
            payload = build_write_linkedin_draft_metadata_payload(
                run_id=run_id,
                status="failed",
                base_path=settings.base_path,
                source_relative_path=source_relative_path,
                draft_relative_path=None,
                source_content_sha256=source_content_sha256,
                draft_content_sha256=None,
                size_bytes=None,
                draft_written=False,
                title=body.title,
                slug_hint=body.slug_hint,
                errors=path_errors,
                started_at=started_at,
                completed_at=completed_at,
            )
            metadata_written = write_run_metadata(
                settings.base_path, run_id, payload
            )
            logger.info(
                "write-linkedin-draft run_id=%s status=failed draft_written=false "
                "metadata_written=%s source_relative_path=%s errors=%s",
                run_id,
                metadata_written,
                source_relative_path,
                path_errors,
            )
            return build_write_linkedin_draft_response(
                run_id=run_id,
                status="failed",
                metadata_written=metadata_written,
                source_relative_path=source_relative_path,
                source_content_sha256=source_content_sha256,
                draft_written=False,
                draft_relative_path=None,
                draft_content_sha256=None,
                size_bytes=None,
                errors=path_errors if metadata_written else path_errors + ["metadata_write_failed"],
            )

        draft_result = write_draft_file(
            settings.base_path,
            draft_content=body.draft_content,
            source_relative_path=source_relative_path,
            slug_hint=body.slug_hint,
            run_id=run_id,
        )

        if draft_result.errors:
            completed_at = utc_now_iso()
            errors = list(draft_result.errors)
            payload = build_write_linkedin_draft_metadata_payload(
                run_id=run_id,
                status="failed",
                base_path=settings.base_path,
                source_relative_path=source_relative_path,
                draft_relative_path=None,
                source_content_sha256=source_content_sha256,
                draft_content_sha256=None,
                size_bytes=None,
                draft_written=False,
                title=body.title,
                slug_hint=body.slug_hint,
                errors=errors,
                started_at=started_at,
                completed_at=completed_at,
            )
            metadata_written = write_run_metadata(
                settings.base_path, run_id, payload
            )
            logger.info(
                "write-linkedin-draft run_id=%s status=failed draft_written=false "
                "metadata_written=%s source_relative_path=%s errors=%s",
                run_id,
                metadata_written,
                source_relative_path,
                errors,
            )
            return build_write_linkedin_draft_response(
                run_id=run_id,
                status="failed",
                metadata_written=metadata_written,
                source_relative_path=source_relative_path,
                source_content_sha256=source_content_sha256,
                draft_written=False,
                draft_relative_path=None,
                draft_content_sha256=None,
                size_bytes=None,
                errors=errors if metadata_written else errors + ["metadata_write_failed"],
            )

        completed_at = utc_now_iso()
        payload = build_write_linkedin_draft_metadata_payload(
            run_id=run_id,
            status="completed",
            base_path=settings.base_path,
            source_relative_path=source_relative_path,
            draft_relative_path=draft_result.draft_relative_path,
            source_content_sha256=source_content_sha256,
            draft_content_sha256=draft_result.draft_content_sha256,
            size_bytes=draft_result.size_bytes,
            draft_written=True,
            title=body.title,
            slug_hint=body.slug_hint,
            errors=[],
            started_at=started_at,
            completed_at=completed_at,
        )
        metadata_written = write_run_metadata(settings.base_path, run_id, payload)
        errors: list[str] = []
        status = "completed"
        if not metadata_written:
            status = "failed"
            errors = ["metadata_write_failed"]

        logger.info(
            "write-linkedin-draft run_id=%s status=%s draft_written=true "
            "metadata_written=%s source_relative_path=%s draft_relative_path=%s "
            "size_bytes=%s",
            run_id,
            status,
            metadata_written,
            source_relative_path,
            draft_result.draft_relative_path,
            draft_result.size_bytes,
        )
        if draft_result.draft_content_sha256:
            logger.debug(
                "write-linkedin-draft run_id=%s draft_content_sha256=%s",
                run_id,
                draft_result.draft_content_sha256,
            )

        return build_write_linkedin_draft_response(
            run_id=run_id,
            status=status,
            metadata_written=metadata_written,
            source_relative_path=source_relative_path,
            source_content_sha256=source_content_sha256,
            draft_written=True,
            draft_relative_path=draft_result.draft_relative_path,
            draft_content_sha256=draft_result.draft_content_sha256,
            size_bytes=draft_result.size_bytes,
            errors=errors,
        )

    @app.post("/generate-linkedin-draft")
    def generate_linkedin_draft(
        body: GenerateLinkedinDraftRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        run_id = generate_run_id()
        started_at = utc_now_iso()
        source_relative_path = body.source_relative_path
        source_content_sha256 = _resolve_source_content_sha256(
            body.markdown_content, body.source_content_sha256
        )
        slug_for_filename = _effective_slug_hint(body.slug_hint, body.variant)

        metadata_readiness = check_metadata_runs_ready(settings.base_path)
        if not metadata_readiness.ready:
            errors = [metadata_readiness.error_code or "metadata_runs_not_ready"]
            logger.info(
                "generate-linkedin-draft run_id=%s status=failed metadata_written=false "
                "source_relative_path=%s provider=%s",
                run_id,
                source_relative_path,
                PROVIDER_DEEPSEEK,
            )
            return build_generate_linkedin_draft_response(
                run_id=run_id,
                status="failed",
                metadata_written=False,
                source_relative_path=source_relative_path,
                source_content_sha256=source_content_sha256,
                draft_written=False,
                draft_relative_path=None,
                draft_content_sha256=None,
                size_bytes=None,
                provider=PROVIDER_DEEPSEEK,
                model=None,
                errors=errors,
                **_generate_linkedin_draft_public_fields(body),
            )

        deepseek_load = load_deepseek_settings(os.environ)
        if deepseek_load.config_invalid or deepseek_load.settings is None:
            completed_at = utc_now_iso()
            errors = ["deepseek_config_invalid"]
            payload = build_generate_linkedin_draft_metadata_payload(
                run_id=run_id,
                status="failed",
                base_path=settings.base_path,
                provider=PROVIDER_DEEPSEEK,
                model=None,
                source_relative_path=source_relative_path,
                draft_relative_path=None,
                source_content_sha256=source_content_sha256,
                draft_content_sha256=None,
                size_bytes=None,
                draft_written=False,
                errors=errors,
                started_at=started_at,
                completed_at=completed_at,
                **_generate_linkedin_draft_editorial_fields(body),
            )
            metadata_written = write_run_metadata(
                settings.base_path, run_id, payload
            )
            logger.info(
                "generate-linkedin-draft run_id=%s status=failed "
                "metadata_written=%s errors=%s",
                run_id,
                metadata_written,
                errors,
            )
            return build_generate_linkedin_draft_response(
                run_id=run_id,
                status="failed",
                metadata_written=metadata_written,
                source_relative_path=source_relative_path,
                source_content_sha256=source_content_sha256,
                draft_written=False,
                draft_relative_path=None,
                draft_content_sha256=None,
                size_bytes=None,
                provider=PROVIDER_DEEPSEEK,
                model=None,
                errors=errors if metadata_written else errors + ["metadata_write_failed"],
                **_generate_linkedin_draft_public_fields(body),
            )

        deepseek_settings = deepseek_load.settings
        model_name = deepseek_settings.model

        if not deepseek_settings.is_configured:
            completed_at = utc_now_iso()
            errors = ["deepseek_api_key_missing"]
            payload = build_generate_linkedin_draft_metadata_payload(
                run_id=run_id,
                status="failed",
                base_path=settings.base_path,
                provider=PROVIDER_DEEPSEEK,
                model=model_name,
                source_relative_path=source_relative_path,
                draft_relative_path=None,
                source_content_sha256=source_content_sha256,
                draft_content_sha256=None,
                size_bytes=None,
                draft_written=False,
                errors=errors,
                started_at=started_at,
                completed_at=completed_at,
                **_generate_linkedin_draft_editorial_fields(body),
            )
            metadata_written = write_run_metadata(
                settings.base_path, run_id, payload
            )
            logger.info(
                "generate-linkedin-draft run_id=%s status=failed "
                "metadata_written=%s model=%s errors=%s",
                run_id,
                metadata_written,
                model_name,
                errors,
            )
            return build_generate_linkedin_draft_response(
                run_id=run_id,
                status="failed",
                metadata_written=metadata_written,
                source_relative_path=source_relative_path,
                source_content_sha256=source_content_sha256,
                draft_written=False,
                draft_relative_path=None,
                draft_content_sha256=None,
                size_bytes=None,
                provider=PROVIDER_DEEPSEEK,
                model=model_name,
                errors=errors if metadata_written else errors + ["metadata_write_failed"],
                **_generate_linkedin_draft_public_fields(body),
            )

        review_readiness = check_review_dir_ready(settings.base_path)
        if not review_readiness.ready:
            completed_at = utc_now_iso()
            errors = [review_readiness.error_code or "review_dir_not_ready"]
            payload = build_generate_linkedin_draft_metadata_payload(
                run_id=run_id,
                status="failed",
                base_path=settings.base_path,
                provider=PROVIDER_DEEPSEEK,
                model=model_name,
                source_relative_path=source_relative_path,
                draft_relative_path=None,
                source_content_sha256=source_content_sha256,
                draft_content_sha256=None,
                size_bytes=None,
                draft_written=False,
                errors=errors,
                started_at=started_at,
                completed_at=completed_at,
                **_generate_linkedin_draft_editorial_fields(body),
            )
            metadata_written = write_run_metadata(
                settings.base_path, run_id, payload
            )
            logger.info(
                "generate-linkedin-draft run_id=%s status=failed draft_written=false "
                "metadata_written=%s source_relative_path=%s errors=%s",
                run_id,
                metadata_written,
                source_relative_path,
                errors,
            )
            return build_generate_linkedin_draft_response(
                run_id=run_id,
                status="failed",
                metadata_written=metadata_written,
                source_relative_path=source_relative_path,
                source_content_sha256=source_content_sha256,
                draft_written=False,
                draft_relative_path=None,
                draft_content_sha256=None,
                size_bytes=None,
                provider=PROVIDER_DEEPSEEK,
                model=model_name,
                errors=errors if metadata_written else errors + ["metadata_write_failed"],
                **_generate_linkedin_draft_public_fields(body),
            )

        path_errors = validate_source_path_shape(
            settings.base_path, source_relative_path
        )
        if path_errors:
            completed_at = utc_now_iso()
            payload = build_generate_linkedin_draft_metadata_payload(
                run_id=run_id,
                status="failed",
                base_path=settings.base_path,
                provider=PROVIDER_DEEPSEEK,
                model=model_name,
                source_relative_path=source_relative_path,
                draft_relative_path=None,
                source_content_sha256=source_content_sha256,
                draft_content_sha256=None,
                size_bytes=None,
                draft_written=False,
                errors=path_errors,
                started_at=started_at,
                completed_at=completed_at,
                **_generate_linkedin_draft_editorial_fields(body),
            )
            metadata_written = write_run_metadata(
                settings.base_path, run_id, payload
            )
            logger.info(
                "generate-linkedin-draft run_id=%s status=failed draft_written=false "
                "metadata_written=%s source_relative_path=%s errors=%s",
                run_id,
                metadata_written,
                source_relative_path,
                path_errors,
            )
            return build_generate_linkedin_draft_response(
                run_id=run_id,
                status="failed",
                metadata_written=metadata_written,
                source_relative_path=source_relative_path,
                source_content_sha256=source_content_sha256,
                draft_written=False,
                draft_relative_path=None,
                draft_content_sha256=None,
                size_bytes=None,
                provider=PROVIDER_DEEPSEEK,
                model=model_name,
                errors=path_errors if metadata_written else path_errors + ["metadata_write_failed"],
                **_generate_linkedin_draft_public_fields(body),
            )

        messages = build_chat_messages(
            markdown_content=body.markdown_content,
            title=body.title,
            tone=body.tone,
            audience=body.audience,
            variant=body.variant,
            source_public_url=body.source_public_url,
            topic_theme=body.topic_theme,
        )
        generation = generate_linkedin_draft_content(deepseek_settings, messages)
        if generation.error_code:
            completed_at = utc_now_iso()
            errors = [generation.error_code]
            payload = build_generate_linkedin_draft_metadata_payload(
                run_id=run_id,
                status="failed",
                base_path=settings.base_path,
                provider=PROVIDER_DEEPSEEK,
                model=model_name,
                source_relative_path=source_relative_path,
                draft_relative_path=None,
                source_content_sha256=source_content_sha256,
                draft_content_sha256=None,
                size_bytes=None,
                draft_written=False,
                errors=errors,
                started_at=started_at,
                completed_at=completed_at,
                **_generate_linkedin_draft_editorial_fields(body),
            )
            metadata_written = write_run_metadata(
                settings.base_path, run_id, payload
            )
            logger.info(
                "generate-linkedin-draft run_id=%s status=failed draft_written=false "
                "metadata_written=%s model=%s errors=%s",
                run_id,
                metadata_written,
                model_name,
                errors,
            )
            return build_generate_linkedin_draft_response(
                run_id=run_id,
                status="failed",
                metadata_written=metadata_written,
                source_relative_path=source_relative_path,
                source_content_sha256=source_content_sha256,
                draft_written=False,
                draft_relative_path=None,
                draft_content_sha256=None,
                size_bytes=None,
                provider=PROVIDER_DEEPSEEK,
                model=model_name,
                errors=errors if metadata_written else errors + ["metadata_write_failed"],
                **_generate_linkedin_draft_public_fields(body),
            )

        generated_text = generation.content
        assert generated_text is not None

        draft_result = write_draft_file(
            settings.base_path,
            draft_content=generated_text,
            source_relative_path=source_relative_path,
            slug_hint=slug_for_filename,
            run_id=run_id,
        )

        if draft_result.errors:
            completed_at = utc_now_iso()
            errors = list(draft_result.errors)
            payload = build_generate_linkedin_draft_metadata_payload(
                run_id=run_id,
                status="failed",
                base_path=settings.base_path,
                provider=PROVIDER_DEEPSEEK,
                model=model_name,
                source_relative_path=source_relative_path,
                draft_relative_path=None,
                source_content_sha256=source_content_sha256,
                draft_content_sha256=None,
                size_bytes=None,
                draft_written=False,
                errors=errors,
                started_at=started_at,
                completed_at=completed_at,
                **_generate_linkedin_draft_editorial_fields(body),
            )
            metadata_written = write_run_metadata(
                settings.base_path, run_id, payload
            )
            logger.info(
                "generate-linkedin-draft run_id=%s status=failed draft_written=false "
                "metadata_written=%s source_relative_path=%s errors=%s",
                run_id,
                metadata_written,
                source_relative_path,
                errors,
            )
            return build_generate_linkedin_draft_response(
                run_id=run_id,
                status="failed",
                metadata_written=metadata_written,
                source_relative_path=source_relative_path,
                source_content_sha256=source_content_sha256,
                draft_written=False,
                draft_relative_path=None,
                draft_content_sha256=None,
                size_bytes=None,
                provider=PROVIDER_DEEPSEEK,
                model=model_name,
                errors=errors if metadata_written else errors + ["metadata_write_failed"],
                **_generate_linkedin_draft_public_fields(body),
            )

        completed_at = utc_now_iso()
        payload = build_generate_linkedin_draft_metadata_payload(
            run_id=run_id,
            status="completed",
            base_path=settings.base_path,
            provider=PROVIDER_DEEPSEEK,
            model=model_name,
            source_relative_path=source_relative_path,
            draft_relative_path=draft_result.draft_relative_path,
            source_content_sha256=source_content_sha256,
            draft_content_sha256=draft_result.draft_content_sha256,
            size_bytes=draft_result.size_bytes,
            draft_written=True,
            errors=[],
            started_at=started_at,
            completed_at=completed_at,
            **_generate_linkedin_draft_editorial_fields(body),
        )
        metadata_written = write_run_metadata(settings.base_path, run_id, payload)
        errors: list[str] = []
        status = "completed"
        if not metadata_written:
            status = "failed"
            errors = ["metadata_write_failed"]

        logger.info(
            "generate-linkedin-draft run_id=%s status=%s draft_written=true "
            "metadata_written=%s source_relative_path=%s draft_relative_path=%s "
            "model=%s provider=%s size_bytes=%s",
            run_id,
            status,
            metadata_written,
            source_relative_path,
            draft_result.draft_relative_path,
            model_name,
            PROVIDER_DEEPSEEK,
            draft_result.size_bytes,
        )
        if draft_result.draft_content_sha256:
            logger.debug(
                "generate-linkedin-draft run_id=%s draft_content_sha256=%s",
                run_id,
                draft_result.draft_content_sha256,
            )

        return build_generate_linkedin_draft_response(
            run_id=run_id,
            status=status,
            metadata_written=metadata_written,
            source_relative_path=source_relative_path,
            source_content_sha256=source_content_sha256,
            draft_written=True,
            draft_relative_path=draft_result.draft_relative_path,
            draft_content_sha256=draft_result.draft_content_sha256,
            size_bytes=draft_result.size_bytes,
            provider=PROVIDER_DEEPSEEK,
            model=model_name,
            errors=errors,
            generated_draft_content=generated_text if status == "completed" else None,
            **_generate_linkedin_draft_public_fields(body),
        )

    @app.post("/generate-linkedin-package")
    def generate_linkedin_package_endpoint(
        body: GenerateLinkedInPackageRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        result = generate_linkedin_package(
            settings.base_path,
            campaign_id=body.campaign_id,
            source_relative_path=body.source_relative_path,
            variants=body.variants,
            topic_theme=body.topic_theme,
            site_url=body.site_url,
            environ=os.environ,
        )
        logger.info(
            "generate-linkedin-package status=%s campaign_id=%s state=%s",
            result.status,
            result.campaign_id,
            result.state,
        )
        return result.to_dict()

    @app.post("/schedule-linkedin-distribution")
    def schedule_linkedin_distribution_endpoint(
        body: ScheduleLinkedInDistributionRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        result = schedule_linkedin_distribution(
            settings.base_path,
            campaign_id=body.campaign_id,
            source_relative_path=body.source_relative_path,
            strategy=body.strategy,
            start_at_utc=body.start_at_utc,
            timezone=body.timezone,
        )
        logger.info(
            "schedule-linkedin-distribution status=%s campaign_id=%s state=%s strategy=%s",
            result.status,
            result.campaign_id,
            result.state,
            result.strategy,
        )
        return result.to_dict()

    @app.post("/queue-linkedin-publication")
    def queue_linkedin_publication_endpoint(
        body: QueueLinkedInPublicationRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        result = queue_linkedin_publication(
            settings.base_path,
            campaign_id=body.campaign_id,
            variant=body.variant,
            dry_run=body.dry_run,
            safety_delay_minutes=body.safety_delay_minutes,
            publish_after_utc=body.publish_after_utc,
            recovery_confirmation=body.recovery_confirmation,
            environ=os.environ,
        )
        logger.info(
            "queue-linkedin-publication status=%s campaign_id=%s variant=%s dry_run=%s",
            result.status,
            result.campaign_id,
            result.variant,
            result.dry_run,
        )
        return result.to_dict()

    @app.post("/publish-linkedin-due-variants")
    def publish_linkedin_due_variants_endpoint(
        body: PublishLinkedInDueVariantsRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        result = publish_linkedin_due_variants(
            settings.base_path,
            campaign_id=body.campaign_id,
            variant=body.variant,
            dry_run=body.dry_run,
            publish_now=body.publish_now,
            auto_queue_pending=body.auto_queue_pending,
            environ=os.environ,
        )
        auto_queued = sum(
            1
            for item in result.auto_queue_results
            if item.status == "completed" and not item.skipped
        )
        published = sum(
            1
            for item in result.results
            if item.publish_state == "published" and item.status == "completed"
        )
        skipped = sum(item.skipped for item in result.auto_queue_results) + sum(
            item.skipped for item in result.results
        )
        logger.info(
            "publish-linkedin-due-variants status=%s dry_run=%s publish_now=%s "
            "auto_queue_pending=%s queued=%s published=%s skipped=%s results=%s",
            result.status,
            result.dry_run,
            result.publish_now,
            body.auto_queue_pending,
            auto_queued,
            published,
            skipped,
            len(result.results),
        )
        return result.to_dict()

    @app.post("/cancel-linkedin-publication")
    def cancel_linkedin_publication_endpoint(
        body: CancelLinkedInPublicationRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        result = cancel_linkedin_publication(
            settings.base_path,
            campaign_id=body.campaign_id,
            variant=body.variant,
            dry_run=body.dry_run,
            reason=body.reason,
            idempotency_key=body.idempotency_key,
        )
        logger.info(
            "cancel-linkedin-publication status=%s campaign_id=%s variant=%s dry_run=%s phase=%s",
            result.status,
            result.campaign_id,
            result.variant,
            result.dry_run,
            result.phase,
        )
        return result.to_dict()

    @app.post("/correct-linkedin-variant")
    def correct_linkedin_variant_endpoint(
        body: CorrectLinkedInVariantRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        result = correct_linkedin_variant(
            settings.base_path,
            campaign_id=body.campaign_id,
            variant=body.variant,
            draft_content=body.draft_content,
            dry_run=body.dry_run,
            reason=body.reason,
            idempotency_key=body.idempotency_key,
            auto_queue_eligible=body.auto_queue_eligible,
        )
        logger.info(
            "correct-linkedin-variant status=%s campaign_id=%s variant=%s dry_run=%s",
            result.status,
            result.campaign_id,
            result.variant,
            result.dry_run,
        )
        return result.to_dict()

    @app.post("/defer-linkedin-variant")
    def defer_linkedin_variant_endpoint(
        body: DeferLinkedInVariantRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        result = defer_linkedin_variant(
            settings.base_path,
            campaign_id=body.campaign_id,
            variant=body.variant,
            new_scheduled_at_utc=body.new_scheduled_at_utc,
            dry_run=body.dry_run,
            reason=body.reason,
            idempotency_key=body.idempotency_key,
            actor=body.actor,
            source=body.source,
            operator_timezone=body.operator_timezone,
            environ=os.environ,
        )
        logger.info(
            "defer-linkedin-variant status=%s campaign_id=%s variant=%s dry_run=%s",
            result.status,
            result.campaign_id,
            result.variant,
            result.dry_run,
        )
        return result.to_dict()

    @app.post("/reopen-linkedin-variant")
    def reopen_linkedin_variant_endpoint(
        body: ReopenLinkedInVariantRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        result = reopen_linkedin_variant(
            settings.base_path,
            campaign_id=body.campaign_id,
            variant=body.variant,
            new_scheduled_at_utc=body.new_scheduled_at_utc,
            dry_run=body.dry_run,
            reason=body.reason,
            idempotency_key=body.idempotency_key,
            actor=body.actor,
            source=body.source,
            operator_timezone=body.operator_timezone,
            environ=os.environ,
        )
        logger.info(
            "reopen-linkedin-variant status=%s campaign_id=%s variant=%s dry_run=%s "
            "publish_state=%s",
            result.status,
            result.campaign_id,
            result.variant,
            result.dry_run,
            result.publish_state,
        )
        return result.to_dict()

    @app.post("/validate-linkedin-article-preview")
    def validate_linkedin_article_preview_endpoint(
        body: ValidateLinkedInArticlePreviewRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        result = validate_linkedin_article_preview(
            settings.base_path,
            campaign_id=body.campaign_id,
            dry_run=body.dry_run,
            environ=os.environ,
        )
        logger.info(
            "validate-linkedin-article-preview status=%s campaign_id=%s dry_run=%s codes=%s",
            result.status,
            result.campaign_id,
            result.dry_run,
            len(result.codes),
        )
        return result.to_dict()

    @app.get("/linkedin/oauth/authorize", response_model=None)
    def linkedin_oauth_authorize(
        redirect: bool = Query(default=False),
        _auth: None = Depends(require_api_key),
    ):
        result = build_authorize_result(os.environ)
        if result.status != "completed" or not result.authorization_url:
            return {
                "status": result.status,
                "errors": result.errors,
            }
        if redirect:
            return RedirectResponse(url=result.authorization_url, status_code=302)
        return {"authorization_url": result.authorization_url}

    @app.get("/linkedin/oauth/callback")
    def linkedin_oauth_callback(
        code: str | None = None,
        state: str | None = None,
        error: str | None = None,
        error_description: str | None = None,
    ) -> HTMLResponse:
        result = handle_oauth_callback(
            code=code,
            state=state,
            error=error,
            error_description=error_description,
            environ=os.environ,
        )
        title = "LinkedIn OAuth"
        safe_message = html.escape(result.message, quote=True)
        if result.status == "completed":
            body = f"<h1>Authorization successful</h1><p>{safe_message}</p>"
        else:
            body = f"<h1>Authorization failed</h1><p>{safe_message}</p>"
        safe_title = html.escape(title, quote=True)
        html_doc = (
            f"<!DOCTYPE html><html><head><title>{safe_title}</title></head>"
            f"<body>{body}</body></html>"
        )
        return HTMLResponse(content=html_doc, status_code=result.http_status)

    @app.get("/linkedin/oauth/status")
    def linkedin_oauth_status(_auth: None = Depends(require_api_key)) -> dict:
        result = build_oauth_status(os.environ)
        return result.to_dict()

    @app.post("/complete-flow-a-ready-path")
    def complete_flow_a_ready_path_endpoint(
        body: CompleteFlowAReadyPathRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        result = complete_flow_a_ready_path(
            settings.base_path,
            campaign_id=body.campaign_id,
            source_relative_path=body.source_relative_path,
            update_calendar=body.update_calendar,
        )
        logger.info(
            "complete-flow-a-ready-path status=%s campaign_id=%s "
            "source_lifecycle_status=%s calendar_update_status=%s",
            result.status,
            result.campaign_id,
            result.source_lifecycle_status,
            result.calendar_update_status,
        )
        return result.to_dict()

    @app.post("/publish-blog-post")
    def publish_blog_post_endpoint(
        body: PublishBlogPostRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        site_url = body.site_url or DEFAULT_SITE_URL
        github_pages_repo_path = os.environ.get(ENV_REPO_PATH, "").strip() or None
        result = publish_blog_post(
            settings.base_path,
            body.source_relative_path,
            site_url=site_url,
            public_slug_override=body.public_slug,
            github_pages_repo_path=github_pages_repo_path,
            environ=os.environ,
            git_publication=body.git_publication,
            live_site_confirmation=body.live_site_confirmation,
        )
        logger.info(
            "publish-blog-post status=%s campaign_id=%s state=%s source_relative_path=%s",
            result.status,
            result.campaign_id,
            result.state,
            result.source_relative_path,
        )
        return result.to_dict()

    @app.post("/editorial-calendar/plan-due")
    def editorial_calendar_plan_due(
        body: PlanEditorialCalendarDueRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        result = plan_editorial_calendar_due(
            settings.base_path,
            now_utc=body.now_utc,
        )
        logger.info(
            "editorial-calendar/plan-due status=%s due_items=%s",
            result.status,
            len(result.due_items),
        )
        return result.to_dict()

    @app.get("/editorial-calendar/status")
    def editorial_calendar_status(_auth: None = Depends(require_api_key)) -> dict:
        result = get_editorial_calendar_status(settings.base_path)
        logger.info(
            "editorial-calendar/status status=%s calendar_present=%s",
            result.status,
            result.calendar_present,
        )
        return result.to_dict()

    @app.post("/editorial-calendar/update-item-schedule")
    def editorial_calendar_update_item_schedule(
        body: UpdateEditorialCalendarItemScheduleRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        result = update_editorial_calendar_item_schedule(
            settings.base_path,
            item_id=body.item_id,
            new_due_at_utc=body.new_due_at_utc,
            dry_run=body.dry_run,
            reason=body.reason,
            idempotency_key=body.idempotency_key,
            actor=body.actor,
            source=body.source,
            expected_calendar_fingerprint=body.expected_calendar_fingerprint,
            operator_timezone=body.operator_timezone,
            environ=os.environ,
        )
        logger.info(
            "editorial-calendar/update-item-schedule status=%s item_id=%s dry_run=%s",
            result.status,
            result.item_id,
            result.dry_run,
        )
        return result.to_dict()

    @app.get("/flow-a/operational-status")
    def flow_a_operational_status(
        now_utc: str | None = Query(default=None),
        _auth: None = Depends(require_api_key),
    ) -> dict:
        try:
            validated_now = (
                validate_canonical_utc_timestamp(now_utc)
                if now_utc is not None
                else None
            )
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail="now_utc must be a canonical UTC timestamp",
            ) from None
        result = get_flow_a_operational_status(
            settings.base_path,
            now_utc=validated_now,
        )
        logger.info(
            "flow-a/operational-status status=%s executions=%s campaigns=%s "
            "delayed=%s data_issues=%s",
            result.status,
            sum(len(items) for items in result.executions.values()),
            len(result.campaigns),
            len(result.delayed_calendar_items),
            len(result.data_issues),
        )
        return result.to_dict()

    @app.get("/flow-a/linkedin-variants/pending-supervision")
    def flow_a_linkedin_variants_pending_supervision(
        _auth: None = Depends(require_api_key),
    ) -> dict:
        result = get_pending_linkedin_variant_supervision(settings.base_path)
        logger.info(
            "flow-a/linkedin-variants/pending-supervision status=%s "
            "variants=%s issues=%s linkedin_publication_enabled=%s",
            result.status,
            len(result.variants),
            len(result.issues),
            result.linkedin_publication_enabled,
        )
        return result.to_dict()

    @app.get("/flow-a/schedule-visibility")
    def flow_a_schedule_visibility(
        year: int | None = None,
        month: int | None = None,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        result = get_flow_a_schedule_visibility(
            settings.base_path,
            year=year,
            month=month,
        )
        logger.info(
            "flow-a/schedule-visibility status=%s year=%s month=%s "
            "items=%s issues=%s linkedin_publication_enabled=%s",
            result.status,
            result.year,
            result.month,
            len(result.items),
            len(result.issues),
            result.linkedin_publication_enabled,
        )
        return result.to_dict()

    @app.get(
        "/flow-a/console/linkedin-variant-supervision",
        response_class=HTMLResponse,
    )
    def flow_a_console_linkedin_variant_supervision() -> HTMLResponse:
        try:
            html_doc = load_console_html()
        except OSError as exc:
            logger.error(
                "flow-a/console/linkedin-variant-supervision failed to load "
                "static asset: %s",
                exc,
            )
            raise HTTPException(
                status_code=500,
                detail="supervision console asset unavailable",
            ) from None
        return HTMLResponse(content=html_doc, status_code=200)

    _console_assets = console_assets_dir()
    if _console_assets.is_dir():
        # Same-origin hashed Vite assets; confined to the build assets directory.
        app.mount(
            "/flow-a/console/linkedin-variant-supervision/assets",
            StaticFiles(directory=str(_console_assets)),
            name="linkedin_variant_supervision_console_assets",
        )

    @app.get("/flow-a/incomplete-campaign-recovery/{campaign_id}")
    def flow_a_incomplete_campaign_recovery_inspect(
        campaign_id: str,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        stripped = campaign_id.strip()
        if (
            not stripped
            or stripped.startswith("/")
            or ".." in stripped
            or "\\" in stripped
        ):
            raise HTTPException(status_code=422, detail="invalid campaign_id")
        try:
            validate_campaign_id(stripped)
        except CampaignLifecycleError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        result = inspect_incomplete_campaign_recovery(settings.base_path, stripped)
        logger.info(
            "flow-a/incomplete-campaign-recovery inspect campaign_id=%s "
            "outcome=%s reason_code=%s last_valid_stage=%s",
            result.campaign_id,
            result.outcome,
            result.reason_code,
            result.last_valid_stage,
        )
        payload = result.to_dict()
        if result.reason_code in {
            REASON_CAMPAIGN_NOT_FOUND,
            REASON_INVALID_CAMPAIGN_ID,
            REASON_MALFORMED_CAMPAIGN,
            REASON_NOT_FLOW_A,
        }:
            raise HTTPException(status_code=404, detail=payload)
        return payload

    @app.post("/flow-a/incomplete-campaign-recovery/resume")
    def flow_a_incomplete_campaign_recovery_resume(
        body: ResumeIncompleteCampaignRecoveryRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        result = resume_incomplete_campaign_recovery(
            settings.base_path,
            campaign_id=body.campaign_id,
            dry_run=body.dry_run,
            stop_after_stage=body.stop_after_stage,
        )
        logger.info(
            "flow-a/incomplete-campaign-recovery resume campaign_id=%s "
            "outcome=%s reason_code=%s dry_run=%s last_valid_stage=%s",
            result.campaign_id,
            result.outcome,
            result.reason_code,
            body.dry_run,
            result.last_valid_stage,
        )
        payload = result.to_dict()
        if result.reason_code in {
            REASON_CAMPAIGN_NOT_FOUND,
            REASON_INVALID_CAMPAIGN_ID,
            REASON_MALFORMED_CAMPAIGN,
            REASON_NOT_FLOW_A,
        }:
            raise HTTPException(status_code=404, detail=payload)
        return payload

    @app.post("/flow-a/incomplete-campaign-recovery/repair")
    def flow_a_incomplete_campaign_recovery_repair(
        body: RepairIncompleteCampaignRecoveryRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        result = repair_incomplete_campaign_recovery(
            settings.base_path,
            campaign_id=body.campaign_id,
            repair_action=body.repair_action,
            dry_run=body.dry_run,
        )
        logger.info(
            "flow-a/incomplete-campaign-recovery repair campaign_id=%s "
            "outcome=%s reason_code=%s repair_action=%s dry_run=%s",
            result.campaign_id,
            result.outcome,
            result.reason_code,
            body.repair_action,
            body.dry_run,
        )
        payload = result.to_dict()
        if result.reason_code in {
            REASON_CAMPAIGN_NOT_FOUND,
            REASON_INVALID_CAMPAIGN_ID,
            REASON_MALFORMED_CAMPAIGN,
            REASON_NOT_FLOW_A,
        }:
            raise HTTPException(status_code=404, detail=payload)
        return payload

    @app.post("/flow-a/incomplete-campaign-recovery/cancel")
    def flow_a_incomplete_campaign_recovery_cancel(
        body: CancelIncompleteCampaignRecoveryRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        result = cancel_incomplete_campaign_recovery(
            settings.base_path,
            campaign_id=body.campaign_id,
            dry_run=body.dry_run,
            reason_code=body.reason_code,
            summary=body.summary,
        )
        logger.info(
            "flow-a/incomplete-campaign-recovery cancel campaign_id=%s "
            "outcome=%s reason_code=%s dry_run=%s",
            result.campaign_id,
            result.outcome,
            result.reason_code,
            body.dry_run,
        )
        payload = result.to_dict()
        if result.reason_code in {
            REASON_CAMPAIGN_NOT_FOUND,
            REASON_INVALID_CAMPAIGN_ID,
            REASON_MALFORMED_CAMPAIGN,
            REASON_NOT_FLOW_A,
        }:
            raise HTTPException(status_code=404, detail=payload)
        return payload

    @app.post("/flow-a/operational-alerts/evaluate")
    def flow_a_operational_alerts_evaluate(
        body: EvaluateFlowAOperationalAlertsRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        result = evaluate_flow_a_operational_alerts(
            settings.base_path,
            now_utc=body.now_utc,
            emit=body.emit,
        )
        logger.info(
            "flow-a/operational-alerts/evaluate status=%s emit=%s alerts=%s "
            "emission=%s data_issues=%s",
            result.status,
            body.emit,
            len(result.alerts),
            result.emission.status,
            len(result.data_issues),
        )
        return result.to_dict()

    @app.post("/flow-a/operational-alerts/report-orchestration-failure")
    def flow_a_operational_alerts_report_orchestration_failure(
        body: ReportOrchestrationFailureRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        result = report_orchestration_failure(
            settings.base_path,
            workflow_id=body.workflow_id,
            reason_code=body.reason_code,
            observed_at_utc=body.observed_at_utc,
            execution_id=body.execution_id,
            node_name=body.node_name,
            campaign_id=body.campaign_id,
            run_id=body.run_id,
        )
        logger.info(
            "flow-a/operational-alerts/report-orchestration-failure "
            "fingerprint=%s workflow_id=%s reason_code=%s created=%s",
            result.fingerprint,
            result.workflow_id,
            result.reason_code,
            result.created,
        )
        return result.to_dict()

    @app.post("/editorial-calendar/execute-flow-a-due")
    def editorial_calendar_execute_flow_a_due(
        body: ExecuteEditorialCalendarFlowADueRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        result = execute_due_editorial_calendar_flow_a(
            settings.base_path,
            now_utc=body.now_utc,
            dry_run=body.dry_run,
            limit=body.limit,
            git_publication=body.git_publication,
            live_site_confirmation=body.live_site_confirmation,
        )
        logger.info(
            "editorial-calendar/execute-flow-a-due status=%s dry_run=%s items=%s counts=%s",
            result.status,
            result.dry_run,
            len(result.items),
            result.counts,
        )
        return result.to_dict()

    @app.post("/flow-b/gap-trigger")
    def post_flow_b_gap_trigger(
        body: FlowBGapTriggerRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        """Authenticated Flow B weekly gap trigger (US-082).

        When gap_trigger_enabled and inside the operator-local weekly window,
        detects next-week gaps and on gaps runs discovery + draft generation
        into blog-posts/pending-approval/ (capped by max_drafts_per_weekly_run).
        Never writes ready/, never publishes blog/LinkedIn, never approves/promotes.
        """
        validated_now = (
            validate_canonical_utc_timestamp(body.now_utc)
            if body.now_utc is not None
            else None
        )
        result = run_flow_b_gap_trigger(
            settings.base_path,
            now_utc=validated_now,
            dry_run=body.dry_run,
            force_window=body.force_window,
            environ=os.environ,
        )
        payload = result.to_dict()
        logger.info(
            "flow-b/gap-trigger status=%s iso_week=%s drafts=%s "
            "idempotency_key=%s dry_run=%s force_window=%s",
            result.status,
            result.target_week,
            len(result.drafts),
            result.idempotency_key,
            result.dry_run,
            result.force_window,
        )
        return payload

    @app.get("/flow-b/calendar-gaps")
    def get_flow_b_calendar_gaps(
        now_utc: str | None = Query(default=None),
        _auth: None = Depends(require_api_key),
    ) -> dict:
        """Authenticated detect-only next-week LinkedIn calendar gaps (US-077).

        Read-only: does not mutate campaigns, calendar, or drafts, and does not
        start discovery/draft/trigger. Detect may run when gap_trigger_enabled
        is false (flag echoed; auto-trigger remains US-082).
        """
        try:
            validated_now = (
                validate_canonical_utc_timestamp(now_utc)
                if now_utc is not None
                else None
            )
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail="now_utc must be a canonical UTC timestamp",
            ) from None
        try:
            result = detect_next_week_calendar_gaps(
                settings.base_path,
                now_utc=validated_now,
                environ=os.environ,
            )
        except RuntimeError as exc:
            code = str(exc)
            if code in {
                ERROR_SETTINGS_STORE_NOT_CONFIGURED,
                "gap_operator_settings_store_not_configured",
            }:
                raise HTTPException(
                    status_code=503,
                    detail={
                        "errors": [
                            {
                                "field": "_store",
                                "code": ERROR_SETTINGS_STORE_NOT_CONFIGURED,
                                "message": "settings store is not configured",
                            }
                        ]
                    },
                ) from exc
            raise HTTPException(
                status_code=503,
                detail={
                    "errors": [
                        {
                            "field": "_store",
                            "code": ERROR_SETTINGS_STORE_UNAVAILABLE,
                            "message": "settings store is unavailable",
                        }
                    ]
                },
            ) from exc
        logger.info(
            "flow-b/calendar-gaps status=%s iso_week=%s gaps=%s "
            "settings_source=%s gap_trigger_enabled=%s read_only=%s",
            result.status,
            (result.target_week or {}).get("iso_week"),
            len(result.gaps),
            result.settings_source,
            result.gap_trigger_enabled,
            result.read_only,
        )
        return result.to_dict()

    @app.get("/flow-b/gap-operator-settings")
    def get_flow_b_gap_operator_settings(
        _auth: None = Depends(require_api_key),
    ) -> dict:
        """Authenticated read of Flow B gap operator settings (US-076)."""
        try:
            snapshot = load_gap_operator_settings(environ=os.environ)
        except RuntimeError as exc:
            code = str(exc)
            if code in {
                ERROR_SETTINGS_STORE_NOT_CONFIGURED,
                "gap_operator_settings_store_not_configured",
            }:
                raise HTTPException(
                    status_code=503,
                    detail={
                        "errors": [
                            {
                                "field": "_store",
                                "code": ERROR_SETTINGS_STORE_NOT_CONFIGURED,
                                "message": "settings store is not configured",
                            }
                        ]
                    },
                ) from exc
            raise HTTPException(
                status_code=503,
                detail={
                    "errors": [
                        {
                            "field": "_store",
                            "code": ERROR_SETTINGS_STORE_UNAVAILABLE,
                            "message": "settings store is unavailable",
                        }
                    ]
                },
            ) from exc
        logger.info(
            "flow-b/gap-operator-settings GET source=%s gap_trigger_enabled=%s",
            snapshot.source,
            snapshot.settings.get("gap_trigger_enabled"),
        )
        return snapshot.to_response_dict()

    @app.put("/flow-b/gap-operator-settings")
    def put_flow_b_gap_operator_settings(
        body: GapOperatorSettingsPutRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        """Authenticated full-document update of Flow B gap operator settings (US-076).

        Does not mutate SILVERMAN_LINKEDIN_PUBLICATION_ENABLED or publish to LinkedIn.
        """
        document = {
            "operator_timezone": body.operator_timezone,
            "gap_trigger_enabled": body.gap_trigger_enabled,
            "gap_scan_mode": body.gap_scan_mode,
            "weekly_run_local_day": body.weekly_run_local_day,
            "weekly_run_local_time": body.weekly_run_local_time,
            "min_lead_days": body.min_lead_days,
            "gap_posts_threshold": body.gap_posts_threshold,
            "max_drafts_per_weekly_run": body.max_drafts_per_weekly_run,
            "density_max_per_local_day": body.density_max_per_local_day,
        }
        try:
            snapshot, errors = save_gap_operator_settings(
                document,
                expected_row_version=body.expected_row_version,
            )
        except RuntimeError as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "errors": [
                        {
                            "field": "_store",
                            "code": ERROR_SETTINGS_STORE_UNAVAILABLE,
                            "message": "settings store is unavailable",
                        }
                    ]
                },
            ) from exc
        if errors:
            raise HTTPException(status_code=422, detail={"errors": errors})
        assert snapshot is not None
        logger.info(
            "flow-b/gap-operator-settings PUT source=%s gap_trigger_enabled=%s",
            snapshot.source,
            snapshot.settings.get("gap_trigger_enabled"),
        )
        return snapshot.to_response_dict()

    @app.post("/flow-b/discover-topics")
    def post_flow_b_discover_topics(
        body: FlowBDiscoverTopicsRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        """Authenticated Flow B AI topic discovery (US-078).

        Discovery-only: returns attachable topic payloads; does not write under
        blog-posts/ready/ or blog-posts/pending-approval/, and does not start
        draft/approve/trigger or enable LinkedIn API publication.
        """
        field_errors = validate_discovery_request_fields(
            count=body.count,
            target_week=body.target_week,
            empty_days=body.empty_days,
        )
        if field_errors:
            raise HTTPException(status_code=422, detail={"errors": field_errors})

        result = discover_flow_b_topics(
            settings.base_path,
            count=body.count,
            target_week=body.target_week,
            empty_days=body.empty_days,
            dry_run=body.dry_run,
            environ=os.environ,
        )
        payload = result.to_dict()
        logger.info(
            "flow-b/discover-topics status=%s provider=%s topics=%s "
            "max_drafts=%s settings_source=%s dry_run=%s error_code=%s",
            result.status,
            result.provider,
            len(result.topics),
            result.max_drafts_per_weekly_run,
            result.settings_source,
            result.dry_run,
            result.error_code,
        )
        if result.status == STATUS_TOPICS_DISCOVERED:
            return payload
        if result.status == "discovery_dry_run":
            return payload

        # Fail closed — never invent filler topics.
        assert result.status == STATUS_DISCOVERY_FAILED
        code = result.error_code or ERROR_DISCOVERY_FAILED
        if code == ERROR_SETTINGS_UNAVAILABLE:
            status_code = 503
        elif code in {
            ERROR_CONFIG_INVALID,
            "deepseek_api_key_missing",
            ERROR_CANON_MISSING,
            ERROR_CANON_SECTION_MISSING,
            ERROR_NOT_OBJECTIVE_ALIGNED,
            "discovery_provider_unsupported",
        }:
            status_code = 422
        elif code.startswith("deepseek_"):
            status_code = 502
        else:
            status_code = 502
        raise HTTPException(status_code=status_code, detail=payload)

    @app.post("/flow-b/generate-blog-drafts")
    def post_flow_b_generate_blog_drafts(
        body: FlowBGenerateBlogDraftsRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        """Authenticated Flow B blog draft + hero image generation (US-079).

        Writes Markdown + PNG pairs under blog-posts/pending-approval/ only.
        Does not write blog-posts/ready/, invoke Flow A publish/package/schedule,
        or enable LinkedIn API publication. Approve/promote (US-080/081) and gap
        trigger (US-082) are out of scope.
        """
        field_errors = validate_draft_request_fields(
            topics=body.topics,
            target_week=body.target_week,
            empty_days=body.empty_days,
        )
        if field_errors:
            raise HTTPException(status_code=422, detail={"errors": field_errors})

        result = generate_flow_b_blog_drafts(
            settings.base_path,
            topics=body.topics,
            target_week=body.target_week,
            empty_days=body.empty_days,
            dry_run=body.dry_run,
            environ=os.environ,
        )
        payload = result.to_dict()
        logger.info(
            "flow-b/generate-blog-drafts status=%s provider=%s drafts=%s "
            "max_drafts=%s settings_source=%s dry_run=%s error_code=%s",
            result.status,
            result.provider,
            len(result.drafts),
            result.max_drafts_per_weekly_run,
            result.settings_source,
            result.dry_run,
            result.error_code,
        )
        if result.status in {
            STATUS_DRAFTS_GENERATED,
            STATUS_DRAFTS_PARTIAL,
            "draft_generation_dry_run",
        }:
            return payload

        assert result.status == "draft_generation_failed"
        code = result.error_code or "draft_generation_failed"
        if code == DRAFT_ERROR_SETTINGS_UNAVAILABLE:
            status_code = 503
        elif code in {
            DRAFT_ERROR_CONFIG_INVALID,
            "deepseek_api_key_missing",
            DRAFT_ERROR_CANON_MISSING,
            DRAFT_ERROR_CANON_SECTION_MISSING,
            DRAFT_ERROR_TOPICS_EMPTY,
            DRAFT_ERROR_TOPICS_DUPLICATE,
            DRAFT_ERROR_TOPIC_INVALID,
            DRAFT_ERROR_ANTI_AI_BLOCKED,
            "draft_provider_unsupported",
            "draft_target_week_invalid",
            "draft_empty_days_invalid",
            "pending_approval_dir_not_ready",
            "pending_approval_dir_not_writable",
        }:
            status_code = 422
        elif code.startswith("deepseek_"):
            status_code = 502
        else:
            status_code = 502
        raise HTTPException(status_code=status_code, detail=payload)

    def _flow_b_draft_decision_http_error(result: DraftDecisionResult) -> None:
        """Raise HTTPException for failed approve/reject/detail lookups."""
        payload = result.to_dict()
        code = result.error_code or "draft_decision_failed"
        if code in {
            ERROR_DRAFT_ID_INVALID,
            ERROR_PATH_TRAVERSAL,
            ERROR_DRAFT_ALREADY_REJECTED,
            ERROR_DRAFT_NOT_APPROVABLE,
            ERROR_DRAFT_NOT_REJECTABLE,
            ERROR_SIDECAR_INVALID,
        }:
            status_code = 422
        elif code in {ERROR_DRAFT_NOT_FOUND, ERROR_IMAGE_NOT_FOUND}:
            status_code = 404
        elif code == ERROR_SIDECAR_WRITE_FAILED:
            status_code = 502
        else:
            status_code = 502
        raise HTTPException(status_code=status_code, detail=payload)

    def _flow_b_draft_promote_http_error(result: DraftPromoteResult) -> None:
        """Raise HTTPException for failed promote attempts."""
        payload = result.to_dict()
        code = result.error_code or "draft_promote_failed"
        if code in {
            ERROR_DRAFT_ID_INVALID,
            ERROR_PATH_TRAVERSAL,
            ERROR_SIDECAR_INVALID,
            ERROR_DRAFT_NOT_APPROVED,
            ERROR_DRAFT_REJECTED,
            ERROR_DRAFT_PAIR_INCOMPLETE,
            ERROR_READY_COLLISION,
            ERROR_APPROVAL_METADATA_MISSING,
        }:
            status_code = 422
        elif code == ERROR_DRAFT_NOT_FOUND:
            status_code = 404
        elif code in {
            ERROR_PROMOTE_MOVE_FAILED,
            ERROR_PROMOTE_SIDECAR_WRITE_FAILED,
        }:
            status_code = 502
        else:
            status_code = 502
        raise HTTPException(status_code=status_code, detail=payload)

    @app.get("/flow-b/pending-approval-drafts")
    def get_flow_b_pending_approval_drafts(
        status: str | None = Query(
            default=None,
            description=(
                "Optional status filter. Default lists actionable pending "
                "and approved-not-promoted drafts."
            ),
        ),
        _auth: None = Depends(require_api_key),
    ) -> dict:
        """Authenticated list of Flow B pending-approval drafts (US-080)."""
        result = list_pending_approval_drafts(
            settings.base_path,
            status_filter=status.strip() if status else None,
        )
        logger.info(
            "flow-b/pending-approval-drafts list count=%s filter=%s",
            len(result.drafts),
            result.filter_status,
        )
        return result.to_dict()

    @app.get("/flow-b/pending-approval-drafts/{draft_id}")
    def get_flow_b_pending_approval_draft(
        draft_id: str,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        """Authenticated detail for one pending-approval draft (US-080)."""
        result = get_pending_approval_draft(settings.base_path, draft_id)
        if isinstance(result, DraftDecisionResult):
            _flow_b_draft_decision_http_error(result)
        assert isinstance(result, PendingDraftDetail)
        return result.to_dict()

    @app.get("/flow-b/pending-approval-drafts/{draft_id}/image")
    def get_flow_b_pending_approval_draft_image(
        draft_id: str,
        _auth: None = Depends(require_api_key),
    ) -> FileResponse:
        """Authenticated hero PNG confined to pending-approval/ (US-080)."""
        path, error_code = resolve_pending_approval_image_path(
            settings.base_path, draft_id
        )
        if path is None:
            fake = DraftDecisionResult(
                status="failed",
                draft_id=draft_id,
                promotion_pending=False,
                error_code=error_code or ERROR_IMAGE_NOT_FOUND,
                error=error_code or ERROR_IMAGE_NOT_FOUND,
            )
            _flow_b_draft_decision_http_error(fake)
        assert path is not None
        return FileResponse(
            path=path,
            media_type="image/png",
            filename=path.name,
        )

    @app.post("/flow-b/pending-approval-drafts/{draft_id}/approve")
    def post_flow_b_pending_approval_draft_approve(
        draft_id: str,
        body: FlowBApproveDraftRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        """Record approve decision only — does not promote to ready/ (US-080)."""
        result = approve_pending_approval_draft(
            settings.base_path,
            draft_id,
            approved_by=body.approved_by,
            dry_run=body.dry_run,
        )
        logger.info(
            "flow-b/pending-approval-drafts approve draft_id=%s status=%s "
            "dry_run=%s promoted=%s error_code=%s",
            result.draft_id,
            result.status,
            result.dry_run,
            result.promoted,
            result.error_code,
        )
        if result.status == STATUS_APPROVED:
            return result.to_dict()
        _flow_b_draft_decision_http_error(result)
        return result.to_dict()  # pragma: no cover

    @app.post("/flow-b/pending-approval-drafts/{draft_id}/reject")
    def post_flow_b_pending_approval_draft_reject(
        draft_id: str,
        body: FlowBRejectDraftRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        """Record reject; remains non-publishable — no ready/ writes (US-080)."""
        result = reject_pending_approval_draft(
            settings.base_path,
            draft_id,
            rejection_reason=body.rejection_reason,
            dry_run=body.dry_run,
        )
        logger.info(
            "flow-b/pending-approval-drafts reject draft_id=%s status=%s "
            "dry_run=%s error_code=%s",
            result.draft_id,
            result.status,
            result.dry_run,
            result.error_code,
        )
        if result.status == STATUS_REJECTED:
            return result.to_dict()
        _flow_b_draft_decision_http_error(result)
        return result.to_dict()  # pragma: no cover

    @app.post("/flow-b/pending-approval-drafts/{draft_id}/promote")
    def post_flow_b_pending_approval_draft_promote(
        draft_id: str,
        body: FlowBPromoteDraftRequest,
        _auth: None = Depends(require_api_key),
    ) -> dict:
        """Promote approved draft to blog-posts/ready/ (US-081). Does not publish."""
        result = promote_pending_approval_draft(
            settings.base_path,
            draft_id,
            promoted_by=body.promoted_by,
            dry_run=body.dry_run,
        )
        logger.info(
            "flow-b/pending-approval-drafts promote draft_id=%s status=%s "
            "dry_run=%s promoted=%s already_promoted=%s error_code=%s",
            result.draft_id,
            result.status,
            result.dry_run,
            result.promoted,
            result.already_promoted,
            result.error_code,
        )
        if result.status == STATUS_PROMOTED:
            return result.to_dict()
        _flow_b_draft_promote_http_error(result)
        return result.to_dict()  # pragma: no cover

    return app


def main() -> None:
    """Run the worker with uvicorn."""
    import uvicorn

    settings = load_settings()
    uvicorn.run(
        "silverman_blog_linkedin.main:create_app",
        host="0.0.0.0",
        port=settings.port,
        factory=True,
    )


if __name__ == "__main__":
    main()
