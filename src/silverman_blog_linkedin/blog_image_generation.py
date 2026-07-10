"""Blog image generation orchestration via ComfyUI."""

from __future__ import annotations

import hashlib
import os
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.blog_image_prompt import build_blog_image_prompt
from silverman_blog_linkedin.campaign_lifecycle import (
    compute_source_content_sha256,
    read_campaign_metadata,
    write_campaign_metadata,
)
from silverman_blog_linkedin.comfyui_client import (
    BLOG_IMAGE_GENERATION_COMFYUI_FAILED,
    BLOG_IMAGE_GENERATION_NOT_CONFIGURED,
    ComfyUIClientProtocol,
    ComfyUIHttpClient,
    load_workflow_template,
    workflow_has_dimension_bindings,
)
from silverman_blog_linkedin.comfyui_config import (
    ComfyUISettings,
    ComfyUISettingsLoadResult,
    load_comfyui_settings,
)
from silverman_blog_linkedin.github_pages_publish import (
    BLOG_IMAGE_PUBLIC_ASSET_HANDOFF_FAILED,
    ENV_REPO_PATH,
    IMAGES_RELATIVE,
    PublishError,
    _split_frontmatter,
    copy_public_blog_image,
    public_blog_image_relative,
    render_markdown,
    resolve_public_slug,
)
from silverman_blog_linkedin.ready_post_validation import READY_RELATIVE_PREFIX
from silverman_blog_linkedin.run_metadata import (
    generate_run_id,
    utc_now_iso,
    write_run_metadata,
)

BLOG_IMAGE_GENERATION_DISABLED = "blog_image_generation_disabled"
BLOG_IMAGE_GENERATION_FAILED = "blog_image_generation_failed"
BLOG_IMAGE_GENERATION_WRITE_FAILED = "blog_image_generation_write_failed"
BLOG_IMAGE_GENERATION_FRONTMATTER_UPDATE_FAILED = (
    "blog_image_generation_frontmatter_update_failed"
)

SKIP_REASON_GENERATION_DISABLED = "generation_disabled"
SKIP_REASON_ALREADY_VALID = "already_valid"
SKIP_REASON_PUBLIC_ASSET_REUSE = "public_asset_reuse"
SKIP_REASON_NON_CANONICAL_IMAGE = "non_canonical_image"
SKIP_REASON_NOT_APPLICABLE = "not_applicable"

WARNING_READY_SIBLING_BACKFILL_FAILED = "ready_sibling_backfill_failed"

PUBLIC_ASSET_SOURCE_EXISTING = "existing_public_asset"
PUBLIC_ASSET_SOURCE_READY_SIBLING = "ready_sibling_png"
PUBLIC_ASSET_SOURCE_COMFYUI = "comfyui_generated"

TRIGGER_BLOG_IMAGE_GENERATION = "blog_image_generation"


@dataclass
class BlogImageGenerationResult:
    status: str
    source_relative_path: str
    image_relative_path: str | None = None
    public_image_path: str | None = None
    width: int | None = None
    height: int | None = None
    workflow_controls_dimensions: bool | None = None
    prompt_hash: str | None = None
    generated_at: str | None = None
    error_code: str | None = None
    skip_reason: str | None = None
    front_matter_updated: bool = False
    metadata_written: bool = False
    metadata_error_code: str | None = None
    run_id: str | None = None
    public_asset_handoff_status: str | None = None
    public_asset_source: str | None = None
    public_repo_image_relative_path: str | None = None
    ready_sibling_backfill_status: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("front_matter_updated", None)
        if not payload.get("warnings"):
            payload.pop("warnings", None)
        return {key: value for key, value in payload.items() if value is not None}


def _canonical_public_image_path(public_slug: str) -> str:
    return f"/assets/images/{public_slug}.png"


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _comfyui_generation_enabled(settings: ComfyUISettings) -> bool:
    """Return whether ComfyUI generation is enabled via ``ComfyUISettings.enabled``."""
    return settings.generation_enabled


