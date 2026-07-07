"""Flow A ready-post editorial validation gate."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.campaign_lifecycle import (
    ACTOR_WORKER,
    FLOW_A,
    STATE_READY,
    STATE_VALIDATED,
    STATE_VALIDATION_FAILED,
    build_initial_campaign_metadata,
    compute_source_content_sha256,
    generate_campaign_id,
    read_campaign_metadata,
    transition_state,
    write_campaign_metadata,
)
from silverman_blog_linkedin.github_pages_publish import (
    DEFAULT_SITE_URL,
    PublishError,
    SLUG_PATTERN,
    _split_frontmatter,
    derive_public_slug,
    public_url,
    validate_slug,
)

READY_RELATIVE_PREFIX = "blog-posts/ready/"
IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".bmp"})

# Blocking error codes
READY_POST_NOT_UNDER_READY = "ready_post_not_under_ready"
READY_POST_NOT_MARKDOWN = "ready_post_not_markdown"
READY_POST_MISSING = "ready_post_missing"
READY_POST_EMPTY = "ready_post_empty"
FRONTMATTER_MISSING = "frontmatter_missing"
FRONTMATTER_INVALID = "frontmatter_invalid"
FRONTMATTER_REQUIRED_FIELD_MISSING = "frontmatter_required_field_missing"
FRONTMATTER_INVALID_DATE = "frontmatter_invalid_date"
FRONTMATTER_INVALID_IMAGE = "frontmatter_invalid_image"
INVALID_PUBLIC_SLUG = "invalid_public_slug"
READY_POST_IMAGE_MISSING = "ready_post_image_missing"
READY_POST_IMAGE_INVALID_EXTENSION = "ready_post_image_invalid_extension"
CONTENT_MISSING_H1 = "content_missing_h1"
CONTENT_TITLE_MISMATCH = "content_title_mismatch"
CONTENT_CONTAINS_TODO = "content_contains_todo"
CONTENT_CONTAINS_SECRET_MARKER = "content_contains_secret_marker"
CONTENT_UNSUPPORTED_LOCAL_IMAGE = "content_unsupported_local_image"
CONTENT_NON_SILVERMAN_PUBLISH_TARGET = "content_non_silverman_publish_target"
CONTENT_EMBEDDED_LINKEDIN_DRAFT = "content_embedded_linkedin_draft"
CAMPAIGN_CONTENT_HASH_CHANGED = "campaign_content_hash_changed"
CAMPAIGN_INVALID_EXISTING_STATE = "campaign_invalid_existing_state"
CAMPAIGN_METADATA_WRITE_FAILED = "campaign_metadata_write_failed"

READY_POST_ERROR_CODES = frozenset(
    {
        READY_POST_NOT_UNDER_READY,
        READY_POST_NOT_MARKDOWN,
        READY_POST_MISSING,
        READY_POST_EMPTY,
        FRONTMATTER_MISSING,
        FRONTMATTER_INVALID,
        FRONTMATTER_REQUIRED_FIELD_MISSING,
        FRONTMATTER_INVALID_DATE,
        FRONTMATTER_INVALID_IMAGE,
        INVALID_PUBLIC_SLUG,
        READY_POST_IMAGE_MISSING,
        READY_POST_IMAGE_INVALID_EXTENSION,
        CONTENT_MISSING_H1,
        CONTENT_TITLE_MISMATCH,
        CONTENT_CONTAINS_TODO,
        CONTENT_CONTAINS_SECRET_MARKER,
        CONTENT_UNSUPPORTED_LOCAL_IMAGE,
        CONTENT_NON_SILVERMAN_PUBLISH_TARGET,
        CONTENT_EMBEDDED_LINKEDIN_DRAFT,
        CAMPAIGN_CONTENT_HASH_CHANGED,
        CAMPAIGN_INVALID_EXISTING_STATE,
        CAMPAIGN_METADATA_WRITE_FAILED,
    }
)

# Warning codes (non-blocking for Flow A user blogs)
WARNING_AI_OPENING = "warning_ai_opening"
WARNING_GENERIC_ENDING = "warning_generic_ending"
WARNING_GENERIC_TRANSITION = "warning_generic_transition"
WARNING_WEAK_CTA = "warning_weak_cta"
WARNING_INFLUENCER_TONE = "warning_influencer_tone"
WARNING_STYLE_DRIFT = "warning_style_drift"

WARNING_CODES = frozenset(
    {
        WARNING_AI_OPENING,
        WARNING_GENERIC_ENDING,
        WARNING_GENERIC_TRANSITION,
        WARNING_WEAK_CTA,
        WARNING_INFLUENCER_TONE,
        WARNING_STYLE_DRIFT,
    }
)

REQUIRED_FRONTMATTER_FIELDS = (
    "title",
    "audience",
    "type",
    "language",
    "layout",
    "date",
    "categories",
    "tags",
    "description",
    "image",
)

TODO_PATTERN = re.compile(r"\b(TODO|FIXME|PLACEHOLDER|TBD)\b", re.IGNORECASE)
SECRET_PATTERNS = (
    re.compile(r"\bapi[_-]?key\s*[:=]", re.IGNORECASE),
    re.compile(r"\bsecret\s*[:=]", re.IGNORECASE),
    re.compile(r"\bpassword\s*[:=]", re.IGNORECASE),
    re.compile(r"\bsk-[a-zA-Z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)
LOCAL_IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
NON_SILVERMAN_PUBLISH_PATTERNS = (
    re.compile(r"publish\s+(?:to|on)\s+(?:medium|dev\.to|substack|hashnode)", re.IGNORECASE),
    re.compile(r"post\s+(?:to|on)\s+(?:medium|dev\.to|substack|linkedin)", re.IGNORECASE),
    re.compile(r"https?://(?:medium\.com|dev\.to|substack\.com)", re.IGNORECASE),
)
LINKEDIN_DRAFT_PATTERNS = (
    re.compile(r"##\s*LinkedIn\s+(?:draft|post|variant)", re.IGNORECASE),
    re.compile(r"variant:\s*(?:executive-recruiter|technical-architect|short-provocative)", re.IGNORECASE),
    re.compile(r"linkedin-posts/(?:review|approved)/", re.IGNORECASE),
)

AI_OPENING_PATTERNS = (
    re.compile(r"in today'?s fast[- ]paced world", re.IGNORECASE),
    re.compile(r"in the ever[- ]evolving landscape", re.IGNORECASE),
    re.compile(r"in modern software development", re.IGNORECASE),
    re.compile(r"in the digital age", re.IGNORECASE),
    re.compile(r"as technology continues to evolve", re.IGNORECASE),
    re.compile(r"let'?s dive into", re.IGNORECASE),
    re.compile(r"here are \d+ reasons why", re.IGNORECASE),
    re.compile(r"have you ever wondered", re.IGNORECASE),
    re.compile(r"it'?s no secret that", re.IGNORECASE),
    re.compile(r"now more than ever", re.IGNORECASE),
)

GENERIC_ENDING_PATTERNS = (
    re.compile(r"what are your thoughts\??", re.IGNORECASE),
    re.compile(r"agree or disagree\??", re.IGNORECASE),
    re.compile(r"comment below", re.IGNORECASE),
    re.compile(r"let me know in the comments", re.IGNORECASE),
    re.compile(r"the future belongs to", re.IGNORECASE),
    re.compile(r"the possibilities are endless", re.IGNORECASE),
    re.compile(r"follow for more insights", re.IGNORECASE),
    re.compile(r"tag someone who needs this", re.IGNORECASE),
)

GENERIC_TRANSITION_PATTERN = re.compile(
    r"\b(Moreover|Furthermore|Additionally|Ultimately|"
    r"It is important to note|That being said|At the end of the day)\b",
    re.IGNORECASE,
)

INFLUENCER_TONE_PATTERN = re.compile(
    r"\b(game[- ]changer|revolutionize|unlock|leverage|cutting[- ]edge|"
    r"holistic|empower|paradigm shift|best[- ]in[- ]class)\b",
    re.IGNORECASE,
)

STYLE_DRIFT_PATTERN = re.compile(
    r"\b(delve|crucial|robust|landscape|tapestry|synergy|transformation journey)\b",
    re.IGNORECASE,
)

WEAK_CTA_PATTERN = re.compile(
    r"\b(follow me|connect with me|dm me|reach out to me)\b",
    re.IGNORECASE,
)

NORMALIZE_TITLE_PATTERN = re.compile(r"[^\w\s]+")
WHITESPACE_PATTERN = re.compile(r"\s+")

STATES_BEYOND_VALIDATED = frozenset(
    {
        "blog_publish_pending",
        "blog_published",
        "derivatives_pending",
        "derivatives_generated",
        "distribution_scheduled",
        "distribution_complete",
        "flow_a_complete",
    }
)


@dataclass
class ReadyPostValidationResult:
    ok: bool
    source_relative_path: str
    campaign_id: str | None = None
    state: str | None = None
    source_slug: str | None = None
    public_slug: str | None = None
    publication_date: str | None = None
    image_relative_path: str | None = None
    source_content_sha256: str | None = None
    source_public_url: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata_written: bool = False
    metadata_error_code: str | None = None


def _normalize_relative_path(source_relative_path: str) -> str:
    normalized = source_relative_path.replace("\\", "/").lstrip("/")
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    return normalized


def _validate_path_and_file(
    base_path: Path, source_relative_path: str
) -> tuple[list[str], Path | None, str | None]:
    errors: list[str] = []
    normalized = _normalize_relative_path(source_relative_path)
    ready_dir = (base_path / "blog-posts" / "ready").resolve()

    if not normalized.startswith(READY_RELATIVE_PREFIX):
        errors.append(READY_POST_NOT_UNDER_READY)
        return errors, None, None

    if not normalized.endswith(".md"):
        errors.append(READY_POST_NOT_MARKDOWN)
        return errors, None, None

    resolved = (base_path / normalized).resolve()
    try:
        resolved.relative_to(ready_dir)
    except ValueError:
        errors.append(READY_POST_NOT_UNDER_READY)
        return errors, None, None

    if not resolved.is_file():
        errors.append(READY_POST_MISSING)
        return errors, None, None

    source_slug = resolved.stem
    return errors, resolved, source_slug


def _validate_slugs(source_slug: str) -> tuple[list[str], str | None]:
    errors: list[str] = []
    try:
        validate_slug(source_slug, label="source slug")
    except PublishError:
        errors.append(INVALID_PUBLIC_SLUG)
        return errors, None

    public_slug = derive_public_slug(source_slug)
    if not SLUG_PATTERN.match(public_slug):
        errors.append(INVALID_PUBLIC_SLUG)
        return errors, None

    return errors, public_slug


def _validate_image(
    base_path: Path, source_slug: str
) -> tuple[list[str], str | None]:
    errors: list[str] = []
    ready_dir = base_path / "blog-posts" / "ready"
    expected_png = ready_dir / f"{source_slug}.png"
    image_relative = f"{READY_RELATIVE_PREFIX}{source_slug}.png"

    if expected_png.is_file():
        return errors, image_relative

    same_basename_other: list[Path] = []
    if ready_dir.is_dir():
        for candidate in ready_dir.iterdir():
            if not candidate.is_file():
                continue
            if candidate.stem == source_slug and candidate.suffix.lower() != ".png":
                if candidate.suffix.lower() in IMAGE_EXTENSIONS:
                    same_basename_other.append(candidate)

    if same_basename_other:
        errors.append(READY_POST_IMAGE_INVALID_EXTENSION)
    else:
        errors.append(READY_POST_IMAGE_MISSING)

    return errors, None


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _normalize_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _extract_publication_date(raw_date: Any) -> str | None:
    if _is_blank(raw_date):
        return None
    raw = str(raw_date).strip()
    if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
        candidate = raw[:10]
        try:
            datetime.strptime(candidate, "%Y-%m-%d")
            return candidate
        except ValueError:
            return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed.date().isoformat()
    except ValueError:
        return None


def _parse_frontmatter(content: str) -> tuple[list[str], dict[str, Any] | None, str]:
    if not content.startswith("---"):
        return [FRONTMATTER_MISSING], None, content

    try:
        frontmatter, body = _split_frontmatter(content)
    except PublishError:
        return [FRONTMATTER_INVALID], None, content

    if not frontmatter:
        return [FRONTMATTER_MISSING], None, body

    return [], frontmatter, body


def _validate_frontmatter_fields(
    frontmatter: dict[str, Any], public_slug: str
) -> tuple[list[str], str | None]:
    errors: list[str] = []

    for field_name in REQUIRED_FRONTMATTER_FIELDS:
        if field_name in ("categories", "tags"):
            values = _normalize_list(frontmatter.get(field_name))
            if not values:
                errors.append(FRONTMATTER_REQUIRED_FIELD_MISSING)
        elif _is_blank(frontmatter.get(field_name)):
            errors.append(FRONTMATTER_REQUIRED_FIELD_MISSING)

    if errors:
        return errors, None

    if str(frontmatter.get("type", "")).strip() != "blog-post":
        errors.append(FRONTMATTER_REQUIRED_FIELD_MISSING)
    if str(frontmatter.get("language", "")).strip() != "en":
        errors.append(FRONTMATTER_REQUIRED_FIELD_MISSING)
    if str(frontmatter.get("layout", "")).strip() != "post":
        errors.append(FRONTMATTER_REQUIRED_FIELD_MISSING)

    expected_image = f"/assets/images/{public_slug}.png"
    if str(frontmatter.get("image", "")).strip() != expected_image:
        errors.append(FRONTMATTER_INVALID_IMAGE)

    publication_date = _extract_publication_date(frontmatter.get("date"))
    if publication_date is None:
        errors.append(FRONTMATTER_INVALID_DATE)

    return errors, publication_date


def _normalize_title(text: str) -> str:
    lowered = text.lower().strip()
    cleaned = NORMALIZE_TITLE_PATTERN.sub(" ", lowered)
    return WHITESPACE_PATTERN.sub(" ", cleaned).strip()


def _titles_match(frontmatter_title: str, h1_title: str) -> bool:
    normalized_title = _normalize_title(frontmatter_title)
    normalized_h1 = _normalize_title(h1_title)
    if not normalized_title or not normalized_h1:
        return False
    if normalized_title == normalized_h1:
        return True
    if normalized_title in normalized_h1 or normalized_h1 in normalized_title:
        return True

    title_tokens = set(normalized_title.split())
    h1_tokens = set(normalized_h1.split())
    if not title_tokens or not h1_tokens:
        return False
    overlap = len(title_tokens & h1_tokens)
    ratio = overlap / max(len(title_tokens), len(h1_tokens))
    return ratio >= 0.6


def _extract_h1(body: str) -> str | None:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            return stripped[2:].strip()
    return None


def _validate_content_blocking(
    *,
    frontmatter: dict[str, Any],
    body: str,
    full_content: str,
) -> list[str]:
    errors: list[str] = []
    combined = f"{full_content}\n{frontmatter}"

    if not body.strip():
        errors.append(READY_POST_EMPTY)
        return errors

    h1 = _extract_h1(body)
    if h1 is None:
        errors.append(CONTENT_MISSING_H1)
    else:
        title = str(frontmatter.get("title", ""))
        if not _titles_match(title, h1):
            errors.append(CONTENT_TITLE_MISMATCH)

    if TODO_PATTERN.search(combined):
        errors.append(CONTENT_CONTAINS_TODO)

    for pattern in SECRET_PATTERNS:
        if pattern.search(combined):
            errors.append(CONTENT_CONTAINS_SECRET_MARKER)
            break

    for match in LOCAL_IMAGE_PATTERN.finditer(body):
        target = match.group(1).strip()
        if target.startswith(("http://", "https://", "/assets/images/")):
            continue
        errors.append(CONTENT_UNSUPPORTED_LOCAL_IMAGE)
        break

    for pattern in NON_SILVERMAN_PUBLISH_PATTERNS:
        if pattern.search(combined):
            errors.append(CONTENT_NON_SILVERMAN_PUBLISH_TARGET)
            break

    for pattern in LINKEDIN_DRAFT_PATTERNS:
        if pattern.search(combined):
            errors.append(CONTENT_EMBEDDED_LINKEDIN_DRAFT)
            break

    return errors


def _collect_editorial_warnings(body: str) -> list[str]:
    warnings: list[str] = []
    body_stripped = body.strip()
    if not body_stripped:
        return warnings

    opening_window = body_stripped[:500]
    for pattern in AI_OPENING_PATTERNS:
        if pattern.search(opening_window):
            warnings.append(WARNING_AI_OPENING)
            break

    closing_window = body_stripped[-500:]
    for pattern in GENERIC_ENDING_PATTERNS:
        if pattern.search(closing_window):
            warnings.append(WARNING_GENERIC_ENDING)
            break

    transition_matches = GENERIC_TRANSITION_PATTERN.findall(body_stripped)
    if len(transition_matches) >= 3:
        warnings.append(WARNING_GENERIC_TRANSITION)

    if WEAK_CTA_PATTERN.search(body_stripped):
        warnings.append(WARNING_WEAK_CTA)

    if INFLUENCER_TONE_PATTERN.search(body_stripped):
        warnings.append(WARNING_INFLUENCER_TONE)

    if STYLE_DRIFT_PATTERN.search(body_stripped):
        warnings.append(WARNING_STYLE_DRIFT)

    return warnings


def _check_existing_campaign(
    *,
    base_path: Path,
    campaign_id: str,
    content_hash: str,
) -> tuple[list[str], dict[str, Any] | None, bool]:
    """Return blocking errors, existing campaign, and idempotent-success flag."""
    existing = read_campaign_metadata(base_path, campaign_id)
    if existing is None:
        return [], None, False

    stored_hash = existing.get("source_content_sha256")
    if stored_hash and stored_hash != content_hash:
        return [CAMPAIGN_CONTENT_HASH_CHANGED], existing, False

    state = existing.get("state")
    if state in STATES_BEYOND_VALIDATED:
        return [CAMPAIGN_INVALID_EXISTING_STATE], existing, False

    if state == STATE_VALIDATION_FAILED:
        return [CAMPAIGN_INVALID_EXISTING_STATE], existing, False

    if state == STATE_VALIDATED and stored_hash == content_hash:
        return [], existing, True

    return [], existing, False


def _persist_campaign_metadata(
    *,
    base_path: Path,
    campaign_id: str,
    source_slug: str,
    public_slug: str,
    source_relative_path: str,
    image_relative_path: str,
    source_content: str,
    publication_date: str,
    source_public_url: str | None,
    warnings: list[str],
    errors: list[str],
    existing: dict[str, Any] | None,
) -> tuple[bool, str | None, str | None]:
    blocking_errors = [code for code in errors if code in READY_POST_ERROR_CODES]
    ok = len(blocking_errors) == 0

    if existing is None:
        campaign = build_initial_campaign_metadata(
            flow=FLOW_A,
            source_slug=source_slug,
            public_slug=public_slug,
            source_relative_path=source_relative_path,
            image_relative_path=image_relative_path,
            source_content=source_content,
            publication_date=publication_date,
        )
    else:
        campaign = dict(existing)
        campaign["source_slug"] = source_slug
        campaign["public_slug"] = public_slug
        campaign["source_relative_path"] = source_relative_path
        campaign["image_relative_path"] = image_relative_path
        campaign["source_content_sha256"] = compute_source_content_sha256(source_content)
        campaign["publication_date"] = publication_date

    if source_public_url:
        campaign["source_public_url"] = source_public_url

    if ok:
        campaign["warnings"] = list(warnings)
        transition_state(
            campaign,
            STATE_VALIDATED,
            reason="Editorial validation passed",
            actor=ACTOR_WORKER,
        )
    else:
        primary_error = blocking_errors[0]
        if campaign.get("state") == STATE_READY:
            transition_state(
                campaign,
                STATE_VALIDATION_FAILED,
                reason="Editorial validation failed",
                actor=ACTOR_WORKER,
                error_code=primary_error,
            )
        else:
            return False, CAMPAIGN_INVALID_EXISTING_STATE, campaign.get("state")

    write_result = write_campaign_metadata(base_path, campaign_id, campaign)
    if not write_result.written:
        return False, write_result.error_code, campaign.get("state")

    return True, None, campaign.get("state")


def validate_ready_post(
    base_path: Path,
    source_relative_path: str,
    *,
    site_url: str = DEFAULT_SITE_URL,
) -> ReadyPostValidationResult:
    """Validate one ready blog post and update campaign metadata when possible."""
    normalized_path = _normalize_relative_path(source_relative_path)
    result = ReadyPostValidationResult(
        ok=False,
        source_relative_path=normalized_path,
        errors=[],
        warnings=[],
    )

    path_errors, resolved_file, source_slug = _validate_path_and_file(
        base_path, normalized_path
    )
    result.errors.extend(path_errors)
    if path_errors or resolved_file is None or source_slug is None:
        return result

    result.source_slug = source_slug

    slug_errors, public_slug = _validate_slugs(source_slug)
    result.errors.extend(slug_errors)
    if slug_errors or public_slug is None:
        return result

    result.public_slug = public_slug

    try:
        content = resolved_file.read_text(encoding="utf-8")
    except OSError:
        result.errors.append(READY_POST_MISSING)
        return result

    fm_errors, frontmatter, body = _parse_frontmatter(content)
    result.errors.extend(fm_errors)

    image_errors, image_relative_path = _validate_image(base_path, source_slug)
    result.errors.extend(image_errors)
    if image_relative_path:
        result.image_relative_path = image_relative_path

    publication_date: str | None = None
    if frontmatter is not None:
        field_errors, publication_date = _validate_frontmatter_fields(
            frontmatter, public_slug
        )
        result.errors.extend(field_errors)
        if publication_date:
            result.publication_date = publication_date

    result.source_content_sha256 = compute_source_content_sha256(content)

    campaign_id: str | None = None
    existing_campaign: dict[str, Any] | None = None
    idempotent_success = False

    if publication_date and public_slug:
        try:
            campaign_id = generate_campaign_id(FLOW_A, publication_date, public_slug)
            result.campaign_id = campaign_id
        except Exception:
            campaign_id = None

        if campaign_id and result.source_content_sha256:
            campaign_errors, existing_campaign, idempotent_success = (
                _check_existing_campaign(
                    base_path=base_path,
                    campaign_id=campaign_id,
                    content_hash=result.source_content_sha256,
                )
            )
            result.errors.extend(campaign_errors)

    if frontmatter is not None and not fm_errors:
        content_errors = _validate_content_blocking(
            frontmatter=frontmatter,
            body=body,
            full_content=content,
        )
        result.errors.extend(content_errors)
        result.warnings.extend(_collect_editorial_warnings(body))

    blocking_errors = [
        code for code in result.errors if code in READY_POST_ERROR_CODES
    ]
    result.ok = len(blocking_errors) == 0

    guardrail_errors = {
        CAMPAIGN_CONTENT_HASH_CHANGED,
        CAMPAIGN_INVALID_EXISTING_STATE,
    }
    if guardrail_errors.intersection(result.errors):
        result.ok = False
        return result

    if idempotent_success and existing_campaign is not None:
        result.ok = True
        result.state = existing_campaign.get("state")
        result.source_public_url = existing_campaign.get("source_public_url")
        result.metadata_written = False
        return result

    source_public_url: str | None = None
    if publication_date and public_slug and result.ok:
        pub_date = date.fromisoformat(publication_date)
        source_public_url = public_url(site_url, pub_date, public_slug)
        result.source_public_url = source_public_url

    if campaign_id and publication_date:
        can_persist = result.ok or (
            existing_campaign is not None
            and existing_campaign.get("state") == STATE_READY
        ) or (existing_campaign is None and blocking_errors)
        if can_persist:
            metadata_written, metadata_error_code, final_state = (
                _persist_campaign_metadata(
                    base_path=base_path,
                    campaign_id=campaign_id,
                    source_slug=source_slug,
                    public_slug=public_slug,
                    source_relative_path=normalized_path,
                    image_relative_path=image_relative_path
                    or f"{READY_RELATIVE_PREFIX}{source_slug}.png",
                    source_content=content,
                    publication_date=publication_date,
                    source_public_url=source_public_url,
                    warnings=result.warnings,
                    errors=blocking_errors,
                    existing=existing_campaign,
                )
            )
            result.metadata_written = metadata_written
            result.metadata_error_code = metadata_error_code
            if final_state:
                result.state = final_state
            if metadata_error_code and not metadata_written:
                if metadata_error_code not in result.errors:
                    result.errors.append(metadata_error_code)
                result.ok = False

    return result
