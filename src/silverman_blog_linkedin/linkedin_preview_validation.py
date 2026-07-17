"""On-demand verification of LinkedIn article preview inputs (US-023).

Verifies package preview metadata, public-checkout front matter consistency,
live Open Graph tags, and public image HTTP availability for one Flow A
campaign with a generated LinkedIn package. Makes no LinkedIn API calls and
reads no LinkedIn OAuth tokens (US-024 boundary).
"""

from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx

from silverman_blog_linkedin.campaign_lifecycle import (
    read_campaign_metadata,
    write_campaign_metadata,
)
from silverman_blog_linkedin.github_pages_publish import (
    ENV_REPO_PATH,
    POSTS_RELATIVE,
    _split_frontmatter,
)
from silverman_blog_linkedin.run_metadata import utc_now_iso

logger = logging.getLogger(__name__)

# Overall verdicts.
VALIDATION_PASSED = "passed"
VALIDATION_FAILED = "failed"
VALIDATION_BLOCKED = "blocked"

# Per-check statuses.
CHECK_PASSED = "passed"
CHECK_FAILED = "failed"
CHECK_SKIPPED = "skipped"

# Check identifiers.
CHECK_PACKAGE_METADATA = "package_metadata"
CHECK_CHECKOUT_CONSISTENCY = "checkout_consistency"
CHECK_LIVE_OG_METADATA = "live_og_metadata"
CHECK_PUBLIC_IMAGE_AVAILABILITY = "public_image_availability"

# Stable outcome codes (delta spec linkedin-article-preview-verification).
LINKEDIN_PREVIEW_VALIDATION_CAMPAIGN_NOT_FOUND = (
    "linkedin_preview_validation_campaign_not_found"
)
LINKEDIN_PREVIEW_VALIDATION_PACKAGE_NOT_GENERATED = (
    "linkedin_preview_validation_package_not_generated"
)
LINKEDIN_PREVIEW_VALIDATION_METADATA_MISSING = (
    "linkedin_preview_validation_metadata_missing"
)
LINKEDIN_PREVIEW_VALIDATION_TITLE_MISSING = (
    "linkedin_preview_validation_title_missing"
)
LINKEDIN_PREVIEW_VALIDATION_DESCRIPTION_MISSING = (
    "linkedin_preview_validation_description_missing"
)
LINKEDIN_PREVIEW_VALIDATION_IMAGE_URL_MISSING = (
    "linkedin_preview_validation_image_url_missing"
)
LINKEDIN_PREVIEW_VALIDATION_TITLE_MISMATCH = (
    "linkedin_preview_validation_title_mismatch"
)
LINKEDIN_PREVIEW_VALIDATION_DESCRIPTION_MISMATCH = (
    "linkedin_preview_validation_description_mismatch"
)
LINKEDIN_PREVIEW_VALIDATION_CHECKOUT_POST_MISSING = (
    "linkedin_preview_validation_checkout_post_missing"
)
LINKEDIN_PREVIEW_VALIDATION_CHECKOUT_NOT_CONFIGURED = (
    "linkedin_preview_validation_checkout_not_configured"
)
LINKEDIN_PREVIEW_VALIDATION_PUBLIC_URL_UNREACHABLE = (
    "linkedin_preview_validation_public_url_unreachable"
)
LINKEDIN_PREVIEW_VALIDATION_OG_TITLE_MISMATCH = (
    "linkedin_preview_validation_og_title_mismatch"
)
LINKEDIN_PREVIEW_VALIDATION_OG_DESCRIPTION_MISMATCH = (
    "linkedin_preview_validation_og_description_mismatch"
)
LINKEDIN_PREVIEW_VALIDATION_OG_IMAGE_MISMATCH = (
    "linkedin_preview_validation_og_image_mismatch"
)
LINKEDIN_PREVIEW_VALIDATION_OG_TAGS_MISSING = (
    "linkedin_preview_validation_og_tags_missing"
)
LINKEDIN_PREVIEW_VALIDATION_PUBLIC_IMAGE_UNREACHABLE = (
    "linkedin_preview_validation_public_image_unreachable"
)
LINKEDIN_PREVIEW_VALIDATION_PUBLIC_IMAGE_NOT_IMAGE = (
    "linkedin_preview_validation_public_image_not_image"
)