def _resolve_github_pages_repo_path(
    github_pages_repo_path: str | Path | None,
    environ: dict[str, str] | None,
) -> Path | None:
    if github_pages_repo_path is not None:
        raw = str(github_pages_repo_path).strip()
        if raw:
            return Path(raw).expanduser().resolve()
    env = os.environ if environ is None else environ
    raw = env.get(ENV_REPO_PATH, "").strip()
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def _public_asset_path(repo_path: Path, public_slug: str) -> Path:
    return (repo_path / IMAGES_RELATIVE / f"{public_slug}.png").resolve()


def _public_asset_readable(repo_path: Path | None, public_slug: str) -> bool:
    if repo_path is None:
        return False
    candidate = _public_asset_path(repo_path, public_slug)
    return candidate.is_file()


@dataclass(frozen=True)
class _DetectionOutcome:
    needs_action: bool
    needs_comfyui: bool
    reuse_public_asset: bool = False
    adopt_ready_sibling: bool = False
    backfill_ready_sibling: bool = False
    skip_reason: str | None = None


def _detection_outcome(
    *,
    frontmatter: dict[str, Any],
    public_slug: str,
    source_slug: str,
    base_path: Path,
    github_pages_repo_path: Path | None,
) -> _DetectionOutcome:
    """Return whether remediation is needed and whether ComfyUI must be called."""
    canonical_image = _canonical_public_image_path(public_slug)
    image_value = frontmatter.get("image")
    png_path = base_path / READY_RELATIVE_PREFIX / f"{source_slug}.png"
    png_exists = png_path.is_file()
    public_exists = _public_asset_readable(github_pages_repo_path, public_slug)
    public_repo_relative = public_blog_image_relative(public_slug)

    if not _is_blank(image_value):
        current = str(image_value).strip()
        if current != canonical_image:
            return _DetectionOutcome(
                needs_action=False,
                needs_comfyui=False,
                skip_reason=SKIP_REASON_NON_CANONICAL_IMAGE,
            )
        if public_exists and png_exists:
            return _DetectionOutcome(
                needs_action=False,
                needs_comfyui=False,
                skip_reason=SKIP_REASON_ALREADY_VALID,
            )
        if public_exists:
            return _DetectionOutcome(
                needs_action=True,
                needs_comfyui=False,
                reuse_public_asset=True,
                backfill_ready_sibling=not png_exists,
            )
        if png_exists:
            return _DetectionOutcome(
                needs_action=True,
                needs_comfyui=False,
                adopt_ready_sibling=True,
            )
        return _DetectionOutcome(needs_action=True, needs_comfyui=True)

    if public_exists:
        return _DetectionOutcome(
            needs_action=True,
            needs_comfyui=False,
            reuse_public_asset=True,
            backfill_ready_sibling=not png_exists,
        )

    if png_exists:
        return _DetectionOutcome(
            needs_action=True,
            needs_comfyui=False,
            adopt_ready_sibling=True,
        )

    return _DetectionOutcome(needs_action=True, needs_comfyui=True)


