"""FastAPI application and HTTP routes."""

from __future__ import annotations

import hashlib
import logging
import os

from fastapi import Depends, FastAPI
from pydantic import BaseModel, ConfigDict, field_validator

from silverman_blog_linkedin import SERVICE_NAME, __version__
from silverman_blog_linkedin.auth import require_api_key
from silverman_blog_linkedin.config import Settings, load_settings
from silverman_blog_linkedin.deepseek_client import generate_linkedin_draft_content
from silverman_blog_linkedin.deepseek_config import load_deepseek_settings
from silverman_blog_linkedin.draft_writer import (
    check_review_dir_ready,
    validate_source_path_shape,
    write_draft_file,
)
from silverman_blog_linkedin.file_reader import (
    derive_filename,
    normalize_relative_path,
    read_blog_post_file,
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
                title=body.title,
                slug_hint=body.slug_hint,
                tone=body.tone,
                audience=body.audience,
                variant=body.variant,
                errors=errors,
                started_at=started_at,
                completed_at=completed_at,
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
                title=body.title,
                slug_hint=body.slug_hint,
                tone=body.tone,
                audience=body.audience,
                variant=body.variant,
                errors=errors,
                started_at=started_at,
                completed_at=completed_at,
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
                title=body.title,
                slug_hint=body.slug_hint,
                tone=body.tone,
                audience=body.audience,
                variant=body.variant,
                errors=errors,
                started_at=started_at,
                completed_at=completed_at,
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
                title=body.title,
                slug_hint=body.slug_hint,
                tone=body.tone,
                audience=body.audience,
                variant=body.variant,
                errors=path_errors,
                started_at=started_at,
                completed_at=completed_at,
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
            )

        messages = build_chat_messages(
            markdown_content=body.markdown_content,
            title=body.title,
            tone=body.tone,
            audience=body.audience,
            variant=body.variant,
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
                title=body.title,
                slug_hint=body.slug_hint,
                tone=body.tone,
                audience=body.audience,
                variant=body.variant,
                errors=errors,
                started_at=started_at,
                completed_at=completed_at,
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
                title=body.title,
                slug_hint=body.slug_hint,
                tone=body.tone,
                audience=body.audience,
                variant=body.variant,
                errors=errors,
                started_at=started_at,
                completed_at=completed_at,
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
            title=body.title,
            slug_hint=body.slug_hint,
            tone=body.tone,
            audience=body.audience,
            variant=body.variant,
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
        )

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
