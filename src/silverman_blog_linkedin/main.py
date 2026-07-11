"""FastAPI application and HTTP routes."""

from __future__ import annotations

import hashlib
import html
import logging
import os
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from silverman_blog_linkedin import SERVICE_NAME, __version__
from silverman_blog_linkedin.auth import require_api_key
from silverman_blog_linkedin.blog_publish_flow import publish_blog_post
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
from silverman_blog_linkedin.linkedin_package_flow import generate_linkedin_package
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


class CancelLinkedInPublicationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: str
    variant: str
    dry_run: bool = True

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
        validation = validate_folders(settings.base_path)
        status = "healthy" if validation.folders_ready else "degraded"
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
            environ=os.environ,
        )
        logger.info(
            "publish-linkedin-due-variants status=%s dry_run=%s publish_now=%s results=%s",
            result.status,
            result.dry_run,
            result.publish_now,
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
        )
        logger.info(
            "cancel-linkedin-publication status=%s campaign_id=%s variant=%s dry_run=%s",
            result.status,
            result.campaign_id,
            result.variant,
            result.dry_run,
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