def _derive_seed(source_slug: str, prompt_hash: str) -> int:
    digest = hashlib.sha256(f"{source_slug}:{prompt_hash}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % (2**31 - 1)


def _patch_frontmatter_image(source_md: Path, public_slug: str) -> None:
    content = source_md.read_text(encoding="utf-8")
    frontmatter, body = _split_frontmatter(content)
    frontmatter["image"] = _canonical_public_image_path(public_slug)
    source_md.write_text(render_markdown(frontmatter, body), encoding="utf-8")


def _backfill_ready_sibling_from_public(
    public_png: Path,
    ready_png: Path,
) -> str:
    if ready_png.is_file():
        return "not_needed"
    try:
        ready_png.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(public_png, ready_png)
        return "copied"
    except OSError:
        return "failed"


def _handoff_failure_result(
    result: BlogImageGenerationResult,
    *,
    public_slug: str,
    base_path: Path,
    campaign_id: str | None,
    started_at: str,
    run_id: str,
) -> BlogImageGenerationResult:
    result.public_asset_handoff_status = "failed"
    result.public_repo_image_relative_path = public_blog_image_relative(public_slug)
    return _finalize_failure(
        result,
        error_code=BLOG_IMAGE_PUBLIC_ASSET_HANDOFF_FAILED,
        base_path=base_path,
        campaign_id=campaign_id,
        started_at=started_at,
        run_id=run_id,
    )


def _finalize_success(
    result: BlogImageGenerationResult,
    *,
    base_path: Path,
    campaign_id: str | None,
    started_at: str,
    run_id: str,
    status: str,
) -> BlogImageGenerationResult:
    result.status = status
    if status in ("generated", "skipped"):
        result.generated_at = utc_now_iso()
    summary = _build_metadata_summary(result)
    written, metadata_error_code = _persist_campaign_blog_image_generation(
        base_path, campaign_id, summary
    )
    result.metadata_written = written
    result.metadata_error_code = metadata_error_code
    completed_at = result.generated_at or utc_now_iso()
    _append_run_record(
        base_path,
        run_id=run_id,
        summary=summary,
        started_at=started_at,
        completed_at=completed_at,
    )
    return result


def _build_metadata_summary(result: BlogImageGenerationResult) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "status": result.status,
        "source_relative_path": result.source_relative_path,
    }
    if result.image_relative_path is not None:
        summary["image_relative_path"] = result.image_relative_path
    if result.public_image_path is not None:
        summary["public_image_path"] = result.public_image_path
    if result.width is not None:
        summary["width"] = result.width
    if result.height is not None:
        summary["height"] = result.height
    if result.workflow_controls_dimensions is not None:
        summary["workflow_controls_dimensions"] = result.workflow_controls_dimensions
    if result.prompt_hash is not None:
        summary["prompt_hash"] = result.prompt_hash
    if result.generated_at is not None:
        summary["generated_at"] = result.generated_at
    if result.error_code is not None:
        summary["error_code"] = result.error_code
    if result.skip_reason is not None:
        summary["skip_reason"] = result.skip_reason
    if result.public_asset_handoff_status is not None:
        summary["public_asset_handoff_status"] = result.public_asset_handoff_status
    if result.public_asset_source is not None:
        summary["public_asset_source"] = result.public_asset_source
    if result.public_repo_image_relative_path is not None:
        summary["public_repo_image_relative_path"] = result.public_repo_image_relative_path
    if result.ready_sibling_backfill_status is not None:
        summary["ready_sibling_backfill_status"] = result.ready_sibling_backfill_status
    if result.warnings:
        summary["warnings"] = list(result.warnings)
    return summary


def _persist_campaign_blog_image_generation(
    base_path: Path,
    campaign_id: str | None,
    summary: dict[str, Any],
) -> tuple[bool, str | None]:
    if not campaign_id:
        return False, None
    campaign = read_campaign_metadata(base_path, campaign_id)
    if campaign is None:
        return False, "campaign_not_found"
    campaign["blog_image_generation"] = summary
    write_result = write_campaign_metadata(base_path, campaign_id, campaign)
    if write_result.written:
        return True, None
    return False, write_result.error_code or "campaign_metadata_write_failed"


def _record_result_metadata(
    result: BlogImageGenerationResult,
    *,
    base_path: Path,
    campaign_id: str | None,
    started_at: str,
    run_id: str,
) -> None:
    summary = _build_metadata_summary(result)
    written, metadata_error_code = _persist_campaign_blog_image_generation(
        base_path, campaign_id, summary
    )
    result.metadata_written = written
    result.metadata_error_code = metadata_error_code
    completed_at = result.generated_at or utc_now_iso()
    _append_run_record(
        base_path,
        run_id=run_id,
        summary=summary,
        started_at=started_at,
        completed_at=completed_at,
    )


