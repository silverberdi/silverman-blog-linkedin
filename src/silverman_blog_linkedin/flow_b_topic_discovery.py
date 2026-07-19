"""US-078: Flow B AI topic discovery (discovery-only; no draft filesystem writes).

Assembles authority brief + editorial canon topic spaces + soft anti-dup from
recent ``blog-posts/processed/`` titles (read-only) + optional durable primary
material under ``prompts/flow-b/``. Caps batch size with
``load_gap_operator_settings().max_drafts_per_weekly_run`` (default 2).

MUST NOT write under ``blog-posts/ready/`` or ``blog-posts/pending-approval/``.
MUST NOT require BL-020 backlog. MUST NOT use RSS/news APIs as primary driver.
MUST NOT enable LinkedIn API publication.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from silverman_blog_linkedin.deepseek_config import load_deepseek_settings
from silverman_blog_linkedin.flow_b_gap_operator_settings import (
    SETTINGS_KEY_MAX_DRAFTS_PER_WEEKLY_RUN,
    GapOperatorSettingsSnapshot,
    load_gap_operator_settings,
)
from silverman_blog_linkedin.flow_b_gap_operator_settings_store import (
    GapOperatorSettingsStore,
)
from silverman_blog_linkedin.run_metadata import utc_now_iso
from silverman_blog_linkedin.topic_discovery_provider import (
    DEFAULT_TOPIC_DISCOVERY_PROVIDER,
    ENV_TOPIC_DISCOVERY_PROVIDER,
    PROVIDER_DEEPSEEK,
    TopicDiscoveryProvider,
    create_topic_discovery_provider,
)

STATUS_TOPICS_DISCOVERED: Literal["topics_discovered"] = "topics_discovered"
STATUS_DISCOVERY_FAILED: Literal["discovery_failed"] = "discovery_failed"
STATUS_DISCOVERY_DRY_RUN: Literal["discovery_dry_run"] = "discovery_dry_run"

ERROR_DISCOVERY_FAILED = "discovery_failed"
ERROR_NOT_OBJECTIVE_ALIGNED = "discovery_not_objective_aligned"
ERROR_CONFIG_INVALID = "discovery_config_invalid"
ERROR_CANON_MISSING = "editorial_canon_missing"
ERROR_CANON_SECTION_MISSING = "editorial_canon_section_missing"
ERROR_SETTINGS_UNAVAILABLE = "gap_operator_settings_unavailable"

EDITORIAL_CANON_RELATIVE = Path("content-strategy") / "silverman-editorial-system.md"
PROCESSED_BLOGS_RELATIVE = Path("blog-posts") / "processed"
READY_BLOGS_RELATIVE = Path("blog-posts") / "ready"
PENDING_APPROVAL_RELATIVE = Path("blog-posts") / "pending-approval"
PRIMARY_MATERIAL_RELATIVE = Path("prompts") / "flow-b"

REQUIRED_CANON_ANCHORS = (
    "brand-positioning",
    "content-pillars",
    "topic-boundaries",
    "flow-a-vs-flow-b",
)

SOFT_ANTI_DUP_LIMIT = 12
PRIMARY_MATERIAL_FILE_LIMIT = 4
PRIMARY_MATERIAL_CHARS_PER_FILE = 1200

_SECTION_HEADING_RE = re.compile(r"^## .+ \{#([a-z0-9-]+)\}\s*$", re.MULTILINE)
_JSON_FENCE_RE = re.compile(
    r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```",
    re.DOTALL | re.IGNORECASE,
)
_NEWS_CHASE_RE = re.compile(
    r"(?:\bvs\.?\b|versus\b|what'?s\s+new\b|this\s+week\s+in\b|"
    r"top\s+stories\b|breaking\s*:|headline\s+rebroadcast\b|"
    r"\bx\s+vs\s+y\b)",
    re.IGNORECASE,
)

_ISO_WEEK_RE = re.compile(r"^\d{4}-W\d{2}$")
_LOCAL_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class DiscoveredTopic:
    """Attachable topic payload for later US-079 draft packages."""

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


@dataclass(frozen=True)
class TopicDiscoveryResult:
    """Orchestration result for HTTP / internal callers."""

    status: Literal["topics_discovered", "discovery_failed", "discovery_dry_run"]
    provider: str | None
    topics: list[DiscoveredTopic] = field(default_factory=list)
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
            "topics": [topic.to_dict() for topic in self.topics],
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


def default_editorial_canon_path() -> Path:
    """Resolve repo ``content-strategy/silverman-editorial-system.md`` from package."""
    # src/silverman_blog_linkedin/flow_b_topic_discovery.py → repo root
    return Path(__file__).resolve().parents[2] / EDITORIAL_CANON_RELATIVE


def extract_canon_section(markdown: str, anchor: str) -> str | None:
    """Extract a level-2 section body by ``{#anchor}`` (editorial canon contract)."""
    matches = list(_SECTION_HEADING_RE.finditer(markdown))
    for index, match in enumerate(matches):
        if match.group(1) != anchor:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        body = markdown[start:end].strip()
        return body or None
    return None


def load_required_canon_sections(
    canon_path: Path,
) -> tuple[dict[str, str] | None, str | None]:
    """Load required canon sections or return ``(None, error_code)``."""
    if not canon_path.is_file():
        return None, ERROR_CANON_MISSING
    text = canon_path.read_text(encoding="utf-8")
    sections: dict[str, str] = {}
    for anchor in REQUIRED_CANON_ANCHORS:
        body = extract_canon_section(text, anchor)
        if body is None:
            return None, ERROR_CANON_SECTION_MISSING
        sections[anchor] = body
    return sections, None


def read_recent_processed_titles(
    base_path: Path,
    *,
    limit: int = SOFT_ANTI_DUP_LIMIT,
) -> list[str]:
    """Read-only soft anti-dup signals from recent ``blog-posts/processed/`` titles."""
    processed = base_path / PROCESSED_BLOGS_RELATIVE
    if not processed.is_dir():
        return []
    markdown_files = sorted(
        (path for path in processed.glob("*.md") if path.is_file()),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )
    titles: list[str] = []
    for path in markdown_files[: max(0, limit)]:
        title = _title_from_blog_markdown(path)
        if title:
            titles.append(title)
    return titles


def read_optional_primary_material(
    base_path: Path,
    *,
    file_limit: int = PRIMARY_MATERIAL_FILE_LIMIT,
    chars_per_file: int = PRIMARY_MATERIAL_CHARS_PER_FILE,
) -> list[str]:
    """Optional durable excerpts under ``prompts/flow-b/``; absence is fine."""
    root = base_path / PRIMARY_MATERIAL_RELATIVE
    if not root.is_dir():
        return []
    files = sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in {".md", ".txt"}
        ),
        key=lambda path: path.name.lower(),
    )
    excerpts: list[str] = []
    for path in files[: max(0, file_limit)]:
        try:
            text = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if not text:
            continue
        excerpts.append(text[:chars_per_file])
    return excerpts


