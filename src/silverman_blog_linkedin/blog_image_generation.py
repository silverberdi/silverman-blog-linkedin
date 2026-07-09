"""Blog image generation orchestration via ComfyUI."""

from __future__ import annotations

import hashlib
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
    BLOG_IMAGE_GENERATION_TIMEOUT,
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
    PublishError,
    _split_frontmatter,
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
SKIP_REASON_NON_CANONICAL_IMAGE = "non_canonical_image"
SKIP_REASON_NOT_APPLICABLE = "not_applicable"

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
    run_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("front_matter_updated", None)
        return {key: value for key, value in payload.items() if value is not None}


def _canonical_public_image_path(public_slug: str) -> str:
    return f"/assets/images/{public_slug}.png"


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


@dataclass(frozen=True)
class _DetectionOutcome:
    needs_action: bool
    needs_comfyui: bool
    skip_reason: str | None = None


def _detection_outcome(
    *,
    frontmatter: dict[str, Any],
    public_slug: str,
    source_slug: str,
    base_path: Path,
) -> _DetectionOutcome:
    """Return whether remediation is needed and whether ComfyUI must be called."""
    canonical_image = _canonical_public_image_path(public_slug)
    image_value = frontmatter.get("image")
    png_path = base_path / READY_RELATIVE_PREFIX / f"{source_slug}.png"
    png_exists = png_path.is_file()

    if not _is_blank(image_value):
        current = str(image_value).strip()
        if current != canonical_image:
            return _DetectionOutcome(
                needs_action=False,
                needs_comfyui=False,
                skip_reason=SKIP_REASON_NON_CANONICAL_IMAGE,
            )
        if png_exists:
            return _DetectionOutcome(
                needs_action=False,
                needs_comfyui=False,
                skip_reason=SKIP_REASON_ALREADY_VALID,
            )
        return _DetectionOutcome(needs_action=True, needs_comfyui=True)

    if png_exists:
        return _DetectionOutcome(needs_action=True, needs_comfyui=False)

    return _DetectionOutcome(needs_action=True, needs_comfyui=True)


