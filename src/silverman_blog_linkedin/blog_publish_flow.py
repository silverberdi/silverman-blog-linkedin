"""Flow A blog publish orchestration."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.campaign_lifecycle import (
    ACTOR_WORKER,
    FLOW_A,
    FLOW_B,
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
    generate_campaign_id,
    read_campaign_metadata,
    transition_state,
    write_campaign_metadata,
)
from silverman_blog_linkedin.github_pages_publish import (
    DEFAULT_SITE_URL,
    ENV_REPO_PATH,
    PublishError,
    PublishPlan,
    _split_frontmatter,
    load_config,
    prepare_frontmatter,
    public_url,
    render_markdown,
    resolve_public_slug,
    run_publish,
    validate_repo_layout,
)
from silverman_blog_linkedin.ready_post_validation import (
    CAMPAIGN_CONTENT_HASH_CHANGED,
    CONTENT_CONTAINS_TODO,
    READY_RELATIVE_PREFIX,
    validate_ready_post,
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
RECONCILIATION_SKIPPED_IDEMPOTENCY_MISMATCH = (
    "blog_publish_reconciliation_skipped_idempotency_mismatch"
)


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


def _preflight_inspect(
    base_path: Path,
    source_relative_path: str,
    *,
    public_slug_override: str | None,
) -> PreflightContext:
    normalized = _normalize_relative_path(source_relative_path)
    errors: list[str] = []
    ready_dir = (base_path / "blog-posts" / "ready").resolve()

    if not normalized.startswith(READY_RELATIVE_PREFIX):
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

    resolved = (base_path / normalized).resolve()
    try:
        resolved.relative_to(ready_dir)
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
            image_relative_path=f"{READY_RELATIVE_PREFIX}{source_slug}.png",
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
            image_relative_path=f"{READY_RELATIVE_PREFIX}{source_slug}.png",
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
        image_relative_path=f"{READY_RELATIVE_PREFIX}{source_slug}.png",
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


def _public_targets_match_source(
    base_path: Path,
    repo_path: Path,
    preflight: PreflightContext,
    *,
    post_relative: str,
    image_relative: str,
    pub_date: date,
) -> bool:
    assert preflight.source_slug is not None
    assert preflight.public_slug is not None

    source_md = (base_path / preflight.source_relative_path).resolve()
    source_png = (base_path / preflight.image_relative_path).resolve()
    public_post = (repo_path / post_relative).resolve()
    public_image = (repo_path / image_relative).resolve()

    if not source_md.is_file() or not source_png.is_file():
        return False
    if not public_post.is_file() or not public_image.is_file():
        return False

    try:
        frontmatter, body = prepare_frontmatter(
            source_md, preflight.public_slug, pub_date
        )
        expected_post = render_markdown(frontmatter, body)
        if public_post.read_text(encoding="utf-8") != expected_post:
            return False
        if public_image.read_bytes() != source_png.read_bytes():
            return False
    except (OSError, PublishError):
        return False

    return True


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


def _reconciliation_skip_reason(
    base_path: Path,
    campaign: dict[str, Any],
    preflight: PreflightContext,
    repo_path: Path,
    *,
    post_relative: str,
    image_relative: str,
    pub_date: date,
) -> str | None:
    if campaign.get("state") not in RECONCILABLE_PUBLISH_STATES:
        return RECONCILIATION_SKIPPED_STATE_NOT_ALLOWED

    if campaign.get("flow") != FLOW_A:
        return RECONCILIATION_SKIPPED_STATE_NOT_ALLOWED

    if campaign.get("source_relative_path") != preflight.source_relative_path:
        return RECONCILIATION_SKIPPED_SOURCE_MISMATCH

    if campaign.get("source_content_sha256") != preflight.source_content_sha256:
        return RECONCILIATION_SKIPPED_HASH_MISMATCH

    post_exists, image_exists = _public_target_existence(
        repo_path,
        post_relative=post_relative,
        image_relative=image_relative,
    )
    if not post_exists and not image_exists:
        return None
    if not post_exists:
        return RECONCILIATION_SKIPPED_MISSING_PUBLIC_POST
    if not image_exists:
        return RECONCILIATION_SKIPPED_MISSING_PUBLIC_IMAGE

    blog_publish = campaign.get("blog_publish") or {}
    stored_key = blog_publish.get("idempotency_key")
    if (
        stored_key is not None
        and stored_key != preflight.expected_idempotency_key
    ):
        return RECONCILIATION_SKIPPED_IDEMPOTENCY_MISMATCH

    if not _public_targets_match_source(
        base_path,
        repo_path,
        preflight,
        post_relative=post_relative,
        image_relative=image_relative,
        pub_date=pub_date,
    ):
        return RECONCILIATION_SKIPPED_PUBLIC_CONTENT_MISMATCH

    return None


def _target_exists_failure(
    preflight: PreflightContext,
    *,
    campaign: dict[str, Any],
    campaign_id: str,
    site_url: str,
    skip_reason: str | None,
    warnings: list[str],
    validation_summary: dict[str, Any],
) -> BlogPublishResult:
    blog_publish = dict(campaign.get("blog_publish") or {})
    if skip_reason:
        blog_publish["reconciliation_skip_reason"] = skip_reason
    return _failed_result(
        preflight,
        errors=[BLOG_PUBLISH_TARGET_EXISTS],
        warnings=warnings,
        validation=validation_summary,
        campaign_id=campaign_id,
        state=campaign.get("state"),
        source_public_url=_resolve_source_public_url(preflight, campaign, site_url),
        blog_publish=blog_publish,
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

    skip_reason = _reconciliation_skip_reason(
        base_path,
        campaign,
        preflight,
        repo_path,
        post_relative=post_relative,
        image_relative=image_relative,
        pub_date=pub_date,
    )
    if skip_reason is None:
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
        )

    if post_exists or image_exists:
        return _target_exists_failure(
            preflight,
            campaign=campaign,
            campaign_id=campaign_id,
            site_url=site_url,
            skip_reason=skip_reason,
            warnings=warnings,
            validation_summary=validation_summary,
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

    campaign["blog_publish"] = blog_publish
    campaign["source_public_url"] = reconciled_url

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


def publish_blog_post(
    base_path: Path,
    source_relative_path: str,
    *,
    site_url: str = DEFAULT_SITE_URL,
    public_slug_override: str | None = None,
    github_pages_repo_path: str | None = None,
    environ: dict[str, str] | None = None,
) -> BlogPublishResult:
    """Orchestrate Flow A blog publishing for one ready post."""
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
        metadata_written=metadata_written,
        metadata_error_code=metadata_error_code,
    )
    if not metadata_written:
        result.status = "failed"
    return result