def clamp_discovery_count(requested: int | None, max_drafts: int) -> int:
    """Clamp requested count into ``[1, max_drafts]``; omit ⇒ effective max."""
    ceiling = max(1, int(max_drafts))
    if requested is None:
        return ceiling
    return max(1, min(int(requested), ceiling))


def is_news_chase_thesis(thesis: str) -> bool:
    """Lightweight rejection for obvious news-chase / comparison-headline theses."""
    normalized = " ".join(thesis.split()).strip()
    if not normalized:
        return True
    return bool(_NEWS_CHASE_RE.search(normalized))


def parse_provider_topics_json(
    raw: str,
    *,
    count: int,
) -> list[dict[str, Any]]:
    """Parse provider JSON into candidate topic dicts (may be empty)."""
    payload = _loads_json_payload(raw)
    if payload is None:
        return []
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get("topics")
        if not isinstance(items, list):
            return []
    else:
        return []

    candidates: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        thesis = _as_nonempty_str(item.get("thesis"))
        referent = _as_nonempty_str(
            item.get("referent_positioning") or item.get("referentPositioning")
        )
        rationale = _as_nonempty_str(item.get("rationale"))
        if thesis is None or referent is None or rationale is None:
            continue
        hints_raw = item.get("pillar_hints") or item.get("pillarHints") or []
        pillar_hints: list[str] = []
        if isinstance(hints_raw, list):
            for hint in hints_raw:
                text = _as_nonempty_str(hint)
                if text is not None:
                    pillar_hints.append(text)
        topic_id = _as_nonempty_str(item.get("topic_id") or item.get("topicId"))
        candidates.append(
            {
                "thesis": thesis,
                "referent_positioning": referent,
                "rationale": rationale,
                "pillar_hints": pillar_hints,
                "topic_id": topic_id,
            }
        )
        if len(candidates) >= count:
            break
    return candidates