def _finalize_failure(
    result: BlogImageGenerationResult,
    *,
    error_code: str,
    base_path: Path,
    campaign_id: str | None,
    started_at: str,
    run_id: str,
) -> BlogImageGenerationResult:
    result.status = "failed"
    result.error_code = error_code
    _record_result_metadata(
        result,
        base_path=base_path,
        campaign_id=campaign_id,
        started_at=started_at,
        run_id=run_id,
    )
    return result


def _append_run_record(
    base_path: Path,
    *,
    run_id: str,
    summary: dict[str, Any],
    started_at: str,
    completed_at: str,
) -> bool:
    payload = {
        "run_id": run_id,
        "trigger": TRIGGER_BLOG_IMAGE_GENERATION,
        "started_at": started_at,
        "completed_at": completed_at,
        "status": summary.get("status"),
        "source_relative_path": summary.get("source_relative_path"),
        "image_relative_path": summary.get("image_relative_path"),
        "public_image_path": summary.get("public_image_path"),
        "width": summary.get("width"),
        "height": summary.get("height"),
        "workflow_controls_dimensions": summary.get("workflow_controls_dimensions"),
        "prompt_hash": summary.get("prompt_hash"),
        "error_code": summary.get("error_code"),
        "skip_reason": summary.get("skip_reason"),
        "public_asset_handoff_status": summary.get("public_asset_handoff_status"),
        "public_asset_source": summary.get("public_asset_source"),
        "public_repo_image_relative_path": summary.get(
            "public_repo_image_relative_path"
        ),
        "ready_sibling_backfill_status": summary.get("ready_sibling_backfill_status"),
        "warnings": summary.get("warnings"),
    }
    return write_run_metadata(base_path, run_id, payload)


def ensure_blog_image(
    base_path: Path,
    source_relative_path: str,
    *,
    config: ComfyUISettingsLoadResult | None = None,
    client: ComfyUIClientProtocol | None = None,
    dry_run: bool | None = None,
    environ: dict[str, str] | None = None,
    public_slug_override: str | None = None,
    campaign_id: str | None = None,
    github_pages_repo_path: str | Path | None = None,
) -> BlogImageGenerationResult:
    """Detect missing canonical images, optionally generate via ComfyUI, update source files."""
    try:
        return _ensure_blog_image_impl(
            base_path,
            source_relative_path,
            config=config,
            client=client,
            dry_run=dry_run,
            environ=environ,
            public_slug_override=public_slug_override,
            campaign_id=campaign_id,
            github_pages_repo_path=github_pages_repo_path,
        )
    except Exception:
        normalized = source_relative_path.replace("\\", "/").lstrip("/")
        result = BlogImageGenerationResult(
            status="failed",
            source_relative_path=normalized,
            error_code=BLOG_IMAGE_GENERATION_FAILED,
        )
        if campaign_id:
            summary = _build_metadata_summary(result)
            written, metadata_error_code = _persist_campaign_blog_image_generation(
                base_path, campaign_id, summary
            )
            result.metadata_written = written
            result.metadata_error_code = metadata_error_code
        return result


