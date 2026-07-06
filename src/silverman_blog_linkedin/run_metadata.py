"""Run identifier generation and metadata/runs persistence."""

from __future__ import annotations

import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.ready_scan import ScanResult

METADATA_RUNS_RELATIVE = "metadata/runs"
TRIGGER_PROCESS_READY = "POST /process-ready"
TRIGGER_PROCESS_FILE = "POST /process-file"
TRIGGER_WRITE_LINKEDIN_DRAFT = "POST /write-linkedin-draft"
TRIGGER_GENERATE_LINKEDIN_DRAFT = "POST /generate-linkedin-draft"
PROVIDER_DEEPSEEK = "deepseek"


@dataclass(frozen=True)
class MetadataRunsReadiness:
    ready: bool
    error_code: str | None = None


def generate_run_id() -> str:
    """Generate a traceable run id: run-YYYYMMDDTHHMMSSZ-abcd."""
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%dT%H%M%SZ")
    suffix = secrets.token_hex(2)
    return f"run-{timestamp}-{suffix}"


def metadata_relative_path(run_id: str) -> str:
    """Relative metadata file path from editorial base."""
    return f"{METADATA_RUNS_RELATIVE}/{run_id}.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def check_metadata_runs_ready(base_path: Path) -> MetadataRunsReadiness:
    """Check whether metadata/runs exists, is a directory, and is writable."""
    metadata_dir = base_path / METADATA_RUNS_RELATIVE
    if not metadata_dir.exists() or not metadata_dir.is_dir():
        return MetadataRunsReadiness(
            ready=False, error_code="metadata_runs_not_ready"
        )
    if not os.access(metadata_dir, os.W_OK):
        return MetadataRunsReadiness(
            ready=False, error_code="metadata_runs_not_writable"
        )
    return MetadataRunsReadiness(ready=True)


def write_run_metadata(base_path: Path, run_id: str, payload: dict[str, Any]) -> bool:
    """Write run metadata JSON when metadata/runs is writable."""
    readiness = check_metadata_runs_ready(base_path)
    if not readiness.ready:
        return False

    metadata_path = base_path / metadata_relative_path(run_id)
    try:
        metadata_path.write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
    except OSError:
        return False
    return True


def build_run_metadata_payload(
    *,
    run_id: str,
    status: str,
    base_path: Path,
    folders_ready: bool,
    scan_valid_files: list[dict],
    scan_invalid_files: list[dict],
    scan_ignored_files: list[dict],
    candidate_count: int,
    valid_count: int,
    invalid_count: int,
    ignored_count: int,
    errors: list[str],
    started_at: str,
    completed_at: str,
) -> dict[str, Any]:
    """Build run metadata document (must not include secrets)."""
    return {
        "run_id": run_id,
        "trigger": TRIGGER_PROCESS_READY,
        "started_at": started_at,
        "completed_at": completed_at,
        "status": status,
        "base_path": str(base_path),
        "folders_ready": folders_ready,
        "candidate_count": candidate_count,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "ignored_count": ignored_count,
        "valid_files": scan_valid_files,
        "invalid_files": scan_invalid_files,
        "ignored_files": scan_ignored_files,
        "errors": errors,
    }


def build_process_file_metadata_payload(
    *,
    run_id: str,
    status: str,
    base_path: Path,
    folders_ready: bool,
    relative_path: str,
    filename: str | None,
    size_bytes: int | None,
    content_sha256: str | None,
    errors: list[str],
    started_at: str,
    completed_at: str,
) -> dict[str, Any]:
    """Build run metadata for POST /process-file (no markdown_content or secrets)."""
    return {
        "run_id": run_id,
        "trigger": TRIGGER_PROCESS_FILE,
        "started_at": started_at,
        "completed_at": completed_at,
        "status": status,
        "base_path": str(base_path),
        "folders_ready": folders_ready,
        "relative_path": relative_path,
        "filename": filename,
        "size_bytes": size_bytes,
        "content_sha256": content_sha256,
        "errors": errors,
    }


def build_process_file_response(
    *,
    run_id: str,
    status: str,
    metadata_written: bool,
    folders_ready: bool,
    relative_path: str,
    filename: str | None,
    size_bytes: int | None,
    content_sha256: str | None,
    markdown_content: str | None,
    errors: list[str],
) -> dict[str, Any]:
    """Build POST /process-file HTTP response body."""
    metadata_path: str | None
    if metadata_written:
        metadata_path = metadata_relative_path(run_id)
    else:
        metadata_path = None

    return {
        "run_id": run_id,
        "status": status,
        "metadata_written": metadata_written,
        "metadata_path": metadata_path,
        "folders_ready": folders_ready,
        "relative_path": relative_path,
        "filename": filename,
        "size_bytes": size_bytes,
        "content_sha256": content_sha256,
        "markdown_content": markdown_content,
        "errors": errors,
    }


def build_write_linkedin_draft_metadata_payload(
    *,
    run_id: str,
    status: str,
    base_path: Path,
    source_relative_path: str,
    draft_relative_path: str | None,
    source_content_sha256: str | None,
    draft_content_sha256: str | None,
    size_bytes: int | None,
    draft_written: bool,
    title: str | None,
    slug_hint: str | None,
    errors: list[str],
    started_at: str,
    completed_at: str,
) -> dict[str, Any]:
    """Build run metadata for POST /write-linkedin-draft (no draft_content or secrets)."""
    payload: dict[str, Any] = {
        "run_id": run_id,
        "trigger": TRIGGER_WRITE_LINKEDIN_DRAFT,
        "started_at": started_at,
        "completed_at": completed_at,
        "status": status,
        "base_path": str(base_path),
        "source_relative_path": source_relative_path,
        "draft_relative_path": draft_relative_path,
        "source_content_sha256": source_content_sha256,
        "draft_content_sha256": draft_content_sha256,
        "size_bytes": size_bytes,
        "draft_written": draft_written,
        "errors": errors,
    }
    if title is not None:
        payload["title"] = title
    if slug_hint is not None:
        payload["slug_hint"] = slug_hint
    return payload