def filter_objective_aligned_topics(
    candidates: list[dict[str, Any]],
    *,
    count: int,
) -> list[DiscoveredTopic]:
    """Keep distinct, non-news-chase topics with required fields; no filler padding."""
    accepted: list[DiscoveredTopic] = []
    seen_theses: set[str] = set()
    for candidate in candidates:
        thesis = candidate["thesis"]
        if is_news_chase_thesis(thesis):
            continue
        key = " ".join(thesis.lower().split())
        if key in seen_theses:
            continue
        seen_theses.add(key)
        topic_id = candidate.get("topic_id") or str(uuid.uuid4())
        accepted.append(
            DiscoveredTopic(
                thesis=thesis,
                referent_positioning=candidate["referent_positioning"],
                rationale=candidate["rationale"],
                topic_id=str(topic_id),
                pillar_hints=list(candidate.get("pillar_hints") or []),
            )
        )
        if len(accepted) >= count:
            break
    return accepted


def build_discovery_messages(
    *,
    sections: dict[str, str],
    recent_titles: list[str],
    primary_material: list[str],
    count: int,
    target_week: str | None,
    empty_days: list[str] | None,
) -> list[dict[str, str]]:
    """Assemble system/user messages for authority-constrained topic discovery."""
    anti_dup = (
        "\n".join(f"- {title}" for title in recent_titles)
        if recent_titles
        else "(none available — prefer distinct durable themes)"
    )
    primary = (
        "\n\n---\n\n".join(primary_material)
        if primary_material
        else "(none provided — proceed without primary material)"
    )
    gap_lines: list[str] = []
    if target_week:
        gap_lines.append(f"Target ISO week (informational scheduling hint): {target_week}")
    if empty_days:
        gap_lines.append(
            "Empty local days (informational; not a filesystem inventory): "
            + ", ".join(empty_days)
        )
    gap_block = "\n".join(gap_lines) if gap_lines else "(no gap context provided)"

    system = (
        "You are the Flow B topic-discovery assistant for Silverio Bernal "
        "(Solutions Architect). Propose authority-aligned blog theses that "
        "position him as a referent for senior leadership / architecture / "
        "transformation / AI roles (compensation framing ≥ ~USD 7,000). "
        "MUST NOT optimize for 'X vs Y', 'what's new', headline rebroadcast, "
        "or tech-news chase. Prefer durable architectural theses over trends. "
        "Return ONLY valid JSON matching the schema in the user message."
    )
    user = (
        f"Produce exactly {count} DISTINCT topic choice(s).\n\n"
        "## Authority / brand positioning\n"
        f"{sections['brand-positioning']}\n\n"
        "## Flow A vs Flow B (career / authority objective)\n"
        f"{sections['flow-a-vs-flow-b']}\n\n"
        "## Content pillars (topic spaces)\n"
        f"{sections['content-pillars']}\n\n"
        "## Topic boundaries\n"
        f"{sections['topic-boundaries']}\n\n"
        "## Soft anti-dup — recent published blog titles (prefer distinct themes)\n"
        f"{anti_dup}\n\n"
        "## Optional durable primary material\n"
        f"{primary}\n\n"
        "## Optional gap-batch context (scheduling hints only)\n"
        f"{gap_block}\n\n"
        "## Output JSON schema\n"
        "{\n"
        '  "topics": [\n'
        "    {\n"
        '      "thesis": "string — clear topic thesis / working title framing",\n'
        '      "referent_positioning": "string — why this positions Silverio as a referent",\n'
        '      "rationale": "string — brief operator-readable discovery rationale",\n'
        '      "pillar_hints": ["optional pillar names"],\n'
        '      "topic_id": "optional opaque id"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "No markdown fences. No news-chase theses."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def discover_flow_b_topics(
    base_path: Path,
    *,
    count: int | None = None,
    target_week: str | None = None,
    empty_days: list[str] | None = None,
    dry_run: bool = False,
    store: GapOperatorSettingsStore | None = None,
    environ: dict[str, str] | None = None,
    settings_snapshot: GapOperatorSettingsSnapshot | None = None,
    provider: TopicDiscoveryProvider | None = None,
    canon_path: Path | None = None,
) -> TopicDiscoveryResult:
    """Run Flow B topic discovery; never writes draft folders."""
    observed = utc_now_iso()
    env = os.environ if environ is None else environ

    try:
        snapshot = settings_snapshot or load_gap_operator_settings(
            store=store,
            environ=env,
        )
    except RuntimeError:
        return TopicDiscoveryResult(
            status=STATUS_DISCOVERY_FAILED,
            provider=None,
            observed_at_utc=observed,
            error_code=ERROR_SETTINGS_UNAVAILABLE,
            error="Gap operator settings store is unavailable",
        )

    max_drafts = int(
        snapshot.settings.get(SETTINGS_KEY_MAX_DRAFTS_PER_WEEKLY_RUN)
        or 2
    )
    effective_count = clamp_discovery_count(count, max_drafts)
    gap_context = _build_gap_context(target_week, empty_days)

    resolved_canon = canon_path or default_editorial_canon_path()
    sections, canon_error = load_required_canon_sections(resolved_canon)
    if sections is None:
        return TopicDiscoveryResult(
            status=STATUS_DISCOVERY_FAILED,
            provider=None,
            max_drafts_per_weekly_run=max_drafts,
            settings_source=snapshot.source,
            gap_context=gap_context,
            observed_at_utc=observed,
            error_code=canon_error,
            error=_operator_message_for_code(canon_error or ERROR_DISCOVERY_FAILED),
        )

    recent_titles = read_recent_processed_titles(base_path)
    primary_material = read_optional_primary_material(base_path)
    messages = build_discovery_messages(
        sections=sections,
        recent_titles=recent_titles,
        primary_material=primary_material,
        count=effective_count,
        target_week=target_week,
        empty_days=empty_days,
    )

    provider_name = (
        env.get(ENV_TOPIC_DISCOVERY_PROVIDER, DEFAULT_TOPIC_DISCOVERY_PROVIDER)
        .strip()
        .lower()
        or DEFAULT_TOPIC_DISCOVERY_PROVIDER
    )

    if dry_run:
        return TopicDiscoveryResult(
            status=STATUS_DISCOVERY_DRY_RUN,
            provider=provider_name,
            topics=[],
            max_drafts_per_weekly_run=max_drafts,
            settings_source=snapshot.source,
            gap_context=gap_context,
            observed_at_utc=observed,
            dry_run=True,
        )

    if provider is None:
        deepseek_load = load_deepseek_settings(env)
        if deepseek_load.config_invalid or deepseek_load.settings is None:
            return TopicDiscoveryResult(
                status=STATUS_DISCOVERY_FAILED,
                provider=PROVIDER_DEEPSEEK,
                max_drafts_per_weekly_run=max_drafts,
                settings_source=snapshot.source,
                gap_context=gap_context,
                observed_at_utc=observed,
                error_code=ERROR_CONFIG_INVALID,
                error="DeepSeek configuration is invalid",
            )
        if not deepseek_load.settings.is_configured:
            return TopicDiscoveryResult(
                status=STATUS_DISCOVERY_FAILED,
                provider=PROVIDER_DEEPSEEK,
                max_drafts_per_weekly_run=max_drafts,
                settings_source=snapshot.source,
                gap_context=gap_context,
                observed_at_utc=observed,
                error_code="deepseek_api_key_missing",
                error="DeepSeek API key is missing",
            )
        provider = create_topic_discovery_provider(
            provider_name,
            settings=deepseek_load.settings,
        )

    provider_result = provider.discover_topics(messages, count=effective_count)
    if provider_result.error_code:
        return TopicDiscoveryResult(
            status=STATUS_DISCOVERY_FAILED,
            provider=provider_result.provider,
            max_drafts_per_weekly_run=max_drafts,
            settings_source=snapshot.source,
            gap_context=gap_context,
            observed_at_utc=observed,
            error_code=provider_result.error_code,
            error=_operator_message_for_code(provider_result.error_code),
        )

    raw = provider_result.content
    if raw is None or not raw.strip():
        return TopicDiscoveryResult(
            status=STATUS_DISCOVERY_FAILED,
            provider=provider_result.provider,
            max_drafts_per_weekly_run=max_drafts,
            settings_source=snapshot.source,
            gap_context=gap_context,
            observed_at_utc=observed,
            error_code=ERROR_DISCOVERY_FAILED,
            error="Discovery provider returned no usable topic content",
        )

    candidates = parse_provider_topics_json(raw, count=effective_count)
    topics = filter_objective_aligned_topics(candidates, count=effective_count)
    if not topics:
        return TopicDiscoveryResult(
            status=STATUS_DISCOVERY_FAILED,
            provider=provider_result.provider,
            max_drafts_per_weekly_run=max_drafts,
            settings_source=snapshot.source,
            gap_context=gap_context,
            observed_at_utc=observed,
            error_code=ERROR_NOT_OBJECTIVE_ALIGNED,
            error=(
                "Discovery could not produce an objective-aligned topic "
                "(authority / referent posture required)"
            ),
        )

    return TopicDiscoveryResult(
        status=STATUS_TOPICS_DISCOVERED,
        provider=provider_result.provider,
        topics=topics,
        max_drafts_per_weekly_run=max_drafts,
        settings_source=snapshot.source,
        gap_context=gap_context,
        observed_at_utc=observed,
    )


