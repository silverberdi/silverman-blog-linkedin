"""US-079: Flow B blog draft + hero image generation into pending-approval/.

Accepts US-078 topic payloads, generates Markdown via DeepSeek (provider seam),
applies blocking anti-AI heuristics, writes ``blog-posts/pending-approval/``
pairs + sidecar metadata, and requests hero images via ComfyUI blog image path.

MUST NOT write under ``blog-posts/ready/``.
MUST NOT invoke Flow A publish/package/schedule, Git publication, or LinkedIn API.
MUST NOT enable LinkedIn publication.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Literal

from silverman_blog_linkedin.blog_draft_generation_provider import (
    DEFAULT_BLOG_DRAFT_PROVIDER,
    ENV_BLOG_DRAFT_PROVIDER,
    PROVIDER_DEEPSEEK,
    BlogDraftGenerationProvider,
    create_blog_draft_provider,
)
from silverman_blog_linkedin.blog_image_generation import (
    BLOG_IMAGE_GENERATION_DISABLED,
    ensure_editorial_blog_image,
)
from silverman_blog_linkedin.comfyui_client import ComfyUIClientProtocol
from silverman_blog_linkedin.deepseek_config import load_deepseek_settings
from silverman_blog_linkedin.flow_b_gap_operator_settings import (
    SETTINGS_KEY_MAX_DRAFTS_PER_WEEKLY_RUN,
    GapOperatorSettingsSnapshot,
    load_gap_operator_settings,
)
from silverman_blog_linkedin.flow_b_gap_operator_settings_store import (
    GapOperatorSettingsStore,
)
from silverman_blog_linkedin.flow_b_pending_approval_writer import (
    ERROR_PENDING_DIR_NOT_READY,
    ERROR_PENDING_DIR_NOT_WRITABLE,
    PENDING_APPROVAL_PREFIX,
    READY_PREFIX,
    check_pending_approval_dir_ready,
    remove_pending_approval_partial,
    write_pending_approval_markdown,
    write_pending_approval_sidecar,
)
from silverman_blog_linkedin.flow_b_topic_discovery import (
    DiscoveredTopic,
    default_editorial_canon_path,
    extract_canon_section,
)
from silverman_blog_linkedin.ready_post_validation import (
    AI_OPENING_PATTERNS,
    GENERIC_ENDING_PATTERNS,
    GENERIC_TRANSITION_PATTERN,
    INFLUENCER_TONE_PATTERN,
    STYLE_DRIFT_PATTERN,
    WARNING_AI_OPENING,
    WARNING_GENERIC_ENDING,
    WARNING_GENERIC_TRANSITION,
    WARNING_INFLUENCER_TONE,
    WARNING_STYLE_DRIFT,
    WARNING_WEAK_CTA,
    WEAK_CTA_PATTERN,
)
from silverman_blog_linkedin.run_metadata import utc_now_iso

STATUS_DRAFTS_GENERATED: Literal["drafts_generated"] = "drafts_generated"
STATUS_DRAFTS_PARTIAL: Literal["drafts_partial"] = "drafts_partial"
STATUS_DRAFT_GENERATION_FAILED: Literal["draft_generation_failed"] = (
    "draft_generation_failed"
)
STATUS_DRAFT_GENERATION_DRY_RUN: Literal["draft_generation_dry_run"] = (
    "draft_generation_dry_run"
)

ERROR_DRAFT_GENERATION_FAILED = "draft_generation_failed"
ERROR_CONFIG_INVALID = "draft_config_invalid"
ERROR_CANON_MISSING = "editorial_canon_missing"
ERROR_CANON_SECTION_MISSING = "editorial_canon_section_missing"
ERROR_SETTINGS_UNAVAILABLE = "gap_operator_settings_unavailable"
ERROR_TOPICS_EMPTY = "draft_topics_empty"
ERROR_TOPICS_DUPLICATE = "draft_topics_duplicate_topic_id"
ERROR_TOPIC_INVALID = "draft_topic_invalid"
ERROR_ANTI_AI_BLOCKED = "anti_ai_blocked"
ERROR_COMFYUI_DISABLED = "comfyui_disabled"
ERROR_PROVIDER_EMPTY = "draft_provider_empty_response"

IMAGE_STATUS_GENERATED = "generated"
IMAGE_STATUS_DRY_RUN = "dry_run"
IMAGE_STATUS_SKIPPED = "skipped"
IMAGE_STATUS_FAILED = "failed"
IMAGE_STATUS_PENDING = "pending"

ANTI_AI_PASSED = "passed"
ANTI_AI_BLOCKED = "blocked"

REQUIRED_DRAFT_CANON_ANCHORS = (
    "brand-positioning",
    "content-pillars",
    "topic-boundaries",
    "blog-post-rules",
    "flow-a-vs-flow-b",
    "anti-ai-writing-rules",
)

_ISO_WEEK_RE = re.compile(r"^\d{4}-W\d{2}$")
_LOCAL_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_TITLE_LINE_RE = re.compile(r"^title:\s*[\"']?(.*?)[\"']?\s*$", re.MULTILINE | re.IGNORECASE)
_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_TITLE_AS_FIRST_SENTENCE_RE = re.compile(
    r"^(?:i wrote (?:a |an )?(?:post|blog post) about)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DraftTopicInput:
    """US-078 topic payload accepted by draft generation."""

    thesis: str
    referent_positioning: str
    rationale: str
    topic_id: str
    pillar_hints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "thesis": self.thesis,
            "referent_positioning": self.referent_positioning,
            "rationale": self.rationale,
            "topic_id": self.topic_id,
        }
        if self.pillar_hints:
            payload["pillar_hints"] = list(self.pillar_hints)
        return payload

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> DraftTopicInput | None:
        thesis = _as_nonempty_str(raw.get("thesis"))
        referent = _as_nonempty_str(
            raw.get("referent_positioning") or raw.get("referentPositioning")
        )
        rationale = _as_nonempty_str(raw.get("rationale"))
        topic_id = _as_nonempty_str(raw.get("topic_id") or raw.get("topicId"))
        if thesis is None or referent is None or rationale is None or topic_id is None:
            return None
        hints_raw = raw.get("pillar_hints") or raw.get("pillarHints") or []
        pillar_hints: list[str] = []
        if isinstance(hints_raw, list):
            for hint in hints_raw:
                text = _as_nonempty_str(hint)
                if text is not None:
                    pillar_hints.append(text)
        return cls(
            thesis=thesis,
            referent_positioning=referent,
            rationale=rationale,
            topic_id=topic_id,
            pillar_hints=pillar_hints,
        )

    @classmethod
    def from_discovered(cls, topic: DiscoveredTopic) -> DraftTopicInput:
        return cls(
            thesis=topic.thesis,
            referent_positioning=topic.referent_positioning,
            rationale=topic.rationale,
            topic_id=topic.topic_id,
            pillar_hints=list(topic.pillar_hints),
        )


@dataclass(frozen=True)
class DraftItemResult:
    """Per-topic generation outcome."""

    topic_id: str
    status: Literal["generated", "failed", "blocked", "dry_run"]
    blog_relative_path: str | None = None
    image_relative_path: str | None = None
    metadata_relative_path: str | None = None
    title: str | None = None
    slug: str | None = None
    image_status: str | None = None
    image_error_code: str | None = None
    anti_ai_status: str | None = None
    anti_ai_violations: list[str] = field(default_factory=list)
    error_code: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "topic_id": self.topic_id,
            "status": self.status,
        }
        if self.blog_relative_path is not None:
            payload["blog_relative_path"] = self.blog_relative_path
        if self.image_relative_path is not None:
            payload["image_relative_path"] = self.image_relative_path
        if self.metadata_relative_path is not None:
            payload["metadata_relative_path"] = self.metadata_relative_path
        if self.title is not None:
            payload["title"] = self.title
        if self.slug is not None:
            payload["slug"] = self.slug
        if self.image_status is not None:
            payload["image_status"] = self.image_status
        if self.image_error_code is not None:
            payload["image_error_code"] = self.image_error_code
        if self.anti_ai_status is not None:
            payload["anti_ai_status"] = self.anti_ai_status
        if self.anti_ai_violations:
            payload["anti_ai_violations"] = list(self.anti_ai_violations)
        if self.error_code is not None:
            payload["error_code"] = self.error_code
        if self.error is not None:
            payload["error"] = self.error
        return payload


@dataclass(frozen=True)
class BlogDraftGenerationResult:
    """Orchestration result for HTTP / internal callers."""

    status: Literal[
        "drafts_generated",
        "drafts_partial",
        "draft_generation_failed",
        "draft_generation_dry_run",
    ]
    provider: str | None
    drafts: list[DraftItemResult] = field(default_factory=list)
    max_drafts_per_weekly_run: int | None = None
    settings_source: Literal["defaults", "database"] | None = None
    gap_context: dict[str, Any] | None = None
    observed_at_utc: str = ""
    error_code: str | None = None
    error: str | None = None
    dry_run: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status,
            "provider": self.provider,
            "drafts": [item.to_dict() for item in self.drafts],
            "max_drafts_per_weekly_run": self.max_drafts_per_weekly_run,
            "settings_source": self.settings_source,
            "observed_at_utc": self.observed_at_utc or utc_now_iso(),
        }
        if self.gap_context is not None:
            payload["gap_context"] = self.gap_context
        if self.dry_run:
            payload["dry_run"] = True
        if self.error_code is not None:
            payload["error_code"] = self.error_code
        if self.error is not None:
            payload["error"] = self.error
        return payload


def load_draft_canon_sections(
    canon_path: Path,
) -> tuple[dict[str, str] | None, str | None]:
    """Load required canon sections for draft prompts or return ``(None, error_code)``."""
    if not canon_path.is_file():
        return None, ERROR_CANON_MISSING
    text = canon_path.read_text(encoding="utf-8")
    sections: dict[str, str] = {}
    for anchor in REQUIRED_DRAFT_CANON_ANCHORS:
        body = extract_canon_section(text, anchor)
        if body is None:
            return None, ERROR_CANON_SECTION_MISSING
        sections[anchor] = body
    return sections, None


def collect_flow_b_anti_ai_violations(
    markdown: str,
    *,
    title: str | None = None,
) -> list[str]:
    """Blocking anti-AI heuristics for Flow B generated blogs (canon #anti-ai-writing-rules)."""
    violations: list[str] = []
    body = _body_after_frontmatter(markdown)
    body_stripped = body.strip()
    if not body_stripped:
        return ["anti_ai_empty_body"]

    opening_window = body_stripped[:500]
    for pattern in AI_OPENING_PATTERNS:
        if pattern.search(opening_window):
            violations.append(WARNING_AI_OPENING)
            break

    # Title-as-first-sentence / "I wrote a post about…"
    first_paragraph = body_stripped.split("\n\n", 1)[0]
    first_plain = re.sub(r"^#+\s*", "", first_paragraph).strip()
    if _TITLE_AS_FIRST_SENTENCE_RE.search(first_plain):
        violations.append("anti_ai_title_as_opener")
    if title:
        normalized_title = " ".join(title.lower().split())
        normalized_first = " ".join(first_plain.lower().split())
        if normalized_title and normalized_first.startswith(normalized_title):
            # Allow H1 that matches title; block body restating title as first prose sentence
            if not first_plain.lstrip().startswith("#"):
                # first_plain already stripped heading markers above for prose check
                h1_match = _H1_RE.search(body_stripped)
                prose_start = body_stripped
                if h1_match:
                    prose_start = body_stripped[h1_match.end() :].lstrip()
                first_prose = prose_start.split("\n\n", 1)[0].strip()
                first_prose_norm = " ".join(first_prose.lower().split())
                if first_prose_norm.startswith(normalized_title):
                    violations.append("anti_ai_title_restated")

    closing_window = body_stripped[-500:]
    for pattern in GENERIC_ENDING_PATTERNS:
        if pattern.search(closing_window):
            violations.append(WARNING_GENERIC_ENDING)
            break

    transition_matches = GENERIC_TRANSITION_PATTERN.findall(body_stripped)
    if len(transition_matches) >= 3:
        violations.append(WARNING_GENERIC_TRANSITION)

    if WEAK_CTA_PATTERN.search(body_stripped):
        violations.append(WARNING_WEAK_CTA)

    if INFLUENCER_TONE_PATTERN.search(body_stripped):
        violations.append(WARNING_INFLUENCER_TONE)

    if STYLE_DRIFT_PATTERN.search(body_stripped):
        violations.append(WARNING_STYLE_DRIFT)

    return violations


def build_blog_draft_messages(
    *,
    sections: dict[str, str],
    topic: DraftTopicInput,
    target_week: str | None,
    empty_days: list[str] | None,
    image_filename: str,
    generation_date: str,
) -> list[dict[str, str]]:
    """Assemble system/user messages for authority-constrained blog Markdown."""
    gap_lines: list[str] = []
    if target_week:
        gap_lines.append(f"Target ISO week (informational scheduling hint): {target_week}")
    if empty_days:
        gap_lines.append(
            "Empty local days (informational; not a filesystem inventory): "
            + ", ".join(empty_days)
        )
    gap_block = "\n".join(gap_lines) if gap_lines else "(no gap context provided)"
    pillar_block = (
        ", ".join(topic.pillar_hints) if topic.pillar_hints else "(none provided)"
    )

    system = (
        "You are the Flow B blog-draft writer for Silverio Bernal "
        "(Solutions Architect). Write a complete senior, practical blog post in "
        "English that positions him as a referent — not a news spreader. "
        "Follow the editorial canon. Avoid AI-sounding openings, transitions, "
        "endings, and influencer tone. Return ONLY Markdown with YAML front matter. "
        "Do not wrap the response in markdown fences."
    )
    user = (
        "Generate one complete blog Markdown document.\n\n"
        "## Authority / brand positioning\n"
        f"{sections['brand-positioning']}\n\n"
        "## Content pillars\n"
        f"{sections['content-pillars']}\n\n"
        "## Topic boundaries\n"
        f"{sections['topic-boundaries']}\n\n"
        "## Blog post rules\n"
        f"{sections['blog-post-rules']}\n\n"
        "## Flow A vs Flow B\n"
        f"{sections['flow-a-vs-flow-b']}\n\n"
        "## Anti-AI writing rules (MUST obey; blocking for Flow B)\n"
        f"{sections['anti-ai-writing-rules']}\n\n"
        "## Topic to materialize\n"
        f"- thesis: {topic.thesis}\n"
        f"- referent_positioning: {topic.referent_positioning}\n"
        f"- rationale: {topic.rationale}\n"
        f"- topic_id: {topic.topic_id}\n"
        f"- pillar_hints: {pillar_block}\n\n"
        "## Optional gap-batch context (scheduling hints only)\n"
        f"{gap_block}\n\n"
        "## Output contract\n"
        "Return Markdown starting with YAML front matter containing at least:\n"
        f"- title: (derived from thesis; human-readable)\n"
        f"- date: {generation_date}\n"
        "- description: short SEO/social summary\n"
        f"- image: {image_filename}\n"
        "- flow: flow_b\n"
        f"- topic_id: {topic.topic_id}\n"
        "Then an H1 matching the title and a structured practical body "
        "(problem/decision opening within first two paragraphs; trade-offs; "
        "senior tone). No LinkedIn drafts embedded. No TODO placeholders."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def validate_draft_request_fields(
    *,
    topics: list[Any] | None,
    target_week: str | None,
    empty_days: list[str] | None,
) -> list[str]:
    """Return field-level validation error codes (empty when OK)."""
    errors: list[str] = []
    if topics is None or not isinstance(topics, list) or len(topics) == 0:
        errors.append(ERROR_TOPICS_EMPTY)
    if target_week is not None and not _ISO_WEEK_RE.match(target_week.strip()):
        errors.append("draft_target_week_invalid")
    if empty_days is not None:
        if not isinstance(empty_days, list):
            errors.append("draft_empty_days_invalid")
        else:
            for day in empty_days:
                if not isinstance(day, str) or not _LOCAL_DATE_RE.match(day.strip()):
                    errors.append("draft_empty_days_invalid")
                    break
    return errors


def parse_and_clamp_topics(
    topics_raw: list[Any],
    *,
    max_drafts: int,
) -> tuple[list[DraftTopicInput] | None, str | None]:
    """Parse topic objects, reject duplicates, clamp to max_drafts (prefer clamp)."""
    parsed: list[DraftTopicInput] = []
    seen_ids: set[str] = set()
    for item in topics_raw:
        if not isinstance(item, dict):
            return None, ERROR_TOPIC_INVALID
        topic = DraftTopicInput.from_mapping(item)
        if topic is None:
            return None, ERROR_TOPIC_INVALID
        if topic.topic_id in seen_ids:
            return None, ERROR_TOPICS_DUPLICATE
        seen_ids.add(topic.topic_id)
        parsed.append(topic)

    if not parsed:
        return None, ERROR_TOPICS_EMPTY

    ceiling = max(1, int(max_drafts))
    return parsed[:ceiling], None


def extract_title_from_markdown(markdown: str, *, fallback: str) -> str:
    """Prefer front-matter title, then H1, then fallback thesis."""
    match = _FRONTMATTER_RE.match(markdown.lstrip())
    if match:
        title_match = _TITLE_LINE_RE.search(match.group(1))
        if title_match:
            title = title_match.group(1).strip()
            if title:
                return title
    h1 = _H1_RE.search(markdown)
    if h1:
        return h1.group(1).strip()
    return fallback


def ensure_required_frontmatter(
    markdown: str,
    *,
    topic: DraftTopicInput,
    image_filename: str,
    generation_date: str,
) -> str:
    """Ensure YAML front matter includes flow_b fields and sibling image reference."""
    stripped = markdown.lstrip()
    match = _FRONTMATTER_RE.match(stripped)
    required = {
        "flow": "flow_b",
        "topic_id": topic.topic_id,
        "image": image_filename,
        "date": generation_date,
    }
    if match:
        fm_body = match.group(1)
        remainder = stripped[match.end() :]
        for key, value in required.items():
            key_re = re.compile(rf"^{re.escape(key)}\s*:", re.MULTILINE | re.IGNORECASE)
            if not key_re.search(fm_body):
                fm_body = f"{fm_body.rstrip()}\n{key}: {value}\n"
            elif key == "image":
                fm_body = re.sub(
                    rf"^image\s*:.*$",
                    f"image: {image_filename}",
                    fm_body,
                    count=1,
                    flags=re.MULTILINE | re.IGNORECASE,
                )
            elif key == "flow":
                fm_body = re.sub(
                    r"^flow\s*:.*$",
                    "flow: flow_b",
                    fm_body,
                    count=1,
                    flags=re.MULTILINE | re.IGNORECASE,
                )
            elif key == "topic_id":
                fm_body = re.sub(
                    r"^topic_id\s*:.*$",
                    f"topic_id: {topic.topic_id}",
                    fm_body,
                    count=1,
                    flags=re.MULTILINE | re.IGNORECASE,
                )
        if not re.search(r"^title\s*:", fm_body, re.MULTILINE | re.IGNORECASE):
            fm_body = f"title: {topic.thesis}\n{fm_body}"
        if not re.search(r"^description\s*:", fm_body, re.MULTILINE | re.IGNORECASE):
            fm_body = f"{fm_body.rstrip()}\ndescription: {topic.rationale}\n"
        return f"---\n{fm_body.strip()}\n---\n\n{remainder.lstrip()}"

    title = topic.thesis
    return (
        "---\n"
        f"title: {title}\n"
        f"date: {generation_date}\n"
        f"description: {topic.rationale}\n"
        f"image: {image_filename}\n"
        "flow: flow_b\n"
        f"topic_id: {topic.topic_id}\n"
        "---\n\n"
        f"# {title}\n\n"
        f"{stripped}"
    )


def snapshot_ready_folder(base_path: Path) -> dict[str, set[str]]:
    """Snapshot filenames under ready/ (and pending-approval) for write-guard tests."""
    result: dict[str, set[str]] = {}
    for relative in ("blog-posts/ready", "blog-posts/pending-approval"):
        folder = base_path / relative
        if folder.is_dir():
            result[relative] = {path.name for path in folder.iterdir() if path.is_file()}
        else:
            result[relative] = set()
    return result


def generate_flow_b_blog_drafts(
    base_path: Path,
    *,
    topics: list[Any],
    target_week: str | None = None,
    empty_days: list[str] | None = None,
    dry_run: bool = False,
    store: GapOperatorSettingsStore | None = None,
    environ: dict[str, str] | None = None,
    settings_snapshot: GapOperatorSettingsSnapshot | None = None,
    provider: BlogDraftGenerationProvider | None = None,
    comfyui_client: ComfyUIClientProtocol | None = None,
    canon_path: Path | None = None,
) -> BlogDraftGenerationResult:
    """Generate Flow B blog drafts into pending-approval/; never writes ready/."""
    observed = utc_now_iso()
    env = os.environ if environ is None else environ
    generation_date = date.today().isoformat()

    try:
        snapshot = settings_snapshot or load_gap_operator_settings(
            store=store,
            environ=env,
        )
    except RuntimeError:
        return BlogDraftGenerationResult(
            status=STATUS_DRAFT_GENERATION_FAILED,
            provider=None,
            observed_at_utc=observed,
            error_code=ERROR_SETTINGS_UNAVAILABLE,
            error="Gap operator settings store is unavailable",
        )

    max_drafts = int(
        snapshot.settings.get(SETTINGS_KEY_MAX_DRAFTS_PER_WEEKLY_RUN) or 2
    )
    gap_context = _build_gap_context(target_week, empty_days)

    field_errors = validate_draft_request_fields(
        topics=topics,
        target_week=target_week,
        empty_days=empty_days,
    )
    if field_errors:
        return BlogDraftGenerationResult(
            status=STATUS_DRAFT_GENERATION_FAILED,
            provider=None,
            max_drafts_per_weekly_run=max_drafts,
            settings_source=snapshot.source,
            gap_context=gap_context,
            observed_at_utc=observed,
            error_code=field_errors[0],
            error=_operator_message_for_code(field_errors[0]),
        )

    clamped, topic_error = parse_and_clamp_topics(topics, max_drafts=max_drafts)
    if clamped is None:
        return BlogDraftGenerationResult(
            status=STATUS_DRAFT_GENERATION_FAILED,
            provider=None,
            max_drafts_per_weekly_run=max_drafts,
            settings_source=snapshot.source,
            gap_context=gap_context,
            observed_at_utc=observed,
            error_code=topic_error or ERROR_TOPIC_INVALID,
            error=_operator_message_for_code(topic_error or ERROR_TOPIC_INVALID),
        )

    resolved_canon = canon_path or default_editorial_canon_path()
    sections, canon_error = load_draft_canon_sections(resolved_canon)
    if sections is None:
        return BlogDraftGenerationResult(
            status=STATUS_DRAFT_GENERATION_FAILED,
            provider=None,
            max_drafts_per_weekly_run=max_drafts,
            settings_source=snapshot.source,
            gap_context=gap_context,
            observed_at_utc=observed,
            error_code=canon_error,
            error=_operator_message_for_code(canon_error or ERROR_DRAFT_GENERATION_FAILED),
        )

    provider_name = (
        env.get(ENV_BLOG_DRAFT_PROVIDER, DEFAULT_BLOG_DRAFT_PROVIDER).strip().lower()
        or DEFAULT_BLOG_DRAFT_PROVIDER
    )

    if dry_run:
        dry_items = [
            DraftItemResult(
                topic_id=topic.topic_id,
                status="dry_run",
                blog_relative_path=(
                    f"{PENDING_APPROVAL_PREFIX}<would-generate>-{topic.topic_id}.md"
                ),
                image_relative_path=(
                    f"{PENDING_APPROVAL_PREFIX}<would-generate>-{topic.topic_id}.png"
                ),
                metadata_relative_path=(
                    f"{PENDING_APPROVAL_PREFIX}"
                    f"<would-generate>-{topic.topic_id}.flow-b.json"
                ),
                title=topic.thesis,
                image_status=IMAGE_STATUS_DRY_RUN,
                anti_ai_status=ANTI_AI_PASSED,
            )
            for topic in clamped
        ]
        return BlogDraftGenerationResult(
            status=STATUS_DRAFT_GENERATION_DRY_RUN,
            provider=provider_name,
            drafts=dry_items,
            max_drafts_per_weekly_run=max_drafts,
            settings_source=snapshot.source,
            gap_context=gap_context,
            observed_at_utc=observed,
            dry_run=True,
        )

    readiness = check_pending_approval_dir_ready(base_path)
    if not readiness.ready:
        code = readiness.error_code or ERROR_PENDING_DIR_NOT_READY
        return BlogDraftGenerationResult(
            status=STATUS_DRAFT_GENERATION_FAILED,
            provider=provider_name,
            max_drafts_per_weekly_run=max_drafts,
            settings_source=snapshot.source,
            gap_context=gap_context,
            observed_at_utc=observed,
            error_code=code,
            error=_operator_message_for_code(code),
        )

    if provider is None:
        deepseek_load = load_deepseek_settings(env)
        if deepseek_load.config_invalid or deepseek_load.settings is None:
            return BlogDraftGenerationResult(
                status=STATUS_DRAFT_GENERATION_FAILED,
                provider=PROVIDER_DEEPSEEK,
                max_drafts_per_weekly_run=max_drafts,
                settings_source=snapshot.source,
                gap_context=gap_context,
                observed_at_utc=observed,
                error_code=ERROR_CONFIG_INVALID,
                error="DeepSeek configuration is invalid",
            )
        if not deepseek_load.settings.is_configured:
            return BlogDraftGenerationResult(
                status=STATUS_DRAFT_GENERATION_FAILED,
                provider=PROVIDER_DEEPSEEK,
                max_drafts_per_weekly_run=max_drafts,
                settings_source=snapshot.source,
                gap_context=gap_context,
                observed_at_utc=observed,
                error_code="deepseek_api_key_missing",
                error="DeepSeek API key is missing",
            )
        provider = create_blog_draft_provider(
            provider_name,
            settings=deepseek_load.settings,
        )

    draft_results: list[DraftItemResult] = []
    for topic in clamped:
        draft_results.append(
            _generate_one_draft(
                base_path,
                topic=topic,
                sections=sections,
                target_week=target_week,
                empty_days=empty_days,
                gap_context=gap_context,
                generation_date=generation_date,
                provider=provider,
                comfyui_client=comfyui_client,
                environ=env,
                observed_at_utc=observed,
            )
        )

    successes = [item for item in draft_results if item.status == "generated"]
    if len(successes) == len(draft_results) and successes:
        overall: Literal[
            "drafts_generated",
            "drafts_partial",
            "draft_generation_failed",
            "draft_generation_dry_run",
        ] = STATUS_DRAFTS_GENERATED
        error_code = None
        error = None
    elif successes:
        overall = STATUS_DRAFTS_PARTIAL
        error_code = None
        error = None
    else:
        overall = STATUS_DRAFT_GENERATION_FAILED
        first_fail = draft_results[0] if draft_results else None
        error_code = (
            first_fail.error_code if first_fail else ERROR_DRAFT_GENERATION_FAILED
        )
        error = (
            first_fail.error
            if first_fail
            else _operator_message_for_code(ERROR_DRAFT_GENERATION_FAILED)
        )

    # Guard: never claim success if any path escaped into ready/
    for item in draft_results:
        for path in (
            item.blog_relative_path,
            item.image_relative_path,
            item.metadata_relative_path,
        ):
            if path and path.replace("\\", "/").startswith(READY_PREFIX):
                return BlogDraftGenerationResult(
                    status=STATUS_DRAFT_GENERATION_FAILED,
                    provider=provider.name,
                    drafts=draft_results,
                    max_drafts_per_weekly_run=max_drafts,
                    settings_source=snapshot.source,
                    gap_context=gap_context,
                    observed_at_utc=observed,
                    error_code="pending_approval_ready_write_forbidden",
                    error="Draft generation attempted a ready/ write",
                )

    return BlogDraftGenerationResult(
        status=overall,
        provider=provider.name,
        drafts=draft_results,
        max_drafts_per_weekly_run=max_drafts,
        settings_source=snapshot.source,
        gap_context=gap_context,
        observed_at_utc=observed,
        error_code=error_code,
        error=error,
    )


def _generate_one_draft(
    base_path: Path,
    *,
    topic: DraftTopicInput,
    sections: dict[str, str],
    target_week: str | None,
    empty_days: list[str] | None,
    gap_context: dict[str, Any] | None,
    generation_date: str,
    provider: BlogDraftGenerationProvider,
    comfyui_client: ComfyUIClientProtocol | None,
    environ: dict[str, str],
    observed_at_utc: str,
) -> DraftItemResult:
    """Process a single topic sequentially: text → anti-AI → write → image → sidecar."""
    placeholder_image = "pending-hero.png"
    messages = build_blog_draft_messages(
        sections=sections,
        topic=topic,
        target_week=target_week,
        empty_days=empty_days,
        image_filename=placeholder_image,
        generation_date=generation_date,
    )
    provider_result = provider.generate_blog_draft(messages)
    if provider_result.error_code:
        return DraftItemResult(
            topic_id=topic.topic_id,
            status="failed",
            error_code=provider_result.error_code,
            error=_operator_message_for_code(provider_result.error_code),
            anti_ai_status=None,
        )

    raw = provider_result.content
    if raw is None or not raw.strip():
        return DraftItemResult(
            topic_id=topic.topic_id,
            status="failed",
            error_code=ERROR_PROVIDER_EMPTY,
            error="Blog draft provider returned no usable Markdown content",
        )

    title = extract_title_from_markdown(raw, fallback=topic.thesis)
    # Provisional image name until slug is known — rewritten after path allocation
    markdown = ensure_required_frontmatter(
        raw,
        topic=topic,
        image_filename=placeholder_image,
        generation_date=generation_date,
    )

    violations = collect_flow_b_anti_ai_violations(markdown, title=title)
    if violations:
        # Prefer validate-before-write: do not leave approval-ready package
        return DraftItemResult(
            topic_id=topic.topic_id,
            status="blocked",
            title=title,
            anti_ai_status=ANTI_AI_BLOCKED,
            anti_ai_violations=violations,
            error_code=ERROR_ANTI_AI_BLOCKED,
            error="Generated Markdown failed Flow B anti-AI writing rules",
        )

    write_result = write_pending_approval_markdown(
        base_path,
        markdown=markdown,
        title_or_thesis=title,
        topic_id=topic.topic_id,
    )
    if write_result.errors or write_result.blog_relative_path is None:
        code = write_result.errors[0] if write_result.errors else ERROR_DRAFT_GENERATION_FAILED
        return DraftItemResult(
            topic_id=topic.topic_id,
            status="failed",
            title=title,
            anti_ai_status=ANTI_AI_PASSED,
            error_code=code,
            error=_operator_message_for_code(code),
        )

    assert write_result.slug is not None
    assert write_result.image_relative_path is not None
    assert write_result.metadata_relative_path is not None
    slug = write_result.slug
    # ComfyUI blog image path expects canonical public image front matter
    # (sibling PNG on disk is still written under pending-approval/).
    canonical_image = f"/assets/images/{slug}.png"
    finalized = ensure_required_frontmatter(
        markdown,
        topic=topic,
        image_filename=canonical_image,
        generation_date=generation_date,
    )
    md_path = base_path / write_result.blog_relative_path
    try:
        if not finalized.endswith("\n"):
            finalized = finalized + "\n"
        md_path.write_text(finalized, encoding="utf-8")
    except OSError:
        remove_pending_approval_partial(
            base_path,
            blog_relative_path=write_result.blog_relative_path,
        )
        return DraftItemResult(
            topic_id=topic.topic_id,
            status="failed",
            title=title,
            anti_ai_status=ANTI_AI_PASSED,
            error_code="pending_approval_write_failed",
            error="Failed to finalize pending-approval Markdown",
        )

    image_result = ensure_editorial_blog_image(
        base_path,
        write_result.blog_relative_path,
        client=comfyui_client,
        dry_run=False,
        environ=environ,
        campaign_id=None,
        public_slug_override=slug,
    )
    image_status, image_error = _map_image_status(image_result.status, image_result.error_code)
    png_path = base_path / write_result.image_relative_path
    if image_status != IMAGE_STATUS_FAILED and not png_path.is_file():
        # Completeness: approval-ready package requires a durable hero sibling
        image_status = IMAGE_STATUS_FAILED
        image_error = image_error or ERROR_DRAFT_GENERATION_FAILED

    if image_status == IMAGE_STATUS_FAILED:
        # Leave Markdown for operator inspection; do not promote; record failed image
        sidecar_status = "pending_approval_image_failed"
    else:
        sidecar_status = "pending_approval"

    sidecar_payload: dict[str, Any] = {
        "flow": "flow_b",
        "status": sidecar_status,
        "topic_id": topic.topic_id,
        "thesis": topic.thesis,
        "referent_positioning": topic.referent_positioning,
        "rationale": topic.rationale,
        "generated_at_utc": observed_at_utc,
        "provider": provider.name,
        "slug": slug,
        "blog_relative_path": write_result.blog_relative_path,
        "image_relative_path": write_result.image_relative_path,
        "image_status": image_status,
        "anti_ai_status": ANTI_AI_PASSED,
    }
    if topic.pillar_hints:
        sidecar_payload["pillar_hints"] = list(topic.pillar_hints)
    if gap_context:
        if "target_week" in gap_context:
            sidecar_payload["target_week"] = gap_context["target_week"]
        if "empty_days" in gap_context:
            sidecar_payload["empty_days"] = list(gap_context["empty_days"])
    if image_error:
        sidecar_payload["image_error_code"] = image_error

    sidecar_error = write_pending_approval_sidecar(
        base_path,
        write_result.metadata_relative_path,
        sidecar_payload,
    )
    if sidecar_error:
        # Metadata failure after md+image: still report paths; surface error
        return DraftItemResult(
            topic_id=topic.topic_id,
            status="failed" if image_status == IMAGE_STATUS_FAILED else "generated",
            blog_relative_path=write_result.blog_relative_path,
            image_relative_path=write_result.image_relative_path,
            metadata_relative_path=None,
            title=title,
            slug=slug,
            image_status=image_status,
            image_error_code=image_error or sidecar_error,
            anti_ai_status=ANTI_AI_PASSED,
            error_code=sidecar_error if image_status != IMAGE_STATUS_FAILED else image_error,
            error=_operator_message_for_code(sidecar_error),
        )

    if image_status == IMAGE_STATUS_FAILED:
        # Spec: not a complete successful package without hero image
        return DraftItemResult(
            topic_id=topic.topic_id,
            status="failed",
            blog_relative_path=write_result.blog_relative_path,
            image_relative_path=write_result.image_relative_path,
            metadata_relative_path=write_result.metadata_relative_path,
            title=title,
            slug=slug,
            image_status=image_status,
            image_error_code=image_error,
            anti_ai_status=ANTI_AI_PASSED,
            error_code=image_error or ERROR_COMFYUI_DISABLED,
            error=_operator_message_for_code(image_error or ERROR_COMFYUI_DISABLED),
        )

    return DraftItemResult(
        topic_id=topic.topic_id,
        status="generated",
        blog_relative_path=write_result.blog_relative_path,
        image_relative_path=write_result.image_relative_path,
        metadata_relative_path=write_result.metadata_relative_path,
        title=title,
        slug=slug,
        image_status=image_status,
        image_error_code=None,
        anti_ai_status=ANTI_AI_PASSED,
    )


def _map_image_status(
    status: str,
    error_code: str | None,
) -> tuple[str, str | None]:
    if status == "generated":
        return IMAGE_STATUS_GENERATED, None
    if status == "dry_run":
        return IMAGE_STATUS_DRY_RUN, None
    if status == "skipped":
        # Skipped-as-already-valid is rare for new drafts; treat as failed completeness
        # unless a sibling somehow exists — still report skipped for operator clarity.
        return IMAGE_STATUS_SKIPPED, error_code
    mapped = error_code
    if error_code == BLOG_IMAGE_GENERATION_DISABLED:
        mapped = ERROR_COMFYUI_DISABLED
    return IMAGE_STATUS_FAILED, mapped or ERROR_DRAFT_GENERATION_FAILED


def _build_gap_context(
    target_week: str | None,
    empty_days: list[str] | None,
) -> dict[str, Any] | None:
    if target_week is None and empty_days is None:
        return None
    context: dict[str, Any] = {}
    if target_week is not None:
        context["target_week"] = target_week.strip()
    if empty_days is not None:
        context["empty_days"] = [day.strip() for day in empty_days]
    return context


def _body_after_frontmatter(markdown: str) -> str:
    stripped = markdown.lstrip()
    match = _FRONTMATTER_RE.match(stripped)
    if match:
        return stripped[match.end() :]
    return stripped


def _as_nonempty_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _operator_message_for_code(code: str) -> str:
    messages = {
        ERROR_DRAFT_GENERATION_FAILED: "Blog draft generation failed",
        ERROR_CONFIG_INVALID: "DeepSeek / draft configuration is invalid",
        ERROR_CANON_MISSING: "Editorial canon file is missing",
        ERROR_CANON_SECTION_MISSING: "Required editorial canon section is missing",
        ERROR_SETTINGS_UNAVAILABLE: "Gap operator settings store is unavailable",
        ERROR_TOPICS_EMPTY: "topics must be a non-empty array",
        ERROR_TOPICS_DUPLICATE: "Duplicate topic_id in topics array",
        ERROR_TOPIC_INVALID: "Each topic requires thesis, referent_positioning, rationale, topic_id",
        ERROR_ANTI_AI_BLOCKED: "Generated Markdown failed Flow B anti-AI writing rules",
        ERROR_COMFYUI_DISABLED: "ComfyUI image generation is disabled",
        ERROR_PROVIDER_EMPTY: "Blog draft provider returned no usable Markdown content",
        ERROR_PENDING_DIR_NOT_READY: "blog-posts/pending-approval/ is not ready",
        ERROR_PENDING_DIR_NOT_WRITABLE: "blog-posts/pending-approval/ is not writable",
        "deepseek_api_key_missing": "DeepSeek API key is missing",
        "draft_provider_unsupported": "Unsupported blog draft generation provider",
        "draft_target_week_invalid": "target_week must be YYYY-Www",
        "draft_empty_days_invalid": "empty_days must be YYYY-MM-DD strings",
        BLOG_IMAGE_GENERATION_DISABLED: "ComfyUI image generation is disabled",
        "pending_approval_path_collision": "Could not allocate a unique pending-approval path",
        "pending_approval_write_failed": "Failed to write pending-approval artifact",
        "pending_approval_ready_write_forbidden": "Ready-folder writes are forbidden",
    }
    return messages.get(code, f"Draft generation error: {code}")
