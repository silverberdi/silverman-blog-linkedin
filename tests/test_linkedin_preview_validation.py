"""Tests for LinkedIn article preview input verification (US-023).

All outbound HTTP is mocked; no live network and no LinkedIn API involvement.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.campaign_lifecycle import (
    METADATA_CAMPAIGNS_RELATIVE,
    read_campaign_metadata,
    write_campaign_metadata,
)
from silverman_blog_linkedin.github_pages_publish import ENV_REPO_PATH
from silverman_blog_linkedin.linkedin_preview_validation import (
    CHECK_CHECKOUT_CONSISTENCY,
    CHECK_FAILED,
    CHECK_LIVE_OG_METADATA,
    CHECK_PACKAGE_METADATA,
    CHECK_PASSED,
    CHECK_PUBLIC_IMAGE_AVAILABILITY,
    CHECK_SKIPPED,
    EVIDENCE_FIELD,
    LINKEDIN_PREVIEW_VALIDATION_CAMPAIGN_NOT_FOUND,
    LINKEDIN_PREVIEW_VALIDATION_CHECKOUT_NOT_CONFIGURED,
    LINKEDIN_PREVIEW_VALIDATION_CHECKOUT_POST_MISSING,
    LINKEDIN_PREVIEW_VALIDATION_DESCRIPTION_MISMATCH,
    LINKEDIN_PREVIEW_VALIDATION_DESCRIPTION_MISSING,
    LINKEDIN_PREVIEW_VALIDATION_IMAGE_URL_MISSING,
    LINKEDIN_PREVIEW_VALIDATION_METADATA_MISSING,
    LINKEDIN_PREVIEW_VALIDATION_OG_DESCRIPTION_MISMATCH,
    LINKEDIN_PREVIEW_VALIDATION_OG_IMAGE_MISMATCH,
    LINKEDIN_PREVIEW_VALIDATION_OG_TAGS_MISSING,
    LINKEDIN_PREVIEW_VALIDATION_OG_TITLE_MISMATCH,
    LINKEDIN_PREVIEW_VALIDATION_PACKAGE_NOT_GENERATED,
    LINKEDIN_PREVIEW_VALIDATION_PUBLIC_IMAGE_NOT_IMAGE,
    LINKEDIN_PREVIEW_VALIDATION_PUBLIC_IMAGE_UNREACHABLE,
    LINKEDIN_PREVIEW_VALIDATION_PUBLIC_URL_UNREACHABLE,
    LINKEDIN_PREVIEW_VALIDATION_TITLE_MISMATCH,
    LINKEDIN_PREVIEW_VALIDATION_TITLE_MISSING,
    VALIDATION_BLOCKED,
    VALIDATION_FAILED,
    VALIDATION_PASSED,
    PreviewFetchResult,
    extract_og_tags,
    validate_linkedin_article_preview,
)
from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, make_settings

PUBLIC_SLUG = "why-i-did-not-start-with-the-database"
PUBLICATION_DATE = "2026-07-06"
CAMPAIGN_ID = f"flow-a-{PUBLICATION_DATE}-{PUBLIC_SLUG}"
PUBLIC_URL = f"https://silverman.pro/2026/07/06/{PUBLIC_SLUG}/"
PUBLIC_IMAGE_URL = f"https://silverman.pro/assets/images/{PUBLIC_SLUG}.png"
TITLE = "Why I Did Not Start With the Database"
DESCRIPTION = "A senior practitioner's take on starting with the domain."
POST_RELATIVE = f"_posts/{PUBLICATION_DATE}-{PUBLIC_SLUG}.md"


class FakePreviewHttpClient:
    """Injectable HTTP client; records calls and returns canned results."""

    def __init__(
        self,
        document: PreviewFetchResult | None = None,
        headers: PreviewFetchResult | None = None,
    ) -> None:
        self.document_result = document
        self.header_result = headers
        self.document_calls: list[tuple[str, float]] = []
        self.header_calls: list[tuple[str, float]] = []

    def fetch_document(self, url: str, *, timeout: float) -> PreviewFetchResult:
        self.document_calls.append((url, timeout))
        assert self.document_result is not None, "unexpected document fetch"
        return self.document_result

    def fetch_headers(self, url: str, *, timeout: float) -> PreviewFetchResult:
        self.header_calls.append((url, timeout))
        assert self.header_result is not None, "unexpected header fetch"
        return self.header_result


def _og_page(
    *,
    title: str | None = TITLE,
    description: str | None = DESCRIPTION,
    image: str | None = PUBLIC_IMAGE_URL,
) -> str:
    tags = []
    if title is not None:
        tags.append(f'<meta property="og:title" content="{title}">')
    if description is not None:
        tags.append(f'<meta property="og:description" content="{description}">')
    if image is not None:
        tags.append(f'<meta property="og:image" content="{image}">')
    head = "\n".join(tags)
    return f"<html><head>\n{head}\n</head><body>post body</body></html>"


def _ok_document(text: str | None = None) -> PreviewFetchResult:
    return PreviewFetchResult(
        status_code=200,
        content_type="text/html; charset=utf-8",
        text=text if text is not None else _og_page(),
    )


def _ok_image() -> PreviewFetchResult:
    return PreviewFetchResult(status_code=200, content_type="image/png")


def _happy_client() -> FakePreviewHttpClient:
    return FakePreviewHttpClient(document=_ok_document(), headers=_ok_image())


def _campaign(
    *,
    article_preview: dict | None | str = "default",
    with_package: bool = True,
) -> dict:
    campaign: dict = {
        "campaign_id": CAMPAIGN_ID,
        "flow": "flow-a",
        "state": "distribution_scheduled",
        "public_slug": PUBLIC_SLUG,
        "publication_date": PUBLICATION_DATE,
        "source_public_url": PUBLIC_URL,
        "published_post_relative_path": POST_RELATIVE,
        "variants": [
            {
                "variant": "executive-recruiter",
                "publish_state": "pending",
                "source_public_url": PUBLIC_URL,
            }
        ],
        "errors": [],
        "warnings": [],
    }
    if with_package:
        package: dict = {
            "package_status": "generated",
            "source_public_url": PUBLIC_URL,
            "variant_ids": ["executive-recruiter"],
        }
        if article_preview == "default":
            package["article_preview"] = {
                "status": "available",
                "article_title": TITLE,
                "article_description": DESCRIPTION,
                "public_image_url": PUBLIC_IMAGE_URL,
                "public_image_path": f"/assets/images/{PUBLIC_SLUG}.png",
                "public_url": PUBLIC_URL,
            }
        elif article_preview is not None:
            package["article_preview"] = article_preview
        campaign["linkedin_package"] = package
    return campaign


@pytest.fixture
def editorial_base(tmp_path: Path) -> Path:
    (tmp_path / METADATA_CAMPAIGNS_RELATIVE).mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def checkout_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "public-checkout"
    (repo / "_posts").mkdir(parents=True, exist_ok=True)
    (repo / POST_RELATIVE).write_text(
        "---\n"
        f"title: {TITLE}\n"
        f"description: {DESCRIPTION}\n"
        "layout: post\n"
        "---\n"
        "Post body.\n",
        encoding="utf-8",
    )
    return repo


def _write_campaign(base: Path, campaign: dict) -> None:
    result = write_campaign_metadata(base, CAMPAIGN_ID, campaign)
    assert result.written


def _checkout_env(repo: Path) -> dict[str, str]:
    return {ENV_REPO_PATH: str(repo)}


def test_full_pass_all_checks(editorial_base: Path, checkout_repo: Path):
    _write_campaign(editorial_base, _campaign())
    client = _happy_client()

    result = validate_linkedin_article_preview(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        dry_run=True,
        environ=_checkout_env(checkout_repo),
        http_client=client,
    )

    assert result.status == VALIDATION_PASSED
    assert result.codes == []
    assert result.dry_run is True
    for name in (
        CHECK_PACKAGE_METADATA,
        CHECK_CHECKOUT_CONSISTENCY,
        CHECK_LIVE_OG_METADATA,
        CHECK_PUBLIC_IMAGE_AVAILABILITY,
    ):
        assert result.checks[name].status == CHECK_PASSED
    assert result.public_url == PUBLIC_URL
    assert result.public_image_url == PUBLIC_IMAGE_URL
    assert client.document_calls == [(PUBLIC_URL, 10.0)]
    assert client.header_calls == [(PUBLIC_IMAGE_URL, 10.0)]


def test_missing_preview_block_fails_and_skips_dependent_checks(
    editorial_base: Path,
):
    _write_campaign(editorial_base, _campaign(article_preview=None))
    client = FakePreviewHttpClient()

    result = validate_linkedin_article_preview(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        dry_run=True,
        environ={},
        http_client=client,
    )

    assert result.status == VALIDATION_FAILED
    assert LINKEDIN_PREVIEW_VALIDATION_METADATA_MISSING in result.codes
    assert result.checks[CHECK_PACKAGE_METADATA].status == CHECK_FAILED
    assert result.checks[CHECK_LIVE_OG_METADATA].status == CHECK_SKIPPED
    assert result.checks[CHECK_PUBLIC_IMAGE_AVAILABILITY].status == CHECK_SKIPPED
    assert client.document_calls == []
    assert client.header_calls == []


def test_missing_individual_fields_fail_with_stable_codes(editorial_base: Path):
    _write_campaign(
        editorial_base,
        _campaign(
            article_preview={
                "status": "missing",
                "article_title": "",
                "article_description": None,
                "public_image_url": "",
                "public_url": PUBLIC_URL,
            }
        ),
    )
    client = FakePreviewHttpClient(document=_ok_document(_og_page()))

    result = validate_linkedin_article_preview(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        dry_run=True,
        environ={},
        http_client=client,
    )

    assert result.status == VALIDATION_FAILED
    assert LINKEDIN_PREVIEW_VALIDATION_TITLE_MISSING in result.codes
    assert LINKEDIN_PREVIEW_VALIDATION_DESCRIPTION_MISSING in result.codes
    assert LINKEDIN_PREVIEW_VALIDATION_IMAGE_URL_MISSING in result.codes
    assert LINKEDIN_PREVIEW_VALIDATION_METADATA_MISSING not in result.codes
    # public_image_url absent: dependent availability check is skipped.
    assert result.checks[CHECK_PUBLIC_IMAGE_AVAILABILITY].status == CHECK_SKIPPED
    assert client.header_calls == []


def test_checkout_title_and_description_mismatch(
    editorial_base: Path, checkout_repo: Path
):
    (checkout_repo / POST_RELATIVE).write_text(
        "---\n"
        "title: A Different Title\n"
        "description: A different description entirely.\n"
        "---\n"
        "Body.\n",
        encoding="utf-8",
    )
    _write_campaign(editorial_base, _campaign())

    result = validate_linkedin_article_preview(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        dry_run=True,
        environ=_checkout_env(checkout_repo),
        http_client=_happy_client(),
    )

    assert result.status == VALIDATION_FAILED
    assert result.checks[CHECK_CHECKOUT_CONSISTENCY].status == CHECK_FAILED
    assert LINKEDIN_PREVIEW_VALIDATION_TITLE_MISMATCH in result.codes
    assert LINKEDIN_PREVIEW_VALIDATION_DESCRIPTION_MISMATCH in result.codes


def test_checkout_post_missing(editorial_base: Path, checkout_repo: Path):
    (checkout_repo / POST_RELATIVE).unlink()
    _write_campaign(editorial_base, _campaign())

    result = validate_linkedin_article_preview(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        dry_run=True,
        environ=_checkout_env(checkout_repo),
        http_client=_happy_client(),
    )

    assert result.status == VALIDATION_FAILED
    assert LINKEDIN_PREVIEW_VALIDATION_CHECKOUT_POST_MISSING in result.codes


def test_checkout_skipped_when_repo_unset_still_passes(editorial_base: Path):
    _write_campaign(editorial_base, _campaign())

    result = validate_linkedin_article_preview(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        dry_run=True,
        environ={},
        http_client=_happy_client(),
    )

    assert result.status == VALIDATION_PASSED
    check = result.checks[CHECK_CHECKOUT_CONSISTENCY]
    assert check.status == CHECK_SKIPPED
    assert LINKEDIN_PREVIEW_VALIDATION_CHECKOUT_NOT_CONFIGURED in check.codes
    assert LINKEDIN_PREVIEW_VALIDATION_CHECKOUT_NOT_CONFIGURED in result.codes


def test_unreachable_public_url_is_not_reported_as_mismatch(editorial_base: Path):
    _write_campaign(editorial_base, _campaign())
    client = FakePreviewHttpClient(
        document=PreviewFetchResult(status_code=None, transport_error="ConnectTimeout"),
        headers=_ok_image(),
    )

    result = validate_linkedin_article_preview(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        dry_run=True,
        environ={},
        http_client=client,
    )

    assert result.status == VALIDATION_FAILED
    og_check = result.checks[CHECK_LIVE_OG_METADATA]
    assert og_check.status == CHECK_FAILED
    assert og_check.codes == [LINKEDIN_PREVIEW_VALIDATION_PUBLIC_URL_UNREACHABLE]
    assert LINKEDIN_PREVIEW_VALIDATION_OG_TITLE_MISMATCH not in result.codes
    assert LINKEDIN_PREVIEW_VALIDATION_OG_DESCRIPTION_MISMATCH not in result.codes


def test_public_url_non_2xx_is_unreachable(editorial_base: Path):
    _write_campaign(editorial_base, _campaign())
    client = FakePreviewHttpClient(
        document=PreviewFetchResult(status_code=404, content_type="text/html"),
        headers=_ok_image(),
    )

    result = validate_linkedin_article_preview(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        dry_run=True,
        environ={},
        http_client=client,
    )

    assert LINKEDIN_PREVIEW_VALIDATION_PUBLIC_URL_UNREACHABLE in result.codes


def test_og_tags_missing(editorial_base: Path):
    _write_campaign(editorial_base, _campaign())
    client = FakePreviewHttpClient(
        document=_ok_document("<html><head><title>x</title></head></html>"),
        headers=_ok_image(),
    )

    result = validate_linkedin_article_preview(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        dry_run=True,
        environ={},
        http_client=client,
    )

    assert result.status == VALIDATION_FAILED
    assert LINKEDIN_PREVIEW_VALIDATION_OG_TAGS_MISSING in result.codes


def test_og_per_field_mismatch_codes(editorial_base: Path):
    _write_campaign(editorial_base, _campaign())
    client = FakePreviewHttpClient(
        document=_ok_document(
            _og_page(
                title="Wrong Title",
                description="Wrong description.",
                image="https://silverman.pro/assets/images/other.png",
            )
        ),
        headers=_ok_image(),
    )

    result = validate_linkedin_article_preview(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        dry_run=True,
        environ={},
        http_client=client,
    )

    assert result.status == VALIDATION_FAILED
    assert LINKEDIN_PREVIEW_VALIDATION_OG_TITLE_MISMATCH in result.codes
    assert LINKEDIN_PREVIEW_VALIDATION_OG_DESCRIPTION_MISMATCH in result.codes
    assert LINKEDIN_PREVIEW_VALIDATION_OG_IMAGE_MISMATCH in result.codes
    assert LINKEDIN_PREVIEW_VALIDATION_OG_TAGS_MISSING not in result.codes


def test_og_whitespace_normalization_passes(editorial_base: Path):
    _write_campaign(editorial_base, _campaign())
    client = FakePreviewHttpClient(
        document=_ok_document(_og_page(title=f"  {TITLE.replace(' ', '  ')} ")),
        headers=_ok_image(),
    )

    result = validate_linkedin_article_preview(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        dry_run=True,
        environ={},
        http_client=client,
    )

    assert result.checks[CHECK_LIVE_OG_METADATA].status == CHECK_PASSED


def test_public_image_unreachable(editorial_base: Path):
    _write_campaign(editorial_base, _campaign())
    client = FakePreviewHttpClient(
        document=_ok_document(),
        headers=PreviewFetchResult(status_code=404),
    )

    result = validate_linkedin_article_preview(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        dry_run=True,
        environ={},
        http_client=client,
    )

    assert result.status == VALIDATION_FAILED
    image_check = result.checks[CHECK_PUBLIC_IMAGE_AVAILABILITY]
    assert image_check.codes == [
        LINKEDIN_PREVIEW_VALIDATION_PUBLIC_IMAGE_UNREACHABLE
    ]


def test_public_image_not_image_content_type(editorial_base: Path):
    _write_campaign(editorial_base, _campaign())
    client = FakePreviewHttpClient(
        document=_ok_document(),
        headers=PreviewFetchResult(
            status_code=200, content_type="text/html; charset=utf-8"
        ),
    )

    result = validate_linkedin_article_preview(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        dry_run=True,
        environ={},
        http_client=client,
    )

    assert result.status == VALIDATION_FAILED
    assert LINKEDIN_PREVIEW_VALIDATION_PUBLIC_IMAGE_NOT_IMAGE in result.codes


def test_multi_failure_single_pass_reports_all_codes(editorial_base: Path):
    _write_campaign(editorial_base, _campaign())
    client = FakePreviewHttpClient(
        document=_ok_document(_og_page(title="Wrong Title")),
        headers=PreviewFetchResult(status_code=None, transport_error="ConnectError"),
    )

    result = validate_linkedin_article_preview(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        dry_run=True,
        environ={},
        http_client=client,
    )

    assert result.status == VALIDATION_FAILED
    assert LINKEDIN_PREVIEW_VALIDATION_OG_TITLE_MISMATCH in result.codes
    assert LINKEDIN_PREVIEW_VALIDATION_PUBLIC_IMAGE_UNREACHABLE in result.codes


def test_blocked_campaign_not_found_makes_no_http_calls(editorial_base: Path):
    client = FakePreviewHttpClient()

    result = validate_linkedin_article_preview(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        dry_run=True,
        environ={},
        http_client=client,
    )

    assert result.status == VALIDATION_BLOCKED
    assert result.codes == [LINKEDIN_PREVIEW_VALIDATION_CAMPAIGN_NOT_FOUND]
    assert result.checks == {}
    assert client.document_calls == []
    assert client.header_calls == []


def test_blocked_package_not_generated_makes_no_http_calls(editorial_base: Path):
    _write_campaign(editorial_base, _campaign(with_package=False))
    client = FakePreviewHttpClient()

    result = validate_linkedin_article_preview(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        dry_run=False,
        environ={},
        http_client=client,
    )

    assert result.status == VALIDATION_BLOCKED
    assert result.codes == [LINKEDIN_PREVIEW_VALIDATION_PACKAGE_NOT_GENERATED]
    assert client.document_calls == []
    assert client.header_calls == []
    # Blocked runs persist no evidence.
    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    assert EVIDENCE_FIELD not in campaign


def test_dry_run_leaves_campaign_document_byte_identical(editorial_base: Path):
    _write_campaign(editorial_base, _campaign())
    campaign_path = editorial_base / METADATA_CAMPAIGNS_RELATIVE / f"{CAMPAIGN_ID}.json"
    before = campaign_path.read_bytes()

    result = validate_linkedin_article_preview(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        dry_run=True,
        environ={},
        http_client=_happy_client(),
    )

    assert result.dry_run is True
    assert result.metadata_written is False
    assert campaign_path.read_bytes() == before


def test_real_run_persists_evidence_and_changes_no_other_field(
    editorial_base: Path,
):
    _write_campaign(editorial_base, _campaign())
    before = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert before is not None

    result = validate_linkedin_article_preview(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        dry_run=False,
        environ={},
        http_client=_happy_client(),
    )

    assert result.dry_run is False
    assert result.metadata_written is True

    after = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert after is not None
    evidence = after[EVIDENCE_FIELD]
    assert evidence["status"] == VALIDATION_PASSED
    assert evidence["codes"] == [LINKEDIN_PREVIEW_VALIDATION_CHECKOUT_NOT_CONFIGURED]
    assert evidence["public_url"] == PUBLIC_URL
    assert evidence["public_image_url"] == PUBLIC_IMAGE_URL
    assert evidence["validated_at_utc"].endswith("Z")
    assert set(evidence["checks"]) == {
        CHECK_PACKAGE_METADATA,
        CHECK_CHECKOUT_CONSISTENCY,
        CHECK_LIVE_OG_METADATA,
        CHECK_PUBLIC_IMAGE_AVAILABILITY,
    }

    stripped = {key: value for key, value in after.items() if key != EVIDENCE_FIELD}
    assert stripped == before
    assert after["linkedin_package"] == before["linkedin_package"]
    assert after["variants"] == before["variants"]


def test_real_run_evidence_is_last_write_wins_snapshot(editorial_base: Path):
    _write_campaign(editorial_base, _campaign())

    first = validate_linkedin_article_preview(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        dry_run=False,
        environ={},
        http_client=FakePreviewHttpClient(
            document=_ok_document(),
            headers=PreviewFetchResult(status_code=404),
        ),
    )
    assert first.status == VALIDATION_FAILED

    second = validate_linkedin_article_preview(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        dry_run=False,
        environ={},
        http_client=_happy_client(),
    )
    assert second.status == VALIDATION_PASSED

    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    assert campaign[EVIDENCE_FIELD]["status"] == VALIDATION_PASSED


def test_extract_og_tags_handles_attribute_order_and_entities():
    document = (
        "<html><head>"
        '<meta content="Fish &amp; Chips" property="og:title" />'
        "<META PROPERTY='og:image' CONTENT='https://example.test/x.png'>"
        '<meta name="description" content="not og">'
        "</head></html>"
    )
    tags = extract_og_tags(document)
    assert tags["og:title"] == "Fish &amp; Chips"
    assert tags["og:image"] == "https://example.test/x.png"
    assert "description" not in tags


def test_non_https_public_url_reports_unreachable(editorial_base: Path):
    campaign = _campaign()
    campaign["linkedin_package"]["article_preview"]["public_url"] = (
        PUBLIC_URL.replace("https://", "http://")
    )
    _write_campaign(editorial_base, campaign)
    client = FakePreviewHttpClient(headers=_ok_image())

    result = validate_linkedin_article_preview(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        dry_run=True,
        environ={},
        http_client=client,
    )

    assert LINKEDIN_PREVIEW_VALIDATION_PUBLIC_URL_UNREACHABLE in result.codes
    assert client.document_calls == []


# --- HTTP endpoint (blocked scenarios only: no outbound HTTP is possible) ---


@pytest.fixture
def api_client(editorial_base: Path) -> TestClient:
    return TestClient(create_app(make_settings(editorial_base)))


def test_endpoint_requires_auth(api_client: TestClient):
    response = api_client.post(
        "/validate-linkedin-article-preview",
        json={"campaign_id": CAMPAIGN_ID},
    )
    assert response.status_code == 401


def test_endpoint_rejects_invalid_body_with_422(api_client: TestClient):
    missing = api_client.post(
        "/validate-linkedin-article-preview",
        json={},
        headers=auth_header(),
    )
    assert missing.status_code == 422

    extra = api_client.post(
        "/validate-linkedin-article-preview",
        json={"campaign_id": CAMPAIGN_ID, "unknown_field": True},
        headers=auth_header(),
    )
    assert extra.status_code == 422

    blank = api_client.post(
        "/validate-linkedin-article-preview",
        json={"campaign_id": "   "},
        headers=auth_header(),
    )
    assert blank.status_code == 422


def test_endpoint_dry_run_defaults_true_and_returns_structured_response(
    api_client: TestClient,
):
    response = api_client.post(
        "/validate-linkedin-article-preview",
        json={"campaign_id": CAMPAIGN_ID},
        headers=auth_header(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == VALIDATION_BLOCKED
    assert payload["dry_run"] is True
    assert payload["campaign_id"] == CAMPAIGN_ID
    assert payload["codes"] == [LINKEDIN_PREVIEW_VALIDATION_CAMPAIGN_NOT_FOUND]
    assert payload["checks"] == {}


def test_endpoint_blocked_package_not_generated(
    api_client: TestClient, editorial_base: Path
):
    _write_campaign(editorial_base, _campaign(with_package=False))

    response = api_client.post(
        "/validate-linkedin-article-preview",
        json={"campaign_id": CAMPAIGN_ID, "dry_run": False},
        headers=auth_header(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == VALIDATION_BLOCKED
    assert payload["dry_run"] is False
    assert payload["codes"] == [
        LINKEDIN_PREVIEW_VALIDATION_PACKAGE_NOT_GENERATED
    ]