EVIDENCE_FIELD = "linkedin_article_preview_validation"

HTTP_TIMEOUT_SECONDS = 10.0
_MAX_REDIRECTS = 5
# OG tags live in <head>; cap the fetched document so responses stay bounded.
_MAX_DOCUMENT_BYTES = 262_144

_META_TAG_PATTERN = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
_ATTR_PATTERN = re.compile(
    r"""([a-zA-Z:-]+)\s*=\s*("([^"]*)"|'([^']*)')""",
)


@dataclass(frozen=True)
class PreviewFetchResult:
    """Outcome of one outbound HTTPS request (no body retained for images)."""

    status_code: int | None
    content_type: str | None = None
    text: str = ""
    transport_error: str | None = None

    @property
    def reachable(self) -> bool:
        return (
            self.transport_error is None
            and self.status_code is not None
            and 200 <= self.status_code < 300
        )


class PreviewHttpClient(Protocol):
    def fetch_document(self, url: str, *, timeout: float) -> PreviewFetchResult: ...

    def fetch_headers(self, url: str, *, timeout: float) -> PreviewFetchResult: ...


class HttpxPreviewHttpClient:
    """Production HTTPS client with bounded timeout and capped document reads."""

    def fetch_document(self, url: str, *, timeout: float) -> PreviewFetchResult:
        try:
            with httpx.Client(
                timeout=timeout,
                follow_redirects=True,
                max_redirects=_MAX_REDIRECTS,
            ) as client:
                with client.stream("GET", url) as response:
                    chunks: list[bytes] = []
                    total = 0
                    for chunk in response.iter_bytes():
                        chunks.append(chunk)
                        total += len(chunk)
                        if total >= _MAX_DOCUMENT_BYTES:
                            break
                    body = b"".join(chunks)[:_MAX_DOCUMENT_BYTES]
                    return PreviewFetchResult(
                        status_code=response.status_code,
                        content_type=response.headers.get("content-type"),
                        text=body.decode("utf-8", errors="replace"),
                    )
        except httpx.HTTPError as exc:
            return PreviewFetchResult(
                status_code=None, transport_error=type(exc).__name__
            )

    def fetch_headers(self, url: str, *, timeout: float) -> PreviewFetchResult:
        try:
            with httpx.Client(
                timeout=timeout,
                follow_redirects=True,
                max_redirects=_MAX_REDIRECTS,
            ) as client:
                with client.stream("GET", url) as response:
                    # Status and content type only; body is never read or kept.
                    return PreviewFetchResult(
                        status_code=response.status_code,
                        content_type=response.headers.get("content-type"),
                    )
        except httpx.HTTPError as exc:
            return PreviewFetchResult(
                status_code=None, transport_error=type(exc).__name__
            )


@dataclass
class PreviewCheckResult:
    status: str
    codes: list[str] = field(default_factory=list)
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"status": self.status, "codes": list(self.codes)}
        if self.detail:
            payload["detail"] = dict(self.detail)
        return payload


@dataclass
class PreviewValidationResult:
    status: str
    campaign_id: str
    dry_run: bool
    checks: dict[str, PreviewCheckResult] = field(default_factory=dict)
    codes: list[str] = field(default_factory=list)
    public_url: str | None = None
    public_image_url: str | None = None
    metadata_written: bool = False
    metadata_error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "campaign_id": self.campaign_id,
            "dry_run": self.dry_run,
            "checks": {name: check.to_dict() for name, check in self.checks.items()},
            "codes": list(self.codes),
            "public_url": self.public_url,
            "public_image_url": self.public_image_url,
            "metadata_written": self.metadata_written,
            "metadata_error_code": self.metadata_error_code,
        }


