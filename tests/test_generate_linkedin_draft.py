"""Tests for POST /generate-linkedin-draft."""

import hashlib
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.deepseek_client import DeepSeekGenerationResult
from silverman_blog_linkedin.main import create_app
from silverman_blog_linkedin.run_metadata import metadata_relative_path
from tests.conftest import auth_header, create_full_layout, make_settings

MARKDOWN = "# Architecture\n\nA senior perspective on systems design.\n"
SOURCE_PATH = "blog-posts/ready/my-post.md"
PUBLIC_URL = "https://silverman.pro/2026/07/06/why-i-did-not-start-with-the-database/"
DEEPSEEK_KEY = "sk-test-deepseek-key"


def _valid_payload(**overrides):
    payload = {
        "source_relative_path": SOURCE_PATH,
        "markdown_content": MARKDOWN,
    }
    payload.update(overrides)
    return payload


def _mock_deepseek_success(text: str = "Generated LinkedIn draft for review."):
    return DeepSeekGenerationResult(content=text, error_code=None)


@pytest.fixture(autouse=True)
def _deepseek_env(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", DEEPSEEK_KEY)
    monkeypatch.setenv("DEEPSEEK_TIMEOUT_SECONDS", "60")
    monkeypatch.setenv("DEEPSEEK_MAX_OUTPUT_TOKENS", "1024")


def test_successful_generation(tmp_path, monkeypatch):
    base = tmp_path / "editorial"
    create_full_layout(base)
    monkeypatch.setattr(
        "silverman_blog_linkedin.main.generate_linkedin_draft_content",
        lambda *_args, **_kwargs: _mock_deepseek_success(),
    )

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/generate-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(
            source_content_sha256="abc123",
            title="Optional title",
            slug_hint="executive",
            tone="professional",
            audience="CTOs",
            variant="technical",
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
    assert body["source_relative_path"] == SOURCE_PATH
    assert body["source_content_sha256"] == "abc123"
    assert body["provider"] == "deepseek"
    assert body["model"] == "deepseek-v4-flash"
    assert body["generated_draft_content"] == "Generated LinkedIn draft for review."
    assert body["errors"] == []

    draft_file = base / body["draft_relative_path"]
    assert draft_file.is_file()
    assert "Generated LinkedIn draft" in draft_file.read_text(encoding="utf-8")

    metadata = json.loads(
        (base / body["metadata_path"]).read_text(encoding="utf-8")
    )
    assert metadata["trigger"] == "POST /generate-linkedin-draft"
    assert metadata["provider"] == "deepseek"
    assert metadata["model"] == "deepseek-v4-flash"
    assert metadata["title"] == "Optional title"
    assert metadata["tone"] == "professional"
    assert "markdown_content" not in metadata
    assert "generated_draft_content" not in metadata
    assert DEEPSEEK_KEY not in json.dumps(metadata)
    assert "test-secret-key" not in json.dumps(metadata)


def test_requires_authentication(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    client = TestClient(create_app(make_settings(base)))

    response = client.post("/generate-linkedin-draft", json=_valid_payload())

    assert response.status_code == 401


def test_invalid_api_key(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    client = TestClient(create_app(make_settings(base)))

    response = client.post(
        "/generate-linkedin-draft",
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
        "/generate-linkedin-draft",
        headers=auth_header(),
        json={"markdown_content": MARKDOWN},
    )
    missing_markdown = client.post(
        "/generate-linkedin-draft",
        headers=auth_header(),
        json={"source_relative_path": SOURCE_PATH},
    )

    assert missing_source.status_code == 422
    assert "run_id" not in missing_source.json()
    assert missing_markdown.status_code == 422
    assert "run_id" not in missing_markdown.json()


def test_empty_markdown_content_returns_422(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    client = TestClient(create_app(make_settings(base)))

    response = client.post(
        "/generate-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(markdown_content="   "),
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
        "draft_content",
        "cta_style",
        "unexpected_field",
    ):
        response = client.post(
            "/generate-linkedin-draft",
            headers=auth_header(),
            json=_valid_payload(**{extra_field: "evil"}),
        )
        assert response.status_code == 422
        assert "run_id" not in response.json()


def test_computed_source_content_sha256(tmp_path, monkeypatch):
    base = tmp_path / "editorial"
    create_full_layout(base)
    monkeypatch.setattr(
        "silverman_blog_linkedin.main.generate_linkedin_draft_content",
        lambda *_args, **_kwargs: _mock_deepseek_success(),
    )

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/generate-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(),
    )

    expected = hashlib.sha256(MARKDOWN.encode("utf-8")).hexdigest()
    body = response.json()
    assert body["source_content_sha256"] == expected

    metadata = json.loads(
        (base / body["metadata_path"]).read_text(encoding="utf-8")
    )
    assert metadata["source_content_sha256"] == expected


def test_metadata_runs_missing_no_writes(tmp_path, monkeypatch):
    base = tmp_path / "editorial"
    create_full_layout(base)
    runs_dir = base / "metadata" / "runs"
    for child in runs_dir.iterdir():
        child.unlink()
    runs_dir.rmdir()

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/generate-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["provider"] == "deepseek"
    assert body["model"] is None
    assert body["metadata_written"] is False
    assert body["draft_written"] is False
    assert body["source_content_sha256"] is not None
    assert "metadata_runs_not_ready" in body["errors"]
    assert list((base / "linkedin-posts" / "review").glob("*.md")) == []


def test_deepseek_config_invalid(tmp_path, monkeypatch):
    base = tmp_path / "editorial"
    create_full_layout(base)
    monkeypatch.setenv("DEEPSEEK_TIMEOUT_SECONDS", "abc")

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/generate-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["provider"] == "deepseek"
    assert body["model"] is None
    assert body["draft_written"] is False
    assert body["metadata_written"] is True
    assert body["errors"] == ["deepseek_config_invalid"]
    assert list((base / "linkedin-posts" / "review").glob("*.md")) == []


def test_deepseek_api_key_missing(tmp_path, monkeypatch):
    base = tmp_path / "editorial"
    create_full_layout(base)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/generate-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["provider"] == "deepseek"
    assert body["model"] == "deepseek-v4-flash"
    assert body["draft_written"] is False
    assert body["metadata_written"] is True
    assert body["errors"] == ["deepseek_api_key_missing"]


def test_review_dir_missing_with_metadata(tmp_path, monkeypatch):
    base = tmp_path / "editorial"
    create_full_layout(base)
    review_dir = base / "linkedin-posts" / "review"
    for child in review_dir.iterdir():
        child.unlink()
    review_dir.rmdir()

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/generate-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["draft_written"] is False
    assert body["provider"] == "deepseek"
    assert body["model"] == "deepseek-v4-flash"
    assert "review_dir_not_ready" in body["errors"]


def test_source_path_shape_failure(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    client = TestClient(create_app(make_settings(base)))

    response = client.post(
        "/generate-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(source_relative_path="blog-posts/processed/post.md"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["draft_written"] is False
    assert body["provider"] == "deepseek"
    assert "path_outside_ready" in body["errors"]


@pytest.mark.parametrize(
    "error_code",
    [
        "deepseek_auth_failed",
        "deepseek_rate_limited",
        "deepseek_empty_response",
        "deepseek_timeout",
    ],
)
def test_deepseek_error_codes(tmp_path, monkeypatch, error_code):
    base = tmp_path / "editorial"
    create_full_layout(base)
    monkeypatch.setattr(
        "silverman_blog_linkedin.main.generate_linkedin_draft_content",
        lambda *_args, **_kwargs: DeepSeekGenerationResult(
            content=None, error_code=error_code
        ),
    )

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/generate-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["draft_written"] is False
    assert error_code in body["errors"]
    assert "generated_draft_content" not in body
    assert list((base / "linkedin-posts" / "review").glob("*.md")) == []


@patch("silverman_blog_linkedin.main.generate_run_id", return_value="run-20260705T150045Z-a1b2")
@patch("silverman_blog_linkedin.draft_writer._utc_timestamp", return_value="20260705T150045Z")
def test_draft_path_collision(_mock_ts, _mock_run_id, tmp_path, monkeypatch):
    base = tmp_path / "editorial"
    create_full_layout(base)
    review = base / "linkedin-posts" / "review"
    for name in (
        "20260705T150045Z-my-post.md",
        "20260705T150045Z-my-post-a1b2.md",
        "20260705T150045Z-my-post-run-20260705T150045Z-a1b2.md",
    ):
        (review / name).write_text("occupied\n", encoding="utf-8")

    monkeypatch.setattr(
        "silverman_blog_linkedin.main.generate_linkedin_draft_content",
        lambda *_args, **_kwargs: _mock_deepseek_success(),
    )

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/generate-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["draft_written"] is False
    assert body["errors"] == ["draft_path_collision"]


def test_metadata_write_failed_partial_failure(tmp_path, monkeypatch):
    base = tmp_path / "editorial"
    create_full_layout(base)
    monkeypatch.setattr(
        "silverman_blog_linkedin.main.generate_linkedin_draft_content",
        lambda *_args, **_kwargs: _mock_deepseek_success(),
    )

    def fail_metadata_write(*_args, **_kwargs):
        return False

    monkeypatch.setattr(
        "silverman_blog_linkedin.main.write_run_metadata",
        fail_metadata_write,
    )

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/generate-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["draft_written"] is True
    assert body["draft_relative_path"] is not None
    assert body["metadata_written"] is False
    assert body["metadata_path"] is None
    assert body["errors"] == ["metadata_write_failed"]
    assert "generated_draft_content" not in body

    draft_file = base / body["draft_relative_path"]
    assert draft_file.is_file()


def test_variant_used_as_slug_when_slug_hint_absent(
    tmp_path, monkeypatch
):
    base = tmp_path / "editorial"
    create_full_layout(base)
    monkeypatch.setattr(
        "silverman_blog_linkedin.main.generate_linkedin_draft_content",
        lambda *_args, **_kwargs: _mock_deepseek_success(),
    )

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/generate-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(variant="executive-recruiter"),
    )

    body = response.json()
    assert body["status"] == "completed"
    assert body["draft_relative_path"].endswith("-my-post-executive-recruiter.md")


def test_worker_health_without_deepseek_key(tmp_path, monkeypatch):
    base = tmp_path / "editorial"
    create_full_layout(base)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    client = TestClient(create_app(make_settings(base)))
    health = client.get("/health")
    process_ready = client.post("/process-ready", headers=auth_header())

    assert health.status_code == 200
    assert process_ready.status_code == 200


def test_no_secrets_in_response(tmp_path, monkeypatch):
    base = tmp_path / "editorial"
    create_full_layout(base)
    monkeypatch.setattr(
        "silverman_blog_linkedin.main.generate_linkedin_draft_content",
        lambda *_args, **_kwargs: _mock_deepseek_success(),
    )

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/generate-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(),
    )

    text = response.text
    assert DEEPSEEK_KEY not in text
    assert "test-secret-key" not in text
    assert MARKDOWN not in text

def test_source_blog_file_not_modified(tmp_path, monkeypatch):
    base = tmp_path / "editorial"
    create_full_layout(base)
    source = base / "blog-posts" / "ready" / "my-post.md"
    original = "# Original\n\nUnchanged.\n"
    source.write_text(original, encoding="utf-8")

    monkeypatch.setattr(
        "silverman_blog_linkedin.main.generate_linkedin_draft_content",
        lambda *_args, **_kwargs: _mock_deepseek_success(),
    )

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/generate-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(),
    )

    assert response.status_code == 200
    assert source.read_text(encoding="utf-8") == original


@pytest.mark.parametrize(
    "source_public_url",
    [
        PUBLIC_URL,
        "http://silverman.pro/2026/07/06/my-post/",
    ],
)
def test_valid_source_public_url_accepted(
    tmp_path, monkeypatch, source_public_url
):
    base = tmp_path / "editorial"
    create_full_layout(base)
    monkeypatch.setattr(
        "silverman_blog_linkedin.main.generate_linkedin_draft_content",
        lambda *_args, **_kwargs: _mock_deepseek_success(),
    )

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/generate-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(source_public_url=source_public_url),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["source_public_url"] == source_public_url


@pytest.mark.parametrize(
    "source_public_url",
    [
        "not-a-url",
        "javascript:alert(1)",
        "file:///etc/passwd",
        "//silverman.pro/post/",
        "   ",
    ],
)
def test_invalid_source_public_url_returns_422(tmp_path, source_public_url):
    base = tmp_path / "editorial"
    create_full_layout(base)
    client = TestClient(create_app(make_settings(base)))

    response = client.post(
        "/generate-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(source_public_url=source_public_url),
    )

    assert response.status_code == 422
    assert "run_id" not in response.json()


def test_whitespace_topic_theme_returns_422(tmp_path):
    base = tmp_path / "editorial"
    create_full_layout(base)
    client = TestClient(create_app(make_settings(base)))

    response = client.post(
        "/generate-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(topic_theme="   "),
    )

    assert response.status_code == 422
    assert "run_id" not in response.json()


def test_public_url_and_topic_theme_in_metadata_and_response(tmp_path, monkeypatch):
    base = tmp_path / "editorial"
    create_full_layout(base)
    monkeypatch.setattr(
        "silverman_blog_linkedin.main.generate_linkedin_draft_content",
        lambda *_args, **_kwargs: _mock_deepseek_success(),
    )

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/generate-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(
            source_public_url=PUBLIC_URL,
            topic_theme="architecture",
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_public_url"] == PUBLIC_URL
    assert body["topic_theme"] == "architecture"

    metadata = json.loads(
        (base / body["metadata_path"]).read_text(encoding="utf-8")
    )
    assert metadata["source_public_url"] == PUBLIC_URL
    assert metadata["topic_theme"] == "architecture"
    assert "markdown_content" not in metadata
    assert "generated_draft_content" not in metadata


def test_public_url_fields_omitted_when_not_provided(tmp_path, monkeypatch):
    base = tmp_path / "editorial"
    create_full_layout(base)
    monkeypatch.setattr(
        "silverman_blog_linkedin.main.generate_linkedin_draft_content",
        lambda *_args, **_kwargs: _mock_deepseek_success(),
    )

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/generate-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(),
    )

    body = response.json()
    assert "source_public_url" not in body
    assert "topic_theme" not in body

    metadata = json.loads(
        (base / body["metadata_path"]).read_text(encoding="utf-8")
    )
    assert "source_public_url" not in metadata
    assert "topic_theme" not in metadata


def test_backward_compatible_generation_without_public_url_fields(
    tmp_path, monkeypatch
):
    base = tmp_path / "editorial"
    create_full_layout(base)
    monkeypatch.setattr(
        "silverman_blog_linkedin.main.generate_linkedin_draft_content",
        lambda *_args, **_kwargs: _mock_deepseek_success(),
    )

    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        "/generate-linkedin-draft",
        headers=auth_header(),
        json=_valid_payload(
            source_content_sha256="abc123",
            title="Optional title",
            slug_hint="executive",
            tone="professional",
            audience="CTOs",
            variant="technical",
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["draft_written"] is True
    assert "source_public_url" not in body
    assert "topic_theme" not in body
