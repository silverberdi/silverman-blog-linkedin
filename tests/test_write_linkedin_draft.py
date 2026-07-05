"""Tests for POST /write-linkedin-draft."""

import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from silverman_blog_linkedin.main import create_app
from silverman_blog_linkedin.run_metadata import metadata_relative_path
from tests.conftest import auth_header, create_full_layout, make_settings


def _valid_payload(**overrides):
    payload = {
        "source_relative_path": "blog-posts/ready/my-post.md",
        "draft_content": "LinkedIn draft text here.",
    }
    payload.update(overrides)
    return payload


def test_successful_write(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/write-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(
            source_content_sha256="abc123",
            title="Optional title",
            slug_hint="executive",
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["metadata_written"] is True
    assert body["metadata_path"] == metadata_relative_path(body["run_id"])
    assert body["draft_written"] is True
    assert body["draft_relative_path"].startswith("linkedin-posts/review/")
    assert body["draft_relative_path"].endswith("-my-post-executive.md")
    assert body["source_relative_path"] == "blog-posts/ready/my-post.md"
    assert body["source_content_sha256"] == "abc123"
    assert body["draft_content_sha256"] is not None
    assert body["size_bytes"] > 0
    assert body["errors"] == []

    draft_file = base / body["draft_relative_path"]
    assert draft_file.is_file()
    assert "LinkedIn draft text here." in draft_file.read_text(encoding="utf-8")

    metadata = json.loads(
        (base / body["metadata_path"]).read_text(encoding="utf-8")
    )
    assert metadata["trigger"] == "POST /write-linkedin-draft"
    assert metadata["draft_written"] is True
    assert metadata["title"] == "Optional title"
    assert metadata["slug_hint"] == "executive"
    assert "draft_content" not in metadata


def test_requires_authentication(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    client = TestClient(create_app(make_settings(base)))

    response = client.post("/write-linkedin-draft", json=_valid_payload())

    assert response.status_code == 401


def test_invalid_api_key(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    client = TestClient(create_app(make_settings(base)))

    response = client.post(
        "/write-linkedin-draft",
        headers={"Authorization": "Bearer wrong-key"},
        json=_valid_payload(),
    )

    assert response.status_code == 401
    assert "test-secret-key" not in response.text


def test_missing_required_fields_return_422(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    client = TestClient(create_app(make_settings(base)))

    missing_source = client.post(
        "/write-linkedin-draft",
        headers=auth_header(),
        json={"draft_content": "text"},
    )
    missing_draft = client.post(
        "/write-linkedin-draft",
        headers=auth_header(),
        json={"source_relative_path": "blog-posts/ready/post.md"},
    )

    assert missing_source.status_code == 422
    assert "run_id" not in missing_source.json()
    assert missing_draft.status_code == 422
    assert "run_id" not in missing_draft.json()


def test_empty_draft_content_returns_422(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    client = TestClient(create_app(make_settings(base)))

    response = client.post(
        "/write-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(draft_content="   "),
    )

    assert response.status_code == 422
    assert "run_id" not in response.json()


def test_empty_source_path_returns_422(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    client = TestClient(create_app(make_settings(base)))

    response = client.post(
        "/write-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(source_relative_path=""),
    )

    assert response.status_code == 422
    assert "run_id" not in response.json()


def test_extra_fields_return_422(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    client = TestClient(create_app(make_settings(base)))

    for extra_field in (
        "draft_relative_path",
        "output_path",
        "filename",
        "target_path",
        "unexpected_field",
    ):
        response = client.post(
            "/write-linkedin-draft",
            headers=auth_header(),
            json=_valid_payload(**{extra_field: "evil"}),
        )
        assert response.status_code == 422
        assert "run_id" not in response.json()


def test_metadata_runs_missing_no_writes(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    runs_dir = base / "metadata" / "runs"
    for child in runs_dir.iterdir():
        child.unlink()
    runs_dir.rmdir()

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/write-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["metadata_written"] is False
    assert body["metadata_path"] is None
    assert body["draft_written"] is False
    assert body["draft_relative_path"] is None
    assert "metadata_runs_not_ready" in body["errors"]
    assert list((base / "linkedin-posts" / "review").glob("*.md")) == []


def test_review_dir_missing_with_metadata(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    review_dir = base / "linkedin-posts" / "review"
    for child in review_dir.iterdir():
        child.unlink()
    review_dir.rmdir()

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/write-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["draft_written"] is False
    assert body["metadata_written"] is True
    assert "review_dir_not_ready" in body["errors"]


def test_review_dir_not_writable_with_metadata(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    review_dir = base / "linkedin-posts" / "review"
    review_dir.chmod(0o555)

    try:
        client = TestClient(create_app(make_settings(base)))
        response = client.post(
            "/write-linkedin-draft",
            headers=auth_header(),
            json=_valid_payload(),
        )
    finally:
        review_dir.chmod(0o755)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["draft_written"] is False
    assert body["metadata_written"] is True
    assert "review_dir_not_writable" in body["errors"]


def test_source_path_shape_failure(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    client = TestClient(create_app(make_settings(base)))

    response = client.post(
        "/write-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(source_relative_path="blog-posts/processed/post.md"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["draft_written"] is False
    assert body["metadata_written"] is True
    assert "path_outside_ready" in body["errors"]
    assert list((base / "linkedin-posts" / "review").glob("*.md")) == []


@patch("silverman_blog_linkedin.main.generate_run_id", return_value="run-20260705T150045Z-a1b2")
@patch("silverman_blog_linkedin.draft_writer._utc_timestamp", return_value="20260705T150045Z")
def test_draft_path_collision(_mock_ts, _mock_run_id, tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    review = base / "linkedin-posts" / "review"
    for name in (
        "20260705T150045Z-my-post.md",
        "20260705T150045Z-my-post-a1b2.md",
        "20260705T150045Z-my-post-run-20260705T150045Z-a1b2.md",
    ):
        (review / name).write_text("occupied\n", encoding="utf-8")

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/write-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["draft_written"] is False
    assert body["metadata_written"] is True
    assert body["errors"] == ["draft_path_collision"]


def test_metadata_write_failed_partial_failure(tmp_path, monkeypatch):
    base = tmp_path / "editorial"
    create_full_layout(base)

    def fail_metadata_write(*_args, **_kwargs):
        return False

    monkeypatch.setattr(
        "silverman_blog_linkedin.main.write_run_metadata",
        fail_metadata_write,
    )

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/write-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["draft_written"] is True
    assert body["draft_relative_path"] is not None
    assert body["draft_content_sha256"] is not None
    assert body["size_bytes"] is not None
    assert body["metadata_written"] is False
    assert body["metadata_path"] is None
    assert body["errors"] == ["metadata_write_failed"]

    draft_file = base / body["draft_relative_path"]
    assert draft_file.is_file()


def test_source_blog_file_not_modified(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    source = base / "blog-posts" / "ready" / "my-post.md"
    original = "# Original\n\nUnchanged.\n"
    source.write_text(original, encoding="utf-8")

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/write-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(),
    )

    assert response.status_code == 200
    assert source.read_text(encoding="utf-8") == original
