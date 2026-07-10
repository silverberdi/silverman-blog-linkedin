"""Flow A blog publish orchestration."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.blog_image_generation import (
    BLOG_IMAGE_GENERATION_FAILED,
    ensure_editorial_blog_image,
    handoff_public_blog_image,
    recompute_source_hash_after_generation,
)
from silverman_blog_linkedin.comfyui_config import load_comfyui_settings
from silverman_blog_linkedin.comfyui_client import ComfyUIClientProtocol
from silverman_blog_linkedin.campaign_lifecycle import (
    ACTOR_WORKER,
    FLOW_A,
    FLOW_B,
    POST_SCHEDULE_SOURCE_RESOLUTION_STATES,
    STATE_BLOG_PUBLISH_PENDING,
    STATE_BLOG_PUBLISHED,
    STATE_DERIVATIVES_GENERATED,
    STATE_DERIVATIVES_PENDING,
    STATE_DISTRIBUTION_COMPLETE,
    STATE_DISTRIBUTION_SCHEDULED,
    STATE_ERROR,
    STATE_FLOW_A_COMPLETE,
    STATE_READY,
    STATE_VALIDATED,
    STATE_VALIDATION_FAILED,
    _append_state_history,
    build_blog_publish_idempotency_key,
    compute_source_content_sha256,
    find_campaign_by_source_path,
    generate_campaign_id,
    read_campaign_metadata,
    resolve_campaign_source_paths,
    transition_state,
    write_campaign_metadata,
)
from silverman_blog_linkedin.github_pages_publish import (
    BLOG_IMAGE_PUBLIC_ASSET_HANDOFF_FAILED,
    DEFAULT_SITE_URL,
    ENV_REPO_PATH,
    PublishError,
    PublishPlan,
    _split_frontmatter,
    load_config,
    public_url,
    render_expected_public_post,
    resolve_public_slug,
    run_publish,
    validate_repo_layout,
)
from silverman_blog_linkedin.ready_post_validation import (
    CAMPAIGN_CONTENT_HASH_CHANGED,
    CAMPAIGN_METADATA_WRITE_FAILED,
    CONTENT_CONTAINS_TODO,
    ALLOWED_PUBLISH_SOURCE_PREFIXES,
    validate_ready_post,
    validate_ready_post_pre_generation,
)
from silverman_blog_linkedin.run_metadata import utc_now_iso

BLOG_PUBLISH_VALIDATION_FAILED = "blog_publish_validation_failed"
BLOG_PUBLISH_INVALID_CAMPAIGN_STATE = "blog_publish_invalid_campaign_state"
BLOG_PUBLISH_CONTENT_HASH_CHANGED = "blog_publish_content_hash_changed"
BLOG_PUBLISH_TARGET_EXISTS = "blog_publish_target_exists"
BLOG_PUBLISH_FAILED = "blog_publish_failed"
BLOG_PUBLISH_METADATA_WRITE_FAILED = "blog_publish_metadata_write_failed"
BLOG_PUBLISH_PUBLIC_REPO_NOT_CONFIGURED = "blog_publish_public_repo_not_configured"
BLOG_PUBLISH_SOURCE_NOT_READY = "blog_publish_source_not_ready"
BLOG_PUBLISH_FLOW_B_NOT_ALLOWED = "blog_publish_flow_b_not_allowed"

BLOG_PUBLISH_HASH_RECONCILIATION_FAILED = "blog_publish_hash_reconciliation_failed"

BLOG_PUBLISH_ERROR_CODES = frozenset(
    {
        BLOG_PUBLISH_VALIDATION_FAILED,
        BLOG_PUBLISH_INVALID_CAMPAIGN_STATE,
        BLOG_PUBLISH_CONTENT_HASH_CHANGED,
        BLOG_PUBLISH_TARGET_EXISTS,
        BLOG_PUBLISH_FAILED,
        BLOG_PUBLISH_METADATA_WRITE_FAILED,
        BLOG_PUBLISH_PUBLIC_REPO_NOT_CONFIGURED,
        BLOG_PUBLISH_SOURCE_NOT_READY,
        BLOG_PUBLISH_FLOW_B_NOT_ALLOWED,
        BLOG_PUBLISH_HASH_RECONCILIATION_FAILED,
    }
)

INVALID_PUBLISH_STATES = frozenset(
    {
        STATE_VALIDATION_FAILED,
        STATE_ERROR,
        STATE_DERIVATIVES_PENDING,
        STATE_DERIVATIVES_GENERATED,
        STATE_DISTRIBUTION_SCHEDULED,
        STATE_DISTRIBUTION_COMPLETE,
        STATE_FLOW_A_COMPLETE,
    }
)

RESUMABLE_WITHOUT_VALIDATION = frozenset({STATE_BLOG_PUBLISH_PENDING})

SKIP_VALIDATION_STATES = frozenset({STATE_BLOG_PUBLISH_PENDING, STATE_ERROR})

RECONCILABLE_PUBLISH_STATES = frozenset(
    {STATE_VALIDATED, STATE_BLOG_PUBLISH_PENDING, STATE_ERROR}
)

STALE_PUBLISH_ERROR_CODES = frozenset(
    {
        BLOG_PUBLISH_TARGET_EXISTS,
        BLOG_PUBLISH_PUBLIC_REPO_NOT_CONFIGURED,
        BLOG_PUBLISH_INVALID_CAMPAIGN_STATE,
    }
)

RECONCILED_FROM_ERROR_WARNING = "blog_publish_reconciled_from_error_state"

RECONCILIATION_SKIPPED_STATE_NOT_ALLOWED = (
    "blog_publish_reconciliation_skipped_state_not_allowed"
)
RECONCILIATION_SKIPPED_SOURCE_MISMATCH = (
    "blog_publish_reconciliation_skipped_source_mismatch"
)
RECONCILIATION_SKIPPED_HASH_MISMATCH = (
    "blog_publish_reconciliation_skipped_hash_mismatch"
)
RECONCILIATION_SKIPPED_MISSING_PUBLIC_POST = (
    "blog_publish_reconciliation_skipped_missing_public_post"
)
RECONCILIATION_SKIPPED_MISSING_PUBLIC_IMAGE = (
    "blog_publish_reconciliation_skipped_missing_public_image"
)
RECONCILIATION_SKIPPED_PUBLIC_CONTENT_MISMATCH = (
    "blog_publish_reconciliation_skipped_public_content_mismatch"
)
RECONCILIATION_SKIPPED_PUBLIC_IMAGE_MISMATCH = (
    "blog_publish_reconciliation_skipped_public_image_mismatch"
)
RECONCILIATION_SKIPPED_IDEMPOTENCY_MISMATCH = (
    "blog_publish_reconciliation_skipped_idempotency_mismatch"
)


@dataclass(frozen=True)
class PublicTargetComparison:
    expected_post_relative: str
    actual_post_relative: str
    expected_image_relative: str
    actual_image_relative: str
    post_matches: bool
    image_matches: bool
    expected_post_sha256: str | None = None
    actual_post_sha256: str | None = None
    expected_image_sha256: str | None = None
    actual_image_sha256: str | None = None

    @property
    def matches(self) -> bool:
        return self.post_matches and self.image_matches

    def diagnostics(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "reconciliation_expected_post_relative_path": self.expected_post_relative,
            "reconciliation_actual_post_relative_path": self.actual_post_relative,
        }
        if self.expected_post_sha256 is not None:
            payload["reconciliation_expected_post_sha256"] = self.expected_post_sha256
        if self.actual_post_sha256 is not None:
            payload["reconciliation_actual_post_sha256"] = self.actual_post_sha256
        if self.expected_image_sha256 is not None:
            payload["reconciliation_expected_image_sha256"] = self.expected_image_sha256
        if self.actual_image_sha256 is not None:
            payload["reconciliation_actual_image_sha256"] = self.actual_image_sha256
        return payload


@dataclass
class BlogPublishResult:
    status: str
    source_relative_path: str
    campaign_id: str | None = None
    state: str | None = None
    source_slug: str | None = None
    public_slug: str | None = None
    publication_date: str | None = None
    image_relative_path: str | None = None
    source_public_url: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    validation: dict[str, Any] = field(default_factory=dict)
    blog_publish: dict[str, Any] = field(default_factory=dict)
    blog_image_generation: dict[str, Any] = field(default_factory=dict)
    metadata_written: bool = False
    metadata_error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_relative_path(source_relative_path: str) -> str:
    normalized = source_relative_path.replace("\\", "/").lstrip("/")
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    return normalized


def _extract_publication_date(raw_date: Any) -> str | None:
    if raw_date is None or (isinstance(raw_date, str) and raw_date.strip() == ""):
        return None
    raw = str(raw_date).strip()
    if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
        candidate = raw[:10]
        try:
            date.fromisoformat(candidate)
            return candidate
        except ValueError:
            return None
    return None


@dataclass(frozen=True)
class PreflightContext:
    source_relative_path: str
    source_slug: str | None
    public_slug: str | None
    publication_date: str | None
    source_content_sha256: str | None
    campaign_id: str | None
    expected_idempotency_key: str | None
    image_relative_path: str | None
    errors: tuple[str, ...]


def _preflight_from_campaign_source(
    base_path: Path,
    campaign: dict[str, Any],
    *,
    requested_source_relative_path: str,
) -> PreflightContext | None:
    """Build preflight context from campaign metadata when ready copy is absent."""
    md_relative, image_relative = resolve_campaign_source_paths(campaign)
    if not md_relative:
        return None

    resolved = (base_path / md_relative).resolve()
    if not resolved.is_file():
        return None

    try:
        content = resolved.read_text(encoding="utf-8")
    except OSError:
        return None

    source_slug = campaign.get("source_slug") or resolved.stem
    public_slug = campaign.get("public_slug")
    publication_date = campaign.get("publication_date")
    content_hash = campaign.get("source_content_sha256") or compute_source_content_sha256(
        content
    )
    campaign_id = campaign.get("campaign_id")
    expected_key = None
    if publication_date and public_slug and source_slug and content_hash:
        try:
            expected_key = build_blog_publish_idempotency_key(
                source_slug=source_slug,
                public_slug=public_slug,
                publication_date=publication_date,
                source_content_sha256=content_hash,
            )
        except Exception:
            expected_key = None

    return PreflightContext(
        source_relative_path=requested_source_relative_path,
        source_slug=source_slug,
        public_slug=public_slug,
        publication_date=publication_date,
        source_content_sha256=content_hash,
        campaign_id=campaign_id,
        expected_idempotency_key=expected_key,
        image_relative_path=image_relative,
        errors=(),
    )


def _try_post_schedule_idempotent_publish(
    base_path: Path,
    source_relative_path: str,
) -> BlogPublishResult | None:
    """Return completed publish when campaign already progressed past ready source."""
    normalized = _normalize_relative_path(source_relative_path)
    campaign = find_campaign_by_source_path(base_path, normalized)
    if campaign is None or campaign.get("flow") != FLOW_A:
        return None

    state = campaign.get("state")
    if state not in (
        STATE_BLOG_PUBLISHED,
        *POST_SCHEDULE_SOURCE_RESOLUTION_STATES,
        STATE_FLOW_A_COMPLETE,
    ):
        return None

    if not campaign.get("source_public_url"):
        return None

    preflight = _preflight_from_campaign_source(
        base_path,
        campaign,
        requested_source_relative_path=normalized,
    )
    if preflight is None:
        return None

    if state == STATE_BLOG_PUBLISHED and preflight.expected_idempotency_key:
        if _check_idempotent_already_published(
            campaign,
            expected_idempotency_key=preflight.expected_idempotency_key,
            source_content_sha256=preflight.source_content_sha256 or "",
        ):
            return _already_published_result(preflight, campaign)

    if state in POST_SCHEDULE_SOURCE_RESOLUTION_STATES or state == STATE_FLOW_A_COMPLETE:
        return _already_published_result(preflight, campaign)

    return None


def _preflight_inspect(
    base_path: Path,
    source_relative_path: str,
    *,
    public_slug_override: str | None,
) -> PreflightContext:
    normalized = _normalize_relative_path(source_relative_path)
    errors: list[str] = []

    allowed_prefixes = ALLOWED_PUBLISH_SOURCE_PREFIXES
    matched_prefix = None
    for prefix in allowed_prefixes:
        if normalized.startswith(prefix):
            matched_prefix = prefix
            break

    if matched_prefix is None:
        errors.append(BLOG_PUBLISH_SOURCE_NOT_READY)
        return PreflightContext(
            source_relative_path=normalized,
            source_slug=None,
            public_slug=None,
            publication_date=None,
            source_content_sha256=None,
            campaign_id=None,
            expected_idempotency_key=None,
            image_relative_path=None,
            errors=tuple(errors),
        )

    if not normalized.endswith(".md"):
        errors.append(BLOG_PUBLISH_SOURCE_NOT_READY)
        return PreflightContext(
            source_relative_path=normalized,
            source_slug=None,
            public_slug=None,
            publication_date=None,
            source_content_sha256=None,
            campaign_id=None,
            expected_idempotency_key=None,
            image_relative_path=None,
            errors=tuple(errors),
        )

    folder_name = matched_prefix.removeprefix("blog-posts/").removesuffix("/")
    source_dir = (base_path / "blog-posts" / folder_name).resolve()
    resolved = (base_path / normalized).resolve()
    try:
        resolved.relative_to(source_dir)
    except ValueError:
        errors.append(BLOG_PUBLISH_SOURCE_NOT_READY)
        return PreflightContext(
            source_relative_path=normalized,
            source_slug=None,
            public_slug=None,
            publication_date=None,
            source_content_sha256=None,
            campaign_id=None,
            expected_idempotency_key=None,
            image_relative_path=None,
            errors=tuple(errors),
        )

    if not resolved.is_file():
        errors.append(BLOG_PUBLISH_SOURCE_NOT_READY)
        return PreflightContext(
            source_relative_path=normalized,
            source_slug=None,
            public_slug=None,
            publication_date=None,
            source_content_sha256=None,
            campaign_id=None,
            expected_idempotency_key=None,
            image_relative_path=None,
            errors=tuple(errors),
        )

    source_slug = resolved.stem
    try:
        public_slug = resolve_public_slug(source_slug, public_slug_override)
    except PublishError:
        errors.append(BLOG_PUBLISH_SOURCE_NOT_READY)
        return PreflightContext(
            source_relative_path=normalized,
            source_slug=source_slug,
            public_slug=None,
            publication_date=None,
            source_content_sha256=None,
            campaign_id=None,
            expected_idempotency_key=None,
            image_relative_path=f"{matched_prefix}{source_slug}.png",
            errors=tuple(errors),
        )

    try:
        content = resolved.read_text(encoding="utf-8")
    except OSError:
        errors.append(BLOG_PUBLISH_SOURCE_NOT_READY)
        return PreflightContext(
            source_relative_path=normalized,
            source_slug=source_slug,
            public_slug=public_slug,
            publication_date=None,
            source_content_sha256=None,
            campaign_id=None,
            expected_idempotency_key=None,
            image_relative_path=f"{matched_prefix}{source_slug}.png",
            errors=tuple(errors),
        )

    content_hash = compute_source_content_sha256(content)
    publication_date: str | None = None
    if content.startswith("---"):
        try:
            frontmatter, _body = _split_frontmatter(content)
            publication_date = _extract_publication_date(frontmatter.get("date"))
        except PublishError:
            pass

    campaign_id: str | None = None
    expected_key: str | None = None
    if publication_date and public_slug:
        try:
            campaign_id = generate_campaign_id(FLOW_A, publication_date, public_slug)
            expected_key = build_blog_publish_idempotency_key(
                source_slug=source_slug,
                public_slug=public_slug,
                publication_date=publication_date,
                source_content_sha256=content_hash,
            )
        except Exception:
            campaign_id = None
            expected_key = None

    return PreflightContext(
        source_relative_path=normalized,
        source_slug=source_slug,
        public_slug=public_slug,
        publication_date=publication_date,
        source_content_sha256=content_hash,
        campaign_id=campaign_id,
        expected_idempotency_key=expected_key,
        image_relative_path=f"{matched_prefix}{source_slug}.png",
        errors=tuple(errors),
    )


def _validation_summary(validation: Any) -> dict[str, Any]:
    return {
        "ok": validation.ok,
        "errors": list(validation.errors),
        "warnings": list(validation.warnings),
        "campaign_id": validation.campaign_id,
        "state": validation.state,
        "source_slug": validation.source_slug,
        "public_slug": validation.public_slug,
        "publication_date": validation.publication_date,
        "image_relative_path": validation.image_relative_path,
        "source_content_sha256": validation.source_content_sha256,
        "source_public_url": validation.source_public_url,
        "metadata_written": validation.metadata_written,
        "metadata_error_code": validation.metadata_error_code,
    }


def _failed_result(
    preflight: PreflightContext,
    *,
    errors: list[str],
    warnings: list[str] | None = None,
    validation: dict[str, Any] | None = None,
    blog_publish: dict[str, Any] | None = None,
    blog_image_generation: dict[str, Any] | None = None,
    campaign_id: str | None = None,
    state: str | None = None,
    source_public_url: str | None = None,
    metadata_written: bool = False,
    metadata_error_code: str | None = None,
) -> BlogPublishResult:
    return BlogPublishResult(
        status="failed",
        source_relative_path=preflight.source_relative_path,
        campaign_id=campaign_id if campaign_id is not None else preflight.campaign_id,
        state=state,
        source_slug=preflight.source_slug,
        public_slug=preflight.public_slug,
        publication_date=preflight.publication_date,
        image_relative_path=preflight.image_relative_path,
        source_public_url=source_public_url,
        errors=errors,
        warnings=warnings or [],
        validation=validation or {},
        blog_publish=blog_publish or {},
        blog_image_generation=blog_image_generation or {},
        metadata_written=metadata_written,
        metadata_error_code=metadata_error_code,
    )


def _check_idempotent_already_published(
    campaign: dict[str, Any],
    *,
    expected_idempotency_key: str,
    source_content_sha256: str,
) -> bool:
    if campaign.get("flow") != FLOW_A:
        return False
    if campaign.get("state") != STATE_BLOG_PUBLISHED:
        return False
    if campaign.get("source_content_sha256") != source_content_sha256:
        return False
    blog_publish = campaign.get("blog_publish") or {}
    if blog_publish.get("idempotency_key") != expected_idempotency_key:
        return False
    if not campaign.get("source_public_url"):
        return False
    return True


def _already_published_result(
    preflight: PreflightContext,
    campaign: dict[str, Any],
) -> BlogPublishResult:
    blog_publish = dict(campaign.get("blog_publish") or {})
    blog_publish["status"] = "already_published"
    return BlogPublishResult(
        status="completed",
        source_relative_path=preflight.source_relative_path,
        campaign_id=campaign.get("campaign_id", preflight.campaign_id),
        state=STATE_BLOG_PUBLISHED,
        source_slug=preflight.source_slug,
        public_slug=preflight.public_slug,
        publication_date=preflight.publication_date,
        image_relative_path=preflight.image_relative_path,
        source_public_url=campaign.get("source_public_url"),
        errors=[],
        warnings=list(campaign.get("warnings") or []),
        validation={},
        blog_publish=blog_publish,
        metadata_written=False,
        metadata_error_code=None,
    )


def _check_campaign_eligible_for_publish(
    campaign: dict[str, Any] | None,
    *,
    source_content_sha256: str,
) -> str | None:
    if campaign is None:
        return None

    if campaign.get("flow") == FLOW_B:
        return BLOG_PUBLISH_FLOW_B_NOT_ALLOWED

    state = campaign.get("state")

    stored_hash = campaign.get("source_content_sha256")
    if stored_hash and stored_hash != source_content_sha256:
        return BLOG_PUBLISH_CONTENT_HASH_CHANGED

    if state == STATE_ERROR:
        return None

    if state in INVALID_PUBLISH_STATES:
        return BLOG_PUBLISH_INVALID_CAMPAIGN_STATE

    if state == STATE_BLOG_PUBLISHED:
        return BLOG_PUBLISH_INVALID_CAMPAIGN_STATE

    if state not in (STATE_READY, STATE_VALIDATED, *RESUMABLE_WITHOUT_VALIDATION):
        return BLOG_PUBLISH_INVALID_CAMPAIGN_STATE

    return None


def _expected_public_target_paths(
    public_slug: str,
    publication_date: date,
) -> tuple[str, str]:
    post_relative = f"_posts/{publication_date.isoformat()}-{public_slug}.md"
    image_relative = f"assets/images/{public_slug}.png"
    return post_relative, image_relative


def _public_target_existence(
    repo_path: Path,
    *,
    post_relative: str,
    image_relative: str,
) -> tuple[bool, bool]:
    return (
        (repo_path / post_relative).is_file(),
        (repo_path / image_relative).is_file(),
    )


def _clear_stale_publish_errors(campaign: dict[str, Any]) -> None:
    campaign["errors"] = [
        code
        for code in campaign.get("errors", [])
        if code not in STALE_PUBLISH_ERROR_CODES
    ]


def _compare_public_targets(
    base_path: Path,
    repo_path: Path,
    preflight: PreflightContext,
    *,
    post_relative: str,
    image_relative: str,
    pub_date: date,
    execution_time: datetime,
) -> PublicTargetComparison | None:
    """Compare public artifacts against canonical publish output for the ready source."""
    assert preflight.source_slug is not None
    assert preflight.public_slug is not None

    source_md = (base_path / preflight.source_relative_path).resolve()
    source_png = (base_path / preflight.image_relative_path).resolve()
    public_post = (repo_path / post_relative).resolve()
    public_image = (repo_path / image_relative).resolve()

    if not source_md.is_file() or not source_png.is_file():
        return None
    if not public_post.is_file() or not public_image.is_file():
        return None

    try:
        expected_post = render_expected_public_post(
            source_md,
            preflight.public_slug,
            pub_date,
            execution_time=execution_time,
        )
        actual_post = public_post.read_text(encoding="utf-8")
        expected_image = source_png.read_bytes()
        actual_image = public_image.read_bytes()
    except (OSError, PublishError):
        return None

    return PublicTargetComparison(
        expected_post_relative=post_relative,
        actual_post_relative=post_relative,
        expected_image_relative=image_relative,
        actual_image_relative=image_relative,
        post_matches=actual_post == expected_post,
        image_matches=actual_image == expected_image,
        expected_post_sha256=compute_source_content_sha256(expected_post),
        actual_post_sha256=compute_source_content_sha256(actual_post),
        expected_image_sha256=compute_source_content_sha256(expected_image),
        actual_image_sha256=compute_source_content_sha256(actual_image),
    )


def _enrich_preflight_from_campaign(
    preflight: PreflightContext,
    campaign: dict[str, Any],
) -> PreflightContext:
    """Prefer campaign publication identity when resuming publish without validation."""
    publication_date = campaign.get("publication_date") or preflight.publication_date
    public_slug = campaign.get("public_slug") or preflight.public_slug
    source_slug = campaign.get("source_slug") or preflight.source_slug
    source_content_sha256 = (
        campaign.get("source_content_sha256") or preflight.source_content_sha256
    )
    image_relative_path = campaign.get("image_relative_path") or preflight.image_relative_path
    campaign_id = campaign.get("campaign_id") or preflight.campaign_id

    expected_idempotency_key = preflight.expected_idempotency_key
    if (
        publication_date
        and public_slug
        and source_slug
        and source_content_sha256
    ):
        try:
            expected_idempotency_key = build_blog_publish_idempotency_key(
                source_slug=source_slug,
                public_slug=public_slug,
                publication_date=publication_date,
                source_content_sha256=source_content_sha256,
            )
        except Exception:
            pass

    return PreflightContext(
        source_relative_path=preflight.source_relative_path,
        source_slug=source_slug,
        public_slug=public_slug,
        publication_date=publication_date,
        source_content_sha256=source_content_sha256,
        campaign_id=campaign_id,
        expected_idempotency_key=expected_idempotency_key,
        image_relative_path=image_relative_path,
        errors=preflight.errors,
    )


def _resolve_source_public_url(
    preflight: PreflightContext,
    campaign: dict[str, Any] | None,
    site_url: str,
) -> str | None:
    if campaign:
        stored_url = campaign.get("source_public_url")
        if stored_url:
            return str(stored_url)
    if preflight.publication_date and preflight.public_slug:
        return public_url(
            site_url,
            date.fromisoformat(preflight.publication_date),
            preflight.public_slug,
        )
    return None


def _handoff_image_matches_ready(
    base_path: Path,
    repo_path: Path,
    preflight: PreflightContext,
    *,
    image_relative: str,
) -> bool:
    if not preflight.image_relative_path:
        return False
    source_png = (base_path / preflight.image_relative_path).resolve()
    public_image = (repo_path / image_relative).resolve()
    if not source_png.is_file() or not public_image.is_file():
        return False
    try:
        return source_png.read_bytes() == public_image.read_bytes()
    except OSError:
        return False


def _reconciliation_skip_reason(
    base_path: Path,
    campaign: dict[str, Any],
    preflight: PreflightContext,
    repo_path: Path,
    *,
    post_relative: str,
    image_relative: str,
    pub_date: date,
    execution_time: datetime,
) -> tuple[str | None, dict[str, Any], PublicTargetComparison | None]:
    if campaign.get("state") not in RECONCILABLE_PUBLISH_STATES:
        return RECONCILIATION_SKIPPED_STATE_NOT_ALLOWED, {}, None

    if campaign.get("flow") != FLOW_A:
        return RECONCILIATION_SKIPPED_STATE_NOT_ALLOWED, {}, None

    if campaign.get("source_relative_path") != preflight.source_relative_path:
        return RECONCILIATION_SKIPPED_SOURCE_MISMATCH, {}, None

    if campaign.get("source_content_sha256") != preflight.source_content_sha256:
        return RECONCILIATION_SKIPPED_HASH_MISMATCH, {}, None

    post_exists, image_exists = _public_target_existence(
        repo_path,
        post_relative=post_relative,
        image_relative=image_relative,
    )
    if not post_exists and not image_exists:
        return None, {}, None
    if not post_exists:
        if _handoff_image_matches_ready(
            base_path,
            repo_path,
            preflight,
            image_relative=image_relative,
        ):
            return None, {}, None
        return RECONCILIATION_SKIPPED_MISSING_PUBLIC_POST, {}, None
    if not image_exists:
        return RECONCILIATION_SKIPPED_MISSING_PUBLIC_IMAGE, {}, None

    blog_publish = campaign.get("blog_publish") or {}
    stored_key = blog_publish.get("idempotency_key")
    if (
        stored_key is not None
        and stored_key != preflight.expected_idempotency_key
    ):
        return RECONCILIATION_SKIPPED_IDEMPOTENCY_MISMATCH, {}, None

    comparison = _compare_public_targets(
        base_path,
        repo_path,
        preflight,
        post_relative=post_relative,
        image_relative=image_relative,
        pub_date=pub_date,
        execution_time=execution_time,
    )
    if comparison is None:
        return RECONCILIATION_SKIPPED_PUBLIC_CONTENT_MISMATCH, {}, None

    diagnostics = comparison.diagnostics()
    if not comparison.post_matches:
        return RECONCILIATION_SKIPPED_PUBLIC_CONTENT_MISMATCH, diagnostics, comparison
    # Canonical post matches — reconcile; adopt existing public image when it
    # differs from the ready image (never overwrite the public asset).
    return None, diagnostics, comparison


def _target_exists_failure(
    preflight: PreflightContext,
    *,
    campaign: dict[str, Any],
    campaign_id: str,
    site_url: str,
    skip_reason: str | None,
    reconciliation_diagnostics: dict[str, Any] | None = None,
    warnings: list[str],
    validation_summary: dict[str, Any],
    blog_image_generation: dict[str, Any] | None = None,
) -> BlogPublishResult:
    blog_publish = dict(campaign.get("blog_publish") or {})
    if skip_reason:
        blog_publish["reconciliation_skip_reason"] = skip_reason
    if reconciliation_diagnostics:
        blog_publish.update(reconciliation_diagnostics)
    return _failed_result(
        preflight,
        errors=[BLOG_PUBLISH_TARGET_EXISTS],
        warnings=warnings,
        validation=validation_summary,
        campaign_id=campaign_id,
        state=campaign.get("state"),
        source_public_url=_resolve_source_public_url(preflight, campaign, site_url),
        blog_publish=blog_publish,
        blog_image_generation=blog_image_generation or {},
    )


def _attempt_blog_publish_reconciliation(
    base_path: Path,
    preflight: PreflightContext,
    campaign: dict[str, Any],
    *,
    campaign_id: str,
    repo_path: Path,
    site_url: str,
    pub_date: date,
    post_relative: str,
    image_relative: str,
    warnings: list[str],
    validation_summary: dict[str, Any],
    blog_image_generation: dict[str, Any] | None = None,
    execution_time: datetime,
) -> BlogPublishResult | None:
    """Reconcile metadata when both public targets exist; otherwise explain skip."""
    if campaign.get("state") not in RECONCILABLE_PUBLISH_STATES:
        return None

    post_exists, image_exists = _public_target_existence(
        repo_path,
        post_relative=post_relative,
        image_relative=image_relative,
    )
    if not post_exists and not image_exists:
        return None

    skip_reason, reconciliation_diagnostics, comparison = _reconciliation_skip_reason(
        base_path,
        campaign,
        preflight,
        repo_path,
        post_relative=post_relative,
        image_relative=image_relative,
        pub_date=pub_date,
        execution_time=execution_time,
    )
    if skip_reason is None and comparison is not None:
        return _reconcile_existing_publication(
            base_path,
            preflight,
            campaign,
            campaign_id=campaign_id,
            post_relative=post_relative,
            image_relative=image_relative,
            site_url=site_url,
            pub_date=pub_date,
            warnings=warnings,
            validation_summary=validation_summary,
            reconciled_from_error=campaign.get("state") == STATE_ERROR,
            comparison=comparison,
            blog_image_generation=blog_image_generation,
        )

    if skip_reason is None:
        return None

    if post_exists or image_exists:
        return _target_exists_failure(
            preflight,
            campaign=campaign,
            campaign_id=campaign_id,
            site_url=site_url,
            skip_reason=skip_reason,
            reconciliation_diagnostics=reconciliation_diagnostics,
            warnings=warnings,
            validation_summary=validation_summary,
            blog_image_generation=blog_image_generation,
        )

    return None


def _reconcile_existing_publication(
    base_path: Path,
    preflight: PreflightContext,
    campaign: dict[str, Any],
    *,
    campaign_id: str,
    post_relative: str,
    image_relative: str,
    site_url: str,
    pub_date: date,
    warnings: list[str],
    validation_summary: dict[str, Any],
    reconciled_from_error: bool = False,
    comparison: PublicTargetComparison | None = None,
    blog_image_generation: dict[str, Any] | None = None,
) -> BlogPublishResult:
    """Align campaign metadata with public repo files already on disk."""
    assert preflight.public_slug is not None
    assert preflight.expected_idempotency_key is not None

    reconciled_url = public_url(site_url, pub_date, preflight.public_slug)
    state = campaign.get("state")

    try:
        if state == STATE_VALIDATED:
            transition_state(
                campaign,
                STATE_BLOG_PUBLISH_PENDING,
                reason="Blog publish reconciliation started",
                actor=ACTOR_WORKER,
            )

        if campaign.get("state") == STATE_BLOG_PUBLISH_PENDING:
            transition_state(
                campaign,
                STATE_BLOG_PUBLISHED,
                reason="Blog publish reconciled from existing public artifacts",
                actor=ACTOR_WORKER,
            )
        elif state == STATE_ERROR:
            now = utc_now_iso()
            _append_state_history(
                campaign,
                from_state=state,
                to_state=STATE_BLOG_PUBLISHED,
                reason="Blog publish reconciled from error after prior publish failure",
                actor=ACTOR_WORKER,
                error_code=None,
                at=now,
            )
            campaign["state"] = STATE_BLOG_PUBLISHED
            campaign["updated_at"] = now
            _clear_stale_publish_errors(campaign)
    except Exception:
        return _failed_result(
            preflight,
            errors=[BLOG_PUBLISH_INVALID_CAMPAIGN_STATE],
            warnings=warnings,
            validation=validation_summary,
            campaign_id=campaign_id,
            state=campaign.get("state"),
        )

    published_at = utc_now_iso()
    blog_publish = {
        "idempotency_key": preflight.expected_idempotency_key,
        "status": "reconciled",
        "source_public_url": reconciled_url,
        "published_at": published_at,
        "public_repo_path": post_relative,
        "public_repo_image_path": image_relative,
        "error_code": None,
    }
    if reconciled_from_error:
        blog_publish["reconciled_from_error_state"] = True
    if (
        comparison is not None
        and comparison.post_matches
        and not comparison.image_matches
    ):
        blog_publish["public_image_adopted"] = True
        blog_publish["public_image_source"] = "existing_public_asset"
        blog_publish["ready_image_sha256"] = comparison.expected_image_sha256
        blog_publish["published_image_sha256"] = comparison.actual_image_sha256
        blog_publish["reconciliation_note"] = (
            "public_image_differs_from_ready_image_adopted"
        )

    campaign["blog_publish"] = blog_publish
    campaign["source_public_url"] = reconciled_url
    campaign["published_post_relative_path"] = post_relative
    campaign["published_image_relative_path"] = image_relative

    result_warnings = list(warnings)
    if reconciled_from_error:
        result_warnings.append(RECONCILED_FROM_ERROR_WARNING)

    metadata_written, metadata_error_code = _persist_campaign(
        base_path, campaign_id, campaign
    )

    result = BlogPublishResult(
        status="completed",
        source_relative_path=preflight.source_relative_path,
        campaign_id=campaign_id,
        state=STATE_BLOG_PUBLISHED,
        source_slug=preflight.source_slug,
        public_slug=preflight.public_slug,
        publication_date=preflight.publication_date,
        image_relative_path=preflight.image_relative_path,
        source_public_url=reconciled_url,
        errors=[] if metadata_written else [BLOG_PUBLISH_METADATA_WRITE_FAILED],
        warnings=result_warnings,
        validation=validation_summary,
        blog_publish=blog_publish,
        blog_image_generation=blog_image_generation or {},
        metadata_written=metadata_written,
        metadata_error_code=metadata_error_code,
    )
    if not metadata_written:
        result.status = "failed"
    return result


def _build_environ(
    base_path: Path,
    site_url: str,
    github_pages_repo_path: str | None,
    environ: dict[str, str] | None,
) -> dict[str, str]:
    env = dict(os.environ if environ is None else environ)
    env["SILVERMAN_BLOG_LINKEDIN_BASE_PATH"] = str(base_path)
    env["SILVERMAN_SITE_URL"] = site_url.rstrip("/")
    if github_pages_repo_path:
        env[ENV_REPO_PATH] = github_pages_repo_path
    return env


def _persist_campaign(
    base_path: Path,
    campaign_id: str,
    campaign: dict[str, Any],
) -> tuple[bool, str | None]:
    write_result = write_campaign_metadata(base_path, campaign_id, campaign)
    if not write_result.written:
        return False, write_result.error_code or BLOG_PUBLISH_METADATA_WRITE_FAILED
    return True, None


def reconcile_authorized_source_hash(
    base_path: Path,
    *,
    campaign_id: str,
    source_relative_path: str,
    front_matter_updated: bool,
) -> tuple[bool, str | None, str | None, str | None]:
    """Persist authorized active hash after editorial frontmatter patch."""
    campaign = read_campaign_metadata(base_path, campaign_id)
    if campaign is None:
        return False, None, None, "campaign_not_found"

    updated_hash = recompute_source_hash_after_generation(base_path, source_relative_path)
    if not updated_hash:
        return False, None, None, BLOG_PUBLISH_HASH_RECONCILIATION_FAILED

    if not front_matter_updated:
        return True, updated_hash, None, None

    intake_hash = campaign.get("intake_source_content_sha256")
    if not isinstance(intake_hash, str) or not intake_hash:
        existing_active = campaign.get("source_content_sha256")
        if isinstance(existing_active, str) and existing_active:
            campaign["intake_source_content_sha256"] = existing_active

    campaign["source_content_sha256"] = updated_hash
    source_slug = campaign.get("source_slug")
    public_slug = campaign.get("public_slug")
    publication_date = campaign.get("publication_date")
    expected_key: str | None = None
    if source_slug and public_slug and publication_date:
        try:
            expected_key = build_blog_publish_idempotency_key(
                source_slug=str(source_slug),
                public_slug=str(public_slug),
                publication_date=str(publication_date),
                source_content_sha256=updated_hash,
            )
            blog_publish = dict(campaign.get("blog_publish") or {})
            blog_publish["idempotency_key"] = expected_key
            campaign["blog_publish"] = blog_publish
        except Exception:
            return False, updated_hash, None, BLOG_PUBLISH_HASH_RECONCILIATION_FAILED

    metadata_written, metadata_error_code = _persist_campaign(
        base_path, campaign_id, campaign
    )
    if not metadata_written:
        return False, updated_hash, expected_key, (
            metadata_error_code or BLOG_PUBLISH_HASH_RECONCILIATION_FAILED
        )
    return True, updated_hash, expected_key, None


def publish_blog_post(
    base_path: Path,
    source_relative_path: str,
    *,
    site_url: str = DEFAULT_SITE_URL,
    public_slug_override: str | None = None,
    github_pages_repo_path: str | None = None,
    environ: dict[str, str] | None = None,
    comfyui_client: ComfyUIClientProtocol | None = None,
    execution_time: datetime | None = None,
) -> BlogPublishResult:
    """Orchestrate Flow A blog publishing for one ready post."""
    publish_execution_time = (
        execution_time
        if execution_time is not None
        else datetime.now(timezone.utc)
    )
    post_schedule_result = _try_post_schedule_idempotent_publish(
        base_path, source_relative_path
    )
    if post_schedule_result is not None:
        return post_schedule_result

    preflight = _preflight_inspect(
        base_path,
        source_relative_path,
        public_slug_override=public_slug_override,
    )

    if preflight.errors:
        return _failed_result(preflight, errors=list(preflight.errors))

    assert preflight.source_slug is not None
    assert preflight.public_slug is not None
    assert preflight.source_content_sha256 is not None

    campaign: dict[str, Any] | None = None
    if preflight.campaign_id and preflight.expected_idempotency_key:
        campaign = read_campaign_metadata(base_path, preflight.campaign_id)
        if campaign and _check_idempotent_already_published(
            campaign,
            expected_idempotency_key=preflight.expected_idempotency_key,
            source_content_sha256=preflight.source_content_sha256,
        ):
            return _already_published_result(preflight, campaign)

        pre_validation_error = _check_campaign_eligible_for_publish(
            campaign,
            source_content_sha256=preflight.source_content_sha256,
        )
        if pre_validation_error:
            return _failed_result(
                preflight,
                errors=[pre_validation_error],
                campaign_id=campaign.get("campaign_id", preflight.campaign_id),
                state=campaign.get("state"),
                source_public_url=campaign.get("source_public_url"),
            )

    skip_validation = (
        campaign is not None
        and campaign.get("state") in SKIP_VALIDATION_STATES
        and campaign.get("source_content_sha256") == preflight.source_content_sha256
    )

    if skip_validation and campaign is not None:
        preflight = _enrich_preflight_from_campaign(preflight, campaign)

    validation_summary: dict[str, Any] = {}
    warnings: list[str] = []
    blog_image_generation_summary: dict[str, Any] = {}

    env = _build_environ(base_path, site_url, github_pages_repo_path, environ)
    comfy_config = load_comfyui_settings(environ)

    if not skip_validation:
        pre_validation = validate_ready_post_pre_generation(
            base_path,
            preflight.source_relative_path,
            site_url=site_url,
            environ=environ,
        )
        validation_summary = _validation_summary(pre_validation)
        warnings = list(pre_validation.warnings)
        if not pre_validation.ok:
            errors = list(pre_validation.errors)
            if BLOG_PUBLISH_VALIDATION_FAILED not in errors:
                errors.insert(0, BLOG_PUBLISH_VALIDATION_FAILED)
            return _failed_result(
                preflight,
                errors=errors,
                warnings=warnings,
                validation=validation_summary,
                campaign_id=pre_validation.campaign_id or preflight.campaign_id,
                state=pre_validation.state,
                source_public_url=pre_validation.source_public_url,
            )

    editorial_result = ensure_editorial_blog_image(
        base_path,
        preflight.source_relative_path,
        config=comfy_config,
        client=comfyui_client,
        environ=environ,
        public_slug_override=public_slug_override,
        campaign_id=preflight.campaign_id,
        github_pages_repo_path=github_pages_repo_path,
    )
    blog_image_generation_summary = editorial_result.to_dict()

    if editorial_result.status == "failed":
        failure_errors: list[str] = []
        if editorial_result.error_code:
            failure_errors.append(editorial_result.error_code)
        else:
            failure_errors.append(BLOG_IMAGE_GENERATION_FAILED)
        return _failed_result(
            preflight,
            errors=failure_errors,
            warnings=warnings,
            validation=validation_summary,
            campaign_id=preflight.campaign_id,
            state=campaign.get("state") if campaign else None,
            source_public_url=(
                campaign.get("source_public_url") if campaign else None
            ),
            blog_image_generation=blog_image_generation_summary,
            metadata_written=editorial_result.metadata_written,
            metadata_error_code=editorial_result.metadata_error_code,
        )

    if editorial_result.image_relative_path:
        preflight = PreflightContext(
            source_relative_path=preflight.source_relative_path,
            source_slug=preflight.source_slug,
            public_slug=preflight.public_slug,
            publication_date=preflight.publication_date,
            source_content_sha256=preflight.source_content_sha256,
            campaign_id=preflight.campaign_id,
            expected_idempotency_key=preflight.expected_idempotency_key,
            image_relative_path=editorial_result.image_relative_path,
            errors=preflight.errors,
        )

    if editorial_result.front_matter_updated:
        updated_hash = recompute_source_hash_after_generation(
            base_path,
            preflight.source_relative_path,
        )
        if updated_hash:
            expected_key = preflight.expected_idempotency_key
            if (
                preflight.publication_date
                and preflight.source_slug
                and preflight.public_slug
            ):
                expected_key = build_blog_publish_idempotency_key(
                    source_slug=preflight.source_slug,
                    public_slug=preflight.public_slug,
                    publication_date=preflight.publication_date,
                    source_content_sha256=updated_hash,
                )
            preflight = PreflightContext(
                source_relative_path=preflight.source_relative_path,
                source_slug=preflight.source_slug,
                public_slug=preflight.public_slug,
                publication_date=preflight.publication_date,
                source_content_sha256=updated_hash,
                campaign_id=preflight.campaign_id,
                expected_idempotency_key=expected_key,
                image_relative_path=preflight.image_relative_path,
                errors=preflight.errors,
            )
        if preflight.campaign_id:
            existing_campaign = read_campaign_metadata(base_path, preflight.campaign_id)
            if existing_campaign is not None:
                reconciled_ok, reconciled_hash, updated_key, reconcile_error = (
                    reconcile_authorized_source_hash(
                        base_path,
                        campaign_id=preflight.campaign_id,
                        source_relative_path=preflight.source_relative_path,
                        front_matter_updated=True,
                    )
                )
                if not reconciled_ok:
                    reconcile_errors = [BLOG_PUBLISH_HASH_RECONCILIATION_FAILED]
                    underlying = reconcile_error
                    if (
                        underlying
                        and underlying != BLOG_PUBLISH_HASH_RECONCILIATION_FAILED
                    ):
                        reconcile_errors.append(underlying)
                    return _failed_result(
                        preflight,
                        errors=reconcile_errors,
                        warnings=warnings,
                        validation=validation_summary,
                        campaign_id=preflight.campaign_id,
                        state=campaign.get("state") if campaign else None,
                        blog_image_generation=blog_image_generation_summary,
                    )
                if reconciled_hash:
                    preflight = PreflightContext(
                        source_relative_path=preflight.source_relative_path,
                        source_slug=preflight.source_slug,
                        public_slug=preflight.public_slug,
                        publication_date=preflight.publication_date,
                        source_content_sha256=reconciled_hash,
                        campaign_id=preflight.campaign_id,
                        expected_idempotency_key=updated_key or preflight.expected_idempotency_key,
                        image_relative_path=preflight.image_relative_path,
                        errors=preflight.errors,
                    )
                    campaign = read_campaign_metadata(base_path, preflight.campaign_id)

    if not skip_validation:
        validation = validate_ready_post(
            base_path,
            preflight.source_relative_path,
            site_url=site_url,
        )
        validation_summary = _validation_summary(validation)
        warnings = list(validation.warnings)

        if not validation.ok:
            errors = list(validation.errors)
            if CAMPAIGN_CONTENT_HASH_CHANGED in errors:
                publish_error = BLOG_PUBLISH_CONTENT_HASH_CHANGED
            else:
                publish_error = BLOG_PUBLISH_VALIDATION_FAILED
            if publish_error not in errors:
                errors.insert(0, publish_error)
            return _failed_result(
                preflight,
                errors=errors,
                warnings=warnings,
                validation=validation_summary,
                campaign_id=validation.campaign_id or preflight.campaign_id,
                state=validation.state,
                source_public_url=validation.source_public_url,
                metadata_written=validation.metadata_written,
                metadata_error_code=validation.metadata_error_code,
                blog_image_generation=blog_image_generation_summary,
            )

        preflight_campaign_id = validation.campaign_id or preflight.campaign_id
        if preflight_campaign_id:
            campaign = read_campaign_metadata(base_path, preflight_campaign_id)
        if validation.publication_date:
            preflight = PreflightContext(
                source_relative_path=preflight.source_relative_path,
                source_slug=validation.source_slug or preflight.source_slug,
                public_slug=validation.public_slug or preflight.public_slug,
                publication_date=validation.publication_date,
                source_content_sha256=(
                    validation.source_content_sha256 or preflight.source_content_sha256
                ),
                campaign_id=preflight_campaign_id,
                expected_idempotency_key=(
                    build_blog_publish_idempotency_key(
                        source_slug=validation.source_slug or preflight.source_slug,
                        public_slug=validation.public_slug or preflight.public_slug,
                        publication_date=validation.publication_date,
                        source_content_sha256=(
                            validation.source_content_sha256
                            or preflight.source_content_sha256
                        ),
                    )
                    if validation.source_slug
                    and validation.public_slug
                    and validation.publication_date
                    and (
                        validation.source_content_sha256
                        or preflight.source_content_sha256
                    )
                    else preflight.expected_idempotency_key
                ),
                image_relative_path=(
                    validation.image_relative_path or preflight.image_relative_path
                ),
                errors=preflight.errors,
            )

    handoff_result = handoff_public_blog_image(
        base_path,
        preflight.source_relative_path,
        github_pages_repo_path=github_pages_repo_path,
        public_slug_override=public_slug_override,
        campaign_id=preflight.campaign_id,
        environ=environ,
    )
    handoff_summary = handoff_result.to_dict()
    blog_image_generation_summary.update(
        {
            key: value
            for key, value in handoff_summary.items()
            if value is not None
            and key
            not in {
                "source_relative_path",
                "status",
                "error_code",
                "metadata_written",
                "metadata_error_code",
            }
        }
    )
    if handoff_result.status == "failed":
        handoff_errors = [
            handoff_result.error_code or BLOG_IMAGE_PUBLIC_ASSET_HANDOFF_FAILED
        ]
        blog_image_generation_summary["status"] = "failed"
        blog_image_generation_summary["error_code"] = handoff_errors[0]
        return _failed_result(
            preflight,
            errors=handoff_errors,
            warnings=warnings,
            validation=validation_summary,
            campaign_id=preflight.campaign_id,
            state=campaign.get("state") if campaign else None,
            blog_image_generation=blog_image_generation_summary,
            metadata_written=handoff_result.metadata_written,
            metadata_error_code=handoff_result.metadata_error_code,
        )

    eligibility_error = _check_campaign_eligible_for_publish(
        campaign,
        source_content_sha256=preflight.source_content_sha256,
    )
    if eligibility_error:
        return _failed_result(
            preflight,
            errors=[eligibility_error],
            warnings=warnings,
            validation=validation_summary,
            campaign_id=(campaign or {}).get("campaign_id", preflight.campaign_id),
            state=(campaign or {}).get("state"),
            source_public_url=_resolve_source_public_url(preflight, campaign, site_url),
        )

    if campaign is None or preflight.campaign_id is None:
        return _failed_result(
            preflight,
            errors=[BLOG_PUBLISH_INVALID_CAMPAIGN_STATE],
            warnings=warnings,
            validation=validation_summary,
            source_public_url=_resolve_source_public_url(preflight, campaign, site_url),
        )

    campaign_id = preflight.campaign_id
    assert preflight.publication_date is not None
    assert preflight.expected_idempotency_key is not None

    allowed_publish_states = {STATE_VALIDATED, STATE_ERROR, *RESUMABLE_WITHOUT_VALIDATION}
    if campaign.get("state") not in allowed_publish_states:
        return _failed_result(
            preflight,
            errors=[BLOG_PUBLISH_INVALID_CAMPAIGN_STATE],
            warnings=warnings,
            validation=validation_summary,
            campaign_id=campaign_id,
            state=campaign.get("state"),
            source_public_url=_resolve_source_public_url(preflight, campaign, site_url),
        )

    env = _build_environ(base_path, site_url, github_pages_repo_path, environ)
    try:
        config = load_config(env)
        validate_repo_layout(config.repo_path)
    except PublishError:
        return _failed_result(
            preflight,
            errors=[BLOG_PUBLISH_PUBLIC_REPO_NOT_CONFIGURED],
            warnings=warnings,
            validation=validation_summary,
            campaign_id=campaign_id,
            state=campaign.get("state"),
            source_public_url=_resolve_source_public_url(preflight, campaign, site_url),
        )

    pub_date = date.fromisoformat(preflight.publication_date)
    post_relative, image_relative = _expected_public_target_paths(
        preflight.public_slug,
        pub_date,
    )

    reconciliation_result = _attempt_blog_publish_reconciliation(
        base_path,
        preflight,
        campaign,
        campaign_id=campaign_id,
        repo_path=config.repo_path,
        site_url=site_url,
        pub_date=pub_date,
        post_relative=post_relative,
        image_relative=image_relative,
        warnings=warnings,
        validation_summary=validation_summary,
        blog_image_generation=blog_image_generation_summary,
        execution_time=publish_execution_time,
    )
    if reconciliation_result is not None:
        return reconciliation_result

    if campaign.get("state") == STATE_ERROR:
        return _failed_result(
            preflight,
            errors=[BLOG_PUBLISH_INVALID_CAMPAIGN_STATE],
            warnings=warnings,
            validation=validation_summary,
            campaign_id=campaign_id,
            state=campaign.get("state"),
            source_public_url=_resolve_source_public_url(preflight, campaign, site_url),
        )

    if campaign.get("state") == STATE_VALIDATED:
        try:
            transition_state(
                campaign,
                STATE_BLOG_PUBLISH_PENDING,
                reason="Blog publish started",
                actor=ACTOR_WORKER,
            )
        except Exception:
            return _failed_result(
                preflight,
                errors=[BLOG_PUBLISH_INVALID_CAMPAIGN_STATE],
                warnings=warnings,
                validation=validation_summary,
                campaign_id=campaign_id,
                state=campaign.get("state"),
            )

        blog_publish = dict(campaign.get("blog_publish") or {})
        blog_publish.update(
            {
                "idempotency_key": preflight.expected_idempotency_key,
                "status": "pending",
                "error_code": None,
            }
        )
        campaign["blog_publish"] = blog_publish

        metadata_written, metadata_error_code = _persist_campaign(
            base_path, campaign_id, campaign
        )
        if not metadata_written:
            return _failed_result(
                preflight,
                errors=[BLOG_PUBLISH_METADATA_WRITE_FAILED],
                warnings=warnings,
                validation=validation_summary,
                campaign_id=campaign_id,
                state=campaign.get("state"),
                metadata_written=False,
                metadata_error_code=metadata_error_code,
            )

    try:
        plan: PublishPlan = run_publish(
            preflight.source_slug,
            publication_date=pub_date,
            apply=True,
            public_slug_override=public_slug_override,
            environ=env,
            execution_time=publish_execution_time,
            source_relative_path=preflight.source_relative_path,
        )
    except PublishError as exc:
        error_code = BLOG_PUBLISH_TARGET_EXISTS
        message = str(exc)
        if "refusing to overwrite" not in message:
            error_code = BLOG_PUBLISH_FAILED
        else:
            overwrite_reconciliation = _attempt_blog_publish_reconciliation(
                base_path,
                preflight,
                campaign,
                campaign_id=campaign_id,
                repo_path=config.repo_path,
                site_url=site_url,
                pub_date=pub_date,
                post_relative=post_relative,
                image_relative=image_relative,
                warnings=warnings,
                validation_summary=validation_summary,
                blog_image_generation=blog_image_generation_summary,
                execution_time=publish_execution_time,
            )
            if overwrite_reconciliation is not None:
                return overwrite_reconciliation

        blog_publish = dict(campaign.get("blog_publish") or {})
        blog_publish.update({"status": "failed", "error_code": error_code})
        campaign["blog_publish"] = blog_publish

        try:
            transition_state(
                campaign,
                STATE_ERROR,
                reason="Blog publish bridge failed",
                actor=ACTOR_WORKER,
                error_code=error_code,
            )
        except Exception:
            pass

        metadata_written, metadata_error_code = _persist_campaign(
            base_path, campaign_id, campaign
        )
        errors = [error_code]
        if not metadata_written and metadata_error_code:
            errors.append(metadata_error_code)
        return _failed_result(
            preflight,
            errors=errors,
            warnings=warnings,
            validation=validation_summary,
            campaign_id=campaign_id,
            state=campaign.get("state"),
            source_public_url=_resolve_source_public_url(preflight, campaign, site_url),
            blog_publish=blog_publish,
            metadata_written=metadata_written,
            metadata_error_code=metadata_error_code,
        )

    try:
        transition_state(
            campaign,
            STATE_BLOG_PUBLISHED,
            reason="Blog published to public repo checkout",
            actor=ACTOR_WORKER,
        )
    except Exception:
        return _failed_result(
            preflight,
            errors=[BLOG_PUBLISH_FAILED],
            warnings=warnings,
            validation=validation_summary,
            campaign_id=campaign_id,
            state=campaign.get("state"),
            source_public_url=plan.public_url,
        )

    published_at = utc_now_iso()
    blog_publish = {
        "idempotency_key": preflight.expected_idempotency_key,
        "status": "published",
        "source_public_url": plan.public_url,
        "published_at": published_at,
        "public_repo_path": plan.post_relative,
        "public_repo_image_path": plan.image_relative,
        "error_code": None,
    }
    if plan.date_adjusted:
        blog_publish["date_adjusted"] = True
        blog_publish["publish_timestamp"] = plan.publish_timestamp.isoformat()
        if plan.permalink:
            blog_publish["permalink"] = plan.permalink
    campaign["blog_publish"] = blog_publish
    campaign["source_public_url"] = plan.public_url

    metadata_written, metadata_error_code = _persist_campaign(
        base_path, campaign_id, campaign
    )

    result = BlogPublishResult(
        status="completed",
        source_relative_path=preflight.source_relative_path,
        campaign_id=campaign_id,
        state=STATE_BLOG_PUBLISHED,
        source_slug=preflight.source_slug,
        public_slug=preflight.public_slug,
        publication_date=preflight.publication_date,
        image_relative_path=preflight.image_relative_path,
        source_public_url=plan.public_url,
        errors=[] if metadata_written else [BLOG_PUBLISH_METADATA_WRITE_FAILED],
        warnings=warnings,
        validation=validation_summary,
        blog_publish=blog_publish,
        blog_image_generation=blog_image_generation_summary,
        metadata_written=metadata_written,
        metadata_error_code=metadata_error_code,
    )
    if not metadata_written:
        result.status = "failed"
    return result
