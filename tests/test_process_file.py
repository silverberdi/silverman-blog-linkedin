"""Tests for POST /process-file."""

import json

from fastapi.testclient import TestClient

from silverman_blog_linkedin.main import create_app
from silverman_blog_linkedin.run_metadata import metadata_relative_path
from tests.conftest import auth_header, create_full_layout, make_settings


def test_successful_read(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    content = "# Title\n\nBody text.\n"
    (base / "blog-posts" / "ready" / "my-post.md").write_text(
        content, encoding="utf-8"
    )

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/process-file",
        headers=auth_header(),
        json={"relative_path": "blog-posts/ready/my-post.md"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["folders_ready"] is True
    assert body["metadata_written"] is True
    assert body["metadata_path"] == metadata_relative_path(body["run_id"])
    assert body["relative_path"] == "blog-posts/ready/my-post.md"
    assert body["filename"] == "my-post.md"
    assert body["size_bytes"] == len(content.encode("utf-8"))
    assert body["content_sha256"] is not None
    assert body["markdown_content"] == content
    assert body["errors"] == []

    metadata_file = base / body["metadata_path"]
    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    assert metadata["trigger"] == "POST /process-file"
    assert "markdown_content" not in metadata
    assert metadata["content_sha256"] == body["content_sha256"]


def test_requires_authentication(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    client = TestClient(create_app(make_settings(base)))

    response = client.post(
        "/process-file",
        json={"relative_path": "blog-posts/ready/post.md"},
    )

    assert response.status_code == 401


def test_invalid_api_key(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    client = TestClient(create_app(make_settings(base)))

    response = client.post(
        "/process-file",
        headers={"Authorization": "Bearer wrong-key"},
        json={"relative_path": "blog-posts/ready/post.md"},
    )

    assert response.status_code == 401


def test_missing_relative_path_returns_422(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    client = TestClient(create_app(make_settings(base)))

    response = client.post("/process-file", headers=auth_header(), json={})

    assert response.status_code == 422
    body = response.json()
    assert "run_id" not in body


def test_empty_relative_path_returns_422(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    client = TestClient(create_app(make_settings(base)))

    response = client.post(
        "/process-file",
        headers=auth_header(),
        json={"relative_path": ""},
    )

    assert response.status_code == 422
    assert "run_id" not in response.json()


def test_folders_not_ready_with_metadata_written(tmp_path):
    base = tmp_path / "editorial"
    base.mkdir()
    (base / "metadata" / "runs").mkdir(parents=True)
    (base / "blog-posts" / "ready").mkdir(parents=True)
    (base / "blog-posts" / "ready" / "post.md").write_text(
        "# Post\n", encoding="utf-8"
    )

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/process-file",
        headers=auth_header(),
        json={"relative_path": "blog-posts/ready/post.md"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["folders_ready"] is False
    assert body["metadata_written"] is True
    assert body["relative_path"] == "blog-posts/ready/post.md"
    assert body["size_bytes"] is None
    assert body["content_sha256"] is None
    assert body["markdown_content"] is None
    assert "editorial_folders_not_ready" in body["errors"]

    metadata = json.loads(
        (base / body["metadata_path"]).read_text(encoding="utf-8")
    )
    assert metadata["size_bytes"] is None
    assert metadata["content_sha256"] is None
    assert "markdown_content" not in metadata


def test_metadata_runs_missing(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    runs_dir = base / "metadata" / "runs"
    for child in runs_dir.iterdir():
        child.unlink()
    runs_dir.rmdir()
    (base / "blog-posts" / "ready" / "post.md").write_text(
        "# Post\n", encoding="utf-8"
    )

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/process-file",
        headers=auth_header(),
        json={"relative_path": "blog-posts/ready/post.md"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["metadata_written"] is False
    assert body["metadata_path"] is None
    assert body["relative_path"] == "blog-posts/ready/post.md"
    assert body["size_bytes"] is None
    assert body["content_sha256"] is None
    assert body["markdown_content"] is None
    assert body["errors"] == ["metadata_runs_not_ready"]


def test_metadata_runs_not_writable(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    runs_dir = base / "metadata" / "runs"
    runs_dir.chmod(0o555)
    (base / "blog-posts" / "ready" / "post.md").write_text(
        "# Post\n", encoding="utf-8"
    )

    try:
        client = TestClient(create_app(make_settings(base)))
        response = client.post(
            "/process-file",
            headers=auth_header(),
            json={"relative_path": "blog-posts/ready/post.md"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["metadata_written"] is False
        assert body["metadata_path"] is None
        assert body["errors"] == ["metadata_runs_not_writable"]
    finally:
        runs_dir.chmod(0o755)


def test_path_validation_failure(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/process-file",
        headers=auth_header(),
        json={"relative_path": "blog-posts/processed/post.md"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["relative_path"] == "blog-posts/processed/post.md"
    assert body["filename"] == "post.md"
    assert body["size_bytes"] is None
    assert body["content_sha256"] is None
    assert body["markdown_content"] is None
    assert body["errors"] == ["path_outside_ready"]
    assert body["metadata_written"] is True


def test_missing_file(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/process-file",
        headers=auth_header(),
        json={"relative_path": "blog-posts/ready/missing.md"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["errors"] == ["file_not_found"]
    assert body["markdown_content"] is None
    assert body["content_sha256"] is None


def test_empty_file(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    (base / "blog-posts" / "ready" / "empty.md").write_bytes(b"")

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/process-file",
        headers=auth_header(),
        json={"relative_path": "blog-posts/ready/empty.md"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["errors"] == ["file_empty"]
    assert body["content_sha256"] is None
    assert body["markdown_content"] is None


def test_invalid_utf8(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    (base / "blog-posts" / "ready" / "bad.md").write_bytes(b"\xff\xfe")

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/process-file",
        headers=auth_header(),
        json={"relative_path": "blog-posts/ready/bad.md"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["errors"] == ["not_utf8"]
    assert body["markdown_content"] is None
    assert body["content_sha256"] is not None


def test_process_file_does_not_expose_secrets(tmp_path):
    secret = "super-secret-api-key-value"
    base = tmp_path / "editorial"
    create_full_layout(base)
    (base / "blog-posts" / "ready" / "post.md").write_text(
        "# Post\n", encoding="utf-8"
    )

    client = TestClient(create_app(make_settings(base, api_key=secret)))
    response = client.post(
        "/process-file",
        headers=auth_header(secret),
        json={"relative_path": "blog-posts/ready/post.md"},
    )
    raw = response.text

    assert response.status_code == 200
    assert secret not in raw
    assert secret not in json.dumps(response.json())


def test_process_file_is_read_only_for_source_files(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    post = base / "blog-posts" / "ready" / "post.md"
    post.write_text("# Original\n", encoding="utf-8")
    mtime_before = post.stat().st_mtime
    content_before = post.read_text(encoding="utf-8")

    client = TestClient(create_app(make_settings(base)))
    client.post(
        "/process-file",
        headers=auth_header(),
        json={"relative_path": "blog-posts/ready/post.md"},
    )

    assert post.read_text(encoding="utf-8") == content_before
    assert post.stat().st_mtime == mtime_before