def _derive_seed(source_slug: str, prompt_hash: str) -> int:
    digest = hashlib.sha256(f"{source_slug}:{prompt_hash}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % (2**31 - 1)


def _patch_frontmatter_image(source_md: Path, public_slug: str) -> None:
    content = source_md.read_text(encoding="utf-8")
    frontmatter, body = _split_frontmatter(content)
    frontmatter["image"] = _canonical_public_image_path(public_slug)
    source_md.write_text(render_markdown(frontmatter, body), encoding="utf-8")


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
    return summary


def _persist_campaign_blog_image_generation(
    base_path: Path,
    campaign_id: str | None,
    summary: dict[str, Any],
) -> bool:
    if not campaign_id:
        return False
    campaign = read_campaign_metadata(base_path, campaign_id)
    if campaign is None:
        return False
    campaign["blog_image_generation"] = summary
    write_result = write_campaign_metadata(base_path, campaign_id, campaign)
    return write_result.written


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
) -> BlogImageGenerationResult:
    """Detect missing canonical images, optionally generate via ComfyUI, update source files."""
    normalized = source_relative_path.replace("\\", "/").lstrip("/")
    result = BlogImageGenerationResult(
        status="skipped",
        source_relative_path=normalized,
    )

    load_result = config if config is not None else load_comfyui_settings(environ)
    settings = load_result.settings
    effective_dry_run = settings.dry_run if dry_run is None else dry_run

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
    result.image_relative_path = image_relative_path
    result.public_image_path = public_image_path
    result.width = settings.image_width
    result.height = settings.image_height
    try:
        _workflow, workflow_bindings = load_workflow_template(settings.workflow_path)
        result.workflow_controls_dimensions = not workflow_has_dimension_bindings(
            workflow_bindings
        )
    except ValueError:
        result.workflow_controls_dimensions = None

    detection = _detection_outcome(
        frontmatter=frontmatter,
        public_slug=public_slug,
        source_slug=source_slug,
        base_path=base_path,
    )

    if not detection.needs_action:
        result.skip_reason = detection.skip_reason or SKIP_REASON_NOT_APPLICABLE
        summary = _build_metadata_summary(result)
        result.metadata_written = _persist_campaign_blog_image_generation(
            base_path, campaign_id, summary
        )
        return result

    if not settings.enabled:
        result.skip_reason = SKIP_REASON_GENERATION_DISABLED
        summary = _build_metadata_summary(result)
        result.metadata_written = _persist_campaign_blog_image_generation(
            base_path, campaign_id, summary
        )
        return result

    if load_result.config_invalid:
        result.status = "failed"
        result.error_code = BLOG_IMAGE_GENERATION_NOT_CONFIGURED
        summary = _build_metadata_summary(result)
        result.metadata_written = _persist_campaign_blog_image_generation(
            base_path, campaign_id, summary
        )
        return result

    if not settings.base_url:
        result.status = "failed"
        result.error_code = BLOG_IMAGE_GENERATION_NOT_CONFIGURED
        summary = _build_metadata_summary(result)
        result.metadata_written = _persist_campaign_blog_image_generation(
            base_path, campaign_id, summary
        )
        return result

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

    started_at = utc_now_iso()
    run_id = generate_run_id()
    result.run_id = run_id

    if effective_dry_run:
        result.status = "dry_run"
        completed_at = utc_now_iso()
        summary = _build_metadata_summary(result)
        result.metadata_written = _persist_campaign_blog_image_generation(
            base_path, campaign_id, summary
        )
        _append_run_record(
            base_path,
            run_id=run_id,
            summary=summary,
            started_at=started_at,
            completed_at=completed_at,
        )
        return result

    if not detection.needs_comfyui:
        try:
            _patch_frontmatter_image(source_md, public_slug)
            result.front_matter_updated = True
        except (OSError, PublishError):
            result.status = "failed"
            result.error_code = BLOG_IMAGE_GENERATION_FRONTMATTER_UPDATE_FAILED
            completed_at = utc_now_iso()
            summary = _build_metadata_summary(result)
            result.metadata_written = _persist_campaign_blog_image_generation(
                base_path, campaign_id, summary
            )
            _append_run_record(
                base_path,
                run_id=run_id,
                summary=summary,
                started_at=started_at,
                completed_at=completed_at,
            )
            return result

        result.status = "generated"
        result.generated_at = utc_now_iso()
        completed_at = result.generated_at
        summary = _build_metadata_summary(result)
        result.metadata_written = _persist_campaign_blog_image_generation(
            base_path, campaign_id, summary
        )
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
        result.status = "failed"
        result.error_code = generation.error_code or BLOG_IMAGE_GENERATION_COMFYUI_FAILED
        completed_at = utc_now_iso()
        summary = _build_metadata_summary(result)
        result.metadata_written = _persist_campaign_blog_image_generation(
            base_path, campaign_id, summary
        )
        _append_run_record(
            base_path,
            run_id=run_id,
            summary=summary,
            started_at=started_at,
            completed_at=completed_at,
        )
        return result

    png_path = base_path / image_relative_path
    try:
        png_path.parent.mkdir(parents=True, exist_ok=True)
        png_path.write_bytes(generation.png_bytes)
    except OSError:
        result.status = "failed"
        result.error_code = BLOG_IMAGE_GENERATION_WRITE_FAILED
        completed_at = utc_now_iso()
        summary = _build_metadata_summary(result)
        result.metadata_written = _persist_campaign_blog_image_generation(
            base_path, campaign_id, summary
        )
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
            result.status = "failed"
            result.error_code = BLOG_IMAGE_GENERATION_FRONTMATTER_UPDATE_FAILED
            completed_at = utc_now_iso()
            summary = _build_metadata_summary(result)
            result.metadata_written = _persist_campaign_blog_image_generation(
                base_path, campaign_id, summary
            )
            _append_run_record(
                base_path,
                run_id=run_id,
                summary=summary,
                started_at=started_at,
                completed_at=completed_at,
            )
            return result

    result.status = "generated"
    result.generated_at = utc_now_iso()
    completed_at = result.generated_at
    summary = _build_metadata_summary(result)
    result.metadata_written = _persist_campaign_blog_image_generation(
        base_path, campaign_id, summary
    )
    _append_run_record(
        base_path,
        run_id=run_id,
        summary=summary,
        started_at=started_at,
        completed_at=completed_at,
    )
    return result


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
