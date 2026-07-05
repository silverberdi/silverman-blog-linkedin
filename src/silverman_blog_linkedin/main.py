"""FastAPI application and HTTP routes."""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI
from pydantic import BaseModel, field_validator

from silverman_blog_linkedin import SERVICE_NAME, __version__
from silverman_blog_linkedin.auth import require_api_key
from silverman_blog_linkedin.config import Settings, load_settings
from silverman_blog_linkedin.file_reader import (
    derive_filename,
    normalize_relative_path,
    read_blog_post_file,
)
from silverman_blog_linkedin.paths import validate_folders
from silverman_blog_linkedin.ready_scan import ScanResult, scan_ready_folder
from silverman_blog_linkedin.run_metadata import (
    build_process_file_metadata_payload,
    build_process_file_response,
    build_process_ready_response,
    build_run_metadata_payload,
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
