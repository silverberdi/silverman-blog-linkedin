"""US-078: Flow B AI topic discovery (discovery-only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from silverman_blog_linkedin.deepseek_config import DeepSeekSettings
from silverman_blog_linkedin.flow_b_gap_operator_settings import (
    save_gap_operator_settings,
)
from silverman_blog_linkedin.flow_b_topic_discovery import (
    ERROR_NOT_OBJECTIVE_ALIGNED,
    STATUS_DISCOVERY_FAILED,
    STATUS_TOPICS_DISCOVERED,
    build_discovery_messages,
    clamp_discovery_count,
    discover_flow_b_topics,
    filter_objective_aligned_topics,
    is_news_chase_thesis,
    load_required_canon_sections,
    parse_provider_topics_json,
    read_recent_processed_titles,
    snapshot_draft_folders,
)
from silverman_blog_linkedin.main import create_app
from silverman_blog_linkedin.topic_discovery_provider import (
    PROVIDER_DEEPSEEK,
    DiscoveryProviderResult,
    DeepSeekTopicDiscoveryProvider,
    create_topic_discovery_provider,
)
from tests.conftest import auth_header, make_settings

DISCOVER_PATH = "/flow-b/discover-topics"

VALID_SETTINGS = {
    "operator_timezone": "America/Chicago",
    "gap_trigger_enabled": False,
    "gap_scan_mode": "next_week",
    "weekly_run_local_day": "friday",
    "weekly_run_local_time": "15:00",
    "min_lead_days": 5,
    "gap_posts_threshold": 0,
    "max_drafts_per_weekly_run": 2,
    "density_max_per_local_day": 2,
}

MINI_CANON = """\
## 2 Brand Positioning {#brand-positioning}

Lead with domain-first design. Referent, not news aggregator.

## 5 Content Pillars {#content-pillars}

Software architecture. Engineering leadership. AI-assisted SDLC.

## 6 Topic Boundaries {#topic-boundaries}

Allowed: architecture decisions with trade-offs.
Forbidden: news commentary and tool-vs-tool hot takes.

## 14 Flow A vs Flow B {#flow-a-vs-flow-b}

