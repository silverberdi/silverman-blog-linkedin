"""US-079: Flow B blog draft + hero image generation into pending-approval/."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from silverman_blog_linkedin.blog_draft_generation_provider import (
    PROVIDER_DEEPSEEK,
    BlogDraftProviderResult,
    DeepSeekBlogDraftGenerationProvider,
    create_blog_draft_provider,
)
from silverman_blog_linkedin.comfyui_client import FakeComfyUIClient
from silverman_blog_linkedin.deepseek_config import DeepSeekSettings
from silverman_blog_linkedin.flow_b_blog_draft_generation import (
    ERROR_ANTI_AI_BLOCKED,
    ERROR_COMFYUI_DISABLED,
    ERROR_TOPICS_DUPLICATE,
    STATUS_DRAFT_GENERATION_DRY_RUN,
    STATUS_DRAFT_GENERATION_FAILED,
    STATUS_DRAFTS_GENERATED,
    STATUS_DRAFTS_PARTIAL,
    collect_flow_b_anti_ai_violations,
    generate_flow_b_blog_drafts,
    snapshot_ready_folder,
)
from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, make_settings

GENERATE_PATH = "/flow-b/generate-blog-drafts"

MINI_CANON = """\
## 2 Brand Positioning {#brand-positioning}

Lead with domain-first design. Referent, not news aggregator.

## 5 Content Pillars {#content-pillars}

Software architecture. Engineering leadership. AI-assisted SDLC.

## 6 Topic Boundaries {#topic-boundaries}

Allowed: architecture decisions with trade-offs.
Forbidden: news commentary and tool-vs-tool hot takes.

## 7 Blog Post Rules {#blog-post-rules}

Require Markdown + image sibling pair. Practical senior tone.

## 11 Anti-AI-Writing Rules {#anti-ai-writing-rules}

No AI-sounding openings. Flow B generated content uses blocking rules.

## 14 Flow A vs Flow B {#flow-a-vs-flow-b}

Career objective ≥ ~USD 7,000; discovery as referent not news spreader.
"""

GOOD_MARKDOWN = """\
---
title: Domain boundaries before ORM choices
date: 2026-07-19
description: Why naming the business comes before picking a database.
image: placeholder.png
flow: flow_b
topic_id: topic-domain-boundaries
---

# Domain boundaries before ORM choices

Teams often reach for an ORM before they agree what the business event is.

The expensive mistake is committing to a schema while the domain language is still mush. I have watched delivery pressure push persistence decisions earlier than judgment allows — and the refactor cost shows up in every later change.

When we named the boundary first, the storage choice became an implementation detail. That is the trade-off: slower early alignment for cheaper long-term change.
"""

BLOCKED_MARKDOWN = """\
---
title: Soft skills for architects
date: 2026-07-19
description: Generic filler
image: placeholder.png
flow: flow_b
topic_id: topic-blocked
---

# Soft skills for architects

In today's fast-paced world, technology continues to evolve. Let's dive into why architecture matters.

Moreover, it is important to note that soft skills are crucial. Furthermore, the landscape is a tapestry of synergy. Additionally, ultimately the future belongs to those who leverage cutting-edge holistic empowerment.