def _ensure_blog_image_impl(
    base_path: Path,
    source_relative_path: str,
    *,
    config: ComfyUISettingsLoadResult | None = None,
    client: ComfyUIClientProtocol | None = None,
    dry_run: bool | None = None,
    environ: dict[str, str] | None = None,
    public_slug_override: str | None = None,
    campaign_id: str | None = None,
    github_pages_repo_path: str | Path | None = None,
) -> BlogImageGenerationResult:
    """Internal implementation for ``ensure_blog_image``."""
    normalized = source_relative_path.replace("\\", "/").lstrip("/")
    result = BlogImageGenerationResult(
        status="skipped",
        source_relative_path=normalized,
    )

    load_result = config if config is not None else load_comfyui_settings(environ)
    settings = load_result.settings
    effective_dry_run = settings.dry_run if dry_run is None else dry_run
    repo_path = _resolve_github_pages_repo_path(github_pages_repo_path, environ)

    source_md = (base_path / normalized).resolve()
    if not source_md.is_file():
        result.status = "failed"
        result.error_code = BLOG_IMAGE_GENERATION_FAILED
        return result

    source_slug = source_md.stem
    try:
        public_slug = resolve_public_slug(source_slug, public_slug_override)
    except PublishError:
        result.status = "failed"
        result.error_code = BLOG_IMAGE_GENERATION_FAILED
        return result

    try:
        content = source_md.read_text(encoding="utf-8")
        frontmatter, body = _split_frontmatter(content)
    except (OSError, PublishError):
        result.status = "failed"
        result.error_code = BLOG_IMAGE_GENERATION_FAILED
        return result

    image_relative_path = f"{READY_RELATIVE_PREFIX}{source_slug}.png"
    public_image_path = _canonical_public_image_path(public_slug)
    public_repo_relative = public_blog_image_relative(public_slug)
    ready_png_path = base_path / image_relative_path

    result.image_relative_path = image_relative_path
    result.public_image_path = public_image_path
    result.public_repo_image_relative_path = public_repo_relative
    result.width = settings.image_width
    result.height = settings.image_height
    try:
        _workflow, workflow_bindings = load_workflow_template(settings.workflow_path)
        result.workflow_controls_dimensions = workflow_has_dimension_bindings(
            workflow_bindings
        )
    except ValueError:
        result.workflow_controls_dimensions = None

    detection = _detection_outcome(
        frontmatter=frontmatter,
        public_slug=public_slug,
        source_slug=source_slug,
        base_path=base_path,
        github_pages_repo_path=repo_path,
    )

    started_at = utc_now_iso()
    run_id = generate_run_id()
    result.run_id = run_id

    if not detection.needs_action:
        result.skip_reason = detection.skip_reason or SKIP_REASON_NOT_APPLICABLE
        if detection.skip_reason == SKIP_REASON_ALREADY_VALID:
            result.public_asset_handoff_status = "reused"
            result.public_asset_source = PUBLIC_ASSET_SOURCE_EXISTING
            result.ready_sibling_backfill_status = "not_needed"
        summary = _build_metadata_summary(result)
        written, metadata_error_code = _persist_campaign_blog_image_generation(
            base_path, campaign_id, summary
        )
        result.metadata_written = written
        result.metadata_error_code = metadata_error_code
        return result

    needs_handoff = detection.reuse_public_asset or detection.adopt_ready_sibling

    if needs_handoff and repo_path is None:
        return _handoff_failure_result(
            result,
            public_slug=public_slug,
            base_path=base_path,
            campaign_id=campaign_id,
            started_at=started_at,
            run_id=run_id,
        )

    if detection.reuse_public_asset:
        if effective_dry_run:
            result.status = "dry_run"
            result.public_asset_handoff_status = "reused"
            result.public_asset_source = PUBLIC_ASSET_SOURCE_EXISTING
            if detection.backfill_ready_sibling:
                result.ready_sibling_backfill_status = "copied"
            else:
                result.ready_sibling_backfill_status = "not_needed"
            completed_at = utc_now_iso()
            summary = _build_metadata_summary(result)
            written, metadata_error_code = _persist_campaign_blog_image_generation(
                base_path, campaign_id, summary
            )
            result.metadata_written = written
            result.metadata_error_code = metadata_error_code
            _append_run_record(
                base_path,
                run_id=run_id,
                summary=summary,
                started_at=started_at,
                completed_at=completed_at,
            )
            return result

        needs_frontmatter_patch = _is_blank(frontmatter.get("image")) or str(
            frontmatter.get("image", "")
        ).strip() != public_image_path
        if needs_frontmatter_patch:
            try:
                _patch_frontmatter_image(source_md, public_slug)
                result.front_matter_updated = True
            except (OSError, PublishError):
                result.error_code = BLOG_IMAGE_GENERATION_FRONTMATTER_UPDATE_FAILED
                return _finalize_failure(
                    result,
                    error_code=BLOG_IMAGE_GENERATION_FRONTMATTER_UPDATE_FAILED,
                    base_path=base_path,
                    campaign_id=campaign_id,
                    started_at=started_at,
                    run_id=run_id,
                )

        assert repo_path is not None
        public_png = _public_asset_path(repo_path, public_slug)
        result.public_asset_handoff_status = "reused"
        result.public_asset_source = PUBLIC_ASSET_SOURCE_EXISTING

        if detection.backfill_ready_sibling:
            backfill_status = _backfill_ready_sibling_from_public(
                public_png, ready_png_path
            )
            result.ready_sibling_backfill_status = backfill_status
            if backfill_status == "failed":
                result.warnings.append(WARNING_READY_SIBLING_BACKFILL_FAILED)
        else:
            result.ready_sibling_backfill_status = "not_needed"

        result.skip_reason = SKIP_REASON_PUBLIC_ASSET_REUSE
        return _finalize_success(
            result,
            base_path=base_path,
            campaign_id=campaign_id,
            started_at=started_at,
            run_id=run_id,
            status="skipped",
        )

    if detection.adopt_ready_sibling:
        if effective_dry_run:
            result.status = "dry_run"
            result.public_asset_handoff_status = "copied"
            result.public_asset_source = PUBLIC_ASSET_SOURCE_READY_SIBLING
            completed_at = utc_now_iso()
            summary = _build_metadata_summary(result)
            written, metadata_error_code = _persist_campaign_blog_image_generation(
                base_path, campaign_id, summary
            )
            result.metadata_written = written
            result.metadata_error_code = metadata_error_code
            _append_run_record(
                base_path,
                run_id=run_id,
                summary=summary,
                started_at=started_at,
                completed_at=completed_at,
            )
            return result

        assert repo_path is not None
        handoff = copy_public_blog_image(ready_png_path, repo_path, public_slug)
        if handoff.status == "failed":
            return _handoff_failure_result(
                result,
                public_slug=public_slug,
                base_path=base_path,
                campaign_id=campaign_id,
                started_at=started_at,
                run_id=run_id,
            )

        result.public_asset_handoff_status = handoff.status
        result.public_asset_source = PUBLIC_ASSET_SOURCE_READY_SIBLING
        result.ready_sibling_backfill_status = "not_needed"

        needs_frontmatter_patch = _is_blank(frontmatter.get("image")) or str(
            frontmatter.get("image", "")
        ).strip() != public_image_path
        if needs_frontmatter_patch:
            try:
                _patch_frontmatter_image(source_md, public_slug)
                result.front_matter_updated = True
            except (OSError, PublishError):
                return _finalize_failure(
                    result,
                    error_code=BLOG_IMAGE_GENERATION_FRONTMATTER_UPDATE_FAILED,
                    base_path=base_path,
                    campaign_id=campaign_id,
                    started_at=started_at,
                    run_id=run_id,
                )

        return _finalize_success(
            result,
            base_path=base_path,
            campaign_id=campaign_id,
            started_at=started_at,
            run_id=run_id,
            status="generated",
        )

    if not _comfyui_generation_enabled(settings):
        result.skip_reason = SKIP_REASON_GENERATION_DISABLED
        return _finalize_failure(
            result,
            error_code=BLOG_IMAGE_GENERATION_DISABLED,
            base_path=base_path,
            campaign_id=campaign_id,
            started_at=started_at,
            run_id=run_id,
        )

    if load_result.config_invalid:
        return _finalize_failure(
            result,
            error_code=BLOG_IMAGE_GENERATION_NOT_CONFIGURED,
            base_path=base_path,
            campaign_id=campaign_id,
            started_at=started_at,
            run_id=run_id,
        )

    if not settings.base_url:
        return _finalize_failure(
            result,
            error_code=BLOG_IMAGE_GENERATION_NOT_CONFIGURED,
            base_path=base_path,
            campaign_id=campaign_id,
            started_at=started_at,
            run_id=run_id,
        )

    title = str(frontmatter.get("title") or source_slug)
    prompt = build_blog_image_prompt(
        title=title,
        description=frontmatter.get("description"),
        tags=frontmatter.get("tags"),
        categories=frontmatter.get("categories"),
        body=body,
    )
    result.prompt_hash = prompt.prompt_hash
    seed = _derive_seed(source_slug, prompt.prompt_hash)

    if effective_dry_run:
        result.status = "dry_run"
        result.public_asset_handoff_status = "copied"
        result.public_asset_source = PUBLIC_ASSET_SOURCE_COMFYUI
        completed_at = utc_now_iso()
        summary = _build_metadata_summary(result)
        written, metadata_error_code = _persist_campaign_blog_image_generation(
            base_path, campaign_id, summary
        )
        result.metadata_written = written
        result.metadata_error_code = metadata_error_code
        _append_run_record(
            base_path,
            run_id=run_id,
            summary=summary,
            started_at=started_at,
            completed_at=completed_at,
        )
        return result

    owns_client = False
    comfy_client = client
    if comfy_client is None:
        comfy_client = ComfyUIHttpClient(settings)
        owns_client = True

    try:
        generation = comfy_client.generate_image(
            positive_prompt=prompt.positive,
            negative_prompt=prompt.negative,
            width=settings.image_width,
            height=settings.image_height,
            seed=seed,
        )
    finally:
        if owns_client and isinstance(comfy_client, ComfyUIHttpClient):
            comfy_client.close()

    if generation.error_code or not generation.png_bytes:
        propagated_code = generation.error_code or BLOG_IMAGE_GENERATION_COMFYUI_FAILED
        return _finalize_failure(
            result,
            error_code=propagated_code,
            base_path=base_path,
            campaign_id=campaign_id,
            started_at=started_at,
            run_id=run_id,
        )

    try:
        ready_png_path.parent.mkdir(parents=True, exist_ok=True)
        ready_png_path.write_bytes(generation.png_bytes)
    except OSError:
        return _finalize_failure(
            result,
            error_code=BLOG_IMAGE_GENERATION_WRITE_FAILED,
            base_path=base_path,
            campaign_id=campaign_id,
            started_at=started_at,
            run_id=run_id,
        )

    if repo_path is None:
        return _handoff_failure_result(
            result,
            public_slug=public_slug,
            base_path=base_path,
            campaign_id=campaign_id,
            started_at=started_at,
            run_id=run_id,
        )

    handoff = copy_public_blog_image(ready_png_path, repo_path, public_slug)
    if handoff.status == "failed":
        return _handoff_failure_result(
            result,
            public_slug=public_slug,
            base_path=base_path,
            campaign_id=campaign_id,
            started_at=started_at,
            run_id=run_id,
        )

    result.public_asset_handoff_status = handoff.status
    result.public_asset_source = PUBLIC_ASSET_SOURCE_COMFYUI
    result.ready_sibling_backfill_status = "not_needed"

    needs_frontmatter_patch = _is_blank(frontmatter.get("image")) or str(
        frontmatter.get("image", "")
    ).strip() != public_image_path

    if needs_frontmatter_patch:
        try:
            _patch_frontmatter_image(source_md, public_slug)
            result.front_matter_updated = True
        except (OSError, PublishError):
            return _finalize_failure(
                result,
                error_code=BLOG_IMAGE_GENERATION_FRONTMATTER_UPDATE_FAILED,
                base_path=base_path,
                campaign_id=campaign_id,
                started_at=started_at,
                run_id=run_id,
            )

    return _finalize_success(
        result,
        base_path=base_path,
        campaign_id=campaign_id,
        started_at=started_at,
        run_id=run_id,
        status="generated",
    )


def recompute_source_hash_after_generation(
    base_path: Path,
    source_relative_path: str,
) -> str | None:
    """Re-read source markdown and return updated content hash."""
    source_md = (base_path / source_relative_path).resolve()
    if not source_md.is_file():
        return None
    try:
        content = source_md.read_text(encoding="utf-8")
    except OSError:
        return None
    return compute_source_content_sha256(content)