Career objective ≥ ~USD 7,000; discovery as referent not news spreader.
"""


class _StubProvider:
    def __init__(
        self,
        *,
        content: str | None = None,
        error_code: str | None = None,
        name: str = PROVIDER_DEEPSEEK,
    ) -> None:
        self._content = content
        self._error_code = error_code
        self._name = name
        self.calls: list[tuple[list[dict[str, str]], int]] = []

    @property
    def name(self) -> str:
        return self._name

    def discover_topics(
        self,
        messages: list[dict[str, str]],
        *,
        count: int,
    ) -> DiscoveryProviderResult:
        self.calls.append((messages, count))
        return DiscoveryProviderResult(
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
        "prompts/flow-b",
        "metadata/campaigns",
    ):
        (base / relative).mkdir(parents=True, exist_ok=True)
    return base


def _write_canon(tmp_path: Path, text: str = MINI_CANON) -> Path:
    path = tmp_path / "canon.md"
    path.write_text(text, encoding="utf-8")
    return path


def _topics_json(topics: list[dict[str, Any]]) -> str:
    return json.dumps({"topics": topics})


def _good_topics(n: int = 2) -> list[dict[str, Any]]:
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
            "pillar_hints": ["AI-assisted SDLC", "Engineering leadership"],
            "topic_id": "topic-ai-governance",
        },
        {
            "thesis": "Incremental modernization without rewrite theater",
            "referent_positioning": "Signals transformation leadership with risk control",
            "rationale": "Modernization pillar; distinct from prior theses",
            "pillar_hints": ["Modernization and technical debt"],
            "topic_id": "topic-modernization",
        },
    ]
    return items[:n]


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
    ):
        assert needle not in blob


def test_clamp_discovery_count_respects_ceiling() -> None:
    assert clamp_discovery_count(None, 2) == 2
    assert clamp_discovery_count(5, 2) == 2
    assert clamp_discovery_count(1, 2) == 1
    assert clamp_discovery_count(0, 2) == 1


def test_news_chase_filter() -> None:
    assert is_news_chase_thesis("X vs Y cloud vendors this week")
    assert is_news_chase_thesis("What's new in Kubernetes 1.32")
    assert not is_news_chase_thesis("Domain boundaries before ORM choices")


def test_provider_seam_deepseek_only() -> None:
    settings = DeepSeekSettings(
        api_key="test-key",
        base_url="https://api.deepseek.com",
        model="deepseek-v4-flash",
        timeout_seconds=30.0,
        max_output_tokens=1024,
    )
    provider = create_topic_discovery_provider("deepseek", settings=settings)
    assert isinstance(provider, DeepSeekTopicDiscoveryProvider)
    assert provider.name == PROVIDER_DEEPSEEK

    unsupported = create_topic_discovery_provider("openai", settings=settings)
    result = unsupported.discover_topics([], count=1)
    assert result.error_code == "discovery_provider_unsupported"
    assert result.content is None


def test_happy_path_n_distinct_topics(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    before = snapshot_draft_folders(base)
    stub = _StubProvider(content=_topics_json(_good_topics(2)))

    result = discover_flow_b_topics(
        base,
        count=2,
        provider=stub,
        canon_path=canon,
    )
    assert result.status == STATUS_TOPICS_DISCOVERED
    assert result.provider == PROVIDER_DEEPSEEK
    assert result.settings_source == "defaults"
    assert result.max_drafts_per_weekly_run == 2
    assert len(result.topics) == 2
    theses = {t.thesis for t in result.topics}
    assert len(theses) == 2
    for topic in result.topics:
        assert topic.referent_positioning
        assert topic.rationale
        assert topic.topic_id
    assert snapshot_draft_folders(base) == before
    assert len(stub.calls) == 1
    messages, count = stub.calls[0]
    assert count == 2
    joined = " ".join(m["content"] for m in messages).lower()
    assert "referent" in joined or "authority" in joined
    assert "x vs y" in joined or "what's new" in joined or "whats new" in joined


def test_clamp_to_max_drafts_and_db_max(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    save_gap_operator_settings({**VALID_SETTINGS, "max_drafts_per_weekly_run": 1})
    stub = _StubProvider(content=_topics_json(_good_topics(3)))

    result = discover_flow_b_topics(
        base,
        count=5,
        provider=stub,
        canon_path=canon,
    )
    assert result.status == STATUS_TOPICS_DISCOVERED
    assert result.settings_source == "database"
    assert result.max_drafts_per_weekly_run == 1
    assert len(result.topics) == 1
    assert stub.calls[0][1] == 1


def test_defaults_when_settings_row_missing(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    stub = _StubProvider(content=_topics_json(_good_topics(2)))
    result = discover_flow_b_topics(base, provider=stub, canon_path=canon)
    assert result.settings_source == "defaults"
    assert result.max_drafts_per_weekly_run == 2
    assert len(result.topics) == 2


def test_optional_gap_context_echoed(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    stub = _StubProvider(content=_topics_json(_good_topics(1)))
    result = discover_flow_b_topics(
        base,
        count=1,
        target_week="2026-W30",
        empty_days=["2026-07-22", "2026-07-23"],
        provider=stub,
        canon_path=canon,
    )
    assert result.status == STATUS_TOPICS_DISCOVERED
    assert result.gap_context == {
        "target_week": "2026-W30",
        "empty_days": ["2026-07-22", "2026-07-23"],
    }
    joined = " ".join(m["content"] for m in stub.calls[0][0])
    assert "2026-W30" in joined
    assert "2026-07-22" in joined


def test_runs_without_bl020_backlog(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    # Explicitly ensure no BL-020-style backlog folder is required.
    assert not (base / "topic-backlog").exists()
    canon = _write_canon(tmp_path)
    stub = _StubProvider(content=_topics_json(_good_topics(1)))
    result = discover_flow_b_topics(
        base,
        count=1,
        provider=stub,
        canon_path=canon,
    )
    assert result.status == STATUS_TOPICS_DISCOVERED


def test_soft_anti_dup_reads_processed_titles(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    processed = base / "blog-posts" / "processed"
    (processed / "older-post.md").write_text(
        "# Older architectural lesson\n\nBody.\n", encoding="utf-8"
    )
    (processed / "newer-post.md").write_text(
        "# Newer delivery discipline note\n\nBody.\n", encoding="utf-8"
    )
    titles = read_recent_processed_titles(base, limit=5)
    assert "Newer delivery discipline note" in titles
    assert "Older architectural lesson" in titles

    sections, err = load_required_canon_sections(_write_canon(tmp_path))
    assert err is None and sections is not None
    messages = build_discovery_messages(
        sections=sections,
        recent_titles=titles,
        primary_material=[],
        count=1,
        target_week=None,
        empty_days=None,
    )
    joined = " ".join(m["content"] for m in messages)
    assert "Newer delivery discipline note" in joined


def test_news_chase_only_fails_closed(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    before = snapshot_draft_folders(base)
    stub = _StubProvider(
        content=_topics_json(
            [
                {
                    "thesis": "AWS vs Azure: what's new this week",
                    "referent_positioning": "comparison",
                    "rationale": "hot take",
                }
            ]
        )
    )
    result = discover_flow_b_topics(
        base,
        count=1,
        provider=stub,
        canon_path=canon,
    )
    assert result.status == STATUS_DISCOVERY_FAILED
    assert result.error_code == ERROR_NOT_OBJECTIVE_ALIGNED
    assert result.topics == []
    assert snapshot_draft_folders(base) == before


def test_missing_deepseek_config_fails_closed(tmp_path: Path, monkeypatch) -> None:
    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    before = snapshot_draft_folders(base)
    result = discover_flow_b_topics(
        base,
        count=1,
        canon_path=canon,
        environ={"DEEPSEEK_TIMEOUT_SECONDS": "not-a-number"},
    )
    assert result.status == STATUS_DISCOVERY_FAILED
    assert result.error_code == "discovery_config_invalid"
    assert snapshot_draft_folders(base) == before


def test_missing_api_key_fails_closed(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    result = discover_flow_b_topics(
        base,
        count=1,
        canon_path=canon,
        environ={"DEEPSEEK_API_KEY": ""},
    )
    assert result.status == STATUS_DISCOVERY_FAILED
    assert result.error_code == "deepseek_api_key_missing"


def test_filter_rejects_incomplete_and_duplicate() -> None:
    raw = parse_provider_topics_json(
        _topics_json(
            [
                {
                    "thesis": "Same thesis",
                    "referent_positioning": "A",
                    "rationale": "R1",
                },
                {
                    "thesis": "Same thesis",
                    "referent_positioning": "B",
                    "rationale": "R2",
                },
                {"thesis": "Incomplete", "rationale": "missing referent"},
            ]
        ),
        count=3,
    )
    topics = filter_objective_aligned_topics(raw, count=3)
    assert len(topics) == 1
    assert topics[0].thesis == "Same thesis"


def test_http_auth_required(tmp_path: Path) -> None:
    client = TestClient(create_app(make_settings(_editorial_base(tmp_path))))
    response = client.post(DISCOVER_PATH, json={"count": 1})
    assert response.status_code == 401


def test_http_happy_path_and_no_draft_writes(
    tmp_path: Path, monkeypatch
) -> None:
    base = _editorial_base(tmp_path)
    (base / "blog-posts" / "ready" / "marker.txt").write_text("keep\n", encoding="utf-8")
    (base / "blog-posts" / "pending-approval").mkdir(parents=True, exist_ok=True)
    before = snapshot_draft_folders(base)
    canon = _write_canon(tmp_path)

    stub = _StubProvider(content=_topics_json(_good_topics(2)))

    def _fake_discover(base_path: Path, **kwargs: Any):
        patched = dict(kwargs)
        patched["provider"] = stub
        patched["canon_path"] = canon
        return discover_flow_b_topics(base_path, **patched)

    monkeypatch.setattr(
        "silverman_blog_linkedin.main.discover_flow_b_topics",
        _fake_discover,
    )
    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        DISCOVER_PATH,
        headers=auth_header(),
        json={
            "count": 2,
            "target_week": "2026-W30",
            "empty_days": ["2026-07-22"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == STATUS_TOPICS_DISCOVERED
    assert body["provider"] == PROVIDER_DEEPSEEK
    assert body["max_drafts_per_weekly_run"] == 2
    assert body["settings_source"] == "defaults"
    assert len(body["topics"]) == 2
    assert body["gap_context"]["target_week"] == "2026-W30"
    assert "observed_at_utc" in body
    _assert_no_secrets(body)
    assert snapshot_draft_folders(base) == before


def test_http_news_chase_fails_closed(tmp_path: Path, monkeypatch) -> None:
    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    stub = _StubProvider(
        content=_topics_json(
            [
                {
                    "thesis": "Top stories: X vs Y frameworks",
                    "referent_positioning": "news",
                    "rationale": "chase",
                }
            ]
        )
    )

    def _fake_discover(base_path: Path, **kwargs: Any):
        patched = dict(kwargs)
        patched["provider"] = stub
        patched["canon_path"] = canon
        return discover_flow_b_topics(base_path, **patched)

    monkeypatch.setattr(
        "silverman_blog_linkedin.main.discover_flow_b_topics",
        _fake_discover,
    )
    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        DISCOVER_PATH,
        headers=auth_header(),
        json={"count": 1},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["status"] == STATUS_DISCOVERY_FAILED
    assert detail["error_code"] == ERROR_NOT_OBJECTIVE_ALIGNED
    _assert_no_secrets(detail)


def test_http_dry_run_skips_provider(tmp_path: Path, monkeypatch) -> None:
    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    stub = _StubProvider(content=_topics_json(_good_topics(1)))

    def _fake_discover(base_path: Path, **kwargs: Any):
        patched = dict(kwargs)
        patched["provider"] = stub
        patched["canon_path"] = canon
        return discover_flow_b_topics(base_path, **patched)

    monkeypatch.setattr(
        "silverman_blog_linkedin.main.discover_flow_b_topics",
        _fake_discover,
    )
    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        DISCOVER_PATH,
        headers=auth_header(),
        json={"dry_run": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "discovery_dry_run"
    assert body["topics"] == []
    assert stub.calls == []


def test_no_out_of_scope_routes_added(tmp_path: Path) -> None:
    """US-078 adds discovery only — not draft/approve/promote/trigger."""
    app = create_app(make_settings(_editorial_base(tmp_path)))
    paths = {getattr(route, "path", None) for route in app.routes}
    assert "/flow-b/discover-topics" in paths
    forbidden = {
        "/flow-b/gap-trigger",
        "/flow-b/draft",
        "/flow-b/approve",
        "/flow-b/promote",
    }
    assert not (paths & forbidden)