What are your thoughts? Comment below and follow me for more insights.
"""


class _StubDraftProvider:
    def __init__(
        self,
        *,
        content: str | None = None,
        error_code: str | None = None,
        name: str = PROVIDER_DEEPSEEK,
        contents_by_call: list[str] | None = None,
    ) -> None:
        self._content = content
        self._error_code = error_code
        self._name = name
        self._contents_by_call = list(contents_by_call or [])
        self.calls: list[list[dict[str, str]]] = []

    @property
    def name(self) -> str:
        return self._name

    def generate_blog_draft(
        self,
        messages: list[dict[str, str]],
    ) -> BlogDraftProviderResult:
        self.calls.append(messages)
        if self._contents_by_call:
            content = self._contents_by_call.pop(0)
            return BlogDraftProviderResult(
                content=content,
                error_code=None,
                provider=self._name,
            )
        return BlogDraftProviderResult(
            content=self._content,
            error_code=self._error_code,
            provider=self._name,
        )


def _editorial_base(tmp_path: Path) -> Path:
    base = tmp_path / "editorial"
    for relative in (
        "blog-posts/ready",
        "blog-posts/pending-approval",
        "blog-posts/processed",
        "metadata/campaigns",
        "metadata/runs",
    ):
        (base / relative).mkdir(parents=True, exist_ok=True)
    return base


def _write_canon(tmp_path: Path, text: str = MINI_CANON) -> Path:
    path = tmp_path / "canon.md"
    path.write_text(text, encoding="utf-8")
    return path


def _topics(n: int = 1) -> list[dict[str, Any]]:
    items = [
        {
            "thesis": "Domain boundaries before ORM choices",
            "referent_positioning": (
                "Shows senior architecture judgment under delivery pressure"
            ),
            "rationale": "Durable authority theme; not a news chase",
            "pillar_hints": ["Domain-first design"],
            "topic_id": "topic-domain-boundaries",
        },
        {
            "thesis": "Governance patterns for AI-assisted SDLC",
            "referent_positioning": (
                "Positions Silverio as a referent on AI delivery guardrails"
            ),
            "rationale": "Leadership + architecture transformation angle",
            "pillar_hints": ["AI-assisted SDLC"],
            "topic_id": "topic-ai-governance",
        },
        {
            "thesis": "Incremental modernization without rewrite theater",
            "referent_positioning": "Signals transformation leadership with risk control",
            "rationale": "Modernization pillar; distinct from prior theses",
            "topic_id": "topic-modernization",
        },
    ]
    return items[:n]


def _good_markdown_for(topic_id: str, title: str) -> str:
    return GOOD_MARKDOWN.replace("topic-domain-boundaries", topic_id).replace(
        "Domain boundaries before ORM choices", title
    )


def _comfy_env(base: Path) -> dict[str, str]:
    return {
        "SILVERMAN_BLOG_LINKEDIN_BASE_PATH": str(base),
        "SILVERMAN_COMFYUI_IMAGE_ENABLED": "true",
        "SILVERMAN_COMFYUI_BASE_URL": "http://127.0.0.1:8188",
        "SILVERMAN_COMFYUI_API_KEY": "test-key",
        "DEEPSEEK_API_KEY": "test-deepseek-key",
    }


def _assert_no_secrets(body: dict) -> None:
    blob = str(body).lower()
    for needle in (
        "password",
        "api_key",
        "apikey",
        "oauth",
        "token",
        "postgresql://",
        "sk-",
        "secret",
        "test-deepseek-key",
        "test-key",
    ):
        assert needle not in blob


def test_provider_seam_deepseek_only() -> None:
    settings = DeepSeekSettings(
        api_key="test-key",
        base_url="https://api.deepseek.com",
        model="deepseek-v4-flash",
        timeout_seconds=30.0,
        max_output_tokens=1024,
    )
    provider = create_blog_draft_provider("deepseek", settings=settings)
    assert isinstance(provider, DeepSeekBlogDraftGenerationProvider)
    assert provider.name == PROVIDER_DEEPSEEK

    unsupported = create_blog_draft_provider("openai", settings=settings)
    result = unsupported.generate_blog_draft([])
    assert result.error_code == "draft_provider_unsupported"
    assert result.content is None


def test_anti_ai_blocks_generic_patterns() -> None:
    violations = collect_flow_b_anti_ai_violations(BLOCKED_MARKDOWN, title="Soft skills")
    assert "warning_ai_opening" in violations
    assert violations


def test_happy_path_writes_pending_approval_pair_and_sidecar(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    before = snapshot_ready_folder(base)
    fake = FakeComfyUIClient()
    provider = _StubDraftProvider(content=GOOD_MARKDOWN)

    result = generate_flow_b_blog_drafts(
        base,
        topics=_topics(1),
        target_week="2026-W30",
        empty_days=["2026-07-20", "2026-07-22"],
        provider=provider,
        comfyui_client=fake,
        environ=_comfy_env(base),
        canon_path=canon,
    )

    assert result.status == STATUS_DRAFTS_GENERATED
    assert result.provider == PROVIDER_DEEPSEEK
    assert result.max_drafts_per_weekly_run == 2
    assert len(result.drafts) == 1
    item = result.drafts[0]
    assert item.status == "generated"
    assert item.topic_id == "topic-domain-boundaries"
    assert item.blog_relative_path is not None
    assert item.blog_relative_path.startswith("blog-posts/pending-approval/")
    assert item.image_relative_path is not None
    assert item.image_relative_path.endswith(".png")
    assert item.metadata_relative_path is not None
    assert item.metadata_relative_path.endswith(".flow-b.json")
    assert item.anti_ai_status == "passed"
    assert item.image_status == "generated"
    assert (base / item.blog_relative_path).is_file()
    assert (base / item.image_relative_path).is_file()
    sidecar = json.loads((base / item.metadata_relative_path).read_text(encoding="utf-8"))
    assert sidecar["topic_id"] == "topic-domain-boundaries"
    assert sidecar["target_week"] == "2026-W30"
    assert sidecar["empty_days"] == ["2026-07-20", "2026-07-22"]
    assert sidecar["flow"] == "flow_b"
    assert sidecar["status"] == "pending_approval"
    assert sidecar["provider"] == PROVIDER_DEEPSEEK
    after = snapshot_ready_folder(base)
    assert after["blog-posts/ready"] == before["blog-posts/ready"]
    assert fake.calls  # ComfyUI invoked


def test_batch_clamps_to_max_drafts(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    from silverman_blog_linkedin.flow_b_gap_operator_settings import (
        GapOperatorSettingsSnapshot,
        documented_defaults,
    )

    snapshot = GapOperatorSettingsSnapshot(
        settings={**documented_defaults(), "max_drafts_per_weekly_run": 1},
        source="database",
        row_version=1,
        updated_at_utc="2026-07-19T00:00:00Z",
    )
    provider = _StubDraftProvider(
        contents_by_call=[
            _good_markdown_for("topic-domain-boundaries", "Domain boundaries before ORM choices"),
            _good_markdown_for("topic-ai-governance", "Governance patterns for AI-assisted SDLC"),
        ]
    )
    result = generate_flow_b_blog_drafts(
        base,
        topics=_topics(3),
        provider=provider,
        comfyui_client=FakeComfyUIClient(),
        environ=_comfy_env(base),
        canon_path=canon,
        settings_snapshot=snapshot,
    )
    assert result.status == STATUS_DRAFTS_GENERATED
    assert result.max_drafts_per_weekly_run == 1
    assert len(result.drafts) == 1
    assert len(provider.calls) == 1


def test_duplicate_topic_id_rejected(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    topics = _topics(1)
    topics.append(dict(topics[0]))
    result = generate_flow_b_blog_drafts(
        base,
        topics=topics,
        provider=_StubDraftProvider(content=GOOD_MARKDOWN),
        comfyui_client=FakeComfyUIClient(),
        environ=_comfy_env(base),
        canon_path=canon,
    )
    assert result.status == STATUS_DRAFT_GENERATION_FAILED
    assert result.error_code == ERROR_TOPICS_DUPLICATE
    assert not list((base / "blog-posts/pending-approval").glob("*.md"))


def test_anti_ai_blocked_not_successful_package(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    before = snapshot_ready_folder(base)
    result = generate_flow_b_blog_drafts(
        base,
        topics=_topics(1),
        provider=_StubDraftProvider(content=BLOCKED_MARKDOWN),
        comfyui_client=FakeComfyUIClient(),
        environ=_comfy_env(base),
        canon_path=canon,
    )
    assert result.status == STATUS_DRAFT_GENERATION_FAILED
    assert result.drafts[0].status == "blocked"
    assert result.drafts[0].anti_ai_status == "blocked"
    assert result.drafts[0].error_code == ERROR_ANTI_AI_BLOCKED
    assert result.drafts[0].anti_ai_violations
    after = snapshot_ready_folder(base)
    assert after["blog-posts/pending-approval"] == before["blog-posts/pending-approval"]
    assert after["blog-posts/ready"] == before["blog-posts/ready"]


def test_comfyui_disabled_structured_failure(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    env = _comfy_env(base)
    env["SILVERMAN_COMFYUI_IMAGE_ENABLED"] = "false"
    result = generate_flow_b_blog_drafts(
        base,
        topics=_topics(1),
        provider=_StubDraftProvider(content=GOOD_MARKDOWN),
        comfyui_client=FakeComfyUIClient(),
        environ=env,
        canon_path=canon,
    )
    assert result.status == STATUS_DRAFT_GENERATION_FAILED
    item = result.drafts[0]
    assert item.status == "failed"
    assert item.image_status == "failed"
    assert item.image_error_code == ERROR_COMFYUI_DISABLED
    assert item.blog_relative_path is not None
    assert (base / item.blog_relative_path).is_file()
    # Not under ready/
    assert not item.blog_relative_path.startswith("blog-posts/ready/")


def test_dry_run_no_durable_pair(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    before = snapshot_ready_folder(base)
    fake = FakeComfyUIClient()
    result = generate_flow_b_blog_drafts(
        base,
        topics=_topics(1),
        dry_run=True,
        provider=_StubDraftProvider(content=GOOD_MARKDOWN),
        comfyui_client=fake,
        environ=_comfy_env(base),
        canon_path=canon,
    )
    assert result.status == STATUS_DRAFT_GENERATION_DRY_RUN
    assert result.dry_run is True
    assert result.drafts[0].image_status == "dry_run"
    assert not fake.calls
    after = snapshot_ready_folder(base)
    assert after == before


def test_missing_deepseek_config_fails_closed(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    env = {
        "SILVERMAN_BLOG_LINKEDIN_BASE_PATH": str(base),
        "SILVERMAN_COMFYUI_IMAGE_ENABLED": "true",
        "SILVERMAN_COMFYUI_BASE_URL": "http://127.0.0.1:8188",
        # no DEEPSEEK_API_KEY
    }
    result = generate_flow_b_blog_drafts(
        base,
        topics=_topics(1),
        environ=env,
        canon_path=canon,
    )
    assert result.status == STATUS_DRAFT_GENERATION_FAILED
    assert result.error_code == "deepseek_api_key_missing"
    assert not list((base / "blog-posts/pending-approval").glob("*.md"))


def test_partial_batch_image_failure(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    from silverman_blog_linkedin.flow_b_gap_operator_settings import (
        GapOperatorSettingsSnapshot,
        documented_defaults,
    )

    snapshot = GapOperatorSettingsSnapshot(
        settings={**documented_defaults(), "max_drafts_per_weekly_run": 2},
        source="defaults",
        row_version=0,
        updated_at_utc="2026-07-19T00:00:00Z",
    )
    call_count = {"n": 0}

    class _FlakyComfy:
        def generate_image(self, **kwargs: Any) -> Any:
            from silverman_blog_linkedin.comfyui_client import ComfyUIImageResult

            call_count["n"] += 1
            if call_count["n"] == 1:
                return ComfyUIImageResult(
                    png_bytes=b"\x89PNG\r\n\x1a\nok",
                    error_code=None,
                )
            return ComfyUIImageResult(
                png_bytes=None,
                error_code="blog_image_generation_comfyui_failed",
            )

    provider = _StubDraftProvider(
        contents_by_call=[
            _good_markdown_for("topic-domain-boundaries", "Domain boundaries before ORM choices"),
            _good_markdown_for("topic-ai-governance", "Governance patterns for AI-assisted SDLC"),
        ]
    )
    result = generate_flow_b_blog_drafts(
        base,
        topics=_topics(2),
        provider=provider,
        comfyui_client=_FlakyComfy(),  # type: ignore[arg-type]
        environ=_comfy_env(base),
        canon_path=canon,
        settings_snapshot=snapshot,
    )
    assert result.status == STATUS_DRAFTS_PARTIAL
    assert result.drafts[0].status == "generated"
    assert result.drafts[1].status == "failed"
    assert result.drafts[1].image_status == "failed"
    assert not any(
        p.name.endswith(".md")
        for p in (base / "blog-posts/ready").iterdir()
        if p.is_file()
    )


def test_http_auth_required(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    client = TestClient(create_app(settings))
    response = client.post(GENERATE_PATH, json={"topics": _topics(1)})
    assert response.status_code == 401


def test_http_happy_path_and_openapi(tmp_path: Path, monkeypatch: Any) -> None:
    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    settings = make_settings(base)
    app = create_app(settings)
    client = TestClient(app)

    paths = {route.path for route in app.routes}
    assert GENERATE_PATH in paths
    # Scope guard: no promote/trigger routes (approve lives under US-080 pending-approval-drafts)
    assert "/flow-b/promote-blog-draft" not in paths
    assert "/flow-b/gap-trigger" not in paths
    assert "/flow-b/approve-blog-draft" not in paths

    fake = FakeComfyUIClient()
    provider = _StubDraftProvider(content=GOOD_MARKDOWN)

    def _fake_generate(base_path: Path, **kwargs: Any) -> Any:
        kwargs.setdefault("provider", provider)
        kwargs.setdefault("comfyui_client", fake)
        kwargs.setdefault("canon_path", canon)
        kwargs["environ"] = {
            **_comfy_env(base_path),
            **(kwargs.get("environ") or {}),
        }
        return generate_flow_b_blog_drafts(base_path, **kwargs)

    monkeypatch.setattr(
        "silverman_blog_linkedin.main.generate_flow_b_blog_drafts",
        _fake_generate,
    )

    response = client.post(
        GENERATE_PATH,
        headers=auth_header(),
        json={
            "topics": _topics(1),
            "target_week": "2026-W30",
            "empty_days": ["2026-07-21"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    _assert_no_secrets(body)
    assert body["status"] == STATUS_DRAFTS_GENERATED
    assert body["provider"] == PROVIDER_DEEPSEEK
    assert body["gap_context"]["target_week"] == "2026-W30"
    assert body["drafts"][0]["blog_relative_path"].startswith(
        "blog-posts/pending-approval/"
    )


def test_http_dry_run(tmp_path: Path, monkeypatch: Any) -> None:
    base = _editorial_base(tmp_path)
    settings = make_settings(base)
    client = TestClient(create_app(settings))

    def _fake_generate(base_path: Path, **kwargs: Any) -> Any:
        from silverman_blog_linkedin.flow_b_blog_draft_generation import (
            BlogDraftGenerationResult,
            DraftItemResult,
        )

        return BlogDraftGenerationResult(
            status=STATUS_DRAFT_GENERATION_DRY_RUN,
            provider=PROVIDER_DEEPSEEK,
            drafts=[
                DraftItemResult(
                    topic_id="topic-domain-boundaries",
                    status="dry_run",
                    image_status="dry_run",
                    anti_ai_status="passed",
                )
            ],
            max_drafts_per_weekly_run=2,
            settings_source="defaults",
            dry_run=True,
            observed_at_utc="2026-07-19T12:00:00Z",
        )

    monkeypatch.setattr(
        "silverman_blog_linkedin.main.generate_flow_b_blog_drafts",
        _fake_generate,
    )
    response = client.post(
        GENERATE_PATH,
        headers=auth_header(),
        json={"topics": _topics(1), "dry_run": True},
    )
    assert response.status_code == 200
    assert response.json()["status"] == STATUS_DRAFT_GENERATION_DRY_RUN
    assert not list((base / "blog-posts/pending-approval").glob("*.md"))


def test_no_flow_a_or_linkedin_imports_in_orchestration() -> None:
    """Guard: orchestration module must not call Flow A / LinkedIn publish paths."""
    import silverman_blog_linkedin.flow_b_blog_draft_generation as mod

    source = Path(mod.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "publish_blog_post",
        "generate_linkedin_package",
        "schedule_linkedin_distribution",
        "complete_flow_a_ready_path",
        "SILVERMAN_LINKEDIN_PUBLICATION_ENABLED",
    ):
        assert forbidden not in source