def build_write_linkedin_draft_response(
    *,
    run_id: str,
    status: str,
    metadata_written: bool,
    source_relative_path: str,
    source_content_sha256: str | None,
    draft_written: bool,
    draft_relative_path: str | None,
    draft_content_sha256: str | None,
    size_bytes: int | None,
    errors: list[str],
) -> dict[str, Any]:
    """Build POST /write-linkedin-draft HTTP response body."""
    metadata_path: str | None
    if metadata_written:
        metadata_path = metadata_relative_path(run_id)
    else:
        metadata_path = None

    return {
        "run_id": run_id,
        "status": status,
        "metadata_written": metadata_written,
        "metadata_path": metadata_path,
        "draft_written": draft_written,
        "draft_relative_path": draft_relative_path,
        "source_relative_path": source_relative_path,
        "source_content_sha256": source_content_sha256,
        "draft_content_sha256": draft_content_sha256,
        "size_bytes": size_bytes,
        "errors": errors,
    }


def build_generate_linkedin_draft_metadata_payload(
    *,
    run_id: str,
    status: str,
    base_path: Path,
    provider: str,
    model: str | None,
    source_relative_path: str,
    draft_relative_path: str | None,
    source_content_sha256: str,
    draft_content_sha256: str | None,
    size_bytes: int | None,
    draft_written: bool,
    title: str | None,
    slug_hint: str | None,
    tone: str | None,
    audience: str | None,
    variant: str | None,
    source_public_url: str | None = None,
    topic_theme: str | None = None,
    errors: list[str],
    started_at: str,
    completed_at: str,
) -> dict[str, Any]:
    """Build run metadata for POST /generate-linkedin-draft (no content bodies or secrets)."""
    payload: dict[str, Any] = {
        "run_id": run_id,
        "trigger": TRIGGER_GENERATE_LINKEDIN_DRAFT,
        "started_at": started_at,
        "completed_at": completed_at,
        "status": status,
        "base_path": str(base_path),
        "provider": provider,
        "model": model,
        "source_relative_path": source_relative_path,
        "draft_relative_path": draft_relative_path,
        "source_content_sha256": source_content_sha256,
        "draft_content_sha256": draft_content_sha256,
        "size_bytes": size_bytes,
        "draft_written": draft_written,
        "errors": errors,
    }
    if title is not None:
        payload["title"] = title
    if slug_hint is not None:
        payload["slug_hint"] = slug_hint
    if tone is not None:
        payload["tone"] = tone
    if audience is not None:
        payload["audience"] = audience
    if variant is not None:
        payload["variant"] = variant
    if source_public_url is not None:
        payload["source_public_url"] = source_public_url
    if topic_theme is not None:
        payload["topic_theme"] = topic_theme
    return payload


def build_generate_linkedin_draft_response(
    *,
    run_id: str,
    status: str,
    metadata_written: bool,
    source_relative_path: str,
    source_content_sha256: str,
    draft_written: bool,
    draft_relative_path: str | None,
    draft_content_sha256: str | None,
    size_bytes: int | None,
    provider: str,
    model: str | None,
    errors: list[str],
    generated_draft_content: str | None = None,
    source_public_url: str | None = None,
    topic_theme: str | None = None,
) -> dict[str, Any]:
    """Build POST /generate-linkedin-draft HTTP response body."""
    metadata_path: str | None
    if metadata_written:
        metadata_path = metadata_relative_path(run_id)
    else:
        metadata_path = None

    response: dict[str, Any] = {
        "run_id": run_id,
        "status": status,
        "metadata_written": metadata_written,
        "metadata_path": metadata_path,
        "draft_written": draft_written,
        "draft_relative_path": draft_relative_path,
        "source_relative_path": source_relative_path,
        "source_content_sha256": source_content_sha256,
        "draft_content_sha256": draft_content_sha256,
        "size_bytes": size_bytes,
        "provider": provider,
        "model": model,
        "errors": errors,
    }
    if status == "completed" and generated_draft_content is not None:
        response["generated_draft_content"] = generated_draft_content
    if source_public_url is not None:
        response["source_public_url"] = source_public_url
    if topic_theme is not None:
        response["topic_theme"] = topic_theme
    return response


def build_process_ready_response(
    *,
    run_id: str,
    status: str,
    metadata_written: bool,
    folders_ready: bool,
    scan: ScanResult,
    errors: list[str],
) -> dict[str, Any]:
    """Build POST /process-ready HTTP response body."""
    metadata_path: str | None
    if metadata_written:
        metadata_path = metadata_relative_path(run_id)
    else:
        metadata_path = None

    return {
        "run_id": run_id,
        "status": status,
        "metadata_written": metadata_written,
        "metadata_path": metadata_path,
        "folders_ready": folders_ready,
        "candidate_count": scan.candidate_count,
        "valid_count": scan.valid_count,
        "invalid_count": scan.invalid_count,
        "ignored_count": scan.ignored_count,
        "valid_files": scan.valid_files,
        "invalid_files": scan.invalid_files,
        "ignored_files": scan.ignored_files,
        "errors": errors,
    }
