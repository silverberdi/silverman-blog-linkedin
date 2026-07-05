"""Tests for run metadata generation and persistence."""

import json
from pathlib import Path

from silverman_blog_linkedin.run_metadata import (
    METADATA_RUNS_RELATIVE,
    build_run_metadata_payload,
    check_metadata_runs_ready,
    generate_run_id,
    metadata_relative_path,
    write_run_metadata,
)


def test_generate_run_id_format():
    run_id = generate_run_id()

    assert run_id.startswith("run-")
    assert run_id.endswith("Z-" + run_id.split("-")[-1])
    parts = run_id.split("-")
    assert len(parts) >= 3
    assert len(parts[-1]) == 4


def test_metadata_relative_path():
    run_id = "run-20260704T223045Z-a1b2"
    assert metadata_relative_path(run_id) == f"{METADATA_RUNS_RELATIVE}/{run_id}.json"


def test_check_metadata_runs_ready_when_writable(tmp_path):
    metadata_dir = tmp_path / METADATA_RUNS_RELATIVE
    metadata_dir.mkdir(parents=True)

    readiness = check_metadata_runs_ready(tmp_path)

    assert readiness.ready is True
    assert readiness.error_code is None


def test_check_metadata_runs_missing(tmp_path):
    readiness = check_metadata_runs_ready(tmp_path)

    assert readiness.ready is False
    assert readiness.error_code == "metadata_runs_not_ready"


def test_check_metadata_runs_not_writable(tmp_path):
    metadata_dir = tmp_path / METADATA_RUNS_RELATIVE
    metadata_dir.mkdir(parents=True)
    metadata_dir.chmod(0o555)

    try:
        readiness = check_metadata_runs_ready(tmp_path)
        assert readiness.ready is False
        assert readiness.error_code == "metadata_runs_not_writable"
    finally:
        metadata_dir.chmod(0o755)


def test_write_run_metadata_creates_file(tmp_path):
    metadata_dir = tmp_path / METADATA_RUNS_RELATIVE
    metadata_dir.mkdir(parents=True)
    run_id = "run-20260704T223045Z-test"
    payload = build_run_metadata_payload(
        run_id=run_id,
        status="completed",
        base_path=tmp_path,
        folders_ready=True,
        scan_valid_files=[],
        scan_invalid_files=[],
        scan_ignored_files=[],
        candidate_count=0,
        valid_count=0,
        invalid_count=0,
        ignored_count=0,
        errors=[],
        started_at="2026-07-04T22:30:45Z",
        completed_at="2026-07-04T22:30:45Z",
    )

    written = write_run_metadata(tmp_path, run_id, payload)

    assert written is True
    metadata_file = tmp_path / metadata_relative_path(run_id)
    assert metadata_file.is_file()
    data = json.loads(metadata_file.read_text(encoding="utf-8"))
    assert data["run_id"] == run_id
    assert data["trigger"] == "POST /process-ready"
    assert "api_key" not in data


def test_write_run_metadata_skipped_when_missing(tmp_path):
    run_id = "run-20260704T223045Z-test"
    payload = {"run_id": run_id}

    written = write_run_metadata(tmp_path, run_id, payload)

    assert written is False


def test_build_process_file_metadata_payload_success():
    from silverman_blog_linkedin.run_metadata import (
        TRIGGER_PROCESS_FILE,
        build_process_file_metadata_payload,
    )

    payload = build_process_file_metadata_payload(
        run_id="run-20260704T223045Z-a1b2",
        status="completed",
        base_path=Path("/data/silverman-blog-linkedin"),
        folders_ready=True,
        relative_path="blog-posts/ready/my-post.md",
        filename="my-post.md",
        size_bytes=42,
        content_sha256="abc123",
        errors=[],
        started_at="2026-07-04T22:30:45Z",
        completed_at="2026-07-04T22:30:45Z",
    )

    assert payload["trigger"] == TRIGGER_PROCESS_FILE
    assert payload["relative_path"] == "blog-posts/ready/my-post.md"
    assert payload["filename"] == "my-post.md"
    assert payload["size_bytes"] == 42
    assert payload["content_sha256"] == "abc123"
    assert "markdown_content" not in payload
    assert "api_key" not in payload