def _normalize_text(value: Any) -> str:
    """Whitespace-normalized comparison form (HTML entities decoded)."""
    if value is None:
        return ""
    return " ".join(html.unescape(str(value)).split())


def _non_empty(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _is_https(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def extract_og_tags(document: str) -> dict[str, str]:
    """Extract og:* meta tag contents from an HTML document."""
    tags: dict[str, str] = {}
    for match in _META_TAG_PATTERN.finditer(document):
        attributes: dict[str, str] = {}
        for attr in _ATTR_PATTERN.finditer(match.group(0)):
            name = attr.group(1).lower()
            value = attr.group(3) if attr.group(3) is not None else attr.group(4)
            attributes[name] = value
        prop = attributes.get("property") or attributes.get("name") or ""
        if prop.lower().startswith("og:") and "content" in attributes:
            tags.setdefault(prop.lower(), attributes["content"])
    return tags


def _check_package_metadata(
    article_preview: dict[str, Any] | None,
) -> PreviewCheckResult:
    if not isinstance(article_preview, dict) or not article_preview:
        return PreviewCheckResult(
            status=CHECK_FAILED,
            codes=[LINKEDIN_PREVIEW_VALIDATION_METADATA_MISSING],
        )

    codes: list[str] = []
    if not _non_empty(article_preview.get("public_url")):
        codes.append(LINKEDIN_PREVIEW_VALIDATION_METADATA_MISSING)
    if not _non_empty(article_preview.get("article_title")):
        codes.append(LINKEDIN_PREVIEW_VALIDATION_TITLE_MISSING)
    if not _non_empty(article_preview.get("article_description")):
        codes.append(LINKEDIN_PREVIEW_VALIDATION_DESCRIPTION_MISSING)
    if not _non_empty(article_preview.get("public_image_url")):
        codes.append(LINKEDIN_PREVIEW_VALIDATION_IMAGE_URL_MISSING)

    if codes:
        return PreviewCheckResult(status=CHECK_FAILED, codes=codes)
    return PreviewCheckResult(status=CHECK_PASSED)


def _resolve_checkout_post_path(
    repo_path: Path, campaign: dict[str, Any]
) -> Path | None:
    recorded = _non_empty(campaign.get("published_post_relative_path"))
    if recorded:
        candidate = (repo_path / recorded).resolve()
        if _is_within(candidate, repo_path):
            return candidate
        return None
    publication_date = _non_empty(campaign.get("publication_date"))
    public_slug = _non_empty(campaign.get("public_slug"))
    if not publication_date or not public_slug:
        return None
    candidate = (
        repo_path / POSTS_RELATIVE / f"{publication_date}-{public_slug}.md"
    ).resolve()
    if _is_within(candidate, repo_path):
        return candidate
    return None


def _is_within(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def _check_checkout_consistency(
    campaign: dict[str, Any],
    *,
    article_title: str | None,
    article_description: str | None,
    environ: dict[str, str] | None,
) -> PreviewCheckResult:
    repo_raw = (environ or {}).get(ENV_REPO_PATH, "").strip()
    if not repo_raw:
        return PreviewCheckResult(
            status=CHECK_SKIPPED,
            codes=[LINKEDIN_PREVIEW_VALIDATION_CHECKOUT_NOT_CONFIGURED],
        )

    if article_title is None and article_description is None:
        # Required inputs absent from package metadata; package_metadata
        # already carries the missing-field codes.
        return PreviewCheckResult(status=CHECK_SKIPPED)

    repo_path = Path(repo_raw).expanduser().resolve()
    post_path = _resolve_checkout_post_path(repo_path, campaign)
    if post_path is None or not post_path.is_file():
        return PreviewCheckResult(
            status=CHECK_FAILED,
            codes=[LINKEDIN_PREVIEW_VALIDATION_CHECKOUT_POST_MISSING],
        )

    try:
        frontmatter, _body = _split_frontmatter(
            post_path.read_text(encoding="utf-8")
        )
    except Exception:
        return PreviewCheckResult(
            status=CHECK_FAILED,
            codes=[LINKEDIN_PREVIEW_VALIDATION_CHECKOUT_POST_MISSING],
        )

    codes: list[str] = []
    if article_title is not None and _normalize_text(
        frontmatter.get("title")
    ) != _normalize_text(article_title):
        codes.append(LINKEDIN_PREVIEW_VALIDATION_TITLE_MISMATCH)
    if article_description is not None and _normalize_text(
        frontmatter.get("description")
    ) != _normalize_text(article_description):
        codes.append(LINKEDIN_PREVIEW_VALIDATION_DESCRIPTION_MISMATCH)

    if codes:
        return PreviewCheckResult(status=CHECK_FAILED, codes=codes)
    return PreviewCheckResult(status=CHECK_PASSED)


def _check_live_og_metadata(
    *,
    public_url: str | None,
    article_title: str | None,
    article_description: str | None,
    public_image_url: str | None,
    http_client: PreviewHttpClient,
) -> PreviewCheckResult:
    if not public_url:
        # Missing public_url is already coded by package_metadata.
        return PreviewCheckResult(status=CHECK_SKIPPED)

    if not _is_https(public_url):
        return PreviewCheckResult(
            status=CHECK_FAILED,
            codes=[LINKEDIN_PREVIEW_VALIDATION_PUBLIC_URL_UNREACHABLE],
            detail={"reason": "public_url_not_https"},
        )

    response = http_client.fetch_document(public_url, timeout=HTTP_TIMEOUT_SECONDS)
    if not response.reachable:
        return PreviewCheckResult(
            status=CHECK_FAILED,
            codes=[LINKEDIN_PREVIEW_VALIDATION_PUBLIC_URL_UNREACHABLE],
            detail={"http_status": response.status_code},
        )

    og_tags = extract_og_tags(response.text)
    codes: list[str] = []
    expectations = [
        ("og:title", article_title, LINKEDIN_PREVIEW_VALIDATION_OG_TITLE_MISMATCH),
        (
            "og:description",
            article_description,
            LINKEDIN_PREVIEW_VALIDATION_OG_DESCRIPTION_MISMATCH,
        ),
        ("og:image", public_image_url, LINKEDIN_PREVIEW_VALIDATION_OG_IMAGE_MISMATCH),
    ]
    missing_tags = False
    for tag_name, expected, mismatch_code in expectations:
        if expected is None:
            # Missing recorded metadata is already coded by package_metadata.
            continue
        served = og_tags.get(tag_name)
        if served is None:
            missing_tags = True
            continue
        if _normalize_text(served) != _normalize_text(expected):
            codes.append(mismatch_code)

    if missing_tags:
        codes.insert(0, LINKEDIN_PREVIEW_VALIDATION_OG_TAGS_MISSING)

    if codes:
        return PreviewCheckResult(status=CHECK_FAILED, codes=codes)
    return PreviewCheckResult(status=CHECK_PASSED)


def _check_public_image_availability(
    *,
    public_image_url: str | None,
    http_client: PreviewHttpClient,
) -> PreviewCheckResult:
    if not public_image_url:
        # Missing image URL is already coded by package_metadata.
        return PreviewCheckResult(status=CHECK_SKIPPED)

    if not _is_https(public_image_url):
        return PreviewCheckResult(
            status=CHECK_FAILED,
            codes=[LINKEDIN_PREVIEW_VALIDATION_PUBLIC_IMAGE_UNREACHABLE],
            detail={"reason": "public_image_url_not_https"},
        )

    response = http_client.fetch_headers(
        public_image_url, timeout=HTTP_TIMEOUT_SECONDS
    )
    if not response.reachable:
        return PreviewCheckResult(
            status=CHECK_FAILED,
            codes=[LINKEDIN_PREVIEW_VALIDATION_PUBLIC_IMAGE_UNREACHABLE],
            detail={"http_status": response.status_code},
        )

    content_type = (response.content_type or "").split(";")[0].strip().lower()
    if not content_type.startswith("image/"):
        return PreviewCheckResult(
            status=CHECK_FAILED,
            codes=[LINKEDIN_PREVIEW_VALIDATION_PUBLIC_IMAGE_NOT_IMAGE],
            detail={"content_type": content_type or None},
        )

    return PreviewCheckResult(status=CHECK_PASSED)


def _aggregate_codes(checks: dict[str, PreviewCheckResult]) -> list[str]:
    codes: list[str] = []
    for check in checks.values():
        for code in check.codes:
            if code not in codes:
                codes.append(code)
    return codes


def _overall_status(checks: dict[str, PreviewCheckResult]) -> str:
    if any(check.status == CHECK_FAILED for check in checks.values()):
        return VALIDATION_FAILED
    return VALIDATION_PASSED


def validate_linkedin_article_preview(
    base_path: Path,
    *,
    campaign_id: str,
    dry_run: bool = True,
    environ: dict[str, str] | None = None,
    http_client: PreviewHttpClient | None = None,
) -> PreviewValidationResult:
    """Verify article preview inputs for one campaign with a generated package."""
    campaign = read_campaign_metadata(base_path, campaign_id)
    if campaign is None:
        return PreviewValidationResult(
            status=VALIDATION_BLOCKED,
            campaign_id=campaign_id,
            dry_run=dry_run,
            codes=[LINKEDIN_PREVIEW_VALIDATION_CAMPAIGN_NOT_FOUND],
        )

    linkedin_package = campaign.get("linkedin_package")
    if not isinstance(linkedin_package, dict) or not linkedin_package:
        return PreviewValidationResult(
            status=VALIDATION_BLOCKED,
            campaign_id=campaign_id,
            dry_run=dry_run,
            codes=[LINKEDIN_PREVIEW_VALIDATION_PACKAGE_NOT_GENERATED],
        )

    client = http_client or HttpxPreviewHttpClient()
    article_preview = linkedin_package.get("article_preview")
    preview = article_preview if isinstance(article_preview, dict) else {}
    article_title = _non_empty(preview.get("article_title"))
    article_description = _non_empty(preview.get("article_description"))
    public_url = _non_empty(preview.get("public_url"))
    public_image_url = _non_empty(preview.get("public_image_url"))

    checks: dict[str, PreviewCheckResult] = {}
    checks[CHECK_PACKAGE_METADATA] = _check_package_metadata(article_preview)
    checks[CHECK_CHECKOUT_CONSISTENCY] = _check_checkout_consistency(
        campaign,
        article_title=article_title,
        article_description=article_description,
        environ=environ,
    )
    checks[CHECK_LIVE_OG_METADATA] = _check_live_og_metadata(
        public_url=public_url,
        article_title=article_title,
        article_description=article_description,
        public_image_url=public_image_url,
        http_client=client,
    )
    checks[CHECK_PUBLIC_IMAGE_AVAILABILITY] = _check_public_image_availability(
        public_image_url=public_image_url,
        http_client=client,
    )

    result = PreviewValidationResult(
        status=_overall_status(checks),
        campaign_id=campaign_id,
        dry_run=dry_run,
        checks=checks,
        codes=_aggregate_codes(checks),
        public_url=public_url,
        public_image_url=public_image_url,
    )

    if not dry_run:
        campaign[EVIDENCE_FIELD] = {
            "status": result.status,
            "checks": {name: check.to_dict() for name, check in checks.items()},
            "codes": list(result.codes),
            "validated_at_utc": utc_now_iso(),
            "public_url": public_url,
            "public_image_url": public_image_url,
        }
        write_result = write_campaign_metadata(base_path, campaign_id, campaign)
        result.metadata_written = write_result.written
        result.metadata_error_code = write_result.error_code

    return result