def snapshot_draft_folders(base_path: Path) -> dict[str, tuple[bytes, int]]:
    """Snapshot files under ready/ and pending-approval/ for write-guard tests."""
    return _snapshot_draft_folders(base_path)


def validate_discovery_request_fields(
    *,
    count: int | None,
    target_week: str | None,
    empty_days: list[str] | None,
) -> list[dict[str, str]]:
    """Return structured field errors for HTTP 422 mapping; empty = valid."""
    errors: list[dict[str, str]] = []
    if count is not None and count < 1:
        errors.append(
            {
                "field": "count",
                "code": "invalid_count",
                "message": "count must be >= 1 when provided",
            }
        )
    if target_week is not None:
        stripped = target_week.strip()
        if not stripped or not _ISO_WEEK_RE.match(stripped):
            errors.append(
                {
                    "field": "target_week",
                    "code": "invalid_target_week",
                    "message": "target_week must look like YYYY-Www",
                }
            )
    if empty_days is not None:
        for index, day in enumerate(empty_days):
            if not isinstance(day, str) or not _LOCAL_DATE_RE.match(day.strip()):
                errors.append(
                    {
                        "field": f"empty_days[{index}]",
                        "code": "invalid_empty_day",
                        "message": "empty_days entries must be YYYY-MM-DD",
                    }
                )
    return errors