def test_build_process_file_metadata_payload_failure_nulls():
    from silverman_blog_linkedin.run_metadata import build_process_file_metadata_payload

    payload = build_process_file_metadata_payload(
        run_id="run-20260704T223045Z-a1b2",
        status="failed",
        base_path=Path("/data/silverman-blog-linkedin"),
        folders_ready=False,
        relative_path="blog-posts/ready/my-post.md",
        filename="my-post.md",
        size_bytes=None,
        content_sha256=None,
        errors=["editorial_folders_not_ready"],
        started_at="2026-07-04T22:30:45Z",
        completed_at="2026-07-04T22:30:45Z",
    )

    assert payload["size_bytes"] is None
    assert payload["content_sha256"] is None
    assert "markdown_content" not in payload


def test_build_process_file_response_shape():
    from silverman_blog_linkedin.run_metadata import build_process_file_response

    response = build_process_file_response(
        run_id="run-20260704T223045Z-a1b2",
        status="failed",
        metadata_written=False,
        folders_ready=False,
        relative_path="blog-posts/ready/my-post.md",
        filename="my-post.md",
        size_bytes=None,
        content_sha256=None,
        markdown_content=None,
        errors=["metadata_runs_not_ready"],
    )

    assert response["relative_path"] == "blog-posts/ready/my-post.md"
    assert response["markdown_content"] is None
    assert response["metadata_path"] is None


def test_build_write_linkedin_draft_metadata_payload_success():
    from silverman_blog_linkedin.run_metadata import (
        TRIGGER_WRITE_LINKEDIN_DRAFT,
        build_write_linkedin_draft_metadata_payload,
    )

    payload = build_write_linkedin_draft_metadata_payload(
        run_id="run-20260704T223045Z-a1b2",
        status="completed",
        base_path=Path("/data/silverman-blog-linkedin"),
        source_relative_path="blog-posts/ready/my-post.md",
        draft_relative_path="linkedin-posts/review/20260704T223045Z-my-post.md",
        source_content_sha256="abc123",
        draft_content_sha256="def456",
        size_bytes=512,
        draft_written=True,
        title="Optional title",
        slug_hint="executive",
        errors=[],
        started_at="2026-07-04T22:30:45Z",
        completed_at="2026-07-04T22:30:45Z",
    )

    assert payload["trigger"] == TRIGGER_WRITE_LINKEDIN_DRAFT
    assert payload["draft_written"] is True
    assert payload["title"] == "Optional title"
    assert payload["slug_hint"] == "executive"
    assert "draft_content" not in payload
    assert "api_key" not in payload


def test_build_write_linkedin_draft_metadata_payload_failure():
    from silverman_blog_linkedin.run_metadata import (
        build_write_linkedin_draft_metadata_payload,
    )

    payload = build_write_linkedin_draft_metadata_payload(
        run_id="run-20260704T223045Z-a1b2",
        status="failed",
        base_path=Path("/data/silverman-blog-linkedin"),
        source_relative_path="blog-posts/processed/post.md",
        draft_relative_path=None,
        source_content_sha256=None,
        draft_content_sha256=None,
        size_bytes=None,
        draft_written=False,
        title=None,
        slug_hint=None,
        errors=["path_outside_ready"],
        started_at="2026-07-04T22:30:45Z",
        completed_at="2026-07-04T22:30:45Z",
    )

    assert payload["draft_relative_path"] is None
    assert payload["draft_content_sha256"] is None
    assert payload["size_bytes"] is None
    assert payload["draft_written"] is False
    assert "title" not in payload
    assert "slug_hint" not in payload
    assert "draft_content" not in payload


def test_build_write_linkedin_draft_response_partial_failure():
    from silverman_blog_linkedin.run_metadata import (
        build_write_linkedin_draft_response,
    )

    response = build_write_linkedin_draft_response(
        run_id="run-20260704T223045Z-a1b2",
        status="failed",
        metadata_written=False,
        source_relative_path="blog-posts/ready/my-post.md",
        source_content_sha256="abc123",
        draft_written=True,
        draft_relative_path="linkedin-posts/review/20260704T223045Z-my-post.md",
        draft_content_sha256="def456",
        size_bytes=512,
        errors=["metadata_write_failed"],
    )

    assert response["draft_written"] is True
    assert response["metadata_written"] is False
    assert response["metadata_path"] is None
    assert response["draft_relative_path"] is not None
    assert "draft_content" not in response
