"""Tests for POST /process-ready."""

import json

from fastapi.testclient import TestClient

from silverman_blog_linkedin.main import create_app
from silverman_blog_linkedin.run_metadata import metadata_relative_path
from tests.conftest import auth_header, create_full_layout, make_settings


def test_successful_scan_with_mixed_results(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    ready = base / "blog-posts" / "ready"
    (ready / "good.md").write_text("# Good\n", encoding="utf-8")
    (ready / "empty.md").write_bytes(b"")
    (ready / "notes.txt").write_text("ignore me", encoding="utf-8")

    client = TestClient(create_app(make_settings(base)))
    response = client.post("/process-ready", headers=auth_header())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["folders_ready"] is True
    assert body["metadata_written"] is True
    assert body["metadata_path"] == metadata_relative_path(body["run_id"])
    assert body["candidate_count"] == 2
    assert body["valid_count"] == 1
    assert body["invalid_count"] == 1
    assert body["ignored_count"] == 1
    assert body["errors"] == []

    metadata_file = base / body["metadata_path"]
    assert metadata_file.is_file()


def test_empty_ready_folder(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)

    client = TestClient(create_app(make_settings(base)))
    response = client.post("/process-ready", headers=auth_header())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["candidate_count"] == 0
    assert body["metadata_written"] is True


def test_folders_not_ready_with_metadata_written(tmp_path):
    base = tmp_path / "editorial"
    base.mkdir()
    (base / "metadata" / "runs").mkdir(parents=True)

    client = TestClient(create_app(make_settings(base)))
    response = client.post("/process-ready", headers=auth_header())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["folders_ready"] is False
    assert body["metadata_written"] is True
    assert body["metadata_path"] == metadata_relative_path(body["run_id"])
    assert body["candidate_count"] == 0
    assert "editorial_folders_not_ready" in body["errors"]
    assert (base / body["metadata_path"]).is_file()


def test_metadata_runs_missing(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    runs_dir = base / "metadata" / "runs"
    for child in runs_dir.iterdir():
        child.unlink()
    runs_dir.rmdir()

    client = TestClient(create_app(make_settings(base)))
    response = client.post("/process-ready", headers=auth_header())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["folders_ready"] is False
    assert body["metadata_written"] is False
    assert body["metadata_path"] is None
    assert body["errors"] == ["metadata_runs_not_ready"]


def test_metadata_runs_not_writable(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    runs_dir = base / "metadata" / "runs"
    runs_dir.chmod(0o555)

    try:
        client = TestClient(create_app(make_settings(base)))
        response = client.post("/process-ready", headers=auth_header())

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "failed"
        assert body["metadata_written"] is False
        assert body["metadata_path"] is None
        assert body["errors"] == ["metadata_runs_not_writable"]
    finally:
        runs_dir.chmod(0o755)


def test_process_ready_does_not_expose_secrets(tmp_path):
    secret = "super-secret-api-key-value"
    base = tmp_path / "editorial"
    create_full_layout(base)

    client = TestClient(create_app(make_settings(base, api_key=secret)))
    response = client.post("/process-ready", headers=auth_header(secret))
    raw = response.text

    assert response.status_code == 200
    assert secret not in raw
    assert secret not in json.dumps(response.json())


def test_process_ready_is_read_only_for_source_files(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    ready = base / "blog-posts" / "ready"
    post = ready / "post.md"
    post.write_text("# Original\n", encoding="utf-8")
    mtime_before = post.stat().st_mtime
    content_before = post.read_text(encoding="utf-8")

    client = TestClient(create_app(make_settings(base)))
    client.post("/process-ready", headers=auth_header())

    assert post.read_text(encoding="utf-8") == content_before
    assert post.stat().st_mtime == mtime_before


def test_health_remains_unauthenticated(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    client = TestClient(create_app(make_settings(base)))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_requires_authentication(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    client = TestClient(create_app(make_settings(base)))

    response = client.post("/process-ready")

    assert response.status_code == 401
