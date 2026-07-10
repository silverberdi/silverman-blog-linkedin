"""LinkedIn article preview image metadata for Flow A package generation."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from silverman_blog_linkedin.github_pages_publish import (
    DEFAULT_SITE_URL,
    ENV_REPO_PATH,
    ENV_SITE_URL,
    IMAGES_RELATIVE,
    _split_frontmatter,
    public_blog_image_relative,
)

ARTICLE_PREVIEW_AVAILABLE = "available"
ARTICLE_PREVIEW_MISSING = "missing"
ARTICLE_PREVIEW_SKIPPED = "skipped"
ARTICLE_PREVIEW_INVALID = "invalid"

LINKEDIN_ARTICLE_PREVIEW_IMAGE_MISSING = "linkedin_article_preview_image_missing"
LINKEDIN_ARTICLE_PREVIEW_IMAGE_INVALID = "linkedin_article_preview_image_invalid"
LINKEDIN_ARTICLE_PREVIEW_PUBLIC_IMAGE_MISSING = "linkedin_article_preview_public_image_missing"
LINKEDIN_ARTICLE_PREVIEW_PUBLIC_REPO_NOT_CONFIGURED = (
    "linkedin_article_preview_public_repo_not_configured"
)

_CANONICAL_IMAGE_PATH_PATTERN = re.compile(
    r"^/assets/images/[a-z0-9]+(?:-[a-z0-9]+)*\.png$"
)


@dataclass
class LinkedInArticlePreviewMetadata:
    status: str
    public_image_url: str | None = None
    public_image_path: str | None = None
    article_title: str | None = None
    article_description: str | None = None
    public_url: str | None = None
    campaign_id: str | None = None
    error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _resolve_site_base_url(
    *,
    source_public_url: str | None,
    site_url: str | None,
    environ: dict[str, str] | None,
) -> str:
    if site_url:
        return site_url.rstrip("/")
    if source_public_url:
        parsed = urlparse(source_public_url.strip())
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    if environ:
        configured = environ.get(ENV_SITE_URL, "").strip().rstrip("/")
        if configured:
            return configured
    return DEFAULT_SITE_URL


def _public_repo_relative_path(public_image_path: str) -> str:
    return public_image_path.lstrip("/")


def _canonical_image_path(public_slug: str) -> str:
    repo_relative = public_blog_image_relative(public_slug)
    return f"/{repo_relative}"


def _resolve_image_path(
    frontmatter: dict[str, Any] | None,
    public_slug: str | None,
) -> str | None:
    if frontmatter:
        image_value = str(frontmatter.get("image", "")).strip()
        if image_value:
            return image_value
    if public_slug:
        return _canonical_image_path(public_slug)
    return None


def _validate_image_path(image_path: str) -> bool:
    return bool(_CANONICAL_IMAGE_PATH_PATTERN.match(image_path))


def build_public_image_url(site_base_url: str, public_image_path: str) -> str:
    normalized_path = (
        public_image_path
        if public_image_path.startswith("/")
        else f"/{public_image_path}"
    )
    return f"{site_base_url.rstrip('/')}{normalized_path}"


def _parse_article_fields(
    markdown_content: str,
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    try:
        frontmatter, _body = _split_frontmatter(markdown_content)
    except Exception:
        return None, None, None
    title = str(frontmatter.get("title", "")).strip() or None
    description = str(frontmatter.get("description", "")).strip() or None
    return frontmatter, title, description


def _public_image_exists(repo_path: Path, public_image_path: str) -> bool:
    candidate = (repo_path / _public_repo_relative_path(public_image_path)).resolve()
    return candidate.is_file()


def resolve_linkedin_article_preview(
    *,
    markdown_content: str,
    campaign: dict[str, Any],
    source_public_url: str,
    site_url: str | None = None,
    environ: dict[str, str] | None = None,
) -> LinkedInArticlePreviewMetadata:
    """Resolve article preview metadata from blog frontmatter and public assets."""
    campaign_id = campaign.get("campaign_id")
    public_slug = campaign.get("public_slug")
    frontmatter, article_title, article_description = _parse_article_fields(
        markdown_content
    )

    image_path = _resolve_image_path(frontmatter, public_slug)
    if not image_path:
        return LinkedInArticlePreviewMetadata(
            status=ARTICLE_PREVIEW_MISSING,
            article_title=article_title,
            article_description=article_description,
            public_url=source_public_url,
            campaign_id=campaign_id,
            error_code=LINKEDIN_ARTICLE_PREVIEW_IMAGE_MISSING,
        )

    if not _validate_image_path(image_path):
        return LinkedInArticlePreviewMetadata(
            status=ARTICLE_PREVIEW_INVALID,
            public_image_path=image_path,
            article_title=article_title,
            article_description=article_description,
            public_url=source_public_url,
            campaign_id=campaign_id,
            error_code=LINKEDIN_ARTICLE_PREVIEW_IMAGE_INVALID,
        )

    site_base_url = _resolve_site_base_url(
        source_public_url=source_public_url,
        site_url=site_url,
        environ=environ,
    )
    public_image_url = build_public_image_url(site_base_url, image_path)

    repo_raw = (environ or {}).get(ENV_REPO_PATH, "").strip()
    if not repo_raw:
        return LinkedInArticlePreviewMetadata(
            status=ARTICLE_PREVIEW_SKIPPED,
            public_image_url=public_image_url,
            public_image_path=image_path,
            article_title=article_title,
            article_description=article_description,
            public_url=source_public_url,
            campaign_id=campaign_id,
            error_code=LINKEDIN_ARTICLE_PREVIEW_PUBLIC_REPO_NOT_CONFIGURED,
        )

    repo_path = Path(repo_raw).expanduser().resolve()
    images_dir = repo_path / IMAGES_RELATIVE
    if not images_dir.is_dir():
        return LinkedInArticlePreviewMetadata(
            status=ARTICLE_PREVIEW_SKIPPED,
            public_image_url=public_image_url,
            public_image_path=image_path,
            article_title=article_title,
            article_description=article_description,
            public_url=source_public_url,
            campaign_id=campaign_id,
            error_code=LINKEDIN_ARTICLE_PREVIEW_PUBLIC_REPO_NOT_CONFIGURED,
        )

    if not _public_image_exists(repo_path, image_path):
        return LinkedInArticlePreviewMetadata(
            status=ARTICLE_PREVIEW_MISSING,
            public_image_url=public_image_url,
            public_image_path=image_path,
            article_title=article_title,
            article_description=article_description,
            public_url=source_public_url,
            campaign_id=campaign_id,
            error_code=LINKEDIN_ARTICLE_PREVIEW_PUBLIC_IMAGE_MISSING,
        )

    return LinkedInArticlePreviewMetadata(
        status=ARTICLE_PREVIEW_AVAILABLE,
        public_image_url=public_image_url,
        public_image_path=image_path,
        article_title=article_title,
        article_description=article_description,
        public_url=source_public_url,
        campaign_id=campaign_id,
    )
