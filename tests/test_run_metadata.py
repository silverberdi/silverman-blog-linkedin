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
