"""Flow A LinkedIn derivative package generation orchestration."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from urllib.parse import urlparse
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.campaign_lifecycle import (
    ACTOR_WORKER,
    CANONICAL_VARIANT_IDS,
    FLOW_A,
    FLOW_B,
    METADATA_CAMPAIGNS_RELATIVE,
    STATE_BLOG_PUBLISHED,
    STATE_DERIVATIVES_GENERATED,
    STATE_DERIVATIVES_PENDING,
    STATE_DISTRIBUTION_COMPLETE,
    STATE_DISTRIBUTION_SCHEDULED,
    STATE_FLOW_A_COMPLETE,
    build_derivative_idempotency_key,
    compute_source_content_sha256,
    read_campaign_metadata,
    transition_state,
    write_campaign_metadata,
)
from silverman_blog_linkedin.deepseek_client import (
    DeepSeekGenerationResult,
    generate_linkedin_draft_content,
)
from silverman_blog_linkedin.deepseek_config import DeepSeekSettings, load_deepseek_settings
from silverman_blog_linkedin.file_reader import normalize_relative_path
from silverman_blog_linkedin.linkedin_prompt import build_chat_messages
from silverman_blog_linkedin.run_metadata import PROVIDER_DEEPSEEK, utc_now_iso

GENERATED_RELATIVE = "linkedin-posts/generated"

LINKEDIN_PACKAGE_CAMPAIGN_NOT_FOUND = "linkedin_package_campaign_not_found"
LINKEDIN_PACKAGE_FLOW_NOT_ALLOWED = "linkedin_package_flow_not_allowed"
LINKEDIN_PACKAGE_INVALID_CAMPAIGN_STATE = "linkedin_package_invalid_campaign_state"
LINKEDIN_PACKAGE_MISSING_SOURCE_PUBLIC_URL = "linkedin_package_missing_source_public_url"
LINKEDIN_PACKAGE_SOURCE_MISSING = "linkedin_package_source_missing"
LINKEDIN_PACKAGE_SOURCE_HASH_CHANGED = "linkedin_package_source_hash_changed"
LINKEDIN_PACKAGE_PUBLIC_URL_CHANGED = "linkedin_package_public_url_changed"
LINKEDIN_PACKAGE_TARGET_EXISTS = "linkedin_package_target_exists"
LINKEDIN_PACKAGE_GENERATION_FAILED = "linkedin_package_generation_failed"
LINKEDIN_PACKAGE_METADATA_WRITE_FAILED = "linkedin_package_metadata_write_failed"
LINKEDIN_PACKAGE_INVALID_VARIANT = "linkedin_package_invalid_variant"
LINKEDIN_PACKAGE_NO_VARIANTS = "linkedin_package_no_variants"
LINKEDIN_PACKAGE_GENERATED_DIR_NOT_READY = "linkedin_package_generated_dir_not_ready"
LINKEDIN_PACKAGE_GENERATED_DIR_NOT_WRITABLE = "linkedin_package_generated_dir_not_writable"

PACKAGE_ELIGIBLE_STATES = frozenset(
    {
        STATE_BLOG_PUBLISHED,
        STATE_DERIVATIVES_PENDING,
        STATE_DERIVATIVES_GENERATED,
    }
)

PACKAGE_INVALID_STATES = frozenset(
    {
        STATE_DISTRIBUTION_SCHEDULED,
        STATE_DISTRIBUTION_COMPLETE,
        STATE_FLOW_A_COMPLETE,
    }
)

DEFAULT_VARIANT_EDITORIAL_MAP: dict[str, dict[str, str]] = {
    "executive-recruiter": {
        "audience": "recruiters and hiring managers for senior architecture roles",
        "tone": "executive, hireable judgment",
    },
    "technical-architect": {
        "audience": "software architects and senior developers",
        "tone": "technical depth, design trade-offs",
    },
    "engineering-leadership": {
        "audience": "engineering managers and technical leaders",
        "tone": "leadership, delivery implications",
    },
    "short-provocative": {
        "audience": "senior ICs and architecture practitioners",
        "tone": "concise, pattern-interrupt",
    },
}

GenerateContentFn = Callable[..., DeepSeekGenerationResult]


@dataclass
class LinkedInPackageResult:
    status: str
    campaign_id: str | None = None
    state: str | None = None
    package_id: str | None = None
    source_relative_path: str | None = None
    source_public_url: str | None = None
    source_content_sha256: str | None = None
    variants: list[dict[str, Any]] = field(default_factory=list)
    package: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata_written: bool = False
    metadata_error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_package_idempotency_key(
    *,
    campaign_id: str,
    source_content_sha256: str,
    variant_ids: list[str],
    flow: str,
) -> str:
    """Build package-level idempotency key with sorted variant list."""
    sorted_variants = ",".join(sorted(variant_ids))
    return f"package:{campaign_id}:{source_content_sha256}:{sorted_variants}:{flow}"


def _package_id(campaign_id: str) -> str:
    return f"{campaign_id}-pkg"


def _artifact_relative_path(campaign_id: str, variant_id: str) -> str:
    return f"{GENERATED_RELATIVE}/{campaign_id}/{variant_id}.md"


def _find_campaign_by_source_path(
    base_path: Path, source_relative_path: str
) -> dict[str, Any] | None:
    campaigns_dir = base_path / METADATA_CAMPAIGNS_RELATIVE
    if not campaigns_dir.is_dir():
        return None
    normalized = normalize_relative_path(source_relative_path)
    for metadata_path in campaigns_dir.glob("*.json"):
        try:
            data = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("source_relative_path") == normalized:
            return data
    return None


def _resolve_campaign(
    base_path: Path,
    *,
    campaign_id: str | None,
    source_relative_path: str | None,
) -> dict[str, Any] | None:
    if campaign_id:
        return read_campaign_metadata(base_path, campaign_id)
    if source_relative_path:
        return _find_campaign_by_source_path(base_path, source_relative_path)
    return None


def _resolve_variant_ids(requested: list[str] | None) -> tuple[list[str] | None, str | None]:
    if requested is None:
        return sorted(CANONICAL_VARIANT_IDS), None
    if not requested:
        return None, LINKEDIN_PACKAGE_NO_VARIANTS
    for variant_id in requested:
        if variant_id not in CANONICAL_VARIANT_IDS:
            return None, LINKEDIN_PACKAGE_INVALID_VARIANT
    return sorted(set(requested)), None


def _count_url_occurrences(content: str, source_public_url: str) -> int:
    return content.count(source_public_url)


def _normalize_url_parts(url: str) -> tuple[str, str, str]:
    parsed = urlparse(url.strip().rstrip("/"))
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    return scheme, netloc, path


def _site_url_compatible(site_url: str, source_public_url: str) -> bool:
    """Check optional site_url base against campaign source_public_url (scheme/host/path prefix)."""
    site_scheme, site_netloc, site_path = _normalize_url_parts(site_url)
    src_scheme, src_netloc, src_path = _normalize_url_parts(source_public_url)
    if site_scheme != src_scheme or site_netloc != src_netloc:
        return False
    if not site_path:
        return True
    return src_path == site_path or src_path.startswith(f"{site_path}/")


def _generation_failure_errors(provider_error: str | None = None) -> list[str]:
    errors = [LINKEDIN_PACKAGE_GENERATION_FAILED]
    if provider_error and provider_error != LINKEDIN_PACKAGE_GENERATION_FAILED:
        errors.append(provider_error)
    return errors


def _prepare_variant_bytes(content: str) -> bytes:
    text = content
    if text and not text.endswith("\n"):
        text = text + "\n"
    return text.encode("utf-8")


def _check_generated_dir_ready(base_path: Path) -> str | None:
    generated_dir = base_path / GENERATED_RELATIVE
    if generated_dir.exists() and not generated_dir.is_dir():
        return LINKEDIN_PACKAGE_GENERATED_DIR_NOT_READY
    return None


def _ensure_generated_dirs(base_path: Path, campaign_id: str) -> str | None:
    readiness_error = _check_generated_dir_ready(base_path)
    if readiness_error:
        return readiness_error

    generated_dir = base_path / GENERATED_RELATIVE
    campaign_dir = generated_dir / campaign_id
    try:
        campaign_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return LINKEDIN_PACKAGE_GENERATED_DIR_NOT_WRITABLE

    if not os.access(generated_dir, os.W_OK) or not os.access(campaign_dir, os.W_OK):
        return LINKEDIN_PACKAGE_GENERATED_DIR_NOT_WRITABLE
    return None


def write_generated_variant_file(
    base_path: Path,
    *,
    campaign_id: str,
    variant_id: str,
    content: str,
) -> tuple[str | None, str | None, str | None]:
    """Write variant artifact with exclusive create. Returns path, sha256, error_code."""
    artifact_relative = _artifact_relative_path(campaign_id, variant_id)
    artifact_path = base_path / artifact_relative
    raw_bytes = _prepare_variant_bytes(content)
    content_sha256 = hashlib.sha256(raw_bytes).hexdigest()

    try:
        with open(artifact_path, "xb") as handle:
            handle.write(raw_bytes)
    except FileExistsError:
        return None, None, LINKEDIN_PACKAGE_TARGET_EXISTS
    except OSError:
        return None, None, LINKEDIN_PACKAGE_GENERATION_FAILED

    return artifact_relative, content_sha256, None


def _variant_metadata_entry(
    *,
    variant_id: str,
    campaign: dict[str, Any],
    source_public_url: str,
    artifact_relative_path: str,
    derivative_content_sha256: str,
    generated_at: str,
    provider: str,
    model: str,
) -> dict[str, Any]:
    editorial = DEFAULT_VARIANT_EDITORIAL_MAP[variant_id]
    campaign_id = campaign["campaign_id"]
    source_content_sha256 = campaign["source_content_sha256"]
    return {
        "variant": variant_id,
        "audience": editorial["audience"],
        "tone": editorial["tone"],
        "source_public_url": source_public_url,
        "source_relative_path": campaign["source_relative_path"],
        "campaign_id": campaign_id,
        "source_content_sha256": source_content_sha256,
        "derivative_content_sha256": derivative_content_sha256,
        "artifact_relative_path": artifact_relative_path,
        "idempotency_key": build_derivative_idempotency_key(
            campaign_id=campaign_id,
            source_content_sha256=source_content_sha256,
            variant=variant_id,
            flow=FLOW_A,
        ),
        "generated_at": generated_at,
        "provider": provider,
        "model": model,
    }


def _variant_summary(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "variant": entry["variant"],
        "artifact_relative_path": entry["artifact_relative_path"],
        "derivative_content_sha256": entry["derivative_content_sha256"],
        "idempotency_key": entry["idempotency_key"],
        "provider": entry.get("provider"),
        "model": entry.get("model"),
        "generated_at": entry.get("generated_at"),
    }


def _get_variant_metadata_map(campaign: dict[str, Any]) -> dict[str, dict[str, Any]]:
    variants = campaign.get("variants") or []
    return {
        entry["variant"]: entry
        for entry in variants
        if isinstance(entry, dict) and entry.get("variant")
    }


def _check_idempotent_completed(
    campaign: dict[str, Any],
    *,
    variant_ids: list[str],
    package_idempotency_key: str,
    source_content_sha256: str,
    base_path: Path,
) -> bool:
    if campaign.get("state") != STATE_DERIVATIVES_GENERATED:
        return False
    if campaign.get("source_content_sha256") != source_content_sha256:
        return False
    package = campaign.get("linkedin_package") or {}
    if package.get("idempotency_key") != package_idempotency_key:
        return False

    metadata_map = _get_variant_metadata_map(campaign)
    for variant_id in variant_ids:
        entry = metadata_map.get(variant_id)
        if entry is None:
            return False
        artifact_relative = entry.get("artifact_relative_path")
        derivative_hash = entry.get("derivative_content_sha256")
        if not artifact_relative or not derivative_hash:
            return False
        artifact_path = base_path / artifact_relative
        if not artifact_path.is_file():
            return False
        on_disk_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        if on_disk_hash != derivative_hash:
            return False
    return True


def _check_orphan_artifacts(
    base_path: Path,
    campaign: dict[str, Any],
    *,
    variant_ids: list[str],
    package_idempotency_key: str,
) -> str | None:
    metadata_map = _get_variant_metadata_map(campaign)
    for variant_id in variant_ids:
        artifact_relative = _artifact_relative_path(campaign["campaign_id"], variant_id)
        artifact_path = base_path / artifact_relative
        if not artifact_path.exists():
            continue
        entry = metadata_map.get(variant_id)
        if entry is None:
            return LINKEDIN_PACKAGE_TARGET_EXISTS
        if campaign.get("linkedin_package", {}).get("idempotency_key") != package_idempotency_key:
            return LINKEDIN_PACKAGE_TARGET_EXISTS
        on_disk_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        if entry.get("derivative_content_sha256") != on_disk_hash:
            return LINKEDIN_PACKAGE_TARGET_EXISTS
    return None


def _generate_variant_content(
    *,
    markdown_content: str,
    variant_id: str,
    source_public_url: str,
    topic_theme: str | None,
    deepseek_settings: DeepSeekSettings,
    generate_content: GenerateContentFn,
) -> tuple[str | None, str | None]:
    editorial = DEFAULT_VARIANT_EDITORIAL_MAP[variant_id]
    messages = build_chat_messages(
        markdown_content=markdown_content,
        audience=editorial["audience"],
        tone=editorial["tone"],
        variant=variant_id,
        source_public_url=source_public_url,
        topic_theme=topic_theme,
    )
    result = generate_content(deepseek_settings, messages)
    if result.error_code:
        return None, result.error_code
    if not result.content:
        return None, LINKEDIN_PACKAGE_GENERATION_FAILED
    return result.content, None


def _failed_result(
    *,
    campaign: dict[str, Any] | None,
    errors: list[str],
    warnings: list[str] | None = None,
    metadata_written: bool = False,
    metadata_error_code: str | None = None,
    package: dict[str, Any] | None = None,
    variants: list[dict[str, Any]] | None = None,
) -> LinkedInPackageResult:
    return LinkedInPackageResult(
        status="failed",
        campaign_id=campaign.get("campaign_id") if campaign else None,
        state=campaign.get("state") if campaign else None,
        package_id=(
            (campaign.get("linkedin_package") or {}).get("package_id")
            if campaign
            else None
        ),
        source_relative_path=campaign.get("source_relative_path") if campaign else None,
        source_public_url=campaign.get("source_public_url") if campaign else None,
        source_content_sha256=campaign.get("source_content_sha256") if campaign else None,
        variants=variants or [],
        package=package,
        errors=errors,
        warnings=warnings or list(campaign.get("warnings") or []) if campaign else [],
        metadata_written=metadata_written,
        metadata_error_code=metadata_error_code,
    )


def _completed_result(
    campaign: dict[str, Any],
    *,
    variant_entries: list[dict[str, Any]],
    metadata_written: bool,
    metadata_error_code: str | None = None,
    errors: list[str] | None = None,
) -> LinkedInPackageResult:
    package = dict(campaign.get("linkedin_package") or {})
    return LinkedInPackageResult(
        status="completed",
        campaign_id=campaign["campaign_id"],
        state=campaign["state"],
        package_id=package.get("package_id"),
        source_relative_path=campaign.get("source_relative_path"),
        source_public_url=campaign.get("source_public_url"),
        source_content_sha256=campaign.get("source_content_sha256"),
        variants=[_variant_summary(entry) for entry in variant_entries],
        package=package,
        errors=errors or [],
        warnings=list(campaign.get("warnings") or []),
        metadata_written=metadata_written,
        metadata_error_code=metadata_error_code,
    )


def generate_linkedin_package(
    base_path: Path,
    *,
    campaign_id: str | None = None,
    source_relative_path: str | None = None,
    variants: list[str] | None = None,
    topic_theme: str | None = None,
    site_url: str | None = None,
    environ: dict[str, str] | None = None,
    generate_content: GenerateContentFn | None = None,
) -> LinkedInPackageResult:
    """Generate Flow A multi-variant LinkedIn package for one campaign."""
    campaign = _resolve_campaign(
        base_path,
        campaign_id=campaign_id,
        source_relative_path=source_relative_path,
    )
    if campaign is None:
        return LinkedInPackageResult(
            status="failed",
            errors=[LINKEDIN_PACKAGE_CAMPAIGN_NOT_FOUND],
        )

    if campaign.get("flow") == FLOW_B:
        return _failed_result(campaign=campaign, errors=[LINKEDIN_PACKAGE_FLOW_NOT_ALLOWED])

    state = campaign.get("state")
    if state in PACKAGE_INVALID_STATES or state not in PACKAGE_ELIGIBLE_STATES:
        return _failed_result(
            campaign=campaign, errors=[LINKEDIN_PACKAGE_INVALID_CAMPAIGN_STATE]
        )

    source_public_url = campaign.get("source_public_url")
    if not source_public_url:
        return _failed_result(
            campaign=campaign, errors=[LINKEDIN_PACKAGE_MISSING_SOURCE_PUBLIC_URL]
        )

    if site_url and not _site_url_compatible(site_url, source_public_url):
        return _failed_result(
            campaign=campaign, errors=[LINKEDIN_PACKAGE_PUBLIC_URL_CHANGED]
        )

    source_relative = campaign.get("source_relative_path")
    if not source_relative:
        return _failed_result(campaign=campaign, errors=[LINKEDIN_PACKAGE_SOURCE_MISSING])

    source_path = base_path / source_relative
    if not source_path.is_file():
        return _failed_result(campaign=campaign, errors=[LINKEDIN_PACKAGE_SOURCE_MISSING])

    try:
        markdown_content = source_path.read_text(encoding="utf-8")
    except OSError:
        return _failed_result(campaign=campaign, errors=[LINKEDIN_PACKAGE_SOURCE_MISSING])

    on_disk_hash = compute_source_content_sha256(markdown_content)
    stored_hash = campaign.get("source_content_sha256")
    if stored_hash and stored_hash != on_disk_hash:
        return _failed_result(
            campaign=campaign, errors=[LINKEDIN_PACKAGE_SOURCE_HASH_CHANGED]
        )

    variant_ids, variant_error = _resolve_variant_ids(variants)
    if variant_error:
        return _failed_result(campaign=campaign, errors=[variant_error])
    assert variant_ids is not None

    resolved_campaign_id = campaign["campaign_id"]
    package_idempotency_key = build_package_idempotency_key(
        campaign_id=resolved_campaign_id,
        source_content_sha256=on_disk_hash,
        variant_ids=variant_ids,
        flow=FLOW_A,
    )

    if _check_idempotent_completed(
        campaign,
        variant_ids=variant_ids,
        package_idempotency_key=package_idempotency_key,
        source_content_sha256=on_disk_hash,
        base_path=base_path,
    ):
        metadata_map = _get_variant_metadata_map(campaign)
        variant_entries = [metadata_map[variant_id] for variant_id in variant_ids]
        return _completed_result(
            campaign,
            variant_entries=variant_entries,
            metadata_written=False,
        )

    orphan_error = _check_orphan_artifacts(
        base_path,
        campaign,
        variant_ids=variant_ids,
        package_idempotency_key=package_idempotency_key,
    )
    if orphan_error:
        return _failed_result(campaign=campaign, errors=[orphan_error])

    dir_error = _check_generated_dir_ready(base_path)
    if dir_error:
        return _failed_result(campaign=campaign, errors=[dir_error])

    deepseek_load = load_deepseek_settings(environ)
    if deepseek_load.config_invalid or deepseek_load.settings is None:
        return _failed_result(campaign=campaign, errors=["deepseek_config_invalid"])

    deepseek_settings = deepseek_load.settings
    if not deepseek_settings.is_configured:
        return _failed_result(campaign=campaign, errors=["deepseek_api_key_missing"])

    ensure_error = _ensure_generated_dirs(base_path, resolved_campaign_id)
    if ensure_error:
        return _failed_result(campaign=campaign, errors=[ensure_error])

    content_generator = generate_content or generate_linkedin_draft_content
    working_campaign = deepcopy(campaign)
    history_len_before = len(working_campaign.get("state_history") or [])

    if working_campaign.get("state") == STATE_BLOG_PUBLISHED:
        try:
            transition_state(
                working_campaign,
                STATE_DERIVATIVES_PENDING,
                reason="LinkedIn derivative package generation started",
                actor=ACTOR_WORKER,
            )
        except Exception:
            return _failed_result(
                campaign=working_campaign,
                errors=[LINKEDIN_PACKAGE_INVALID_CAMPAIGN_STATE],
            )

        write_result = write_campaign_metadata(
            base_path, resolved_campaign_id, working_campaign
        )
        if not write_result.written:
            return _failed_result(
                campaign=working_campaign,
                errors=[LINKEDIN_PACKAGE_METADATA_WRITE_FAILED],
                metadata_written=False,
                metadata_error_code=write_result.error_code
                or LINKEDIN_PACKAGE_METADATA_WRITE_FAILED,
            )

    generated_entries: list[dict[str, Any]] = []
    generated_at = utc_now_iso()
    model_name = deepseek_settings.model

    for variant_id in variant_ids:
        content, gen_error = _generate_variant_content(
            markdown_content=markdown_content,
            variant_id=variant_id,
            source_public_url=source_public_url,
            topic_theme=topic_theme,
            deepseek_settings=deepseek_settings,
            generate_content=content_generator,
        )
        if gen_error:
            return _failed_result(
                campaign=working_campaign,
                errors=_generation_failure_errors(gen_error),
            )
        assert content is not None

        url_count = _count_url_occurrences(content, source_public_url)
        if url_count != 1:
            return _failed_result(
                campaign=working_campaign,
                errors=[LINKEDIN_PACKAGE_GENERATION_FAILED],
            )

        artifact_relative, derivative_hash, write_error = write_generated_variant_file(
            base_path,
            campaign_id=resolved_campaign_id,
            variant_id=variant_id,
            content=content,
        )
        if write_error:
            return _failed_result(campaign=working_campaign, errors=[write_error])

        assert artifact_relative is not None
        assert derivative_hash is not None
        generated_entries.append(
            _variant_metadata_entry(
                variant_id=variant_id,
                campaign=working_campaign,
                source_public_url=source_public_url,
                artifact_relative_path=artifact_relative,
                derivative_content_sha256=derivative_hash,
                generated_at=generated_at,
                provider=PROVIDER_DEEPSEEK,
                model=model_name,
            )
        )

    metadata_map = _get_variant_metadata_map(working_campaign)
    for entry in generated_entries:
        metadata_map[entry["variant"]] = entry
    working_campaign["variants"] = list(metadata_map.values())
    working_campaign["linkedin_package"] = {
        "package_id": _package_id(resolved_campaign_id),
        "idempotency_key": package_idempotency_key,
        "package_status": "generated",
        "generated_at": generated_at,
        "source_public_url": source_public_url,
        "source_relative_path": source_relative,
        "source_content_sha256": on_disk_hash,
        "variant_ids": variant_ids,
    }

    try:
        transition_state(
            working_campaign,
            STATE_DERIVATIVES_GENERATED,
            reason="LinkedIn derivative package generated",
            actor=ACTOR_WORKER,
        )
    except Exception:
        return _failed_result(
            campaign=working_campaign,
            errors=[LINKEDIN_PACKAGE_INVALID_CAMPAIGN_STATE],
            variants=[_variant_summary(entry) for entry in generated_entries],
            package=working_campaign.get("linkedin_package"),
        )

    if len(working_campaign.get("state_history") or []) <= history_len_before:
        return _failed_result(
            campaign=working_campaign,
            errors=[LINKEDIN_PACKAGE_INVALID_CAMPAIGN_STATE],
            variants=[_variant_summary(entry) for entry in generated_entries],
            package=working_campaign.get("linkedin_package"),
        )

    write_result = write_campaign_metadata(
        base_path, resolved_campaign_id, working_campaign
    )
    if not write_result.written:
        return _failed_result(
            campaign=working_campaign,
            errors=[LINKEDIN_PACKAGE_METADATA_WRITE_FAILED],
            variants=[_variant_summary(entry) for entry in generated_entries],
            package=working_campaign.get("linkedin_package"),
            metadata_written=False,
            metadata_error_code=write_result.error_code
            or LINKEDIN_PACKAGE_METADATA_WRITE_FAILED,
        )

    return _completed_result(
        working_campaign,
        variant_entries=generated_entries,
        metadata_written=True,
    )