def _snapshot_draft_folders(base_path: Path) -> dict[str, tuple[bytes, int]]:
    snapshot: dict[str, tuple[bytes, int]] = {}
    for relative in (READY_BLOGS_RELATIVE, PENDING_APPROVAL_RELATIVE):
        root = base_path / relative
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file():
                key = str(path.relative_to(base_path))
                snapshot[key] = (path.read_bytes(), path.stat().st_mtime_ns)
    return snapshot


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


def _title_from_blog_markdown(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return path.stem.replace("-", " ").strip() or None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            if title:
                return title
    stem = path.stem.replace("-", " ").strip()
    return stem or None


def _loads_json_payload(raw: str) -> Any | None:
    text = raw.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fence = _JSON_FENCE_RE.search(text)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            return None
    start_obj = text.find("{")
    start_arr = text.find("[")
    starts = [s for s in (start_obj, start_arr) if s >= 0]
    if not starts:
        return None
    start = min(starts)
    try:
        return json.loads(text[start:])
    except json.JSONDecodeError:
        return None


def _as_nonempty_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _operator_message_for_code(code: str) -> str:
    messages = {
        ERROR_CANON_MISSING: "Editorial canon file is missing",
        ERROR_CANON_SECTION_MISSING: "Required editorial canon section is missing",
        ERROR_CONFIG_INVALID: "DeepSeek configuration is invalid",
        ERROR_NOT_OBJECTIVE_ALIGNED: (
            "Discovery could not produce an objective-aligned topic"
        ),
        ERROR_DISCOVERY_FAILED: "Topic discovery failed",
        ERROR_SETTINGS_UNAVAILABLE: "Gap operator settings store is unavailable",
        "deepseek_api_key_missing": "DeepSeek API key is missing",
        "deepseek_auth_failed": "DeepSeek authentication failed",
        "deepseek_insufficient_balance": "DeepSeek account has insufficient balance",
        "deepseek_invalid_request": "DeepSeek rejected the discovery request",
        "deepseek_rate_limited": "DeepSeek rate limit exceeded",
        "deepseek_unavailable": "DeepSeek is temporarily unavailable",
        "deepseek_timeout": "DeepSeek request timed out",
        "deepseek_empty_response": "DeepSeek returned an empty response",
        "discovery_provider_unsupported": "Requested discovery provider is not supported",
    }
    return messages.get(code, "Topic discovery failed")
